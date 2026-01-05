# GrowBot Sync - Integração de Dados

## Visão Geral

O módulo `growbot_sync` é responsável por importar dados do sistema GrowBot (processamento de mensagens WhatsApp) para o Grow (ERP).

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GrowBot (DuckDB)                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │ blocos_raw  │───▶│ movimentos  │───▶│   API       │                      │
│  │ (mensagens) │    │ (validados) │    │ :8001       │                      │
│  └─────────────┘    └─────────────┘    └─────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              │ HTTP GET /api/movimentos/export
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Grow (PostgreSQL)                              │
│  ┌─────────────────┐    ┌──────────────────────────────────────────────┐   │
│  │ growbot_        │    │              Entidades Grow                   │   │
│  │ movimentos      │───▶│  ┌───────┐  ┌──────────────┐  ┌───────────┐  │   │
│  │ (staging)       │    │  │ Sales │  │StockTransfer │  │ CheckIn   │  │   │
│  └─────────────────┘    │  └───────┘  └──────────────┘  └───────────┘  │   │
│        ▲                └──────────────────────────────────────────────┘   │
│        │                                                                    │
│  ┌─────────────────┐                                                        │
│  │  API :8000      │                                                        │
│  │ /api/v1/growbot │                                                        │
│  └─────────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados

### 1. Fetch (GrowBot → growbot_movimentos)

**Endpoint:** `POST /api/v1/growbot/fetch`

**Request:**
```json
{
  "driver_name": "RODRIGO",      // opcional
  "data_inicio": "2025-12-22",
  "data_fim": "2025-12-22",
  "tipo": "entrega"              // opcional
}
```

**Processo:**
1. Grow chama GrowBot API: `GET http://localhost:8001/api/movimentos/export`
2. Para cada movimento recebido:
   - Verifica se já existe pelo `growbot_id`
   - Se existe: atualiza campos
   - Se não existe: cria novo registro
3. Executa auto-match de driver e product
4. Salva na tabela `growbot_movimentos`

**Código:** `service.py:143-243` (`fetch_from_growbot`)

### 2. Auto-Match

Durante o fetch, o sistema tenta fazer match automático:

**Driver Match:**
- Compara `movimento.driver_name` com `Driver.name` (case-insensitive)
- Se encontrar: preenche `movimento.driver_id`

**Product Match:**
- Compara `movimento.produto_original` com:
  1. `Product.name` (exact)
  2. `Product.nickname` (exact)
  3. Nicknames em `ProductQuantityPrice`
- Se encontrar: preenche `movimento.product_id` e `movimento.unit_id`

**Código:** `service.py:245-340` (`_auto_match`, `_match_product`)

### 3. Import (growbot_movimentos → Entidades Grow)

**Endpoint:** `POST /api/v1/growbot/import`

**Request:**
```json
{
  "movimento_ids": [1, 2, 3],
  "skip_with_errors": true
}
```

**Mapeamento por Tipo:**

| tipo GrowBot | Entidade Grow              | Descrição                         |
|--------------|----------------------------|-----------------------------------|
| `entrega`    | Sale + SaleItem + Delivery | Venda para cliente                |
| `recarga`    | StockTransfer              | Transferência estoque → motorista |
| `estoque`    | DriverStockCheckIn         | Check-in de estoque do motorista  |

**Detalhes do Import:**

#### entrega → Sale

```python
Sale(
    customer_name=movimento.endereco[:50] or "-",
    customer_address=movimento.endereco,
    sale_date=movimento.data_movimento,
    status="delivered",
    external_reference=movimento.id_sale_delivery,  # 🏎️001, 🏎️002...
    original_message=movimento.texto_raw,           # Mensagem original WhatsApp
)
```

#### recarga → StockTransfer

```python
StockTransfer(
    from_warehouse="main",
    to_driver_id=movimento.driver_id,
    product_id=movimento.product_id,
    quantity=movimento.quantidade,
    transfer_date=movimento.data_movimento,
)
```

#### estoque → DriverStockCheckIn

