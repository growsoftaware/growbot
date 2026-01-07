# Plano de Execução - Pendências de Saídas

## IMPORTANTE: Arquivos de Export

⚠️ **`_chat.txt` e `_chat_2.txt` são exports do MESMO chat em momentos diferentes!**

| Arquivo | Até quando | Usar? |
|---------|------------|-------|
| `_chat.txt` | 02/01/2026 | ❌ NÃO - versão antiga |
| `_chat_2.txt` | 03/01/2026 | ✅ SIM - versão mais recente |

**Usar APENAS `_chat_2.txt` para evitar duplicidades.**

---

## Resumo Executivo

| Status | Quantidade |
|--------|------------|
| **Processados** | 9 sessões (RODRIGO 22-31/12, ARTHUR 31/12) |
| **Pendentes** | 32 sessões |
| **Prioridade Crítica** | 11 sessões (01/01-03/01) |
| **Prioridade Alta** | 14 sessões |
| **Prioridade Média** | 7 sessões |

## Drivers por Data - Estado Atual

```
         | 21/12 | 22/12 | 26/12 | 27/12 | 28/12 | 29/12 | 30/12 | 31/12 | 01/01 | 02/01 | 03/01 |
---------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
RODRIGO  |   P   |   ✓   |   ✓   |   ✓   |   ✓   |   ✓   |   P   |   ✓   |   P   |   P   |   P   |
ARTHUR   |   P   |   P   |   P   |   -   |   P   |   P   |   P   |   ✓   |   P   |   P   |   P   |
KAROL    |   P   |   P   |   P   |   P   |   P   |   P   |   P   |   P   |   P   |   -   |   P   |
FRANCIS  |   P   |   P   |   -   |   -   |   -   |   -   |   P   |   P   |   P   |   P   |   P   |
```

Legenda: ✓ = Processado | P = Pendente | - = Não tem dados

---

## Fase 1: Prioridade CRÍTICA (01/01 - 03/01/2026)

Dados mais recentes que precisam entrar no sistema urgentemente.

### Lote 1.1 - 01/01/2026 (Quarta-feira)
| # | Driver | Arquivo | Linhas | Blocos | Comando |
|---|--------|---------|--------|--------|---------|
| 1 | RODRIGO | _chat_2.txt | 6169-6454 | 52 | `sed -n '6169,6454p' exports/_chat_2.txt` |
| 2 | KAROL | _chat_2.txt | 6459-6650 | 24 | `sed -n '6459,6650p' exports/_chat_2.txt` |
| 3 | FRANCIS | _chat_2.txt | 6655-6897 | 25 | `sed -n '6655,6897p' exports/_chat_2.txt` |
| 4 | ARTHUR | _chat_2.txt | 6942-7194 | 39 | `sed -n '6942,7194p' exports/_chat_2.txt` |

### Lote 1.2 - 02/01/2026 (Quinta-feira)
| # | Driver | Arquivo | Linhas | Blocos | Comando |
|---|--------|---------|--------|--------|---------|
| 5 | RODRIGO | _chat_2.txt | 7267-7408 | 27 | `sed -n '7267,7408p' exports/_chat_2.txt` |
| 6 | ARTHUR | _chat_2.txt | 7411-7544 | 26 | `sed -n '7411,7544p' exports/_chat_2.txt` |
| 7 | FRANCIS | _chat_2.txt | 7611-7769 | 34 | `sed -n '7611,7769p' exports/_chat_2.txt` |

### Lote 1.3 - 03/01/2026 (Sexta-feira)
| # | Driver | Arquivo | Linhas | Blocos | Comando |
|---|--------|---------|--------|--------|---------|
| 8 | RODRIGO | _chat_2.txt | 7912-8051 | 27 | `sed -n '7912,8051p' exports/_chat_2.txt` |
| 9 | FRANCIS | _chat_2.txt | 8088-8222 | 27 | `sed -n '8088,8222p' exports/_chat_2.txt` |
| 10 | KAROL | _chat_2.txt | 8225-8372 | 29 | `sed -n '8225,8372p' exports/_chat_2.txt` |
| 11 | ARTHUR | _chat_2.txt | 8405-8536 | 21 | `sed -n '8405,8536p' exports/_chat_2.txt` |

**Checkpoint:** Após Fase 1, executar `/sync` e verificar relatório.

---

## Fase 2: Prioridade ALTA (30/12 - Arquivos Individuais)

Arquivos separados por driver - mais fáceis de processar.

### Lote 2.1 - 30/12/2025 (Terça)
| # | Driver | Arquivo | Blocos | Comando |
|---|--------|---------|--------|---------|
| 12 | RODRIGO | export_30122025_RODRIGO.txt | 29 | `/validar exports/export_30122025_RODRIGO.txt` |
| 13 | ARTHUR | export_30122025_ARTHUR.txt | 26 | `/validar exports/export_30122025_ARTHUR.txt` |
| 14 | FRANCIS | export_30122025_FRANCIS.txt | 26 | `/validar exports/export_30122025_FRANCIS.txt` |
| 15 | KAROL | export_30122025_KAROL.txt | 13 | `/validar exports/export_30122025_KAROL.txt` |

