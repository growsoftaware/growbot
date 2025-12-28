# Schema: Resgate (Transferência entre Drivers)

Registro de transferência de produtos entre drivers. Um driver "resgata" produto de outro.

## Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| driver_origem | string | ✅ | Driver que está cedendo o produto |
| driver_destino | string | ✅ | Driver que está recebendo o produto |
| produto | string | ✅ | Nome do produto normalizado |
| quantidade | number | ✅ | Quantidade transferida |
| data_resgate | string | ✅ | DD/MM/YYYY - quando aconteceu |
| motivo | string | ❌ | Por que foi transferido |

## Output

**Arquivo:** `output/resgate_YYYYMMDD.json`

```json
{
  "tipo": "resgate",
  "data_import": "2025-12-27",
  "items": [
    {
      "driver_origem": "RODRIGO",
      "driver_destino": "KAROL",
      "produto": "prensado",
      "quantidade": 10,
      "data_resgate": "27/12/2025",
      "motivo": "acabou estoque da Karol"
    },
    {
      "driver_origem": "ARTHUR",
      "driver_destino": "FRANCIS",
      "produto": "arizona",
      "quantidade": 5,
      "data_resgate": "27/12/2025",
      "motivo": null
    }
  ],
  "resumo": {
    "total_transferencias": 2,
    "total_unidades": 15,
    "saldo_por_driver": {
      "RODRIGO": -10,
      "KAROL": +10,
      "ARTHUR": -5,
      "FRANCIS": +5
    }
  }
}
```

## Exemplo de Input (WhatsApp)

```
Resgate 27/12:
- Karol pegou 10 prensado do Rodrigo (acabou estoque)
- Francis pegou 5 arizona do Arthur
```

Ou formato alternativo:
```
Rodrigo passou pra Karol:
- 10 prensado

Arthur passou pra Francis:
- 5 arizona
```

## Impacto no Estoque

Cada resgate é uma transferência:
```
estoque[driver_origem][produto] -= quantidade
estoque[driver_destino][produto] += quantidade
```

## Validações

1. Ambos drivers devem estar na lista válida
2. driver_origem ≠ driver_destino
3. Quantidade deve ser > 0
4. Produto deve existir no estoque do driver_origem
5. Quantidade não pode exceder estoque disponível do driver_origem

## Aliases para Parsing

Palavras que indicam resgate:
- "pegou de", "pegou do"
- "passou pra", "passou para"
- "transferiu", "transferência"
- "resgatou", "resgate"
- "cedeu", "deu"
