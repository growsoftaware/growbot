#!/usr/bin/env python3
"""
GrowBot API - FastAPI para o frontend mobile
Endpoints REST para consumo de dados do DuckDB
"""

import json
import duckdb
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="GrowBot API",
    description="API REST para o GrowBot Mobile",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão read-only para evitar problemas de lock
DB_PATH = Path(__file__).parent / "growbot.duckdb"

def get_db():
    """Cria conexão read-only fresh para cada request"""
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_db_write():
    """Cria conexão write para operações de escrita"""
    return duckdb.connect(str(DB_PATH), read_only=False)


# Drivers válidos
DRIVERS = ["RAFA", "FRANCIS", "RODRIGO", "KAROL", "ARTHUR"]

OUTPUT_PATH = Path(__file__).parent / "output"


def parse_date_br(date_str: str) -> Optional[str]:
    """Converte DD/MM/YYYY para YYYY-MM-DD"""
    if not date_str:
        return None
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            day, month, year = parts
            if len(year) == 2:
                year = "20" + year
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        pass
    return None


def iso_to_br(date_str: str) -> str:
    """Converte YYYY-MM-DD para DD/MM/YYYY"""
    if not date_str:
        return ""
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except:
        pass
    return date_str


def normalizar_tipo(tipo: str) -> str:
    """Normaliza tipos de movimento para exibição"""
    mapa = {
        "estoque": "estoque",
        "recarga": "recarga",
        "entrega": "entrega",
        "resgate_saida": "entrega",
        "resgate_entrada": "recarga"
    }
    return mapa.get(tipo, tipo)


# ============ ENDPOINTS ============

@app.get("/api/health")
def health_check():
    """Health check da API"""
    try:
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM movimentos").fetchone()[0]
        conn.close()
        return {
            "status": "ok",
            "db_connected": True,
            "total_registros": total,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "db_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/drivers")
def get_drivers():
    """Lista de drivers válidos"""
    return {"drivers": DRIVERS}


@app.get("/api/kpis")
def get_kpis(
    data_inicio: str = Query(None, description="Data início DD/MM/YYYY"),
    data_fim: str = Query(None, description="Data fim DD/MM/YYYY"),
    driver: str = Query(None, description="Filtrar por driver")
):
    """
    Retorna KPIs calculados (replica lógica do TUI)
    """
    # Converte datas
    data_ini_iso = parse_date_br(data_inicio) if data_inicio else None
    data_fim_iso = parse_date_br(data_fim) if data_fim else None

    # Query base com filtros
    where_clauses = []
    params = []

    if data_ini_iso:
        where_clauses.append("data_movimento >= ?")
        params.append(data_ini_iso)
    if data_fim_iso:
        where_clauses.append("data_movimento <= ?")
        params.append(data_fim_iso)
    if driver and driver != "TODOS":
        where_clauses.append("driver = ?")
        params.append(driver)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # KPIs de entregas (IDs distintos)
    query_entregas = f"""
        SELECT COUNT(DISTINCT endereco || '-' || data_movimento || '-' || driver) as total
        FROM movimentos
        WHERE tipo = 'entrega' AND {where_sql}
    """
    entregas_result = get_db().execute(query_entregas, params).fetchone()
    kpi_entregas = entregas_result[0] if entregas_result else 0

    # KPIs de retiradas (datas distintas com recarga)
    query_retiradas = f"""
        SELECT COUNT(DISTINCT data_movimento) as total
        FROM movimentos
        WHERE tipo = 'recarga' AND {where_sql}
    """
    retiradas_result = get_db().execute(query_retiradas, params).fetchone()
    kpi_retiradas = retiradas_result[0] if retiradas_result else 0

    # Totais por tipo
    query_totais = f"""
        SELECT
            tipo,
            SUM(quantidade) as total
        FROM movimentos
        WHERE {where_sql}
        GROUP BY tipo
    """
    totais = get_db().execute(query_totais, params).fetchall()

    total_estoque = 0
    total_recarga = 0
    total_entrega = 0

    for tipo, total in totais:
        if tipo == "estoque":
            total_estoque = total or 0
        elif tipo == "recarga" or tipo == "resgate_entrada":
            total_recarga += total or 0
        elif tipo == "entrega" or tipo == "resgate_saida":
            total_entrega += total or 0

    # Produtos negativos
    query_negativos = f"""
        SELECT COUNT(*) FROM (
            SELECT
                driver, produto,
                SUM(CASE WHEN tipo IN ('estoque', 'recarga', 'resgate_entrada') THEN quantidade ELSE 0 END) -
                SUM(CASE WHEN tipo IN ('entrega', 'resgate_saida') THEN quantidade ELSE 0 END) as saldo
            FROM movimentos
            WHERE {where_sql}
            GROUP BY driver, produto
            HAVING saldo < 0
        )
    """
    negativos_result = get_db().execute(query_negativos, params).fetchone()
    kpi_negativos = negativos_result[0] if negativos_result else 0

    # Saldo total
    saldo = total_estoque + total_recarga - total_entrega

    return {
        "entregas": kpi_entregas,
        "retiradas": kpi_retiradas,
        "negativos": kpi_negativos,
        "total_recarga": total_recarga,
        "total_entrega": total_entrega,
        "total_estoque": total_estoque,
        "saldo": saldo
    }


