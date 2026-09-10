import tkinter as tk

from config import APP_NAME
from core.app_logging import configure_logging
from core.paths import DB_PATH
from database.database import Database
from ui.login import LoginFrame
from ui.main_window import MainFrame
from ui.theme import configure_style


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.logger = configure_logging()
        self.title(APP_NAME)
        self.geometry("1440x880")
        self.minsize(1180, 720)
        self.db = Database(DB_PATH)
        try:
            self.db.create_daily_backup_if_needed()
        except Exception as exc:
            self.logger.exception("Falha no backup automático: %s", exc)
            try:
                self.db.audit_event("backup_automatico_falhou", details={"erro": str(exc)})
            except Exception:
                self.logger.exception("Também não foi possível registrar a falha do backup na auditoria.")
        configure_style(self)
        self.show_login(initial=True)

    def clear_root(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def show_login(self, initial: bool = False) -> None:
        if not initial:
            try:
                self.db.end_session()
            except Exception as exc:
                self.logger.exception("Falha ao registrar encerramento de sessão: %s", exc)
        self.clear_root()
        frame = LoginFrame(self, self.db, self.show_main)
        frame.pack(fill="both", expand=True)

    def show_main(self) -> None:
        self.clear_root()
        frame = MainFrame(self, self.db, self.show_login)
        frame.pack(fill="both", expand=True)
        frame.after(350, frame.show_startup_alerts)
