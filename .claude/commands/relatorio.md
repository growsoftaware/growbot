---
allowed-tools: Read, Glob, Grep, Bash
description: Gerar relatório de métricas (usa DuckDB)
argument-hint: [tipo: movimentos|totais|driver|produto|periodo|negativos]
---

Gerar relatório de métricas: $ARGUMENTS

Use o banco DuckDB para consultas rápidas:
```bash
source venv/bin/activate && python db.py query "SQL"
```

## Ícones Padrão

-  📸  Estoque (foto)
-  📦  Recarga (box)
-  🏎️  Entrega (delivery)
-  💰  Saldo

## Tipos de Relatório

### movimentos (principal)
Movimentação cronológica por driver com colunas por dia/tipo.

```sql
SELECT
    driver,
    SUM(CASE WHEN tipo = 'estoque' AND data_movimento = 'YYYY-MM-DD' THEN quantidade ELSE 0 END) as "📸 DD",
    SUM(CASE WHEN tipo = 'recarga' AND data_movimento = 'YYYY-MM-DD' THEN quantidade ELSE 0 END) as "📦 DD",
    SUM(CASE WHEN tipo = 'entrega' AND data_movimento = 'YYYY-MM-DD' THEN quantidade ELSE 0 END) as "🏎️ DD",
    -- calcular saldo
FROM movimentos GROUP BY driver ORDER BY driver
```

**Output esperado:**

| Driver |  📸 22  |  🏎️ 25  |  📸 26  |  📦 26  |  🏎️ 26  |  📸 27  |  📦 27  |  💰  |
|--------|---------|---------|---------|---------|---------|---------|---------|------|
| ARTHUR | 141 | 52 | - | 174 | 112 | - | 56 | **207** |

---

### totais
Resumo geral de todos os movimentos.

```sql
SELECT tipo, COUNT(*) as qtd, SUM(quantidade) as total FROM movimentos GROUP BY tipo
```

---

### driver [NOME]
Métricas de um driver específico.

```sql
SELECT * FROM v_saldo_driver WHERE driver = 'NOME'
SELECT * FROM v_saldo_produto WHERE driver = 'NOME' ORDER BY saldo DESC
```

---

### produto
Ranking de produtos (todas as movimentações).

```sql
SELECT produto,
    SUM(CASE WHEN tipo IN ('estoque','recarga') THEN quantidade ELSE 0 END) as entradas,
    SUM(CASE WHEN tipo = 'entrega' THEN quantidade ELSE 0 END) as saidas
FROM movimentos GROUP BY produto ORDER BY saidas DESC
```

---

### periodo [DD/MM/YYYY]
Movimentos de uma data específica.

```sql
SELECT * FROM v_movimentos_dia WHERE data_movimento = 'YYYY-MM-DD'
```

---

### negativos
Produtos com saldo negativo (alertas).

```bash
python db.py negativos
```

---

## Legenda Final

Sempre incluir no final do relatório:

```
📸 Estoque (foto)  |  📦 Recarga (box)  |  🏎️ Entrega  |  💰 Saldo
```
