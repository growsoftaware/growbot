#!/usr/bin/env python3
"""
GrowBot Telegram - v1.1
Modos de processamento: 1por1 ou Auto (só dúvidas).
"""

import os
import re
import io
import json
import zipfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# Importar módulos do projeto
import sys
sys.path.insert(0, str(Path(__file__).parent))
from db import GrowBotDB
from parser import parsear_arquivo, Bloco

# Carregar variáveis de ambiente
load_dotenv()

# Configuração
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USERS = [
    int(uid.strip())
    for uid in os.getenv("TELEGRAM_AUTHORIZED_USERS", "").split(",")
    if uid.strip()
]
EXPORTS_DIR = Path(__file__).parent / "exports"
ALIASES_PATH = Path(__file__).parent / "aliases.json"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Drivers válidos
DRIVERS = {"RAFA", "FRANCIS", "RODRIGO", "KAROL", "ARTHUR"}

# Estados do processamento
user_states: Dict[int, dict] = {}


def load_aliases() -> Dict[str, str]:
    """Carrega aliases de produtos."""
    if not ALIASES_PATH.exists():
        return {}
    with open(ALIASES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['alias'].lower(): item['canonical'].lower() for item in data}

ALIASES = load_aliases()


@dataclass
class ParsedItem:
    """Item parseado de um bloco."""
    produto: str
    quantidade: int
    raw_match: str  # texto original que gerou o match


@dataclass
class ParsedBlock:
    """Bloco parseado."""
    id_entrega: str
    texto_raw: str
    items: List[ParsedItem]
    endereco: Optional[str] = None
    linha_inicio: int = 0
    ambiguidades: List[str] = field(default_factory=list)


@dataclass
class SessionState:
    """Estado de processamento de uma sessão."""
    driver: str
    data: str
    blocks: List[ParsedBlock]
    current_idx: int = 0
    processed: List[dict] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    filepath: Path = None


@dataclass
class FileAnalysis:
    """Resultado da análise de um arquivo."""
    filepath: Path
    tipo: str
    sessions: list = field(default_factory=list)
    new_sessions: list = field(default_factory=list)
    existing_sessions: list = field(default_factory=list)
    total_lines: int = 0
    raw_content: str = ""
    saved_filename: str = ""


def normalize_product(name: str) -> str:
    """Normaliza nome de produto usando aliases."""
    name_lower = name.lower().strip()
    return ALIASES.get(name_lower, name_lower)


def parse_quantity(text: str) -> Tuple[int, str]:
    """
    Extrai quantidade do texto.
    Retorna (quantidade, produto_restante).
    """
    text = text.strip()

    # Padrão: "Xg produto" ou "X g produto"
    match = re.match(r'^(\d+)\s*g\s+(.+)$', text, re.IGNORECASE)
    if match:
        return int(match.group(1)), match.group(2).strip()

    # Padrão: "X produto"
    match = re.match(r'^(\d+)\s+(.+)$', text)
    if match:
        return int(match.group(1)), match.group(2).strip()

    # Padrão: "produto X"
    match = re.match(r'^(.+?)\s+(\d+)$', text)
    if match:
        return int(match.group(2)), match.group(1).strip()

    # Padrão: "produto Xg"
    match = re.match(r'^(.+?)\s+(\d+)\s*g$', text, re.IGNORECASE)
    if match:
        return int(match.group(2)), match.group(1).strip()

    # Sem quantidade explícita = 1
    return 1, text


def extract_items_from_text(text: str) -> List[ParsedItem]:
    """Extrai itens (produto + quantidade) de um texto."""
    items = []

    # Limpar texto
    lines = text.split('\n')

    for line in lines:
        # Ignorar linhas de sistema
        if any(x in line.lower() for x in ['omitted', 'edited', 'deleted', 'joined', 'created']):
            continue

        # Remover timestamp [YYYY-MM-DD, HH:MM:SS]
        line = re.sub(r'\[\d{4}-\d{2}-\d{2},?\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\]', '', line)
        line = re.sub(r'\[\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\]', '', line)

        # Remover nome do remetente (Akita:, etc)
        line = re.sub(r'^[^:]+:\s*', '', line)

        # Remover emoji de carro (marcador de bloco)
        line = re.sub(r'🏎️\d*|\d*🏎️|🚗\d*|\d*🚗', '', line)

        line = line.strip()
        if not line:
            continue

        # Tentar extrair "X produto e Y produto"
        if ' e ' in line.lower():
            parts = re.split(r'\s+e\s+', line, flags=re.IGNORECASE)
            for part in parts:
                part = part.strip()
                if part:
                    qty, prod = parse_quantity(part)
                    prod_norm = normalize_product(prod)
                    if prod_norm and len(prod_norm) > 1:
                        items.append(ParsedItem(prod_norm, qty, part))
        else:
            # Item único
            qty, prod = parse_quantity(line)
            prod_norm = normalize_product(prod)
            if prod_norm and len(prod_norm) > 1:
                items.append(ParsedItem(prod_norm, qty, line))

    return items


