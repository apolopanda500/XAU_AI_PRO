"""
XAU AI PRO - Design System

Componentes visuais modernos inspirados em design systems como Figma:
cards arredondados, bordas suaves, tipografia limpa, sombras sutis
e paleta consistente com os temas do app.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Colors:
    DARK_BG = "#0f1115"
    DARK_PANEL = "#161920"
    DARK_CARD = "#1c1f26"
    LIGHT_BG = "#f4f5f7"
    LIGHT_PANEL = "#ffffff"
    LIGHT_CARD = "#ffffff"
    PRIMARY = "#6366f1"
    PRIMARY_HOVER = "#4f46e5"
    SUCCESS = "#10b981"
    DANGER = "#ef4444"
    WARNING = "#f59e0b"
    TEXT_PRIMARY = "#f9fafb"
    TEXT_SECONDARY = "#9ca3af"
    TEXT_DARK = "#111827"
    TEXT_DARK_SECONDARY = "#6b7280"
    BORDER = "#2a2e37"
    BORDER_LIGHT = "#e5e7eb"


def get_colors(theme: str = "dark") -> type[Colors]:
    """Retorna classe Colors populada com o tema atual do app."""
    import themes
    mapped = themes.map_theme_to_design_system(theme)
    class ThemeColors(Colors):
        pass
    for key, value in mapped.items():
        setattr(ThemeColors, key, value)
    return ThemeColors


class Card(tk.Frame):
    """Card com cantos levemente arredondados, fundo elevado e borda sutil."""

    def __init__(self, parent, theme: str = "dark", title: str | None = None,
                 padx: int = 12, pady: int = 12, *args, **kwargs):
        self.theme = get_colors(theme)
        super().__init__(parent, bg=self.theme.CARD, highlightbackground=self.theme.BORDER_COLOR,
                         highlightthickness=1, *args, **kwargs)
        if title:
            self.title_label = tk.Label(self, text=title, bg=self.theme.CARD,
                                        fg=self.theme.TEXT, font=("Segoe UI", 11, "bold"),
                                        anchor="w")
            self.title_label.pack(fill="x", padx=padx, pady=(pady, 4))
        self.body = tk.Frame(self, bg=self.theme.CARD)
        self.body.pack(fill="both", expand=True, padx=padx, pady=(0, pady))


class PrimaryButton(tk.Button):
    """Botao primario com hover e cantos arredondados simulados."""

    def __init__(self, parent, theme: str = "dark", command=None, text: str = "",
                 width: int = 14, *args, **kwargs):
        self.colors = get_colors(theme)
        super().__init__(parent, text=text, command=command, width=width,
                         bg=self.colors.PRIMARY, fg="white",
                         activebackground=self.colors.PRIMARY_HOVER,
                         activeforeground="white",
                         font=("Segoe UI", 9, "bold"),
                         relief="flat", cursor="hand2",
                         highlightthickness=0, borderwidth=0,
                         *args, **kwargs)
        self.bind("<Enter>", lambda e: self.config(bg=self.colors.PRIMARY_HOVER))
        self.bind("<Leave>", lambda e: self.config(bg=self.colors.PRIMARY))


class SecondaryButton(tk.Button):
    def __init__(self, parent, theme: str = "dark", command=None, text: str = "",
                 width: int = 14, *args, **kwargs):
        self.colors = get_colors(theme)
        super().__init__(parent, text=text, command=command, width=width,
                         bg=self.colors.PANEL, fg=self.colors.TEXT,
                         activebackground=self.colors.BORDER_COLOR,
                         activeforeground=self.colors.TEXT,
                         font=("Segoe UI", 9),
                         relief="flat", cursor="hand2",
                         highlightthickness=1, highlightbackground=self.colors.BORDER_COLOR,
                         borderwidth=0,
                         *args, **kwargs)


class StatusBadge(tk.Label):
    """Badge de status colorido (online, offline, aviso)."""

    def __init__(self, parent, theme: str = "dark", text: str = "offline",
                 status: str = "offline", *args, **kwargs):
        self.colors = get_colors(theme)
        color = {
            "online": self.colors.SUCCESS,
            "offline": self.colors.TEXT_SECONDARY,
            "warning": self.colors.WARNING,
            "error": self.colors.DANGER,
        }.get(status, self.colors.TEXT_SECONDARY)
        super().__init__(parent, text=text, bg=self.colors.CARD, fg=color,
                         font=("Segoe UI", 9, "bold"), *args, **kwargs)


class Metric(tk.Frame):
    """Metrica com label e valor grandes (KPI)."""

    def __init__(self, parent, theme: str = "dark", label: str = "", value: str = "",
                 color: str | None = None, *args, **kwargs):
        self.colors = get_colors(theme)
        super().__init__(parent, bg=self.colors.CARD, *args, **kwargs)
        tk.Label(self, text=label, bg=self.colors.CARD, fg=self.colors.TEXT2,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.metric_value = tk.Label(self, text=value, bg=self.colors.CARD,
                                     fg=color or self.colors.TEXT,
                                     font=("Segoe UI", 18, "bold"))
        self.metric_value.pack(anchor="w")


class FigmaFrame(tk.Frame):
    """Frame com fundo de painel e padding generoso (estilo Figma artboard)."""

    def __init__(self, parent, theme: str = "dark", *args, **kwargs):
        self.colors = get_colors(theme)
        super().__init__(parent, bg=self.colors.PANEL, *args, **kwargs)