@app.get("/api/movimentos")
def get_movimentos(
    data_inicio: str = Query(None, description="Data início DD/MM/YYYY"),
    data_fim: str = Query(None, description="Data fim DD/MM/YYYY"),
    driver: str = Query(None, description="Filtrar por driver")
):
    """
    Retorna movimentos agregados para a tabela (replica estrutura do TUI)
    """
    data_ini_iso = parse_date_br(data_inicio) if data_inicio else None
    data_fim_iso = parse_date_br(data_fim) if data_fim else None

    # Query base com filtros
    where_clauses = []
    params = []

    if data_ini_iso:
        where_clauses.append("data_movimento >= ?")
        params.append(data_ini_iso)
    if data_fim_iso:
        where_clauses.append("data_movimento <= ?")
        params.append(data_fim_iso)
    if driver and driver != "TODOS":
        where_clauses.append("driver = ?")
        params.append(driver)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Busca movimentos agregados
    query = f"""
        SELECT
            driver,
            produto,
            CAST(data_movimento AS VARCHAR) as data,
            tipo,
            SUM(quantidade) as total
        FROM movimentos
        WHERE {where_sql}
        GROUP BY driver, produto, data_movimento, tipo
        ORDER BY driver, produto, data_movimento
    """

    rows = get_db().execute(query, params).fetchall()

    # Organiza dados por driver -> produto -> data -> tipo
    dados_driver = {}  # driver -> {data_tipo: total}
    dados_produto = {}  # driver -> produto -> {data_tipo: total}
    todas_colunas = set()  # (data, tipo_normalizado)

    for driver_name, produto, data, tipo, total in rows:
        tipo_norm = normalizar_tipo(tipo)
        col_key = f"{data}_{tipo_norm}"
        todas_colunas.add((data, tipo_norm))

        # Agregado por driver
        if driver_name not in dados_driver:
            dados_driver[driver_name] = {}
        if col_key not in dados_driver[driver_name]:
            dados_driver[driver_name][col_key] = 0
        dados_driver[driver_name][col_key] += total

        # Agregado por produto
        if driver_name not in dados_produto:
            dados_produto[driver_name] = {}
        if produto not in dados_produto[driver_name]:
            dados_produto[driver_name][produto] = {}
        if col_key not in dados_produto[driver_name][produto]:
            dados_produto[driver_name][produto][col_key] = 0
        dados_produto[driver_name][produto][col_key] += total

    # Ordena colunas por data
    colunas_ordenadas = sorted(todas_colunas, key=lambda x: (x[0], x[1]))

    # Monta lista de colunas
    colunas = [{"data": data, "tipo": tipo} for data, tipo in colunas_ordenadas]

    # Monta lista de drivers com produtos
    drivers_list = []

    for driver_name in sorted(dados_driver.keys()):
        # Calcula saldo do driver
        valores_driver = dados_driver[driver_name]
        saldo_driver = sum(
            v for k, v in valores_driver.items()
            if k.endswith("_estoque") or k.endswith("_recarga")
        ) - sum(
            v for k, v in valores_driver.items()
            if k.endswith("_entrega")
        )

        # Monta produtos do driver
        produtos_list = []
        if driver_name in dados_produto:
            for produto_name in sorted(dados_produto[driver_name].keys()):
                valores_prod = dados_produto[driver_name][produto_name]
                saldo_prod = sum(
                    v for k, v in valores_prod.items()
                    if k.endswith("_estoque") or k.endswith("_recarga")
                ) - sum(
                    v for k, v in valores_prod.items()
                    if k.endswith("_entrega")
                )

                produtos_list.append({
                    "produto": produto_name,
                    "saldo": saldo_prod,
                    "valores": valores_prod
                })

        drivers_list.append({
            "driver": driver_name,
            "saldo_total": saldo_driver,
            "valores": valores_driver,
            "produtos": produtos_list
        })

    return {
        "colunas": colunas,
        "drivers": drivers_list
    }


