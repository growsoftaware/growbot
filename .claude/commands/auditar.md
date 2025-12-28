---
allowed-tools: Read, Glob, Grep
description: Auditar output vs raw export para encontrar inconsistências
---

Auditar a validação comparando raw export com JSON validado.

Leia o CLAUDE.md do projeto para entender o contexto completo.

## Arquivos
- Raw: exports/_chat.txt
- Output: output/entregas_validadas.json
- Log: logs/validacao_*.md

## Regras de Quantidade
- Sem unidade = unidades
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
```

## Processo de Auditoria
1. Ler amostras do raw export (início, meio, fim de cada sessão)
2. Comparar com os itens correspondentes no JSON
3. Verificar:
   - Produtos estão corretos (incluindo aliases)
   - Quantidades seguem as regras
   - Endereços foram capturados
   - Não há itens faltando ou duplicados incorretos

## Output
Liste TODAS as incongruências encontradas:

### Erros Críticos
- Produtos errados
- Quantidades erradas
- Itens faltando

### Avisos
- Endereços incompletos
- Referências ambíguas

Seja crítico - questione tudo. O objetivo é encontrar erros, não confirmar acertos.
