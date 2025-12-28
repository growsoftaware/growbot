# GrowBot

Extrator de entregas a partir de exports do WhatsApp. Usa LLM (Claude/OpenAI) para interpretar pedidos e exporta CSV estruturado.

## Quick Start

```bash
# Setup
cd /Users/andremaciel/dev/growbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar API keys
cp .env.example .env
# Editar .env com suas keys

# Colar export do WhatsApp
# Salvar como exports/arquivo.txt

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

- `output/entregas_claude_YYYYMMDD_HHMMSS.json`
- `output/entregas_claude_YYYYMMDD_HHMMSS.csv`

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
| main.py | Pipeline completo |
| parser.py | Separa blocos por 🏎️ |
| llm.py | Wrapper Claude/OpenAI |
| validator.py | Valida output |
| aliases.json | Dicionário de produtos |
| system_prompt.md | Prompt do extrator |