def extract_address(text: str) -> Optional[str]:
    """Tenta extrair endereço do texto."""
    # Padrões comuns de endereço
    patterns = [
        r'(?:rua|av|avenida|alameda|travessa)\s+[^\n]+',
        r'(?:bairro|centro|vila)\s+[^\n]+',
        r'\d{5}-?\d{3}',  # CEP
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return None


def parse_blocks_from_content(content: str, driver: str, data: str) -> List[ParsedBlock]:
    """Parseia blocos de um conteúdo de arquivo."""
    blocks = []
    lines = content.split('\n')

    current_block_lines = []
    current_block_start = 0

    for i, line in enumerate(lines):
        # Detectar marcador de bloco 🏎️N ou N🏎️
        block_match = re.search(r'(\d+)?🏎️(\d+)?|(\d+)?🚗(\d+)?', line)

        if block_match:
            # Extrair ID do bloco
            nums = [g for g in block_match.groups() if g]
            block_id = nums[0] if nums else str(len(blocks) + 1)
            block_id = block_id.zfill(3)

            # Incluir a linha atual no bloco
            current_block_lines.append(line)

            # Processar bloco acumulado
            if current_block_lines:
                texto_raw = '\n'.join(current_block_lines)
                items = extract_items_from_text(texto_raw)
                endereco = extract_address(texto_raw)

                if items:  # Só adiciona se tiver itens
                    blocks.append(ParsedBlock(
                        id_entrega=block_id,
                        texto_raw=texto_raw,
                        items=items,
                        endereco=endereco,
                        linha_inicio=current_block_start
                    ))

            # Reset para próximo bloco
            current_block_lines = []
            current_block_start = i + 1
        else:
            if not current_block_lines:
                current_block_start = i
            current_block_lines.append(line)

    return blocks


# ============ FUNÇÕES DE AUTORIZAÇÃO ============

def is_authorized(user_id: int) -> bool:
    if not AUTHORIZED_USERS:
        return True
    return user_id in AUTHORIZED_USERS


# ============ FUNÇÕES DE ARQUIVO ============

def detect_file_type(content: str) -> str:
    if "Abastecimento drivers" in content or "Retiradas / Recargas" in content:
        return "recargas"
    elif "🏎️" in content or "🚗" in content:
        return "saidas"
    elif "estoque" in content.lower():
        return "estoque"
    return "desconhecido"


def generate_filename(tipo: str, original_name: str = "") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = original_name.replace(".txt", "").replace(" ", "_") if original_name else ""
    return f"telegram_{timestamp}_{tipo}_{clean_name}.txt"


def extract_txt_from_zip(zip_bytes: bytes) -> List[tuple]:
    txt_files = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            for name in zf.namelist():
                if name.endswith('/') or name.startswith('__') or '/.' in name:
                    continue
                if name.lower().endswith('.txt'):
                    try:
                        content = zf.read(name).decode('utf-8')
                        filename = Path(name).name
                        txt_files.append((filename, content))
                    except Exception as e:
                        logger.warning(f"Erro ao ler {name} do ZIP: {e}")
    except Exception as e:
        logger.error(f"Erro ao abrir ZIP: {e}")
    return txt_files


# ============ ANÁLISE DE SESSÕES ============

def parse_date_from_text(text: str, ref_date: datetime = None) -> Optional[str]:
    match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', text)
    if match:
        day, month, year = match.groups()
        if not year:
            year = str(ref_date.year if ref_date else datetime.now().year)
        elif len(year) == 2:
            year = "20" + year
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    match = re.search(r'(\d{1,2})\s+(?:do|de)\s+(\d{1,2})', text, re.IGNORECASE)
    if match:
        day, month = match.groups()
        year = str(ref_date.year if ref_date else datetime.now().year)
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    dias = {
        'segunda': 0, 'terça': 1, 'terca': 1, 'quarta': 2,
        'quinta': 3, 'sexta': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
    }
    for dia, weekday in dias.items():
        if dia in text.lower():
            if ref_date:
                diff = (ref_date.weekday() - weekday) % 7
                if diff == 0:
                    diff = 7
                target = ref_date - timedelta(days=diff)
                return target.strftime("%d/%m/%Y")
    return None


def detect_driver(text: str) -> Optional[str]:
    text_upper = text.upper()
    for driver in DRIVERS:
        if re.search(r'\b' + driver + r'\b', text_upper):
            return driver
    return None


def analyze_saidas_file(content: str) -> list:
    """Retorna: [(driver, data, num_blocos, linha_inicio, linha_fim, content_slice)]"""
    lines = content.split('\n')
    sessions = []

    current_driver = None
    current_date = None
    current_blocks = 0
    session_start = 0
    last_timestamp = None

    for i, line in enumerate(lines):
        ts_match = re.search(r'\[(\d{4}-\d{2}-\d{2})', line)
        if ts_match:
            try:
                last_timestamp = datetime.strptime(ts_match.group(1), "%Y-%m-%d")
            except:
                pass

        if '🏎️' in line or '🚗' in line:
            current_blocks += 1

        driver_found = detect_driver(line)
        date_found = parse_date_from_text(line, last_timestamp)

        is_footer = driver_found and (date_found or any(d in line.lower() for d in
            ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']))

        if is_footer:
            if not date_found:
                date_found = parse_date_from_text(line, last_timestamp)

            if current_driver and current_blocks > 0:
                content_slice = '\n'.join(lines[session_start:i])
                sessions.append((current_driver, current_date, current_blocks, session_start, i-1, content_slice))

            current_driver = driver_found
            current_date = date_found
            current_blocks = 0
            session_start = i + 1

    if current_driver and current_blocks > 0:
        content_slice = '\n'.join(lines[session_start:])
        sessions.append((current_driver, current_date, current_blocks, session_start, len(lines), content_slice))

    return sessions


def get_existing_data_from_db() -> dict:
    try:
        db = GrowBotDB(read_only=True)
        result = db.query("""
            SELECT driver, data_movimento, COUNT(*) as qtd
            FROM movimentos WHERE tipo IN ('entrega', 'recarga')
            GROUP BY driver, data_movimento
        """)
        db.close()

        existing = {}
        for row in result:
            data = row['data_movimento']
            data_str = data.strftime("%d/%m/%Y") if hasattr(data, 'strftime') else str(data)
            existing[(row['driver'], data_str)] = row['qtd']
        return existing
    except Exception as e:
        logger.error(f"Erro ao consultar DB: {e}")
        return {}


def analyze_file(filepath: Path, content: str) -> FileAnalysis:
    tipo = detect_file_type(content)
    analysis = FileAnalysis(
        filepath=filepath,
        tipo=tipo,
        total_lines=len(content.split('\n')),
        raw_content=content
    )

    if tipo == "saidas":
        sessions = analyze_saidas_file(content)
    else:
        return analysis

    analysis.sessions = sessions
    existing = get_existing_data_from_db()

    for session in sessions:
        driver, data, count, start, end, content_slice = session
        key = (driver, data)
        if key in existing:
            analysis.existing_sessions.append((driver, data, count, existing[key]))
        else:
            analysis.new_sessions.append((driver, data, count, start, end, content_slice))

    return analysis


# ============ HANDLERS DE COMANDO ============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text(f"Acesso negado.\nSeu ID: `{user.id}`", parse_mode="Markdown")
        return

    await update.message.reply_text(
        f"Olá {user.first_name}!\n\n"
        "Envie um arquivo .txt ou .zip de export do WhatsApp.\n\n"
        "Vou analisar, mostrar o que é novo, e processar bloco a bloco.\n\n"
        "Comandos:\n"
        "/status - Arquivos salvos\n"
        "/saldo - Saldo por driver\n"
        "/cancelar - Cancelar processamento",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Comandos:*\n\n"
        "/start - Iniciar\n"
        "/status - Arquivos salvos\n"
        "/saldo - Saldo por driver\n"
        "/cancelar - Cancelar processamento\n\n"
        "*Como usar:*\n"
        "1. Envie .txt ou .zip\n"
        "2. Confirme sessões a processar\n"
        "3. Valide cada bloco",
        parse_mode="Markdown"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    telegram_files = sorted(EXPORTS_DIR.glob("telegram_*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]

    if not telegram_files:
        await update.message.reply_text("Nenhum arquivo salvo ainda.")
        return

    lines = ["*Últimos arquivos:*\n"]
    for f in telegram_files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        size_kb = f.stat().st_size / 1024
        lines.append(f"• `{f.name}`\n  {size_kb:.1f}KB - {mtime:%d/%m %H:%M}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    try:
        db = GrowBotDB(read_only=True)
        driver_filter = context.args[0].upper() if context.args else None
        saldos = db.saldo_driver(driver_filter)
        db.close()

        if not saldos:
            await update.message.reply_text("Nenhum dado encontrado.")
            return

        lines = ["*Saldo por Driver:*\n```"]
        lines.append(f"{'Driver':<10} {'Est':>5} {'Rec':>5} {'Saí':>5} {'Saldo':>6}")
        lines.append("-" * 35)
        for s in saldos:
            lines.append(f"{s['driver']:<10} {s['estoque']:>5} {s['recargas']:>5} {s['saidas']:>5} {s['saldo']:>6}")
        lines.append("```")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")


async def cancelar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
        await update.message.reply_text("Processamento cancelado.")
    else:
        await update.message.reply_text("Nenhum processamento em andamento.")


# ============ HANDLER DE DOCUMENTO ============

def count_blocks_in_content(content: str) -> int:
    """Conta quantos blocos (🏎️) existem no conteúdo."""
    return len(re.findall(r'🏎️|🚗', content))


def format_date_short(date_str: str) -> str:
    """
    Converte 'DD/MM/YYYY' para 'DD-Mmm (Ddd)'.
    Ex: '02/01/2026' -> '02-Jan (Qui)'
    """
    MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

    try:
        parts = date_str.split('/')
        dia = int(parts[0])
        mes = int(parts[1])
        ano = int(parts[2])

        dt = datetime(ano, mes, dia)
        dia_semana = DIAS[dt.weekday()]
        mes_nome = MESES[mes - 1]

        return f"{dia:02d}-{mes_nome} ({dia_semana})"
    except:
        return date_str  # Fallback para formato original


def analyze_file_sessions_from_path(filepath: Path) -> Dict[str, Dict[str, int]]:
    """
    Analisa arquivo usando o parser real e retorna sessões por driver/data.
    Retorna: {driver: {data: num_blocos}}
    """
    try:
        blocos, log = parsear_arquivo(str(filepath), gerar_log=False)

        sessions = {}  # {driver: {data: count}}

        for bloco in blocos:
            driver = bloco.driver
            data = bloco.data_entrega

            if not driver or not data:
                continue

            if driver not in sessions:
                sessions[driver] = {}

            sessions[driver][data] = sessions[driver].get(data, 0) + 1

        return sessions
    except Exception as e:
        logger.error(f"Erro ao parsear arquivo: {e}")
        return {}


def get_existing_sessions_from_db() -> Dict[str, set]:
    """
    Retorna sessões existentes no banco.
    Retorna: {driver: {data1, data2, ...}}
    """
    try:
        db = GrowBotDB(read_only=True)
        result = db.query("""
            SELECT DISTINCT driver, data_movimento
            FROM movimentos
            WHERE tipo = 'entrega'
        """)
        db.close()

        existing = {}
        for row in result:
            driver = row['driver']
            data = row['data_movimento']
            data_str = data.strftime("%d/%m/%Y") if hasattr(data, 'strftime') else str(data)

            if driver not in existing:
                existing[driver] = set()
            existing[driver].add(data_str)

        return existing
    except Exception as e:
        logger.error(f"Erro ao consultar DB: {e}")
        return {}


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text(f"Acesso negado.\nSeu ID: `{user.id}`", parse_mode="Markdown")
        return

    document = update.message.document
    filename = document.file_name.lower()

    if not (filename.endswith(".txt") or filename.endswith(".zip")):
        await update.message.reply_text(f"Envie .txt ou .zip\nRecebido: {document.file_name}")
        return

    await update.message.reply_text("⏳ Baixando...")

    try:
        file = await document.get_file()
        content_bytes = await file.download_as_bytearray()
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")
        return

    # Processar arquivo(s)
    all_content = ""
    saved_files = []

    if filename.endswith(".zip"):
        await update.message.reply_text("📦 Extraindo ZIP...")
        txt_files = extract_txt_from_zip(bytes(content_bytes))
        if not txt_files:
            await update.message.reply_text("Nenhum .txt no ZIP.")
            return

        for fname, content in txt_files:
            tipo = detect_file_type(content)
            saved_filename = generate_filename(tipo, fname)
            filepath = EXPORTS_DIR / saved_filename
            filepath.write_text(content, encoding="utf-8")
            saved_files.append((saved_filename, filepath, content))
            all_content += content + "\n"
    else:
        try:
            content = content_bytes.decode("utf-8")
            tipo = detect_file_type(content)
            saved_filename = generate_filename(tipo, document.file_name)
            filepath = EXPORTS_DIR / saved_filename
            filepath.write_text(content, encoding="utf-8")
            saved_files.append((saved_filename, filepath, content))
            all_content = content
        except Exception as e:
            await update.message.reply_text(f"Erro ao decodificar: {e}")
            return

    await update.message.reply_text("🔍 Analisando com parser...")

    # Analisar sessões usando o parser real
    # Usa o primeiro arquivo salvo (ou combina múltiplos)
    file_sessions = {}
    for saved_filename, filepath, content in saved_files:
        sessions = analyze_file_sessions_from_path(filepath)
        for driver, dates in sessions.items():
            if driver not in file_sessions:
                file_sessions[driver] = {}
            for data, count in dates.items():
                file_sessions[driver][data] = file_sessions[driver].get(data, 0) + count

    existing_sessions = get_existing_sessions_from_db()

    # Calcular estatísticas por driver
    driver_stats = {}  # {driver: {'new': [(data, count)], 'existing': [(data, count)]}}

    for driver, dates in file_sessions.items():
        driver_stats[driver] = {'new': [], 'existing': []}
        existing_dates = existing_sessions.get(driver, set())

        for data, count in dates.items():
            if data in existing_dates:
                driver_stats[driver]['existing'].append((data, count))
            else:
                driver_stats[driver]['new'].append((data, count))

    total_blocks = count_blocks_in_content(all_content)

    logger.info(f"Arquivo salvo por {user.username or user.id}: {total_blocks} blocos, {len(file_sessions)} drivers")

    # Salvar estado
    user_states[user.id] = {
        'mode': 'select_driver',
        'content': all_content,
        'saved_files': saved_files,
        'total_blocks': total_blocks,
        'file_sessions': file_sessions,
        'existing_sessions': existing_sessions,
        'driver_stats': driver_stats,
        'driver': None,
        'data': None
    }

    # Montar botões de driver com estatísticas
    keyboard = []
    driver_order = ['RODRIGO', 'KAROL', 'FRANCIS', 'ARTHUR', 'RAFA']

    for driver in driver_order:
        if driver in driver_stats:
            stats = driver_stats[driver]
            new_days = len(stats['new'])
            existing_days = len(stats['existing'])

            # Formato: "DRIVER ✨5 🔄8"
            label_parts = [driver]
            if new_days > 0:
                label_parts.append(f"✨{new_days}")
            if existing_days > 0:
                label_parts.append(f"🔄{existing_days}")

            label = " ".join(label_parts)
            keyboard.append([InlineKeyboardButton(label, callback_data=f"driver_{driver}")])

    keyboard.append([InlineKeyboardButton("❌", callback_data="cancel")])

    # Resumo
    total_new_days = sum(len(s['new']) for s in driver_stats.values())
    total_existing_days = sum(len(s['existing']) for s in driver_stats.values())

    await update.message.reply_text(
        f"✨ {total_new_days}  🔄 {total_existing_days}\n\n"
        f"*Driver:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============ HANDLER DE CALLBACKS ============

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Callback answer failed: {e}")

    user_id = query.from_user.id
    data = query.data

    if user_id not in user_states:
        await query.edit_message_text("Sessão expirada. Envie o arquivo novamente.")
        return

    state = user_states[user_id]

    # ---- CANCELAR ----
    if data == "cancel":
        del user_states[user_id]
        await query.edit_message_text("❌ Cancelado.")
        return

    # ---- SELEÇÃO DE DRIVER ----
    if data.startswith("driver_"):
        driver = data.replace("driver_", "")
        state['driver'] = driver
        state['mode'] = 'select_date'

        # Obter estatísticas do driver
        driver_stats = state.get('driver_stats', {}).get(driver, {'new': [], 'existing': []})
        # Ordem CRESCENTE (mais antiga primeiro)
        new_dates = sorted(driver_stats['new'], key=lambda x: datetime.strptime(x[0], "%d/%m/%Y"))
        existing_dates = sorted(driver_stats['existing'], key=lambda x: datetime.strptime(x[0], "%d/%m/%Y"))

        keyboard = []

        # Datas NOVAS - podem ser importadas direto
        if new_dates:
            for dt, count in new_dates:
                dt_formatted = format_date_short(dt)
                keyboard.append([InlineKeyboardButton(f"✨ {dt_formatted} 🏎️{count}", callback_data=f"date_{dt}")])

        # Botão de reimportar se houver datas existentes
        if existing_dates:
            keyboard.append([InlineKeyboardButton(f"🔄 Reimportar ({len(existing_dates)} dias)", callback_data="show_reimport")])

        # Opção manual
        keyboard.append([InlineKeyboardButton("✏️ Digitar data", callback_data="date_manual")])
        keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_drivers")])
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])

        # Resumo
        msg = f"*{driver}*  ✨{len(new_dates)} 🔄{len(existing_dates)}"

        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---- VOLTAR PARA DRIVERS ----
    if data == "back_to_drivers":
        state['driver'] = None
        state['mode'] = 'select_driver'

        driver_stats = state.get('driver_stats', {})
        keyboard = []
        driver_order = ['RODRIGO', 'KAROL', 'FRANCIS', 'ARTHUR', 'RAFA']

        for driver in driver_order:
            if driver in driver_stats:
                stats = driver_stats[driver]
                new_days = len(stats['new'])
                existing_days = len(stats['existing'])

                label_parts = [driver]
                if new_days > 0:
                    label_parts.append(f"✨{new_days}")
                if existing_days > 0:
                    label_parts.append(f"🔄{existing_days}")

                label = " ".join(label_parts)
                keyboard.append([InlineKeyboardButton(label, callback_data=f"driver_{driver}")])

        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])

        total_new_days = sum(len(s['new']) for s in driver_stats.values())
        total_existing_days = sum(len(s['existing']) for s in driver_stats.values())

        await query.edit_message_text(
            f"✨ {total_new_days}  🔄 {total_existing_days}\n\n"
            f"*Driver:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---- MOSTRAR DATAS PARA REIMPORTAR ----
    if data == "show_reimport":
        driver = state['driver']
        driver_stats = state.get('driver_stats', {}).get(driver, {'new': [], 'existing': []})
        # Ordem CRESCENTE
        existing_dates = sorted(driver_stats['existing'], key=lambda x: datetime.strptime(x[0], "%d/%m/%Y"))

        keyboard = []
        for dt, count in existing_dates:
            dt_formatted = format_date_short(dt)
            keyboard.append([InlineKeyboardButton(f"🔄 {dt_formatted} 🏎️{count}", callback_data=f"reimport_{dt}")])

        keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"driver_{driver}")])
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])

        await query.edit_message_text(
            f"*Driver:* {driver}\n\n"
            f"⚠️ *Reimportar* substituirá os dados existentes!\n\n"
            f"*Escolha a data para reimportar:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---- REIMPORTAR DATA EXISTENTE ----
    if data.startswith("reimport_"):
        date_value = data.replace("reimport_", "")
        state['data'] = date_value
        state['mode'] = 'select_mode'
        state['reimport'] = True  # Flag para deletar dados antigos

        # Contar blocos para esta data
        driver = state['driver']
        file_sessions = state.get('file_sessions', {})
        block_count = file_sessions.get(driver, {}).get(date_value, 0)

        keyboard = [
            [InlineKeyboardButton("👁️ Ver 1 por 1", callback_data="mode_one_by_one")],
            [InlineKeyboardButton("⚡ Auto (só dúvidas)", callback_data="mode_auto")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="show_reimport")],
        ]

        await query.edit_message_text(
            f"🔄 *{driver}* — {format_date_short(date_value)}\n"
            f"📦 {block_count} deliveries\n\n"
            f"*Modo:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---- SELEÇÃO DE DATA ----
    if data.startswith("date_"):
        date_value = data.replace("date_", "")

        if date_value == "manual":
            state['mode'] = 'await_date_input'
            await query.edit_message_text(
                f"*Driver:* {state['driver']}\n\n"
                f"Digite a data no formato DD/MM/YYYY:\n"
                f"(ou DD/MM para ano atual)",
                parse_mode="Markdown"
            )
            return

        # Data selecionada - mostrar escolha de modo
        state['data'] = date_value
        state['mode'] = 'select_mode'

        # Contar blocos para esta data
        driver = state['driver']
        file_sessions = state.get('file_sessions', {})
        block_count = file_sessions.get(driver, {}).get(date_value, 0)

        keyboard = [
            [InlineKeyboardButton("👁️ Ver 1 por 1", callback_data="mode_one_by_one")],
            [InlineKeyboardButton("⚡ Auto (só dúvidas)", callback_data="mode_auto")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data=f"driver_{driver}")],
        ]

        await query.edit_message_text(
            f"*{driver}* — {format_date_short(date_value)}\n"
            f"📦 {block_count} deliveries\n\n"
            f"*Modo:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---- SELEÇÃO DE MODO ----
    if data == "mode_one_by_one":
        state['processing_mode'] = 'one_by_one'
        state['mode'] = 'processing'
        await start_block_processing(query, context, user_id)
        return

    if data == "mode_auto":
        state['processing_mode'] = 'auto'
        state['mode'] = 'processing'
        await start_auto_processing(query, context, user_id)
        return

    # ---- PROCESSAMENTO DE BLOCOS ----
    if data.startswith("confirm_"):
        await handle_confirm_block(query, context, user_id)
        return

    if data.startswith("skip_"):
        await handle_skip_block(query, context, user_id)
        return

    if data == "confirm_all":
        await handle_confirm_all(query, context, user_id)
        return

    if data.startswith("edit_"):
        await query.edit_message_text(
            "Para corrigir, responda com o formato:\n"
            "`/corrigir produto quantidade`\n\n"
            "Exemplo: `/corrigir escama 5`",
            parse_mode="Markdown"
        )
        return

    if data == "next_session":
        state['current_session_idx'] += 1
        await start_session_processing(query, context, user_id)
        return

    if data == "finish":
        await handle_finish(query, context, user_id)
        return

    # Legacy - manter compatibilidade
    if data == "process_all":
        state['mode'] = 'processing'
        state['current_session_idx'] = 0
        await start_session_processing(query, context, user_id)
        return

    if data == "choose_sessions":
        await query.edit_message_text("Função em desenvolvimento.")
        return


async def start_block_processing(query, context, user_id: int):
    """Inicia processamento de blocos com driver/data selecionados."""
    state = user_states[user_id]
    driver = state['driver']
    data = state['data']
    saved_files = state.get('saved_files', [])

    # Parsear usando o parser real
    all_blocos = []
    for saved_filename, filepath, content in saved_files:
        try:
            blocos, log = parsear_arquivo(str(filepath), gerar_log=False)
            # Filtrar só os blocos do driver/data selecionados
            for bloco in blocos:
                if bloco.driver == driver and bloco.data_entrega == data:
                    all_blocos.append(bloco)
        except Exception as e:
            logger.error(f"Erro ao parsear {filepath}: {e}")

    if not all_blocos:
        await query.edit_message_text(
            f"❌ Nenhum bloco encontrado.\n\n"
            f"Driver: {driver}\n"
            f"Data: {data}"
        )
        del user_states[user_id]
        return

    # Converter blocos do parser para o formato interno
    blocks = []
    for bloco in all_blocos:
        # Extrair itens do texto
        items = extract_items_from_text(bloco.texto)
        if items:
            blocks.append(ParsedBlock(
                id_entrega=bloco.id_entrega,
                texto_raw=bloco.texto,
                items=items,
                endereco=extract_address(bloco.texto),
                linha_inicio=bloco.linha_inicio
            ))

    if not blocks:
        await query.edit_message_text(
            f"❌ Blocos encontrados mas sem itens detectados.\n\n"
            f"Driver: {driver}\n"
            f"Data: {data}\n"
            f"Blocos raw: {len(all_blocos)}"
        )
        del user_states[user_id]
        return

    # Salvar blocos no estado
    state['current_blocks'] = blocks
    state['current_block_idx'] = 0
    state['session_results'] = []

    await query.edit_message_text(
        f"*Processando: {driver} - {data}*\n"
        f"Total: {len(blocks)} blocos\n\n"
        "Iniciando validação...",
        parse_mode="Markdown"
    )

    # Mostrar primeiro bloco
    await show_block(query.message.chat_id, context, user_id)


def detect_block_doubts(block: ParsedBlock, bloco_original=None) -> List[str]:
    """Detecta dúvidas/problemas em um bloco."""
    doubts = []

    # Sem itens detectados
    if not block.items:
        doubts.append("Nenhum item detectado")

    # Quantidade suspeita (muito alta)
    for item in block.items:
        if item.quantidade > 50:
            doubts.append(f"Qtd alta: {item.produto} x{item.quantidade}")

    # Produto muito curto (pode ser erro)
    for item in block.items:
        if len(item.produto) <= 2:
            doubts.append(f"Produto curto: '{item.produto}'")

    # Issues do parser original
    if bloco_original and hasattr(bloco_original, 'issues') and bloco_original.issues:
        for issue in bloco_original.issues:
            if issue.needs_review:
                doubts.append(issue.description)

    return doubts


async def start_auto_processing(query, context, user_id: int):
    """Processa automaticamente e mostra apenas dúvidas."""
    state = user_states[user_id]
    driver = state['driver']
    data = state['data']
    saved_files = state.get('saved_files', [])

    await query.edit_message_text(
        f"⚡ *Auto: {driver} - {format_date_short(data)}*\n\n"
        "Processando...",
        parse_mode="Markdown"
    )

    # Parsear usando o parser real
    all_blocos = []
    for saved_filename, filepath, content in saved_files:
        try:
            blocos, log = parsear_arquivo(str(filepath), gerar_log=False)
            for bloco in blocos:
                if bloco.driver == driver and bloco.data_entrega == data:
                    all_blocos.append(bloco)
        except Exception as e:
            logger.error(f"Erro ao parsear {filepath}: {e}")

    if not all_blocos:
        await query.message.reply_text(
            f"❌ Nenhum bloco encontrado.\n\n"
            f"Driver: {driver}\n"
            f"Data: {data}"
        )
        del user_states[user_id]
        return

    # Converter e classificar blocos
    blocks_ok = []      # Blocos sem dúvidas
    blocks_doubt = []   # Blocos com dúvidas
    results_auto = []   # Resultados auto-confirmados

    for bloco in all_blocos:
        items = extract_items_from_text(bloco.texto)

        parsed_block = ParsedBlock(
            id_entrega=bloco.id_entrega,
            texto_raw=bloco.texto,
            items=items if items else [],
            endereco=extract_address(bloco.texto),
            linha_inicio=bloco.linha_inicio
        )

        doubts = detect_block_doubts(parsed_block, bloco)

        if doubts:
            parsed_block.ambiguidades = doubts
            blocks_doubt.append(parsed_block)
        else:
            blocks_ok.append(parsed_block)
            # Auto-confirmar
            for item in parsed_block.items:
                results_auto.append({
                    'id_sale_delivery': parsed_block.id_entrega,
                    'driver': driver,
                    'data': data,
                    'produto': item.produto,
                    'quantidade': item.quantidade,
                    'endereco': parsed_block.endereco,
                    'texto_raw': parsed_block.texto_raw
                })

    # Salvar no estado
    state['session_results'] = results_auto
    state['current_blocks'] = blocks_doubt
    state['current_block_idx'] = 0
    state['auto_confirmed'] = len(blocks_ok)

    # Resumo
    total_items = sum(len(b.items) for b in blocks_ok)

    if blocks_doubt:
        await query.message.reply_text(
            f"⚡ *Auto-confirmados:* {len(blocks_ok)} blocos ({total_items} itens)\n"
            f"⚠️ *Com dúvidas:* {len(blocks_doubt)} blocos\n\n"
            "Revisando dúvidas...",
            parse_mode="Markdown"
        )
        # Mostrar primeiro bloco com dúvida
        await show_doubt_block(query.message.chat_id, context, user_id)
    else:
        # Tudo ok, salvar direto
        await query.message.reply_text(
            f"⚡ *Auto-confirmados:* {len(blocks_ok)} blocos ({total_items} itens)\n"
            f"✅ Sem dúvidas!\n\n"
            "Salvando...",
            parse_mode="Markdown"
        )
        await save_results_to_db(query.message.chat_id, context, user_id)


async def show_doubt_block(chat_id: int, context, user_id: int):
    """Mostra bloco com dúvida para revisão."""
    state = user_states[user_id]
    blocks = state['current_blocks']
    idx = state['current_block_idx']
    driver = state['driver']
    data = state['data']
    auto_confirmed = state.get('auto_confirmed', 0)

    if idx >= len(blocks):
        # Acabaram as dúvidas, salvar
        await save_results_to_db(chat_id, context, user_id)
        return

    block = blocks[idx]

    # Montar mensagem
    items_text = "\n".join([f"  • {item.produto}: {item.quantidade}" for item in block.items]) if block.items else "  (nenhum)"

    raw_text = block.texto_raw
    if len(raw_text) > 1000:
        raw_text = raw_text[:1000] + "..."

    # Dúvidas
    doubts_text = "\n".join([f"  ⚠️ {d}" for d in block.ambiguidades])

    msg = (
        f"*Dúvida {idx + 1}/{len(blocks)}* 🏎️{block.id_entrega}\n"
        f"(✅ {auto_confirmed} já confirmados)\n\n"
        f"```\n{raw_text}\n```\n\n"
        f"📦 *Itens:*\n{items_text}\n\n"
        f"*Problemas:*\n{doubts_text}"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm_{idx}"),
            InlineKeyboardButton("⏭️ Pular", callback_data=f"skip_{idx}")
        ],
        [
            InlineKeyboardButton("✅ Confirmar Resto", callback_data="confirm_all"),
            InlineKeyboardButton("🏁 Finalizar", callback_data="finish")
        ]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def start_session_processing(query, context, user_id: int):
    """Inicia processamento de uma sessão (modo legado)."""
    state = user_states[user_id]
    sessions = state['sessions']
    idx = state['current_session_idx']

    if idx >= len(sessions):
        await finish_processing(query, context, user_id)
        return

    session = sessions[idx]

    # Parsear blocos da sessão
    blocks = parse_blocks_from_content(session['content'], session['driver'], session['data'])

    if not blocks:
        await query.edit_message_text(
            f"Sessão {session['driver']} {session['data']}: Nenhum bloco encontrado.\n"
            "Pulando para próxima..."
        )
        state['current_session_idx'] += 1
        await start_session_processing(query, context, user_id)
        return

    # Salvar blocos no estado
    state['current_blocks'] = blocks
    state['current_block_idx'] = 0
    state['session_results'] = []

    await query.edit_message_text(
        f"*Processando: {session['driver']} - {session['data']}*\n"
        f"Total: {len(blocks)} blocos\n\n"
        "Iniciando validação...",
        parse_mode="Markdown"
    )

    # Mostrar primeiro bloco
    await show_current_block(query.message.chat_id, context, user_id)


async def show_block(chat_id: int, context, user_id: int):
    """Mostra o bloco atual para validação (novo fluxo)."""
    state = user_states[user_id]
    blocks = state['current_blocks']
    idx = state['current_block_idx']
    driver = state['driver']
    data = state['data']

    if idx >= len(blocks):
        # Acabaram os blocos
        await save_results_to_db(chat_id, context, user_id)
        return

    block = blocks[idx]

    # Montar mensagem
    items_text = "\n".join([f"  • {item.produto}: {item.quantidade}" for item in block.items])

    # Mostrar texto completo (até 1000 chars para caber no Telegram)
    raw_text = block.texto_raw
    if len(raw_text) > 1000:
        raw_text = raw_text[:1000] + "..."

    msg = (
        f"*{idx + 1}/{len(blocks)}* 🏎️{block.id_entrega}\n\n"
        f"```\n{raw_text}\n```\n\n"
        f"📦 *Itens:*\n{items_text}\n"
    )

    if block.endereco:
        msg += f"\n📍 {block.endereco}"

    if block.ambiguidades:
        msg += f"\n⚠️ {', '.join(block.ambiguidades)}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm_{idx}"),
            InlineKeyboardButton("⏭️ Pular", callback_data=f"skip_{idx}")
        ],
        [
            InlineKeyboardButton("✅ Confirmar Todos", callback_data="confirm_all"),
            InlineKeyboardButton("🏁 Finalizar", callback_data="finish")
        ]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def save_results_to_db(chat_id: int, context, user_id: int):
    """Salva resultados no banco (novo fluxo)."""
    state = user_states[user_id]
    results = state.get('session_results', [])
    driver = state['driver']
    data = state['data']
    reimport = state.get('reimport', False)
    saved_files = state.get('saved_files', [])

    # Nome do arquivo origem
    arquivo_origem = saved_files[0][0] if saved_files else None

    if not results:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Nenhum item confirmado para {driver} {data}."
        )
    else:
        try:
            db = GrowBotDB()

            # Converter data DD/MM/YYYY para YYYY-MM-DD
            parts = data.split('/')
            data_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"

            # Se for reimportação, deletar dados antigos de AMBAS tabelas
            deleted_mov = 0
            deleted_raw = 0
            if reimport:
                result = db.conn.execute("""
                    DELETE FROM movimentos
                    WHERE tipo = 'entrega' AND driver = ? AND data_movimento = ?
                """, [driver, data_iso])
                deleted_mov = result.rowcount

                result = db.conn.execute("""
                    DELETE FROM blocos_raw
                    WHERE driver = ? AND data_entrega = ?
                """, [driver, data_iso])
                deleted_raw = result.rowcount

            # Agrupar resultados por bloco (id_sale_delivery)
            blocos_map = {}  # {id_entrega: {texto_raw, items: [...]}}
            for item in results:
                id_ent = item['id_sale_delivery']
                if id_ent not in blocos_map:
                    blocos_map[id_ent] = {
                        'texto_raw': item.get('texto_raw', ''),
                        'endereco': item.get('endereco'),
                        'items': []
                    }
                blocos_map[id_ent]['items'].append(item)

            # 1. Salvar blocos_raw (um por bloco)
            blocos_count = 0
            for id_entrega, bloco_data in blocos_map.items():
                try:
                    db.conn.execute("""
                        INSERT INTO blocos_raw (
                            id_sale_delivery, texto_raw, driver, data_entrega,
                            arquivo_origem, review_status
                        ) VALUES (?, ?, ?, ?, ?, 'ok')
                        ON CONFLICT (id_sale_delivery, driver, data_entrega) DO UPDATE SET
                            texto_raw = EXCLUDED.texto_raw,
                            arquivo_origem = EXCLUDED.arquivo_origem,
                            review_status = 'ok'
                    """, [
                        id_entrega,
                        bloco_data['texto_raw'],
                        driver,
                        data_iso,
                        arquivo_origem
                    ])
                    blocos_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao salvar bloco_raw {id_entrega}: {e}")

            # 2. Salvar movimentos (um por item/produto)
            mov_count = 0
            for item in results:
                db.conn.execute("""
                    INSERT INTO movimentos (
                        tipo, id_sale_delivery, driver, produto, quantidade,
                        data_movimento, endereco, arquivo_origem
                    ) VALUES ('entrega', ?, ?, ?, ?, ?, ?, ?)
                """, [
                    item['id_sale_delivery'],
                    driver,
                    item['produto'],
                    item['quantidade'],
                    data_iso,
                    item.get('endereco'),
                    arquivo_origem
                ])
                mov_count += 1

            db.close()

            msg = f"✅ *Salvos: {driver} {data}*\n"
            if reimport:
                if deleted_mov > 0:
                    msg += f"🔄 Removidos: {deleted_mov} mov, {deleted_raw} blocos\n"
            msg += f"📦 Blocos: {blocos_count}\n"
            msg += f"📥 Movimentos: {mov_count}"

            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Erro ao salvar: {e}"
            )

    # Limpar estado
    if user_id in user_states:
        del user_states[user_id]

    await context.bot.send_message(
        chat_id=chat_id,
        text="🏁 *Processamento concluído!*\n\nUse /saldo para ver o resultado.",
        parse_mode="Markdown"
    )


