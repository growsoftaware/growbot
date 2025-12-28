#!/usr/bin/env python3
"""
GrowBot - Extrator de Entregas WhatsApp
Pipeline completo: parse -> LLM -> validação -> export
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from parser import parsear_arquivo
from llm import extract
from validator import validar_output


def processar_arquivo(caminho: str, provider: str, aliases_path: str, limit: int = 0) -> dict:
    """Processa um arquivo de export."""
    blocos = parsear_arquivo(caminho)

    if limit > 0:
        blocos = blocos[:limit]

    if not blocos:
        return {"items": [], "suggested_rule_updates": {"produto_aliases_to_add": []}}

    todos_items = []
    todas_sugestoes = []

    for i, bloco in enumerate(blocos, 1):
        print(f"  Bloco {i}/{len(blocos)}...")
        try:
            resultado = extract(bloco.texto, provider, aliases_path)

            if "items" in resultado:
                # Preenche driver/data do parser em cada item
                for item in resultado["items"]:
                    if not item.get("driver") and bloco.driver:
                        item["driver"] = bloco.driver
                    if not item.get("data_entrega") and bloco.data_entrega:
                        item["data_entrega"] = bloco.data_entrega
                todos_items.extend(resultado["items"])

            if "suggested_rule_updates" in resultado:
                sugestoes = resultado["suggested_rule_updates"].get("produto_aliases_to_add", [])
                todas_sugestoes.extend(sugestoes)
        except Exception as e:
            print(f"  ERRO no bloco {i}: {e}")

    return {
        "items": todos_items,
        "suggested_rule_updates": {
            "produto_aliases_to_add": todas_sugestoes
        }
    }


def exportar_csv(items: list, caminho: str):
    """Exporta items para CSV."""
    if not items:
        return

    campos = [
        "id_pedido_item", "id_sale_delivery", "produto", "quantidade",
        "endereco_1", "endereco_2", "driver", "data_entrega", "observacoes"
    ]

    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()
        for item in items:
            # Converte observacoes para string
            item_copy = item.copy()
            if item_copy.get("observacoes"):
                item_copy["observacoes"] = "; ".join(item_copy["observacoes"])
            writer.writerow(item_copy)


def atualizar_aliases(sugestoes: list, aliases_path: str):
    """Adiciona novas sugestões ao arquivo de aliases."""
    aliases_existentes = []

    if Path(aliases_path).exists():
        with open(aliases_path, 'r', encoding='utf-8') as f:
            aliases_existentes = json.load(f)

    # Pega aliases já conhecidos
    aliases_conhecidos = {a["alias"] for a in aliases_existentes}

    # Adiciona apenas novos
    novos = [s for s in sugestoes if s["alias"] not in aliases_conhecidos]

    if novos:
        aliases_existentes.extend(novos)
        with open(aliases_path, 'w', encoding='utf-8') as f:
            json.dump(aliases_existentes, f, indent=2, ensure_ascii=False)
        print(f"\n{len(novos)} novas sugestões de aliases adicionadas!")
        for s in novos:
            print(f"  - {s['alias']} => {s['canonical']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GrowBot - Extrator de Entregas WhatsApp")
    parser.add_argument("--provider", choices=["claude", "openai"], default="claude",
                        help="LLM provider (default: claude)")
    parser.add_argument("--input", default="exports",
                        help="Pasta com arquivos .txt (default: exports)")
    parser.add_argument("--output", default="output",
                        help="Pasta para salvar resultados (default: output)")
    parser.add_argument("--aliases", default="aliases.json",
                        help="Arquivo de aliases (default: aliases.json)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limitar número de blocos (0 = todos)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    # Lista arquivos .txt
    arquivos = list(input_dir.glob("*.txt"))
    if not arquivos:
        print(f"Nenhum arquivo .txt encontrado em {input_dir}/")
        print("Cole seus exports do WhatsApp na pasta exports/")
        sys.exit(1)

    print(f"Processando {len(arquivos)} arquivo(s) com {args.provider}...\n")

    todos_items = []
    todas_sugestoes = []

    for arquivo in arquivos:
        print(f"Arquivo: {arquivo.name}")
        resultado = processar_arquivo(str(arquivo), args.provider, args.aliases, args.limit)
        todos_items.extend(resultado["items"])
        todas_sugestoes.extend(resultado["suggested_rule_updates"]["produto_aliases_to_add"])

    # Valida output
    output_completo = {"items": todos_items}
    erros, output_validado = validar_output(output_completo)

    if erros:
        print(f"\nValidação: {len(erros)} campos corrigidos")

    # Gera timestamp para output
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Exporta JSON
    json_path = output_dir / f"entregas_{args.provider}_{ts}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_validado, f, indent=2, ensure_ascii=False)
    print(f"\nJSON salvo: {json_path}")

    # Exporta CSV
    csv_path = output_dir / f"entregas_{args.provider}_{ts}.csv"
    exportar_csv(output_validado["items"], str(csv_path))
    print(f"CSV salvo: {csv_path}")

    # Atualiza aliases
    if todas_sugestoes:
        atualizar_aliases(todas_sugestoes, args.aliases)

    print(f"\nTotal: {len(todos_items)} itens extraídos")


if __name__ == "__main__":
    main()
