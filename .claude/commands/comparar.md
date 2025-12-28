---
allowed-tools: Read, Glob, Grep
description: Comparar duas versões de output JSON
argument-hint: [arquivo1.json] [arquivo2.json]
---

Comparar dois arquivos JSON de entregas validadas: $ARGUMENTS

## Processo
1. Ler ambos os arquivos JSON
2. Identificar diferenças:
   - Itens adicionados
   - Itens removidos
   - Itens modificados (produto, quantidade, endereço)
3. Agrupar por tipo de mudança

## Output
```
## Adicionados (N itens)
- 🏎️XX DRIVER DD/MM: produto quantidade

## Removidos (N itens)
- 🏎️XX DRIVER DD/MM: produto quantidade

## Modificados (N itens)
- 🏎️XX DRIVER DD/MM:
  - produto: valor_antigo → valor_novo
  - quantidade: valor_antigo → valor_novo
```

## Métricas
- Total itens v1: X
- Total itens v2: Y
- Diferença: +/-Z