async def show_current_block(chat_id: int, context, user_id: int):
    """Mostra o bloco atual para validação (modo legado)."""
    state = user_states[user_id]
    blocks = state['current_blocks']
    idx = state['current_block_idx']
    session = state['sessions'][state['current_session_idx']]

    if idx >= len(blocks):
        # Acabaram os blocos desta sessão
        await save_session_to_db(chat_id, context, user_id)
        return

    block = blocks[idx]

    # Montar mensagem
    items_text = "\n".join([f"  • {item.produto}: {item.quantidade}" for item in block.items])

    # Truncar texto raw se muito grande
    raw_preview = block.texto_raw[:300]
    if len(block.texto_raw) > 300:
        raw_preview += "..."

    msg = (
        f"*Bloco {idx + 1}/{len(blocks)}* - ID: {block.id_entrega}\n"
        f"Driver: {session['driver']} | Data: {session['data']}\n\n"
        f"📝 *Texto:*\n```\n{raw_preview}\n```\n\n"
        f"📦 *Itens detectados:*\n{items_text}\n"
    )

    if block.endereco:
        msg += f"\n📍 Endereço: {block.endereco}"

    if block.ambiguidades:
        msg += f"\n⚠️ Avisos: {', '.join(block.ambiguidades)}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm_{idx}"),
            InlineKeyboardButton("⏭️ Pular", callback_data=f"skip_{idx}")
        ],
        [InlineKeyboardButton("✏️ Corrigir", callback_data=f"edit_{idx}")]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_confirm_block(query, context, user_id: int):
    """Confirma bloco atual."""
    state = user_states[user_id]
    blocks = state['current_blocks']
    idx = state['current_block_idx']
    block = blocks[idx]

    # Determinar driver/data (novo fluxo vs legado)
    if 'driver' in state and state['driver']:
        driver = state['driver']
        data = state['data']
        new_flow = True
    else:
        session = state['sessions'][state['current_session_idx']]
        driver = session['driver']
        data = session['data']
        new_flow = False

    # Salvar resultado
    for item in block.items:
        state['session_results'].append({
            'id_sale_delivery': block.id_entrega,
            'driver': driver,
            'data': data,
            'produto': item.produto,
            'quantidade': item.quantidade,
            'endereco': block.endereco,
            'texto_raw': block.texto_raw
        })

    await query.edit_message_text(f"✅ Bloco {block.id_entrega} confirmado!")

    # Próximo bloco
    state['current_block_idx'] += 1

    # Determinar qual função de exibição usar
    if state.get('processing_mode') == 'auto':
        await show_doubt_block(query.message.chat_id, context, user_id)
    elif new_flow:
        await show_block(query.message.chat_id, context, user_id)
    else:
        await show_current_block(query.message.chat_id, context, user_id)


