import sqlite3
from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

from config import DATE_FMT_DB
from core.dates import status_from_values, today_db
from core.finance import from_cents
from core.formatters import format_date_ui, format_money, parse_date_ui
from database.database import Database
from ui.date_dialog import DateInputDialog
from ui.fraud_window import FraudGuardWindow
from ui.theme import THEME

class BillsWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, db: Database, purchase_id: int, on_change=None):
        super().__init__(master)
        self.configure(background=THEME["bg"])
        self.db = db
        self.purchase_id = purchase_id
        self.on_change = on_change
        self.title(f"Boletos / Parcelas - Lançamento #{purchase_id}")
        self.geometry("980x520")
        self.minsize(820, 440)
        self.transient(master)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(14, 12))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Gerenciamento de boletos", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Em dia = pago | Pendente = ainda no prazo | Atrasado = vencido e não pago",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))
        company = self.db.get_company_for_purchase(self.purchase_id)
        if company:
            company_name = company["nome_fantasia"] or company["razao_social"] or company["nome"]
            company_local = " / ".join(x for x in (company["municipio"], company["uf"]) if x)
            company_text = f"Empresa: {company_name}   •   CNPJ: {company['cnpj'] or 'não informado'}   •   Situação: {company['situacao_cadastral'] or 'cadastro local'}"
            if company_local:
                company_text += f"   •   {company_local}"
            tk.Label(header, text=company_text, bg=THEME["accent_soft"], fg=THEME["accent"], font=("Segoe UI Semibold", 8), anchor="w", padx=10, pady=7).grid(row=2, column=0, sticky="ew", pady=(8, 0))

        area = ttk.Frame(self, padding=(14, 0, 14, 12))
        area.grid(row=1, column=0, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.rowconfigure(0, weight=1)

        columns = ("id", "parcela", "numero", "vencimento", "valor", "status", "antifraude", "pagamento", "alerta")
        self.tree = ttk.Treeview(area, columns=columns, show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")

        headers = {
            "id": "ID",
            "parcela": "Parcela",
            "numero": "Boleto",
            "vencimento": "Vencimento",
            "valor": "Valor",
            "status": "Status",
            "antifraude": "Antifraude",
            "pagamento": "Data pagamento",
            "alerta": "Aviso",
        }
        widths = {"id": 50, "parcela": 65, "numero": 120, "vencimento": 105, "valor": 105,
                  "status": 90, "antifraude": 115, "pagamento": 115, "alerta": 120}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center" if col != "numero" else "w")

        self.tree.tag_configure("late", background=THEME["red_soft"], foreground=THEME["red"])
        self.tree.tag_configure("tomorrow", background=THEME["amber_soft"], foreground=THEME["amber_dark"])
        self.tree.tag_configure("paid", background=THEME["green_soft"], foreground=THEME["green"])

        yscroll = ttk.Scrollbar(area, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)

        actions = ttk.Frame(area)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Verificar antes de pagar", style="Primary.TButton", command=self.open_fraud_guard).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Marcar como pago", style="Accent.TButton", command=self.mark_paid).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Marcar como pendente", command=self.mark_pending).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Alterar vencimento", command=self.change_due_date).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Atualizar", command=self.refresh).pack(side="left")

        self.refresh()

    def selected_bill_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Boletos", "Selecione uma parcela primeiro.", parent=self)
            return None
        return int(self.tree.item(selection[0], "values")[0])

    def open_fraud_guard(self) -> None:
        bill_id = self.selected_bill_id()
        if bill_id is None:
            return
        FraudGuardWindow(self, self.db, bill_id=bill_id, purchase_id=self.purchase_id)

    def mark_paid(self) -> None:
        bill_id = self.selected_bill_id()
        if bill_id is None:
            return
        self.db.set_bill_paid(bill_id, True, today_db())
        self.refresh()
        if self.on_change:
            self.on_change()

    def mark_pending(self) -> None:
        bill_id = self.selected_bill_id()
        if bill_id is None:
            return
        self.db.set_bill_paid(bill_id, False, None)
        self.refresh()
        if self.on_change:
            self.on_change()

    def change_due_date(self) -> None:
        bill_id = self.selected_bill_id()
        if bill_id is None:
            return
        values = self.tree.item(self.tree.selection()[0], "values")
        current = values[3]

        dialog = DateInputDialog(self, "Alterar vencimento", "Novo vencimento (DD/MM/AAAA):", current)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            due = parse_date_ui(dialog.result, "o vencimento")
            assert due is not None
            self.db.update_bill_due_date(bill_id, due)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Vencimento", str(exc), parent=self)
            return
        self.refresh()
        if self.on_change:
            self.on_change()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        tomorrow = (date.today() + timedelta(days=1)).strftime(DATE_FMT_DB)
        for row in self.db.list_bills(self.purchase_id):
            status = status_from_values(int(row["pago"]), row["vencimento"])
            warning = ""
            tag = ""
            if status == "Em dia":
                tag = "paid"
            elif row["vencimento"] < today_db():
                warning = "Vencido"
                tag = "late"
            elif row["vencimento"] == tomorrow:
                warning = "Vence amanhã"
                tag = "tomorrow"

            self.tree.insert(
                "", tk.END, iid=str(row["id"]),
                values=(
                    row["id"], f"{row['parcela']}/{len(self.db.list_bills(self.purchase_id))}",
                    row["numero_boleto"], format_date_ui(row["vencimento"]),
                    format_money(from_cents(row["valor_centavos"])), status,
                    (lambda a: "Não analisado" if not a else ("Alto risco" if a["nivel"] == "ALTO" else "Atenção" if a["nivel"] == "ATENÇÃO" else "Baixo risco"))(self.db.latest_bill_analysis(int(row["id"]))),
                    format_date_ui(row["data_pagamento"]), warning,
                ),
                tags=(tag,) if tag else (),
            )
