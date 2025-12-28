---
name: growbot
description: Sistema de extração e validação de entregas a partir de exports do WhatsApp. Use quando o usuário mencionar validar, exports, entregas, WhatsApp, drivers, produtos.
allowed-tools: Read, Write, Glob, Grep
---

# GrowBot - Extrator de Entregas WhatsApp

## O que é
Sistema para processar exports de conversas do WhatsApp contendo pedidos de entregas, gerando JSON/CSV estruturado.

## Fluxo
```
exports/*.txt → Parser → Validação → output/*.json
```

## Regras de Quantidade
- Sem unidade = unidades (ex: "4 abacaxi" = 4)
- 1g = 1 unidade (ex: "1g meleca" = 1)
- Xg = X unidades (ex: "5g arizona" = 5)
- **Prensado especial: 20g = 1, 40g = 2, 60g = 3**
- "de 60/70" = preço, não quantidade

## Aliases de Produtos
```
pren, prensa, massa, peso → prensado
dry suíço, suíço, dry milano → dry
ice kalifa → ice khalifa
colomba → colombia
exportaaa, expor, 99 → exporta
afeghan, afghan → afghan
marga rosa → manga rosa
piteira bem bolado → piteira
gelo nugg → ice nug
```

## Estrutura do Export
- Blocos terminam com 🏎️N (conteúdo vem ANTES do emoji)
- Linha sem [timestamp] = continua bloco anterior
- Footer (driver + data) aplica a TODAS as entregas acima
- Nova sessão = quando aparece novo driver

## Drivers Válidos
RAFA, FRANCIS, RODRIGO, KAROL, ARTHUR

## Comandos Disponíveis
- `/validar [arquivo]` - Validação interativa
- `/auditar` - Comparar raw vs JSON
- `/comparar [v1] [v2]` - Diff entre versões
- `/relatorio [tipo]` - Métricas
- `/importar [tipo] [arquivo]` - Novos tipos de dados
- `/sync [--force]` - Sincronizar dados com DuckDB

## Banco de Dados (DuckDB)

Após `/sync`, consultas instantâneas via:

```bash
python db.py saldo           # Saldo por driver
python db.py saldo RODRIGO   # Saldo de um driver
python db.py negativos       # Produtos negativos (alertas)
python db.py stats           # Estatísticas
python db.py query "SQL"     # Query livre
```

Views prontas:
- `v_saldo_driver` - Estoque + Recargas - Saídas
- `v_saldo_produto` - Por produto/driver
- `v_produtos_negativos` - Alertas
- `v_movimentos_dia` - Resumo diário

## Ícones Padrão (Relatórios)

| Ícone | Tipo | Descrição |
|-------|------|-----------|
| 📸 | Estoque | Foto do inventário |
| 📦 | Recarga | Box/entrada do central |
| 🏎️ | Entrega | Delivery/saída |
| 💰 | Saldo | Total final |

## Arquivos Importantes
- `exports/` - Arquivos .txt do WhatsApp
- `output/` - JSONs de entregas, estoque, recarga, resgate
- `growbot.duckdb` - Banco de dados analítico
- `aliases.json` - Dicionário de produtos
- `logs/` - Logs de validação
