# Implementação do Sistema de Comentários de Revisão - GrowBot

## Contexto

Estamos implementando um sistema para capturar comentários de revisão durante /validar, /auditar e /importar. Este sistema substitui o conceito de "dúvidas" por uma estrutura que rastreia:
- Problemas detectados automaticamente (AI)
- Observações manuais (humano)
- Decisões tomadas
- Status de resolução

## Plano de Referência

Ver arquivo `PLAN_SISTEMA_REVISAO.md` nesta worktree - contém todas as decisões de design.

## Campos a Implementar (8 colunas)

```sql
ALTER TABLE movimentos ADD COLUMN review_severity VARCHAR;   -- critico/atencao/info
ALTER TABLE movimentos ADD COLUMN review_category VARCHAR;   -- tecnico/negocio
ALTER TABLE movimentos ADD COLUMN review_status VARCHAR;     -- ok/pendente/resolvido/ignorado
ALTER TABLE movimentos ADD COLUMN review_issue TEXT;         -- O QUÊ aconteceu (curto)
ALTER TABLE movimentos ADD COLUMN review_ai_notes TEXT;      -- CONTEXTO do AI (detalhado)
ALTER TABLE movimentos ADD COLUMN review_human_notes TEXT;   -- Comentários do operador
ALTER TABLE movimentos ADD COLUMN review_decision TEXT;      -- Decisão final
ALTER TABLE movimentos ADD COLUMN reviewed_at TIMESTAMP;     -- Última atualização
```

## Decisões de Design Já Tomadas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| issue vs ai_notes | Separados | issue=resumo buscável, ai_notes=contexto detalhado |
| review_source | Não adicionar | Overengineering, inferível de arquivo_origem |
| review_detected_at | Não adicionar | Workflow síncrono, um timestamp basta |
| Categorias | 2: tecnico/negocio | Regra: humano errou→negocio, sistema errou→tecnico |

## Escopo desta Conversa

### FAZER:
1. **Atualizar db.py** - Adicionar 8 colunas em `_init_schema()`
2. **Criar view** `v_review_pendentes` para itens pendentes
3. **Criar view** `v_review_stats` para estatísticas de revisão
4. **Testar** que colunas foram criadas e queries funcionam
5. **Atualizar CLAUDE.md** com seção sobre sistema de revisão
6. **Commits** bem estruturados na branch review-system

### NÃO FAZER:
- ❌ Modificar /validar, /auditar ou /importar (próxima fase)
- ❌ Criar tabela review_comments (começar simples)
- ❌ Backfill de dados antigos (colunas ficarão NULL)
- ❌ Integrar com TUI (próxima fase)

## Critérios de Sucesso

✅ `db.py` cria as 8 colunas corretamente no schema
✅ Views `v_review_pendentes` e `v_review_stats` funcionando
✅ Queries de exemplo do plano executam sem erro
✅ `CLAUDE.md` documenta novo sistema
✅ 3-4 commits bem estruturados
✅ Pronto para próxima fase: integrar com /validar

## Arquivos Principais

- `db.py` - Schema e views (principal)
- `CLAUDE.md` - Documentação
- `PLAN_SISTEMA_REVISAO.md` - Referência de design
