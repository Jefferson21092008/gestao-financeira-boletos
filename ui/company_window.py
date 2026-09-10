import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

from config import RECEITA_CNPJ_PORTAL_URL
from core.cnpj import cnpj_compact, format_cnpj, validate_cnpj
from database.database import Database
from services.background import run_background_task
from ui.theme import THEME

class CompanyDirectoryWindow(tk.Toplevel):
    """Central de empresas: consulta CNPJ, cadastro automático e ficha local."""
    def __init__(self, master: tk.Misc, db: Database, on_change=None):
        super().__init__(master)
        self.db = db
        self.on_change = on_change
        self.configure(background=THEME["bg"])
        self.title("Empresas cadastradas")
        self.geometry("1180x760")
        self.minsize(960, 640)
        self.transient(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.lookup_running = False
        self.selected_company_id: int | None = None

        header = ttk.Frame(self, style="App.TFrame", padding=(22, 18, 22, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Empresas cadastradas", style="PageTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Consulte um CNPJ uma vez. Depois, os lançamentos e boletos usam somente o cadastro local.",
            style="PageSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        register = ttk.Frame(self, style="Surface.TFrame", padding=16)
        register.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 12))
        register.columnconfigure(1, weight=1)
        ttk.Label(register, text="Cadastrar empresa pelo CNPJ", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(register, text="Digite o CNPJ e o sistema buscará os dados cadastrais e salvará a empresa automaticamente.", style="CardHint.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 10))
        ttk.Label(register, text="CNPJ", style="FieldLabel.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8))
        self.cnpj_var = tk.StringVar()
        self.cnpj_entry = ttk.Entry(register, textvariable=self.cnpj_var, font=("Segoe UI", 10))
        self.cnpj_entry.grid(row=2, column=1, sticky="ew", padx=(0, 8))
        self.lookup_btn = ttk.Button(register, text="Consultar e cadastrar", style="Primary.TButton", command=self.lookup_and_register)
        self.lookup_btn.grid(row=2, column=2, sticky="e")
        self.lookup_status_var = tk.StringVar(value="Informe um CNPJ para iniciar.")
        ttk.Label(register, textvariable=self.lookup_status_var, style="CardHint.TLabel").grid(row=3, column=1, columnspan=2, sticky="w", pady=(6, 0))

        body = ttk.Frame(self, style="App.TFrame", padding=(22, 0, 22, 20))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        list_card = ttk.Frame(body, style="Surface.TFrame", padding=16)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        list_card.columnconfigure(0, weight=1)
        list_card.rowconfigure(3, weight=1)
        ttk.Label(list_card, text="Cadastro local", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        search = ttk.Entry(list_card, textvariable=self.search_var)
        search.grid(row=1, column=0, sticky="ew", pady=(8, 4))
        search.bind("<KeyRelease>", lambda _e: self.refresh())
        ttk.Label(list_card, text="Pesquise por razão social, nome fantasia, CNPJ ou cidade.", style="CardHint.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 8))

        cols = ("id", "empresa", "cnpj", "situacao", "local")
        self.tree = ttk.Treeview(list_card, columns=cols, show="headings", selectmode="browse", style="Clean.Treeview")
        self.tree.grid(row=3, column=0, sticky="nsew")
        headers = {"id":"ID", "empresa":"Empresa", "cnpj":"CNPJ", "situacao":"Situação", "local":"Cidade / UF"}
        widths = {"id":50, "empresa":270, "cnpj":145, "situacao":100, "local":150}
        for col in cols:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w" if col in ("empresa", "local") else "center")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        yscroll = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=3, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)

        detail = ttk.Frame(body, style="Surface.TFrame", padding=18)
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        detail.columnconfigure(0, weight=1)
        ttk.Label(detail, text="Ficha da empresa", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(detail, text="Dados usados automaticamente na conferência dos boletos.", style="CardHint.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 12))
        self.detail_title_var = tk.StringVar(value="Selecione uma empresa")
        self.detail_var = tk.StringVar(value="A ficha cadastral aparecerá aqui.")
        self.detail_title = tk.Label(detail, textvariable=self.detail_title_var, bg=THEME["accent_soft"], fg=THEME["accent"], font=("Segoe UI Semibold", 11), anchor="w", padx=12, pady=10, wraplength=390, justify="left")
        self.detail_title.grid(row=2, column=0, sticky="ew")
        tk.Label(detail, textvariable=self.detail_var, bg=THEME["surface"], fg=THEME["text"], font=("Segoe UI", 9), anchor="nw", justify="left", wraplength=390).grid(row=3, column=0, sticky="new", pady=(12, 12))

        actions = ttk.Frame(detail, style="Surface.TFrame")
        actions.grid(row=4, column=0, sticky="ew")
        self.refresh_btn = ttk.Button(actions, text="Atualizar cadastro online", style="Secondary.TButton", command=self.refresh_selected_online, state="disabled")
        self.refresh_btn.pack(side="left")
        ttk.Button(actions, text="Portal oficial", style="Ghost.TButton", command=lambda: webbrowser.open(RECEITA_CNPJ_PORTAL_URL)).pack(side="left", padx=(8, 0))

        self.refresh()
        self.cnpj_entry.focus_set()

    def lookup_and_register(self):
        raw = self.cnpj_var.get().strip()
        if not raw:
            messagebox.showwarning("Empresas", "Informe o CNPJ da empresa.", parent=self)
            return
        if not validate_cnpj(raw):
            messagebox.showwarning("CNPJ inválido", "O CNPJ informado não passou na validação dos dígitos verificadores.", parent=self)
            return
        if self.lookup_running:
            return
        self.lookup_running = True
        self.lookup_btn.configure(state="disabled")
        self.refresh_btn.configure(state="disabled")
        self.lookup_status_var.set("Consultando cadastro público...")
        self._start_company_lookup(raw, False)

    def _start_company_lookup(self, cnpj: str, force: bool) -> None:
        def task():
            return self.db.lookup_cnpj(cnpj, force_refresh=force)

        def done(result, error):
            if error is not None:
                result = {"status": "unavailable", "message": str(error), "cnpj": cnpj_compact(cnpj)}
            assert isinstance(result, dict)
            self._finish_lookup(result)

        run_background_task(self, task, done)

    def _finish_lookup(self, result: dict):
        self.lookup_running = False
        self.lookup_btn.configure(state="normal")
        self.refresh_btn.configure(state="normal" if self.selected_company_id else "disabled")
        status = result.get("status")
        if status == "ok":
            try:
                company_id = self.db.upsert_company_from_lookup(result)
            except Exception as exc:
                messagebox.showerror("Cadastro da empresa", str(exc), parent=self)
                return
            self.lookup_status_var.set(f"Empresa cadastrada/atualizada: {result.get('razao_social') or result.get('nome_fantasia') or format_cnpj(result.get('cnpj',''))}")
            self.cnpj_var.set(format_cnpj(result.get("cnpj", "")))
            self.refresh(select_id=company_id)
            if self.on_change:
                self.on_change()
        elif status == "provider_unsupported":
            self.lookup_status_var.set(result.get("message", "Consulta automática ainda não suporta esse formato."))
            messagebox.showinfo("CNPJ alfanumérico", result.get("message", "Confirme o cadastro no portal oficial."), parent=self)
        else:
            self.lookup_status_var.set(result.get("message", "Não foi possível consultar o CNPJ."))
            messagebox.showwarning("Consulta de CNPJ", result.get("message", "Não foi possível consultar o CNPJ."), parent=self)

    def refresh(self, select_id: int | None = None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.db.list_companies(self.search_var.get(), limit=500)
        for row in rows:
            display = row["nome_fantasia"] or row["razao_social"] or row["nome"]
            local = " / ".join(x for x in (row["municipio"], row["uf"]) if x)
            self.tree.insert("", tk.END, iid=str(row["id"]), values=(row["id"], display, row["cnpj"], row["situacao_cadastral"] or "Cadastro local", local))
        if select_id is not None and self.tree.exists(str(select_id)):
            self.tree.selection_set(str(select_id))
            self.tree.focus(str(select_id))
            self.tree.see(str(select_id))
            self.on_select()

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            self.selected_company_id = None
            self.refresh_btn.configure(state="disabled")
            return
        self.selected_company_id = int(sel[0])
        row = self.db.get_company(self.selected_company_id)
        if not row:
            return
        title = row["nome_fantasia"] or row["razao_social"] or row["nome"]
        self.detail_title_var.set(title)
        address = ", ".join(x for x in (row["logradouro"], row["numero_endereco"], row["bairro"]) if x)
        city = " / ".join(x for x in (row["municipio"], row["uf"]) if x)
        lines = [
            f"Razão social: {row['razao_social'] or row['nome']}",
            f"CNPJ: {row['cnpj'] or 'Não informado'}",
            f"Situação: {row['situacao_cadastral'] or 'Ainda não consultada'}",
            f"Local: {city or 'Não informado'}",
        ]
        if address:
            lines.append(f"Endereço: {address}")
        if row["cep"]:
            lines.append(f"CEP: {row['cep']}")
        if row["telefone"]:
            lines.append(f"Telefone: {row['telefone']}")
        if row["email"]:
            lines.append(f"E-mail: {row['email']}")
        if row["natureza_juridica"]:
            lines.append(f"Natureza jurídica: {row['natureza_juridica']}")
        lines.append(f"Última consulta: {row['consultado_em'] or 'Não realizada'}")
        self.detail_var.set("\n\n".join(lines))
        self.refresh_btn.configure(state="normal" if row["cnpj"] else "disabled")

    def refresh_selected_online(self):
        if not self.selected_company_id or self.lookup_running:
            return
        row = self.db.get_company(self.selected_company_id)
        if not row or not row["cnpj"]:
            return
        if not validate_cnpj(row["cnpj"]):
            messagebox.showwarning("Empresas", "O CNPJ salvo não passa na validação local.", parent=self)
            return
        self.lookup_running = True
        self.lookup_btn.configure(state="disabled")
        self.refresh_btn.configure(state="disabled")
        self.lookup_status_var.set(f"Atualizando {row['cnpj']}...")
        self._start_company_lookup(row["cnpj"], True)
