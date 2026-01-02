# Sistema de Comentários de Revisão - GrowBot

## Objetivo
Substituir o conceito de "dúvidas" por um sistema estruturado de **comentários de revisão** que captura:
- Problemas detectados automaticamente (AI)
- Observações manuais (humano)
- Decisões tomadas
- Status de resolução

## Escopo
- **Granularidade**: Por item individual (nível de linha na tabela `movimentos`)
- **Momentos de captura**: /validar (auto + interativo), /auditar, revisão manual pós-validação
- **Armazenamento**: Colunas adicionais na tabela `movimentos` (sem nova tabela)
- **Histórico**: Só versão atual (sobrescreve em novas revisões)

---

## Proposta de Campos

### Campos de Classificação

**`review_severity`** (VARCHAR, NULLABLE)
- Valores: `'critico'`, `'atencao'`, `'info'`, `NULL`
- Indica gravidade do problema encontrado
- Exemplos:
  - `'critico'`: Endereço faltando, produto desconhecido
  - `'atencao'`: Produto raro/suspeito, quantidade atípica
  - `'info'`: Produto normalizado, alias sugerido

**`review_category`** (VARCHAR, NULLABLE)
- Valores: `'tecnico'`, `'negocio'`, `NULL`
- Tipo de problema (2 categorias apenas - regra simples)
- **Regra:** Se humano escreveu errado → `negocio`. Se sistema interpretou errado → `tecnico`.
- Exemplos:
  - `'tecnico'`: Parser error, bloco malformado, encoding issue, regex falhou
  - `'negocio'`: Produto não existe no catálogo, driver inválido, endereço faltando, quantidade zero

**`review_status`** (VARCHAR, NULLABLE)
- Valores: `'ok'`, `'pendente'`, `'resolvido'`, `'ignorado'`, `NULL`
- Status de tratamento
- Workflow:
  - `NULL`: Item ainda não passou por revisão
  - `'ok'`: Item validado com sucesso, sem problemas detectados (passou de primeira)
  - `'pendente'`: Problema detectado, aguardando resolução
  - `'resolvido'`: Problema detectado e corrigido/confirmado
  - `'ignorado'`: Problema detectado mas não requer ação

### Campos de Conteúdo

**`review_issue`** (TEXT, NULLABLE)
- **O QUÊ aconteceu** - descrição curta e padronizada
- Objetivo: bater o olho e saber o problema
- Buscável via queries (`WHERE review_issue LIKE '%desconhecido%'`)
- Exemplos:
  - `"Produto desconhecido: papel"`
  - `"Endereço ausente"`
  - `"Quantidade zero"`
  - `"Bloco malformado"`

**`review_ai_notes`** (TEXT, NULLABLE)
- **CONTEXTO e análise** - detalhes e sugestões do AI
- Objetivo: entender mais quando necessário
- Livre, pode ser extenso
- Exemplos:
  - `"Sugestão: 'ice' → 'ice khalifa' (85% confiança). Aparece 3x no histórico."`
  - `"Bloco 014 renumerado de 001 para número real do emoji 🏎️14"`
  - `"Produto '2escamas' normalizado para 'escama'. Quantidade extraída: 2."`

**`review_human_notes`** (TEXT, NULLABLE)
- **Comentários adicionados manualmente pelo usuário**
- Observações, contexto de negócio, decisões
- Exemplos:
  - `"Confirmado com driver: produto correto"`
  - `"Cliente cancelou, manter registro mas ignorar"`
  - `"Endereço corrigido via WhatsApp: Rua X, 123"`

**`review_decision`** (TEXT, NULLABLE)
- **Decisão final tomada sobre o item**
- Ação executada ou planejada
- Exemplos:
  - `"Item removido: impossível determinar produto"`
  - `"Mantido como 'flor' sem especificação"`
  - `"Aguardar confirmação do driver"`

### Campos de Controle

**`reviewed_at`** (TIMESTAMP, NULLABLE)
- Timestamp da última revisão
- Atualizado quando qualquer campo `review_*` é modificado
- Permite filtrar itens revisados recentemente

---

