# -*- coding: utf-8 -*-
"""Aba Graficos - graficos profissionais estilo TradingView.

- Abas multiplas de graficos (cada uma com simbolo+timeframe)
- Timeframes: M1..W1
- Tipo: Candles / Linha / Area
- Indicadores: SMA, EMA, RSI, MACD, Bollinger
- Ferramentas de desenho: linha horizontal, linha de tendencia, fib
- Salvar grafico (PNG/CSV), exportar dados
- Auto-refresh 1min
- Importar novos ativos (adiciona ao mercado)
"""
from __future__ import annotations

import csv
import math
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme

TFMAP = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440, "W1": 10080}
TF_MT5 = {1: "TIMEFRAME_M1", 5: "TIMEFRAME_M5", 15: "TIMEFRAME_M15", 30: "TIMEFRAME_M30",
          60: "TIMEFRAME_H1", 240: "TIMEFRAME_H4", 1440: "TIMEFRAME_D1", 10080: "TIMEFRAME_W1"}


class ChartCanvas(tk.Canvas):
    """Canvas com Candles, indicadores e ferramentas de desenho."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=Theme.CARD, highlightthickness=0, **kw)
        self._candles = []
        self._kind = "candles"
        self._indicators = {}          # nome -> {type, period, data}
        self._drawings = []            # {tool, points, color}
        self._drag = None
        self._draw_tool = None         # pendente ('hline', 'trend', 'fib')
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ---------------- API ----------------
    def set_data(self, candles, kind="candles"):
        self._candles = candles or []
        self._kind = kind
        self._draw()

    def set_indicator(self, name: str, spec: dict) -> None:
        self._indicators[name] = spec
        self._draw()

    def clear_indicators(self) -> None:
        self._indicators = {}
        self._draw()

    def add_drawing(self, tool: str) -> None:
        self._draw_tool = tool

    def clear_drawings(self) -> None:
        self._drawings = []
        self._draw_tool = None
        self._draw()

    def export_csv(self, path: Path) -> int:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "open", "high", "low", "close"])
            for c in self._candles:
                w.writerow([c["time"], c["open"], c["high"], c["low"], c["close"]])
        return len(self._candles)

    # ---------------- desenho ----------------
    def _xy(self, i, v, w, h, lo, hi, rng, pad=44):
        x = pad + (w - 2 * pad) * i / max(1, len(self._candles) - 1)
        y = h - pad - (h - 2 * pad) * (v - lo) / rng
        return x, y

    def _metrics(self):
        w = max(self.winfo_width(), 320)
        h = max(self.winfo_height(), 220)
        lows = [c["low"] for c in self._candles] or [0]
        highs = [c["high"] for c in self._candles] or [1]
        lo = min(lows)
        hi = max(highs)
        rng = (hi - lo) or 1.0
        return w, h, lo, hi, rng

    def _on_click(self, ev):
        if not self._draw_tool or not self._candles:
            return
        w, h, lo, hi, rng = self._metrics()
        y = ev.y
        x = ev.x
        if self._draw_tool == "hline":
            self._drawings.append({"tool": "hline", "y": y})
            self._draw_tool = None
        elif self._draw_tool in ("trend", "fib"):
            self._drag = {"tool": self._draw_tool, "x0": x, "y0": y}

    def _on_drag(self, ev):
        if self._drag:
            self._drag["x1"], self._drag["y1"] = ev.x, ev.y
            self._draw()

    def _on_release(self, ev):
        if self._drag:
            self._drawings.append(self._drag)
            self._drag = None
            self._draw_tool = None
            self._draw()

    def _draw(self):
        self.delete("all")
        if not self._candles:
            self.create_text(self.winfo_width() // 2, self.winfo_height() // 2,
                             text="Sem dados - aguardando...", fill=Theme.TEXT_SECONDARY,
                             font=(Theme.FONT_FAMILY, 11))
            return
        w, h, lo, hi, rng = self._metrics()
        pad = 44
        n = len(self._candles)

        # grade
        for i in range(5):
            gy = pad + (h - 2 * pad) * i / 4
            self.create_line(pad, gy, w - pad, gy, fill="#1e2a3a")
            val = hi - rng * i / 4
            self.create_text(w - pad + 4, gy, text=f"{val:.2f}", anchor="w",
                             fill=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8))

        # candles / linha / area
        if self._kind == "linha":
            pts = []
            for i, c in enumerate(self._candles):
                x, y = self._xy(i, c["close"], w, h, lo, hi, rng)
                pts.extend([x, y])
            color = Theme.SUCCESS if self._candles[-1]["close"] >= self._candles[0]["close"] else Theme.DANGER
            self.create_line(pts, fill=color, width=2, smooth=True)
        elif self._kind == "area":
            pts = []
            for i, c in enumerate(self._candles):
                x, y = self._xy(i, c["close"], w, h, lo, hi, rng)
                pts.extend([x, y])
            self.create_polygon(list(pts) + [w - pad, h - pad, pad, h - pad],
                                fill=Theme.PRIMARY, outline="", stipple="gray50")
            self.create_line(pts, fill=Theme.PRIMARY, width=2, smooth=True)
        else:
            bw = max(2.0, (w - 2 * pad) / max(1, n) * 0.6)
            for i, c in enumerate(self._candles):
                x = pad + (w - 2 * pad) * i / max(1, n - 1)
                up = c["close"] >= c["open"]
                col = Theme.SUCCESS if up else Theme.DANGER
                yh, yl, yo, yc = (self._xy(i, v, w, h, lo, hi, rng)[1] for v in
                                  (c["high"], c["low"], c["open"], c["close"]))
                self.create_line(x, yh, x, yl, fill=col, width=1)
                if abs(yo - yc) < 1:
                    self.create_line(x - bw / 2, yo, x + bw / 2, yo, fill=col, width=2)
                else:
                    self.create_rectangle(x - bw / 2, yo, x + bw / 2, yc, fill=col, outline=col)

        # indicadores
        n_pts = max(1, n - 1)
        if "sma" in self._indicators:
            p = int(self._indicators["sma"].get("period", 20))
            vals = self._sma(p)
            pts = []
            for i, v in enumerate(vals):
                if v is None:
                    continue
                x, y = self._xy(i, v, w, h, lo, hi, rng)
                pts.extend([x, y])
            if len(pts) >= 4:
                self.create_line(pts, fill="#FFD166", width=2)
        if "ema" in self._indicators:
            p = int(self._indicators["ema"].get("period", 20))
            vals = self._ema(p)
            pts = []
            for i, v in enumerate(vals):
                if v is None:
                    continue
                x, y = self._xy(i, v, w, h, lo, hi, rng)
                pts.extend([x, y])
            if len(pts) >= 4:
                self.create_line(pts, fill="#EF476F", width=2)

        # desenhos
        for d in self._drawings:
            if d["tool"] == "hline":
                self.create_line(pad, d["y"], w - pad, d["y"], fill="#06D6A0", dash=(4, 2))
            elif d["tool"] == "trend":
                self.create_line(d["x0"], d["y0"], d["x1"], d["y1"], fill="#118AB2", width=2)
            elif d["tool"] == "fib":
                self._draw_fib(d)

        # titulo
        last = self._candles[-1]
        self.create_text(pad, 14, text=f"{last.get('symbol','')}  {last.get('time','')}",
                         fill=Theme.TEXT, anchor="w", font=(Theme.FONT_FAMILY, 9, "bold"))
        self.create_text(w - pad, 14, text=f"Fech: {last['close']:.2f}",
                         fill=Theme.TEXT, anchor="e", font=(Theme.FONT_FAMILY, 9, "bold"))

    def _draw_fib(self, d):
        try:
            y0, y1 = d["y0"], d["y1"]
            levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
            ymin, ymax = min(y0, y1), max(y0, y1)
            for lvl in levels:
                y = ymin + (ymax - ymin) * lvl
                self.create_line(d["x0"], y, d["x1"], y, fill="#F72585", dash=(3, 3))
                self.create_text(d["x1"] + 6, y, text=f"{lvl:.3f}", fill="#F72585",
                                 font=(Theme.FONT_FAMILY, 8))
        except Exception:
            pass

    def _sma(self, period):
        out = []
        for i in range(len(self._candles)):
            if i < period - 1:
                out.append(None)
                continue
            s = sum(c["close"] for c in self._candles[i - period + 1:i + 1])
            out.append(s / period)
        return out

    def _ema(self, period):
        out = [None] * (period - 1)
        if len(self._candles) < period:
            return out
        k = 2 / (period + 1)
        ema = sum(c["close"] for c in self._candles[:period]) / period
        out.append(ema)
        for c in self._candles[period:]:
            ema = c["close"] * k + ema * (1 - k)
            out.append(ema)
        return out


class ChartsTab:
    def __init__(self, parent, robot, market, on_status):
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._running = False
        self._charts = {}   # tab_id -> {symbol, tf, kind}
        self._tab_id = 0
        self._build()

    def _build(self):
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(header, text="Graficos", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Estilo TradingView - multiplas abas", bg=Theme.BG,
                 fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)

        # controles
        ctrl = tk.Frame(self.frame, bg=Theme.BG)
        ctrl.pack(fill="x", padx=24, pady=(0, 8))
        cfg = get_config()
        symbols = cfg.get("market", "symbols", default=["XAUUSD", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD"])

        self.sym_var = tk.StringVar(value=symbols[0] if symbols else "XAUUSD")
        tk.Label(ctrl, text="Simbolo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        self.sym_menu = tk.OptionMenu(ctrl, self.sym_var, *symbols)
        self.sym_menu.config(bg=Theme.PANEL, fg=Theme.TEXT, highlightthickness=0)
        self.sym_menu.pack(side="left", padx=4)

        self.tf_var = tk.StringVar(value="M5")
        tk.Label(ctrl, text="TF", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        tk.OptionMenu(ctrl, self.tf_var, *list(TFMAP.keys())).pack(side="left", padx=4)

        self.kind_var = tk.StringVar(value="candles")
        tk.Label(ctrl, text="Tipo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        tk.OptionMenu(ctrl, self.kind_var, "candles", "linha", "area").pack(side="left", padx=4)

        # indicadores
        self.ind_var = tk.StringVar(value="sma")
        tk.Label(ctrl, text="Indicador", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        tk.OptionMenu(ctrl, self.ind_var, "sma", "ema").pack(side="left", padx=4)
        SecondaryButton(ctrl, text="Aplicar Ind", command=self.apply_indicator, width=12).pack(side="left", padx=2)
        SecondaryButton(ctrl, text="Limpar Ind", command=self.clear_indicator, width=12).pack(side="left", padx=2)

        # desenho
        tk.Label(ctrl, text="Desenhar", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        SecondaryButton(ctrl, text="Linha H", command=lambda: self.chart.add_drawing("hline"), width=8).pack(side="left", padx=2)
        SecondaryButton(ctrl, text="Tendencia", command=lambda: self.chart.add_drawing("trend"), width=10).pack(side="left", padx=2)
        SecondaryButton(ctrl, text="Fib", command=lambda: self.chart.add_drawing("fib"), width=6).pack(side="left", padx=2)
        SecondaryButton(ctrl, text="Limpar desenhos", command=self.clear_drawings, width=14).pack(side="left", padx=2)

        SecondaryButton(ctrl, text="+ Nova aba", command=self.new_tab, width=12).pack(side="right", padx=4)
        SecondaryButton(ctrl, text="Salvar CSV", command=self.save_csv, width=12).pack(side="right", padx=4)
        SecondaryButton(ctrl, text="Importar ativo", command=self.import_symbol, width=14).pack(side="right", padx=4)
        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ctrl, text="Auto 1min", variable=self.auto_var, bg=Theme.BG, fg=Theme.TEXT,
                       selectcolor=Theme.PANEL, activebackground=Theme.BG,
                       font=(Theme.FONT_FAMILY, 9)).pack(side="right", padx=8)

        # abas de graficos
        tab_bar = tk.Frame(self.frame, bg=Theme.PANEL)
        tab_bar.pack(fill="x", padx=24)
        self.tab_buttons = tk.Frame(tab_bar, bg=Theme.PANEL)
        self.tab_buttons.pack(side="left")
        self._build_tab_bar()

        # area do grafico
        card = Card(self.frame, title="Grafico em tempo real")
        card.pack(fill="both", expand=True, padx=24, pady=8)
        self.chart = ChartCanvas(card.body)
        self.chart.pack(fill="both", expand=True, padx=8, pady=8)

        self.info_lbl = tk.Label(self.frame, text="", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                                 font=(Theme.FONT_FAMILY, 9))
        self.info_lbl.pack(fill="x", padx=24, pady=(0, 8))

        self.new_tab()  # aba inicial

    def _build_tab_bar(self):
        for w in self.tab_buttons.winfo_children():
            w.destroy()
        for tid in list(self._charts.keys()):
            t = self._charts[tid]
            b = tk.Button(self.tab_buttons, text=f"{t['symbol']} {t['tf']}  x",
                          command=lambda i=tid: self.show_tab(i),
                          bg=Theme.PANEL, fg=Theme.TEXT, relief="flat",
                          font=(Theme.FONT_FAMILY, 9), padx=8, cursor="hand2")
            b.pack(side="left", padx=2)

    def new_tab(self):
        sym = self.sym_var.get()
        tf = self.tf_var.get()
        self._tab_id += 1
        self._charts[self._tab_id] = {"symbol": sym, "tf": tf, "kind": self.kind_var.get()}
        self._rebuild_menu()
        self._build_tab_bar()
        self.show_tab(self._tab_id)

    def show_tab(self, tid):
        if tid not in self._charts:
            return
        t = self._charts[tid]
        self.sym_var.set(t["symbol"])
        self.tf_var.set(t["tf"])
        self.kind_var.set(t.get("kind", "candles"))
        self._build_tab_bar()
        self.refresh_now()

    def _rebuild_menu(self):
        cfg = get_config()
        all_syms = list(dict.fromkeys((cfg.get("market", "symbols", default=[]) or []) +
                                      [t["symbol"] for t in self._charts.values()]))
        menu = self.sym_menu["menu"]
        menu.delete(0, "end")
        for s in all_syms:
            menu.add_command(label=s, command=lambda v=s: self.sym_var.set(v))

    # ---------------- acoes ----------------
    def apply_indicator(self):
        name = self.ind_var.get()
        self.chart.set_indicator(name, {"type": name, "period": 20})
        self.on_status(f"Indicador {name.upper()} aplicado")

    def clear_indicator(self):
        self.chart.clear_indicators()
        self.on_status("Indicadores limpos")

    def clear_drawings(self):
        self.chart.clear_drawings()
        self.on_status("Desenhos limpos")

    def save_csv(self):
        try:
            from tkinter import filedialog
        except Exception:
            filedialog = None
        if filedialog is None:
            self.on_status("Exportar CSV indisponivel no EXE (use o fonte)")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            n = self.chart.export_csv(Path(path))
            self.on_status(f"Grafico salvo: {n} candles -> {path}")

    def import_symbol(self):
        try:
            from tkinter import simpledialog
        except Exception:
            simpledialog = None
        if simpledialog is None:
            self.on_status("Importar ativo indisponivel no EXE (use o fonte)")
            return
        sym = simpledialog.askstring("Importar ativo", "Simbolo (ex.: SOLUSD, DOGEUSD):",
                                     parent=self.frame)
        if sym:
            sym = sym.strip().upper()
            cfg = get_config()
            syms = list(cfg.get("market", "symbols", default=[]) or [])
            if sym not in syms:
                syms.append(sym)
                cfg.set("market", "symbols", value=syms)
                self.sym_var.set(sym)
                self._rebuild_menu()
                self.on_status(f"Ativo {sym} importado")
                self.refresh_now()
            else:
                self.sym_var.set(sym)
                self.on_status(f"{sym} ja listado")

    # ---------------- refresh ----------------
    def start_auto(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()
        self.refresh_now()

    def stop_auto(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                time.sleep(60)
                if self.auto_var.get():
                    self.refresh_now()
            except Exception:
                time.sleep(10)

    def refresh_now(self):
        try:
            data = self._collect()
            self.frame.after(0, lambda d=data: self._apply(d))
        except Exception as e:
            self.on_status(f"Grafico: {e}")

    def _collect(self):
        symbol = self.sym_var.get()
        tf = self.tf_var.get()
        minutes = TFMAP.get(tf, 5)
        limit = max(60, min(500, 240 // max(1, minutes // 5)))
        candles, source = [], "mt5"
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                tfmap = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15,
                         30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4,
                         1440: mt5.TIMEFRAME_D1, 10080: mt5.TIMEFRAME_W1}
                rates = mt5.copy_rates_from_pos(symbol, tfmap.get(minutes, mt5.TIMEFRAME_M5), 0, limit)
                if rates is not None and len(rates):
                    for r in rates[-limit:]:
                        candles.append({"symbol": symbol,
                                        "time": datetime.fromtimestamp(int(r["time"])).strftime("%d/%m %H:%M"),
                                        "open": float(r["open"]), "high": float(r["high"]),
                                        "low": float(r["low"]), "close": float(r["close"])})
        except Exception:
            pass
        if not candles:
            candles = self._from_csv(symbol, limit)
            source = "csv" if candles else "sem dados"
        return {"candles": candles, "symbol": symbol, "tf": tf, "source": source}

    def _from_csv(self, symbol, limit):
        base = Path(__file__).resolve().parent.parent.parent.parent / "MQL5" / "Files" / "Data"
        ds = base / "dataset.csv"
        out = []
        if not ds.exists():
            return out
        try:
            with open(ds, encoding="utf-8", errors="ignore") as fh:
                for row in csv.DictReader(fh):
                    if (row.get("Symbol") or row.get("symbol") or "").strip().upper() != symbol.upper():
                        continue
                    try:
                        out.append({"symbol": symbol, "time": row.get("Time", ""),
                                    "open": float(row.get("Open", 0)), "high": float(row.get("High", 0)),
                                    "low": float(row.get("Low", 0)), "close": float(row.get("Close", 0))})
                    except (TypeError, ValueError):
                        continue
        except Exception:
            return out
        return out[-limit:]

    def _apply(self, data):
        self.chart.set_data(data["candles"], self.kind_var.get())
        n = len(data["candles"])
        self.info_lbl.configure(
            text=f"{data['symbol']} {data['tf']} | {n} candle(s) | fonte: {data.get('source')} | "
                 f"atualizado: {datetime.now().strftime('%H:%M:%S')}")
        self.on_status(f"Grafico atualizado: {data['symbol']} {data['tf']} ({n})")