async def handle_skip_block(query, context, user_id: int):
    """Pula bloco atual."""
    state = user_states[user_id]
    idx = state['current_block_idx']
    block = state['current_blocks'][idx]

    await query.edit_message_text(f"⏭️ Bloco {block.id_entrega} pulado.")

    state['current_block_idx'] += 1

    # Determinar qual função de exibição usar
    if state.get('processing_mode') == 'auto':
        await show_doubt_block(query.message.chat_id, context, user_id)
    elif 'driver' in state and state['driver']:
        await show_block(query.message.chat_id, context, user_id)
    else:
        await show_current_block(query.message.chat_id, context, user_id)


async def handle_confirm_all(query, context, user_id: int):
    """Confirma todos os blocos restantes."""
    state = user_states[user_id]
    blocks = state['current_blocks']
    idx = state['current_block_idx']
    driver = state['driver']
    data = state['data']

    confirmed = 0
    for i in range(idx, len(blocks)):
        block = blocks[i]
        for item in block.items:
            state['session_results'].append({
                'id_sale_delivery': block.id_entrega,
                'driver': driver,
                'data': data,
                'produto': item.produto,
                'quantidade': item.quantidade,
                'endereco': block.endereco,
                'texto_raw': block.texto_raw
            })
        confirmed += 1

    await query.edit_message_text(f"✅ {confirmed} blocos confirmados!")

    # Salvar no banco
    await save_results_to_db(query.message.chat_id, context, user_id)


