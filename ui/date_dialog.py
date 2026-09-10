import tkinter as tk
from tkinter import ttk

class DateInputDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, title: str, prompt: str, initial: str = ""):
        super().__init__(master)
        self.result: str | None = None
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=prompt).pack(anchor="w")
        self.entry = ttk.Entry(frame, width=28)
        self.entry.pack(fill="x", pady=(6, 12))
        self.entry.insert(0, initial)
        self.entry.select_range(0, tk.END)
        self.entry.focus_set()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Confirmar", style="Accent.TButton", command=self.confirm).pack(side="right", padx=(0, 8))
        self.entry.bind("<Return>", lambda _e: self.confirm())
        self.bind("<Escape>", lambda _e: self.destroy())

    def confirm(self) -> None:
        self.result = self.entry.get().strip()
        self.destroy()
