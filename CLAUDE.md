# GrowBot - Contexto para Claude

## O que é este projeto
Sou um agente exportador que ajuda o André a processar exports de conversas do WhatsApp contendo pedidos de entregas. Meu trabalho é parsear, validar e exportar esses dados de forma estruturada.

## Fluxo de trabalho
```
exports/*.txt → Parser → LLM (Claude/OpenAI) → Validador → output/*.json
```

## Estrutura do projeto
```
growbot/
├── .claude/           # Configuração Claude Code
│   ├── agents/        # Agents especializados (validador, auditor, etc)
│   ├── commands/      # Slash commands (/validar, /sync, etc)
│   ├── schemas/       # Schemas de dados (estoque, recarga, resgate)
│   └── skills/        # Skills reutilizáveis
├── docs/              # Documentação e planos
├── exports/           # Colar arquivos .txt do WhatsApp aqui (gitignore)
├── output/            # JSONs gerados (entregas, estoque, recarga, resgate)
├── growbot.duckdb     # Banco de dados analítico (DuckDB)
├── aliases.json       # Dicionário de produtos (aprendizado contínuo)
├── main.py            # CLI principal - orquestra tudo
├── parser.py          # Pré-processador determinístico
├── llm.py             # Wrapper Claude/OpenAI
├── validator.py       # Validação de output
├── db.py              # Banco de dados DuckDB
├── ui.py              # Interface terminal (Rich) - legado
├── tui.py             # Dashboard TUI (Textual) - principal
├── api.py             # FastAPI (UI futura)
└── system_prompt.md   # Prompt do extrator
```

## Como funciona o Parser (parser.py)

### Formato de entrada
```
[26/12/25, 00:50:56] Akita: 4 abacaxi e 3 escama
[26/12/25, 00:50:57] Akita: 🏎️2
...
[26/12/25, 00:51:09] Akita: Rodrigo
Quinta
```

### Regras importantes
1. **Marcador 🏎️N** = fecha um bloco de entrega (ID = N com 3 dígitos)
2. **Linha sem [timestamp]** = continua pertencendo ao bloco anterior
3. **Rodapé (driver + data)** = aplica a TODAS as entregas anteriores da sessão
4. **Nova sessão** = quando aparece novo driver, IDs reiniciam
5. **"Francisco"** ≠ "FRANCIS" (usar word boundary no regex)

### Drivers válidos (ENUM)
RAFA, FRANCIS, RODRIGO, KAROL, ARTHUR

### Detecção de data
- DD/MM/YYYY, DD/MM/YY, DD/MM
- "DD do MM" (ex: 26 do 12)
- Dia da semana (segunda...domingo) → calcula relativo ao timestamp

## Como funciona o LLM (llm.py)

### O que o LLM faz
- Extrai produtos/quantidades de frases humanas ("me vê 20g de pren")
- Separa múltiplos produtos ("4 abacaxi e 3 escama" → 2 itens)
- Detecta endereços
- Sugere novos aliases para o dicionário

### O que o Parser faz (não precisa de LLM)
- Separar blocos por 🏎️
- Detectar driver/data do rodapé
- Aplicar driver/data a todos os blocos da sessão

## Comandos úteis

```bash
# Ativar ambiente
source venv/bin/activate

# Testar parser
python parser.py exports/_chat.txt

# Processar com Claude
python main.py --provider claude --limit 10

# Processar com OpenAI
python main.py --provider openai --limit 10

# Processar tudo
python main.py --provider claude
```

## Output esperado (JSON)
```json
{
  "items": [
    {
      "id_sale_delivery": "001",
      "produto": "prensado",
      "quantidade": 1,
      "endereco_1": "",
      "driver": "RODRIGO",
      "data_entrega": "25/12/2025"
    }
  ]
}
```
Arquivo: `output/entregas_validadas.json`

## Aprendizado (aliases.json)
O LLM sugere novos aliases quando encontra variantes:
- "pren" → "prensado"
- "dry suíço" → "dry"
- "ice kalifa" → "ice khalifa"

Revisar e aprovar antes de usar na próxima execução.

## Regras de Quantidade (IMPORTANTE)
- **Sem unidade** = quantidade em unidades (ex: "4 abacaxi" = 4)
- **1g** = 1 unidade (ex: "1g meleca" = 1)
- **Xg** = X unidades (ex: "5g arizona" = 5)
- **Prensado 20g / marmita** = 1 unidade de "prensado"
- **50g pren comercial** = 1 unidade de "marmita comercial" (produto diferente!)

⚠️ **prensado** e **marmita comercial** são produtos DIFERENTES:
- `prensado` = 20g (marmita normal)
- `marmita comercial` = 50g (peso maior)

Sempre validar com o André quando aparecer unidade de medida diferente.

## Normalização de Produtos

Produtos canônicos (usar sempre estes nomes):

