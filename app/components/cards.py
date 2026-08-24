"""
Componentes visuais estilo MEXC para o app XAU_AI_PRO.
Cards, KPIs, badges e botoes modernos usando Tkinter padrao.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.theme.mexc import Theme


class Card(tk.Frame):
    """Card com fundo escuro, borda sutil e cantos arredondados simulados."""

    def __init__(self, parent, title: str | None = None, padx: int = 16, pady: int = 16, **kwargs):
        super().__init__(parent, bg=Theme.CARD, highlightbackground=Theme.BORDER,
                         highlightthickness=1, **kwargs)
        if title:
            self.title_label = tk.Label(
                self, text=title, bg=Theme.CARD, fg=Theme.TEXT,
                font=(Theme.FONT_FAMILY, 12, "bold"), anchor="w"
            )
            self.title_label.pack(fill="x", padx=padx, pady=(pady, 4))
        self.body = tk.Frame(self, bg=Theme.CARD)
        self.body.pack(fill="both", expand=True, padx=padx, pady=(0, pady))


class KPI(tk.Frame):
    """Indicador numerico grande com label e cor de destaque."""

    def __init__(self, parent, label: str, value: str = "--", color: str = Theme.TEXT, **kwargs):
        super().__init__(parent, bg=Theme.CARD, **kwargs)
        self.label = tk.Label(
            self, text=label, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 10)
        )
        self.label.pack(anchor="w")
        self.value = tk.Label(
            self, text=value, bg=Theme.CARD, fg=color,
            font=(Theme.FONT_FAMILY, 22, "bold")
        )
        self.value.pack(anchor="w", pady=(2, 0))

    def set(self, text: str, color: str | None = None) -> None:
        self.value.configure(text=text)
        if color:
            self.value.configure(fg=color)


class Badge(tk.Label):
    """Badge de status colorido."""

    def __init__(self, parent, text: str = "offline", status: str = "offline", **kwargs):
        colors = {
            "online": Theme.SUCCESS,
            "offline": Theme.TEXT_MUTED,
            "warning": Theme.WARNING,
            "error": Theme.DANGER,
            "info": Theme.INFO,
        }
        color = colors.get(status, Theme.TEXT_MUTED)
        super().__init__(
            parent, text=text, bg=Theme.CARD, fg=color,
            font=(Theme.FONT_FAMILY, 9, "bold"), **kwargs
        )


class PrimaryButton(tk.Button):
    """Botao primario com cor ciano e hover."""

    def __init__(self, parent, text: str = "", command=None, width: int = 14, **kwargs):
        super().__init__(
            parent, text=text, command=command, width=width,
            bg=Theme.PRIMARY, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9, "bold"),
            relief="flat", cursor="hand2", borderwidth=0, highlightthickness=0,
            activebackground=Theme.PRIMARY_HOVER, activeforeground=Theme.TEXT,
            **kwargs
        )
        self.bind("<Enter>", lambda e: self.config(bg=Theme.PRIMARY_HOVER))
        self.bind("<Leave>", lambda e: self.config(bg=Theme.PRIMARY))


class SecondaryButton(tk.Button):
    """Botao secundario com borda sutil."""

    def __init__(self, parent, text: str = "", command=None, width: int = 14, **kwargs):
        super().__init__(
            parent, text=text, command=command, width=width,
            bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9),
            relief="flat", cursor="hand2", borderwidth=0, highlightthickness=1,
            highlightbackground=Theme.BORDER_LIGHT,
            activebackground=Theme.CARD_HOVER, activeforeground=Theme.TEXT,
            **kwargs
        )


class DangerButton(tk.Button):
    """Botao de perigo (vermelho)."""

    def __init__(self, parent, text: str = "", command=None, width: int = 14, **kwargs):
        super().__init__(
            parent, text=text, command=command, width=width,
            bg=Theme.DANGER, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9, "bold"),
            relief="flat", cursor="hand2", borderwidth=0, highlightthickness=0,
            activebackground=Theme.DANGER_DARK, activeforeground=Theme.TEXT,
            **kwargs
        )


class AccentButton(tk.Button):
    """Botao laranja de destaque."""

    def __init__(self, parent, text: str = "", command=None, width: int = 14, **kwargs):
        super().__init__(
            parent, text=text, command=command, width=width,
            bg=Theme.ACCENT, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9, "bold"),
            relief="flat", cursor="hand2", borderwidth=0, highlightthickness=0,
            activebackground=Theme.ACCENT_HOVER, activeforeground=Theme.TEXT,
            **kwargs
        )
