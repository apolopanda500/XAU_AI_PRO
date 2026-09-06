# -*- coding: utf-8 -*-
"""Aba Grafico - chart profissional com indicadores, crosshair e desenho."""
from __future__ import annotations

import csv
import math
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

from app.components.cards import Card, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.theme.mexc import Theme

TFMAP = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440, "W1": 10080}
TFORDER = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"]


def _sma(vals, n):
    out, s, q = [], 0.0, []
    for v in vals:
        q.append(v); s += v
        if len(q) > n: s -= q.pop(0)
        out.append(s / len(q) if len(q) < n else s / n)
    return out


def _ema(vals, n):
    out, k = [], 2.0 / (n + 1)
    e = None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def _bb(vals, n=20, mult=2.0):
    mid = _sma(vals, n)
    up, lo = [], []
    for i in range(len(vals)):
        w = vals[max(0, i - n + 1):i + 1]
        m = mid[i]
        var = sum((x - m) ** 2 for x in w) / len(w)
        sd = math.sqrt(var)
        up.append(m + mult * sd); lo.append(m - mult * sd)
    return mid, up, lo


def _rsi(vals, n=14):
    out, gains, losses, prev = [], [], [], None
    for v in vals:
        if prev is None:
            out.append(50.0)
        else:
            ch = v - prev
            gains.append(max(ch, 0.0)); losses.append(max(-ch, 0.0))
            if len(gains) >= n:
                ag = sum(gains[-n:]) / n; al = sum(losses[-n:]) / n
                rs = ag / al if al > 0 else 100.0
                out.append(100.0 - 100.0 / (1.0 + rs))
            else:
                out.append(50.0)
        prev = v
    return out


