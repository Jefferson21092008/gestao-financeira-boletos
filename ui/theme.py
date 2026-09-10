import tkinter as tk
from tkinter import ttk

THEME = {
    "bg": "#F4F7FB",
    "sidebar": "#111827",
    "sidebar_hover": "#1F2937",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "surface_hover": "#F1F5F9",
    "text": "#101828",
    "muted": "#667085",
    "border": "#E4E7EC",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "accent_soft": "#EFF6FF",
    "accent_mid": "#BFDBFE",
    "accent_light": "#2563EB",
    "green": "#16A34A",
    "green_soft": "#ECFDF3",
    "red": "#DC2626",
    "red_soft": "#FEF2F2",
    "amber": "#F59E0B",
    "amber_dark": "#B45309",
    "amber_soft": "#FFFBEB",
    "purple": "#7C3AED",
    "purple_soft": "#F5F3FF",
}


def configure_style(self) -> None:
    style = ttk.Style(self)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    self.option_add("*Font", ("Segoe UI", 9))
    self.option_add("*selectBackground", THEME["accent"])
    self.option_add("*selectForeground", "#FFFFFF")
    self.option_add("*TCombobox*Listbox.background", THEME["surface"])
    self.option_add("*TCombobox*Listbox.foreground", THEME["text"])
    self.option_add("*TCombobox*Listbox.selectBackground", THEME["accent"])
    self.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")

    bg = THEME["bg"]
    surface = THEME["surface"]
    surface_alt = THEME["surface_alt"]
    text = THEME["text"]
    muted = THEME["muted"]
    border = THEME["border"]
    accent = THEME["accent"]

    style.configure("App.TFrame", background=bg)
    style.configure("TFrame", background=bg)
    style.configure("Surface.TFrame", background=surface, relief="solid", borderwidth=1, bordercolor=border)
    style.configure("SubCard.TFrame", background=surface_alt, relief="solid", borderwidth=1, bordercolor=border)
    style.configure("SelectionBar.TFrame", background=THEME["accent_soft"])
    style.configure("Metric.TFrame", background=surface, relief="solid", borderwidth=1)
    style.configure("Card.TFrame", background=surface, relief="solid", borderwidth=1, bordercolor=border)

    style.configure("TLabel", background=bg, foreground=text)
    style.configure("PageTitle.TLabel", background=bg, foreground=text, font=("Segoe UI Semibold", 20))
    style.configure("PageSubtitle.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
    style.configure("HeaderDate.TLabel", background=bg, foreground=muted, font=("Segoe UI", 8))
    style.configure("HeaderStatus.TLabel", background=bg, foreground=muted, font=("Segoe UI Semibold", 9))
    style.configure("CardTitle.TLabel", background=surface, foreground=text, font=("Segoe UI Semibold", 11))
    style.configure("CardHint.TLabel", background=surface, foreground=muted, font=("Segoe UI", 8))
    style.configure("Required.TLabel", background=surface, foreground=THEME["red"], font=("Segoe UI Semibold", 8))
    style.configure("FieldLabel.TLabel", background=surface, foreground=muted, font=("Segoe UI Semibold", 8))
    style.configure("FilterLabel.TLabel", background=surface, foreground=muted, font=("Segoe UI Semibold", 8))
    style.configure("SearchHint.TLabel", background=surface, foreground="#98A2B3", font=("Segoe UI", 7))
    style.configure("TableSummary.TLabel", background=surface, foreground=accent, font=("Segoe UI Semibold", 8))
    style.configure("SelectionHint.TLabel", background=THEME["accent_soft"], foreground=accent, font=("Segoe UI", 8))
    style.configure("SubCardTitle.TLabel", background=surface_alt, foreground=text, font=("Segoe UI Semibold", 9))
    style.configure("SubCardHint.TLabel", background=surface_alt, foreground=muted, font=("Segoe UI", 7))
    style.configure("SubFieldLabel.TLabel", background=surface_alt, foreground=muted, font=("Segoe UI Semibold", 8))
    style.configure("MetricLabel.TLabel", background=surface, foreground=muted, font=("Segoe UI", 8))
    style.configure("MetricValue.TLabel", background=surface, foreground=text, font=("Segoe UI Semibold", 13))
    style.configure("LoginTitle.TLabel", background=surface, foreground=text, font=("Segoe UI Semibold", 18))
    style.configure("LoginSubtitle.TLabel", background=surface, foreground=muted, font=("Segoe UI", 9))

    # Compatibilidade visual com as janelas auxiliares.
    style.configure("Title.TLabel", background=bg, foreground=text, font=("Segoe UI Semibold", 18))
    style.configure("SectionTitle.TLabel", background=bg, foreground=text, font=("Segoe UI Semibold", 14))
    style.configure("Subtitle.TLabel", background=surface, foreground=muted, font=("Segoe UI", 9))
    style.configure("Hint.TLabel", background=bg, foreground=muted, font=("Segoe UI", 8))
    style.configure("Status.TLabel", background=bg, foreground=muted, font=("Segoe UI", 8))
    style.configure("Summary.TLabel", background=bg, foreground=text, font=("Segoe UI Semibold", 9))
    style.configure("Alert.TLabel", background=bg, foreground=THEME["red"], font=("Segoe UI Semibold", 8))
    style.configure("CardLabel.TLabel", background=surface, foreground=muted, font=("Segoe UI", 8))
    style.configure("CardValue.TLabel", background=surface, foreground=text, font=("Segoe UI Semibold", 13))

    style.configure("Primary.TButton", background=accent, foreground="#FFFFFF", bordercolor=accent, padding=(13, 7), font=("Segoe UI Semibold", 9))
    style.map("Primary.TButton", background=[("active", THEME["accent_hover"])], foreground=[("active", "#FFFFFF")])
    style.configure("Secondary.TButton", background=surface, foreground=text, bordercolor=border, padding=(11, 6), font=("Segoe UI Semibold", 8))
    style.map("Secondary.TButton", background=[("active", THEME["surface_hover"])], foreground=[("active", text)])
    style.configure("Ghost.TButton", background=surface, foreground=muted, bordercolor=surface, padding=(10, 6), font=("Segoe UI", 8))
    style.map("Ghost.TButton", background=[("active", surface_alt)], foreground=[("active", accent)])
    style.configure("Danger.TButton", background=THEME["red_soft"], foreground=THEME["red"], bordercolor="#FECACA", padding=(10, 6), font=("Segoe UI Semibold", 8))
    style.map("Danger.TButton", background=[("active", "#FEE2E2")], foreground=[("active", THEME["red"])])
    style.configure("DangerGhost.TButton", background=surface, foreground=THEME["red"], bordercolor="#FECACA", padding=(10, 6), font=("Segoe UI", 8))
    style.map("DangerGhost.TButton", background=[("active", THEME["red_soft"])], foreground=[("active", THEME["red"])])
    style.configure("Accent.TButton", background=accent, foreground="#FFFFFF", bordercolor=accent, padding=(12, 7), font=("Segoe UI Semibold", 9))
    style.map("Accent.TButton", background=[("active", THEME["accent_hover"])], foreground=[("active", "#FFFFFF")])
    style.configure("TButton", padding=(10, 6))

    style.configure("TEntry", fieldbackground="#FFFFFF", foreground=text, bordercolor=border, lightcolor=border, darkcolor=border, insertcolor=accent, padding=7)
    style.map("TEntry", bordercolor=[("focus", accent)], lightcolor=[("focus", accent)], darkcolor=[("focus", accent)])
    style.configure("TCombobox", fieldbackground="#FFFFFF", background="#FFFFFF", foreground=text, bordercolor=border, arrowcolor=muted, padding=6)
    style.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")], foreground=[("readonly", text)], selectbackground=[("readonly", accent)], selectforeground=[("readonly", "#FFFFFF")], bordercolor=[("focus", accent)])
    style.configure("TLabelframe", background=bg)
    style.configure("TLabelframe.Label", background=bg, foreground=text, font=("Segoe UI Semibold", 9))

    style.configure("Clean.Treeview", background=surface, fieldbackground=surface, foreground=text, rowheight=32, borderwidth=0, font=("Segoe UI", 8))
    style.configure("Clean.Treeview.Heading", background="#F2F4F7", foreground="#475467", relief="flat", font=("Segoe UI Semibold", 8))
    style.map("Clean.Treeview", background=[("selected", THEME["accent_soft"])], foreground=[("selected", accent)])
    style.configure("Treeview", rowheight=30, font=("Segoe UI", 8), background=surface, fieldbackground=surface, foreground=text)
    style.configure("Treeview.Heading", font=("Segoe UI Semibold", 8), background="#F2F4F7", foreground="#475467", relief="flat")
    style.map("Treeview", background=[("selected", THEME["accent_soft"])], foreground=[("selected", accent)])

    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure("TNotebook.Tab", background="#F2F4F7", foreground=muted, borderwidth=0, padding=(14, 7), font=("Segoe UI Semibold", 8))
    style.map("TNotebook.Tab", background=[("selected", accent), ("active", THEME["surface_hover"])], foreground=[("selected", "#FFFFFF"), ("active", text)])

    style.configure("Vertical.TScrollbar", background="#D0D5DD", troughcolor=bg, bordercolor=bg, arrowcolor=muted, darkcolor="#D0D5DD", lightcolor="#D0D5DD")
    style.configure("Horizontal.TScrollbar", background="#D0D5DD", troughcolor=bg, bordercolor=bg, arrowcolor=muted, darkcolor="#D0D5DD", lightcolor="#D0D5DD")
    style.map("Vertical.TScrollbar", background=[("active", "#98A2B3")])
    style.map("Horizontal.TScrollbar", background=[("active", "#98A2B3")])

    style.configure("TCheckbutton", background=bg, foreground=text, indicatorbackground="#FFFFFF", indicatorforeground=accent)
    style.map("TCheckbutton", background=[("active", bg)], foreground=[("active", accent)], indicatorbackground=[("selected", accent)])
    style.configure("Card.TCheckbutton", background=surface, foreground=muted, indicatorbackground="#FFFFFF", indicatorforeground=accent)
    style.map("Card.TCheckbutton", background=[("active", surface)], foreground=[("active", accent)], indicatorbackground=[("selected", accent)])

    self.configure(background=bg)