### Lote 2.2 - 31/12/2025 (Pendentes)
| # | Driver | Arquivo | Blocos | Notas |
|---|--------|---------|--------|-------|
| 16 | FRANCIS | export_31122025_FRANCIS.txt | 25 | `/validar exports/export_31122025_FRANCIS.txt` |
| 17 | KAROL | export_31122025_KAROL.txt | 1 | ⚠️ **INCOMPLETO!** Verificar origem |

**Checkpoint:** Após Fase 2, executar `/sync` e `/auditar`.

---

## Fase 3: Prioridade ALTA (21-22/12/2025 - Histórico)

Dados do primeiro fim de semana mapeado.

### Lote 3.1 - 21/12/2025 (Sábado)
| # | Driver | Arquivo | Linhas | Blocos | Comando |
|---|--------|---------|--------|--------|---------|
| 18 | RODRIGO | _chat_2.txt | 12-104 | 43 | `sed -n '12,104p' exports/_chat_2.txt` |
| 19 | ARTHUR | _chat_2.txt | 109-182 | 34 | `sed -n '109,182p' exports/_chat_2.txt` |
| 20 | KAROL | _chat_2.txt | 185-258 | 34 | `sed -n '185,258p' exports/_chat_2.txt` |
| 21 | FRANCIS | _chat_2.txt | 261-304 | 22 | `sed -n '261,304p' exports/_chat_2.txt` |

### Lote 3.2 - 22/12/2025 (Outros drivers)
| # | Driver | Arquivo | Linhas | Blocos | Comando |
|---|--------|---------|--------|--------|---------|
| 22 | KAROL | _chat_2.txt | 408-466 | 24 | `sed -n '408,466p' exports/_chat_2.txt` |
| 23 | ARTHUR | _chat_2.txt | 469-520 | 24 | `sed -n '469,520p' exports/_chat_2.txt` |
| 24 | FRANCIS | _chat_2.txt | 523-579 | 23 | `sed -n '523,579p' exports/_chat_2.txt` |

**Checkpoint:** Após Fase 3, executar `/sync`.

---

## Fase 4: Prioridade MÉDIA (26-29/12)

### Lote 4.1 - 26/12/2025 (Quinta)
| # | Driver | Linhas | Blocos | Notas |
|---|--------|--------|--------|-------|
| 25 | ARTHUR | 822-914 | 32 | Sessão completa |
| 26 | KAROL | 1016-1083 | 11 | Sessão incompleta |

### Lote 4.2 - 27/12/2025 (Sexta/Sábado)
| # | Driver | Linhas | Blocos | Notas |
|---|--------|--------|--------|-------|
| 27 | KAROL | 1712-1838 | 27 | Sexta |
| 28 | KAROL | 2312-2509 | 12 | Sábado - 12 entregas |

### Lote 4.3 - 28/12/2025 (Sábado/Domingo)
| # | Driver | Linhas | Blocos | Notas |
|---|--------|--------|--------|-------|
| 29 | ARTHUR | 2512-2664 | 39 | Sábado |
| 30 | ARTHUR | 3136-3307 | 34 | Domingo |
| 31 | KAROL | 3383-3496 | 21 | Domingo |

### Lote 4.4 - 29/12/2025 (Segunda)
| # | Driver | Linhas | Blocos | Notas |
|---|--------|--------|--------|-------|
| 32 | ARTHUR | 3997-4163 | 39 | Sessão completa |
| 33 | KAROL | 4234-4362 | 24 | Sessão completa |

**Checkpoint Final:** Após Fase 4, executar:
```bash
/sync --force
/auditar
/relatorio totais
```

---

## Instruções de Execução

### Antes de Começar
1. Fazer backup do banco: `cp growbot.duckdb growbot.duckdb.bak`
2. Verificar estado atual: `/relatorio totais`

### Para Extrair Blocos do _chat_2.txt
```bash
# Exemplo: extrair RODRIGO 01/01/2026
sed -n '6169,6454p' exports/_chat_2.txt > exports/temp_rodrigo_01jan.txt

# Validar o bloco extraído
/validar exports/temp_rodrigo_01jan.txt
```

### Verificação de Qualidade
Após cada lote:
```bash
# Verificar negativos
python db.py negativos

# Estatísticas
python db.py stats

# Relatório completo
/relatorio totais
```

---

## Alertas e Observações

### Arquivo Problemático
⚠️ **export_31122025_KAROL.txt** - Arquivo com apenas 5 linhas! Menciona "24 corridas" mas só tem 1 bloco.
- Verificar se os dados completos estão em `_chat_2.txt`
- Linhas 6459-6650 têm KAROL 01/01, mas não achei 31/12

### Arquivos Redundantes
- `_chat.txt` (4440 linhas) - **NÃO USAR** - versão antiga
- `_chat_2.txt` (17085 linhas) - **USAR ESTE** - versão completa

---

## Estimativa de Volume

| Período | Sessões | Blocos Estimados |
|---------|---------|------------------|
| Fase 1 (01-03/01) | 11 | ~312 |
| Fase 2 (30-31/12) | 6 | ~120 |
| Fase 3 (21-22/12) | 7 | ~204 |
| Fase 4 (26-29/12) | 9 | ~219 |
| **TOTAL** | **33** | **~855 blocos** |

---

*Arquivo gerado em: 06/01/2026*
*CSV associado: `output/pendencias_saidas.csv`*
