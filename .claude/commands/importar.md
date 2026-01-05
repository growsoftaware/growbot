---
allowed-tools: Read, Write, Glob, Grep
description: Importar novo tipo de dados (estoque, recarga, resgate)
argument-hint: [tipo] [dados ou arquivo]
---

Importar dados: $ARGUMENTS

Leia os schemas em `.claude/schemas/` para entender cada tipo de dados.
Leia o CLAUDE.md do projeto para contexto geral.

## Tipos Suportados

### entregas
Pedidos de entrega do WhatsApp (use `/validar` em vez de `/importar`).

---

### estoque
Estoque atual de cada driver.

**Campos:** driver, produto, quantidade, data_registro
**Output:** `output/estoque_YYYYMMDD_DRIVER.json`

```json
{
  "tipo": "estoque",
  "import_id": "estoque_20251227_RODRIGO",
  "data_import": "2025-12-27",
  "texto_raw": "[texto original completo]",
  "arquivo_origem": "estoque_20251227_RODRIGO.txt",
  "items": [
    {
      "driver": "RODRIGO",
      "produto": "prensado",
      "quantidade": 100,
      "data_registro": "27/12/2025",
      "id_sale_delivery": "estoque_20251227_RODRIGO"
    }
  ],
  "resumo": {"total_drivers": 1, "total_produtos": 1, "total_unidades": 100}
}
```

**Exemplo de input:**
```
Estoque Rodrigo 27/12:
- 100 prensado
- 50 arizona
```

---

### recarga
Produtos retirados do estoque central para o driver entregar.

**Campos:** driver, produto, quantidade, data_recarga, observacao
**Output:** `output/recarga_YYYYMMDD_DRIVER.json`

```json
{
  "tipo": "recarga",
  "import_id": "recarga_20251227_RODRIGO",
  "data_import": "2025-12-27",
  "texto_raw": "[texto original completo]",
  "arquivo_origem": "recarga_20251227_RODRIGO.txt",
  "items": [
    {
      "driver": "RODRIGO",
      "produto": "prensado",
      "quantidade": 50,
      "data_recarga": "27/12/2025",
      "observacao": null,
      "id_sale_delivery": "recarga_20251227_RODRIGO"
    }
  ],
  "resumo": {"total_recargas": 1, "total_unidades": 50, "por_driver": {"RODRIGO": 50}}
}
```

**Exemplo de input:**
```
Rodrigo recarga 27/12:
- 50 prensado
- 30 arizona
```

---

### resgate
Transferência de produtos entre drivers. Um driver "resgata" produto de outro.

**Campos:** driver_origem, driver_destino, produto, quantidade, data_resgate, motivo
**Output:** `output/resgate_YYYYMMDD.json`

```json
{
  "tipo": "resgate",
  "data_import": "2025-12-27",
  "items": [
    {"driver_origem": "RODRIGO", "driver_destino": "KAROL", "produto": "prensado", "quantidade": 10, "data_resgate": "27/12/2025", "motivo": "acabou estoque"}
  ],
  "resumo": {"total_transferencias": 1, "total_unidades": 10, "saldo_por_driver": {"RODRIGO": -10, "KAROL": 10}}
}
```

**Exemplo de input:**
```
Resgate 27/12:
- Karol pegou 10 prensado do Rodrigo (acabou estoque)
```

**Palavras-chave:** pegou de, passou pra, transferiu, resgatou, cedeu

---

## Processo de Importação

1. **Identificar tipo** - estoque, recarga ou resgate
2. **Detectar fonte** - arquivo existente ou texto colado
3. **Parsear conteúdo**
   - Identificar driver(s)
   - Extrair produtos e quantidades
   - Detectar datas
   - Aplicar aliases de produtos
4. **Validar dados**
   - Driver na lista válida
   - Quantidades positivas
   - Datas válidas
5. **Apresentar para confirmação**
6. **Salvar texto original** em `imports/raw/{tipo}_{YYYYMMDD}_{DRIVER}.txt`
7. **Gerar import_id**: `{tipo}_{YYYYMMDD}_{DRIVER}` (ex: `estoque_20251222_RODRIGO`)
8. **Salvar JSON** em `output/{tipo}_{YYYYMMDD}_{DRIVER}.json` com:
   - `import_id`: ID único para relacionamento
   - `texto_raw`: texto original completo
   - `arquivo_origem`: nome do arquivo salvo
   - `items[].id_sale_delivery`: mesmo import_id (para relacionar com blocos_raw)

## Parser Inteligente

Se o formato não for reconhecido:
1. Analisar estrutura do arquivo
2. Identificar padrões (nomes de drivers, produtos, números)
3. Propor mapeamento de campos
4. Pedir confirmação do usuário
5. Ajustar e processar

## Drivers Válidos
RAFA, FRANCIS, RODRIGO, KAROL, ARTHUR

## Aliases de Produtos
Usar os mesmos aliases do CLAUDE.md:
- pren, prensa, massa, peso → prensado
- dry suíço, suíço → dry
- 99, expor → exporta
