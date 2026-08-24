"""
Graficos leves usando Canvas do Tkinter (sem matplotlib).
"""
from __future__ import annotations

import tkinter as tk

from app.theme.mexc import Theme


class EquityChart(tk.Canvas):
    """Grafico de linha simples desenhado em canvas."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Theme.CARD, highlightthickness=0, **kwargs)
        self._values: list[float] = []
        self.bind("<Configure>", lambda e: self._draw())

    def update_data(self, values: list[float], labels: list[str] | None = None) -> None:
        self._values = values
        self._draw()

    def _draw(self, event=None) -> None:
        self.delete("all")
        if len(self._values) < 2:
            self.create_text(self.winfo_width() // 2, self.winfo_height() // 2,
                             text="Aguardando dados...", fill=Theme.TEXT_SECONDARY,
                             font=(Theme.FONT_FAMILY, 10))
            return
        w = max(self.winfo_width(), 200)
        h = max(self.winfo_height(), 150)
        padding = 30
        min_v = min(self._values)
        max_v = max(self._values)
        rng = max_v - min_v if max_v != min_v else 1
        n = len(self._values) - 1
        points = []
        for i, v in enumerate(self._values):
            x = padding + (w - 2 * padding) * i / n
            y = h - padding - (h - 2 * padding) * (v - min_v) / rng
            points.extend([x, y])
        color = Theme.SUCCESS if self._values[-1] >= self._values[0] else Theme.DANGER
        self.create_line(points, fill=color, width=2, smooth=True)
        self.create_text(padding, padding, text=f"{max_v:,.2f}", fill=Theme.TEXT_SECONDARY,
                         anchor="nw", font=(Theme.FONT_FAMILY, 8))
        self.create_text(padding, h - padding, text=f"{min_v:,.2f}", fill=Theme.TEXT_SECONDARY,
                         anchor="sw", font=(Theme.FONT_FAMILY, 8))

