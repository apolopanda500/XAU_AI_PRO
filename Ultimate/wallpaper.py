"""
XAU AI PRO - Wallpaper Engine
Desenha um plano de fundo com simbolos de criptomoedas, robos IA e
gradiente animado usando Canvas do Tkinter.
"""

from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Callable


SYMBOLS = ["₿", "Ξ", "◈", "₳", "◎", "✦", "🤖", "🧠", "⚡", "📈"]


class CryptoWallpaper(tk.Canvas):
    """Canvas animado com particulas de cripto/IA."""

    def __init__(self, parent, theme: dict[str, str], width: int = 1000, height: int = 660, **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.theme = theme
        self.width = width
        self.height = height
        self.particles: list[dict] = []
        self.after_id: str | None = None
        self._build()

    def _build(self) -> None:
        bg = self.theme.get("bg", "#1e1f24")
        accent = self.theme.get("accent", "#3a5a8a")
        fg = self.theme.get("fg", "#e6e6e6")

        self.configure(bg=bg)

        # Fundo gradiente vertical simplificado
        for i in range(40):
            ratio = i / 40.0
            r1, g1, b1 = self._hex_to_rgb(bg)
            r2, g2, b2 = self._hex_to_rgb(accent)
            color = self._rgb_to_hex(
                int(r1 + (r2 - r1) * ratio * 0.25),
                int(g1 + (g2 - g1) * ratio * 0.25),
                int(b1 + (b2 - b1) * ratio * 0.25),
            )
            self.create_rectangle(
                0, int(self.height * i / 40),
                self.width, int(self.height * (i + 1) / 40),
                fill=color, outline="",
            )

        # Criar particulas
        for _ in range(35):
            x = random.randint(20, self.width - 20)
            y = random.randint(20, self.height - 20)
            size = random.randint(14, 28)
            speed = random.uniform(0.2, 0.8) * random.choice([1, -1])
            sym = random.choice(SYMBOLS)
            alpha = random.randint(40, 120)
            color = fg if random.random() > 0.5 else accent
            item = self.create_text(
                x, y, text=sym, font=("Segoe UI", size),
                fill=color, anchor="center",
            )
            self.particles.append({
                "item": item, "x": x, "y": y, "speed": speed,
                "amp": random.randint(10, 40), "phase": random.random() * math.pi * 2,
                "base_y": y,
            })

        self._animate()

    def _animate(self) -> None:
        t = time_ms() / 1000.0
        for p in self.particles:
            new_y = p["base_y"] + math.sin(t + p["phase"]) * p["amp"]
            p["y"] = new_y
            self.coords(p["item"], p["x"], new_y)
        self.after_id = self.after(40, self._animate)

    def stop(self) -> None:
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def time_ms() -> int:
    import time
    return int(time.time() * 1000)


def create_wallpaper(parent, theme: dict[str, str]) -> CryptoWallpaper:
    return CryptoWallpaper(parent, theme)
