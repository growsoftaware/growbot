#!/usr/bin/env python3
"""
Wrapper para LLMs (Claude e OpenAI).
Envia blocos de texto e recebe JSON estruturado.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# Carrega system prompt
SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"


def carregar_system_prompt(aliases_path: str = None) -> str:
    """Carrega o system prompt e adiciona aliases se existirem."""
    with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
        prompt = f.read()

    # Adiciona aliases aprendidos, se existirem
    if aliases_path and Path(aliases_path).exists():
        with open(aliases_path, 'r', encoding='utf-8') as f:
            aliases = json.load(f)
        if aliases:
            prompt += "\n\n### Aliases aprendidos (usar também):\n"
            for alias in aliases:
                prompt += f"- {alias['alias']} => {alias['canonical']}\n"

    return prompt


def extrair_json(texto: str) -> dict:
    """Extrai JSON de uma resposta que pode ter markdown."""
    # Tenta extrair de bloco ```json
    match = texto.find('```json')
    if match != -1:
        inicio = match + 7
        fim = texto.find('```', inicio)
        if fim != -1:
            texto = texto[inicio:fim]

    # Tenta extrair de bloco ``` genérico
    elif texto.find('```') != -1:
        inicio = texto.find('```') + 3
        fim = texto.find('```', inicio)
        if fim != -1:
            texto = texto[inicio:fim]

    return json.loads(texto.strip())


def extract_claude(bloco: str, aliases_path: str = None) -> dict:
    """Extrai dados usando Claude API."""
    import anthropic

    client = anthropic.Anthropic()
    system_prompt = carregar_system_prompt(aliases_path)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {"role": "user", "content": bloco}
        ]
    )

    texto = response.content[0].text
    return extrair_json(texto)


def extract_openai(bloco: str, aliases_path: str = None) -> dict:
    """Extrai dados usando OpenAI API."""
    from openai import OpenAI

    client = OpenAI()
    system_prompt = carregar_system_prompt(aliases_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": bloco}
        ]
    )

    texto = response.choices[0].message.content
    return extrair_json(texto)


def extract(bloco: str, provider: str = "claude", aliases_path: str = None) -> dict:
    """Wrapper que escolhe o provider."""
    if provider == "claude":
        return extract_claude(bloco, aliases_path)
    elif provider == "openai":
        return extract_openai(bloco, aliases_path)
    else:
        raise ValueError(f"Provider desconhecido: {provider}")


# ============ AGENT CHAT ============

AGENT_PROMPT_PATH = Path(__file__).parent / "system_prompt_agent.md"


def load_agent_prompt(context: dict = None) -> str:
    """Carrega o system prompt do agente e injeta contexto."""
    with open(AGENT_PROMPT_PATH, 'r', encoding='utf-8') as f:
        prompt = f.read()

    # Injeta contexto se fornecido
    if context:
        context_str = json.dumps(context, indent=2, ensure_ascii=False)
        prompt = prompt.replace("{context}", context_str)
    else:
        prompt = prompt.replace("{context}", "Nenhum arquivo carregado ainda.")

    return prompt


def chat_with_context(
    message: str,
    history: list = None,
    context: dict = None,
    model: str = "claude-sonnet-4-20250514"
) -> dict:
    """
    Envia mensagem para Claude com histórico de conversa e contexto.

    Args:
        message: Mensagem do usuário
        history: Lista de mensagens anteriores [{"role": "user/assistant", "content": "..."}]
        context: Dicionário com contexto atual (arquivo, driver, data, blocos, etc.)
        model: Modelo Claude a usar

    Returns:
        dict com {"message": str, "action": str|None, "params": dict}
    """
    import anthropic

    client = anthropic.Anthropic()
    system_prompt = load_agent_prompt(context)

    # Monta histórico de mensagens
    messages = []
    if history:
        # Limita a últimas 20 mensagens para economia de tokens
        for msg in history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Adiciona mensagem atual
    messages.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )

        texto = response.content[0].text

        # Tenta parsear como JSON
        try:
            return extrair_json(texto)
        except json.JSONDecodeError:
            # Se não for JSON válido, retorna como mensagem simples
            return {
                "message": texto,
                "action": None,
                "params": {}
            }

    except Exception as e:
        return {
            "message": f"Erro ao processar: {str(e)}",
            "action": None,
            "params": {}
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extrai dados de entregas via LLM")
    parser.add_argument("arquivo", help="Arquivo .txt com export do WhatsApp")
    parser.add_argument("--provider", choices=["claude", "openai"], default="claude")
    parser.add_argument("--aliases", default="aliases.json", help="Arquivo de aliases")
    args = parser.parse_args()

    if not Path(args.arquivo).exists():
        print(f"Arquivo não encontrado: {args.arquivo}")
        sys.exit(1)

    # Importa parser local
    from parser import parsear_arquivo

    blocos = parsear_arquivo(args.arquivo)

    if not blocos:
        print("Nenhum bloco encontrado (procure por marcadores 🏎️)")
        sys.exit(1)

    print(f"Processando {len(blocos)} blocos com {args.provider}...\n")

    todos_items = []
    todas_sugestoes = []

    for i, bloco in enumerate(blocos, 1):
        print(f"Bloco {i}/{len(blocos)}...")
        resultado = extract(bloco.texto, args.provider, args.aliases)

        if "items" in resultado:
            todos_items.extend(resultado["items"])

        if "suggested_rule_updates" in resultado:
            sugestoes = resultado["suggested_rule_updates"].get("produto_aliases_to_add", [])
            todas_sugestoes.extend(sugestoes)

    output = {
        "items": todos_items,
        "suggested_rule_updates": {
            "produto_aliases_to_add": todas_sugestoes
        }
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
