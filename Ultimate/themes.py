"""
XAU AI PRO - Theme Engine
Gerenciador de temas visuais para a interface desktop.
Temas disponiveis: dark, light, cyberpunk, crypto, midnight.
"""

from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "name": "Dark",
        "bg": "#1e1f24",
        "fg": "#e6e6e6",
        "sel": "#cfd0d6",
        "bsel": "#2d2f36",
        "accent": "#3a5a8a",
        "accent_hover": "#4a6aaa",
        "border": "#3a3d45",
        "success": "#0a0",
        "danger": "#d00",
        "warning": "#f90",
        "chart_up": "#26a69a",
        "chart_down": "#ef5350",
    },
    "light": {
        "name": "Light",
        "bg": "#f4f5f7",
        "fg": "#1a1a1a",
        "sel": "#0a0a0a",
        "bsel": "#e0e0e0",
        "accent": "#1976d2",
        "accent_hover": "#1565c0",
        "border": "#c0c0c0",
        "success": "#2e7d32",
        "danger": "#c62828",
        "warning": "#ed6c02",
        "chart_up": "#2e7d32",
        "chart_down": "#c62828",
    },
    "cyberpunk": {
        "name": "Cyberpunk",
        "bg": "#0a0a12",
        "fg": "#00ff9d",
        "sel": "#ff00ff",
        "bsel": "#12121f",
        "accent": "#ff00ff",
        "accent_hover": "#ff33ff",
        "border": "#00ff9d",
        "success": "#00ff9d",
        "danger": "#ff0055",
        "warning": "#ffcc00",
        "chart_up": "#00ff9d",
        "chart_down": "#ff0055",
    },
    "crypto": {
        "name": "Crypto",
        "bg": "#0d1b2a",
        "fg": "#e0e1dd",
        "sel": "#ffd700",
        "bsel": "#1b263b",
        "accent": "#f7931a",
        "accent_hover": "#ffb347",
        "border": "#415a77",
        "success": "#4caf50",
        "danger": "#f44336",
        "warning": "#ff9800",
        "chart_up": "#4caf50",
        "chart_down": "#f44336",
    },
    "midnight": {
        "name": "Midnight",
        "bg": "#0f172a",
        "fg": "#cbd5e1",
        "sel": "#94a3b8",
        "bsel": "#1e293b",
        "accent": "#6366f1",
        "accent_hover": "#818cf8",
        "border": "#334155",
        "success": "#22c55e",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "chart_up": "#22c55e",
        "chart_down": "#ef4444",
    },
}


def get_theme(name: str) -> dict[str, str]:
    """Retorna as cores de um tema. Padrao: dark."""
    return THEMES.get(name, THEMES["dark"])


def list_themes() -> list[str]:
    """Retorna a lista de nomes de temas disponiveis."""
    return list(THEMES.keys())


def map_theme_to_design_system(theme_name: str) -> dict[str, str]:
    """Converte um tema do app para as cores do design_system."""
    t = get_theme(theme_name)
    return {
        "BG": t["bg"],
        "PANEL": t["bsel"],
        "CARD": t["bsel"],
        "TEXT": t["fg"],
        "TEXT2": t["sel"],
        "BORDER_COLOR": t["border"],
        "PRIMARY": t["accent"],
        "PRIMARY_HOVER": t["accent_hover"],
        "SUCCESS": t["success"],
        "DANGER": t["danger"],
        "WARNING": t["warning"],
    }


def apply_ttk_theme(style, theme_name: str) -> dict[str, str]:
    """Aplica o tema em um objeto ttk.Style e retorna o dict de cores."""
    from tkinter import ttk

    t = get_theme(theme_name)
    style.theme_use("clam")

    bg = t["bg"]
    fg = t["fg"]
    bsel = t["bsel"]
    accent = t["accent"]
    accent_hover = t["accent_hover"]
    border = t["border"]

    style.configure(".", background=bg, foreground=fg, fieldbackground=bsel, bordercolor=border)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TButton", background=bsel, foreground=fg, bordercolor=border, padding=4)
    style.map("TButton", background=[("active", accent_hover), ("pressed", accent)])
    style.configure("TNotebook", background=bg, foreground=fg)
    style.configure("TNotebook.Tab", background=bsel, foreground=fg, padding=(10, 6))
    style.map("TNotebook.Tab", background=[("selected", accent)], foreground=[("selected", "#ffffff")])
    style.configure("Treeview", background=bsel, fieldbackground=bsel, foreground=fg, borderwidth=0)
    style.map("Treeview", background=[("selected", accent)])
    style.configure("Treeview.Heading", background=bsel,
                    foreground=fg, relief="flat")
    style.configure("TLabelframe", background=bg, foreground=fg)
    style.configure("TLabelframe.Label", background=bg, foreground=fg)
    style.configure("TEntry", fieldbackground=bsel, foreground=fg, insertcolor=fg)
    style.configure("TSpinbox", fieldbackground=bsel, foreground=fg)
    style.configure("TCombobox", fieldbackground=bsel, foreground=fg)

    return t
