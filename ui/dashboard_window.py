import tkinter as tk
from tkinter import messagebox, ttk

from config import MOVEMENT_TYPES
from core.finance import from_cents
from core.formatters import format_date_ui, format_money, parse_date_ui
from database.database import Database
from ui.theme import THEME

class DashboardWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, db: Database):
        super().__init__(master)
        self.configure(background=THEME["bg"])
        self.db = db
        self.title("Dashboard / Relatório")
        self.geometry("1220x760")
        self.minsize(980, 650)
        self.transient(master)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        title = ttk.Frame(self, padding=(16, 14, 16, 8))
        title.grid(row=0, column=0, sticky="ew")
        ttk.Label(title, text="Dashboard financeiro", style="Title.TLabel").pack(side="left")

        filters = ttk.LabelFrame(self, text="Filtros do relatório", padding=12)
        filters.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        for i in range(10):
            filters.columnconfigure(i, weight=1 if i in (1, 3, 5, 7) else 0)

        self.start_var = tk.StringVar()
        self.end_var = tk.StringVar()
        self.type_var = tk.StringVar(value="Todos")
        self.cost_var = tk.StringVar(value="Todos")

        ttk.Label(filters, text="Data inicial:").grid(row=0, column=0, sticky="w")
        ttk.Entry(filters, textvariable=self.start_var, width=14).grid(row=0, column=1, sticky="ew", padx=(6, 16))
        ttk.Label(filters, text="Data final:").grid(row=0, column=2, sticky="w")
        ttk.Entry(filters, textvariable=self.end_var, width=14).grid(row=0, column=3, sticky="ew", padx=(6, 16))
        ttk.Label(filters, text="Tipo:").grid(row=0, column=4, sticky="w")
        ttk.Combobox(filters, textvariable=self.type_var, values=("Todos",) + MOVEMENT_TYPES, state="readonly", width=15).grid(row=0, column=5, sticky="ew", padx=(6, 16))
        ttk.Label(filters, text="Centro:").grid(row=0, column=6, sticky="w")
        ttk.Combobox(filters, textvariable=self.cost_var, values=("Todos",) + tuple(self.db.list_cost_centers()), state="readonly", width=15).grid(row=0, column=7, sticky="ew", padx=(6, 16))
        ttk.Button(filters, text="Aplicar", style="Accent.TButton", command=self.refresh).grid(row=0, column=8, padx=(0, 8))
        ttk.Button(filters, text="Limpar", command=self.clear_filters).grid(row=0, column=9)
        ttk.Label(filters, text="Datas no formato DD/MM/AAAA. Deixe em branco para considerar todo o período.", style="Hint.TLabel").grid(row=1, column=0, columnspan=10, sticky="w", pady=(8, 0))

        cards = ttk.Frame(self, padding=(16, 0, 16, 10))
        cards.grid(row=2, column=0, sticky="ew")
        for i in range(6):
            cards.columnconfigure(i, weight=1)

        self.card_vars: dict[str, tk.StringVar] = {}
        card_defs = [
            ("entradas", "Entradas"), ("despesas", "Despesas"), ("saldo", "Saldo"),
            ("qtd", "Lançamentos"), ("atrasados", "Boletos atrasados"), ("amanha", "Vencem amanhã")
        ]
        for col, (key, label) in enumerate(card_defs):
            card = ttk.Frame(cards, style="Card.TFrame", padding=12)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 5, 0 if col == 5 else 5))
            ttk.Label(card, text=label, style="CardLabel.TLabel").pack(anchor="w")
            var = tk.StringVar(value="-")
            self.card_vars[key] = var
            ttk.Label(card, textvariable=var, style="CardValue.TLabel").pack(anchor="w", pady=(5, 0))

        notebook = ttk.Notebook(self)
        notebook.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))

        report_tab = ttk.Frame(notebook, padding=10)
        monthly_tab = ttk.Frame(notebook, padding=10)
        notebook.add(report_tab, text="Lançamentos")
        notebook.add(monthly_tab, text="Resumo mensal")

        report_tab.columnconfigure(0, weight=1)
        report_tab.rowconfigure(0, weight=1)
        cols = ("id", "data", "tipo", "centro", "empresa", "nota", "status", "total")
        self.report_tree = ttk.Treeview(report_tab, columns=cols, show="headings")
        self.report_tree.grid(row=0, column=0, sticky="nsew")
        headers = {"id": "ID", "data": "Data", "tipo": "Tipo", "centro": "Centro de custo", "empresa": "Empresa", "nota": "Nota", "status": "Status", "total": "Total"}
        widths = {"id": 55, "data": 100, "tipo": 90, "centro": 130, "empresa": 240, "nota": 110, "status": 120, "total": 130}
        for col in cols:
            self.report_tree.heading(col, text=headers[col])
            self.report_tree.column(col, width=widths[col], anchor="w" if col in ("empresa", "centro") else "center")
        self.report_tree.tag_configure("Entrada", background=THEME["green_soft"], foreground=THEME["green"])
        self.report_tree.tag_configure("Despesa", background=THEME["red_soft"], foreground=THEME["red"])
        y1 = ttk.Scrollbar(report_tab, orient="vertical", command=self.report_tree.yview)
        y1.grid(row=0, column=1, sticky="ns")
        self.report_tree.configure(yscrollcommand=y1.set)

        monthly_tab.columnconfigure(0, weight=1)
        monthly_tab.rowconfigure(0, weight=1)
        mcols = ("mes", "qtd", "entradas", "despesas", "saldo")
        self.month_tree = ttk.Treeview(monthly_tab, columns=mcols, show="headings")
        self.month_tree.grid(row=0, column=0, sticky="nsew")
        mheaders = {"mes": "Mês", "qtd": "Lançamentos", "entradas": "Entradas", "despesas": "Despesas", "saldo": "Saldo"}
        for col, width in zip(mcols, (120, 100, 160, 160, 160)):
            self.month_tree.heading(col, text=mheaders[col])
            self.month_tree.column(col, width=width, anchor="center")
        y2 = ttk.Scrollbar(monthly_tab, orient="vertical", command=self.month_tree.yview)
        y2.grid(row=0, column=1, sticky="ns")
        self.month_tree.configure(yscrollcommand=y2.set)

        self.refresh()

    def get_filters(self) -> tuple[str | None, str | None, str, str]:
        start = parse_date_ui(self.start_var.get(), "a data inicial", allow_empty=True)
        end = parse_date_ui(self.end_var.get(), "a data final", allow_empty=True)
        if start and end and start > end:
            raise ValueError("A data inicial não pode ser posterior à data final.")
        return start, end, self.type_var.get(), self.cost_var.get()

    def clear_filters(self) -> None:
        self.start_var.set("")
        self.end_var.set("")
        self.type_var.set("Todos")
        self.cost_var.set("Todos")
        self.refresh()

    def refresh(self) -> None:
        try:
            start, end, movement_type, cost_center = self.get_filters()
        except ValueError as exc:
            messagebox.showerror("Filtros", str(exc), parent=self)
            return

        summary = self.db.filtered_summary(start, end, movement_type, cost_center)
        self.card_vars["entradas"].set(format_money(summary["entradas"]))
        self.card_vars["despesas"].set(format_money(summary["despesas"]))
        self.card_vars["saldo"].set(format_money(summary["saldo"]))
        self.card_vars["qtd"].set(str(summary["qtd"]))
        self.card_vars["atrasados"].set(str(summary["atrasados"]))
        self.card_vars["amanha"].set(str(summary["amanha"]))

        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        rows = self.db.list_purchases("", start, end, movement_type, "Todos", cost_center)
        for row in rows:
            status = row["status"] + (" • vence amanhã" if row["vence_amanha"] else "")
            self.report_tree.insert(
                "", tk.END,
                values=(row["id"], format_date_ui(row["data_lancamento"]), row["tipo_movimentacao"], row["centro_custo"], row["empresa"], row["numero_nota_fiscal"], status, format_money(row["valor_total"])),
                tags=(row["tipo_movimentacao"],),
            )

        for item in self.month_tree.get_children():
            self.month_tree.delete(item)
        for row in self.db.monthly_summary(start, end, movement_type, cost_center):
            year, month = row["mes"].split("-")
            label = f"{month}/{year}"
            entradas = from_cents(row["entradas_centavos"])
            despesas = from_cents(row["despesas_centavos"])
            self.month_tree.insert(
                "", tk.END,
                values=(label, row["qtd"], format_money(entradas), format_money(despesas), format_money(entradas - despesas)),
            )
