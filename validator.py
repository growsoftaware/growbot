#!/usr/bin/env python3
"""
Validador de output do extrator.
Garante que dados estão no formato correto.
"""

import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


DRIVERS_ENUM = {"RAFA", "FRANCIS", "RODRIGO", "KAROL", "ARTHUR"}


@dataclass
class Erro:
    item_idx: int
    campo: str
    valor: str
    motivo: str


def validar_driver(driver: Optional[str]) -> Optional[str]:
    """Valida se driver está no ENUM."""
    if driver is None:
        return None
    driver_upper = driver.upper()
    if driver_upper in DRIVERS_ENUM:
        return None
    return f"Driver '{driver}' não está no ENUM: {DRIVERS_ENUM}"


def validar_id_sale_delivery(id_sd: Optional[str]) -> Optional[str]:
    """Valida se id_sale_delivery tem 3 dígitos."""
    if id_sd is None:
        return None
    if not re.match(r'^\d{3}$', str(id_sd)):
        return f"id_sale_delivery '{id_sd}' deve ter exatamente 3 dígitos"
    return None


def validar_data_entrega(data: Optional[str]) -> Optional[str]:
    """Valida se data_entrega está no formato DD/MM/YYYY."""
    if data is None:
        return None
    if not re.match(r'^\d{2}/\d{2}/\d{4}$', data):
        return f"data_entrega '{data}' deve estar no formato DD/MM/YYYY"
    return None


def validar_item(item: dict, idx: int) -> list[Erro]:
    """Valida um item e retorna lista de erros."""
    erros = []

    # Valida driver
    erro = validar_driver(item.get("driver"))
    if erro:
        erros.append(Erro(idx, "driver", str(item.get("driver")), erro))

    # Valida id_sale_delivery
    erro = validar_id_sale_delivery(item.get("id_sale_delivery"))
    if erro:
        erros.append(Erro(idx, "id_sale_delivery", str(item.get("id_sale_delivery")), erro))

    # Valida data_entrega
    erro = validar_data_entrega(item.get("data_entrega"))
    if erro:
        erros.append(Erro(idx, "data_entrega", str(item.get("data_entrega")), erro))

    return erros


def validar_output(data: dict) -> tuple[list[Erro], dict]:
    """
    Valida todo o output e corrige campos inválidos.
    Retorna (erros, data_corrigido).
    """
    erros = []
    items = data.get("items", [])

    for idx, item in enumerate(items):
        item_erros = validar_item(item, idx)
        erros.extend(item_erros)

        # Corrige campos inválidos
        for erro in item_erros:
            # Marca como null e adiciona observação
            item[erro.campo] = None
            obs = item.get("observacoes", []) or []
            obs.append(f"[VALIDADOR] {erro.motivo}")
            item["observacoes"] = obs

    return erros, data


def main():
    if len(sys.argv) < 2:
        print("Uso: python validator.py <arquivo.json>")
        sys.exit(1)

    caminho = sys.argv[1]
    if not Path(caminho).exists():
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)

    with open(caminho, 'r', encoding='utf-8') as f:
        data = json.load(f)

    erros, data_corrigido = validar_output(data)

    if erros:
        print(f"Encontrados {len(erros)} erros:\n")
        for erro in erros:
            print(f"  Item {erro.item_idx}: {erro.campo} = {erro.valor}")
            print(f"    -> {erro.motivo}\n")

        # Salva versão corrigida
        output_path = caminho.replace('.json', '_validado.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_corrigido, f, indent=2, ensure_ascii=False)
        print(f"Versão corrigida salva em: {output_path}")
    else:
        print("OK - Nenhum erro encontrado!")


if __name__ == "__main__":
    main()
