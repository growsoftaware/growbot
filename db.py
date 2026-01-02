"""
GrowBot Database - DuckDB para consultas analíticas
"""
import duckdb
from pathlib import Path
from datetime import datetime
import json

DB_PATH = Path(__file__).parent / "growbot.duckdb"
OUTPUT_PATH = Path(__file__).parent / "output"


class GrowBotDB:
    def __init__(self, db_path: Path = DB_PATH, read_only: bool = False):
        self.db_path = db_path
        self.read_only = read_only
        self.conn = duckdb.connect(str(db_path), read_only=read_only)
        if not read_only:
            self._init_schema()

    def _init_schema(self):
        """Cria tabelas e views se não existirem"""

        # Sequência para IDs
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_movimentos START 1")
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_aliases START 1")

        # Tabela principal de movimentos
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS movimentos (
                id INTEGER DEFAULT nextval('seq_movimentos') PRIMARY KEY,
                tipo VARCHAR NOT NULL,
                driver VARCHAR NOT NULL,
                driver_destino VARCHAR,
                produto VARCHAR NOT NULL,
                quantidade INTEGER NOT NULL,
                data_movimento DATE NOT NULL,
                endereco VARCHAR,
                observacao VARCHAR,
                arquivo_origem VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                review_severity VARCHAR,
                review_category VARCHAR,
                review_status VARCHAR,
                review_issue TEXT,
                review_ai_notes TEXT,
                review_human_notes TEXT,
                review_decision TEXT,
                reviewed_at TIMESTAMP
            )
        """)

        # Migração: Adiciona colunas de review se não existirem (para bancos antigos)
        self._migrate_review_columns()

        # Tabela de aliases
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER DEFAULT nextval('seq_aliases') PRIMARY KEY,
                alias VARCHAR UNIQUE NOT NULL,
                canonical VARCHAR NOT NULL,
                reason VARCHAR
            )
        """)

        # Tabela de controle de arquivos importados
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS arquivos_importados (
                arquivo VARCHAR PRIMARY KEY,
                tipo VARCHAR,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Views para relatórios
        self._create_views()

    def _migrate_review_columns(self):
        """Adiciona colunas de review em bancos existentes (migração)"""
        review_columns = [
            ("review_severity", "VARCHAR"),
            ("review_category", "VARCHAR"),
            ("review_status", "VARCHAR"),
            ("review_issue", "TEXT"),
            ("review_ai_notes", "TEXT"),
            ("review_human_notes", "TEXT"),
            ("review_decision", "TEXT"),
            ("reviewed_at", "TIMESTAMP"),
        ]

        # Verifica colunas existentes
        existing = self.conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'movimentos'"
        ).fetchall()
        existing_names = {row[0] for row in existing}

        # Adiciona colunas faltantes
        for col_name, col_type in review_columns:
            if col_name not in existing_names:
                self.conn.execute(f"ALTER TABLE movimentos ADD COLUMN {col_name} {col_type}")

    def _create_views(self):
        """Cria views para relatórios"""

        # View: Saldo por driver
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_saldo_driver AS
            SELECT
                driver,
                SUM(CASE WHEN tipo = 'estoque' THEN quantidade ELSE 0 END) as estoque,
                SUM(CASE WHEN tipo = 'recarga' THEN quantidade ELSE 0 END) as recargas,
                SUM(CASE WHEN tipo = 'entrega' THEN quantidade ELSE 0 END) as saidas,
                SUM(CASE
                    WHEN tipo = 'resgate_saida' THEN -quantidade
                    WHEN tipo = 'resgate_entrada' THEN quantidade
                    ELSE 0
                END) as resgates,
                SUM(CASE WHEN tipo = 'estoque' THEN quantidade ELSE 0 END) +
                SUM(CASE WHEN tipo = 'recarga' THEN quantidade ELSE 0 END) -
                SUM(CASE WHEN tipo = 'entrega' THEN quantidade ELSE 0 END) +
                SUM(CASE
                    WHEN tipo = 'resgate_saida' THEN -quantidade
                    WHEN tipo = 'resgate_entrada' THEN quantidade
                    ELSE 0
                END) as saldo
            FROM movimentos
            GROUP BY driver
            ORDER BY driver
        """)

        # View: Saldo por produto por driver
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_saldo_produto AS
            SELECT
                driver,
                produto,
                SUM(CASE WHEN tipo IN ('estoque', 'recarga', 'resgate_entrada') THEN quantidade ELSE 0 END) as entradas,
                SUM(CASE WHEN tipo IN ('entrega', 'resgate_saida') THEN quantidade ELSE 0 END) as saidas,
                SUM(CASE
                    WHEN tipo IN ('estoque', 'recarga', 'resgate_entrada') THEN quantidade
                    WHEN tipo IN ('entrega', 'resgate_saida') THEN -quantidade
                    ELSE 0
                END) as saldo
            FROM movimentos
            GROUP BY driver, produto
            ORDER BY driver, produto
        """)

        # View: Produtos com saldo negativo (alertas)
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_produtos_negativos AS
            SELECT
                driver,
                produto,
                entradas,
                saidas,
                saldo
            FROM v_saldo_produto
            WHERE saldo < 0
            ORDER BY saldo ASC
        """)

        # View: Movimentos por dia
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_movimentos_dia AS
            SELECT
                data_movimento,
                tipo,
                driver,
                COUNT(*) as qtd_registros,
                SUM(quantidade) as total_unidades
            FROM movimentos
            GROUP BY data_movimento, tipo, driver
            ORDER BY data_movimento DESC, driver
        """)

        # View: Itens pendentes de revisão (ordenados por severidade)
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_review_pendentes AS
            SELECT
                id,
                tipo,
                driver,
                produto,
                quantidade,
                data_movimento,
                endereco,
                review_severity,
                review_category,
                review_issue,
                review_ai_notes,
                reviewed_at,
                arquivo_origem
            FROM movimentos
            WHERE review_status = 'pendente'
            ORDER BY
                CASE review_severity
                    WHEN 'critico' THEN 1
                    WHEN 'atencao' THEN 2
                    WHEN 'info' THEN 3
                    ELSE 4
                END,
                reviewed_at DESC
        """)

        # View: Estatísticas de revisão
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_review_stats AS
            SELECT
                review_status,
                review_severity,
                review_category,
                COUNT(*) as total,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
            FROM movimentos
            GROUP BY review_status, review_severity, review_category
            ORDER BY total DESC
        """)

    def _parse_date(self, date_str: str) -> str:
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

    def _arquivo_ja_importado(self, arquivo: str) -> bool:
        """Verifica se arquivo já foi importado"""
        result = self.conn.execute(
            "SELECT 1 FROM arquivos_importados WHERE arquivo = ?",
            [arquivo]
        ).fetchone()
        return result is not None

    def _marcar_importado(self, arquivo: str, tipo: str):
        """Marca arquivo como importado"""
        self.conn.execute(
            "INSERT OR REPLACE INTO arquivos_importados (arquivo, tipo) VALUES (?, ?)",
            [arquivo, tipo]
        )

    def sync_json(self, json_path: Path, force: bool = False) -> int:
        """
        Importa JSON para o banco
        Retorna quantidade de registros importados
        """
        arquivo = json_path.name

        if not force and self._arquivo_ja_importado(arquivo):
            return 0

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tipo = data.get("tipo", self._detectar_tipo(arquivo))
        items = data.get("items", [])

        if not items:
            return 0

        count = 0

        if tipo == "estoque":
            count = self._import_estoque(items, arquivo)
        elif tipo == "recarga":
            count = self._import_recarga(items, arquivo)
        elif tipo == "resgate":
            count = self._import_resgate(items, arquivo)
        elif tipo in ("entregas", None) and "items" in data:
            count = self._import_entregas(items, arquivo)

        if count > 0:
            self._marcar_importado(arquivo, tipo or "entregas")

        return count

    def _detectar_tipo(self, arquivo: str) -> str:
        """Detecta tipo pelo nome do arquivo"""
        arquivo_lower = arquivo.lower()
        if "estoque" in arquivo_lower:
            return "estoque"
        elif "recarga" in arquivo_lower or "retirada" in arquivo_lower:
            return "recarga"
        elif "resgate" in arquivo_lower:
            return "resgate"
        elif "entrega" in arquivo_lower:
            return "entregas"
        return None

    def _import_estoque(self, items: list, arquivo: str) -> int:
        """Importa registros de estoque"""
        count = 0
        for item in items:
            data = self._parse_date(item.get("data_registro"))
            if not data:
                continue
            self.conn.execute("""
                INSERT INTO movimentos (tipo, driver, produto, quantidade, data_movimento, arquivo_origem)
                VALUES ('estoque', ?, ?, ?, ?, ?)
            """, [
                item.get("driver"),
                item.get("produto"),
                item.get("quantidade"),
                data,
                arquivo
            ])
            count += 1
        return count

    def _import_recarga(self, items: list, arquivo: str) -> int:
        """Importa registros de recarga"""
        count = 0
        for item in items:
            data = self._parse_date(item.get("data_recarga"))
            if not data:
                continue
            self.conn.execute("""
                INSERT INTO movimentos (tipo, driver, produto, quantidade, data_movimento, observacao, arquivo_origem)
                VALUES ('recarga', ?, ?, ?, ?, ?, ?)
            """, [
                item.get("driver"),
                item.get("produto"),
                item.get("quantidade"),
                data,
                item.get("observacao"),
                arquivo
            ])
            count += 1
        return count

    def _import_resgate(self, items: list, arquivo: str) -> int:
        """Importa registros de resgate (gera 2 movimentos: saída e entrada)"""
        count = 0
        for item in items:
            data = self._parse_date(item.get("data_resgate"))
            if not data:
                continue

            # Movimento de saída (driver_origem perde)
            self.conn.execute("""
                INSERT INTO movimentos (tipo, driver, driver_destino, produto, quantidade, data_movimento, observacao, arquivo_origem)
                VALUES ('resgate_saida', ?, ?, ?, ?, ?, ?, ?)
            """, [
                item.get("driver_origem"),
                item.get("driver_destino"),
                item.get("produto"),
                item.get("quantidade"),
                data,
                item.get("motivo"),
                arquivo
            ])

            # Movimento de entrada (driver_destino ganha)
            self.conn.execute("""
                INSERT INTO movimentos (tipo, driver, driver_destino, produto, quantidade, data_movimento, observacao, arquivo_origem)
                VALUES ('resgate_entrada', ?, ?, ?, ?, ?, ?, ?)
            """, [
                item.get("driver_destino"),
                item.get("driver_origem"),
                item.get("produto"),
                item.get("quantidade"),
                data,
                item.get("motivo"),
                arquivo
            ])
            count += 2
        return count

    def _import_entregas(self, items: list, arquivo: str) -> int:
        """Importa registros de entregas"""
        count = 0
        for item in items:
            data = self._parse_date(item.get("data_entrega"))
            if not data:
                continue
            self.conn.execute("""
                INSERT INTO movimentos (tipo, driver, produto, quantidade, data_movimento, endereco, arquivo_origem)
                VALUES ('entrega', ?, ?, ?, ?, ?, ?)
            """, [
                item.get("driver"),
                item.get("produto"),
                item.get("quantidade"),
                data,
                item.get("endereco_1"),
                arquivo
            ])
            count += 1
        return count

    def sync_all(self, force: bool = False) -> dict:
        """
        Sincroniza todos os JSONs de output/
        Retorna resumo da importação
        """
        if not OUTPUT_PATH.exists():
            return {"error": "Pasta output/ não encontrada"}

        if force:
            # Limpa dados existentes
            self.conn.execute("DELETE FROM movimentos")
            self.conn.execute("DELETE FROM arquivos_importados")

        resultado = {
            "arquivos_processados": 0,
            "registros_importados": 0,
            "arquivos_ignorados": 0,
            "detalhes": []
        }

        for json_file in OUTPUT_PATH.glob("*.json"):
            count = self.sync_json(json_file, force=force)
            if count > 0:
                resultado["arquivos_processados"] += 1
                resultado["registros_importados"] += count
                resultado["detalhes"].append(f"{json_file.name}: {count} registros")
            else:
                resultado["arquivos_ignorados"] += 1

        return resultado

    def sync_aliases(self, aliases_path: Path = None):
        """Sincroniza aliases.json para o banco"""
        if aliases_path is None:
            aliases_path = Path(__file__).parent / "aliases.json"

        if not aliases_path.exists():
            return 0

        with open(aliases_path, "r", encoding="utf-8") as f:
            aliases = json.load(f)

        count = 0
        for item in aliases:
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO aliases (alias, canonical, reason)
                    VALUES (?, ?, ?)
                """, [
                    item.get("alias"),
                    item.get("canonical"),
                    item.get("reason")
                ])
                count += 1
            except:
                pass

        return count

    # ============ MÉTODOS DE CONSULTA ============

    def _fetchall_dict(self, query: str, params: list = None) -> list:
        """Executa query e retorna lista de dicts"""
        result = self.conn.execute(query, params or [])
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def saldo_driver(self, driver: str = None) -> list:
        """Retorna saldo por driver"""
        if driver:
            return self._fetchall_dict(
                "SELECT * FROM v_saldo_driver WHERE driver = ?", [driver]
            )
        return self._fetchall_dict("SELECT * FROM v_saldo_driver")

    def saldo_produto(self, driver: str = None, produto: str = None) -> list:
        """Retorna saldo por produto"""
        query = "SELECT * FROM v_saldo_produto WHERE 1=1"
        params = []

        if driver:
            query += " AND driver = ?"
            params.append(driver)
        if produto:
            query += " AND produto = ?"
            params.append(produto)

        return self._fetchall_dict(query, params)

    def produtos_negativos(self) -> list:
        """Retorna produtos com saldo negativo"""
        return self._fetchall_dict("SELECT * FROM v_produtos_negativos")

    def movimentos_dia(self, data: str = None) -> list:
        """Retorna movimentos por dia"""
        if data:
            data_fmt = self._parse_date(data)
            return self._fetchall_dict(
                "SELECT * FROM v_movimentos_dia WHERE data_movimento = ?", [data_fmt]
            )
        return self._fetchall_dict("SELECT * FROM v_movimentos_dia")

    def review_pendentes(self, driver: str = None, severity: str = None) -> list:
        """Retorna itens pendentes de revisão"""
        query = "SELECT * FROM v_review_pendentes WHERE 1=1"
        params = []

        if driver:
            query += " AND driver = ?"
            params.append(driver)
        if severity:
            query += " AND review_severity = ?"
            params.append(severity)

        return self._fetchall_dict(query, params)

    def review_stats(self) -> list:
        """Retorna estatísticas de revisão"""
        return self._fetchall_dict("SELECT * FROM v_review_stats")

    def query(self, sql: str) -> list:
        """Executa query SQL arbitrária"""
        return self._fetchall_dict(sql)

    def stats(self) -> dict:
        """Retorna estatísticas do banco"""
        total = self.conn.execute("SELECT COUNT(*) FROM movimentos").fetchone()[0]
        por_tipo = self._fetchall_dict("""
            SELECT tipo, COUNT(*) as qtd, SUM(quantidade) as total
            FROM movimentos GROUP BY tipo
        """)

        return {
            "total_registros": total,
            "por_tipo": por_tipo,
            "db_path": str(self.db_path)
        }

    def close(self):
        """Fecha conexão"""
        self.conn.close()


# CLI para testes rápidos
if __name__ == "__main__":
    import sys

    db = GrowBotDB()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "sync":
            force = "--force" in sys.argv
            result = db.sync_all(force=force)
            print(f"Sincronização concluída:")
            print(f"  Arquivos processados: {result['arquivos_processados']}")
            print(f"  Registros importados: {result['registros_importados']}")
            print(f"  Arquivos ignorados: {result['arquivos_ignorados']}")
            if result['detalhes']:
                print("\nDetalhes:")
                for d in result['detalhes']:
                    print(f"  - {d}")

        elif cmd == "saldo":
            driver = sys.argv[2] if len(sys.argv) > 2 else None
            for row in db.saldo_driver(driver):
                print(f"{row['driver']}: estoque={row['estoque']} recargas={row['recargas']} saidas={row['saidas']} saldo={row['saldo']}")

        elif cmd == "negativos":
            negs = db.produtos_negativos()
            if negs:
                print("Produtos com saldo negativo:")
                for row in negs:
                    print(f"  {row['driver']} - {row['produto']}: {row['saldo']}")
            else:
                print("Nenhum produto com saldo negativo!")

        elif cmd == "stats":
            stats = db.stats()
            print(f"Total de registros: {stats['total_registros']}")
            print(f"DB: {stats['db_path']}")
            print("\nPor tipo:")
            for t in stats['por_tipo']:
                print(f"  {t['tipo']}: {t['qtd']} registros, {t['total']} unidades")

        elif cmd == "query":
            sql = " ".join(sys.argv[2:])
            result = db.query(sql)
            for row in result:
                print(row)

        elif cmd == "review-pendentes":
            driver = sys.argv[2] if len(sys.argv) > 2 else None
            pendentes = db.review_pendentes(driver=driver)
            if pendentes:
                print(f"Itens pendentes de revisão ({len(pendentes)}):")
                for row in pendentes:
                    sev = row.get('review_severity', '-')
                    cat = row.get('review_category', '-')
                    issue = row.get('review_issue', '-')
                    print(f"  [{sev}|{cat}] {row['driver']} - {row['produto']} x{row['quantidade']}")
                    if issue:
                        print(f"           Issue: {issue}")
            else:
                print("Nenhum item pendente de revisão!")

        elif cmd == "review-stats":
            stats = db.review_stats()
            if stats:
                print("Estatísticas de revisão:")
                for row in stats:
                    status = row.get('review_status') or 'NULL'
                    severity = row.get('review_severity') or '-'
                    category = row.get('review_category') or '-'
                    print(f"  {status:12} | {severity:8} | {category:8} | {row['total']:5} ({row['percentual']}%)")
            else:
                print("Nenhuma estatística de revisão disponível")

        else:
            print("Comandos: sync [--force], saldo [DRIVER], negativos, stats, review-pendentes, review-stats, query <SQL>")

    else:
        print("GrowBot DB - Comandos disponíveis:")
        print("  python db.py sync [--force]     - Sincroniza JSONs")
        print("  python db.py saldo [DRIVER]     - Mostra saldo")
        print("  python db.py negativos          - Mostra alertas")
        print("  python db.py stats              - Estatísticas")
        print("  python db.py review-pendentes   - Itens pendentes de revisão")
        print("  python db.py review-stats       - Estatísticas de revisão")
        print("  python db.py query <SQL>        - Query livre")

    db.close()
