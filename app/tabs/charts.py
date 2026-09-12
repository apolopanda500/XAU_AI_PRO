# -*- coding: utf-8 -*-
"""Aba Grafico profissional - candles, indicadores (SMA/EMA/BB/VWAP/RSI/ATR),
ferramentas de desenho, edicao de objetos, salvamento de layout e exportacao."""
from __future__ import annotations

import csv
import json
import math
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.components.cards import Card, SecondaryButton, AccentButton
from app.theme.mexc import Theme
from app.utils.paths import get_data_dir

from app.data.indicators import _sma, _ema, _rsi  # noqa: E402,F401 (deduplicado)

TFMAP = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440, "W1": 10080}
TFORDER = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"]
TOOLS = [
    ("pan", "Mao"),
    ("select", "Selecionar"),
    ("trend", "Tendencia"),
    ("hline", "Horizontal"),
    ("rect", "Retangulo"),
    ("fib", "Fibonacci"),
    ("free", "Mao livre"),
]

FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]


# ---------------------------------------------------------------------------
# Indicadores puros (funcoes top-level testaveis)
# ---------------------------------------------------------------------------
def _bb(vals: list[float], n: int = 20, mult: float = 2.0) -> tuple[list[float], list[float], list[float]]:
    mid = _sma(vals, n)
    up, lo = [], []
    for i in range(len(vals)):
        w = vals[max(0, i - n + 1):i + 1]
        m = mid[i]
        var = sum((x - m) ** 2 for x in w) / len(w)
        sd = math.sqrt(var)
        up.append(m + mult * sd)
        lo.append(m - mult * sd)
    return mid, up, lo


def _atr(candles: list[dict[str, Any]], n: int = 14) -> list[float | None]:
    """Average True Range (Wilder). Retorna None nas primeiras n-1 barras."""
    trs = []
    for i, c in enumerate(candles):
        if i == 0:
            trs.append(float(c["high"]) - float(c["low"]))
        else:
            pc = float(candles[i - 1]["close"])
            trs.append(max(float(c["high"]) - float(c["low"]),
                          abs(float(c["high"]) - pc),
                          abs(float(c["low"]) - pc)))
    out: list[float | None] = []
    atr = None
    for i, tr in enumerate(trs):
        if i < n:
            out.append(None)
        elif i == n:
            atr = sum(trs[:n]) / n
            out.append(atr)
        else:
            atr = (atr * (n - 1) + tr) / n
            out.append(atr)
    return out


def _typical(c: dict[str, Any]) -> float:
    return (float(c["high"]) + float(c["low"]) + float(c["close"])) / 3.0


def _vwap(candles: list[dict[str, Any]]) -> list[float]:
    """VWAP acumulado da janela visivel (soma TP*V / soma V)."""
    out, spv, sv = [], 0.0, 0.0
    for c in candles:
        v = float(c.get("volume", 0) or 0)
        spv += _typical(c) * v
        sv += v
        out.append(spv / sv if sv > 0 else float(c["close"]))
    return out


# ---------------------------------------------------------------------------
# Persistencia de layout (JSON, leve)
# ---------------------------------------------------------------------------
def _layout_path(symbol: str, tf: str) -> Path:
    return get_data_dir() / "charts" / f"{symbol}_{tf}.json"


def serialize_layout(indicators: dict[str, dict], drawings: list[dict]) -> dict[str, Any]:
    return {
        "version": 2,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "indicators": [{"name": k, **v} for k, v in indicators.items()],
        "drawings": drawings,
    }


def deserialize_layout(payload: dict[str, Any]) -> tuple[dict[str, dict], list[dict]]:
    inds: dict[str, dict] = {}
    for item in payload.get("indicators", []) or []:
        name = item.get("name")
        if not name:
            continue
        spec = {k: v for k, v in item.items() if k != "name"}
        inds[name] = spec
    drawings = []
    for d in payload.get("drawings", []) or []:
        if isinstance(d, dict) and d.get("tool") and isinstance(d.get("pts"), list):
            pts = [(float(a), float(b)) for a, b in d["pts"] if _is_pair(a, b)]
            minp = 2 if d["tool"] in ("trend", "rect", "fib") else 1
            if len(pts) >= minp:
                drawings.append({"tool": d["tool"], "pts": pts})
    return inds, drawings


def _is_pair(a: Any, b: Any) -> bool:
    try:
        float(a)
        float(b)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# ChartCanvas - canvas de grafico profissional
