# Schema: Import Log

Log de cada import processado, com anotações de problemas e dúvidas.

## Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| import_id | string | ✅ | ID único do import (timestamp_arquivo) |
| import_type | string | ✅ | Tipo: `entregas`, `recargas`, `estoque`, `misto` |
| source_file | string | ✅ | Arquivo original processado |
| date_import | string | ✅ | Data/hora do processamento |
| driver | string | ❌ | Driver principal (se único) ou `MISTO` |
| total_blocks | number | ✅ | Total de blocos encontrados |
| blocks_ok | number | ✅ | Blocos parseados sem problemas |
| blocks_with_issues | number | ✅ | Blocos com problemas/dúvidas |
| issues | array | ✅ | Lista de problemas encontrados |
| comments | string | ❌ | Comentários gerais do import |

## Estrutura de Issue

| Campo | Tipo | Descrição |
|-------|------|-----------|
| block_id | string | ID do bloco afetado |
| line_number | number | Linha no arquivo original |
| issue_type | string | `missing_date`, `missing_driver`, `ambiguous_product`, `parse_error` |
| severity | string | `critical`, `warning`, `info` |
| description | string | Descrição do problema |
| fallback_used | string | Valor usado como fallback (ex: data do timestamp) |
| needs_review | boolean | Se precisa revisão manual |

## Output

**Arquivo:** `imports/logs/import_YYYYMMDD_HHMMSS_arquivo.json`

```json
{
  "import_id": "20260102_153000_akita",
  "import_type": "entregas",
  "source_file": "exports/missing/akita.txt",
  "date_import": "2026-01-02T15:30:00",
  "driver": "MISTO",
  "total_blocks": 1178,
  "blocks_ok": 178,
  "blocks_with_issues": 1000,
  "issues": [
    {
      "block_id": "001",
      "line_number": 686,
      "issue_type": "missing_date",
      "severity": "warning",
      "description": "Data não encontrada no rodapé",
      "fallback_used": "10/12/2025 (timestamp)",
      "needs_review": false
    }
  ],
  "comments": "Arquivo com rodapés fragmentados em múltiplas linhas"
}
```

## Estrutura de Pastas

```
imports/
├── raw/          # Arquivos originais copiados
├── logs/         # Logs de cada import
└── parsed/       # JSONs parseados (antes da validação)
```
