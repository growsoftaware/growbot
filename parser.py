#!/usr/bin/env python3
"""
Parser determinístico para exports do WhatsApp.
Separa blocos de entrega pelo marcador 🏎️ e detecta sessões (driver/data).
Gera logs de import com issues encontrados.
"""

import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime, timedelta


DRIVERS = {"RAFA", "FRANCIS", "RODRIGO", "KAROL", "ARTHUR"}
DIAS_SEMANA = {
    "segunda": 0, "terça": 1, "terca": 1, "quarta": 2,
    "quinta": 3, "sexta": 4, "sábado": 5, "sabado": 5, "sabada": 5, "domingo": 6
}


@dataclass
class Issue:
    block_id: str
    line_number: int
    issue_type: str  # missing_date, missing_driver, ambiguous, parse_error
    severity: str    # critical, warning, info
    description: str
    fallback_used: Optional[str] = None
    needs_review: bool = False


@dataclass
class Bloco:
    id_entrega: str
    texto: str
    linha_inicio: int = 0
    driver: Optional[str] = None
    data_entrega: Optional[str] = None
    data_timestamp: Optional[str] = None  # fallback do timestamp
    issues: List[Issue] = field(default_factory=list)
    # Campos de review (compatíveis com db.py)
    review_status: str = "ok"  # ok, pendente, ignorado
    review_severity: Optional[str] = None  # critico, atencao, info
    review_category: Optional[str] = None  # tecnico, negocio
    review_issue: Optional[str] = None
    review_ai_notes: Optional[str] = None


@dataclass
class Sessao:
    blocos: list = field(default_factory=list)
    driver: Optional[str] = None
    data_entrega: Optional[str] = None
    data_base: Optional[datetime] = None


@dataclass
class ImportLog:
    import_id: str
    import_type: str
    source_file: str
    date_import: str
    driver: str
    total_blocks: int
    blocks_ok: int
    blocks_with_issues: int
    issues: List[dict] = field(default_factory=list)
    comments: str = ""


def limpar_linha(linha: str) -> str:
    """Remove caracteres invisíveis e normaliza quebras de linha."""
    # Remove Left-to-Right Mark, Right-to-Left Mark, Zero Width chars
    linha = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\ufeff]', '', linha)
    # Normaliza quebras de linha
    linha = linha.replace('\r\n', '\n').replace('\r', '\n')
    return linha


def extrair_id_entrega(linha: str) -> Optional[str]:
    """Extrai número do marcador 🏎️N e retorna como 3 dígitos."""
    linha = limpar_linha(linha)
    match = re.search(r'(\d+)\s*🏎️|🏎️\s*(\d+)', linha)
    if match:
        num = match.group(1) or match.group(2)
        return num.zfill(3)
    return None


def extrair_timestamp(linha: str) -> Optional[datetime]:
    """Extrai timestamp de linha - suporta múltiplos formatos."""
    linha = limpar_linha(linha)
    # Formato [DD/MM/YY, HH:MM:SS]
    match = re.match(r'\[(\d{2}/\d{2}/\d{2}), (\d{2}:\d{2}:\d{2})\]', linha)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)} {match.group(2)}", "%d/%m/%y %H:%M:%S")
        except ValueError:
            pass

    # Formato [YYYY-MM-DD, H:MM:SS PM/AM] (com possível narrow no-break space \u202f)
    match = re.match(r'\[(\d{4}-\d{2}-\d{2}), (\d{1,2}:\d{2}:\d{2})[\s\u202f]+([AP]M)\]', linha)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)} {match.group(2)} {match.group(3)}", "%Y-%m-%d %I:%M:%S %p")
        except ValueError:
            pass

    return None


def detectar_driver(texto: str) -> Optional[str]:
    """Detecta driver no texto (palavra exata, não parte de outra)."""
    texto_upper = texto.upper()
    for driver in DRIVERS:
        if re.search(rf'\b{driver}\b', texto_upper):
            return driver
    return None


def calcular_data_por_dia_semana(dia_semana: str, data_base: datetime) -> str:
    """Calcula a data do dia da semana mencionado, sempre no passado relativo ao timestamp."""
    dia_semana = dia_semana.lower()
    if dia_semana not in DIAS_SEMANA:
        return None

    target_weekday = DIAS_SEMANA[dia_semana]
    current_weekday = data_base.weekday()

    diff = target_weekday - current_weekday
    if diff > 0:
        diff -= 7

    data_alvo = data_base + timedelta(days=diff)
    return data_alvo.strftime("%d/%m/%Y")


