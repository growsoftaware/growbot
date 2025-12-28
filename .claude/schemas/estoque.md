# Schema: Estoque por Driver

Registro de estoque atual de cada driver.

## Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| driver | string | ✅ | RAFA, FRANCIS, RODRIGO, KAROL, ARTHUR |
| produto | string | ✅ | Nome do produto normalizado |
| quantidade | number | ✅ | Quantidade em unidades |
| data_registro | string | ✅ | DD/MM/YYYY - quando foi registrado |

## Output

**Arquivo:** `output/estoque_YYYYMMDD.json`

```json
{
  "tipo": "estoque",
  "data_import": "2025-12-27",
  "items": [
    {
      "driver": "RODRIGO",
      "produto": "prensado",
      "quantidade": 100,
      "data_registro": "27/12/2025"
    },
    {
      "driver": "RODRIGO",
      "produto": "arizona",
      "quantidade": 50,
      "data_registro": "27/12/2025"
    },
    {
      "driver": "KAROL",
      "produto": "prensado",
      "quantidade": 80,
      "data_registro": "27/12/2025"
    }
  ],
  "resumo": {
    "total_drivers": 2,
    "total_produtos": 3,
    "total_unidades": 230
  }
}
```

## Exemplo de Input (WhatsApp)

```
Estoque Rodrigo 27/12:
- 100 prensado
- 50 arizona
- 30 marmita

Estoque Karol 27/12:
- 80 prensado
- 40 escama
```

## Validações

1. Driver deve estar na lista válida
2. Quantidade deve ser >= 0
3. Produto deve ser normalizado (usar aliases)
4. Data deve ser válida
