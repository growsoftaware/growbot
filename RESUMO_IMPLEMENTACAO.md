# Resumo: Sistema de Revisão - GrowBot

**Branch:** `review-system`
**Data:** 01/01/2026
**Status:** Fase 1 concluída, pronto para merge

---

## Objetivo

Substituir o conceito de "dúvidas" por um sistema estruturado de **comentários de revisão** que captura:
- Problemas detectados automaticamente (AI)
- Observações manuais (humano)
- Decisões tomadas
- Status de resolução

---

## Decisões de Design (SME/PO)

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| `review_issue` vs `review_ai_notes` | Manter separados | Propósitos distintos: resumo buscável vs contexto detalhado |
| `review_source` | Não adicionar | Overengineering, inferível de `arquivo_origem` |
| `review_detected_at` | Não adicionar | Workflow síncrono, um timestamp (`reviewed_at`) basta |
| Categorias | 2: `tecnico`/`negocio` | Regra clara: humano errou → negocio, sistema errou → tecnico |

---

## Escopo Planejado vs Executado

### FAZER (Fase 1) ✅

| Item | Status | Commit |
|------|--------|--------|
| Adicionar 8 colunas em `db.py` | ✅ Feito | `23abe7e` |
| Migração para bancos existentes | ✅ Feito | `23abe7e` |
| View `v_review_pendentes` | ✅ Feito | `23abe7e` |
| View `v_review_stats` | ✅ Feito | `23abe7e` |
| Métodos `review_pendentes()` e `review_stats()` | ✅ Feito | `23abe7e` |
| CLI `review-pendentes` e `review-stats` | ✅ Feito | `23abe7e` |
| Documentar em `CLAUDE.md` | ✅ Feito | `490e3f2` |
| Commits bem estruturados | ✅ Feito | 4 commits |

### NÃO FAZER (Próximas fases) ⏳

| Item | Fase |
|------|------|
| Modificar `/validar` para preencher review_* | Fase 2 |
| Modificar `/auditar` para preencher review_* | Fase 2 |
| Modificar `/importar` para preencher review_* | Fase 2 |
| Criar tabela `review_comments` separada | Futuro (se necessário) |
| Backfill de dados antigos | Não planejado |
| Integrar com TUI | Fase 3 |

---

## Schema Implementado

```sql
-- 8 colunas adicionadas à tabela movimentos
ALTER TABLE movimentos ADD COLUMN review_severity VARCHAR;    -- critico/atencao/info
ALTER TABLE movimentos ADD COLUMN review_category VARCHAR;    -- tecnico/negocio
ALTER TABLE movimentos ADD COLUMN review_status VARCHAR;      -- ok/pendente/resolvido/ignorado
ALTER TABLE movimentos ADD COLUMN review_issue TEXT;          -- O QUÊ aconteceu (curto)
ALTER TABLE movimentos ADD COLUMN review_ai_notes TEXT;       -- CONTEXTO do AI (detalhado)
ALTER TABLE movimentos ADD COLUMN review_human_notes TEXT;    -- Comentários do operador
ALTER TABLE movimentos ADD COLUMN review_decision TEXT;       -- Decisão final
ALTER TABLE movimentos ADD COLUMN reviewed_at TIMESTAMP;      -- Última atualização
```

---

## Views Criadas

### `v_review_pendentes`
Itens com `review_status = 'pendente'` ordenados por severidade:
1. critico
2. atencao
3. info

### `v_review_stats`
Estatísticas agrupadas por `review_status`, `review_severity`, `review_category`.

---

## Commits Realizados

```
848bfb6 chore(db): migrate existing database with review columns
da201cd docs: add review system planning documents
490e3f2 docs: add review system documentation to CLAUDE.md
23abe7e feat(db): add review system schema with 8 columns and views
```

---

## Como Testar

```bash
cd /home/ndr/growapps/growbot-review-system
source venv/bin/activate

# Verificar colunas
python db.py query "DESCRIBE movimentos" | grep review

# Testar views
python db.py review-pendentes
python db.py review-stats

# Query direta
python db.py query "SELECT COUNT(*) FROM movimentos WHERE review_status IS NULL"
```

---

## Workflow de Status

```
NULL ─────────┬──────────────► ok (passou de primeira)
              │
              └──────────────► pendente (problema detectado)
                                    │
                                    ├──► resolvido (corrigido)
                                    │
                                    └──► ignorado (não requer ação)
```

---

## Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `db.py` | +132 linhas (schema, migration, views, métodos, CLI) |
| `CLAUDE.md` | +62 linhas (documentação do sistema) |
| `PLAN_SISTEMA_REVISAO.md` | Novo (documento de design) |
| `PROMPT_IMPLEMENTACAO.md` | Novo (instruções de implementação) |
| `growbot.duckdb` | Migrado (8 colunas adicionadas) |

---

## Próximos Passos (Fase 2)

1. Modificar `/validar` para preencher campos de review automaticamente
2. Modificar `/auditar` para registrar discrepâncias
3. Modificar `/importar` para detectar problemas
4. Criar TUI para gerenciar itens pendentes

---

## Referências

- `PLAN_SISTEMA_REVISAO.md` - Design completo
- `PROMPT_IMPLEMENTACAO.md` - Instruções da fase 1
- `CLAUDE.md` - Documentação atualizada
