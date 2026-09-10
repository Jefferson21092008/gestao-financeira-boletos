import tkinter as tk
from tkinter import messagebox, ttk

from config import DEFAULT_USER
from database.database import Database
from ui.theme import THEME


class PasswordChangeDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, db: Database, username: str):
        super().__init__(master)
        self.db = db
        self.username = username
        self.result = False
        self.title("Defina uma nova senha")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        card = ttk.Frame(self, padding=24)
        card.grid(row=0, column=0, sticky="nsew")
        ttk.Label(card, text="Troca de senha obrigatória", style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            card,
            text="Esta instalação ainda usa a credencial padrão de uma versão anterior. Crie uma senha própria antes de continuar.",
            wraplength=430,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 16))

        self.password = ttk.Entry(card, show="•", width=38)
        self.confirm = ttk.Entry(card, show="•", width=38)
        ttk.Label(card, text="Nova senha").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.password.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(card, text="Confirmar senha").grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.confirm.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        ttk.Button(card, text="Salvar nova senha", style="Primary.TButton", command=self.save).grid(row=6, column=0, columnspan=2, sticky="ew")
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.password.bind("<Return>", lambda _e: self.confirm.focus_set())
        self.confirm.bind("<Return>", lambda _e: self.save())
        self.password.focus_set()

    def save(self) -> None:
        password = self.password.get()
        if password != self.confirm.get():
            messagebox.showerror("Senha", "As duas senhas não são iguais.", parent=self)
            return
        try:
            self.db.force_change_password(self.username, password)
        except ValueError as exc:
            messagebox.showerror("Senha", str(exc), parent=self)
            return
        self.result = True
        self.destroy()

    def cancel(self) -> None:
        self.result = False
        self.destroy()


class LoginFrame(ttk.Frame):
    """Login local. Em banco novo, cria o administrador sem senha padrão."""

    def __init__(self, master: tk.Misc, db: Database, on_success):
        super().__init__(master, style="App.TFrame", padding=24)
        self.db = db
        self.on_success = on_success
        self.first_setup = not db.has_users()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = ttk.Frame(self, padding=(34, 30), style="Card.TFrame")
        card.grid(row=0, column=0)
        card.columnconfigure(0, weight=1)

        brand = tk.Frame(card, bg=THEME["surface"])
        brand.grid(row=0, column=0, sticky="w", pady=(0, 20))
        tk.Label(brand, text="GF", bg=THEME["accent"], fg="#FFFFFF", font=("Segoe UI Semibold", 12), width=3, height=1).pack(side="left")
        tk.Label(brand, text="Gestão Financeira", bg=THEME["surface"], fg=THEME["text"], font=("Segoe UI Semibold", 12)).pack(side="left", padx=(10, 0))

        title = "Configure o primeiro acesso" if self.first_setup else "Bem-vindo"
        subtitle = (
            "Crie a senha do administrador deste computador. Nenhuma senha padrão será utilizada."
            if self.first_setup
            else "Entre para acessar lançamentos, vencimentos, auditoria e o Guardião Antifraude."
        )
        ttk.Label(card, text=title, style="LoginTitle.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(card, text=subtitle, style="LoginSubtitle.TLabel", wraplength=430, justify="left").grid(row=2, column=0, sticky="w", pady=(5, 22))

        ttk.Label(card, text="Usuário", style="FieldLabel.TLabel").grid(row=3, column=0, sticky="w")
        self.username = ttk.Entry(card, width=38)
        self.username.grid(row=4, column=0, sticky="ew", pady=(5, 14))
        self.username.insert(0, DEFAULT_USER)
        if self.first_setup:
            self.username.configure(state="readonly")

        ttk.Label(card, text="Senha" if not self.first_setup else "Nova senha", style="FieldLabel.TLabel").grid(row=5, column=0, sticky="w")
        self.password = ttk.Entry(card, width=38, show="•")
        self.password.grid(row=6, column=0, sticky="ew", pady=(5, 8))

        self.confirm = None
        row = 7
        if self.first_setup:
            ttk.Label(card, text="Confirmar senha", style="FieldLabel.TLabel").grid(row=row, column=0, sticky="w", pady=(6, 0))
            self.confirm = ttk.Entry(card, width=38, show="•")
            self.confirm.grid(row=row + 1, column=0, sticky="ew", pady=(5, 8))
            row += 2

        self.show_password = tk.BooleanVar(value=False)
        ttk.Checkbutton(card, text="Mostrar senha", variable=self.show_password, command=self.toggle_password, style="Card.TCheckbutton").grid(row=row, column=0, sticky="w", pady=(0, 18))
        row += 1

        button_text = "Criar acesso e entrar" if self.first_setup else "Entrar no sistema"
        ttk.Button(card, text=button_text, style="Primary.TButton", command=self.login).grid(row=row, column=0, sticky="ew")
        row += 1

        info = tk.Frame(card, bg=THEME["accent_soft"], highlightthickness=0)
        info.grid(row=row, column=0, sticky="ew", pady=(16, 0))
        info_text = (
            "A senha fica somente neste computador, armazenada com hash e salt. Use pelo menos 8 caracteres."
            if self.first_setup
            else "Os dados e o histórico permanecem armazenados localmente neste computador."
        )
        tk.Label(info, text=info_text, bg=THEME["accent_soft"], fg=THEME["accent"], font=("Segoe UI", 8), padx=10, pady=8, wraplength=410, justify="left").pack(anchor="w")

        self.password.bind("<Return>", lambda _event: self.confirm.focus_set() if self.confirm else self.login())
        if self.confirm:
            self.confirm.bind("<Return>", lambda _event: self.login())
        else:
            self.username.bind("<Return>", lambda _event: self.password.focus_set())
        self.password.focus_set()

    def toggle_password(self) -> None:
        show = "" if self.show_password.get() else "•"
        self.password.configure(show=show)
        if self.confirm is not None:
            self.confirm.configure(show=show)

    def login(self) -> None:
        username = self.username.get().strip()
        if self.first_setup:
            if self.confirm is None or self.password.get() != self.confirm.get():
                messagebox.showerror("Primeiro acesso", "As duas senhas não são iguais.")
                return
            try:
                self.db.create_initial_admin(self.password.get(), username)
            except ValueError as exc:
                messagebox.showerror("Primeiro acesso", str(exc))
                return
            self.on_success()
            return

        if not self.db.authenticate(username, self.password.get()):
            messagebox.showerror("Não foi possível entrar", "Confira o usuário e a senha e tente novamente.")
            self.password.delete(0, tk.END)
            self.password.focus_set()
            return

        if self.db.user_requires_password_change(username):
            dialog = PasswordChangeDialog(self, self.db, username)
            self.wait_window(dialog)
            if not dialog.result:
                self.db.end_session()
                return
        self.on_success()