## Nomenclatura - Resumo

| Campo | Tipo | Propósito |
|-------|------|-----------|
| `review_severity` | VARCHAR | Gravidade: critico / atencao / info |
| `review_category` | VARCHAR | Tipo: tecnico / negocio |
| `review_status` | VARCHAR | Status: ok / pendente / resolvido / ignorado |
| `review_issue` | TEXT | O QUÊ aconteceu (curto, padronizado) |
| `review_ai_notes` | TEXT | CONTEXTO e análise do AI (detalhado) |
| `review_human_notes` | TEXT | Comentários do operador |
| `review_decision` | TEXT | Decisão final tomada |
| `reviewed_at` | TIMESTAMP | Última atualização |

### Decisões de Design (SME/PO)

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| issue vs ai_notes | Manter separados | Propósitos distintos (resumo vs contexto) |
| review_source | Não adicionar | Overengineering, inferível de arquivo_origem |
| review_detected_at | Não adicionar | Workflow síncrono, um timestamp basta |
| Categorias | 2: tecnico/negocio | Evita ambiguidade, regra clara |

---

## Migração de Dados

### Schema Atual (db.py:30-42)
```sql
CREATE TABLE movimentos (
    id INTEGER PRIMARY KEY,
    tipo VARCHAR NOT NULL,
    driver VARCHAR NOT NULL,
    driver_destino VARCHAR,
    produto VARCHAR NOT NULL,
    quantidade INTEGER NOT NULL,
    data_movimento DATE NOT NULL,
    endereco VARCHAR,
    observacao VARCHAR,
    arquivo_origem VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Schema Proposto (adicionar colunas)
```sql
ALTER TABLE movimentos ADD COLUMN review_severity VARCHAR;
ALTER TABLE movimentos ADD COLUMN review_category VARCHAR;
ALTER TABLE movimentos ADD COLUMN review_status VARCHAR;
ALTER TABLE movimentos ADD COLUMN review_issue TEXT;
ALTER TABLE movimentos ADD COLUMN review_ai_notes TEXT;
ALTER TABLE movimentos ADD COLUMN review_human_notes TEXT;
ALTER TABLE movimentos ADD COLUMN review_decision TEXT;
ALTER TABLE movimentos ADD COLUMN reviewed_at TIMESTAMP;
```

**Notas de migração:**
- Todos os campos são NULLABLE por padrão
- Dados existentes não são afetados (campos ficam NULL)
- Sem necessidade de backfill inicial

---

## Integração com Comandos

### `/validar`

**Automático - Sem problemas (passou de primeira):**
```python
# Item validado com sucesso
if validacao_ok:
    item['review_status'] = 'ok'
    item['reviewed_at'] = datetime.now()
    # Outros campos review_* ficam NULL
```

**Automático - Problema detectado:**
```python
# Durante parsing/validação
if not produto_valido:
    item['review_severity'] = 'critico'
    item['review_category'] = 'negocio'
    item['review_status'] = 'pendente'
    item['review_issue'] = f"Produto '{produto}' não existe no catálogo"
    item['review_ai_notes'] = f"Sugestão: verificar aliases ou adicionar ao dicionário"
    item['reviewed_at'] = datetime.now()
```

**Interativo (prompt ao usuário):**
```
⚠️  Produto 'papel' não reconhecido
    Severidade: critico | Categoria: negocio | Status: pendente

    Opções:
    1. Adicionar comentário
    2. Tomar decisão
    3. Ignorar

Seu comentário: [input do usuário] → salva em review_human_notes
Decisão: [input do usuário] → salva em review_decision
```

### `/auditar`

Ao comparar raw export vs JSON final:
```python
if discrepancia_detectada:
    registro['review_severity'] = 'atencao'
    registro['review_category'] = 'tecnico'
    registro['review_issue'] = 'Divergência entre export e JSON processado'
    registro['review_ai_notes'] = f"Export: '{valor_raw}' | JSON: '{valor_json}'"
