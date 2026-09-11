# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""Botao PRO do XAU_AI_PRO (padrao trader: TradingView/Binance/MEXC).

Variantes:
  PRIMARY  - ciano (acoes padrao: OK, atualizar, abrir)
  SUCCESS  - verde (BUY / iniciar)
  DANGER   - vermelho (SELL / parar / excluir)
  GHOST    - neutro com borda (navegacao secundaria)
  ICON     - quadrado compacto para icones (hamburger, fechar)

Estados reais: hover (clareia), pressed (escurece), disabled (apagado).
Serializacao: toda chamada nativa do Tk roda na thread principal do app.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.theme.mexc import Theme


class ProButton(tk.Canvas):
    """Botao desenhado em Canvas: cantos arredondados, hover e pressed reais."""

    _VARIANTS = {
        "PRIMARY": {"bg": Theme.PRIMARY_DARK, "bg_hover": Theme.PRIMARY,
                    "bg_pressed": "#005ecb", "fg": "#ffffff",
                    "outline": Theme.BORDER_LIGHT},
        "SUCCESS": {"bg": Theme.SUCCESS_DARK, "bg_hover": Theme.SUCCESS,
                    "bg_pressed": "#0a9a43", "fg": "#ffffff",
                    "outline": Theme.BORDER_LIGHT},
        "DANGER": {"bg": Theme.DANGER_DARK, "bg_hover": Theme.DANGER,
                   "bg_pressed": "#a02038", "fg": "#ffffff",
                   "outline": Theme.BORDER_LIGHT},
        "GHOST": {"bg": Theme.PANEL, "bg_hover": Theme.CARD_HOVER,
                  "bg_pressed": Theme.CARD, "fg": Theme.TEXT_SECONDARY,
                  "outline": Theme.BORDER},
    }

    def __init__(self, parent, text: str, command: Callable[[], None] | None = None,
                 variant: str = "PRIMARY", font_size: int = 9, bold: bool = False,
                 padx: int = 14, pady: int = 7, radius: int = Theme.BORDER_RADIUS,
                 width: int | None = None, **_ignored) -> None:
        spec = self._VARIANTS.get(variant, self._VARIANTS["PRIMARY"])
        super().__init__(parent, bg=parent["bg"], highlightthickness=0,
                         cursor="hand2" if command else "arrow")
        self._command = command
        self._spec = spec
        self._radius = radius
        self._text = text
        self._font = (Theme.FONT_FAMILY, font_size, "bold" if bold else "normal")
        self._pressed = False
        self._enabled = True
        self._active = False
        # Mede o texto para dimensionar o canvas
        probe = tk.Label(self, text=text, font=self._font)
        tw = probe.winfo_reqwidth()
        th = probe.winfo_reqheight()
        probe.destroy()
        w = width if width is not None else tw + padx * 2
        h = th + pady * 2 + radius // 2
        self._width, self._height = w, h
        self.configure(width=w, height=h)
        self._draw(spec["bg"])
        for seq, fn in (("<Button-1>", self._on_press),
                        ("<ButtonRelease-1>", self._on_release),
                        ("<Enter>", self._on_enter),
                        ("<Leave>", self._on_leave)):
            self.bind(seq, fn)

    # ------------------------------------------------------------- desenho
    def _round_rect(self, bg: str, outline: str) -> None:
        self.delete("all")
        r = self._radius
        self.create_polygon(
            r, 0, self._width - r, 0, self._width, r, self._width, self._height - r,
            self._width - r, self._height, r, self._height, 0, self._height - r, 0, r,
            smooth=True, fill=bg, outline=outline)
        self.create_text(self._width // 2, self._height // 2, text=self._text,
                         fill=self._spec["fg"], font=self._font)

    def _draw(self, bg: str) -> None:
        outline = Theme.BORDER_ACCENT if self._enabled and bg == self._spec["bg_hover"] else self._spec["outline"]
        self._round_rect(bg if self._enabled else Theme.TEXT_DISABLED, outline)

    # ------------------------------------------------------------- estados
    def _on_enter(self, _e=None) -> None:
        if self._enabled and not self._pressed:
            self._draw(self._spec["bg_hover"])

    def _on_leave(self, _e=None) -> None:
        self._pressed = False
        if self._enabled:
            self._draw(self._spec["bg"])

    def _on_press(self, _e=None) -> None:
        if not self._enabled:
            return
        self._pressed = True
        self._draw(self._spec["bg_pressed"])

    def _on_release(self, _e=None) -> None:
        if not self._enabled:
            return
        was_pressed = self._pressed
        self._pressed = False
        self._draw(self._spec["bg_hover"])
        if was_pressed and self._command:
            self._command()


    def set_active(self, active: bool) -> None:
        """Estado de item ativo (navegacao): borda/ texto em PRIMARY."""
        self._active = active
        if active:
            self._round_rect(self._spec["bg"], Theme.BORDER_ACCENT)
        else:
            self._round_rect(self._spec["bg"], self._spec["outline"])

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw(self._spec["bg"])

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw(self._spec["bg"])


# Fatorias semanticas (padrao trader)
def BuyButton(parent, text, command, **kw) -> ProButton:
    return ProButton(parent, text, command, variant="SUCCESS", **kw)


def SellButton(parent, text, command, **kw) -> ProButton:
    return ProButton(parent, text, command, variant="DANGER", **kw)


def GhostButton(parent, text, command, **kw) -> ProButton:
    return ProButton(parent, text, command, variant="GHOST", **kw)