@app.get("/api/cards")
def get_cards(
    data_inicio: str = Query(None, description="Data início DD/MM/YYYY"),
    data_fim: str = Query(None, description="Data fim DD/MM/YYYY"),
    driver: str = Query(None, description="Filtrar por driver")
):
    """
    Retorna dados para visão de cards (agrupados por data/driver)
    """
    data_ini_iso = parse_date_br(data_inicio) if data_inicio else None
    data_fim_iso = parse_date_br(data_fim) if data_fim else None

    where_clauses = []
    params = []

    if data_ini_iso:
        where_clauses.append("data_movimento >= ?")
        params.append(data_ini_iso)
    if data_fim_iso:
        where_clauses.append("data_movimento <= ?")
        params.append(data_fim_iso)
    if driver and driver != "TODOS":
        where_clauses.append("driver = ?")
        params.append(driver)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Busca entregas agrupadas
    query_entregas = f"""
        SELECT
            CAST(data_movimento AS VARCHAR) as data,
            driver,
            endereco,
            produto,
            SUM(quantidade) as total
        FROM movimentos
        WHERE tipo = 'entrega' AND {where_sql}
        GROUP BY data_movimento, driver, endereco, produto
        ORDER BY data_movimento DESC, driver
    """

    entregas = get_db().execute(query_entregas, params).fetchall()

    # Busca recargas
    query_recargas = f"""
        SELECT
            CAST(data_movimento AS VARCHAR) as data,
            driver,
            produto,
            SUM(quantidade) as total
        FROM movimentos
        WHERE tipo = 'recarga' AND {where_sql}
        GROUP BY data_movimento, driver, produto
        ORDER BY data_movimento DESC, driver
    """

    recargas = get_db().execute(query_recargas, params).fetchall()

    # Agrupa por (data, driver)
    cards_dict = {}

    # Processa entregas
    for data, drv, endereco, produto, total in entregas:
        key = (data, drv)
        if key not in cards_dict:
            cards_dict[key] = {
                "data": iso_to_br(data),
                "data_iso": data,
                "driver": drv,
                "resumo": {
                    "total_entregas": 0,
                    "total_unidades": 0,
                    "total_recargas": 0
                },
                "entregas": {},
                "recargas": []
            }

        # Agrupa por endereco (como ID proxy)
        if endereco not in cards_dict[key]["entregas"]:
            cards_dict[key]["entregas"][endereco] = []
        cards_dict[key]["entregas"][endereco].append({
            "produto": produto,
            "quantidade": total
        })
        cards_dict[key]["resumo"]["total_entregas"] += 1
        cards_dict[key]["resumo"]["total_unidades"] += total

    # Processa recargas
    for data, drv, produto, total in recargas:
        key = (data, drv)
        if key not in cards_dict:
            cards_dict[key] = {
                "data": iso_to_br(data),
                "data_iso": data,
                "driver": drv,
                "resumo": {
                    "total_entregas": 0,
                    "total_unidades": 0,
                    "total_recargas": 0
                },
                "entregas": {},
                "recargas": []
            }

        cards_dict[key]["recargas"].append({
            "produto": produto,
            "quantidade": total
        })
        cards_dict[key]["resumo"]["total_recargas"] += total

    # Converte entregas dict para lista
    cards_list = []
    for key in sorted(cards_dict.keys(), key=lambda x: x[0], reverse=True):
        card = cards_dict[key]
        entregas_list = []
        for endereco, produtos in card["entregas"].items():
            entregas_list.append({
                "id": endereco or "sem-endereco",
                "produtos": [f"{p['quantidade']} {p['produto']}" for p in produtos]
            })
        card["entregas"] = entregas_list
        cards_list.append(card)

    return {"cards": cards_list}


