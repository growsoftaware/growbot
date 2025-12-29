# Plan: TUI Visão Tabela (Movimentos por Driver)

## Objetivo
Criar nova visão no TUI em formato tabela com drivers nas linhas e movimentos por data nas colunas.

## Estrutura da Tabela

```
┌──────────┬────────────────────25/12─────────────────┬────────────────────26/12─────────────────┬──────────┐
│  Driver  │  📸    │  📦    │  🏎️   │  💰    │  📸    │  📦    │  🏎️   │  💰    │  💰 TOTAL │
├──────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼───────────┤
│ ▸ RODRIGO│  100   │   50   │   30   │  120   │   -    │   20   │   45   │   95   │    95     │
│   arizona│   20   │   10   │    5   │   25   │   -    │    5   │   10   │   20   │    20     │
│   prensado│  30   │   15   │   10   │   35   │   -    │    8   │   15   │   28   │    28     │
│   ...    │        │        │        │        │        │        │        │        │           │
├──────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼───────────┤
│ ▸ KAROL  │   80   │   30   │   20   │   90   │   -    │   15   │   25   │   80   │    80     │
└──────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┴───────────┘
```

## Funcionalidades

### 1. Layout
- Nova aba/tela no TUI (botão para alternar entre "Cards" e "Tabela")
- Filtros de data (início/fim) mantidos
- Checkboxes para mostrar/ocultar tipos

### 2. Checkboxes de Tipos
```
[x] 📸 Estoque    [x] 📦 Recarga    [x] 🏎️ Saídas
```
- Quando desmarcado: oculta colunas do tipo E recalcula saldo
- Exemplo: desmarcar Recarga → saldo = Estoque - Saídas

### 3. Colunas
- Ordenadas por data (esquerda → direita = mais antiga → mais recente)
- Para cada data: 📸 | 📦 | 🏎️ | 💰 (se tipo habilitado)
- Coluna final: 💰 TOTAL (saldo acumulado geral)

### 4. Linhas - Nível Driver
- Cada driver é uma linha expansível (▸)
- Mostra totais agregados de todos os produtos

### 5. Linhas - Nível Produto (expandido)
- Ao expandir driver (▾): mostra linha por produto
- Mesma estrutura de colunas
- Indentado para indicar hierarquia

### 6. Fórmula Saldo
```
SALDO = ESTOQUE + RECARGA - SAÍDAS
```
- 📸 Estoque: POSITIVO (é a "foto" do inventário)
- 📦 Recarga: POSITIVO (entrada de produtos)
- 🏎️ Saídas: NEGATIVO (entregas, deduz do saldo)

## Arquivos a Modificar

### tui.py
1. Adicionar nova classe `TableView` (widget de tabela)
2. Adicionar classe `DriverRow` (linha expansível)
3. Adicionar classe `ProductRow` (sublinha de produto)
4. Adicionar checkboxes na FilterPanel
5. Adicionar botão/tab para alternar entre Cards e Tabela
6. Implementar lógica de recálculo de saldo baseado nos filtros

### Dados
- Usar DuckDB para consultar movimentos agregados por driver/produto/data/tipo
- Query pivot para montar estrutura de colunas dinâmicas

## Componentes Textual a Usar

- `DataTable` - tabela principal com suporte a expansão
- `Checkbox` - filtros de tipo
- `TabbedContent` ou botões - alternar entre visões
- `Tree` - alternativa para linhas expansíveis (driver → produtos)

## Fluxo de Implementação

1. [x] Adicionar checkboxes de tipo no FilterPanel
2. [x] Criar componente TableView
3. [x] Implementar query de agregação por driver/data/tipo
4. [x] Adicionar expansão para nível produto (Enter na linha)
5. [x] Implementar recálculo de saldo ao toggle de checkboxes
6. [x] Adicionar navegação entre Cards ↔ Tabela (teclas 1/2)
7. [x] Ocultar colunas vazias (sem dados)
8. [x] Saldo apenas na coluna final (removido saldo por data)

