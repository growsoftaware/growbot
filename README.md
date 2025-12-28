# GrowBot

Extrator de entregas a partir de exports do WhatsApp. Usa LLM (Claude/OpenAI) para interpretar pedidos e exporta dados estruturados para DuckDB.

## Quick Start

```bash
# Clone e setup
git clone git@github.com:growsoftaware/growbot.git
cd growbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar API keys
cp .env.example .env
# Editar .env com suas keys

# Colar export do WhatsApp em exports/
# Rodar
python main.py --provider claude
```

## Uso

```bash
# Testar com poucos blocos primeiro
python main.py --provider claude --limit 10

# Usar OpenAI
python main.py --provider openai

# Ver parser funcionando
python parser.py exports/_chat.txt
```

## Output

- `output/entregas_validadas.json` - Entregas extraídas
- `output/estoque_YYYYMMDD_DRIVER.json` - Estoque por driver
- `output/recarga_YYYYMMDD_DRIVER.json` - Recargas
- `growbot.duckdb` - Banco analítico

## DuckDB

```bash
python db.py saldo           # Saldo por driver
python db.py saldo RODRIGO   # Saldo de um driver
python db.py negativos       # Produtos com saldo negativo
python db.py stats           # Estatísticas gerais
```

## Claude Code CLI

```bash
/validar exports/_chat.txt   # Validar export interativamente
/auditar                     # Auditar output vs raw
/relatorio totais            # Gerar relatório
/sync                        # Sincronizar com DuckDB
```

## Formato do CSV

| Campo | Descrição |
|-------|-----------|
| id_pedido_item | Sequencial por entrega |
| id_sale_delivery | ID da entrega (3 dígitos) |
| produto | Nome normalizado |
| quantidade | Quantidade |
| endereco_1 | Endereço principal |
| endereco_2 | Complemento/bairro |
| driver | RAFA/FRANCIS/RODRIGO/KAROL/ARTHUR |
| data_entrega | DD/MM/YYYY |

## Arquivos

| Arquivo | Função |
|---------|--------|
| main.py | CLI principal - orquestra tudo |
| parser.py | Separa blocos por 🏎️ |
| llm.py | Wrapper Claude/OpenAI |
| validator.py | Valida output |
| db.py | Banco de dados DuckDB |
| ui.py | Interface terminal (Rich) |
| aliases.json | Dicionário de produtos |
| system_prompt.md | Prompt do extrator |
| .claude/ | Agents, commands e skills |