def detectar_data(texto: str, data_base: datetime = None) -> Optional[str]:
    """Detecta data no texto."""
    # Formato DD/MM/YYYY ou DD/MM/YY
    match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', texto)
    if match:
        dia, mes = int(match.group(1)), int(match.group(2))
        ano_str = match.group(3)

        if ano_str:
            # Ano explícito
            ano = int(ano_str)
            if ano < 100:
                ano = 2000 + ano
        else:
            # Ano não especificado - inferir do timestamp
            ano = data_base.year if data_base else 2025

            # Se a data seria no futuro relativo ao timestamp, usar ano anterior
            # Ex: timestamp 01/01/2026, texto "31/12" -> deve ser 31/12/2025
            if data_base:
                try:
                    data_mencionada = datetime(ano, mes, dia)
                    if data_mencionada > data_base:
                        ano -= 1
                except ValueError:
                    pass  # Data inválida, manter ano original

        return f"{str(dia).zfill(2)}/{str(mes).zfill(2)}/{ano}"

    # Formato "DD do MM"
    match = re.search(r'(\d{1,2})\s+do\s+(\d{1,2})', texto)
    if match:
        dia, mes = int(match.group(1)), int(match.group(2))
        ano = data_base.year if data_base else 2025

        # Mesma lógica: se seria futuro, usar ano anterior
        if data_base:
            try:
                data_mencionada = datetime(ano, mes, dia)
                if data_mencionada > data_base:
                    ano -= 1
            except ValueError:
                pass

        return f"{str(dia).zfill(2)}/{str(mes).zfill(2)}/{ano}"

    # Dia da semana
    if data_base:
        texto_lower = texto.lower()
        for dia in DIAS_SEMANA.keys():
            if dia in texto_lower:
                return calcular_data_por_dia_semana(dia, data_base)

    return None


def eh_linha_ignoravel(linha: str) -> bool:
    """Verifica se linha deve ser ignorada."""
    ignorar = [
        "sticker omitted", "mídia oculta", "media omitted",
        "document omitted", "image omitted", "video omitted",
        "message was deleted", "this message was edited",
        "salve", "opa", "blz", "ok", "👍", "kk", "show"
    ]
    linha_lower = linha.lower()

    for termo in ignorar:
        if termo in linha_lower:
            return True

    texto_limpo = re.sub(r'\[.*?\].*?:', '', linha).strip()
    if len(texto_limpo) < 3 and '🏎️' not in linha:
        return True

    return False


def eh_rodape(linha: str, proximas_linhas: list) -> bool:
    """Verifica se linha é rodapé (driver/data no final de sessão)."""
    texto = re.sub(r'\[.*?\].*?:', '', linha).strip()

    # Ignora linhas muito longas (provavelmente conteúdo)
    if len(texto) > 50:
        return False

    # Detecta driver
    if detectar_driver(texto):
        return True

    # Detecta padrões de rodapé: "Essas foram", "Esses do", etc
    rodape_patterns = [
        r'ess[ae]s?\s+(foram|do|da|de)',
        r'saídas?\s+\w+',
        r'saidas?\s+\w+',
    ]
    texto_lower = texto.lower()
    for pattern in rodape_patterns:
        if re.search(pattern, texto_lower):
            return True

    # Detecta dia da semana isolado
    for dia in DIAS_SEMANA.keys():
        if dia in texto_lower and len(texto) < 30:
            return True

    # Detecta data numérica DD/MM isolada
    if re.match(r'^\d{1,2}/\d{1,2}', texto) and len(texto) < 30:
        return True

    # Detecta formato "DD do MM"
    if re.search(r'\d{1,2}\s+do\s+\d{1,2}', texto) and len(texto) < 30:
        return True

    return False


def buscar_rodape_multilinhas(linhas: list, inicio: int, max_linhas: int = 5) -> tuple:
    """Busca driver e data em múltiplas linhas consecutivas de rodapé."""
    driver = None
    data = None
    data_base = None

    # Pegar data_base do contexto
    for j in range(max(0, inicio-10), inicio):
        ts = extrair_timestamp(linhas[j])
        if ts:
            data_base = ts

    for j in range(inicio, min(inicio + max_linhas, len(linhas))):
        linha = linhas[j]
        texto = re.sub(r'\[.*?\].*?:', '', linha).strip()

        # Para se encontrar novo bloco de entrega
        if extrair_id_entrega(linha):
            break

        if not driver:
            driver = detectar_driver(texto)
        if not data:
            data = detectar_data(texto, data_base)

        # Se encontrou ambos, retorna
        if driver and data:
            break

    return driver, data


