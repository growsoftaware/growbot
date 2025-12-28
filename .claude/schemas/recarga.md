# Schema: Recarga por Driver

Registro de produtos retirados do estoque central para o driver entregar.

> **Nota:** "retirada" é sinônimo de "recarga" - usar sempre "recarga" como padrão

## Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| driver | string | ✅ | RAFA, FRANCIS, RODRIGO, KAROL, ARTHUR |
| produto | string | ✅ | Nome do produto normalizado |
| quantidade | number | ✅ | Quantidade retirada |
| data_recarga | string | ✅ | DD/MM/YYYY - quando retirou |
| observacao | string | ❌ | Notas adicionais |

## Output

**Arquivo:** `output/recarga_YYYYMMDD_DRIVER.json`

```json
{
  "tipo": "recarga",
  "data_import": "2025-12-27",
  "items": [
    {
      "driver": "RODRIGO",
      "produto": "prensado",
      "quantidade": 50,
      "data_recarga": "27/12/2025",
      "observacao": null
    },
    {
      "driver": "RODRIGO",
      "produto": "arizona",
      "quantidade": 30,
      "data_recarga": "27/12/2025",
      "observacao": "pra festa do bairro"
    },
    {
      "driver": "KAROL",
      "produto": "marmita",
      "quantidade": 20,
      "data_recarga": "27/12/2025",
      "observacao": null
    }
  ],
  "resumo": {
    "total_produtos": 3,
    "total_unidades": 100
  }
}
```

## Exemplo de Input (WhatsApp)

```
Rodrigo retirou 27/12:
- 50 prensado
- 30 arizona (pra festa do bairro)

Karol retirou 27/12:
- 20 marmita
```

## Impacto no Estoque

Cada retirada deve ser subtraída do estoque central:
```
estoque_central[produto] -= quantidade_retirada
```

## Validações

1. Driver deve estar na lista válida
2. Quantidade deve ser > 0
3. Produto deve existir no estoque
4. Quantidade não pode exceder estoque disponível
