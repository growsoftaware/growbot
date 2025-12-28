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
- Xg = X unidades
- Prensado: 20g=1, 40g=2, 60g=3
- "de 60/70" = preço, não quantidade

## Aliases Conhecidos
```
pren, prensa, massa, peso → prensado
dry suíço, suíço, dry milano → dry
ice kalifa → ice khalifa
colomba → colombia
exportaaa, expor, 99 → exporta
afeghan, afghan → afghan
marga rosa → manga rosa
piteira bem bolado → piteira
gelo nugg → ice nug
```

## Processo
1. Ler arquivo linha por linha
2. Identificar blocos por 🏎️N (conteúdo vem ANTES do emoji)
3. Extrair produtos, quantidades, endereços
4. Identificar footer (driver + data) que se aplica a todas as entregas acima
5. Apresentar tabela para confirmação do usuário
6. Salvar em output/entregas_validadas.json
7. Atualizar logs/validacao_YYYY-MM-DD.md

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
      "data_entrega": "25/12/2025"
    }
  ]
}
```

Drivers válidos: RAFA, FRANCIS, RODRIGO, KAROL, ARTHUR
