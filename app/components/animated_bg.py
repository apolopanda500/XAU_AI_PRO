# -*- coding: utf-8 -*-
"""
Plano de fundo animado sutil estilo dark/IA para o XAU_AI_PRO.
Usa um canvas com particulas e linhas de conexao leves.
    Atualizacao a 30 FPS, baixo consumo de CPU (max 25 particulas).
"""
from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Any

from app.theme.mexc import Theme


class AnimatedBackground(tk.Canvas):
    """Canvas de fundo com particulas e ondas sutis."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        super().__init__(parent, bg=Theme.BG, highlightthickness=0, bd=0, **kwargs)
        self._particles: list[dict[str, Any]] = []
        self._max_particles = 22
        self._running = False
        self._after_id: str | None = None
        self._t = 0.0
        self._last_size = (0, 0)
        self._static_lines: list[int] = []
        self._build()

    def _build(self) -> None:
        for _ in range(self._max_particles):
            self._particles.append(self._spawn())
        self._draw()

    def _spawn(self) -> dict[str, Any]:
        w = max(self.winfo_width(), 400)
        h = max(self.winfo_height(), 300)
        return {
            "x": random.uniform(0, w),
            "y": random.uniform(0, h),
            "vx": random.uniform(-0.4, 0.4),
            "vy": random.uniform(-0.3, 0.3),
            "r": random.uniform(1.5, 3.5),
            "alpha": random.uniform(0.15, 0.45),
        }

    def _draw(self) -> None:
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            self._schedule()
            return

        # Mantém o grid estático entre frames; apagar e recriar todos os
        # itens era o maior custo do Canvas e degradava o FPS da GUI.
        if (w, h) != self._last_size:
            self.delete("grid")
            self._static_lines = []
            for i in range(0, h, 120):
                line = self.create_line(0, i, w, i, fill="#11151f", width=1,
                                        tags="grid")
                self._static_lines.append(line)
            self._last_size = (w, h)

        self.delete("dynamic")

        # Grade sutil de ondas no fundo. Limitar a quantidade evita custo
        # desnecessario em monitores grandes e preserva fluidez da GUI.
        self._t += 0.015
        # Particulas
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0 or p["x"] > w:
                p["vx"] *= -1
                p["x"] = max(0, min(w, p["x"]))
            if p["y"] < 0 or p["y"] > h:
                p["vy"] *= -1
                p["y"] = max(0, min(h, p["y"]))

            color = self._alpha_color(Theme.PRIMARY, p["alpha"])
            self.create_oval(
                p["x"] - p["r"], p["y"] - p["r"],
                p["x"] + p["r"], p["y"] + p["r"],
                fill=color, outline="", tags="dynamic"
            )

        # Linhas de conexao entre particulas proximas (muito sutis)
        for i, a in enumerate(self._particles):
            for b in self._particles[i + 1:]:
                dx = a["x"] - b["x"]
                dy = a["y"] - b["y"]
                dist = math.hypot(dx, dy)
                if dist < 120:
                    alpha = 0.08 * (1 - dist / 120)
                    color = self._alpha_color(Theme.PRIMARY, alpha)
                    self.create_line(a["x"], a["y"], b["x"], b["y"],
                                     fill=color, width=1, tags="dynamic")

        self._schedule()

    def _alpha_color(self, hex_color: str, alpha: float) -> str:
        """Converte cor hex para RGBA no formato tk (#RRGGBBAA).

        O Tkinter no Windows nao aceita cores com canal alpha (#RRGGBBAA).
        Portanto, fazemos blend linear entre a cor desejada e o fundo (Theme.BG)
        para simular transparencia.
        """
        alpha = max(0, min(1, alpha))
        hex_color = hex_color.lstrip("#")[:6]
        bg = Theme.BG.lstrip("#")[:6]
        r = int(int(hex_color[0:2], 16) * alpha + int(bg[0:2], 16) * (1 - alpha))
        g = int(int(hex_color[2:4], 16) * alpha + int(bg[2:4], 16) * (1 - alpha))
        b = int(int(hex_color[4:6], 16) * alpha + int(bg[4:6], 16) * (1 - alpha))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _schedule(self) -> None:
        if self._running:
            # 33 ms ~= 30 FPS; o limite garante animacao suave sem disputar
            # recursos com as abas, rede e MT5.
            self._after_id = self.after(33, self._draw)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._schedule()

    def stop(self) -> None:
        self._running = False
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
