#!/usr/bin/env python3
"""
Parser determinístico para exports do WhatsApp.
Separa blocos de entrega pelo marcador 🏎️ e detecta sessões (driver/data).
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta


DRIVERS = {"RAFA", "FRANCIS", "RODRIGO", "KAROL", "ARTHUR"}
DIAS_SEMANA = {
    "segunda": 0, "terça": 1, "terca": 1, "quarta": 2,
    "quinta": 3, "sexta": 4, "sábado": 5, "sabado": 5, "domingo": 6
}


@dataclass
class Bloco:
    id_entrega: str          # "001", "002", etc
    texto: str               # texto bruto do bloco
    driver: Optional[str] = None
    data_entrega: Optional[str] = None


@dataclass
class Sessao:
    blocos: list = field(default_factory=list)
    driver: Optional[str] = None
    data_entrega: Optional[str] = None
    data_base: Optional[datetime] = None  # data dos timestamps pra calcular "quinta", etc


def extrair_id_entrega(linha: str) -> Optional[str]:
    """Extrai número do marcador 🏎️N e retorna como 3 dígitos."""
    match = re.search(r'(\d+)\s*🏎️|🏎️\s*(\d+)', linha)
    if match:
        num = match.group(1) or match.group(2)
        return num.zfill(3)
    return None


def extrair_timestamp(linha: str) -> Optional[datetime]:
    """Extrai timestamp de linha no formato [DD/MM/YY, HH:MM:SS]"""
    match = re.match(r'\[(\d{2}/\d{2}/\d{2}), (\d{2}:\d{2}:\d{2})\]', linha)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)} {match.group(2)}", "%d/%m/%y %H:%M:%S")
        except:
            pass
    return None


def detectar_driver(texto: str) -> Optional[str]:
    """Detecta driver no texto (palavra exata, não parte de outra)."""
    texto_upper = texto.upper()
    # Usa regex para word boundary - não pega "Francisco" como "Francis"
    for driver in DRIVERS:
        if re.search(rf'\b{driver}\b', texto_upper):
            return driver
    return None


def calcular_data_por_dia_semana(dia_semana: str, data_base: datetime) -> str:
    """Calcula a data mais próxima no passado/futuro para um dia da semana."""
    dia_semana = dia_semana.lower()
    if dia_semana not in DIAS_SEMANA:
        return None

    target_weekday = DIAS_SEMANA[dia_semana]
    current_weekday = data_base.weekday()

    # Calcula dias até o próximo dia da semana (pode ser passado ou futuro próximo)
    diff = target_weekday - current_weekday
    if diff > 3:  # Se for mais de 3 dias no futuro, assume semana passada
        diff -= 7
    elif diff < -3:  # Se for mais de 3 dias no passado, assume próxima semana
        diff += 7

    data_alvo = data_base + timedelta(days=diff)
    return data_alvo.strftime("%d/%m/%Y")


def detectar_data(texto: str, data_base: datetime = None) -> Optional[str]:
    """Detecta data no texto."""
    # Formato DD/MM/YYYY ou DD/MM/YY
    match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', texto)
    if match:
        dia, mes = match.group(1), match.group(2)
        ano = match.group(3) or (data_base.year if data_base else 2025)
        if len(str(ano)) == 2:
            ano = f"20{ano}"
        return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"

    # Formato "DD do MM"
    match = re.search(r'(\d{1,2})\s+do\s+(\d{1,2})', texto)
    if match:
        dia, mes = match.group(1), match.group(2)
        ano = data_base.year if data_base else 2025
        return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"

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
        "salve", "opa", "blz", "ok", "👍", "kk"
    ]
    linha_lower = linha.lower()

    # Ignora se é só saudação/confirmação curta
    for termo in ignorar:
        if termo in linha_lower:
            return True

    # Ignora linhas muito curtas sem conteúdo útil
    texto_limpo = re.sub(r'\[.*?\].*?:', '', linha).strip()
    if len(texto_limpo) < 3 and '🏎️' not in linha:
        return True

    return False


def eh_rodape(linha: str, proximas_linhas: list) -> bool:
    """Verifica se linha é rodapé (driver/data no final de sessão)."""
    texto = re.sub(r'\[.*?\].*?:', '', linha).strip()

    # Detecta driver
    driver = detectar_driver(texto)
    if driver:
        return True

    # Detecta dia da semana isolado
    texto_lower = texto.lower()
    for dia in DIAS_SEMANA.keys():
        if dia in texto_lower and len(texto) < 30:
            return True

    return False


def parsear_arquivo(caminho: str) -> list[Bloco]:
    """Lê arquivo e retorna lista de blocos com driver/data."""
    with open(caminho, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

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

    i = 0
    while i < len(linhas):
        linha = linhas[i]

        # Verifica se é rodapé (driver/data)
        proximas = linhas[i+1:i+3] if i+1 < len(linhas) else []
        if eh_rodape(linha, proximas):
            texto = re.sub(r'\[.*?\].*?:', '', linha).strip()

            # Extrai driver e data do rodapé
            driver = detectar_driver(texto)
            data = detectar_data(texto, data_base)

            if driver:
                sessao_atual.driver = driver
            if data:
                sessao_atual.data_entrega = data

            # Verifica próxima linha também (pode ser "Quinta" na linha seguinte)
            if i+1 < len(linhas):
                prox = linhas[i+1]
                if not extrair_timestamp(prox) or eh_rodape(prox, []):
                    texto_prox = re.sub(r'\[.*?\].*?:', '', prox).strip()
                    if not sessao_atual.driver:
                        sessao_atual.driver = detectar_driver(texto_prox)
                    if not sessao_atual.data_entrega:
                        sessao_atual.data_entrega = detectar_data(texto_prox, data_base)
                    i += 1

            # Fecha sessão se já tem blocos
            if sessao_atual.blocos:
                sessoes.append(sessao_atual)
                sessao_atual = Sessao(data_base=data_base)

            i += 1
            continue

        # Ignora linhas sem conteúdo útil
        if eh_linha_ignoravel(linha):
            i += 1
            continue

        # Adiciona linha ao bloco atual
        bloco_atual.append(linha)

        # Verifica se fecha bloco (tem 🏎️)
        id_entrega = extrair_id_entrega(linha)
        if id_entrega:
            sessao_atual.blocos.append(Bloco(
                id_entrega=id_entrega,
                texto=''.join(bloco_atual)
            ))
            bloco_atual = []

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
            todos_blocos.append(bloco)

    return todos_blocos


def main():
    if len(sys.argv) < 2:
        print("Uso: python parser.py <arquivo.txt>")
        print("Exemplo: python parser.py exports/conversa.txt")
        sys.exit(1)

    caminho = sys.argv[1]
    if not Path(caminho).exists():
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)

    blocos = parsear_arquivo(caminho)

    print(f"Encontrados {len(blocos)} blocos de entrega:\n")
    for i, bloco in enumerate(blocos[:10], 1):  # Mostra só os 10 primeiros
        print(f"{'='*50}")
        print(f"BLOCO {i} | ID: {bloco.id_entrega} | Driver: {bloco.driver} | Data: {bloco.data_entrega}")
        print(f"{'='*50}")
        print(bloco.texto)
        print()

    if len(blocos) > 10:
        print(f"... e mais {len(blocos) - 10} blocos")


if __name__ == "__main__":
    main()
