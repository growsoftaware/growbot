---
allowed-tools: Read, Glob, Grep
description: Gerar relatório diário formatado para WhatsApp
argument-hint: [DD/MM/YYYY ou DD/MM]
---

Gerar relatório diário de entregas para: $ARGUMENTS

## Fonte de Dados

Ler o arquivo `output/entregas_validadas.json` e filtrar pela data informada.

Se o argumento for:
- `DD/MM` → assumir ano atual (2025)
- `DD/MM/YYYY` → usar como está
- `hoje` ou vazio → usar data de hoje

## Processamento

1. Filtrar itens por `data_entrega`
2. Agrupar por driver
3. Contar entregas únicas (por `id_sale_delivery`)
4. Somar quantidades por produto
5. Calcular totais gerais

## Formato de Output (WhatsApp)

```
📊 *RESUMO ENTREGAS DD/MM/YYYY*
━━━━━━━━━━━━━━━━━━━━━━━━━━

🏎️ *DRIVER* — X entregas
├ produto1: qtd
├ produto2: qtd
└ produtoN: qtd

[repetir para cada driver]

━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 *TOTAL GERAL*
├ 🚗 XX entregas
├ 📋 XX itens
└ 👥 X drivers

🔝 *TOP 5 PRODUTOS DO DIA*
1. produto — qtd
2. produto — qtd
3. produto — qtd
4. produto — qtd
5. produto — qtd
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Regras de Formatação

1. **Drivers** em ordem alfabética
2. **Produtos** ordenados por quantidade (maior primeiro)
3. Usar caracteres Unicode: `├ └ ━`
4. Negrito com asteriscos: `*texto*`
5. Top 5 considera soma de todos os drivers

## Exemplo de Uso

```
/relatorio-diario 28/12
/relatorio-diario 28/12/2025
/relatorio-diario hoje
```

## Observações

- Se não houver dados para a data, informar "Nenhuma entrega encontrada para DD/MM/YYYY"
- Incluir observações pendentes se houver (ex: produtos para normalizar)
