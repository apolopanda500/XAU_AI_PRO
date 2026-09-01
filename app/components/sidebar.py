"""
Sidebar de navegacao estilo MEXC para o app XAU_AI_PRO.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.theme.mexc import Theme


class SidebarButton(tk.Button):
    """Botao de menu lateral com icone/emoji e indicador ativo."""

    def __init__(self, parent, text: str, icon: str, command: Callable, **kwargs):
        super().__init__(
            parent, text=f"{icon}  {text}", anchor="w",
            bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 11), relief="flat", cursor="hand2",
            borderwidth=0, highlightthickness=0, padx=20, pady=12,
            command=command, **kwargs
        )
        self.active = False
        self.bind("<Enter>", lambda e: self._on_enter())
        self.bind("<Leave>", lambda e: self._on_leave())

    def _on_enter(self) -> None:
        if not self.active:
            self.config(bg=Theme.CARD_HOVER, fg=Theme.TEXT)

    def _on_leave(self) -> None:
        if not self.active:
            self.config(bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY)

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            self.config(bg=Theme.CARD, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 11, "bold"))
        else:
            self.config(bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 11))


class Sidebar(tk.Frame):
    """Menu lateral com logo, botoes e rodape."""

    def __init__(self, parent, on_navigate: Callable[[str], None], **kwargs):
        super().__init__(parent, bg=Theme.PANEL, width=220, **kwargs)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self._buttons: dict[str, SidebarButton] = {}

        # Logo
        logo_frame = tk.Frame(self, bg=Theme.PANEL, height=80)
        logo_frame.pack(fill="x", pady=(20, 10))
        tk.Label(
            logo_frame, text="XAU AI PRO", bg=Theme.PANEL, fg=Theme.TEXT,
            font=(Theme.FONT_FAMILY, 18, "bold")
        ).pack(anchor="w", padx=20)
        tk.Label(
            logo_frame, text="Trading Desk v1.2.0", bg=Theme.PANEL, fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9)
        ).pack(anchor="w", padx=20)

        # Separador
        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill="x", padx=16, pady=10)

        # Botoes
        self._items = [
            ("dashboard", "Dashboard", "📊"),
            ("market", "Mercado", "📈"),
            ("positions", "Carteira", "💰"),
            ("robot", "Robo MT5", "🤖"),
            ("training", "IA / Treino", "🧠"),
            ("assistant", "Assistente", "💬"),
            ("tools", "Ferramentas", "🧰"),
            ("integrations", "Integracoes", "🔌"),
            ("settings", "Configuracoes", "⚙️"),
        ]
        for key, label, icon in self._items:
            btn = SidebarButton(self, label, icon, command=lambda k=key: self._navigate(k))
            btn.pack(fill="x")
            self._buttons[key] = btn

        # Rodape
        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill="x", padx=16, pady=10)
        self.footer_status = tk.Label(
            self, text="Status: offline", bg=Theme.PANEL, fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9), anchor="w", padx=20
        )
        self.footer_status.pack(fill="x", side="bottom", pady=10)

    def _navigate(self, key: str) -> None:
        self.set_active(key)
        self.on_navigate(key)

    def set_active(self, key: str) -> None:
        for k, btn in self._buttons.items():
            btn.set_active(k == key)

    def set_status(self, text: str, color: str = Theme.TEXT_MUTED) -> None:
        self.footer_status.configure(text=text, fg=color)
