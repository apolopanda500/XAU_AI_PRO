"""
Graficos PRO estilo TradingView usando Canvas do Tkinter.
Linha de equity com área preenchida, grid e crosshair.
"""
from __future__ import annotations

import tkinter as tk

from app.theme.mexc import Theme


class EquityChart(tk.Canvas):
    """Grafico de linha com área preenchida (estilo TradingView)."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Theme.CARD_ALT, highlightthickness=0, **kwargs)
        self._values: list[float] = []
        self._labels: list[str] = []
        self.bind("<Configure>", lambda e: self._draw())

    def update_data(self, values: list[float], labels: list[str] | None = None) -> None:
        self._values = values
        self._labels = labels or []
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
        padding = 40
        min_v = min(self._values)
        max_v = max(self._values)
        rng = max_v - min_v if max_v != min_v else 1
        n = len(self._values) - 1

        # Grid horizontal
        for i in range(5):
            y = padding + (h - 2 * padding) * i / 4
            self.create_line(padding, y, w - padding, y, fill=Theme.CHART_GRID, width=1)
            # Label de preço
            price = max_v - rng * i / 4
            self.create_text(padding - 5, y, text=f"{price:,.0f}", fill=Theme.TEXT_MUTED,
                             anchor="e", font=(Theme.FONT_MONO, 8))

        # Pontos da linha
        points = []
        for i, v in enumerate(self._values):
            x = padding + (w - 2 * padding) * i / n
            y = h - padding - (h - 2 * padding) * (v - min_v) / rng
            points.extend([x, y])

        # Área preenchida (gradiente simulado)
        area_points = points.copy()
        area_points.extend([points[-2], h - padding, points[0], h - padding])
        color = Theme.CHART_UP if self._values[-1] >= self._values[0] else Theme.CHART_DOWN
        area_color = Theme.CHART_UP_AREA if self._values[-1] >= self._values[0] else Theme.CHART_DOWN_AREA
        self.create_polygon(area_points, fill=area_color, outline="")

        # Linha principal
        self.create_line(points, fill=color, width=2, smooth=True)

        # Ponto final (destaque)
        self.create_oval(points[-2] - 4, points[-1] - 4, points[-2] + 4, points[-1] + 4,
                         fill=color, outline=color)

        # Labels min/max
        self.create_text(padding, padding - 10, text=f"Max: {max_v:,.2f}", fill=Theme.TEXT_SECONDARY,
                         anchor="w", font=(Theme.FONT_MONO, 8))
        self.create_text(padding, h - padding + 15, text=f"Min: {min_v:,.2f}", fill=Theme.TEXT_SECONDARY,
                         anchor="w", font=(Theme.FONT_MONO, 8))