```

### `/importar`

Similar ao /validar, detecta problemas durante importação de novos tipos de dados.

---

## Views e Queries Úteis

### Itens que passaram de primeira (sem problemas)
```sql
SELECT driver, produto, quantidade, data_movimento, endereco
FROM movimentos
WHERE review_status = 'ok'
ORDER BY reviewed_at DESC;
```

### Contagem por status de revisão
```sql
SELECT
    review_status,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
FROM movimentos
GROUP BY review_status
ORDER BY total DESC;

-- Resultado exemplo:
-- review_status | total | percentual
-- ok            | 150   | 81.08%
-- pendente      | 20    | 10.81%
-- resolvido     | 10    | 5.41%
-- NULL          | 5     | 2.70%
```

### Ver todos os itens pendentes de revisão
```sql
SELECT * FROM movimentos
WHERE review_status = 'pendente'
ORDER BY
    CASE review_severity
        WHEN 'critico' THEN 1
        WHEN 'atencao' THEN 2
        WHEN 'info' THEN 3
        ELSE 4
    END,
    reviewed_at DESC;
```
**Nota:** Usar CASE para ordenar severidade corretamente (não alfabético).

### Relatório de problemas por categoria
```sql
SELECT
    review_category,
    review_severity,
    COUNT(*) as total,
    COUNT(CASE WHEN review_status = 'pendente' THEN 1 END) as pendentes,
    COUNT(CASE WHEN review_status = 'resolvido' THEN 1 END) as resolvidos
FROM movimentos
WHERE review_issue IS NOT NULL
GROUP BY review_category, review_severity
ORDER BY total DESC;
```

### Itens com comentários humanos
```sql
SELECT driver, produto, quantidade,
       review_status, review_issue, review_human_notes, review_decision
FROM movimentos
WHERE review_human_notes IS NOT NULL
ORDER BY reviewed_at DESC;
```

### Taxa de sucesso por driver (quantos passaram de primeira)
```sql
SELECT
    driver,
    COUNT(*) as total,
    COUNT(CASE WHEN review_status = 'ok' THEN 1 END) as passou_primeira,
    COUNT(CASE WHEN review_status IN ('pendente', 'resolvido') THEN 1 END) as com_problemas,
    ROUND(COUNT(CASE WHEN review_status = 'ok' THEN 1 END) * 100.0 / COUNT(*), 2) as taxa_sucesso_pct
FROM movimentos
WHERE review_status IS NOT NULL  -- Só itens revisados
GROUP BY driver
ORDER BY taxa_sucesso_pct DESC;
```

---

## Vantagens da Abordagem

✅ **Sem nova tabela**: Mantém simplicidade, evita JOINs
✅ **Separação clara**: AI (`review_ai_notes`) vs humano (`review_human_notes`)
✅ **Issue vs Contexto**: `review_issue` (bater olho) vs `review_ai_notes` (detalhar)
✅ **2 categorias simples**: tecnico/negocio com regra clara
✅ **Auditável**: `reviewed_at` permite tracking temporal
✅ **Flexível**: Campos TEXT permitem conteúdo livre
✅ **Incremental**: Pode adicionar campos no futuro se necessário
✅ **Compatível**: Dados antigos continuam funcionando (NULL)
✅ **8 campos apenas**: Evitamos overengineering (sem source, sem detected_at)

---

## Próximos Passos

1. **Implementar migration** (ALTER TABLE em db.py)
2. **Atualizar /validar** para preencher campos de revisão
3. **Atualizar /auditar** para registrar discrepâncias
4. **Criar views** para relatórios de revisão
5. **Atualizar TUI** para exibir status de revisão
6. **Documentar workflow** de revisão manual

---

## Alternativa Futura (se precisar de granularidade)

Se no futuro for necessário histórico completo ou múltiplos comentários por item:

```sql
CREATE TABLE review_comments (
    id INTEGER PRIMARY KEY,
    movimento_id INTEGER REFERENCES movimentos(id),
    severity VARCHAR,
    category VARCHAR,
    comment_type VARCHAR, -- 'ai' ou 'human'
    comment_text TEXT,
    created_by VARCHAR,
    created_at TIMESTAMP
);
```

**Por enquanto NÃO é necessário** - começar simples com colunas na tabela existente.
