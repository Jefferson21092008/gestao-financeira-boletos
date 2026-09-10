from datetime import date
import tkinter as tk
from tkinter import ttk

from config import DATE_FMT_UI, MOVEMENT_TYPES, STATUS_OPTIONS
from core.finance import from_cents
from core.formatters import format_date_ui, format_money, parse_date_ui
from database.database import Database
from ui.audit_window import AuditWindow
from ui.company_window import CompanyDirectoryWindow
from ui.fraud_window import FraudGuardWindow
from ui.main_actions import MainFrameActionsMixin
from ui.theme import THEME

class MainFrame(MainFrameActionsMixin, ttk.Frame):
    """V12: controle local de boletos, auditoria e triagem antifraude."""

    def __init__(self, master: tk.Misc, db: Database, on_logout):
        ttk.Frame.__init__(self, master, style="App.TFrame")
        self.db = db
        self.on_logout = on_logout
        self.selected_id: int | None = None
        self.startup_alert_shown = False
        self.record_action_buttons: list[ttk.Button] = []

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_sidebar()

        self.content = ttk.Frame(self, style="App.TFrame", padding=(24, 18, 24, 22))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(3, weight=1)

        self._build_header()
        self._build_quick_summary()
        self._build_form()
        self._build_table()
        self.refresh_table()

    # ---------- navegação ----------
    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self, bg=THEME["sidebar"], width=232, bd=0, highlightthickness=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(11, weight=1)

        brand = tk.Frame(sidebar, bg=THEME["sidebar"])
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 24))
        tk.Label(
            brand, text="GF", bg=THEME["accent"], fg="#FFFFFF",
            font=("Segoe UI Semibold", 12), width=3, height=1,
        ).pack(side="left")
        brand_text = tk.Frame(brand, bg=THEME["sidebar"])
        brand_text.pack(side="left", padx=(10, 0))
        tk.Label(
            brand_text, text="Gestão Financeira", bg=THEME["sidebar"], fg="#FFFFFF",
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w")
        tk.Label(
            brand_text, text="Controle local", bg=THEME["sidebar"], fg="#98A2B3",
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(1, 0))

        self._sidebar_section(sidebar, 1, "PRINCIPAL")
        self.nav_buttons = {}
        self.nav_buttons["lancamentos"] = self._nav_button(
            sidebar, 2, "Lançamentos", lambda: self.entries["empresa"].focus_set(), active=True
        )
        self.nav_buttons["empresas"] = self._nav_button(sidebar, 3, "Empresas", self.open_companies)
        self.nav_buttons["dashboard"] = self._nav_button(sidebar, 4, "Visão geral", self.open_dashboard)
        self.nav_buttons["alertas"] = self._nav_button(sidebar, 5, "Alertas e vencimentos", self.open_alerts)
        self.nav_buttons["antifraude"] = self._nav_button(sidebar, 6, "Guardião antifraude", self.open_fraud_guard)

        self._sidebar_section(sidebar, 7, "FERRAMENTAS")
        self.nav_buttons["backups"] = self._nav_button(sidebar, 8, "Backup e restauração", self.open_backups)
        self.nav_buttons["auditoria"] = self._nav_button(sidebar, 9, "Auditoria", self.open_audit)
        self.nav_buttons["atalho"] = self._nav_button(sidebar, 10, "Criar atalho", self.create_desktop_shortcut)

        footer = tk.Frame(sidebar, bg=THEME["sidebar"])
        footer.grid(row=12, column=0, sticky="sew", padx=14, pady=16)
        user_box = tk.Frame(footer, bg=THEME["sidebar_hover"])
        user_box.pack(fill="x")
        avatar = tk.Label(
            user_box, text="A", bg=THEME["accent"], fg="#FFFFFF",
            font=("Segoe UI Semibold", 9), width=3, height=1,
        )
        avatar.pack(side="left", padx=(9, 8), pady=9)
        user_text = tk.Frame(user_box, bg=THEME["sidebar_hover"])
        user_text.pack(side="left", pady=7)
        tk.Label(user_text, text="Administrador", bg=THEME["sidebar_hover"], fg="#FFFFFF", font=("Segoe UI Semibold", 8)).pack(anchor="w")
        tk.Label(user_text, text="Acesso completo", bg=THEME["sidebar_hover"], fg="#98A2B3", font=("Segoe UI", 7)).pack(anchor="w")

        tk.Button(
            footer, text="Sair do sistema", command=self.on_logout, anchor="w",
            bg=THEME["sidebar"], fg="#98A2B3", activebackground=THEME["sidebar_hover"], activeforeground="#FFFFFF",
            relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 8), cursor="hand2",
        ).pack(fill="x", pady=(8, 0), ipady=5, padx=2)

    def _sidebar_section(self, parent, row: int, text: str) -> None:
        tk.Label(
            parent, text=text, bg=THEME["sidebar"], fg="#667085",
            font=("Segoe UI Semibold", 7),
        ).grid(row=row, column=0, sticky="w", padx=20, pady=(2, 6))

    def _nav_button(self, parent, row: int, text: str, command, active: bool = False):
        bg = THEME["accent"] if active else THEME["sidebar"]
        fg = "#FFFFFF" if active else "#D0D5DD"
        btn = tk.Button(
            parent, text=text, command=command, anchor="w",
            bg=bg, fg=fg,
            activebackground=THEME["accent_hover"] if active else THEME["sidebar_hover"],
            activeforeground="#FFFFFF",
            relief="flat", bd=0, highlightthickness=0,
            font=("Segoe UI Semibold" if active else "Segoe UI", 9), cursor="hand2",
        )
        btn.grid(row=row, column=0, sticky="ew", padx=12, pady=2, ipady=8, ipadx=10)
        return btn

    def open_fraud_guard(self) -> None:
        FraudGuardWindow(self, self.db)

    def open_audit(self) -> None:
        AuditWindow(self, self.db)

    def open_companies(self) -> None:
        CompanyDirectoryWindow(self, self.db, on_change=self._company_directory_changed)

    def _company_directory_changed(self) -> None:
        if hasattr(self, "company_combo"):
            self.company_combo.configure(values=[r["nome"] for r in self.db.list_companies("", limit=500)])
        self._refresh_company_info()

    # ---------- topo e indicadores ----------
    def _build_header(self) -> None:
        header = ttk.Frame(self.content, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        title = ttk.Frame(header, style="App.TFrame")
        title.grid(row=0, column=0, sticky="w")
        ttk.Label(title, text="Lançamentos", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(
            title,
            text="Cadastre, acompanhe e encontre movimentações financeiras sem complicação.",
            style="PageSubtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        actions = ttk.Frame(header, style="App.TFrame")
        actions.grid(row=0, column=1, sticky="e")
        today_text = date.today().strftime("%d/%m/%Y")
        ttk.Label(actions, text=f"Hoje  {today_text}", style="HeaderDate.TLabel").pack(side="left", padx=(0, 10))

        self.alert_banner_var = tk.StringVar(value="Tudo em ordem")
        self.alert_status_chip = tk.Label(
            actions, textvariable=self.alert_banner_var,
            bg=THEME["green_soft"], fg=THEME["green"],
            font=("Segoe UI Semibold", 8), padx=10, pady=7,
        )
        self.alert_status_chip.pack(side="left", padx=(0, 8))
        self.alert_btn = ttk.Button(actions, text="Ver alertas", style="Secondary.TButton", command=self.open_alerts)
        self.alert_btn.pack(side="left")

    def _build_quick_summary(self) -> None:
        strip = ttk.Frame(self.content, style="App.TFrame")
        strip.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for col in range(4):
            strip.columnconfigure(col, weight=1)

        self.mini_summary_vars = {
            "entries": tk.StringVar(value="R$ 0,00"),
            "expenses": tk.StringVar(value="R$ 0,00"),
            "balance": tk.StringVar(value="R$ 0,00"),
            "open": tk.StringVar(value="0"),
        }
        cards = [
            ("Entradas", "entries", THEME["green"], "Recebimentos no filtro atual"),
            ("Despesas", "expenses", THEME["red"], "Saídas no filtro atual"),
            ("Saldo", "balance", THEME["accent"], "Entradas menos despesas"),
            ("Precisa de atenção", "open", THEME["amber"], "Atrasados, hoje ou amanhã"),
        ]
        for i, (label, key, color, hint) in enumerate(cards):
            card = tk.Frame(
                strip, bg=THEME["surface"],
                highlightbackground=THEME["border"], highlightthickness=1,
            )
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            tk.Frame(card, bg=color, height=3).pack(fill="x")
            body = tk.Frame(card, bg=THEME["surface"])
            body.pack(fill="both", expand=True, padx=14, pady=(10, 11))
            tk.Label(body, text=label, bg=THEME["surface"], fg=THEME["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w")
            tk.Label(body, textvariable=self.mini_summary_vars[key], bg=THEME["surface"], fg=THEME["text"], font=("Segoe UI Semibold", 14)).pack(anchor="w", pady=(3, 2))
            tk.Label(body, text=hint, bg=THEME["surface"], fg="#98A2B3", font=("Segoe UI", 7)).pack(anchor="w")

    # ---------- formulário ----------
    def _build_form(self) -> None:
        box = ttk.Frame(self.content, style="Surface.TFrame", padding=16)
        box.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        box.columnconfigure(0, weight=1)

        head = ttk.Frame(box, style="Surface.TFrame")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text="Novo lançamento", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(head, text="Preencha os dados em duas etapas simples.", style="CardHint.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(head, text="* obrigatório", style="Required.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")

        self.vars = {
            "empresa": tk.StringVar(),
            "cnpj": tk.StringVar(),
            "tipo_movimentacao": tk.StringVar(value="Despesa"),
            "centro_custo": tk.StringVar(value="Administrativo"),
            "data_lancamento": tk.StringVar(value=date.today().strftime(DATE_FMT_UI)),
            "numero_nota_fiscal": tk.StringVar(),
            "numero_boleto": tk.StringVar(),
            "quantidade_boletos": tk.StringVar(value="1"),
            "primeiro_vencimento": tk.StringVar(),
            "valor_nota_fiscal": tk.StringVar(),
            "valor_parte_especial": tk.StringVar(value="0,00"),
            "valor_total": tk.StringVar(),
        }
        self.entries: dict[str, tk.Widget] = {}

        stages = ttk.Frame(box, style="Surface.TFrame")
        stages.grid(row=1, column=0, sticky="ew")
        stages.columnconfigure(0, weight=1)
        stages.columnconfigure(1, weight=1)

        identification = ttk.Frame(stages, style="SubCard.TFrame", padding=12)
        identification.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        payment = ttk.Frame(stages, style="SubCard.TFrame", padding=12)
        payment.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._stage_title(identification, "1", "Dados do lançamento", "Quem, quando e qual documento")
        self._stage_title(payment, "2", "Pagamento e vencimento", "Parcelas, datas e valores")

        id_fields = [
            ("Empresa cadastrada *", "empresa", "company_combo"),
            ("CNPJ cadastrado", "cnpj", "entry"),
            ("Tipo de movimentação *", "tipo_movimentacao", "combo"),
            ("Centro de custo *", "centro_custo", "cost_combo"),
            ("Data do lançamento *", "data_lancamento", "entry"),
            ("Número da nota fiscal *", "numero_nota_fiscal", "entry"),
        ]
        payment_fields = [
            ("Número do boleto *", "numero_boleto", "entry"),
            ("Quantidade de parcelas *", "quantidade_boletos", "entry"),
            ("Primeiro vencimento *", "primeiro_vencimento", "entry"),
            ("Valor da nota fiscal *", "valor_nota_fiscal", "entry"),
            ("Parte especial *", "valor_parte_especial", "entry"),
            ("Valor total *", "valor_total", "entry"),
        ]
        self._render_fields(identification, id_fields)
        self._render_fields(payment, payment_fields)

        # A empresa é escolhida a partir do cadastro local; os dados cadastrais
        # ficam visíveis antes de o funcionário criar os boletos.
        self.company_info_var = tk.StringVar(value="Selecione uma empresa cadastrada. Para adicionar uma nova, use o menu Empresas.")
        self.company_info_box = tk.Label(
            identification, textvariable=self.company_info_var,
            bg=THEME["accent_soft"], fg=THEME["accent"], font=("Segoe UI", 8),
            anchor="w", justify="left", wraplength=560, padx=10, pady=8,
        )
        self.company_info_box.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0), padx=(0, 6))

        status_bar = ttk.Frame(box, style="Surface.TFrame")
        status_bar.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        status_bar.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="Pronto para cadastrar um novo lançamento.")
        ttk.Label(status_bar, textvariable=self.status_var, style="CardHint.TLabel").grid(row=0, column=0, sticky="w")

        primary_actions = ttk.Frame(status_bar, style="Surface.TFrame")
        primary_actions.grid(row=0, column=1, sticky="e")
        ttk.Button(primary_actions, text="Limpar", style="Ghost.TButton", command=self.clear_form).pack(side="left", padx=(0, 6))
        ttk.Button(primary_actions, text="Calcular total", style="Secondary.TButton", command=self.calculate_total).pack(side="left", padx=(0, 6))
        ttk.Button(primary_actions, text="Salvar lançamento", style="Primary.TButton", command=self.save_record).pack(side="left")

        selection_bar = ttk.Frame(box, style="SelectionBar.TFrame", padding=(10, 8))
        selection_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        selection_bar.columnconfigure(0, weight=1)
        ttk.Label(
            selection_bar,
            text="Selecione um lançamento na tabela para editar, duplicar, ver parcelas ou excluir.",
            style="SelectionHint.TLabel",
        ).grid(row=0, column=0, sticky="w")

        selected_actions = ttk.Frame(selection_bar, style="SelectionBar.TFrame")
        selected_actions.grid(row=0, column=1, sticky="e")
        action_specs = [
            ("Salvar alterações", self.update_record, "Secondary.TButton"),
            ("Duplicar", self.duplicate_record, "Secondary.TButton"),
            ("Ver parcelas", self.open_bills, "Secondary.TButton"),
            ("Excluir", self.delete_record, "Danger.TButton"),
        ]
        for index, (text, command, style) in enumerate(action_specs):
            btn = ttk.Button(selected_actions, text=text, style=style, command=command, state="disabled")
            btn.pack(side="left", padx=(0 if index == 0 else 5, 0))
            self.record_action_buttons.append(btn)

    def _stage_title(self, parent, number: str, title: str, hint: str) -> None:
        head = ttk.Frame(parent, style="SubCard.TFrame")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        badge = tk.Label(
            head, text=number, bg=THEME["accent_soft"], fg=THEME["accent"],
            font=("Segoe UI Semibold", 8), width=2, height=1,
        )
        badge.pack(side="left", padx=(0, 8))
        words = ttk.Frame(head, style="SubCard.TFrame")
        words.pack(side="left")
        ttk.Label(words, text=title, style="SubCardTitle.TLabel").pack(anchor="w")
        ttk.Label(words, text=hint, style="SubCardHint.TLabel").pack(anchor="w", pady=(1, 0))

    def _render_fields(self, parent, fields) -> None:
        for col in range(2):
            parent.columnconfigure(col, weight=1)
        for index, (label, key, kind) in enumerate(fields):
            row = 1 + (index // 2) * 2
            col = index % 2
            ttk.Label(parent, text=label, style="SubFieldLabel.TLabel").grid(
                row=row, column=col, sticky="w", padx=(0 if col == 0 else 6, 6), pady=(6, 0)
            )
            if kind == "combo":
                widget = ttk.Combobox(parent, textvariable=self.vars[key], values=MOVEMENT_TYPES, state="readonly")
            elif kind == "company_combo":
                widget = ttk.Combobox(parent, textvariable=self.vars[key], values=[r["nome"] for r in self.db.list_companies("", limit=500)], state="normal")
                widget.bind("<KeyRelease>", self.on_company_typing)
                widget.bind("<<ComboboxSelected>>", self.on_company_selected)
                widget.bind("<FocusOut>", lambda _e: self._refresh_company_info())
                self.company_combo = widget
            elif kind == "cost_combo":
                widget = ttk.Combobox(parent, textvariable=self.vars[key], values=self.db.list_cost_centers(), state="normal")
            else:
                widget = ttk.Entry(parent, textvariable=self.vars[key])
                if key == "cnpj":
                    widget.configure(state="readonly")
            widget.grid(row=row + 1, column=col, sticky="ew", padx=(0 if col == 0 else 6, 6), pady=(3, 0))
            self.entries[key] = widget

    # ---------- tabela e filtros ----------
    def _build_table(self) -> None:
        area = ttk.Frame(self.content, style="Surface.TFrame", padding=16)
        area.grid(row=3, column=0, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.rowconfigure(5, weight=1)

        top = ttk.Frame(area, style="Surface.TFrame")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text="Lançamentos cadastrados", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Clique em uma linha para editar • duplo clique abre as parcelas", style="CardHint.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, style="TableSummary.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")

        self.search_var = tk.StringVar()
        self.filter_start_var = tk.StringVar()
        self.filter_end_var = tk.StringVar()
        self.filter_type_var = tk.StringVar(value="Todos")
        self.filter_status_var = tk.StringVar(value="Todos")
        self.filter_cost_var = tk.StringVar(value="Todos")

        search_row = ttk.Frame(area, style="Surface.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        search_row.columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Pesquisar", style="FilterLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        search = ttk.Entry(search_row, textvariable=self.search_var)
        search.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        search.bind("<KeyRelease>", lambda _e: self.refresh_table(silent=True))
        ttk.Button(search_row, text="Limpar filtros", style="Ghost.TButton", command=self.clear_filters).grid(row=0, column=2)

        ttk.Label(
            area,
            text="Você pode pesquisar por empresa, CNPJ, nota, boleto, tipo ou centro de custo.",
            style="SearchHint.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        filters = ttk.Frame(area, style="Surface.TFrame")
        filters.grid(row=3, column=0, sticky="ew", pady=(0, 9))
        for i in range(6):
            filters.columnconfigure(i, weight=1)
        filter_defs = [
            ("Data inicial", "entry", self.filter_start_var, None),
            ("Data final", "entry", self.filter_end_var, None),
            ("Tipo", "combo", self.filter_type_var, ("Todos",) + MOVEMENT_TYPES),
            ("Centro de custo", "combo", self.filter_cost_var, ("Todos",) + tuple(self.db.list_cost_centers())),
            ("Status", "combo", self.filter_status_var, STATUS_OPTIONS),
        ]
        for i, (label, kind, variable, values) in enumerate(filter_defs):
            cell = ttk.Frame(filters, style="Surface.TFrame")
            cell.grid(row=0, column=i, sticky="ew", padx=(0, 8))
            ttk.Label(cell, text=label, style="FilterLabel.TLabel").pack(anchor="w")
            if kind == "combo":
                widget = ttk.Combobox(cell, textvariable=variable, values=values, state="readonly")
                widget.bind("<<ComboboxSelected>>", lambda _e: self.refresh_table(silent=True))
            else:
                widget = ttk.Entry(cell, textvariable=variable)
            widget.pack(fill="x", pady=(3, 0))
        ttk.Button(filters, text="Aplicar filtros", style="Secondary.TButton", command=self.refresh_table).grid(row=0, column=5, sticky="sew")

        legend = tk.Frame(area, bg=THEME["surface"])
        legend.grid(row=4, column=0, sticky="ew", pady=(0, 7))
        self._legend_item(legend, THEME["green"], "Em dia")
        self._legend_item(legend, THEME["amber"], "Vence amanhã")
        self._legend_item(legend, THEME["red"], "Atrasado")

        table_wrap = ttk.Frame(area, style="Surface.TFrame")
        table_wrap.grid(row=5, column=0, sticky="nsew")
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(0, weight=1)

        columns = ("empresa", "tipo", "centro", "data", "nota", "boleto", "qtd", "proximo", "status", "total")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings", selectmode="browse", style="Clean.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew")
        headings = {
            "empresa": "Empresa", "tipo": "Tipo", "centro": "Centro de custo", "data": "Data",
            "nota": "Nota fiscal", "boleto": "Boleto", "qtd": "Parcelas", "proximo": "Próximo vencimento",
            "status": "Status", "total": "Valor total",
        }
        widths = {
            "empresa": 190, "tipo": 84, "centro": 125, "data": 90, "nota": 95, "boleto": 95,
            "qtd": 65, "proximo": 120, "status": 110, "total": 110,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], minwidth=60, anchor="w" if col in ("empresa", "centro") else "center")

        self.tree.tag_configure("late", background=THEME["red_soft"], foreground=THEME["red"])
        self.tree.tag_configure("tomorrow", background=THEME["amber_soft"], foreground=THEME["amber_dark"])
        self.tree.tag_configure("paid", background=THEME["green_soft"], foreground=THEME["green"])

        yscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=xscroll.set)

        self.tree.bind("<<TreeviewSelect>>", self.load_selected_record)
        self.tree.bind("<Double-1>", lambda _e: self.open_bills())

    def _legend_item(self, parent, color: str, text: str) -> None:
        item = tk.Frame(parent, bg=THEME["surface"])
        item.pack(side="left", padx=(0, 14))
        tk.Label(item, text="●", bg=THEME["surface"], fg=color, font=("Segoe UI", 8)).pack(side="left")
        tk.Label(item, text=text, bg=THEME["surface"], fg=THEME["muted"], font=("Segoe UI", 7)).pack(side="left", padx=(3, 0))

    def refresh_table(self, silent: bool = False) -> None:
        start, end = self.get_filter_values(silent=silent) if hasattr(self, "filter_start_var") else (None, None)
        if silent:
            try:
                start = parse_date_ui(self.filter_start_var.get(), "a data inicial", allow_empty=True)
                end = parse_date_ui(self.filter_end_var.get(), "a data final", allow_empty=True)
                if start and end and start > end:
                    start, end = None, None
            except ValueError:
                start, end = None, None

        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self.db.list_purchases(
            self.search_var.get() if hasattr(self, "search_var") else "",
            start, end,
            self.filter_type_var.get() if hasattr(self, "filter_type_var") else "Todos",
            self.filter_status_var.get() if hasattr(self, "filter_status_var") else "Todos",
            self.filter_cost_var.get() if hasattr(self, "filter_cost_var") else "Todos",
        )

        filtered_entries = from_cents(0)
        filtered_expenses = from_cents(0)
        for row in rows:
            display_status = row["status"]
            tag = ""
            if row["status"] == "Atrasado":
                tag = "late"
            elif row["vence_amanha"]:
                display_status = "Vence amanhã"
                tag = "tomorrow"
            elif row["status"] == "Em dia":
                tag = "paid"

            if row["tipo_movimentacao"] == "Entrada":
                filtered_entries += from_cents(row["valor_total_centavos"])
            else:
                filtered_expenses += from_cents(row["valor_total_centavos"])

            self.tree.insert(
                "", tk.END, iid=str(row["id"]),
                values=(
                    row["empresa"], row["tipo_movimentacao"], row["centro_custo"],
                    format_date_ui(row["data_lancamento"]), row["numero_nota_fiscal"], row["numero_boleto"],
                    row["quantidade_boletos"], format_date_ui(row["proximo_vencimento"]),
                    display_status, format_money(from_cents(row["valor_total_centavos"])),
                ),
                tags=(tag,) if tag else (),
            )

        balance = filtered_entries - filtered_expenses
        if hasattr(self, "summary_var"):
            self.summary_var.set(f"{len(rows)} registro(s)  •  Saldo {format_money(balance)}")
        if hasattr(self, "mini_summary_vars"):
            counts = self.db.alert_counts_detailed()
            self.mini_summary_vars["entries"].set(format_money(filtered_entries))
            self.mini_summary_vars["expenses"].set(format_money(filtered_expenses))
            self.mini_summary_vars["balance"].set(format_money(balance))
            self.mini_summary_vars["open"].set(str(counts["atrasados"] + counts["hoje"] + counts["amanha"]))
        self.refresh_alert_badge()

    def refresh_alert_badge(self) -> None:
        counts = self.db.alert_counts_detailed()
        total = counts["atrasados"] + counts["hoje"] + counts["amanha"]
        if hasattr(self, "alert_btn"):
            self.alert_btn.configure(text=f"Ver alertas ({total})" if total else "Ver alertas")
        if hasattr(self, "alert_banner_var"):
            if counts["atrasados"]:
                self.alert_banner_var.set(f"{counts['atrasados']} em atraso")
                bg, fg = THEME["red_soft"], THEME["red"]
            elif counts["hoje"]:
                self.alert_banner_var.set(f"{counts['hoje']} vence hoje")
                bg, fg = THEME["amber_soft"], THEME["amber_dark"]
            elif counts["amanha"]:
                self.alert_banner_var.set(f"{counts['amanha']} vence amanhã")
                bg, fg = THEME["amber_soft"], THEME["amber_dark"]
            else:
                self.alert_banner_var.set("Tudo em ordem")
                bg, fg = THEME["green_soft"], THEME["green"]
            if hasattr(self, "alert_status_chip"):
                self.alert_status_chip.configure(bg=bg, fg=fg)

    def _set_record_actions(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for btn in self.record_action_buttons:
            btn.configure(state=state)

    def load_selected_record(self, _event=None) -> None:
        super().load_selected_record(_event)
        self._refresh_company_info()
        if self.selected_id is not None:
            self._set_record_actions(True)

    def clear_form(self, keep_status: bool = False) -> None:
        super().clear_form(keep_status=keep_status)
        self._refresh_company_info()
        self._set_record_actions(False)

    def duplicate_record(self) -> None:
        had_selection = self.selected_id is not None
        super().duplicate_record()
        if had_selection and self.selected_id is None:
            self._set_record_actions(False)