def parsear_arquivo(caminho: str, gerar_log: bool = True) -> tuple:
    """Lê arquivo e retorna lista de blocos com driver/data e log de issues."""
    with open(caminho, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    issues = []

    # Primeira passada: detectar timestamps pra ter data base
    data_base = None
    for linha in linhas:
        ts = extrair_timestamp(linha)
        if ts:
            data_base = ts
            break

    # Segunda passada: separar em sessões e blocos
    sessoes = []
    sessao_atual = Sessao(data_base=data_base)
    bloco_atual = []
    bloco_linha_inicio = 0
    bloco_timestamp = None

    i = 0
    while i < len(linhas):
        linha = linhas[i]

        # Atualiza timestamp do bloco atual
        ts = extrair_timestamp(linha)
        if ts:
            if not bloco_timestamp:
                bloco_timestamp = ts
            sessao_atual.data_base = ts

        # Verifica se é rodapé (driver/data)
        proximas = linhas[i+1:i+5] if i+1 < len(linhas) else []
        if eh_rodape(linha, proximas):
            # Busca driver/data em múltiplas linhas
            driver, data = buscar_rodape_multilinhas(linhas, i)

            if driver:
                sessao_atual.driver = driver
            if data:
                sessao_atual.data_entrega = data

            # Avança até sair do rodapé
            j = i + 1
            while j < len(linhas) and j < i + 5:
                if extrair_id_entrega(linhas[j]):
                    break
                if eh_rodape(linhas[j], []):
                    j += 1
                else:
                    break
            i = j

            # Fecha sessão se já tem blocos
            if sessao_atual.blocos:
                sessoes.append(sessao_atual)
                sessao_atual = Sessao(data_base=data_base)

            continue

        # Ignora linhas sem conteúdo útil
        if eh_linha_ignoravel(linha):
            i += 1
            continue

        # Marca início do bloco
        if not bloco_atual:
            bloco_linha_inicio = i + 1
            if ts:
                bloco_timestamp = ts

        # Adiciona linha ao bloco atual
        bloco_atual.append(linha)

        # Verifica se fecha bloco (tem 🏎️)
        id_entrega = extrair_id_entrega(linha)
        if id_entrega:
            bloco = Bloco(
                id_entrega=id_entrega,
                texto=''.join(bloco_atual),
                linha_inicio=bloco_linha_inicio,
                data_timestamp=bloco_timestamp.strftime("%d/%m/%Y") if bloco_timestamp else None
            )
            sessao_atual.blocos.append(bloco)
            bloco_atual = []
            bloco_timestamp = None

        i += 1

    # Fecha última sessão
    if sessao_atual.blocos:
        sessoes.append(sessao_atual)

    # Aplica driver/data a todos os blocos de cada sessão
    todos_blocos = []
    for sessao in sessoes:
        for bloco in sessao.blocos:
            bloco.driver = sessao.driver
            bloco.data_entrega = sessao.data_entrega

            # Fallback: usa data do timestamp se não tem data do rodapé
            if not bloco.data_entrega and bloco.data_timestamp:
                bloco.data_entrega = bloco.data_timestamp
                issue = Issue(
                    block_id=bloco.id_entrega,
                    line_number=bloco.linha_inicio,
                    issue_type="missing_date",
                    severity="warning",
                    description="Data não encontrada no rodapé, usando timestamp",
                    fallback_used=f"{bloco.data_timestamp} (timestamp)",
                    needs_review=False
                )
                bloco.issues.append(issue)
                issues.append(issue)

            # Issue: sem driver
            if not bloco.driver:
                issue = Issue(
                    block_id=bloco.id_entrega,
                    line_number=bloco.linha_inicio,
                    issue_type="missing_driver",
                    severity="critical",
                    description="Driver não identificado",
                    needs_review=True
                )
                bloco.issues.append(issue)
                issues.append(issue)

            # Issue: sem data nenhuma
            if not bloco.data_entrega:
                issue = Issue(
                    block_id=bloco.id_entrega,
                    line_number=bloco.linha_inicio,
                    issue_type="missing_date",
                    severity="critical",
                    description="Data não encontrada (nem rodapé, nem timestamp)",
                    needs_review=True
                )
                bloco.issues.append(issue)
                issues.append(issue)

            # Preenche campos de review baseado nos issues
            if bloco.issues:
                # Pega o issue mais severo
                severities = {"critical": 3, "warning": 2, "info": 1}
                worst_issue = max(bloco.issues, key=lambda i: severities.get(i.severity, 0))

                bloco.review_status = "pendente" if worst_issue.needs_review else "ok"
                bloco.review_severity = worst_issue.severity
                bloco.review_category = "tecnico"  # issues de parse são técnicos
                bloco.review_issue = worst_issue.description
                bloco.review_ai_notes = worst_issue.fallback_used

            todos_blocos.append(bloco)

    # Gerar log de import
    log = None
    if gerar_log:
        drivers = set(b.driver for b in todos_blocos if b.driver)
        driver_str = list(drivers)[0] if len(drivers) == 1 else "MISTO"

        blocks_ok = len([b for b in todos_blocos if not b.issues])
        blocks_with_issues = len([b for b in todos_blocos if b.issues])

        log = ImportLog(
            import_id=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(caminho).stem}",
            import_type="entregas",
            source_file=caminho,
            date_import=datetime.now().isoformat(),
            driver=driver_str,
            total_blocks=len(todos_blocos),
            blocks_ok=blocks_ok,
            blocks_with_issues=blocks_with_issues,
            issues=[asdict(i) for i in issues],
            comments=""
        )

    return todos_blocos, log


