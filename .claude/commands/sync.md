---
allowed-tools: Bash, Read
description: Sincronizar dados JSON com banco DuckDB
argument-hint: [--force para reimportar tudo]
---

Sincronizar dados com DuckDB: $ARGUMENTS

Execute o sync do banco de dados e mostre o resultado.

## Comando

```bash
source venv/bin/activate && python db.py sync $ARGUMENTS
```

## Opções

- Sem argumentos: importa apenas arquivos novos
- `--force`: reimporta todos os arquivos (recria o banco)

## Após o sync

Mostre os saldos atualizados:

```bash
source venv/bin/activate && python db.py saldo
```

E alertas de produtos negativos:

```bash
source venv/bin/activate && python db.py negativos
```

## Queries Disponíveis

Após o sync, o usuário pode consultar:

```bash
python db.py saldo           # Saldo por driver
python db.py saldo RODRIGO   # Saldo de um driver
python db.py negativos       # Produtos com saldo negativo
python db.py stats           # Estatísticas gerais
python db.py query "SQL"     # Query livre
```

## Views Disponíveis

- `v_saldo_driver` - Estoque + Recargas - Saídas = Saldo
- `v_saldo_produto` - Saldo por produto por driver
- `v_produtos_negativos` - Alertas de inconsistência
- `v_movimentos_dia` - Resumo diário por tipo/driver
- `v_review_pendentes` - Blocos pendentes de revisão
- `v_review_stats` - Estatísticas de revisão

## Tabelas

O sync popula duas tabelas principais:

- `blocos_raw` - Texto original do WhatsApp (1 por entrega) + campos de review
- `movimentos` - Itens parseados (N por entrega, 1 por produto)
