---
allowed-tools: Read, Write, Glob, Grep
description: Validar export do WhatsApp bloco a bloco
argument-hint: [arquivo.txt]
---

Validar o export em $ARGUMENTS:

Leia o CLAUDE.md do projeto para entender o contexto completo.

## Regras de Quantidade
- Sem unidade = unidades (ex: "4 abacaxi" = 4)
- 1g = 1 unidade
- Xg = X unidades (g COLADO ao número: "5g de arizona" = 5 arizona)
- "X g de" = X unidades (g SEPARADO: "5 g de gold" = 5 gold, NÃO confundir com produto)
- Prensado: 20g=1, 40g=2, 60g=3
- "de 60/70" = preço, não quantidade

**CUIDADO**: "1 gelo khalifa" = 1x ice khalifa (o "g" faz parte do produto, não é grama!)

## Aliases Conhecidos
```
pren, prensa, massa, peso → prensado
dry suíço, suíço, dry milano → dry
ice kalifa, gelo khalifa → ice khalifa
colomba → colombia
exportaaa, expor, 99, exports, exportação → exporta
afeghan, afghan → afghan
marga rosa → manga rosa
piteira bem bolado → piteira
gelo nugg, nugg → ice nugg
marmita, .marmita → prensado
bubba kush → bubba
sower haze → sower
```

## IMPORTANTE: texto_raw
O campo `texto_raw` deve conter EXATAMENTE o texto do arquivo original, sem nenhuma modificação.
Copiar as linhas do arquivo byte por byte, incluindo timestamps e o marcador 🏎️.

## Processo
1. Ler arquivo linha por linha, **mantendo contador de linhas** (1-indexed)
2. Identificar blocos por 🏎️N (conteúdo vem ANTES do emoji)
   - **Anotar linha de início** de cada bloco (primeira linha com conteúdo)
   - **Capturar texto_raw** completo do bloco (incluindo timestamps e 🏎️)
3. Extrair produtos, quantidades, endereços
4. Identificar footer (driver + data) que se aplica a todas as entregas acima
5. **Extrair nome do arquivo** do path (ex: `exports/_chat.txt` → `_chat.txt`)
6. Apresentar tabela para confirmação do usuário
7. Salvar em output/entregas_validadas.json
8. Atualizar logs/validacao_YYYY-MM-DD.md

## Output JSON
```json
{
  "items": [
    {
      "id_sale_delivery": "001",
      "produto": "prensado",
      "quantidade": 1,
      "endereco_1": "Rua X, 123",
      "driver": "RODRIGO",
      "data_entrega": "25/12/2025",
      "texto_raw": "[26/12/25, 00:50:56] Akita: 1 prensado\n[26/12/25, 00:50:57] Akita: 🏎️1",
      "linha_origem": 301,
      "arquivo_origem": "_chat.txt",
      "review_status": "ok",
      "review_severity": null,
      "review_category": null,
      "review_issue": null,
      "review_ai_notes": null
    }
  ]
}
```

## Campos de Rastreabilidade (OBRIGATÓRIO)

| Campo | Descrição |
|-------|-----------|
| `texto_raw` | Texto EXATO do bloco no arquivo original (com timestamps e 🏎️) |
| `linha_origem` | Número da linha onde o bloco COMEÇA no arquivo |
| `arquivo_origem` | Nome do arquivo fonte (ex: `_chat.txt`) |

Esses campos são essenciais para:
- Rastrear a origem de cada entrega
- Permitir auditoria raw vs JSON
- Popular a tabela `blocos_raw` no banco de dados

## Campos de Review (OBRIGATÓRIO)

Cada item DEVE ter campos de review preenchidos:

| Campo | Quando usar |
|-------|-------------|
| `review_status` | **SEMPRE**: `ok` (sem problemas), `pendente` (dúvida), `ignorado` (não é entrega) |
| `review_severity` | Se problema: `critico`, `atencao`, `info` |
| `review_category` | Se problema: `tecnico` (parse errado), `negocio` (dado ambíguo) |
| `review_issue` | Resumo curto do problema |
| `review_ai_notes` | Contexto detalhado da decisão do AI |

### Exemplos de uso:

**Bloco normal (sem problemas):**
```json
{
  "review_status": "ok",
  "review_severity": null,
  "review_category": null,
  "review_issue": null,
  "review_ai_notes": null
}
```

**Bloco ignorado (não é entrega):**
```json
{
  "review_status": "ignorado",
  "review_severity": "info",
  "review_category": "negocio",
  "review_issue": "Bloco sem produto - instrução operacional",
  "review_ai_notes": "Texto 'Deixar moeda' não contém produto/quantidade. Usuário confirmou ignorar."
}
```

**Bloco com dúvida (precisa revisão):**
```json
{
  "review_status": "pendente",
  "review_severity": "atencao",
  "review_category": "negocio",
  "review_issue": "Quantidade ambígua - 'Q dry'",
  "review_ai_notes": "Texto 'Q dry' pode significar 1 dry ou quantidade específica. Interpretado como 1."
}
```

Drivers válidos: RAFA, FRANCIS, RODRIGO, KAROL, ARTHUR
