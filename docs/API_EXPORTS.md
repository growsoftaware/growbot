# API de Exports - GrowBot

Endpoints para acessar arquivos de export do WhatsApp via API REST.

## Base URL

```
http://localhost:8001/api
```

## Endpoints

### 1. Listar Arquivos Disponíveis

```http
GET /api/exports
```

**Response:**
```json
{
  "exports": [
    {
      "filename": "_chat.txt",
      "size_bytes": 208973,
      "size_kb": 204.07,
      "total_lines": 4440,
      "modified": "2026-01-02T03:18:00"
    },
    {
      "filename": "export_31122025_RODRIGO.txt",
      "size_bytes": 8422,
      "size_kb": 8.22,
      "total_lines": 180,
      "modified": "2026-01-02T02:23:00"
    }
  ],
  "subfolders": [
    {"folder": "missing", "file_count": 3},
    {"folder": "backup_20260102", "file_count": 5}
  ],
  "total_files": 9
}
```

---

### 2. Buscar Linhas por Range

```http
GET /api/exports/{filename}?linha_inicial={start}&linha_final={end}
```

**Parâmetros:**

| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `filename` | path | - | Nome do arquivo (ex: `_chat.txt`) |
| `linha_inicial` | query | 1 | Primeira linha (1-indexed) |
| `linha_final` | query | auto | Última linha (inclusive) |
| `max_lines` | query | 500 | Limite de segurança (máx 5000) |

**Exemplo:**
```http
GET /api/exports/_chat.txt?linha_inicial=3550&linha_final=3560
```

**Response:**
```json
{
  "filename": "_chat.txt",
  "lines": [
    {"line_number": 3550, "content": "[2026-01-01, 3:17:56 AM] Akita: Location: ..."},
    {"line_number": 3551, "content": "[2026-01-01, 3:17:56 AM] Akita: Passou algar..."},
    {"line_number": 3552, "content": "[2026-01-01, 3:17:56 AM] Akita: 10g gold"}
  ],
  "metadata": {
    "total_lines_file": 4440,
    "linha_inicial": 3550,
    "linha_final": 3560,
    "lines_returned": 11,
    "has_more": true
  }
}
```

---

### 3. Buscar Texto no Arquivo

```http
GET /api/exports/{filename}/search?query={texto}
```

**Parâmetros:**

| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `filename` | path | - | Nome do arquivo |
| `query` | query | - | Texto a buscar (case-insensitive) |
| `context_lines` | query | 2 | Linhas de contexto antes/depois |
| `max_results` | query | 50 | Limite de resultados (máx 200) |

**Exemplo:**
```http
GET /api/exports/_chat.txt/search?query=RODRIGO&context_lines=3
```

**Response:**
```json
{
  "filename": "_chat.txt",
  "query": "RODRIGO",
  "total_matches": 15,
  "truncated": false,
  "matches": [
    {
      "line_number": 99,
      "content": "21/12/2025 00:49 - Padrim: Rodrigo sábado",
      "context_before": [
        {"line_number": 96, "content": "..."},
        {"line_number": 97, "content": "..."},
        {"line_number": 98, "content": "..."}
      ],
      "context_after": [
        {"line_number": 100, "content": "..."},
        {"line_number": 101, "content": "..."},
        {"line_number": 102, "content": "..."}
      ]
    }
  ]
}
```

---

## Exemplos de Uso

### JavaScript/Fetch

```javascript
// Listar arquivos
const exports = await fetch('/api/exports').then(r => r.json());

// Buscar linhas 100-150
const lines = await fetch('/api/exports/_chat.txt?linha_inicial=100&linha_final=150')
  .then(r => r.json());

// Buscar por texto
const search = await fetch('/api/exports/_chat.txt/search?query=prensado')
  .then(r => r.json());
```

### Python

```python
import requests

BASE_URL = "http://localhost:8001/api"

# Listar arquivos
exports = requests.get(f"{BASE_URL}/exports").json()

# Buscar linhas
lines = requests.get(f"{BASE_URL}/exports/_chat.txt", params={
    "linha_inicial": 3550,
    "linha_final": 3600
}).json()

# Buscar texto
search = requests.get(f"{BASE_URL}/exports/_chat.txt/search", params={
    "query": "RODRIGO",
    "context_lines": 3
}).json()
```

### cURL

```bash
# Listar arquivos
curl http://localhost:8001/api/exports

# Buscar linhas
curl "http://localhost:8001/api/exports/_chat.txt?linha_inicial=3550&linha_final=3560"

# Buscar texto
curl "http://localhost:8001/api/exports/_chat.txt/search?query=RODRIGO"
```

---

## Casos de Uso no Frontend

### Visualizar Bloco Raw de uma Entrega

Dado um movimento do banco com `observacao` contendo o texto raw, buscar o contexto original:

```javascript
// 1. Extrair trecho do texto para busca
const searchText = movimento.observacao.split('\n')[0].substring(0, 30);

// 2. Buscar no arquivo original
const result = await fetch(
  `/api/exports/_chat.txt/search?query=${encodeURIComponent(searchText)}&context_lines=5`
).then(r => r.json());

// 3. Mostrar linhas com contexto
const match = result.matches[0];
console.log(`Encontrado na linha ${match.line_number}`);
```

### Paginação de Arquivo Grande

```javascript
const PAGE_SIZE = 100;
let currentPage = 0;

async function loadPage(page) {
  const start = page * PAGE_SIZE + 1;
  const end = start + PAGE_SIZE - 1;

  const data = await fetch(
    `/api/exports/_chat.txt?linha_inicial=${start}&linha_final=${end}`
  ).then(r => r.json());

  return data;
}

// Carregar próxima página
const page1 = await loadPage(0);
if (page1.metadata.has_more) {
  const page2 = await loadPage(1);
}
```

---

## Erros

| Status | Descrição |
|--------|-----------|
| 400 | `linha_inicial` maior que total de linhas |
| 404 | Arquivo não encontrado |
| 500 | Erro ao ler arquivo |

---

## Notas

- Linhas são 1-indexed (primeira linha = 1)
- Busca é case-insensitive
- Arquivos em subpastas (`missing/`, `backup_*/`) também são acessíveis
- Limite de segurança de 5000 linhas por request