## Tipos de Movimento no DuckDB

| Tipo DB | Ícone | Efeito no Saldo |
|---------|-------|-----------------|
| estoque | 📸 | + (positivo) |
| recarga | 📦 | + (positivo) |
| entrega | 🏎️ | - (negativo) |
| resgate_saida | 🏎️ | - (negativo) |
| resgate_entrada | 📦 | + (positivo) |

---

## Melhorias Visuais com Rich

O Textual usa Rich internamente. Podemos enriquecer a interface com:

### 1. Cores Condicionais por Valor

```python
# Saldo positivo = verde, negativo = vermelho
if saldo > 0:
    cell = f"[green]{saldo}[/]"
elif saldo < 0:
    cell = f"[red]{saldo}[/]"
else:
    cell = f"[dim]-[/]"
```

### 2. Cores por Tipo de Coluna

| Tipo | Cor | Estilo |
|------|-----|--------|
| 📸 Estoque | cyan | bold |
| 📦 Recarga | blue | bold |
| 🏎️ Saídas | yellow | normal |
| 💰 Saldo + | green | bold |
| 💰 Saldo - | red | bold |

### 3. Indicadores Visuais

```
▲ +15%   # Aumento (verde)
▼ -10%   # Queda (vermelho)
━━━━━━   # Sparkline do período
██████░░ # Barra de progresso
```

### 4. Formatação de Linhas

```python
# Driver expandido
f"[bold yellow]▾ {driver}[/]"

# Driver colapsado
f"[yellow]▸ {driver}[/]"

# Produto (sublinha)
f"[dim]  └ {produto}[/]"

# Produto com saldo negativo (alerta)
f"[red]  └ {produto} ⚠[/]"
```

### 5. Header Estilizado

```python
# Cabeçalho com gradiente
f"[bold cyan]📸[/][dim]{dd_mm}[/]"
f"[bold blue]📦[/][dim]{dd_mm}[/]"
f"[bold yellow]🏎️[/][dim]{dd_mm}[/]"
```

### 6. Totais Destacados

```python
# Linha de totais no footer
f"[bold reverse] TOTAL [/]"

# Valores grandes destacados
if valor >= 100:
    f"[bold]{valor}[/]"
```

### 7. Alertas e Badges

```python
# Saldo negativo = badge de alerta
if saldo < 0:
    f"[on red] {saldo} [/]"

# Novo registro hoje
if is_today:
    f"{valor} [green]●[/]"
```

### 8. Separadores Visuais

```python
# Linha separadora entre drivers
Rule(style="dim")

# Divisória de seção
Panel(content, title="[bold]Resumo[/]", border_style="cyan")
```

### 9. Rich Table Features (alternativa ao DataTable)

```python
from rich.table import Table

table = Table(
    title="Movimentos",
    caption="📸 Estoque | 📦 Recarga | 🏎️ Saídas",
    box=box.ROUNDED,
    header_style="bold cyan",
    row_styles=["", "dim"],  # Zebra stripes
    collapse_padding=True,
)
```

### 10. Status Bar Dinâmica

```
┌─────────────────────────────────────────────────────┐
│ 📦 Recargas: 405  │  🏎️ Entregas: 114  │  💰 +291  │
└─────────────────────────────────────────────────────┘
```

## Implementação Sugerida

### Fase 1: Cores Básicas
- [ ] Saldo positivo/negativo colorido
- [ ] Cores por tipo de coluna
- [ ] Destacar linha selecionada

### Fase 2: Formatação Avançada
- [ ] Badges de alerta para saldo negativo
- [ ] Indicador de "novo" para registros de hoje
- [ ] Header com estilo gradiente

### Fase 3: Componentes Rich
- [ ] Status bar com totais
- [ ] Sparklines de tendência (opcional)
- [ ] Painéis para seções