async def handle_finish(query, context, user_id: int):
    """Finaliza o processamento salvando o que foi confirmado."""
    state = user_states[user_id]

    # Verificar se é novo fluxo
    if 'driver' in state and state['driver']:
        await save_results_to_db(query.message.chat_id, context, user_id)
    else:
        await finish_processing(query, context, user_id)


async def save_session_to_db(chat_id: int, context, user_id: int):
    """Salva resultados da sessão no banco."""
    state = user_states[user_id]
    results = state.get('session_results', [])
    session = state['sessions'][state['current_session_idx']]

    if not results:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Sessão {session['driver']} {session['data']}: Nenhum item confirmado."
        )
    else:
        try:
            db = GrowBotDB()
            count = 0

            for item in results:
                # Converter data DD/MM/YYYY para YYYY-MM-DD
                parts = item['data'].split('/')
                data_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"

                db.conn.execute("""
                    INSERT INTO movimentos (tipo, id_sale_delivery, driver, produto, quantidade, data_movimento, endereco)
                    VALUES ('entrega', ?, ?, ?, ?, ?, ?)
                """, [
                    item['id_sale_delivery'],
                    item['driver'],
                    item['produto'],
                    item['quantidade'],
                    data_iso,
                    item.get('endereco')
                ])
                count += 1

            db.close()

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ *Sessão {session['driver']} {session['data']} salva!*\n"
                     f"Total: {count} movimentos inseridos.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Erro ao salvar: {e}"
            )

    # Verificar se há mais sessões
    state['current_session_idx'] += 1
    if state['current_session_idx'] < len(state['sessions']):
        keyboard = [
            [InlineKeyboardButton("▶️ Próxima sessão", callback_data="next_session")],
            [InlineKeyboardButton("🏁 Finalizar", callback_data="finish")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text="Continuar para próxima sessão?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await finish_processing_message(chat_id, context, user_id)


async def finish_processing(query, context, user_id: int):
    """Finaliza todo o processamento."""
    await query.edit_message_text("Processamento finalizado!")
    await finish_processing_message(query.message.chat_id, context, user_id)


async def finish_processing_message(chat_id: int, context, user_id: int):
    """Envia mensagem final e limpa estado."""
    if user_id in user_states:
        del user_states[user_id]

    await context.bot.send_message(
        chat_id=chat_id,
        text="🏁 *Processamento concluído!*\n\nUse /saldo para ver o resultado.",
        parse_mode="Markdown"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    # Verificar se está aguardando entrada de data manual
    if user_id in user_states and user_states[user_id].get('mode') == 'await_date_input':
        state = user_states[user_id]
        text = update.message.text.strip()

        # Tentar parsear data
        date_match = re.match(r'^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$', text)
        if date_match:
            day, month, year = date_match.groups()
            if not year:
                year = str(datetime.now().year)
            elif len(year) == 2:
                year = "20" + year

            state['data'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
            state['mode'] = 'processing'

            await update.message.reply_text(
                f"✅ Data: {state['data']}\n"
                f"Driver: {state['driver']}\n\n"
                "Iniciando processamento..."
            )

            # Criar query fake para iniciar processamento
            # Usamos send_message e depois chamamos a função
            await start_block_processing_from_message(update.message, context, user_id)
            return
        else:
            await update.message.reply_text(
                "❌ Formato inválido.\n\n"
                "Use: DD/MM ou DD/MM/YYYY\n"
                "Exemplo: 07/01 ou 07/01/2026"
            )
            return

    await update.message.reply_text("Envie um arquivo .txt ou .zip\nUse /help para ajuda.")


async def start_block_processing_from_message(message, context, user_id: int):
    """Inicia processamento de blocos a partir de mensagem de texto."""
    state = user_states[user_id]
    driver = state['driver']
    data = state['data']
    saved_files = state.get('saved_files', [])

    # Parsear usando o parser real
    all_blocos = []
    for saved_filename, filepath, content in saved_files:
        try:
            blocos, log = parsear_arquivo(str(filepath), gerar_log=False)
            for bloco in blocos:
                if bloco.driver == driver and bloco.data_entrega == data:
                    all_blocos.append(bloco)
        except Exception as e:
            logger.error(f"Erro ao parsear {filepath}: {e}")

    if not all_blocos:
        await message.reply_text(
            f"❌ Nenhum bloco encontrado.\n\n"
            f"Driver: {driver}\n"
            f"Data: {data}"
        )
        del user_states[user_id]
        return

    # Converter blocos do parser para o formato interno
    blocks = []
    for bloco in all_blocos:
        items = extract_items_from_text(bloco.texto)
        if items:
            blocks.append(ParsedBlock(
                id_entrega=bloco.id_entrega,
                texto_raw=bloco.texto,
                items=items,
                endereco=extract_address(bloco.texto),
                linha_inicio=bloco.linha_inicio
            ))

    if not blocks:
        await message.reply_text(
            f"❌ Blocos encontrados mas sem itens.\n\n"
            f"Driver: {driver}\n"
            f"Data: {data}"
        )
        del user_states[user_id]
        return

    # Salvar blocos no estado
    state['current_blocks'] = blocks
    state['current_block_idx'] = 0
    state['session_results'] = []

    await message.reply_text(
        f"*Processando: {driver} - {data}*\n"
        f"Total: {len(blocks)} blocos",
        parse_mode="Markdown"
    )

    # Mostrar primeiro bloco
    await show_block(message.chat_id, context, user_id)


# ============ MAIN ============

def main():
    if not BOT_TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado!")
        return

    EXPORTS_DIR.mkdir(exist_ok=True)

    print("Iniciando GrowBot Telegram v1.1...")
    print(f"Exports: {EXPORTS_DIR}")
    if AUTHORIZED_USERS:
        print(f"Autorizados: {AUTHORIZED_USERS}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("saldo", saldo_command))
    app.add_handler(CommandHandler("cancelar", cancelar_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot iniciado!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