```python
DriverStockCheckIn(
    driver_id=movimento.driver_id,
    product_id=movimento.product_id,
    reported_quantity=movimento.quantidade,
    expected_quantity=movimento.quantidade,
    period_start=movimento.data_movimento,
)
```

**Código:** `service.py:776-870` (`_import_single`)

## Tipos de Movimento (ENUM)

| Tipo              | Descrição                  | Import Para   |
|-------------------|----------------------------|---------------|
| `entrega`         | Venda/entrega para cliente | Sale          |
| `recarga`         | Motorista retira estoque   | StockTransfer |
| `estoque`         | Conferência de estoque     | CheckIn       |
| `resgate_saida`   | (futuro)                   | -             |
| `resgate_entrada` | (futuro)                   | -             |

## Endpoints Disponíveis

| Método | Endpoint                      | Descrição                     |
|--------|-------------------------------|-------------------------------|
| GET    | `/growbot/matriz`             | Grid motoristas × datas       |
| GET    | `/growbot/movimentos`         | Listar movimentos             |
| GET    | `/growbot/movimentos/{id}`    | Detalhe movimento             |
| POST   | `/growbot/fetch`              | Buscar do GrowBot             |
| PATCH  | `/growbot/movimentos/{id}`    | Atualizar movimento           |
| POST   | `/growbot/import`             | Importar para Grow            |
| POST   | `/growbot/rematch`            | Re-executar match de produtos |
| POST   | `/growbot/reset-import`       | Resetar status de import      |
| POST   | `/growbot/recalculate-prices` | Recalcular preços             |

## Campos Importantes

### growbot_movimentos

| Campo                | Descrição                           |
|----------------------|-------------------------------------|
| `growbot_id`         | ID original no GrowBot              |
| `tipo`               | entrega, recarga, estoque           |
| `driver_name`        | Nome do motorista (texto)           |
| `driver_id`          | FK para drivers (após match)        |
| `produto_original`   | Nome do produto (texto)             |
| `product_id`         | FK para products (após match)       |
| `id_sale_delivery`   | Referência da corrida (🏎️001)       |
| `texto_raw`          | Mensagem original do WhatsApp       |
| `import_status`      | pending, imported, skipped, error   |
| `imported_entity_type` | sale, transfer, checkin           |
| `imported_entity_id` | ID da entidade criada               |

## Arquivos do Módulo (Grow)

```
app/modules/growbot_sync/
├── __init__.py
├── interface.py      # Exports públicos
├── models.py         # GrowBotMovimento model
├── router.py         # API endpoints
├── schemas.py        # Pydantic schemas
└── service.py        # Business logic
```

## GrowBot API Endpoints

API disponível em `http://localhost:8001`

### Listar Arquivos de Export

```http
GET /api/exports
```

### Buscar Linhas de Arquivo

```http
GET /api/exports/{filename}?linha_inicial=1&linha_final=100
```

### Exportar Movimentos

```http
GET /api/movimentos/export?driver=RODRIGO&data_inicio=22/12/2025&data_fim=22/12/2025
```

**Response:**
```json
{
  "total": 52,
  "movimentos": [
    {
      "id": 7234,
      "tipo": "entrega",
      "driver": "RODRIGO",
      "produto": "super lemon",
      "quantidade": 5,
      "data_movimento": "2025-12-22",
      "id_sale_delivery": "001",
      "texto_raw": "22/12/2025 02:26 - Padrim: 5g de super lemon\n...",
      "review_status": "ok"
    }
  ]
}
```

## Troubleshooting

### Produtos não fazem match

1. Verificar se o produto existe em `Product.name` ou `Product.nickname`
2. Usar endpoint `/growbot/rematch` para re-executar
3. Adicionar nickname no Grow se necessário

### Duplicação de registros

1. Verificar `growbot_id` - deve ser único
2. Checar se o JOIN inclui `driver` além de `id_sale_delivery` e `data`

### Texto raw não aparece

1. Verificar se `blocos_raw` foi populado no GrowBot
2. Checar JOIN: `b.driver = m.driver` é obrigatório