@app.get("/api/detalhes/{driver_name}/{produto_name}")
def get_detalhes(
    driver_name: str,
    produto_name: str,
    data_inicio: str = Query(None, description="Data início DD/MM/YYYY"),
    data_fim: str = Query(None, description="Data fim DD/MM/YYYY")
):
    """
    Retorna detalhes das entregas de um produto específico
    """
    data_ini_iso = parse_date_br(data_inicio) if data_inicio else None
    data_fim_iso = parse_date_br(data_fim) if data_fim else None

    where_clauses = ["driver = ?", "produto = ?", "tipo = 'entrega'"]
    params = [driver_name, produto_name]

    if data_ini_iso:
        where_clauses.append("data_movimento >= ?")
        params.append(data_ini_iso)
    if data_fim_iso:
        where_clauses.append("data_movimento <= ?")
        params.append(data_fim_iso)

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            CAST(data_movimento AS VARCHAR) as data,
            endereco,
            quantidade
        FROM movimentos
        WHERE {where_sql}
        ORDER BY data_movimento DESC, endereco
    """

    rows = get_db().execute(query, params).fetchall()

    # Agrupa por data
    por_data = {}
    total_entregas = 0
    total_unidades = 0

    for data, endereco, quantidade in rows:
        if data not in por_data:
            por_data[data] = []
        por_data[data].append({
            "id": endereco or f"entrega-{len(por_data[data])+1}",
            "quantidade": quantidade,
            "endereco": endereco
        })
        total_entregas += 1
        total_unidades += quantidade

    # Converte para lista ordenada
    por_data_list = [
        {
            "data": iso_to_br(data),
            "entregas": entregas
        }
        for data, entregas in sorted(por_data.items(), reverse=True)
    ]

    return {
        "driver": driver_name,
        "produto": produto_name,
        "total_entregas": total_entregas,
        "total_unidades": total_unidades,
        "por_data": por_data_list
    }


@app.get("/api/saldo")
def get_saldo(driver: str = Query(None, description="Filtrar por driver")):
    """
    Retorna saldo por driver
    """
    conn = get_db()
    query = """
        SELECT
            driver,
            SUM(CASE WHEN tipo = 'estoque' THEN quantidade ELSE 0 END) as estoque,
            SUM(CASE WHEN tipo = 'recarga' THEN quantidade ELSE 0 END) as recargas,
            SUM(CASE WHEN tipo = 'entrega' THEN quantidade ELSE 0 END) as saidas,
            SUM(CASE WHEN tipo = 'estoque' THEN quantidade ELSE 0 END) +
            SUM(CASE WHEN tipo = 'recarga' THEN quantidade ELSE 0 END) -
            SUM(CASE WHEN tipo = 'entrega' THEN quantidade ELSE 0 END) as saldo
        FROM movimentos
    """
    params = []
    if driver and driver != "TODOS":
        query += " WHERE driver = ?"
        params.append(driver)
    query += " GROUP BY driver ORDER BY driver"

    result = conn.execute(query, params)
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    conn.close()

    saldos = [dict(zip(columns, row)) for row in rows]
    return {"saldos": saldos}


# ============ NOVOS ENDPOINTS PARA SYNC ============

@app.get("/api/movimentos/export")
def export_movimentos(
    data_inicio: str = Query(None, description="Data início DD/MM/YYYY"),
    data_fim: str = Query(None, description="Data fim DD/MM/YYYY"),
    driver: str = Query(None, description="Filtrar por driver"),
    tipo: str = Query(None, description="Filtrar por tipo (entrega, recarga, estoque)"),
    include_reviews: bool = Query(True, description="Incluir campos de review")
):
    """
    Exporta movimentos com todos os campos para sync com Grow.
    Retorna lista completa de movimentos com filtros opcionais.
    """
    data_ini_iso = parse_date_br(data_inicio) if data_inicio else None
    data_fim_iso = parse_date_br(data_fim) if data_fim else None

    where_clauses = []
    params = []

    if data_ini_iso:
        where_clauses.append("data_movimento >= ?")
        params.append(data_ini_iso)
    if data_fim_iso:
        where_clauses.append("data_movimento <= ?")
        params.append(data_fim_iso)
    if driver and driver != "TODOS":
        where_clauses.append("driver = ?")
        params.append(driver)
    if tipo:
        where_clauses.append("tipo = ?")
        params.append(tipo)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Campos base (com alias m. para movimentos, b. para blocos_raw)
    campos = [
        "m.id", "m.tipo", "m.driver", "m.driver_destino", "m.produto", "m.quantidade",
        "CAST(m.data_movimento AS VARCHAR) as data_movimento",
        "m.endereco", "m.observacao",
        # Campos de rastreabilidade vêm de blocos_raw
        "b.arquivo_origem", "b.linha_origem", "b.texto_raw",
        "CAST(m.created_at AS VARCHAR) as created_at",
        "m.id_sale_delivery"
    ]

    # Campos de review opcionais (agora vêm de blocos_raw)
    if include_reviews:
        campos.extend([
            "b.review_status", "b.review_severity", "b.review_category",
            "b.review_issue", "b.review_ai_notes"
        ])

    # Prefixar where_sql com m.
    where_sql_prefixed = where_sql.replace("data_movimento", "m.data_movimento").replace("driver =", "m.driver =").replace("tipo =", "m.tipo =")

    query = f"""
        SELECT {', '.join(campos)}
        FROM movimentos m
        LEFT JOIN blocos_raw b
            ON m.id_sale_delivery = b.id_sale_delivery
            AND b.data_entrega = m.data_movimento
            AND b.driver = m.driver
        WHERE {where_sql_prefixed}
        ORDER BY m.data_movimento DESC, m.driver, m.id
    """

    conn = get_db()
    result = conn.execute(query, params)
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    conn.close()

    movimentos = [dict(zip(columns, row)) for row in rows]

    return {
        "total": len(movimentos),
        "movimentos": movimentos
    }


@app.get("/api/matriz")
def get_matriz(
    data_inicio: str = Query(None, description="Data início DD/MM/YYYY"),
    data_fim: str = Query(None, description="Data fim DD/MM/YYYY"),
    driver: str = Query(None, description="Filtrar por driver")
):
    """
    Retorna matriz drivers x datas com totais por tipo.
    Formato: {drivers: [...], datas: [...], matriz: {driver: {data: {tipo: total}}}}
    """
    data_ini_iso = parse_date_br(data_inicio) if data_inicio else None
    data_fim_iso = parse_date_br(data_fim) if data_fim else None

    where_clauses = []
    params = []

    if data_ini_iso:
        where_clauses.append("data_movimento >= ?")
        params.append(data_ini_iso)
    if data_fim_iso:
        where_clauses.append("data_movimento <= ?")
        params.append(data_fim_iso)
    if driver and driver != "TODOS":
        where_clauses.append("driver = ?")
        params.append(driver)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
        SELECT
            driver,
            CAST(data_movimento AS VARCHAR) as data,
            tipo,
            SUM(quantidade) as total
        FROM movimentos
        WHERE {where_sql}
        GROUP BY driver, data_movimento, tipo
        ORDER BY driver, data_movimento
    """

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    # Coleta drivers e datas únicos
    drivers_set = set()
    datas_set = set()
    matriz = {}

    for drv, data, tipo, total in rows:
        drivers_set.add(drv)
        datas_set.add(data)

        if drv not in matriz:
            matriz[drv] = {}
        if data not in matriz[drv]:
            matriz[drv][data] = {}

        tipo_norm = normalizar_tipo(tipo)
        if tipo_norm not in matriz[drv][data]:
            matriz[drv][data][tipo_norm] = 0
        matriz[drv][data][tipo_norm] += total

    # Ordena
    drivers_list = sorted(drivers_set)
    datas_list = sorted(datas_set)

    return {
        "drivers": drivers_list,
        "datas": [iso_to_br(d) for d in datas_list],
        "datas_iso": datas_list,
        "matriz": matriz
    }


