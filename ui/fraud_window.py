import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

from config import RECEITA_CNPJ_PORTAL_URL
from core.cnpj import cnpj_compact, format_cnpj
from core.finance import from_cents
from core.formatters import format_money, parse_money
from core.text import digits_only, normalize_text
from database.database import Database
from services.background import run_background_task
from services.fraud_service import calculate_fraud_risk, inspect_payment_code
from ui.theme import THEME

class FraudGuardWindow(tk.Toplevel):
    """Guardião Antifraude: triagem preventiva, local e explicável."""
    def __init__(self, master: tk.Misc, db: Database, *, bill_id: int | None = None, purchase_id: int | None = None):
        super().__init__(master)
        self.db = db
        self.bill_id = bill_id
        self.purchase_id = purchase_id
        self.configure(background=THEME["bg"])
        self.title("Guardião Antifraude de Boletos")
        self.geometry("1180x760")
        self.minsize(980, 660)
        self.transient(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, style="App.TFrame", padding=(22, 18, 22, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Guardião Antifraude", style="PageTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Verifique sinais de boleto falso antes de efetuar o pagamento.", style="PageSubtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 0))

        banner = tk.Frame(self, bg=THEME["amber_soft"], highlightbackground="#FDE68A", highlightthickness=1)
        banner.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 12))
        tk.Label(banner, text="Triagem preventiva", bg=THEME["amber_soft"], fg=THEME["amber_dark"], font=("Segoe UI Semibold", 9)).pack(side="left", padx=(12, 8), pady=9)
        tk.Label(banner, text="O sistema aponta inconsistências, mas não substitui a confirmação final no aplicativo/site oficial do banco.", bg=THEME["amber_soft"], fg="#7C5C00", font=("Segoe UI", 8)).pack(side="left", pady=9)

        body = ttk.Frame(self, style="App.TFrame", padding=(22, 0, 22, 18))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        self._build_input_card(body)
        self._build_result_card(body)
        self._prefill_context()
        self.refresh_history()

    def _build_input_card(self, parent):
        card = ttk.Frame(parent, style="Surface.TFrame", padding=18)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="1  Dados para conferência", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(card, text="Use exatamente os dados que aparecem no boleto e, principalmente, no banco antes de pagar.", style="CardHint.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 14))

        self.company_var = tk.StringVar()
        self.expected_doc_var = tk.StringVar()
        self.expected_value_var = tk.StringVar()
        self.line_var = tk.StringVar()
        self.shown_name_var = tk.StringVar()
        self.shown_doc_var = tk.StringVar()
        self.cnpj_online_result: dict | None = None
        self.cnpj_lookup_running = False
        self.cnpj_status_var = tk.StringVar(value="CNPJ ainda não consultado")
        self.cnpj_detail_var = tk.StringVar(value="A consulta online será feita automaticamente ao analisar quando houver um CNPJ de 14 caracteres. CNPJs alfanuméricos também são aceitos.")

        labels = [
            ("Empresa/beneficiário esperado", self.company_var, 2, 0),
            ("CNPJ/CPF esperado", self.expected_doc_var, 2, 1),
            ("Valor esperado", self.expected_value_var, 4, 0),
            ("CNPJ/CPF exibido pelo banco", self.shown_doc_var, 4, 1),
            ("Beneficiário exibido pelo banco", self.shown_name_var, 6, 0),
        ]
        for label, var, row, col in labels:
            ttk.Label(card, text=label, style="FieldLabel.TLabel").grid(row=row, column=col, sticky="w", padx=(0 if col == 0 else 8, 0), pady=(0, 5))
            if var is self.company_var:
                ent = ttk.Combobox(card, textvariable=var, values=[r["nome"] for r in self.db.list_companies("", limit=500)], state="normal")
                ent.bind("<KeyRelease>", self._company_guard_typing)
                ent.bind("<<ComboboxSelected>>", self._company_guard_selected)
                self.company_combo = ent
            else:
                ent = ttk.Entry(card, textvariable=var)
            ent.grid(row=row+1, column=col, sticky="ew", padx=(0 if col == 0 else 8, 8 if col == 0 else 0), pady=(0, 11))

        # Consulta cadastral online vinculada ao CNPJ exibido pelo banco (ou ao esperado,
        # quando o campo exibido estiver vazio).
        cnpj_box = tk.Frame(card, bg=THEME["accent_soft"], highlightbackground=THEME["accent_mid"], highlightthickness=1)
        cnpj_box.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(2, 12))
        cnpj_box.columnconfigure(0, weight=1)
        tk.Label(cnpj_box, text="VERIFICAÇÃO CADASTRAL ONLINE", bg=THEME["accent_soft"], fg=THEME["accent"], font=("Segoe UI Semibold", 8)).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))
        tk.Label(cnpj_box, textvariable=self.cnpj_status_var, bg=THEME["accent_soft"], fg=THEME["text"], font=("Segoe UI Semibold", 9)).grid(row=1, column=0, sticky="w", padx=10, pady=(2, 0))
        tk.Label(cnpj_box, textvariable=self.cnpj_detail_var, bg=THEME["accent_soft"], fg=THEME["muted"], font=("Segoe UI", 8), wraplength=430, justify="left").grid(row=2, column=0, sticky="w", padx=10, pady=(2, 8))
        cnpj_actions = tk.Frame(cnpj_box, bg=THEME["accent_soft"])
        cnpj_actions.grid(row=0, column=1, rowspan=3, sticky="e", padx=8, pady=8)
        self.lookup_cnpj_btn = ttk.Button(cnpj_actions, text="Consultar CNPJ", style="Secondary.TButton", command=self.lookup_cnpj_manual)
        self.lookup_cnpj_btn.pack(pady=(0, 4), fill="x")
        ttk.Button(cnpj_actions, text="Portal oficial", style="Ghost.TButton", command=self.open_receita_portal).pack(fill="x")

        ttk.Label(card, text="Linha digitável ou código de barras", style="FieldLabel.TLabel").grid(row=10, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.line_entry = ttk.Entry(card, textvariable=self.line_var, font=("Consolas", 10))
        self.line_entry.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Label(card, text="Aceita 44, 47 ou 48 dígitos. Pontos, espaços e traços são ignorados.", style="CardHint.TLabel").grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 14))

        actions = ttk.Frame(card, style="Surface.TFrame")
        actions.grid(row=13, column=0, columnspan=2, sticky="ew")
        self.analyze_btn = ttk.Button(actions, text="Analisar boleto", style="Primary.TButton", command=self.analyze)
        self.analyze_btn.pack(side="left")
        ttk.Button(actions, text="Limpar", style="Secondary.TButton", command=self.clear).pack(side="left", padx=(8, 0))

        ttk.Separator(card).grid(row=14, column=0, columnspan=2, sticky="ew", pady=16)
        ttk.Label(card, text="Histórico recente", style="CardTitle.TLabel").grid(row=15, column=0, columnspan=2, sticky="w", pady=(0, 8))
        cols = ("quando", "empresa", "risco")
        self.history = ttk.Treeview(card, columns=cols, show="headings", height=6, style="Clean.Treeview")
        self.history.grid(row=16, column=0, columnspan=2, sticky="nsew")
        card.rowconfigure(16, weight=1)
        for c, h, w in (("quando", "Quando", 125), ("empresa", "Empresa", 230), ("risco", "Risco", 90)):
            self.history.heading(c, text=h)
            self.history.column(c, width=w, anchor="w" if c == "empresa" else "center")

    def _build_result_card(self, parent):
        card = ttk.Frame(parent, style="Surface.TFrame", padding=18)
        card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(6, weight=1)
        ttk.Label(card, text="2  Resultado da triagem", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, text="O resultado é explicável: cada sinal encontrado aparece abaixo.", style="CardHint.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 12))

        self.risk_box = tk.Frame(card, bg=THEME["surface_alt"], highlightbackground=THEME["border"], highlightthickness=1)
        self.risk_box.grid(row=2, column=0, sticky="ew")
        self.risk_score_var = tk.StringVar(value="—")
        self.risk_label_var = tk.StringVar(value="Aguardando análise")
        tk.Label(self.risk_box, textvariable=self.risk_score_var, bg=THEME["surface_alt"], fg=THEME["text"], font=("Segoe UI Semibold", 28)).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(self.risk_box, textvariable=self.risk_label_var, bg=THEME["surface_alt"], fg=THEME["muted"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=14, pady=(0, 12))

        self.meta_var = tk.StringVar(value="Cole um boleto para iniciar a conferência.")
        ttk.Label(card, textvariable=self.meta_var, style="CardHint.TLabel", wraplength=420, justify="left").grid(row=3, column=0, sticky="w", pady=(10, 8))
        ttk.Separator(card).grid(row=4, column=0, sticky="ew", pady=(2, 10))
        ttk.Label(card, text="Sinais encontrados", style="CardTitle.TLabel").grid(row=5, column=0, sticky="w", pady=(0, 8))

        self.reason_text = tk.Text(card, height=13, wrap="word", bd=0, relief="flat", bg=THEME["surface"], fg=THEME["text"], font=("Segoe UI", 9), padx=2, pady=2)
        self.reason_text.grid(row=6, column=0, sticky="nsew")
        self.reason_text.tag_configure("ok", foreground=THEME["green"])
        self.reason_text.tag_configure("warn", foreground=THEME["amber_dark"])
        self.reason_text.tag_configure("danger", foreground=THEME["red"])
        self.reason_text.tag_configure("title", font=("Segoe UI Semibold", 9))
        self.reason_text.configure(state="disabled")

        footer = tk.Frame(card, bg=THEME["accent_soft"], highlightbackground=THEME["accent_mid"], highlightthickness=1)
        footer.grid(row=7, column=0, sticky="ew", pady=(12, 0))
        tk.Label(footer, text="Regra de ouro:", bg=THEME["accent_soft"], fg=THEME["accent"], font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=10, pady=(8, 0))
        tk.Label(footer, text="Se beneficiário, CPF/CNPJ ou valor exibidos pelo banco forem diferentes, não conclua o pagamento.", bg=THEME["accent_soft"], fg=THEME["text"], font=("Segoe UI", 8), wraplength=410, justify="left").pack(anchor="w", padx=10, pady=(2, 8))

        self.copy_code_btn = ttk.Button(card, text="Copiar código verificado", style="Secondary.TButton", command=self.copy_verified_code, state="disabled")
        self.copy_code_btn.grid(row=8, column=0, sticky="e", pady=(10, 0))

    def _company_guard_typing(self, _event=None):
        typed = self.company_var.get().strip()
        if hasattr(self, "company_combo"):
            self.company_combo.configure(values=[r["nome"] for r in self.db.list_companies(typed, limit=50)])

    def _company_guard_selected(self, _event=None):
        row = self.db.get_company_exact(self.company_var.get())
        if row:
            self.company_var.set(row["nome"])
            self.expected_doc_var.set(row["cnpj"] or "")

    def copy_verified_code(self):
        code = digits_only(self.line_var.get())
        if not code:
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        messagebox.showinfo("Guardião Antifraude", "Código verificado copiado para a área de transferência.", parent=self)

    def _prefill_context(self):
        if self.bill_id:
            row = self.db.get_bill_context(self.bill_id)
            if row:
                self.purchase_id = int(row["compra_id"])
                self.company_var.set(row["empresa"])
                self.expected_doc_var.set(row["cnpj"] or "")
                value = from_cents(row['valor_centavos']) if row['valor_centavos'] is not None else row['valor']
                self.expected_value_var.set(format_money(value).replace('R$ ', ''))
                self.line_entry.focus_set()

    def clear(self):
        self.line_var.set("")
        self.shown_name_var.set("")
        self.shown_doc_var.set("")
        if not self.bill_id:
            self.company_var.set("")
            self.expected_doc_var.set("")
            self.expected_value_var.set("")
        self.risk_score_var.set("—")
        self.risk_label_var.set("Aguardando análise")
        self.cnpj_online_result = None
        self.cnpj_status_var.set("CNPJ ainda não consultado")
        self.cnpj_detail_var.set("A consulta online será feita automaticamente ao analisar quando houver um CNPJ de 14 caracteres. CNPJs alfanuméricos também são aceitos.")
        self.meta_var.set("Cole um boleto para iniciar a conferência.")
        if hasattr(self, "copy_code_btn"):
            self.copy_code_btn.configure(state="disabled")
        self._set_reasons([])
        self.line_entry.focus_set()

    def _set_reasons(self, reasons: list[dict]):
        self.reason_text.configure(state="normal")
        self.reason_text.delete("1.0", tk.END)
        if not reasons:
            self.reason_text.insert(tk.END, "Nenhuma análise realizada ainda.", "warn")
        else:
            icons = {"ok": "✓", "warn": "!", "danger": "×"}
            for item in reasons:
                tag = item["level"]
                self.reason_text.insert(tk.END, f"{icons.get(tag, '•')}  {item['title']}\n", (tag, "title"))
                self.reason_text.insert(tk.END, f"    {item['detail']}\n\n", tag)
        self.reason_text.configure(state="disabled")

    def _document_for_online_lookup(self) -> str:
        shown = cnpj_compact(self.shown_doc_var.get())
        expected = cnpj_compact(self.expected_doc_var.get())
        return shown if len(shown) == 14 else expected if len(expected) == 14 else ""

    def open_receita_portal(self) -> None:
        webbrowser.open(RECEITA_CNPJ_PORTAL_URL)

    def _render_cnpj_result(self, result: dict) -> None:
        self.cnpj_online_result = result
        status = result.get("status")
        cached = " • cache local" if result.get("cached") else ""
        if status == "ok":
            situacao = result.get("situacao") or "NÃO INFORMADA"
            razao = result.get("razao_social") or "Razão social não informada"
            fantasia = result.get("nome_fantasia") or ""
            place = " / ".join(x for x in (result.get("municipio"), result.get("uf")) if x)
            self.cnpj_status_var.set(f"✓ {format_cnpj(result.get('cnpj', ''))} • {situacao}{cached}")
            detail = razao
            if fantasia and normalize_text(fantasia) != normalize_text(razao):
                detail += f" • Fantasia: {fantasia}"
            if place:
                detail += f" • {place}"
            detail += f" • Fonte: {result.get('source', 'consulta online')}"
            self.cnpj_detail_var.set(detail)
        elif status == "invalid":
            self.cnpj_status_var.set("× CNPJ inválido")
            self.cnpj_detail_var.set(result.get("message") or "Os dígitos verificadores do CNPJ não conferem.")
        elif status == "not_found":
            self.cnpj_status_var.set("× CNPJ não encontrado")
            self.cnpj_detail_var.set((result.get("message") or "CNPJ não encontrado.") + " Use o botão Portal oficial para uma conferência adicional.")
        elif status == "provider_unsupported":
            self.cnpj_status_var.set(f"✓ {format_cnpj(result.get('cnpj', ''))} • formato alfanumérico válido")
            self.cnpj_detail_var.set((result.get("message") or "Formato validado localmente.") + " A confirmação cadastral deve ser feita no Portal oficial.")
        else:
            self.cnpj_status_var.set("! Consulta online indisponível")
            self.cnpj_detail_var.set((result.get("message") or "Não foi possível consultar agora.") + " Isso não aumenta o risco por si só.")

    def _lookup_async(self, cnpj: str, callback, *, force_refresh: bool = False) -> None:
        if self.cnpj_lookup_running:
            return
        self.cnpj_lookup_running = True
        self.cnpj_status_var.set("Consultando cadastro na internet…")
        self.cnpj_detail_var.set("Aguarde. A janela continua responsiva durante a consulta.")
        if hasattr(self, "lookup_cnpj_btn"):
            self.lookup_cnpj_btn.configure(state="disabled")
        if hasattr(self, "analyze_btn"):
            self.analyze_btn.configure(state="disabled")

        def task():
            return self.db.lookup_cnpj(cnpj, force_refresh=force_refresh)

        def done(result, error):
            self.cnpj_lookup_running = False
            if hasattr(self, "lookup_cnpj_btn"):
                self.lookup_cnpj_btn.configure(state="normal")
            if hasattr(self, "analyze_btn"):
                self.analyze_btn.configure(state="normal")
            if error is not None:
                result = {
                    "status": "unavailable",
                    "cnpj": cnpj_compact(cnpj),
                    "source": "Consulta online",
                    "message": "Não foi possível concluir a consulta cadastral agora.",
                    "technical": str(error),
                }
            assert isinstance(result, dict)
            self._render_cnpj_result(result)
            callback(result)

        run_background_task(self, task, done)

    def lookup_cnpj_manual(self) -> None:
        cnpj = self._document_for_online_lookup()
        if not cnpj:
            messagebox.showinfo("Consulta de CNPJ", "Informe um CNPJ de 14 caracteres no campo exibido pelo banco ou no CNPJ esperado.", parent=self)
            return
        self._lookup_async(cnpj, lambda _result: None, force_refresh=True)

    def analyze(self):
        company = self.company_var.get().strip()
        line = self.line_var.get().strip()
        if not company:
            messagebox.showwarning("Guardião Antifraude", "Informe a empresa/beneficiário esperado.", parent=self)
            return
        if not line:
            messagebox.showwarning("Guardião Antifraude", "Cole a linha digitável ou o código de barras.", parent=self)
            return
        try:
            expected_value = parse_money(self.expected_value_var.get()) if self.expected_value_var.get().strip() else None
        except ValueError:
            messagebox.showwarning("Guardião Antifraude", "Valor esperado inválido.", parent=self)
            return

        context = {"company": company, "line": line, "expected_value": expected_value}
        cnpj = self._document_for_online_lookup()
        if cnpj:
            self._lookup_async(cnpj, lambda result: self._finish_analysis(context, result))
        else:
            self.cnpj_status_var.set("CNPJ não informado")
            self.cnpj_detail_var.set("A análise seguirá sem consulta cadastral online. CPF não é consultado por este módulo.")
            self._finish_analysis(context, None)

    def _finish_analysis(self, context: dict, cnpj_result: dict | None) -> None:
        company = context["company"]
        line = context["line"]
        expected_value = context["expected_value"]

        company_row = self.db.get_company_exact(company)
        empresa_id = int(company_row["id"]) if company_row else None
        if company_row and not self.expected_doc_var.get().strip():
            self.expected_doc_var.set(company_row["cnpj"] or "")

        inspection = inspect_payment_code(line)
        duplicate = self.db.boleto_duplicate_other_company(line, empresa_id)
        unusual = self.db.boleto_unusual_bank(empresa_id, inspection.get("bank_code", ""))
        prior_high = self.db.boleto_prior_high_risk(line)
        risk = calculate_fraud_risk(
            inspection,
            company,
            self.expected_doc_var.get(),
            self.shown_name_var.get(),
            self.shown_doc_var.get(),
            expected_value,
            duplicate,
            unusual,
            cnpj_result,
            prior_high_risk_same_line=prior_high,
        )

        self.db.save_boleto_analysis(
            compra_id=self.purchase_id,
            boleto_id=self.bill_id,
            empresa_id=empresa_id,
            empresa_nome=company,
            documento_esperado=self.expected_doc_var.get(),
            linha_digitavel=line,
            banco_codigo=inspection.get("bank_code", ""),
            valor_codificado=inspection.get("encoded_value"),
            valor_esperado=expected_value,
            beneficiario_exibido=self.shown_name_var.get(),
            documento_exibido=self.shown_doc_var.get(),
            risk=risk,
        )

        self.risk_score_var.set(f"{risk['score']}/100")
        self.risk_label_var.set(risk["label"])
        self.copy_code_btn.configure(state="normal" if risk["level"] == "BAIXO" else "disabled")
        if risk["level"] == "ALTO":
            bg, fg = THEME["red_soft"], THEME["red"]
        elif risk["level"] == "ATENÇÃO":
            bg, fg = THEME["amber_soft"], THEME["amber_dark"]
        else:
            bg, fg = THEME["green_soft"], THEME["green"]
        self.risk_box.configure(bg=bg, highlightbackground=fg)
        for widget in self.risk_box.winfo_children():
            widget.configure(bg=bg)
        children = self.risk_box.winfo_children()
        if children:
            try:
                children[0].configure(fg=fg)
            except Exception:
                pass

        value_text = format_money(inspection["encoded_value"]) if inspection.get("encoded_value") is not None else "não disponível"
        self.meta_var.set(
            f"{inspection['kind']} • Banco/segmento: {inspection.get('bank_code') or '—'} • Valor codificado: {value_text}\n"
            f"Decisão: {risk.get('decision', '')}"
        )
        extra_reasons = []
        for ok, title in inspection.get("details", []):
            if not ok:
                continue
            extra_reasons.append({"points": 0, "level": "ok", "title": title, "detail": "Verificação técnica concluída sem inconsistência nesse item."})
        self._set_reasons(risk["reasons"] + extra_reasons)
        self.refresh_history()

        if risk["level"] == "ALTO":
            messagebox.showerror("Guardião Antifraude", "Foram encontrados sinais fortes de risco. Não conclua o pagamento antes de confirmar o boleto por um canal oficial do beneficiário.", parent=self)
        elif risk["level"] == "ATENÇÃO":
            messagebox.showwarning("Guardião Antifraude", "Há pontos que precisam ser conferidos antes do pagamento.", parent=self)

    def refresh_history(self):
        if not hasattr(self, "history"):
            return
        for item in self.history.get_children():
            self.history.delete(item)
        for row in self.db.list_boleto_analyses(12):
            when = row["criado_em"][8:10] + "/" + row["criado_em"][5:7] + " " + row["criado_em"][11:16]
            self.history.insert("", tk.END, values=(when, row["empresa_nome"], f"{row['risco']}/100 {row['nivel']}"))