def salvar_log(log: ImportLog, pasta: str = "imports/logs"):
    """Salva log de import em arquivo JSON."""
    Path(pasta).mkdir(parents=True, exist_ok=True)
    arquivo = Path(pasta) / f"{log.import_id}.json"
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(asdict(log), f, ensure_ascii=False, indent=2)
    return arquivo


def exportar_json(blocos: List[Bloco], arquivo: str = "imports/parsed/blocos.json"):
    """Exporta blocos para JSON no formato compatível com entregas_validadas.json"""
    Path(arquivo).parent.mkdir(parents=True, exist_ok=True)

    items = []
    for bloco in blocos:
        item = {
            "id_sale_delivery": bloco.id_entrega,
            "texto_raw": bloco.texto.strip(),
            "driver": bloco.driver,
            "data_entrega": bloco.data_entrega,
            "linha_origem": bloco.linha_inicio,
            "review_status": bloco.review_status,
            "review_severity": bloco.review_severity,
            "review_category": bloco.review_category,
            "review_issue": bloco.review_issue,
            "review_ai_notes": bloco.review_ai_notes
        }
        items.append(item)

    output = {
        "tipo": "blocos_parseados",
        "date_export": datetime.now().isoformat(),
        "total": len(items),
        "items": items
    }

    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return arquivo


def main():
    if len(sys.argv) < 2:
        print("Uso: python parser.py <arquivo.txt>")
        print("Exemplo: python parser.py exports/conversa.txt")
        sys.exit(1)

    caminho = sys.argv[1]
    if not Path(caminho).exists():
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)

    blocos, log = parsear_arquivo(caminho)

    print(f"Encontrados {len(blocos)} blocos de entrega:\n")
    print(f"  ✅ OK: {log.blocks_ok}")
    print(f"  ⚠️  Com issues: {log.blocks_with_issues}")
    print()

    # Resumo por driver/data
    from collections import Counter
    combos = Counter((b.driver or "SEM_DRIVER", b.data_entrega or "SEM_DATA") for b in blocos)
    print("Resumo por driver/data:")
    for (driver, data), count in sorted(combos.items()):
        print(f"  {driver} {data}: {count}")

    print()

    # Mostrar primeiros blocos
    for i, bloco in enumerate(blocos[:5], 1):
        print(f"{'='*50}")
        status = "⚠️" if bloco.issues else "✅"
        print(f"{status} BLOCO {i} | ID: {bloco.id_entrega} | Driver: {bloco.driver} | Data: {bloco.data_entrega}")
        if bloco.issues:
            for issue in bloco.issues:
                print(f"   └─ {issue.severity}: {issue.description}")
        print(f"{'='*50}")
        print(bloco.texto[:200])
        print()

    if len(blocos) > 5:
        print(f"... e mais {len(blocos) - 5} blocos")

    # Salvar log
    arquivo_log = salvar_log(log)
    print(f"\n📋 Log salvo em: {arquivo_log}")


if __name__ == "__main__":
    main()
