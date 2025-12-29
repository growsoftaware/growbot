"""
GrowBot TUI - Dashboard de Entregas
Duas visões: Cards (híbrido) e Tabela (movimentos)
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Static, Label, Button,
    Select, Input, Rule, Collapsible, DataTable,
    TabbedContent, TabPane
)
from textual.binding import Binding
from rich.text import Text
from db import GrowBotDB

DRIVERS = ["TODOS", "RAFA", "FRANCIS", "RODRIGO", "KAROL", "ARTHUR"]
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
OUTPUT_PATH = Path(__file__).parent / "output"

# Ícones
ICON_ESTOQUE = "📸"
ICON_RECARGA = "📦"
ICON_SAIDA = "🏎️"
ICON_SALDO = "💰"


def format_valor(valor: int, tipo: str = None, width: int = 8) -> Text:
    """Formata valor com cores Rich e alinhamento à direita

    Cores:
    - estoque/recarga: verde (entrada = positivo)
    - saida: vermelho (saída = negativo)
    - saldo: verde (+) ou vermelho bold com parênteses (-)
    """
    if not valor:
        return Text("-".rjust(width), style="dim")

    valor_str = str(valor).rjust(width)

    if tipo == "estoque":
        return Text(valor_str, style="green")
    elif tipo == "recarga":
        return Text(valor_str, style="dark_sea_green4")
    elif tipo == "saida":
        return Text(valor_str, style="indian_red")
    elif tipo == "saldo":
        if valor > 0:
            return Text(valor_str, style="green")
        elif valor < 0:
            # Negativo com parênteses e negrito: (15)
            neg_str = f"({abs(valor)})".rjust(width)
            return Text(neg_str, style="bold red")
        else:
            return Text("-".rjust(width), style="dim")
    else:
        return Text(valor_str)


def load_entregas_from_json() -> list:
    """Carrega entregas do JSON para ter id_sale_delivery"""
    entregas_file = OUTPUT_PATH / "entregas_validadas.json"
    if not entregas_file.exists():
        return []

    with open(entregas_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("items", [])


class FilterPanel(Static):
    """Painel de filtros na esquerda"""

    def compose(self) -> ComposeResult:
        yield Label("[bold cyan]FILTROS[/]", classes="panel-title")

        yield Label("Data Inicio:")
        with Horizontal(classes="date-row"):
            yield Button("<", id="btn_ini_menos", classes="date-btn")
            yield Input(
                placeholder="DD/MM/YYYY",
                id="data_inicio",
                classes="filter-input-date"
            )
            yield Button(">", id="btn_ini_mais", classes="date-btn")

        yield Label("Data Fim:")
        with Horizontal(classes="date-row"):
            yield Button("<", id="btn_fim_menos", classes="date-btn")
            yield Input(
                placeholder="DD/MM/YYYY",
                id="data_fim",
                classes="filter-input-date"
            )
            yield Button(">", id="btn_fim_mais", classes="date-btn")

        yield Label("Driver:")
        yield Select(
            [(d, d) for d in DRIVERS],
            value="TODOS",
            id="driver_select",
            classes="filter-select"
        )

        yield Button("Filtrar", id="btn_filtrar", variant="primary")
        yield Button("Limpar", id="btn_limpar", variant="default")

        yield Rule()
        yield Label("[bold cyan]RESUMO[/]", classes="panel-title")
        yield Static(id="resumo_geral", classes="resumo-box")


class DriverDayCard(Static):
    """Card híbrido: resumo no topo + entregas colapsável"""

    def __init__(self, driver: str, data: str, entregas: list, recargas: list = None, **kwargs):
        super().__init__(**kwargs)
        self.driver = driver
        self.data = data
        self.entregas = entregas
        self.recargas = recargas or []

    def compose(self) -> ComposeResult:
        try:
            parts = self.data.split("/")
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = "20" + year
                dt = datetime(int(year), int(month), int(day))
                data_fmt = f"{dt.day:02d}/{dt.month:02d}"
                dia_semana = DIAS_SEMANA[dt.weekday()]
            else:
                data_fmt = self.data
                dia_semana = ""
        except:
            data_fmt = self.data
            dia_semana = ""

        total_entregas = len(set(e["id_sale_delivery"] for e in self.entregas)) if self.entregas else 0
        total_unidades = sum(e.get("quantidade", 0) for e in self.entregas)
        total_recargas = sum(r.get("quantidade", 0) for r in self.recargas)

        yield Label(
            f"[bold yellow]{self.driver}[/] - {data_fmt} ({dia_semana})",
            classes="card-header"
        )

        resumo_parts = []
        if total_recargas > 0:
            resumo_parts.append(f"[cyan]{ICON_RECARGA} +{total_recargas}[/]")
        if total_entregas > 0:
            resumo_parts.append(f"[green]{ICON_SAIDA} {total_entregas} ({total_unidades} un)[/]")

        if resumo_parts:
            yield Label(" | ".join(resumo_parts), classes="card-resumo")
        yield Rule()

        if self.entregas:
            with Collapsible(title=f"Ver {total_entregas} entregas", collapsed=True):
                entregas_por_id = defaultdict(list)
                for e in self.entregas:
                    entregas_por_id[e["id_sale_delivery"]].append(e)

                for id_entrega in sorted(entregas_por_id.keys()):
                    items = entregas_por_id[id_entrega]
                    produtos = [f"{item.get('quantidade', 1)} {item.get('produto', '?')}" for item in items]
                    yield Label(f"[green]#{id_entrega}:[/] {', '.join(produtos)}", classes="entrega-line")

        if self.recargas:
            with Collapsible(title=f"Ver {len(self.recargas)} recargas", collapsed=True):
                for r in self.recargas:
                    yield Label(f"[cyan]+{r.get('quantidade', 0)} {r.get('produto', '?')}[/]", classes="recarga-line")


class CardsPanel(VerticalScroll):
    """Painel com cards"""

    def compose(self) -> ComposeResult:
        yield Label("[dim]Carregando...[/]", id="cards_loading")


class FilterSummary(Static):
    """Resumo dos filtros ativos + legenda"""

    def update_summary(self, driver: str, data_ini: str, data_fim: str):
        """Atualiza o resumo dos filtros"""
        # Formatar datas para DD/MM
        def fmt_data(d):
            if not d:
                return "-"
            parts = d.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
            return d

        driver_txt = f"[bold yellow]{driver}[/]" if driver != "TODOS" else "[dim]TODOS[/]"
        linha1 = f"👤 {driver_txt}  │  📅 {fmt_data(data_ini)} → {fmt_data(data_fim)}"
        linha2 = f"[bold bright_green]{ICON_ESTOQUE} Estoque[/]  [bold bright_blue]{ICON_RECARGA} Recarga[/]  [bold bright_red]{ICON_SAIDA} Saída[/]  [bold bright_yellow]{ICON_SALDO} Saldo[/]"
        self.update(f"{linha1}\n{linha2}")


class KPIBar(Static):
    """Barra de KPIs acima da tabela"""

    def compose(self) -> ComposeResult:
        with Horizontal(id="kpi-container"):
            yield Static("[dim]🏎️ Entregas\n[/][bold]0[/]", id="kpi_entregas", classes="kpi-card")
            yield Static("[dim]📦 Retiradas\n[/][bold]0[/]", id="kpi_retiradas", classes="kpi-card")
            yield Static("[dim]⚠️ Negativos\n[/][bold]0[/]", id="kpi_negativos", classes="kpi-card")
            yield Static("[dim]📦 Tot.Ret\n[/][bold]0[/]", id="kpi_total_ret", classes="kpi-card")
            yield Static("[dim]🏎️ Tot.Del\n[/][bold]0[/]", id="kpi_total_del", classes="kpi-card")
            yield Static("[dim]📸 Estoque\n[/][bold]0[/]", id="kpi_estoque", classes="kpi-card kpi-driver-only")
            yield Static("[dim]💰 Saldo\n[/][bold]0[/]", id="kpi_saldo", classes="kpi-card kpi-driver-only")

    def update_kpis(self, entregas: int, retiradas: int, negativos: int, total_ret: int, total_del: int,
                    total_estoque: int = 0, saldo: int = 0, show_driver_kpis: bool = False):
        """Atualiza os valores dos KPIs"""
        self.query_one("#kpi_entregas").update(f"[dim]🏎️ Entregas\n[/][bold bright_blue]{entregas}[/]")
        self.query_one("#kpi_retiradas").update(f"[dim]📦 Retiradas\n[/][bold bright_green]{retiradas}[/]")

        neg_color = "bright_red" if negativos > 0 else "green"
        self.query_one("#kpi_negativos").update(f"[dim]⚠️ Negativos\n[/][bold {neg_color}]{negativos}[/]")

        self.query_one("#kpi_total_ret").update(f"[dim]📦 Tot.Ret\n[/][bold bright_green]{total_ret}[/]")
        self.query_one("#kpi_total_del").update(f"[dim]🏎️ Tot.Del\n[/][bold bright_blue]{total_del}[/]")

        # KPIs só para driver específico
        kpi_estoque = self.query_one("#kpi_estoque")
        kpi_saldo = self.query_one("#kpi_saldo")

        if show_driver_kpis:
            kpi_estoque.display = True
            kpi_saldo.display = True
            kpi_estoque.update(f"[dim]📸 Estoque\n[/][bold bright_green]{total_estoque}[/]")

            saldo_color = "bright_green" if saldo >= 0 else "bright_red"
            saldo_str = str(saldo) if saldo >= 0 else f"({abs(saldo)})"
            kpi_saldo.update(f"[dim]💰 Saldo\n[/][bold {saldo_color}]{saldo_str}[/]")
        else:
            kpi_estoque.display = False
            kpi_saldo.display = False


class TablePanel(VerticalScroll):
    """Painel com tabela de movimentos"""

    def compose(self) -> ComposeResult:
        table = DataTable(id="movements_table", zebra_stripes=True, cursor_type="row")
        table.header_height = 2  # Permite headers de 2 linhas
        yield table


class DetailPanel(VerticalScroll):
    """Painel de detalhes das entregas de um produto"""

    def compose(self) -> ComposeResult:
        yield Label("[bold cyan]DETALHES[/]", classes="panel-title")
        yield Rule()
        yield Label("[dim]Selecione um produto (Enter)[/]", id="detail_header")
        yield Rule()
        yield Vertical(id="detail_content")

    def show_details(self, driver: str, produto: str, entregas: list):
        """Atualiza o painel com detalhes do produto agrupados por data"""
        header = self.query_one("#detail_header", Label)
        header.update(f"[yellow]{driver}[/] - [green]{produto}[/] ({len(entregas)} total)")

        content = self.query_one("#detail_content", Vertical)
        # Limpar conteúdo anterior
        for child in list(content.children):
            child.remove()

        if not entregas:
            content.mount(Label("[dim]Nenhuma entrega encontrada[/]"))
            return

        # Agrupar por data
        por_data = defaultdict(list)
        for e in entregas:
            data = e.get("data_entrega", "-")
            por_data[data].append(e)

        # Ordenar datas (mais recente primeiro)
        datas_ordenadas = sorted(por_data.keys(), reverse=True)

        for data in datas_ordenadas:
            items = por_data[data]
            # Ordenar por sales_delivery_id
            items.sort(key=lambda x: x.get("id_sale_delivery", "000"))

            # Calcular total de unidades
            total_qtd = sum(e.get("quantidade", 0) for e in items)

            # Montar texto das entregas
            entregas_lines = [f"[bold]{data}[/] ({len(items)} entregas, {total_qtd} un)"]
            for e in items:
                entregas_lines.append(
                    f"  [cyan]#{e.get('id_sale_delivery', '-')}[/] → [green]{e.get('quantidade', 0)}[/] un"
                )
            entregas_lines.append("")  # Linha em branco entre datas

            # Criar label com todas as entregas da data
            content.mount(Label("\n".join(entregas_lines)))

    def clear_details(self):
        """Limpa o painel de detalhes"""
        header = self.query_one("#detail_header", Label)
        header.update("[dim]Selecione um produto (Enter)[/]")
        content = self.query_one("#detail_content", Vertical)
        for child in list(content.children):
            child.remove()


class GrowBotTUI(App):
    """Dashboard TUI do GrowBot"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        layout: horizontal;
    }

    #filter-panel {
        width: 32;
        background: $panel;
        border: solid $primary;
        padding: 1;
        height: 100%;
    }

    #content-area {
        width: 1fr;
        height: 100%;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .legenda {
        text-align: center;
        margin-bottom: 1;
    }

    .filter-input {
        margin-bottom: 1;
    }

    .filter-input-date {
        width: 1fr;
    }

    .date-row {
        height: 3;
        margin-bottom: 1;
    }

    .date-btn {
        width: 3;
        min-width: 3;
        margin-top: 0;
        padding: 0;
    }

    .filter-select {
        margin-bottom: 1;
    }

    .resumo-box {
        background: $boost;
        padding: 1;
        margin-top: 1;
        margin-bottom: 1;
    }

    DriverDayCard {
        background: $panel;
        border: solid $secondary;
        margin: 1;
        padding: 1;
        height: auto;
    }

    .card-header {
        text-style: bold;
    }

    .card-resumo {
        margin-bottom: 1;
    }

    .entrega-line {
        padding-left: 2;
    }

    .recarga-line {
        padding-left: 2;
    }

    Button {
        margin-top: 1;
        width: 100%;
    }

    #btn_limpar {
        margin-top: 0;
    }

    Collapsible {
        padding: 0;
        margin: 0;
    }

    Checkbox {
        margin-bottom: 1;
    }

    DataTable {
        height: auto;
    }

    DataTable > .datatable--cursor {
        background: $surface-lighten-1;
    }

    DataTable:focus > .datatable--cursor {
        background: $primary 30%;
    }

    TabbedContent {
        border: none;
    }

    ContentSwitcher {
        background: transparent;
        border: none;
    }

    TabPane {
        padding: 0;
        background: transparent;
        border: none;
    }

    #movements_table {
        width: auto;
        margin-left: 2;
    }

    #table-panel {
        width: auto;
    }

    #detail-panel {
        width: 45;
        background: $panel;
        border: solid $secondary;
        padding: 1;
        display: none;
    }

    #detail-panel.visible {
        display: block;
    }

    #table-container {
        width: 1fr;
    }

    #detail_table {
        height: auto;
        max-height: 20;
    }

    #kpi-bar {
        height: 4;
        margin-bottom: 1;
    }

    #kpi-container {
        height: 100%;
        width: 100%;
    }

    .kpi-card {
        width: 1fr;
        height: 100%;
        background: $panel;
        border: round $secondary;
        text-align: center;
        padding: 0 1;
        margin-left: 1;
    }

    .kpi-card:first-child {
        margin-left: 0;
    }

    #filter-summary {
        height: 2;
        background: $boost;
        padding: 0 1;
        text-align: center;
    }

    #content-wrapper {
        width: 1fr;
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Sair"),
        Binding("r", "refresh", "Atualizar"),
        Binding("f", "toggle_filter", "Filtros"),
        Binding("1", "show_table", "Dashboard"),
        Binding("2", "show_cards", "Cards"),
        Binding("z", "driver_anterior", "Driver ←"),
        Binding("x", "driver_proximo", "Driver →"),
        Binding("w", "data_ini_menos", "Ini −"),
        Binding("e", "data_ini_mais", "Ini +"),
        Binding("s", "data_fim_menos", "Fim −"),
        Binding("d", "data_fim_mais", "Fim +"),
    ]

    def __init__(self):
        super().__init__()
        self.db = GrowBotDB()
        self.data_inicio = None
        self.data_fim = None
        self.driver_filtro = "TODOS"
        self.show_estoque = True
        self.show_recarga = True
        self.show_saidas = True
        # Cache de dados expandidos
        self.expanded_drivers = set()
        # Estado de ordenação da tabela
        self.sort_column = None  # Coluna sendo ordenada (key)
        self.sort_ascending = True  # True = asc, False = desc
        # Cache dos dados para ordenação
        self._table_data = {}  # driver -> {saldo, valores...}
        self._colunas_visiveis = []
        self._dados_driver = {}
        self._dados_produto = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            yield FilterPanel(id="filter-panel")
            with Vertical(id="content-wrapper"):
                yield FilterSummary(id="filter-summary")
                with TabbedContent(id="content-area"):
                    with TabPane("DASHBOARD", id="tab-table"):
                        with Vertical():
                            yield KPIBar(id="kpi-bar")
                            with Horizontal():
                                yield TablePanel(id="table-panel")
                                yield DetailPanel(id="detail-panel")
                    with TabPane("CARDS", id="tab-cards"):
                        yield CardsPanel(id="cards-panel")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "GrowBot Dashboard"
        self.sub_title = f"{ICON_RECARGA} Recargas | {ICON_SAIDA} Entregas"

        hoje = datetime.now()
        self.data_fim = hoje.strftime("%d/%m/%Y")
        self.data_inicio = (hoje - timedelta(days=7)).strftime("%d/%m/%Y")

        self.query_one("#data_inicio", Input).value = self.data_inicio
        self.query_one("#data_fim", Input).value = self.data_fim

        # Tabela como visão padrão
        self.query_one(TabbedContent).active = "tab-table"

        self.refresh_data()

    def _parse_date_to_iso(self, date_str: str) -> str:
        if not date_str:
            return None
        try:
            parts = date_str.strip().split("/")
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except:
            pass
        return None

    def _parse_date_br(self, date_str: str) -> tuple:
        if not date_str:
            return None
        try:
            parts = date_str.strip().split("/")
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = "20" + year
                return (int(day), int(month), int(year))
        except:
            pass
        return None

    def _date_in_range(self, data_entrega: str, data_ini: tuple, data_fim: tuple) -> bool:
        parsed = self._parse_date_br(data_entrega)
        if not parsed:
            return False

        day, month, year = parsed
        dt = datetime(year, month, day)

        if data_ini:
            dt_ini = datetime(data_ini[2], data_ini[1], data_ini[0])
            if dt < dt_ini:
                return False

        if data_fim:
            dt_fim = datetime(data_fim[2], data_fim[1], data_fim[0])
            if dt > dt_fim:
                return False

        return True

    def _iso_to_br(self, iso_date: str) -> str:
        """Converte YYYY-MM-DD para DD/MM/YYYY"""
        if not iso_date or "-" not in str(iso_date):
            return str(iso_date)
        parts = str(iso_date).split("-")
        return f"{parts[2]}/{parts[1]}/{parts[0]}"

    def refresh_data(self) -> None:
        """Atualiza ambas as visões"""
        # Atualizar resumo dos filtros
        try:
            self.query_one("#filter-summary", FilterSummary).update_summary(
                self.driver_filtro, self.data_inicio, self.data_fim
            )
        except:
            pass

        # Auto-expandir driver quando específico selecionado
        if self.driver_filtro != "TODOS":
            self.expanded_drivers.add(self.driver_filtro)

        self._refresh_cards()
        self._refresh_table()

    def _refresh_cards(self) -> None:
        """Atualiza visão de cards"""
        cards_panel = self.query_one("#cards-panel", CardsPanel)

        for child in list(cards_panel.children):
            child.remove()

        data_ini = self._parse_date_br(self.data_inicio)
        data_fim = self._parse_date_br(self.data_fim)

        all_entregas = load_entregas_from_json()

        entregas_filtradas = []
        for e in all_entregas:
            if not self._date_in_range(e.get("data_entrega", ""), data_ini, data_fim):
                continue
            if self.driver_filtro != "TODOS" and e.get("driver") != self.driver_filtro:
                continue
            entregas_filtradas.append(e)

        grupos = defaultdict(list)
        for e in entregas_filtradas:
            key = (e.get("data_entrega", ""), e.get("driver", ""))
            grupos[key].append(e)

        # Busca recargas
        data_ini_iso = self._parse_date_to_iso(self.data_inicio)
        data_fim_iso = self._parse_date_to_iso(self.data_fim)

        query_recargas = "SELECT data_movimento, driver, produto, quantidade FROM movimentos WHERE tipo = 'recarga'"
        params_rec = []

        if data_ini_iso:
            query_recargas += " AND data_movimento >= ?"
            params_rec.append(data_ini_iso)
        if data_fim_iso:
            query_recargas += " AND data_movimento <= ?"
            params_rec.append(data_fim_iso)
        if self.driver_filtro != "TODOS":
            query_recargas += " AND driver = ?"
            params_rec.append(self.driver_filtro)

        try:
            result_rec = self.db.conn.execute(query_recargas, params_rec).fetchall()
            recargas = [{"data_movimento": self._iso_to_br(str(r[0])), "driver": r[1], "produto": r[2], "quantidade": r[3]} for r in result_rec]
        except:
            recargas = []

        recargas_por_grupo = defaultdict(list)
        for r in recargas:
            key = (r["data_movimento"], r["driver"])
            recargas_por_grupo[key].append(r)

        if not grupos and not recargas_por_grupo:
            cards_panel.mount(Label("[dim]Nenhum dado encontrado.[/]"))
            self._update_resumo({}, [])
            return

        all_keys = set(grupos.keys()) | set(recargas_por_grupo.keys())

        def sort_key(k):
            data, driver = k
            parsed = self._parse_date_br(data)
            if parsed:
                return (-parsed[2], -parsed[1], -parsed[0], driver)
            return (0, 0, 0, driver)

        for key in sorted(all_keys, key=sort_key):
            data, driver = key
            entregas_grupo = grupos.get(key, [])
            recargas_grupo = recargas_por_grupo.get(key, [])

            if entregas_grupo or recargas_grupo:
                card = DriverDayCard(driver=driver, data=data, entregas=entregas_grupo, recargas=recargas_grupo)
                cards_panel.mount(card)

        self._update_resumo(grupos, recargas)

    def _refresh_table(self) -> None:
        """Atualiza visão de tabela com expansão por produto e ordenação"""
        table = self.query_one("#movements_table", DataTable)
        table.clear(columns=True)

        data_ini_iso = self._parse_date_to_iso(self.data_inicio)
        data_fim_iso = self._parse_date_to_iso(self.data_fim)

        # Buscar dados agregados por driver E produto
        query_mov = """
            SELECT
                driver,
                produto,
                data_movimento,
                tipo,
                SUM(quantidade) as total
            FROM movimentos
            WHERE 1=1
        """
        params_mov = []
        if data_ini_iso:
            query_mov += " AND data_movimento >= ?"
            params_mov.append(data_ini_iso)
        if data_fim_iso:
            query_mov += " AND data_movimento <= ?"
            params_mov.append(data_fim_iso)
        if self.driver_filtro != "TODOS":
            query_mov += " AND driver = ?"
            params_mov.append(self.driver_filtro)

        query_mov += " GROUP BY driver, produto, data_movimento, tipo ORDER BY driver, produto, data_movimento"

        try:
            movimentos = self.db.conn.execute(query_mov, params_mov).fetchall()
        except:
            movimentos = []

        if not movimentos:
            table.add_column("Info")
            table.add_row("Nenhum dado encontrado")
            # Zerar KPIs
            try:
                self.query_one("#kpi-bar", KPIBar).update_kpis(0, 0, 0, 0, 0)
            except:
                pass
            return

        # Organizar dados: driver -> produto -> data -> tipo -> total
        # E também agregado: driver -> data -> tipo -> total
        self._dados_produto = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"estoque": 0, "recarga": 0, "saida": 0})))
        self._dados_driver = defaultdict(lambda: defaultdict(lambda: {"estoque": 0, "recarga": 0, "saida": 0}))
        todas_datas = set()
        colunas_com_dados = set()  # (data, tipo) que têm algum valor

        # Variáveis para KPIs
        kpi_total_recarga = 0
        kpi_total_entrega = 0
        kpi_datas_recarga = set()

        for driver, produto, data_mov, tipo, total in movimentos:
            data_str = str(data_mov)
            todas_datas.add(data_str)

            tipo_norm = self._normalizar_tipo(tipo)
            if tipo_norm:
                self._dados_produto[driver][produto][data_str][tipo_norm] += total
                self._dados_driver[driver][data_str][tipo_norm] += total
                colunas_com_dados.add((data_str, tipo_norm))

                # Acumular KPIs
                if tipo_norm == "recarga":
                    kpi_total_recarga += total
                    kpi_datas_recarga.add(data_str)
                elif tipo_norm == "saida":
                    kpi_total_entrega += total

        # Ordenar datas
        datas = sorted(todas_datas)

        if not datas:
            return

        # Determinar quais colunas mostrar (só as que têm dados)
        colunas_visiveis = []  # Lista de (data, tipo) a mostrar

        for data in datas:
            if self.show_estoque and (data, "estoque") in colunas_com_dados:
                colunas_visiveis.append((data, "estoque"))
            if self.show_recarga and (data, "recarga") in colunas_com_dados:
                colunas_visiveis.append((data, "recarga"))
            if self.show_saidas and (data, "saida") in colunas_com_dados:
                colunas_visiveis.append((data, "saida"))

        # Salvar colunas visíveis para ordenação
        self._colunas_visiveis = colunas_visiveis

        # Montar colunas da tabela com indicador de ordenação
        sort_indicator = "▲" if self.sort_ascending else "▼"

        col_name_text = "Driver\nProduto"
        if self.sort_column == "name":
            col_name_text = f"{col_name_text} {sort_indicator}"
        col_name_header = Text(col_name_text, justify="center")
        table.add_column(col_name_header, key="name")

        for data, tipo in colunas_visiveis:
            col_key = f"{data}_{tipo}"

            # Extrair DD e dia da semana da data ISO
            try:
                parts = data.split("-")
                dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                dd = f"{dt.day:02d}"
                dia_semana = DIAS_SEMANA[dt.weekday()].lower()[:3]
            except:
                dd = data[:2]
                dia_semana = ""

            # Header em duas linhas: ícone + DD ddd (centralizado)
            if tipo == "estoque":
                col_text = f"{ICON_ESTOQUE}\n{dd} {dia_semana}"
            elif tipo == "recarga":
                col_text = f"{ICON_RECARGA}\n{dd} {dia_semana}"
            else:  # saida
                col_text = f"{ICON_SAIDA}\n{dd} {dia_semana}"

            if self.sort_column == col_key:
                col_text = f"{col_text} {sort_indicator}"

            col_header = Text(col_text, justify="center")
            table.add_column(col_header, key=col_key)

        # Coluna saldo total (centralizado)
        total_text = f"{ICON_SALDO}\nTOTAL"
        if self.sort_column == "total":
            total_text = f"{total_text} {sort_indicator}"
        total_header = Text(total_text, justify="center")
        table.add_column(total_header, key="total")

        # Preparar dados para ordenação
        self._table_data = {}
        for driver in self._dados_driver.keys():
            saldo_total = 0
            valores = {}

            for data, tipo in colunas_visiveis:
                d = self._dados_driver[driver].get(data, {"estoque": 0, "recarga": 0, "saida": 0})
                valor = d.get(tipo, 0)
                col_key = f"{data}_{tipo}"
                valores[col_key] = valor

                if tipo == "estoque" and self.show_estoque:
                    saldo_total += valor
                elif tipo == "recarga" and self.show_recarga:
                    saldo_total += valor
                elif tipo == "saida" and self.show_saidas:
                    saldo_total -= valor

            valores["total"] = saldo_total
            valores["name"] = driver
            self._table_data[driver] = valores

        # Ordenar drivers
        drivers_ordenados = list(self._dados_driver.keys())
        if self.sort_column:
            def get_sort_value(driver):
                val = self._table_data[driver].get(self.sort_column, 0)
                if self.sort_column == "name":
                    return val.lower() if isinstance(val, str) else val
                return val if val else 0

            drivers_ordenados = sorted(drivers_ordenados, key=get_sort_value, reverse=not self.sort_ascending)
        else:
            drivers_ordenados = sorted(drivers_ordenados)

        # Adicionar linhas
        for driver in drivers_ordenados:
            is_expanded = driver in self.expanded_drivers

            # Linha do driver (agregado) com cor
            if is_expanded:
                driver_cell = Text(f"▾ {driver}", style="bold yellow")
            else:
                driver_cell = Text(f"▸ {driver}", style="yellow")

            row = [driver_cell]
            saldo_total = self._table_data[driver]["total"]

            for data, tipo in colunas_visiveis:
                d = self._dados_driver[driver].get(data, {"estoque": 0, "recarga": 0, "saida": 0})
                valor = d.get(tipo, 0)
                row.append(format_valor(valor, tipo))

            row.append(format_valor(saldo_total, "saldo"))
            table.add_row(*row, key=f"driver_{driver}")

            # Se expandido, adicionar linhas de produto (ordenadas)
            if is_expanded:
                # Preparar dados de produtos para ordenação
                produtos_data = {}
                for produto in self._dados_produto[driver].keys():
                    saldo_prod = 0
                    valores_prod = {"name": produto}

                    for data, tipo in colunas_visiveis:
                        d = self._dados_produto[driver][produto].get(data, {"estoque": 0, "recarga": 0, "saida": 0})
                        valor = d.get(tipo, 0)
                        col_key = f"{data}_{tipo}"
                        valores_prod[col_key] = valor

                        if tipo == "estoque" and self.show_estoque:
                            saldo_prod += valor
                        elif tipo == "recarga" and self.show_recarga:
                            saldo_prod += valor
                        elif tipo == "saida" and self.show_saidas:
                            saldo_prod -= valor

                    valores_prod["total"] = saldo_prod
                    produtos_data[produto] = valores_prod

                # Ordenar produtos
                produtos_ordenados = list(produtos_data.keys())
                if self.sort_column:
                    def get_prod_sort_value(prod):
                        val = produtos_data[prod].get(self.sort_column, 0)
                        if self.sort_column == "name":
                            return val.lower() if isinstance(val, str) else val
                        return val if val else 0

                    produtos_ordenados = sorted(produtos_ordenados, key=get_prod_sort_value, reverse=not self.sort_ascending)
                else:
                    produtos_ordenados = sorted(produtos_ordenados)

                for produto in produtos_ordenados:
                    saldo_prod = produtos_data[produto]["total"]

                    # Produto com alerta se saldo negativo
                    if saldo_prod < 0:
                        prod_cell = Text(f"  └ {produto} ⚠", style="red")
                    else:
                        prod_cell = Text(f"  └ {produto}", style="dim")

                    row_prod = [prod_cell]

                    for data, tipo in colunas_visiveis:
                        d = self._dados_produto[driver][produto].get(data, {"estoque": 0, "recarga": 0, "saida": 0})
                        valor = d.get(tipo, 0)
                        row_prod.append(format_valor(valor, tipo))

                    row_prod.append(format_valor(saldo_prod, "saldo"))
                    table.add_row(*row_prod, key=f"prod_{driver}_{produto}")

        # Calcular e atualizar KPIs
        # Contar entregas distintas (do JSON)
        all_entregas = load_entregas_from_json()
        data_ini = self._parse_date_br(self.data_inicio)
        data_fim = self._parse_date_br(self.data_fim)

        entregas_ids = set()
        for e in all_entregas:
            if self.driver_filtro != "TODOS" and e.get("driver") != self.driver_filtro:
                continue
            if not self._date_in_range(e.get("data_entrega", ""), data_ini, data_fim):
                continue
            entregas_ids.add(e.get("id_sale_delivery"))

        kpi_entregas = len(entregas_ids)
        kpi_retiradas = len(kpi_datas_recarga)

        # Contar produtos com saldo negativo e calcular totais
        kpi_negativos = 0
        kpi_total_estoque = 0
        kpi_saldo_total = 0

        for driver in self._dados_driver.keys():
            for produto in self._dados_produto[driver].keys():
                saldo = 0
                for data_str in todas_datas:
                    d = self._dados_produto[driver][produto].get(data_str, {})
                    saldo += d.get("estoque", 0)
                    saldo += d.get("recarga", 0)
                    saldo -= d.get("saida", 0)
                    kpi_total_estoque += d.get("estoque", 0)
                if saldo < 0:
                    kpi_negativos += 1

        # Calcular saldo total
        kpi_saldo_total = kpi_total_estoque + kpi_total_recarga - kpi_total_entrega

        # Atualizar KPIBar
        show_driver_kpis = self.driver_filtro != "TODOS"
        try:
            self.query_one("#kpi-bar", KPIBar).update_kpis(
                kpi_entregas, kpi_retiradas, kpi_negativos, kpi_total_recarga, kpi_total_entrega,
                kpi_total_estoque, kpi_saldo_total, show_driver_kpis
            )
        except:
            pass

    def _normalizar_tipo(self, tipo: str) -> str:
        """Normaliza tipo do banco para tipo da tabela"""
        if tipo == "estoque":
            return "estoque"
        elif tipo == "recarga":
            return "recarga"
        elif tipo == "entrega":
            return "saida"
        elif tipo == "resgate_saida":
            return "saida"
        elif tipo == "resgate_entrada":
            return "recarga"
        return None

    def _update_resumo(self, grupos: dict, recargas: list) -> None:
        total_entregas = 0
        total_unidades = 0
        total_recargas = 0
        drivers_set = set()

        for key, items in grupos.items():
            data, driver = key
            drivers_set.add(driver)
            ids = set(e["id_sale_delivery"] for e in items)
            total_entregas += len(ids)
            for item in items:
                total_unidades += item.get("quantidade", 0)

        for r in recargas:
            total_recargas += r.get("quantidade", 0)
            drivers_set.add(r.get("driver"))

        resumo = self.query_one("#resumo_geral", Static)
        resumo.update(
            f"[cyan]{ICON_RECARGA} Recargas:[/] {total_recargas}\n"
            f"[green]{ICON_SAIDA} Entregas:[/] {total_entregas}\n"
            f"[green]   Unidades:[/] {total_unidades}\n"
            f"[yellow]👤 Drivers:[/] {len(drivers_set)}"
        )

    def _ajustar_data(self, campo_id: str, dias: int, refresh: bool = True) -> None:
        """Ajusta uma data em N dias"""
        input_field = self.query_one(f"#{campo_id}", Input)
        data_str = input_field.value
        parsed = self._parse_date_br(data_str)
        if parsed:
            day, month, year = parsed
            dt = datetime(year, month, day) + timedelta(days=dias)
            nova_data = dt.strftime("%d/%m/%Y")
            input_field.value = nova_data
            # Atualizar estado
            if campo_id == "data_inicio":
                self.data_inicio = nova_data
            else:
                self.data_fim = nova_data
            if refresh:
                self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_filtrar":
            self.data_inicio = self.query_one("#data_inicio", Input).value
            self.data_fim = self.query_one("#data_fim", Input).value
            select = self.query_one("#driver_select", Select)
            self.driver_filtro = select.value if select.value != Select.BLANK else "TODOS"
            self.refresh_data()

        elif event.button.id == "btn_limpar":
            hoje = datetime.now()
            self.data_fim = hoje.strftime("%d/%m/%Y")
            self.data_inicio = (hoje - timedelta(days=7)).strftime("%d/%m/%Y")

            self.query_one("#data_inicio", Input).value = self.data_inicio
            self.query_one("#data_fim", Input).value = self.data_fim
            self.query_one("#driver_select", Select).value = "TODOS"
            self.driver_filtro = "TODOS"
            self.refresh_data()

        # Botões de ajuste de data
        elif event.button.id == "btn_ini_menos":
            self._ajustar_data("data_inicio", -1)
        elif event.button.id == "btn_ini_mais":
            self._ajustar_data("data_inicio", 1)
        elif event.button.id == "btn_fim_menos":
            self._ajustar_data("data_fim", -1)
        elif event.button.id == "btn_fim_mais":
            self._ajustar_data("data_fim", 1)


    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handler para ordenação ao clicar no header da coluna"""
        col_key = str(event.column_key.value) if event.column_key else None
        if not col_key:
            return

        # Toggle: mesma coluna inverte direção, nova coluna começa asc
        if self.sort_column == col_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = col_key
            self.sort_ascending = True

        self._refresh_table()

    def watch_focused(self, focused) -> None:
        """Esconde painel de detalhes quando foco sai da tabela principal"""
        try:
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            if focused is None or (hasattr(focused, 'id') and focused.id != "movements_table"):
                # Foco saiu da tabela - esconder detalhes
                if "visible" in detail_panel.classes:
                    detail_panel.remove_class("visible")
        except:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handler para expandir/colapsar driver ou mostrar detalhes do produto"""
        # Ignorar se for da tabela de detalhes
        if event.data_table.id == "detail_table":
            return

        row_key = str(event.row_key.value) if event.row_key else None

        if row_key and row_key.startswith("driver_"):
            # Expandir/colapsar driver
            driver = row_key.replace("driver_", "")
            if driver in self.expanded_drivers:
                self.expanded_drivers.remove(driver)
            else:
                self.expanded_drivers.add(driver)
            # Esconder painel de detalhes
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            detail_panel.remove_class("visible")
            self._refresh_table()

        elif row_key and row_key.startswith("prod_"):
            # Mostrar detalhes do produto
            parts = row_key.replace("prod_", "").split("_", 1)
            if len(parts) == 2:
                driver, produto = parts
                self._show_product_details(driver, produto)

    def _show_product_details(self, driver: str, produto: str) -> None:
        """Mostra detalhes das entregas de um produto"""
        # Buscar entregas do JSON
        all_entregas = load_entregas_from_json()

        # Filtrar por driver e produto
        data_ini = self._parse_date_br(self.data_inicio)
        data_fim = self._parse_date_br(self.data_fim)

        entregas_filtradas = []
        for e in all_entregas:
            if e.get("driver") != driver:
                continue
            if e.get("produto") != produto:
                continue
            if not self._date_in_range(e.get("data_entrega", ""), data_ini, data_fim):
                continue
            entregas_filtradas.append(e)

        # Ordenar por data
        entregas_filtradas.sort(key=lambda x: x.get("data_entrega", ""), reverse=True)

        # Mostrar no painel
        detail_panel = self.query_one("#detail-panel", DetailPanel)
        detail_panel.show_details(driver, produto, entregas_filtradas)
        detail_panel.add_class("visible")

    def action_refresh(self) -> None:
        self.refresh_data()

    def action_toggle_filter(self) -> None:
        """Toggle visibilidade do painel de filtros"""
        filter_panel = self.query_one("#filter-panel", FilterPanel)
        if filter_panel.display:
            filter_panel.display = False
        else:
            filter_panel.display = True
            self.query_one("#data_inicio", Input).focus()

    def action_show_cards(self) -> None:
        self.query_one(TabbedContent).active = "tab-cards"

    def action_show_table(self) -> None:
        self.query_one(TabbedContent).active = "tab-table"

    def action_driver_anterior(self) -> None:
        """Muda para driver anterior na lista"""
        idx = DRIVERS.index(self.driver_filtro) if self.driver_filtro in DRIVERS else 0
        novo_idx = (idx - 1) % len(DRIVERS)
        self.driver_filtro = DRIVERS[novo_idx]
        self.query_one("#driver_select", Select).value = self.driver_filtro
        self.refresh_data()

    def action_driver_proximo(self) -> None:
        """Muda para próximo driver na lista"""
        idx = DRIVERS.index(self.driver_filtro) if self.driver_filtro in DRIVERS else 0
        novo_idx = (idx + 1) % len(DRIVERS)
        self.driver_filtro = DRIVERS[novo_idx]
        self.query_one("#driver_select", Select).value = self.driver_filtro
        self.refresh_data()

    def action_data_ini_menos(self) -> None:
        """Retrocede data início em 1 dia"""
        self._ajustar_data("data_inicio", -1)

    def action_data_ini_mais(self) -> None:
        """Avança data início em 1 dia"""
        self._ajustar_data("data_inicio", 1)

    def action_data_fim_menos(self) -> None:
        """Retrocede data fim em 1 dia"""
        self._ajustar_data("data_fim", -1)

    def action_data_fim_mais(self) -> None:
        """Avança data fim em 1 dia"""
        self._ajustar_data("data_fim", 1)


def main():
    app = GrowBotTUI()
    app.run()


if __name__ == "__main__":
    main()
