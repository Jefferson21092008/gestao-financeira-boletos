import json
import tkinter as tk
from tkinter import ttk

from database.database import Database
from ui.theme import THEME


ACTION_LABELS = {
    "usuario_inicial_criado": "Usuário inicial criado",
    "login_sucesso": "Login realizado",
    "login_falhou": "Tentativa de login falhou",
    "logout": "Sessão encerrada",
    "senha_alterada": "Senha alterada",
    "lancamento_criado": "Lançamento criado",
    "lancamento_atualizado": "Lançamento atualizado",
    "lancamento_excluido": "Lançamento excluído",
    "boleto_pago": "Boleto marcado como pago",
    "boleto_reaberto": "Boleto reaberto",
    "vencimento_boleto_alterado": "Vencimento alterado",
    "boleto_analisado": "Boleto analisado",
    "empresa_criada": "Empresa criada",
    "empresa_atualizada": "Empresa atualizada",
    "empresa_consultada_atualizada": "Cadastro de empresa atualizado",
    "backup_criado": "Backup criado",
    "backup_restaurado": "Backup restaurado",
}


class AuditWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, db: Database):
        super().__init__(master)
        self.db = db
        self.configure(background=THEME["bg"])
        self.title("Auditoria local")
        self.geometry("1100x650")
        self.minsize(850, 500)
        self.transient(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(18, 16, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Auditoria local", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Atualizar", command=self.refresh).pack(side="right")

        ttk.Label(
            self,
            text="Registra ações importantes no próprio banco: logins, alterações em lançamentos/boletos, análises antifraude e backups. Senhas nunca são gravadas no histórico.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        area = ttk.Frame(self, padding=(18, 0, 18, 18))
        area.grid(row=2, column=0, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.rowconfigure(0, weight=1)

        cols = ("quando", "ator", "acao", "entidade", "detalhes")
        self.tree = ttk.Treeview(area, columns=cols, show="headings", style="Clean.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew")
        headers = {"quando": "Data/hora", "ator": "Usuário", "acao": "Ação", "entidade": "Registro", "detalhes": "Detalhes"}
        widths = {"quando": 145, "ator": 110, "acao": 220, "entidade": 150, "detalhes": 430}
        for col in cols:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w")
        scroll = ttk.Scrollbar(area, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        self.refresh()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.db.list_audit_events(500):
            try:
                details = json.loads(row["detalhes_json"] or "{}")
                detail_text = " • ".join(f"{k}: {v}" for k, v in details.items())
            except (TypeError, json.JSONDecodeError):
                detail_text = row["detalhes_json"] or ""
            entity = row["entidade_tipo"] + (f" #{row['entidade_id']}" if row["entidade_id"] else "")
            self.tree.insert(
                "", tk.END,
                values=(row["criado_em"], row["ator"], ACTION_LABELS.get(row["acao"], row["acao"]), entity, detail_text),
            )