# ---------------------------------------------------------------------------
class ChartCanvas(tk.Canvas):
    def __init__(self, parent, on_hover: Callable[[str], None] | None = None, **kw):
        super().__init__(parent, bg=Theme.CARD, highlightthickness=0, **kw)
        self._candles: list[dict[str, Any]] = []
        self._kind = "candles"
        self._indicators: dict[str, dict] = {}
        self._drawings: list[dict] = []
        self._tool = "pan"
        self._pan_x = 0.0
        self._zoom = 1.0
        self._pan_start = None
        self._hover = None
        self._hover_i = None
        self._selected: int | None = None
        self._grid = True
        self._show_volume = True
        self._rsi_on = False
        self._atr_on = False
        self._pad_l = 70
        self._pad_r = 12
        self._pad_t = 16
        self._pad_b = 28
        self._on_hover = on_hover
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Delete>", lambda e: self.delete_selected())

    # ---------------- API publica ----------------
    def set_data(self, candles, kind="candles"):
        self._candles = candles or []
        self._kind = kind
        self._draw()

    def set_indicator(self, name, spec):
        self._indicators[name] = spec
        if spec.get("type") == "rsi":
            self._rsi_on = True
        if spec.get("type") == "atr":
            self._atr_on = True
        self._draw()

    def clear_indicators(self):
        self._indicators = {}
        self._rsi_on = False
        self._atr_on = False
        self._draw()

    def indicators_spec(self) -> dict[str, dict]:
        return dict(self._indicators)

    def set_tool(self, tool: str):
        self._tool = tool
        self._selected = None
        self.configure(cursor="crosshair" if tool != "pan" else "arrow")
        self._draw()

    def drawings(self) -> list[dict]:
        return list(self._drawings)

    def load_drawings(self, drawings: list[dict]):
        self._drawings = [d for d in drawings if d.get("tool") and d.get("pts")]
        self._selected = None
        self._draw()

    def set_volume_visible(self, visible: bool):
        self._show_volume = bool(visible)
        self._draw()

    def set_sub_indicators(self, rsi: bool, atr: bool):
        self._rsi_on = bool(rsi)
        self._atr_on = bool(atr)
        self._draw()

    def delete_selected(self):
        if self._selected is not None and 0 <= self._selected < len(self._drawings):
            self._drawings.pop(self._selected)
            self._selected = None
            self._draw()
            return True
        return False

    def clear_drawings(self):
        self._drawings = []
        self._selected = None
        self._draw()

    def export_csv(self, path) -> int:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "open", "high", "low", "close"])
            for c in self._candles:
                w.writerow([c["time"], c["open"], c["high"], c["low"], c["close"]])
        return len(self._candles)

    def save_png(self, path) -> bool:
        """PNG real via PIL; retorna False se PIL indisponivel (fallback PS)."""
        try:
            from PIL import ImageGrab
        except Exception:
            return False
        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty()
            img = ImageGrab.grab(bbox=(x, y, x + self.winfo_width(), y + self.winfo_height()))
            img.save(path)
            return True
        except Exception:
            return False

    def save_ps(self, path) -> int:
        ps = self.postscript(colormode="color", pagewidth=self.winfo_width() * 2,
                             pageheight=self.winfo_height() * 2)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(ps)
        return len(ps)

    # ---------------- metricas / paineis ----------------
    def _metrics(self):
        w = max(self.winfo_width(), 320)
        h = max(self.winfo_height(), 220)
        lows = [c["low"] for c in self._candles] or [0]
        highs = [c["high"] for c in self._candles] or [1]
        lo = min(lows)
        hi = max(highs)
        rng = (hi - lo) or 1.0
        pad = rng * 0.05
        lo -= pad
        hi += pad
        rng = (hi - lo) or 1.0
        return w, h, lo, hi, rng

    def _panels(self, w, h):
        total = h - self._pad_t - self._pad_b
        subs = []
        if self._show_volume:
            subs.append("volume")
        if self._rsi_on:
            subs.append("rsi")
        if self._atr_on:
            subs.append("atr")
        price_h = total if not subs else int(total * 0.62)
        y = self._pad_t
        panels = [("price", (self._pad_l, y, w - self._pad_r, y + price_h))]
        y += price_h
        rest = total - price_h
        n = max(1, len(subs))
        for i, name in enumerate(subs):
            ph = rest // (n - i) if n - i > 0 else rest
            panels.append((name, (self._pad_l, y, w - self._pad_r, y + max(24, ph - 2))))
            y += max(24, ph - 2) + 2
        return panels

    def _panel_rect(self, name, panels):
        for pname, rect in panels:
            if pname == name:
                return rect
        return panels[0][1]

    def _x(self, i, left, right):
        n = max(1, len(self._candles) - 1)
        return left + self._pan_x + (right - left) * i / n * self._zoom

    def _y(self, v, top, bot, lo, rng):
        return bot - (bot - top) * (v - lo) / rng

    def _to_norm(self, x, y):
        w, h, lo, hi, rng = self._metrics()
        left, top, right, bot = self._panel_rect("price", self._panels(w, h))
        if right - left <= 0 or bot - top <= 0:
            return None
        xf = (x - left) / (right - left)
        price = lo + (bot - y) / (bot - top) * rng
        return (max(0.0, min(1.0, xf)), price)

    def _from_norm(self, xf, price):
        w, h, lo, hi, rng = self._metrics()
        left, top, right, bot = self._panel_rect("price", self._panels(w, h))
        return (left + xf * (right - left), self._y(price, top, bot, lo, rng))

    # ---------------- desenho ----------------
    def _draw(self):
        self.delete("all")
        if not self._candles:
            self.create_text(self.winfo_width() / 2, self.winfo_height() / 2,
                             text="Sem dados - clique Atualizar", fill=Theme.TEXT_MUTED,
                             font=(Theme.FONT_FAMILY, 12))
            return
        w, h, lo, hi, rng = self._metrics()
        panels = self._panels(w, h)
        left, top, right, bot = self._panel_rect("price", panels)
        self._draw_grid(left, top, right, bot)
        self._draw_price_axis(left, top, bot, lo, hi, rng)
        if self._show_volume:
            self._draw_panel_bg("volume", panels, "Volume")
        if self._rsi_on:
            self._draw_panel_bg("rsi", panels, "RSI")
        if self._atr_on:
            self._draw_panel_bg("atr", panels, "ATR")
        self._draw_candles(left, top, right, bot, lo, hi, rng)
        self._draw_indicators(left, top, right, bot, lo, hi, rng, panels)
        self._draw_volume(panels)
        self._draw_drawings(panels)
        self._draw_time_axis(left, right, bot)
        self._draw_crosshair(w, h)
        if self._hover_i is not None:
            self._draw_hover_info(left, top)

    def _draw_panel_bg(self, name, panels, label):
        vleft, vtop, vright, vbot = self._panel_rect(name, panels)
        self.create_rectangle(vleft, vtop, vright, vbot, outline=Theme.BORDER, fill=Theme.CARD)
        self.create_text(vleft + 6, vtop + 3, text=label, fill=Theme.TEXT_MUTED,
                         font=(Theme.FONT_MONO, 7), anchor="nw")

    def _draw_grid(self, left, top, right, bot):
        if not self._grid:
            return
        for i in range(1, 6):
            y = top + (bot - top) * i / 6
            self.create_line(left, y, right, y, fill=Theme.BORDER, dash=(2, 4))
        for i in range(1, 8):
            x = left + (right - left) * i / 8
            self.create_line(x, top, x, bot, fill=Theme.BORDER, dash=(2, 4))

    def _draw_price_axis(self, left, top, bot, lo, hi, rng):
        for i in range(7):
            v = lo + rng * (6 - i) / 6
            y = top + (bot - top) * i / 6
            self.create_text(left - 6, y, text=f"{v:,.2f}", fill=Theme.TEXT_MUTED,
                             anchor="e", font=(Theme.FONT_MONO, 8))

    def _draw_time_axis(self, left, right, bot):
        n = len(self._candles)
        step = max(1, n // 6)
        for i in range(0, n, step):
            x = self._x(i, left, right)
            if x < left or x > right:
                continue
            self.create_text(x, bot + 14, text=self._candles[i]["time"],
                             fill=Theme.TEXT_MUTED, font=(Theme.FONT_MONO, 7), anchor="n")

    def _draw_candles(self, left, top, right, bot, lo, hi, rng):
        n = len(self._candles)
        wick_w = max(1, int((right - left) / max(1, n) / 2 * self._zoom))
        for i in range(n):
            c = self._candles[i]
            x = self._x(i, left, right)
            if x < left - 20 or x > right + 20:
                continue
            up = c["close"] >= c["open"]
            color = Theme.SUCCESS if up else Theme.DANGER
            o = self._y(c["open"], top, bot, lo, rng)
            cl = self._y(c["close"], top, bot, lo, rng)
            hh = self._y(c["high"], top, bot, lo, rng)
            ll = self._y(c["low"], top, bot, lo, rng)
            if self._kind in ("line", "area"):
                continue
            self.create_line(x, hh, x, ll, fill=color, width=1)
            body_top = min(o, cl)
            body_bot = max(o, cl)
            fill = color if up else Theme.CARD
            self.create_rectangle(x - wick_w, body_top, x + wick_w, body_bot,
                                  outline=color, fill=fill)
        if self._kind in ("line", "area"):
            pts = []
            for i in range(n):
                pts.extend([self._x(i, left, right), self._y(self._candles[i]["close"], top, bot, lo, rng)])
            if len(pts) >= 4:
                self.create_line(pts, fill=Theme.PRIMARY, width=1.4)

    def _draw_indicators(self, left, top, right, bot, lo, hi, rng, panels):
        closes = [c["close"] for c in self._candles]
        for name, spec in self._indicators.items():
            t = spec.get("type", "")
            if t == "sma":
                self._draw_line(_sma(closes, int(spec.get("period", 20))),
                                left, top, right, bot, lo, rng, spec.get("color", Theme.ACCENT))
            elif t == "ema":
                self._draw_line(_ema(closes, int(spec.get("period", 12))),
                                left, top, right, bot, lo, rng, spec.get("color", Theme.WARNING))
            elif t == "bollinger":
                mid, up, low = _bb(closes, int(spec.get("period", 20)), float(spec.get("mult", 2.0)))
                self._draw_line(mid, left, top, right, bot, lo, rng, Theme.ACCENT)
                self._draw_line(up, left, top, right, bot, lo, rng, Theme.SUCCESS)
                self._draw_line(low, left, top, right, bot, lo, rng, Theme.DANGER)
            elif t == "vwap":
                self._draw_line(_vwap(self._candles), left, top, right, bot, lo, rng,
                                spec.get("color", Theme.PRIMARY))
            elif t == "rsi":
                self._draw_sub_line(_rsi(closes, int(spec.get("period", 14))), "rsi", panels, 0.0, 100.0)
            elif t == "atr":
                self._draw_sub_line(_atr(self._candles, int(spec.get("period", 14))), "atr", panels)

    def _draw_line(self, vals, left, top, right, bot, lo, rng, color):
        pts = []
        for i, v in enumerate(vals):
            if v is None:
                continue
            pts.extend([self._x(i, left, right), self._y(v, top, bot, lo, rng)])
        if len(pts) >= 4:
            self.create_line(pts, fill=color, width=1.2)

    def _draw_sub_line(self, vals, panel_name, panels, vmin=None, vmax=None):
        rect = self._panel_rect(panel_name, panels)
        vleft, vtop, vright, vbot = rect
        good = [v for v in vals if v is not None]
        if not good:
            return
        lo = vmin if vmin is not None else min(good)
        hi = vmax if vmax is not None else max(good)
        rng = (hi - lo) or 1.0
        pts = []
        for i, v in enumerate(vals):
            if v is None:
                continue
            x = self._x(i, vleft, vright)
            y = vbot - (vbot - vtop) * (v - lo) / rng
            pts.extend([x, y])
        if len(pts) >= 4:
            self.create_line(pts, fill=Theme.WARNING if panel_name == "rsi" else Theme.ACCENT, width=1.2)
        if panel_name == "rsi" and vmin is not None:
            for lv, color in ((30.0, Theme.DANGER), (70.0, Theme.SUCCESS)):
                y = vbot - (vbot - vtop) * (lv - lo) / rng
                self.create_line(vleft, y, vright, y, fill=color, dash=(3, 3))
            self.create_text(vright - 4, vtop + 3, text=f"{good[-1]:.1f}", fill=Theme.TEXT,
                             font=(Theme.FONT_MONO, 8), anchor="ne")

    def _draw_volume(self, panels):
        rect = self._panel_rect("volume", panels)
        vl, vt, vr, vb = rect
        vols = [c.get("volume", 0) for c in self._candles]
        mx = max(vols) if vols else 1
        if mx <= 0:
            return
        n = len(self._candles)
        for i in range(n):
            x0 = self._x(i, vl, vr)
            x1 = self._x(i + 0.5, vl, vr) if i < n - 1 else x0 + 2
            v = vols[i]
            y_top = vb - (vb - vt) * v / mx
            color = Theme.SUCCESS if self._candles[i]["close"] >= self._candles[i]["open"] else Theme.DANGER
            self.create_rectangle(x0, y_top, x1, vb, outline=color, fill=color)

    # ---------------- desenhos ----------------
    def _draw_drawings(self, panels):
        left, top, right, bot = self._panel_rect("price", panels)
        for idx, d in enumerate(self._drawings):
            tool = d.get("tool")
            pts = d.get("pts", [])
            sel = idx == self._selected
            color = Theme.PRIMARY if sel else Theme.WARNING
            width = 2 if sel else 1.4
            if tool in ("trend", "free"):
                pixels = []
                for xf, price in pts:
                    px, py = self._from_norm(xf, price)
                    pixels.extend([px, py])
                if len(pixels) >= 4:
                    self.create_line(pixels, fill=color, width=width)
            elif tool == "hline":
                _, price = pts[0] if pts else (0.0, 0.0)
                _, y = self._from_norm(0.0, price)
                self.create_line(left, y, right, y, fill=color, width=width)
            elif tool == "rect":
                (x0, p0), (x1, p1) = pts[0], pts[-1]
                ax, ay = self._from_norm(x0, p0)
                bx, by = self._from_norm(x1, p1)
                self.create_rectangle(ax, ay, bx, by, outline=color, width=width,
                                      fill=Theme.WARNING if sel else "")
            elif tool == "fib":
                (x0, p0), (x1, p1) = pts[0], pts[-1]
                ax, _ = self._from_norm(x0, p0)
                bx, _ = self._from_norm(x1, p1)
                if p1 < p0:
                    p0, p1 = p1, p0
                for frac in FIB_LEVELS:
                    price = p0 + (p1 - p0) * frac
                    _, y = self._from_norm(x0, price)
                    self.create_line(ax, y, bx, y, fill=color, width=width, dash=(4, 2))
                if sel:
                    _, y0 = self._from_norm(x0, p0)
                    _, y1 = self._from_norm(x0, p1)
                    self.create_text(ax + 4, y0, text=f"0% {p0:,.2f}", fill=color,
                                     font=(Theme.FONT_MONO, 7), anchor="sw")
                    self.create_text(ax + 4, y1, text=f"100% {p1:,.2f}", fill=color,
                                     font=(Theme.FONT_MONO, 7), anchor="nw")

    def _hit_test(self, x, y):
        best, best_d = None, 12.0
        for idx, d in enumerate(self._drawings):
            tool = d.get("tool")
            pts = d.get("pts", [])
            if tool in ("trend", "free"):
                pixels = []
                for xf, price in pts:
                    px, py = self._from_norm(xf, price)
                    pixels.append((px, py))
                for a, b in zip(pixels, pixels[1:]):
                    d = _dist_point_seg(x, y, a, b)
                    if d < best_d:
                        best, best_d = idx, d
            elif tool == "hline":
                _, price = pts[0] if pts else (0.0, 0.0)
                _, py = self._from_norm(0.0, price)
                if abs(y - py) < best_d:
                    best, best_d = idx, abs(y - py)
            elif tool == "rect":
                (x0, p0), (x1, p1) = pts[0], pts[-1]
                ax, ay = self._from_norm(x0, p0)
                bx, by = self._from_norm(x1, p1)
                xa, xb = min(ax, bx), max(ax, bx)
                ya, yb = min(ay, by), max(ay, by)
                if xa - 6 <= x <= xb + 6 and ya - 6 <= y <= yb + 6:
                    d = min(abs(x - xa), abs(x - xb), abs(y - ya), abs(y - yb))
                    if d < best_d:
                        best, best_d = idx, d
        return best

    # ---------------- interacao ----------------
    def _on_click(self, event):
        self.focus_set()
        if self._tool == "select":
            self._selected = self._hit_test(event.x, event.y)
            self._pan_start = None
        elif self._tool == "pan":
            self._selected = None
            self._pan_start = event.x
        else:
            self._selected = None
            norm = self._to_norm(event.x, event.y)
            if norm is None:
                return
            if self._tool in ("trend", "rect", "fib"):
                opened = self._drawings and self._drawings[-1].get("tool") == self._tool and len(self._drawings[-1]["pts"]) == 1
                if opened:
                    self._drawings[-1]["pts"].append(norm)
                else:
                    self._drawings.append({"tool": self._tool, "pts": [norm]})
            elif self._tool == "hline":
                self._drawings.append({"tool": self._tool, "pts": [norm]})
            else:
                self._drawings.append({"tool": self._tool, "pts": [norm]})
        self._draw()

    def _on_drag(self, event):
        if self._tool == "select" and self._selected is not None:
            norm = self._to_norm(event.x, event.y)
            if norm is None:
                return
            if self._drag_anchor is None:
                self._drag_anchor = norm
                return
            dx = norm[0] - self._drag_anchor[0]
            dy = norm[1] - self._drag_anchor[1]
            self._drag_anchor = norm
            d = self._drawings[self._selected]
            d["pts"] = [(max(0.0, min(1.0, x + dx)), p + dy) for x, p in d["pts"]]
            self._draw()
        elif self._tool == "free":
            norm = self._to_norm(event.x, event.y)
            if norm is not None and self._drawings and self._drawings[-1].get("tool") == "free":
                self._drawings[-1]["pts"].append(norm)
                self._draw()
        elif self._pan_start is not None:
            self._pan_x += event.x - self._pan_start
            self._pan_start = event.x
            self._draw()

    def _on_release(self, event):
        self._pan_start = None
        self._drag_anchor = None

    def _on_wheel(self, event):
        self._zoom = max(0.5, min(3.0, self._zoom * (1.1 if event.delta > 0 else 0.9)))
        self._draw()

    def _on_motion(self, event):
        self._hover = (event.x, event.y)
        self._hover_i = self._nearest_bar(event.x)
        info = ""
        if self._hover_i is not None:
            c = self._candles[self._hover_i]
            info = (f"{c['time']}  O {c['open']:,.2f}  H {c['high']:,.2f}  "
                    f"L {c['low']:,.2f}  C {c['close']:,.2f}  V {c.get('volume', 0):,.0f}")
        if self._on_hover:
            try:
                self._on_hover(info)
            except Exception:
                pass
        self._draw()

    def _on_leave(self, event):
        self._hover = None
        self._hover_i = None
        self._draw()

    def _nearest_bar(self, x):
        if not self._candles:
            return None
        w, h, lo, hi, rng = self._metrics()
        left, top, right, bot = self._panel_rect("price", self._panels(w, h))
        n = len(self._candles)
        i = int((x - left - self._pan_x) / ((right - left) * self._zoom) * max(1, n - 1))
        i = max(0, min(n - 1, i))
        return i

    def _draw_crosshair(self, w, h):
        if self._hover is None:
            return
        x, y = self._hover
        self.create_line(x, self._pad_t, x, h - self._pad_b, fill=Theme.TEXT_MUTED, dash=(3, 3))
        self.create_line(self._pad_l, y, w - self._pad_r, y, fill=Theme.TEXT_MUTED, dash=(3, 3))

    def _draw_hover_info(self, left, top):
        if self._hover_i is None:
            return
        c = self._candles[self._hover_i]
        txt = (f"O {c['open']:,.2f} H {c['high']:,.2f} L {c['low']:,.2f} "
               f"C {c['close']:,.2f} V {c.get('volume', 0):,.0f}")
        self.create_text(left + 4, top + 4, text=txt, fill=Theme.TEXT,
                         font=(Theme.FONT_MONO, 8), anchor="nw")


def _dist_point_seg(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


# ---------------------------------------------------------------------------
# ChartsTab - aba grafico
# ---------------------------------------------------------------------------
class ChartsTab:
    def __init__(self, parent, robot, market, on_status):
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._running = False
        self._refresh_busy = False
        self._last_data = None
        self._load_lock = False
        self._queue: queue.Queue = queue.Queue()
        self._poller_started = False
        self._poll_active = True
        self._build()

    def _build(self):
        from app.components.banner import TabBanner
        TabBanner(self.frame, "charts")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 6))
        tk.Label(header, text="Grafico", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Analise tecnica profissional - desenhe, edite e salve",
                 bg=Theme.BG, fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)
        # Linha 1: ativo + timeframe + tipo
        row1 = tk.Frame(self.frame, bg=Theme.BG)
        row1.pack(fill="x", padx=24, pady=(8, 4))
        tk.Label(row1, text="Ativo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.sym_var = tk.StringVar(value="XAUUSD")
        tk.Entry(row1, textvariable=self.sym_var, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                 insertbackground=Theme.TEXT, relief="flat").pack(side="left", padx=(4, 12))
        tk.Label(row1, text="Timeframe", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.tf_var = tk.StringVar(value="M5")
        for tf in TFORDER:
            tk.Radiobutton(row1, text=tf, variable=self.tf_var, value=tf, bg=Theme.BG,
                           fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL,
                           activebackground=Theme.BG, font=(Theme.FONT_FAMILY, 8)).pack(side="left")
        tk.Label(row1, text="Tipo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=(12, 0))
        self.kind_var = tk.StringVar(value="candles")
        for k, lbl in [("candles", "Candle"), ("line", "Linha"), ("bar", "OHLC")]:
            tk.Radiobutton(row1, text=lbl, variable=self.kind_var, value=k, bg=Theme.BG,
                           fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL,
                           activebackground=Theme.BG, font=(Theme.FONT_FAMILY, 8)).pack(side="left")
        # Linha 2: indicadores
        row2 = tk.Frame(self.frame, bg=Theme.BG)
        row2.pack(fill="x", padx=24, pady=(2, 4))
        tk.Label(row2, text="Indicadores", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.sma_var = tk.BooleanVar(value=False)
        self.ema_var = tk.BooleanVar(value=False)
        self.bb_var = tk.BooleanVar(value=False)
        self.vwap_var = tk.BooleanVar(value=False)
        self.rsi_var = tk.BooleanVar(value=False)
        self.atr_var = tk.BooleanVar(value=False)
        self.vol_var = tk.BooleanVar(value=True)
        self.p_sma = self._add_check(row2, "SMA", self.sma_var, 20)
        self.p_ema = self._add_check(row2, "EMA", self.ema_var, 12)
        self.p_bb = self._add_check(row2, "BB", self.bb_var, 20)
        self.p_vwap = self._add_check(row2, "VWAP", self.vwap_var, None)
        self.p_rsi = self._add_check(row2, "RSI", self.rsi_var, 14)
        self.p_atr = self._add_check(row2, "ATR", self.atr_var, 14)
        tk.Checkbutton(row2, text="Volume", variable=self.vol_var, bg=Theme.BG,
                       fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL,
                       activebackground=Theme.BG, command=self._refresh).pack(side="left", padx=4)
        # Linha 3: ferramentas de desenho
        row3 = tk.Frame(self.frame, bg=Theme.BG)
        row3.pack(fill="x", padx=24, pady=(2, 4))
        tk.Label(row3, text="Ferramentas", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.tool_var = tk.StringVar(value="pan")
        for key, lbl in TOOLS:
            tk.Radiobutton(row3, text=lbl, variable=self.tool_var, value=key, bg=Theme.BG,
                           fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL,
                           activebackground=Theme.BG, indicatoron=False,
                           font=(Theme.FONT_FAMILY, 8), command=self._on_tool).pack(side="left", padx=2)
        # Linha 4: acoes
        row4 = tk.Frame(self.frame, bg=Theme.BG)
        row4.pack(fill="x", padx=24, pady=(2, 6))
        AccentButton(row4, text="Atualizar", command=self._refresh, width=11).pack(side="left", padx=3)
        SecondaryButton(row4, text="Excluir sel.", command=self._delete_sel, width=11).pack(side="left", padx=3)
        SecondaryButton(row4, text="Limpar desenhos", command=self._clear_draw, width=14).pack(side="left", padx=3)
        SecondaryButton(row4, text="Salvar layout", command=self._save_layout, width=13).pack(side="left", padx=3)
        SecondaryButton(row4, text="Carregar layout", command=self._load_layout, width=14).pack(side="left", padx=3)
        SecondaryButton(row4, text="Exportar CSV", command=self._export_csv, width=13).pack(side="left", padx=3)
        SecondaryButton(row4, text="Salvar imagem", command=self._save_img, width=13).pack(side="left", padx=3)
        chart_card = Card(self.frame, title="")
        chart_card.pack(fill="both", expand=True, padx=24, pady=(0, 8))
        self.chart = ChartCanvas(chart_card.body, on_hover=self._on_hover, height=430)
        self.chart.pack(fill="both", expand=True)
        self.info_lbl = tk.Label(self.frame, text="Pronto", bg=Theme.BG, fg=Theme.TEXT_MUTED,
                                 font=(Theme.FONT_FAMILY, 9), anchor="w")
        self.info_lbl.pack(fill="x", padx=24, pady=(0, 8))

    def _add_check(self, parent, text, var, period_default):
        frame = tk.Frame(parent, bg=Theme.BG)
        frame.pack(side="left", padx=3)
        tk.Checkbutton(frame, text=text, variable=var, bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                       selectcolor=Theme.PANEL, activebackground=Theme.BG,
                       command=self._refresh).pack(side="left")
        if period_default is not None:
            ent = tk.Entry(frame, width=3, bg=Theme.PANEL, fg=Theme.TEXT,
                           insertbackground=Theme.TEXT, relief="flat", justify="center")
            ent.insert(0, str(period_default))
            ent.pack(side="left", padx=(2, 0))
            return ent
        return None

    # ---------------- acoes ----------------
    def _on_tool(self):
        self.chart.set_tool(self.tool_var.get())
        self.on_status(f"Ferramenta: {self.tool_var.get()}")

    def _delete_sel(self):
        if self.chart.delete_selected():
            self.on_status("Objeto excluido")
        else:
            self.on_status("Nenhum objeto selecionado")

    def _clear_draw(self):
        self.chart.clear_drawings()
        self.on_status("Desenhos limpos")

    def _on_hover(self, info):
        self.info_lbl.configure(text=info or "Pronto")

    def _current_period(self, entry) -> int:
        try:
            return max(2, int(entry.get().strip() or "0"))
        except ValueError:
            return 20

    def _indicator_specs(self) -> dict[str, dict]:
        inds: dict[str, dict] = {}
        if self.sma_var.get():
            n = self._current_period(self.p_sma)
            inds[f"sma{n}"] = {"type": "sma", "period": n, "color": Theme.ACCENT}
        if self.ema_var.get():
            n = self._current_period(self.p_ema)
            inds[f"ema{n}"] = {"type": "ema", "period": n, "color": Theme.WARNING}
        if self.bb_var.get():
            n = self._current_period(self.p_bb)
            inds["bb"] = {"type": "bollinger", "period": n, "mult": 2.0}
        if self.vwap_var.get():
            inds["vwap"] = {"type": "vwap", "color": Theme.PRIMARY}
        if self.rsi_var.get():
            n = self._current_period(self.p_rsi)
            inds[f"rsi{n}"] = {"type": "rsi", "period": n}
        if self.atr_var.get():
            n = self._current_period(self.p_atr)
            inds[f"atr{n}"] = {"type": "atr", "period": n}
        return inds

    def _save_layout(self):
        try:
            path = _layout_path(self.sym_var.get(), self.tf_var.get())
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = serialize_layout(self.chart.indicators_spec(), self.chart.drawings())
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.on_status(f"Layout salvo: {path.name}")
        except Exception as e:
            self.on_status(f"Erro ao salvar layout: {e}")

    def _load_layout(self):
        try:
            path = _layout_path(self.sym_var.get(), self.tf_var.get())
            if not path.exists():
                self.on_status("Nenhum layout salvo para este ativo/timeframe")
                return
            payload = json.loads(path.read_text(encoding="utf-8"))
            inds, drawings = deserialize_layout(payload)
            self.chart.clear_indicators()
            for name, spec in inds.items():
                self.chart.set_indicator(name, spec)
            self.chart.load_drawings(drawings)
            self._sync_vars_from(inds)
            self.on_status(f"Layout carregado: {path.name}")
        except Exception as e:
            self.on_status(f"Erro ao carregar layout: {e}")

    def _sync_vars_from(self, inds: dict[str, dict]):
        self.sma_var.set(any(s.get("type") == "sma" for s in inds.values()))
        self.ema_var.set(any(s.get("type") == "ema" for s in inds.values()))
        self.bb_var.set(any(s.get("type") == "bollinger" for s in inds.values()))
        self.vwap_var.set(any(s.get("type") == "vwap" for s in inds.values()))
        self.rsi_var.set(any(s.get("type") == "rsi" for s in inds.values()))
        self.atr_var.set(any(s.get("type") == "atr" for s in inds.values()))
        self.chart.set_sub_indicators(self.rsi_var.get(), self.atr_var.get())

    def _export_csv(self):
        path = Path.home() / "Desktop" / f"chart_{self.sym_var.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            n = self.chart.export_csv(path)
            self.on_status(f"CSV exportado: {n} candles -> {path.name}")
        except Exception as e:
            self.on_status(f"Erro CSV: {e}")

    def _save_img(self):
        base = Path.home() / "Desktop" / f"chart_{self.sym_var.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        png = base.with_suffix(".png")
        try:
            if self.chart.save_png(png):
                self.on_status(f"Imagem PNG salva: {png.name}")
                return
            ps = base.with_suffix(".ps")
            self.chart.save_ps(ps)
            self.on_status(f"Imagem salva (PostScript): {ps.name}")
        except Exception as e:
            self.on_status(f"Erro imagem: {e}")

    # ---------------- dados ----------------
    def _refresh(self):
        if self._refresh_busy:
            return
        self._refresh_busy = True
        self.on_status("Atualizando grafico...")
        symbol = self.sym_var.get()
        tf = self.tf_var.get()
        self._start_poller()
        threading.Thread(target=self._collect_worker, args=(symbol, tf), daemon=True).start()

    def _collect_worker(self, symbol, tf):
        """Roda em thread daemon. Nunca toca em widgets: so enfileira."""
        try:
            data = self._collect(symbol, tf)
        except Exception as e:
            self._queue.put(("err", e))
        else:
            self._queue.put(("ok", data))

    def _start_poller(self):
        if self._poller_started:
            return
        self._poller_started = True
        try:
            self.frame.after(120, self._poll)
        except tk.TclError:
            self._poller_started = False

    def stop_poller(self):
        """Para o loop de poller (usado em teardown/testes)."""
        self._poll_active = False

    def _poll(self):
        if not self._poll_active:
            return
        """Esvazia a fila no main thread (unico lugar que toca widgets)."""
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "ok":
                    self._finish_refresh(payload)
                else:
                    self._finish_refresh_error(payload)
        except queue.Empty:
            pass
        except tk.TclError:
            return
        try:
            self.frame.after(120, self._poll)
        except tk.TclError:
            pass

    def _finish_refresh(self, data):
        self._refresh_busy = False
        self._last_data = data
        self._apply(data)

    def _finish_refresh_error(self, exc):
        self._refresh_busy = False
        self.on_status(f"Grafico: {exc}")

    def _collect(self, symbol, tf):
        minutes = TFMAP.get(tf, 5)
        limit = max(60, min(500, 240 // max(1, minutes // 5)))
        candles = []
        source = "mt5"
        try:
            from app.mt5_lock import mt5_lock
            import MetaTrader5 as mt5
            tfmap = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15,
                     30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4,
                     1440: mt5.TIMEFRAME_D1, 10080: mt5.TIMEFRAME_W1}
            with mt5_lock:
                mt5.symbol_select(symbol, True)
                rates = mt5.copy_rates_from_pos(symbol, tfmap.get(minutes, mt5.TIMEFRAME_M5), 0, limit)
                if rates is None and mt5.initialize():
                    mt5.symbol_select(symbol, True)
                    rates = mt5.copy_rates_from_pos(symbol, tfmap.get(minutes, mt5.TIMEFRAME_M5), 0, limit)
            if rates is not None and len(rates):
                for r in rates[-limit:]:
                    candles.append({"symbol": symbol,
                                    "time": datetime.fromtimestamp(int(r["time"])).strftime("%d/%m %H:%M"),
                                    "open": float(r["open"]), "high": float(r["high"]),
                                    "low": float(r["low"]), "close": float(r["close"]),
                                    "volume": float(r["tick_volume"])})
        except Exception as e:
            source = f"mt5 erro: {e}"
        if not candles:
            candles = self._from_csv(symbol, limit)
            if candles:
                source = "csv (fallback)"
        return {"candles": candles, "symbol": symbol, "tf": tf, "source": source}

    def _from_csv(self, symbol, limit):
        base = Path(__file__).resolve().parent.parent.parent.parent / "MQL5" / "Files" / "Data"
        ds = base / "dataset.csv"
        out = []
        if not ds.exists():
            return out
        for enc in ("utf-16", "utf-8-sig", "utf-8", "latin-1"):
            try:
                rows = []
                with open(ds, encoding=enc, newline="") as fh:
                    for row in csv.DictReader(fh):
                        if (row.get("Symbol") or row.get("symbol") or "").strip().upper() != symbol.upper():
                            continue
                        try:
                            rows.append({"symbol": symbol, "time": row.get("Time", ""),
                                         "open": float(row.get("Open", 0)), "high": float(row.get("High", 0)),
                                         "low": float(row.get("Low", 0)), "close": float(row.get("Close", 0)),
                                         "volume": float(row.get("Volume", row.get("volume", 0)))})
                        except (TypeError, ValueError):
                            continue
                if rows:
                    out = rows
                    break
            except Exception:
                continue
        return out[-limit:]

    def _apply(self, data):
        self.chart.set_data(data["candles"], self.kind_var.get())
        self.chart.set_volume_visible(self.vol_var.get())
        self.chart.clear_indicators()
        inds = self._indicator_specs()
        for name, spec in inds.items():
            self.chart.set_indicator(name, spec)
        self._auto_load(data["symbol"], data["tf"], inds)
        total = len(data["candles"])
        self.info_lbl.configure(
            text=(f"{data['symbol']} {data['tf']} | {total} candle(s) | fonte: {data.get('source')} "
                  f"| atualizado: {datetime.now().strftime('%H:%M:%S')}"))
        self.on_status(f"Grafico atualizado: {data['symbol']} {data['tf']} ({total})")

    def _auto_load(self, symbol, tf, current_inds):
        """Carrega desenhos salvos do par (sem sobrescrever indicadores marcados)."""
        if self._load_lock:
            return
        try:
            path = _layout_path(symbol, tf)
            if not path.exists():
                return
            payload = json.loads(path.read_text(encoding="utf-8"))
            _, drawings = deserialize_layout(payload)
            if drawings:
                self.chart.load_drawings(drawings)
        except Exception:
            pass

    def refresh(self):
        self._refresh()

    def refresh_now(self):
        self._refresh()

    def start_auto(self):
        if self._running:
            return
        self._running = True
        self._refresh()

    def stop_auto(self):
        self._running = False