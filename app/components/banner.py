# -*- coding: utf-8 -*-
"""Banner visual interativo das abas do XAU_AI_PRO.

Cada aba recebe um banner tematico (PNG em app/assets/banners/)
com particulas neon animadas que reagem ao mouse (repulsao suave)
e um glow que segue o cursor - estilo neon das referencias.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import tkinter as tk

BANNER_DIR = Path(__file__).resolve().parents[1] / "assets" / "banners"

# Cores neon por tema de aba (fallback se o PNG nao existir)
NEON = {
    "dashboard": "#00e5ff", "market": "#22ff88", "positions": "#ffd700",
    "robot": "#00c8ff", "training": "#39ff88", "assistant": "#4d9fff",
    "tools": "#ffaa33", "integrations": "#c77dff", "subgraph": "#00ffc8",
    "system": "#7dd3fc", "charts": "#22d3ee", "settings": "#94a3b8",
    "search": "#60a5fa", "community": "#f472b6",
}


class TabBanner(tk.Canvas):
    """Banner com arte tematica + particulas interativas."""

    N_PARTICLES = 14
    TICK_MS = 80

    def __init__(self, parent, key: str, height: int = 110, **kw):
        self._neon = NEON.get(key, "#00e5ff")
        self._img_src = None
        self._photo = None
        img_path = BANNER_DIR / f"banner_{key}.png"
        if img_path.exists():
            try:
                from PIL import Image
                self._img_src = Image.open(img_path)
            except Exception:
                self._img_src = None
        super().__init__(parent, height=height, highlightthickness=0,
                         bd=0, bg="#0a0e1a", **kw)
        self.pack_propagate(False)
        self._particles = []
        self._mouse = (-999, -999)
        self._glow_r = 0
        self._last_w = 0
        self._after_id = None
        rnd = random.Random(hash(key) & 0xFFFF)
        for _ in range(self.N_PARTICLES):
            self._particles.append({
                "x": rnd.uniform(0, 900), "y": rnd.uniform(0, 100),
                "vx": rnd.uniform(-0.7, 0.7), "vy": rnd.uniform(-0.5, 0.5),
                "r": rnd.uniform(1.5, 3.5),
            })
        self.bind("<Configure>", self._on_resize)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", lambda e: setattr(self, "_mouse", (-999, -999)))
        self._after_id = self.after(self.TICK_MS, self._tick)

    # ------------------------------------------------------------------
    def _on_resize(self, event) -> None:
        w = int(event.width)
        h = int(event.height)
        if w < 40 or w == self._last_w:
            return
        self._last_w = w
        self._photo = None
        if self._img_src is not None:
            try:
                from PIL import Image, ImageTk
                ratio = w / self._img_src.width
                nh = max(1, min(int(self._img_src.height * ratio), h))
                img = self._img_src.resize((w, nh), Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
                self._bg_id = self.create_image(0, (h - nh) // 2, anchor="nw",
                                                image=self._photo)
                self.tag_lower(self._bg_id)
            except Exception:
                self._photo = None
        if self._photo is None:
            # Fallback: gradiente simples + glow central
            self.delete("bg")
            for i in range(h):
                t = i / max(1, h - 1)
                c = self._blend((7, 10, 22), (16, 25, 46), t)
                self.create_line(0, i, w, i, fill=c, tags="bg")
            self.tag_lower("bg")

    @staticmethod
    def _blend(a, b, t):
        return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    # ------------------------------------------------------------------
    def _on_motion(self, event) -> None:
        self._mouse = (event.x, event.y)

    def _tick(self) -> None:
        try:
            w = max(1, self.winfo_width())
            h = max(1, self.winfo_height())
            mx, my = self._mouse
            self.delete("fx")
            # Glow que segue o mouse (simulado com stipple)
            if mx > -100:
                self._glow_r = 46
                self.create_oval(mx - self._glow_r, my - self._glow_r,
                                 mx + self._glow_r, my + self._glow_r,
                                 fill=self._neon, outline="", stipple="gray25",
                                 tags="fx")
            for p in self._particles:
                # repulsao suave do mouse
                dx, dy = p["x"] - mx, p["y"] - my
                dist = math.hypot(dx, dy)
                if dist < 90 and dist > 0.01:
                    force = (90 - dist) / 90 * 0.9
                    p["vx"] += dx / dist * force
                    p["vy"] += dy / dist * force
                # atrito + limites de velocidade
                p["vx"] *= 0.985
                p["vy"] *= 0.985
                sp = math.hypot(p["vx"], p["vy"])
                if sp > 2.2:
                    p["vx"] *= 2.2 / sp
                    p["vy"] *= 2.2 / sp
                # deriva base
                p["vx"] += 0.012
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                if p["x"] < -6:
                    p["x"] = w + 6
                if p["x"] > w + 6:
                    p["x"] = -6
                if p["y"] < -6 or p["y"] > h + 6:
                    p["vy"] *= -1
                    p["y"] = min(max(p["y"], -5), h + 5)
                r = p["r"]
                self.create_oval(p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r,
                                 fill=self._neon, outline="", stipple="gray50",
                                 tags="fx")
            if self.winfo_exists():
                self._after_id = self.after(self.TICK_MS, self._tick)
        except Exception:
            self._after_id = None

    def destroy(self) -> None:
        """Cancela o timer antes de destruir o banner."""
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        super().destroy()
