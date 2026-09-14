# -*- coding: utf-8 -*-
"""Barra de navegacao superior do XAU_AI_PRO.

Substitui as sub-abas internas (CombinedTab) por UMA unica faixa no topo,
sincronizada com a Sidebar: um clique aqui chama o mesmo `_navigate` do
core, que usa lazy-load + after_idle (sem travar a thread Tk).

Desenho anti-trava:
  - Guarda `_busy`: cliques repetidos durante a construcao da aba sao
    ignorados (nao empilham CombinedTab/refresh concorrentes).
  - Toda troca passa por `on_navigate` (core._navigate), unica fonte de
    verdade; esta barra apenas reflete o estado via `set_active`.
  - Botoes ProButton GHOST com estado ativo (borda PRIMARY).
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.components.button import ProButton
from app.theme.mexc import Theme


# (chave, rotulo) — espelha as fabricas do core (sem duplicar CombinedTab).
TOP_ITEMS: list[tuple[str, str]] = [
    ("dashboard", "Painel"),
    ("positions", "Carteira"),
    ("market", "Mercado"),
    ("charts", "Graficos"),
    ("robot", "Controle"),
    ("audit", "Auditoria"),
    ("tester", "Strategy Tester"),
    ("vision", "Visao do Robo"),
    ("settings", "Configuracoes"),
    ("connections", "Conexoes"),
]


class TopNav(tk.Frame):
    """Faixa horizontal de abas no topo, sincronizada com a Sidebar."""

    def __init__(self, parent, on_navigate: Callable[[str], None]) -> None:
        super().__init__(parent, bg=Theme.BG)
        self._on_navigate = on_navigate
        self._buttons: dict[str, ProButton] = {}
        self._active = ""
        self._busy = False
        from app.theme.mexc import on_theme_change
        on_theme_change(self._refresh_theme)
        self._build()

    def _build(self) -> None:
        self._bar = tk.Frame(self, bg=Theme.BG_SECONDARY,
                             highlightbackground=Theme.BORDER, highlightthickness=1)
        self._bar.pack(fill="x", padx=24, pady=(8, 0))
        self._inner = tk.Frame(self._bar, bg=Theme.BG_SECONDARY)
        self._inner.pack(fill="x", padx=8, pady=6)
        for key, label in TOP_ITEMS:
            btn = ProButton(self._inner, label,
                            lambda k=key: self._click(k),
                            variant="GHOST", font_size=9,
                            padx=12, pady=6)
            btn.pack(side="left", padx=(0, 6))
            self._buttons[key] = btn

    def _refresh_theme(self) -> None:
        """Reconfigura barra e botoes com os novos valores da Theme."""
        if not getattr(self, "_bar", None):
            return
        self._bar.configure(bg=Theme.BG_SECONDARY,
                            highlightbackground=Theme.BORDER, highlightthickness=1)
        self._inner.configure(bg=Theme.BG_SECONDARY)
        for btn in self._buttons.values():
            btn._refresh_theme()

    def _click(self, key: str) -> None:
        if self._busy or key == self._active:
            return
        self._busy = True
        try:
            self._on_navigate(key)
        finally:
            # Libera no proximo ciclo Tk: a construcao lazy da aba roda
            # em after_idle dentro do core, entao liberamos apos ela.
            try:
                self.after(350, lambda: setattr(self, "_busy", False))
            except Exception:
                self._busy = False

    def set_active(self, key: str) -> None:
        """Reflete a aba atual (chamado pelo core apos _show_tab)."""
        self._active = key
        for name, btn in self._buttons.items():
            try:
                btn.set_active(name == key)
                btn.set_text(dict(TOP_ITEMS)[name])
            except Exception:
                pass