| Canônico | Aliases |
|----------|---------|
| afeghan | afghan, afegan, afeganian |
| bubba | bubaa, bubba kush |
| bruce | bruce banner |
| cogumelo | cogu |
| dry | dry milano, dry suíço, suíço |
| elon musk | bala elon musk |
| escama | escam, escaminha |
| exporta | export, exportação, 99, expor |
| ice khalifa | ice kalifa, kalifa, gelo khalifa |
| ice nugg | ice nug, nug, nugg, gelo nugg |
| kieef | kief |
| manga rosa | manga, marga rosa |
| marmita | marmitw, marmira |
| md | MD |
| prensado | pren, prensa, massa, peso, prensadin |
| sower | sower haze |
| super lemon | super lemos |

Ver lista completa em `aliases.json`.

## Comandos Claude CLI

```bash
# Validar export interativamente
/validar exports/_chat.txt

# Auditar output vs raw
/auditar

# Comparar duas versões
/comparar output/v1.json output/v2.json

# Gerar relatório
/relatorio totais
/relatorio driver RODRIGO
/relatorio produto
/relatorio periodo 26/12/2025

# Importar novos tipos de dados
/importar estoque arquivo.txt
/importar recarga arquivo.txt
/importar resgate arquivo.txt

# Sincronizar dados com DuckDB
/sync
/sync --force
```

## Banco de Dados (DuckDB)

Após `/sync`, consultas analíticas instantâneas:

```bash
python db.py saldo           # Saldo por driver
python db.py saldo RODRIGO   # Saldo de um driver
python db.py negativos       # Produtos com saldo negativo (alertas)
python db.py stats           # Estatísticas gerais
python db.py query "SELECT * FROM v_saldo_produto WHERE driver='RODRIGO'"
```

### Views disponíveis
- `v_saldo_driver` - Estoque + Recargas - Saídas = Saldo
- `v_saldo_produto` - Saldo por produto por driver
- `v_produtos_negativos` - Alertas de inconsistência
- `v_movimentos_dia` - Resumo diário por tipo/driver

## Dashboard TUI

Dashboard interativo no terminal com duas visões.

```bash
python tui.py
```

### Visões
- **DASHBOARD** (padrão) - Tabela de movimentos por driver/produto/data
- **CARDS** - Cards diários agrupados por driver

### Funcionalidades DASHBOARD
- Tabela com drivers expansíveis (Enter para ver produtos)
- Colunas por data: 📸 Estoque | 📦 Recarga | 🏎️ Saída
- Coluna 💰 TOTAL com saldo calculado (Estoque + Recarga - Saída)
- Ordenação por clique no header (▲/▼)
- KPIs: Entregas, Retiradas, Negativos, Tot.Ret, Tot.Del
- KPIs extras ao filtrar driver: Estoque, Saldo
- Painel de detalhes ao selecionar produto (Enter)
- Auto-expande produtos ao filtrar por driver específico

### Funcionalidades CARDS
- Cards por dia/driver com resumo de entregas e recargas
- Seções colapsáveis para ver detalhes

### Filtros
- Data início/fim (DD/MM/YYYY)
- Driver (TODOS ou específico)
- Resumo dos filtros + legenda visível no topo

### Atalhos de Teclado
| Tecla | Ação |
|-------|------|
| `q` | Sair |
| `r` | Atualizar dados |
| `f` | Toggle painel de filtros |
| `1` | Visão Dashboard |
| `2` | Visão Cards |
| `z/x` | Driver anterior/próximo |
| `w/e` | Data início −/+ |
| `s/d` | Data fim −/+ |
| `Enter` | Expandir driver / Ver detalhes produto |

## Agents Disponíveis
- **validador** - Processa exports bloco a bloco
- **auditor** - Verifica qualidade (raw vs JSON)
- **relatorios** - Gera métricas e análises
- **importador** - Parser inteligente para novos formatos

## Tipos de Dados

### entregas (atual)
Pedidos de entrega validados do WhatsApp.
```
Output: output/entregas_validadas.json
Campos: id_sale_delivery, produto, quantidade, endereco_1, driver, data_entrega
```

### estoque
Estoque atual de cada driver.
```
Output: output/estoque_YYYYMMDD.json
Campos: driver, produto, quantidade, data_registro
```

### recarga
Produtos retirados do estoque central para o driver entregar.
```
Output: output/recarga_YYYYMMDD_DRIVER.json
Campos: driver, produto, quantidade, data_recarga, observacao
```

### resgate
Transferência de produtos entre drivers (um "resgata" do outro).
```
Output: output/resgate_YYYYMMDD.json
Campos: driver_origem, driver_destino, produto, quantidade, data_resgate, motivo
```

Ver schemas completos em `.claude/schemas/`

## Próximos passos sugeridos
1. [ ] UI web (FastAPI + React/shadcn) para comparar outputs
2. [ ] Detecção de endereços no parser (antes do LLM)
3. [ ] Batch processing para arquivos grandes
4. [ ] Exportar relatórios do TUI para PDF/Excel
5. [ ] Gráficos de tendência no Dashboard
