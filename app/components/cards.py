# -*- coding: utf-8 -*-
"""
Componentes visuais PRO estilo TradingView/Binance para o app XAU_AI_PRO.
Cards com glassmorphism, KPIs com indicadores visuais, badges e botões modernos.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.theme.mexc import Theme


class Card(tk.Frame):
    """Card com fundo escuro, borda sutil, elevação e efeito glassmorphism."""

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
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.body.bind("<Enter>", lambda e: self._hover(True))
        self.body.bind("<Leave>", lambda e: self._hover(False))
        if title:
            self.title_label.bind("<Enter>", lambda e: self._hover(True))
            self.title_label.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, active: bool) -> None:
        bg = Theme.CARD_HOVER if active else Theme.CARD
        self.configure(bg=bg)
        if hasattr(self, "title_label"):
            self.title_label.configure(bg=bg)
        self.body.configure(bg=bg)


class GlassCard(tk.Frame):
    """Card com efeito glassmorphism (fundo semi-transparente simulado)."""

    def __init__(self, parent, title: str | None = None, padx: int = 16, pady: int = 16, **kwargs):
        super().__init__(parent, bg=Theme.GLASS, highlightbackground=Theme.BORDER_LIGHT,
                         highlightthickness=1, **kwargs)
        if title:
            header = tk.Frame(self, bg=Theme.GLASS)
            header.pack(fill="x", padx=padx, pady=(pady, 0))
            tk.Label(header, text=title, bg=Theme.GLASS, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 11, "bold"), anchor="w").pack(side="left")
            tk.Frame(header, bg=Theme.BORDER_ACCENT, height=2).pack(side="right", fill="x", expand=True, padx=(12, 0))
        self.body = tk.Frame(self, bg=Theme.GLASS)
        self.body.pack(fill="both", expand=True, padx=padx, pady=(8, pady))


class KPI(tk.Frame):
    """Indicador numérico grande com label, cor de destaque e indicador de tendência."""

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
        self._trend_indicator = tk.Label(
            self, text="", bg=Theme.CARD, fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 10)
        )
        self._trend_indicator.pack(anchor="w")

    def set(self, text: str, color: str | None = None, trend: str | None = None) -> None:
        self.value.configure(text=text)
        if color:
            self.value.configure(fg=color)
        if trend:
            self._trend_indicator.configure(text=trend, fg=Theme.SUCCESS if "▲" in trend else Theme.DANGER)


class TerminalKPI(tk.Frame):
    """KPI estilo terminal com fonte mono e indicador de status."""

    def __init__(self, parent, label: str, value: str = "--", color: str = Theme.TEXT, **kwargs):
        super().__init__(parent, bg=Theme.CARD_ALT, **kwargs)
        self.value_color = color
        self.label_widget = tk.Label(
            self, text=label, bg=Theme.CARD_ALT, fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9)
        )
        self.label_widget.pack(anchor="w", padx=12, pady=(8, 0))
        self.value = tk.Label(
            self, text=value, bg=Theme.CARD_ALT, fg=color,
            font=(Theme.FONT_MONO, 18, "bold")
        )
        self.value.pack(anchor="w", padx=12, pady=(0, 8))

    def set(self, text: str, color: str | None = None) -> None:
        self.value.configure(text=text)
        if color:
            self.value_color = color
            self.value.configure(fg=color)


class Badge(tk.Label):
    """Badge de status colorido com indicador visual."""

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
            parent, text=f"● {text}", bg=Theme.CARD, fg=color,
            font=(Theme.FONT_FAMILY, 9, "bold"), **kwargs
        )


class StatusBadge(tk.Frame):
    """Badge de status com indicador pulsante."""

    def __init__(self, parent, text: str = "offline", status: str = "offline", **kwargs):
        super().__init__(parent, bg=Theme.CARD, **kwargs)
        colors = {
            "online": Theme.SUCCESS,
            "offline": Theme.TEXT_MUTED,
            "warning": Theme.WARNING,
            "error": Theme.DANGER,
            "info": Theme.INFO,
        }
        color = colors.get(status, Theme.TEXT_MUTED)
        self.indicator = tk.Label(self, text="●", bg=Theme.CARD, fg=color,
                                   font=(Theme.FONT_FAMILY, 10))
        self.indicator.pack(side="left")
        self.label = tk.Label(self, text=text, bg=Theme.CARD, fg=color,
                              font=(Theme.FONT_FAMILY, 9, "bold"))
        self.label.pack(side="left", padx=(4, 0))


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
        self.bind("<Enter>", lambda e: self.config(bg=Theme.CARD_HOVER))
        self.bind("<Leave>", lambda e: self.config(bg=Theme.PANEL))


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


class BuyButton(tk.Button):
    """Botão de compra (verde)."""

    def __init__(self, parent, text: str = "COMPRAR", command=None, width: int = 14, **kwargs):
        super().__init__(
            parent, text=text, command=command, width=width,
            bg=Theme.SUCCESS, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9, "bold"),
            relief="flat", cursor="hand2", borderwidth=0, highlightthickness=0,
            activebackground=Theme.SUCCESS_DARK, activeforeground=Theme.TEXT,
            **kwargs
        )


class SellButton(tk.Button):
    """Botão de venda (vermelho)."""

    def __init__(self, parent, text: str = "VENDER", command=None, width: int = 14, **kwargs):
        super().__init__(
            parent, text=text, command=command, width=width,
            bg=Theme.DANGER, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9, "bold"),
            relief="flat", cursor="hand2", borderwidth=0, highlightthickness=0,
            activebackground=Theme.DANGER_DARK, activeforeground=Theme.TEXT,
            **kwargs
        )