# ============ ENDPOINTS DE EXPORTS (arquivos raw) ============

EXPORTS_PATH = Path(__file__).parent / "exports"


@app.get("/api/exports")
def list_exports():
    """
    Lista todos os arquivos de export disponíveis.
    Retorna nome, tamanho e número de linhas de cada arquivo.
    """
    exports = []

    # Lista arquivos .txt na pasta exports (não recursivo para subpastas)
    for txt_file in sorted(EXPORTS_PATH.glob("*.txt")):
        try:
            stat = txt_file.stat()
            with open(txt_file, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)

            exports.append({
                "filename": txt_file.name,
                "size_bytes": stat.st_size,
                "size_kb": round(stat.st_size / 1024, 2),
                "total_lines": line_count,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except Exception as e:
            exports.append({
                "filename": txt_file.name,
                "error": str(e)
            })

    # Lista subpastas com arquivos
    subfolders = []
    for folder in EXPORTS_PATH.iterdir():
        if folder.is_dir():
            txt_files = list(folder.glob("*.txt"))
            if txt_files:
                subfolders.append({
                    "folder": folder.name,
                    "file_count": len(txt_files)
                })

    return {
        "exports": exports,
        "subfolders": subfolders,
        "total_files": len(exports)
    }


@app.get("/api/exports/{filename}")
def get_export_lines(
    filename: str,
    linha_inicial: int = Query(1, ge=1, description="Linha inicial (1-indexed)"),
    linha_final: int = Query(None, description="Linha final (inclusive). Se não informado, retorna até o fim do arquivo"),
    max_lines: int = Query(500, ge=1, le=5000, description="Máximo de linhas por request (segurança)")
):
    """
    Retorna linhas de um arquivo de export.

    Parâmetros:
    - filename: Nome do arquivo (ex: _chat.txt)
    - linha_inicial: Primeira linha a retornar (1 = primeira linha do arquivo)
    - linha_final: Última linha a retornar (inclusive)
    - max_lines: Limite de segurança (padrão 500, máximo 5000)

    Retorna:
    - lines: Array de objetos {line_number, content}
    - metadata: Informações sobre o arquivo e range retornado
    """
    # Sanitiza filename (evita path traversal)
    safe_filename = Path(filename).name
    file_path = EXPORTS_PATH / safe_filename

    # Tenta também em subpastas conhecidas
    if not file_path.exists():
        for subfolder in ["missing", "backup_20260102"]:
            alt_path = EXPORTS_PATH / subfolder / safe_filename
            if alt_path.exists():
                file_path = alt_path
                break

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo '{filename}' não encontrado")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {str(e)}")

    total_lines = len(all_lines)

    # Ajusta linha_final se não informado
    if linha_final is None:
        linha_final = min(linha_inicial + max_lines - 1, total_lines)

    # Valida range
    if linha_inicial > total_lines:
        raise HTTPException(
            status_code=400,
            detail=f"linha_inicial ({linha_inicial}) maior que total de linhas ({total_lines})"
        )

    # Limita quantidade de linhas
    requested_lines = linha_final - linha_inicial + 1
    if requested_lines > max_lines:
        linha_final = linha_inicial + max_lines - 1
        requested_lines = max_lines

    # Ajusta para não ultrapassar arquivo
    linha_final = min(linha_final, total_lines)

    # Extrai linhas (converte para 0-indexed)
    lines = []
    for i in range(linha_inicial - 1, linha_final):
        lines.append({
            "line_number": i + 1,
            "content": all_lines[i].rstrip('\n\r')
        })

    return {
        "filename": safe_filename,
        "lines": lines,
        "metadata": {
            "total_lines_file": total_lines,
            "linha_inicial": linha_inicial,
            "linha_final": linha_final,
            "lines_returned": len(lines),
            "has_more": linha_final < total_lines
        }
    }


@app.get("/api/exports/{filename}/search")
def search_export(
    filename: str,
    query: str = Query(..., min_length=1, description="Texto a buscar"),
    context_lines: int = Query(2, ge=0, le=10, description="Linhas de contexto antes/depois"),
    max_results: int = Query(50, ge=1, le=200, description="Máximo de resultados")
):
    """
    Busca texto em um arquivo de export e retorna matches com contexto.

    Parâmetros:
    - filename: Nome do arquivo
    - query: Texto a buscar (case-insensitive)
    - context_lines: Quantas linhas mostrar antes e depois do match
    - max_results: Limite de resultados

    Retorna:
    - matches: Array de {line_number, content, context_before, context_after}
    """
    # Sanitiza filename
    safe_filename = Path(filename).name
    file_path = EXPORTS_PATH / safe_filename

    if not file_path.exists():
        for subfolder in ["missing", "backup_20260102"]:
            alt_path = EXPORTS_PATH / subfolder / safe_filename
            if alt_path.exists():
                file_path = alt_path
                break

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo '{filename}' não encontrado")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = [line.rstrip('\n\r') for line in f.readlines()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {str(e)}")

    query_lower = query.lower()
    matches = []

    for i, line in enumerate(all_lines):
        if query_lower in line.lower():
            # Pega contexto
            start = max(0, i - context_lines)
            end = min(len(all_lines), i + context_lines + 1)

            matches.append({
                "line_number": i + 1,
                "content": line,
                "context_before": [
                    {"line_number": j + 1, "content": all_lines[j]}
                    for j in range(start, i)
                ],
                "context_after": [
                    {"line_number": j + 1, "content": all_lines[j]}
                    for j in range(i + 1, end)
                ]
            })

            if len(matches) >= max_results:
                break

    return {
        "filename": safe_filename,
        "query": query,
        "total_matches": len(matches),
        "truncated": len(matches) >= max_results,
        "matches": matches
    }


# ============ ENDPOINTS LEGADOS (compatibilidade) ============

def get_latest_output(provider: str) -> dict:
    """Pega o output mais recente de um provider."""
    files = sorted(OUTPUT_PATH.glob(f"*{provider}*.json"), reverse=True)
    if files:
        with open(files[0]) as f:
            return json.load(f)
    return {"items": []}


def get_input_text() -> str:
    """Pega o texto do input original."""
    exports_dir = Path(__file__).parent / "exports"
    for txt in exports_dir.glob("*.txt"):
        with open(txt, encoding="utf-8") as f:
            return f.read()
    return ""


@app.get("/api/data")
def get_data():
    """Endpoint legado: dados consolidados"""
    return {
        "input": get_input_text(),
        "claude": get_latest_output("claude"),
        "openai": get_latest_output("openai"),
    }


@app.get("/api/items/{provider}")
def get_items(provider: str):
    """Endpoint legado: items por provider"""
    return get_latest_output(provider)


# ============ MAIN ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
