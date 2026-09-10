import tkinter as tk
from tkinter import messagebox, ttk

from config import ALERT_FILTERS
from core.dates import today_db
from core.finance import from_cents
from core.formatters import format_date_ui, format_money
from database.database import Database
from ui.bills_window import BillsWindow
from ui.fraud_window import FraudGuardWindow
from ui.theme import THEME

class AlertsWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, db: Database, on_change=None):
        super().__init__(master)
        self.configure(background=THEME["bg"])
        self.db = db
        self.on_change = on_change
        self.title("Central de alertas")
        self.geometry("1120x610")
        self.minsize(900, 500)
        self.transient(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Central de alertas", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(header, text="Acompanhe vencidos, vencimentos de hoje e compromissos dos próximos 7 dias.", style="Hint.TLabel").pack(anchor="w", pady=(3, 0))

        cards = ttk.Frame(self, padding=(16, 0, 16, 8))
        cards.grid(row=1, column=0, sticky="ew")
        for i in range(5):
            cards.columnconfigure(i, weight=1)
        self.count_vars = {}
        for i, (key, label) in enumerate((("atrasados", "Atrasados"), ("hoje", "Vencem hoje"), ("amanha", "Amanhã"), ("d3", "Próx. 3 dias"), ("d7", "Próx. 7 dias"))):
            card = ttk.Frame(cards, style="Card.TFrame", padding=10)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 0 if i == 4 else 4))
            ttk.Label(card, text=label, style="CardLabel.TLabel").pack(anchor="w")
            var = tk.StringVar(value="0")
            self.count_vars[key] = var
            ttk.Label(card, textvariable=var, style="CardValue.TLabel").pack(anchor="w", pady=(3, 0))

        filter_bar = ttk.Frame(self, padding=(16, 0, 16, 8))
        filter_bar.grid(row=2, column=0, sticky="ew")
        ttk.Label(filter_bar, text="Exibir:").pack(side="left")
        self.filter_var = tk.StringVar(value="Todos")
        combo = ttk.Combobox(filter_bar, textvariable=self.filter_var, values=ALERT_FILTERS, state="readonly", width=18)
        combo.pack(side="left", padx=(6, 8))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        ttk.Button(filter_bar, text="Atualizar", command=self.refresh).pack(side="left")

        area = ttk.Frame(self, padding=(16, 0, 16, 16))
        area.grid(row=3, column=0, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.rowconfigure(0, weight=1)

        cols = ("id", "alerta", "dias", "empresa", "nota", "boleto", "parcela", "vencimento", "valor")
        self.tree = ttk.Treeview(area, columns=cols, show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        headers = {"id": "ID", "alerta": "Alerta", "dias": "Prazo", "empresa": "Empresa", "nota": "Nota", "boleto": "Boleto", "parcela": "Parcela", "vencimento": "Vencimento", "valor": "Valor"}
        widths = {"id": 55, "alerta": 110, "dias": 90, "empresa": 220, "nota": 100, "boleto": 110, "parcela": 70, "vencimento": 110, "valor": 115}
        for col in cols:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w" if col in ("empresa", "centro") else "center")
        self.tree.tag_configure("late", background=THEME["red_soft"], foreground=THEME["red"])
        self.tree.tag_configure("today", background=THEME["amber_soft"], foreground=THEME["amber_dark"])
        self.tree.tag_configure("tomorrow", background=THEME["amber_soft"], foreground=THEME["amber_dark"])
        self.tree.tag_configure("soon", background=THEME["surface_alt"], foreground=THEME["muted"])

        yscroll = ttk.Scrollbar(area, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)

        actions = ttk.Frame(area)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Marcar selecionado como pago", style="Accent.TButton", command=self.mark_paid).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Abrir parcelas do lançamento", command=self.open_purchase_bills).pack(side="left")
        self.refresh()

    def open_fraud_guard(self) -> None:
        bill_id = self.selected_bill_id()
        if bill_id is None:
            return
        FraudGuardWindow(self, self.db, bill_id=bill_id, purchase_id=self.purchase_id)

    def mark_paid(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Alertas", "Selecione um boleto.", parent=self)
            return
        bill_id = int(self.tree.item(selection[0], "values")[0])
        self.db.set_bill_paid(bill_id, True, today_db())
        self.refresh()
        if self.on_change:
            self.on_change()

    def open_purchase_bills(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Alertas", "Selecione um boleto.", parent=self)
            return
        item = self.tree.item(selection[0])
        purchase_id = int(item["tags"][1]) if len(item.get("tags", ())) > 1 else None
        if purchase_id:
            BillsWindow(self, self.db, purchase_id, self.refresh)

    def refresh(self) -> None:
        counts = self.db.alert_counts_detailed()
        for key, var in self.count_vars.items():
            var.set(str(counts[key]))
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.db.list_alerts(self.filter_var.get()):
            if row["alerta"] == "Atrasado":
                tag = "late"
                prazo = f"{abs(int(row['dias']))} dia(s) atraso"
            elif row["alerta"] == "Vence hoje":
                tag = "today"
                prazo = "Hoje"
            elif row["alerta"] == "Vence amanhã":
                tag = "tomorrow"
                prazo = "1 dia"
            else:
                tag = "soon"
                prazo = f"{int(row['dias'])} dia(s)"
            self.tree.insert(
                "", tk.END, iid=str(row["boleto_id"]),
                values=(row["boleto_id"], row["alerta"], prazo, row["empresa"], row["numero_nota_fiscal"], row["numero_boleto"], row["parcela"], format_date_ui(row["vencimento"]), format_money(from_cents(row["valor_centavos"]))),
                tags=(tag, str(row["compra_id"])),
            )