class ChartCanvas(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=Theme.CARD, highlightthickness=0, **kw)
        self._candles = []; self._kind = "candles"; self._indicators = {}
        self._drawings = []; self._draw_tool = None; self._pan_x = 0
        self._zoom = 1.0; self._pan_start = None; self._hover = None
        self._grid = True; self._show_volume = True
        self._pad_l = 70; self._pad_r = 12; self._pad_t = 16; self._pad_b = 28
        self._vol_ratio = 0.22; self._subinfo = ""
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    def set_data(self, candles, kind="candles"):
        self._candles = candles or []; self._kind = kind; self._draw()

    def set_indicator(self, name, spec):
        self._indicators[name] = spec; self._draw()

    def clear_indicators(self):
        self._indicators = {}; self._draw()

    def add_drawing(self, tool): self._draw_tool = tool

    def clear_drawings(self):
        self._drawings = []; self._draw_tool = None; self._draw()

    def export_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "open", "high", "low", "close"])
            for c in self._candles:
                w.writerow([c["time"], c["open"], c["high"], c["low"], c["close"]])
        return len(self._candles)

    def save_screenshot(self, path):
        ps = self.postscript(colormode="color", pagewidth=self.winfo_width() * 2, pageheight=self.winfo_height() * 2)
        with open(path, "w", encoding="utf-8") as fh: fh.write(ps)
        return len(ps)

    def _metrics(self):
        w = max(self.winfo_width(), 320); h = max(self.winfo_height(), 220)
        lows = [c["low"] for c in self._candles] or [0]
        highs = [c["high"] for c in self._candles] or [1]
        lo = min(lows); hi = max(highs); rng = (hi - lo) or 1.0
        pad = rng * 0.05; lo -= pad; hi += pad; rng = (hi - lo) or 1.0
        return w, h, lo, hi, rng

    def _chart_rect(self, w, h):
        top = self._pad_t; bot = h - self._pad_b
        if self._show_volume: bot -= int((h - self._pad_t - self._pad_b) * self._vol_ratio)
        return self._pad_l, top, w - self._pad_r, bot

    def _vol_rect(self, w, h):
        ch = h - self._pad_t - self._pad_b
        top = h - self._pad_b - int(ch * self._vol_ratio) + 4
        return self._pad_l, top, w - self._pad_r, h - self._pad_b

    def _x(self, i, left, right):
        n = max(1, len(self._candles) - 1)
        return left + self._pan_x + (right - left) * i / n * self._zoom

    def _y(self, v, top, bot, lo, rng):
        return bot - (bot - top) * (v - lo) / rng

    def _draw(self):
        self.delete("all")
        if not self._candles:
            self.create_text(self.winfo_width() / 2, self.winfo_height() / 2, text="Sem dados - clique Atualizar", fill=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 12))
            return
        w, h, lo, hi, rng = self._metrics()
        left, top, right, bot = self._chart_rect(w, h)
        self._draw_grid(left, top, right, bot)
        self._draw_price_axis(left, top, bot, lo, hi, rng)
        if self._show_volume: self._draw_volume(w, h, left, right)
        self._draw_candles(left, top, right, bot, lo, hi, rng)
        self._draw_indicators(left, top, right, bot, lo, hi, rng)
        self._draw_time_axis(left, right, bot)
        self._draw_crosshair(w, h)

    def _draw_grid(self, left, top, right, bot):
        if not self._grid: return
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
            self.create_text(left - 6, y, text=f"{v:,.2f}", fill=Theme.TEXT_MUTED, anchor="e", font=(Theme.FONT_MONO, 8))

    def _draw_time_axis(self, left, right, bot):
        n = len(self._candles); step = max(1, n // 6)
        for i in range(0, n, step):
            x = self._x(i, left, right)
            if x < left or x > right: continue
            self.create_text(x, bot + 14, text=self._candles[i]["time"], fill=Theme.TEXT_MUTED, font=(Theme.FONT_MONO, 7), anchor="n")

    def _draw_volume(self, w, h, left, right):
        vl, vt, vr, vb = self._vol_rect(w, h)
        self.create_rectangle(vl, vt, vr, vb, outline=Theme.BORDER, fill=Theme.CARD)
        vols = [c.get("volume", 0) for c in self._candles]
        mx = max(vols) if vols else 1
        if mx <= 0: return
        n = len(self._candles)
        for i in range(n):
            x0 = self._x(i, left, right)
            x1 = self._x(i + 0.5, left, right) if i < n - 1 else x0 + 4
            v = vols[i]; y_top = vb - (vb - vt) * v / mx
            color = Theme.SUCCESS if self._candles[i]["close"] >= self._candles[i]["open"] else Theme.DANGER
            self.create_rectangle(x0, y_top, x1, vb, outline=color, fill=color)

    def _draw_candles(self, left, top, right, bot, lo, hi, rng):
        n = len(self._candles)
        for i in range(n):
            c = self._candles[i]; x = self._x(i, left, right)
            up = c["close"] >= c["open"]; color = Theme.SUCCESS if up else Theme.DANGER
            o = self._y(c["open"], top, bot, lo, rng)
            cl = self._y(c["close"], top, bot, lo, rng)
            hh = self._y(c["high"], top, bot, lo, rng)
            ll = self._y(c["low"], top, bot, lo, rng)
            self.create_line(x, hh, x, ll, fill=color, width=1)
            body_top = min(o, cl); body_bot = max(o, cl)
            wick_w = max(1, int((right - left) / n / 2 * self._zoom))
            fill = color if up else Theme.CARD
            self.create_rectangle(x - wick_w, body_top, x + wick_w, body_bot, outline=color, fill=fill)

    def _draw_indicators(self, left, top, right, bot, lo, hi, rng):
        closes = [c["close"] for c in self._candles]
        for name, spec in self._indicators.items():
            t = spec.get("type", "")
            if t == "sma":
                vals = _sma(closes, spec.get("period", 20))
                self._draw_line(vals, left, top, right, bot, lo, rng, spec.get("color", Theme.ACCENT), name)
            elif t == "ema":
                vals = _ema(closes, spec.get("period", 12))
                self._draw_line(vals, left, top, right, bot, lo, rng, spec.get("color", Theme.WARNING), name)
            elif t == "bollinger":
                mid, up, lo_bb = _bb(closes, spec.get("period", 20), spec.get("mult", 2.0))
                self._draw_line(mid, left, top, right, bot, lo, rng, Theme.ACCENT, "BB Mid")
                self._draw_line(up, left, top, right, bot, lo, rng, Theme.SUCCESS, "BB Up")
                self._draw_line(lo_bb, left, top, right, bot, lo, rng, Theme.DANGER, "BB Lo")

    def _draw_line(self, vals, left, top, right, bot, lo, rng, color, label):
        pts = []
        for i, v in enumerate(vals):
            x = self._x(i, left, right); y = self._y(v, top, bot, lo, rng)
            pts.extend([x, y])
        if len(pts) >= 4: self.create_line(pts, fill=color, width=1.2)

    def _draw_crosshair(self, w, h):
        if self._hover is None: return
        x, y = self._hover
        self.create_line(x, self._pad_t, x, h - self._pad_b, fill=Theme.TEXT_MUTED, dash=(3, 3))
        self.create_line(self._pad_l, y, w - self._pad_r, y, fill=Theme.TEXT_MUTED, dash=(3, 3))

    def _on_wheel(self, event):
        self._zoom = max(0.5, min(3.0, self._zoom * (1.1 if event.delta > 0 else 0.9))); self._draw()

    def _on_click(self, event):
        if self._draw_tool:
            self._drawings.append({"tool": self._draw_tool, "points": [(event.x, event.y)]})
        else: self._pan_start = event.x

    def _on_drag(self, event):
        if self._draw_tool and self._drawings:
            self._drawings[-1]["points"].append((event.x, event.y)); self._draw()
        elif self._pan_start is not None:
            self._pan_x += event.x - self._pan_start; self._pan_start = event.x; self._draw()

    def _on_release(self, event): self._pan_start = None

    def _on_motion(self, event): self._hover = (event.x, event.y); self._draw()

    def _on_leave(self, event): self._hover = None; self._draw()


class ChartsTab:
    def __init__(self, parent, robot, market, on_status):
        self.parent = parent; self.robot = robot; self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG); self.frame.pack(fill="both", expand=True)
        self._running = False; self._refresh_busy = False; self._last_data = None
        self._build()

    def _build(self):
        from app.components.banner import TabBanner
        TabBanner(self.frame, "charts")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Grafico", bg=Theme.BG, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Analise tecnica profissional", bg=Theme.BG, fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)
        toolbar = tk.Frame(self.frame, bg=Theme.BG); toolbar.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(toolbar, text="Ativo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.sym_var = tk.StringVar(value="XAUUSD")
        tk.Entry(toolbar, textvariable=self.sym_var, width=10, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT, relief="flat").pack(side="left", padx=(4, 12))
        tk.Label(toolbar, text="Timeframe", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.tf_var = tk.StringVar(value="M5")
        for tf in TFORDER:
            tk.Radiobutton(toolbar, text=tf, variable=self.tf_var, value=tf, bg=Theme.BG, fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL, activebackground=Theme.BG, font=(Theme.FONT_FAMILY, 8)).pack(side="left")
        tk.Label(toolbar, text="Tipo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=(12, 0))
        self.kind_var = tk.StringVar(value="candles")
        for k, lbl in [("candles", "Candle"), ("line", "Linha"), ("bar", "OHLC")]:
            tk.Radiobutton(toolbar, text=lbl, variable=self.kind_var, value=k, bg=Theme.BG, fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL, activebackground=Theme.BG, font=(Theme.FONT_FAMILY, 8)).pack(side="left")
        ind_bar = tk.Frame(self.frame, bg=Theme.BG); ind_bar.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(ind_bar, text="Indicadores:", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.sma_var = tk.BooleanVar(value=False)
        self.ema_var = tk.BooleanVar(value=False)
        self.bb_var = tk.BooleanVar(value=False)
        self.vol_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ind_bar, text="SMA", variable=self.sma_var, bg=Theme.BG, fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL, activebackground=Theme.BG, command=self._refresh).pack(side="left", padx=4)
        tk.Checkbutton(ind_bar, text="EMA", variable=self.ema_var, bg=Theme.BG, fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL, activebackground=Theme.BG, command=self._refresh).pack(side="left", padx=4)
        tk.Checkbutton(ind_bar, text="Bollinger", variable=self.bb_var, bg=Theme.BG, fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL, activebackground=Theme.BG, command=self._refresh).pack(side="left", padx=4)
        tk.Checkbutton(ind_bar, text="Volume", variable=self.vol_var, bg=Theme.BG, fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL, activebackground=Theme.BG, command=self._refresh).pack(side="left", padx=4)
        btn_bar = tk.Frame(self.frame, bg=Theme.BG); btn_bar.pack(fill="x", padx=24, pady=(0, 8))
        AccentButton(btn_bar, text="Atualizar", command=self._refresh, width=12).pack(side="left", padx=4)
        SecondaryButton(btn_bar, text="Limpar", command=self._clear_ind, width=10).pack(side="left", padx=4)
        SecondaryButton(btn_bar, text="Exportar CSV", command=self._export_csv, width=14).pack(side="left", padx=4)
        SecondaryButton(btn_bar, text="Salvar imagem", command=self._save_img, width=14).pack(side="left", padx=4)
        chart_card = Card(self.frame, title=""); chart_card.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        self.chart = ChartCanvas(chart_card.body, height=420); self.chart.pack(fill="both", expand=True)
        self.info_lbl = tk.Label(self.frame, text="Pronto", bg=Theme.BG, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9), anchor="w")
        self.info_lbl.pack(fill="x", padx=24, pady=(0, 8))

    def _clear_ind(self):
        self.chart.clear_indicators(); self.on_status("Indicadores limpos")

    def _export_csv(self):
        path = Path.home() / "Desktop" / f"chart_{self.sym_var.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            n = self.chart.export_csv(path); self.on_status(f"CSV exportado: {n} candles")
        except Exception as e: self.on_status(f"Erro CSV: {e}")

    def _save_img(self):
        path = Path.home() / "Desktop" / f"chart_{self.sym_var.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ps"
        try:
            self.chart.save_screenshot(path); self.on_status(f"Imagem salva: {path.name}")
        except Exception as e: self.on_status(f"Erro imagem: {e}")

    def _refresh(self):
        if self._refresh_busy: return
        self._refresh_busy = True; self.on_status("Atualizando grafico...")
        threading.Thread(target=self._collect_thread, daemon=True).start()

    def _collect_thread(self):
        try:
            data = self._collect(); self.frame.after(0, lambda: self._finish_refresh(data))
        except Exception as e: self.frame.after(0, lambda: self._finish_refresh_error(e))

    def _finish_refresh(self, data):
        self._refresh_busy = False; self._last_data = data; self._apply(data)

    def _finish_refresh_error(self, exc):
        self._refresh_busy = False; self.on_status(f"Grafico: {exc}")

    def _collect(self):
        symbol = self.sym_var.get(); tf = self.tf_var.get()
        minutes = TFMAP.get(tf, 5)
        limit = max(60, min(500, 240 // max(1, minutes // 5)))
        candles = []; source = "mt5"
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                tfmap = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15, 30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4, 1440: mt5.TIMEFRAME_D1, 10080: mt5.TIMEFRAME_W1}
                rates = mt5.copy_rates_from_pos(symbol, tfmap.get(minutes, mt5.TIMEFRAME_M5), 0, limit)
                if rates is not None and len(rates):
                    for r in rates[-limit:]:
                        candles.append({"symbol": symbol, "time": datetime.fromtimestamp(int(r["time"])).strftime("%d/%m %H:%M"), "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"]), "volume": float(r.get("tick_volume", 0))})
                mt5.shutdown()
        except Exception: pass
        if not candles:
            candles = self._from_csv(symbol, limit); source = "csv" if candles else "sem dados"
        return {"candles": candles, "symbol": symbol, "tf": tf, "source": source}

    def _from_csv(self, symbol, limit):
        base = Path(__file__).resolve().parent.parent.parent.parent / "MQL5" / "Files" / "Data"
        ds = base / "dataset.csv"; out = []
        if not ds.exists(): return out
        for enc in ("utf-16", "utf-8-sig", "utf-8", "latin-1"):
            try:
                rows = []
                with open(ds, encoding=enc, newline="") as fh:
                    for row in csv.DictReader(fh):
                        if (row.get("Symbol") or row.get("symbol") or "").strip().upper() != symbol.upper(): continue
                        try:
                            rows.append({"symbol": symbol, "time": row.get("Time", ""), "open": float(row.get("Open", 0)), "high": float(row.get("High", 0)), "low": float(row.get("Low", 0)), "close": float(row.get("Close", 0)), "volume": float(row.get("Volume", row.get("volume", 0)))})
                        except (TypeError, ValueError): continue
                if rows: out = rows; break
            except Exception: continue
        return out[-limit:]

    def _apply(self, data):
        self.chart.set_data(data["candles"], self.kind_var.get())
        self.chart._show_volume = self.vol_var.get()
        inds = {}
        if self.sma_var.get():
            inds["sma20"] = {"type": "sma", "period": 20, "color": Theme.ACCENT}
            inds["sma50"] = {"type": "sma", "period": 50, "color": Theme.WARNING}
        if self.ema_var.get():
            inds["ema12"] = {"type": "ema", "period": 12, "color": Theme.PRIMARY}
        if self.bb_var.get():
            inds["bb"] = {"type": "bollinger", "period": 20, "mult": 2.0}
        for name, spec in inds.items():
            self.chart.set_indicator(name, spec)
        total = len(data["candles"])
        self.info_lbl.configure(text=f"{data['symbol']} {data['tf']} | {total} candle(s) | fonte: {data.get('source')} | atualizado: {datetime.now().strftime('%H:%M:%S')}")
        self.on_status(f"Grafico atualizado: {data['symbol']} {data['tf']} ({total})")

    def refresh(self): self._refresh()
    def refresh_now(self): self._refresh()
    def start_auto(self):
        if self._running: return
        self._running = True; self._refresh()
    def stop_auto(self): self._running = False
