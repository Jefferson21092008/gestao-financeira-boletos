import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.paths import BACKUP_DIR
from database.database import Database
from ui.theme import THEME

class BackupWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, db: Database, on_restore=None):
        super().__init__(master)
        self.configure(background=THEME["bg"])
        self.db = db
        self.on_restore = on_restore
        self.title("Backups e restauração")
        self.geometry("900x560")
        self.minsize(760, 460)
        self.transient(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Backups e restauração", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(header, text="O sistema cria um backup automático por dia e mantém os 30 mais recentes.", style="Hint.TLabel").pack(anchor="w", pady=(3, 0))

        actions = ttk.Frame(self, padding=(16, 0, 16, 10))
        actions.grid(row=1, column=0, sticky="ew")
        ttk.Button(actions, text="Criar backup agora", style="Accent.TButton", command=self.create_now).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Restaurar selecionado", command=self.restore_selected).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Importar backup externo...", command=self.import_external).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Salvar cópia externa...", command=self.export_external).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Abrir pasta", command=self.open_folder).pack(side="left")

        area = ttk.Frame(self, padding=(16, 0, 16, 16))
        area.grid(row=2, column=0, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.rowconfigure(0, weight=1)
        cols = ("arquivo", "data", "tamanho")
        self.tree = ttk.Treeview(area, columns=cols, show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading("arquivo", text="Arquivo")
        self.tree.heading("data", text="Criado em")
        self.tree.heading("tamanho", text="Tamanho")
        self.tree.column("arquivo", width=450, anchor="w")
        self.tree.column("data", width=160, anchor="center")
        self.tree.column("tamanho", width=100, anchor="center")
        y = ttk.Scrollbar(area, orient="vertical", command=self.tree.yview)
        y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=y.set)
        self.path_by_iid: dict[str, Path] = {}
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.path_by_iid.clear()
        for idx, path in enumerate(self.db.list_backups()):
            stat = path.stat()
            size = stat.st_size / (1024 * 1024)
            created = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
            iid = str(idx)
            self.path_by_iid[iid] = path
            self.tree.insert("", tk.END, iid=iid, values=(path.name, created, f"{size:.2f} MB"))

    def selected_path(self) -> Path | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Backups", "Selecione um backup primeiro.", parent=self)
            return None
        return self.path_by_iid.get(sel[0])

    def create_now(self):
        try:
            path = self.db.create_backup("manual")
            self.refresh()
            messagebox.showinfo("Backup criado", f"Backup criado com sucesso:\n{path.name}", parent=self)
        except Exception as exc:
            messagebox.showerror("Backup", str(exc), parent=self)

    def restore_path(self, path: Path):
        if not messagebox.askyesno(
            "Confirmar restauração",
            "A restauração substituirá os dados atuais pelos dados do backup selecionado.\n\n"
            "Antes disso, o sistema criará automaticamente uma cópia de segurança do estado atual.\n\n"
            "Continuar?",
            parent=self,
        ):
            return
        try:
            self.db.restore_backup(path)
            self.refresh()
            if self.on_restore:
                self.on_restore()
            messagebox.showinfo("Restauração concluída", "Banco restaurado com sucesso.", parent=self)
        except Exception as exc:
            messagebox.showerror("Restauração", str(exc), parent=self)

    def restore_selected(self):
        path = self.selected_path()
        if path:
            self.restore_path(path)

    def import_external(self):
        filename = filedialog.askopenfilename(parent=self, title="Selecionar backup SQLite", filetypes=[("Banco SQLite", "*.db *.sqlite *.sqlite3"), ("Todos os arquivos", "*.*")])
        if filename:
            self.restore_path(Path(filename))


    def export_external(self):
        selected = self.path_by_iid.get(self.tree.selection()[0]) if self.tree.selection() else None
        suggested = selected.name if selected else f"gestao_empresas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        filename = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar cópia externa do backup",
            defaultextension=".db",
            initialfile=suggested,
            filetypes=[("Banco SQLite", "*.db"), ("Todos os arquivos", "*.*")],
        )
        if not filename:
            return
        try:
            path = self.db.export_backup(Path(filename), selected)
            messagebox.showinfo(
                "Cópia externa criada",
                f"Backup validado e salvo em:\n{path}\n\nGuarde essa cópia em outro dispositivo ou pasta de rede.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Backup externo", str(exc), parent=self)

    def open_folder(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(BACKUP_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(BACKUP_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(BACKUP_DIR)])
        except Exception as exc:
            messagebox.showerror("Pasta de backups", str(exc), parent=self)
