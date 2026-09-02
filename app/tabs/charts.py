# -*- coding: utf-8 -*-
"""Aba Graficos - graficos em tempo real (estilo TradingView).

- Selecao de simbolo, timeframe e tipo (Linha / Candles / Area)
- Auto-refresh com intervalo configuravel (default 60s = 1 min)
- Desenho leve em Canvas (sem matplotlib) compativel com o EXE
- Dados: MetaTrader5 (se conectado) com fallback para dataset.csv local
- MCP TradingView configurado nas Integracoes (mcp/servers/tradingview.json)
"""
from __future__ import annotations

import csv
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme

TFMAP = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440, "W1": 10080,
}
SYMBOLS_DEFAULT = ["XAUUSD", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD",
                   "USDJPY", "AUDUSD", "USDCAD", "NZDUSD"]


class ChartCanvas(tk.Canvas):
    """Canvas com desenho de linha/candles estilo TradingView."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=Theme.CARD, highlightthickness=0, **kw)
        self._candles: list[dict] = []
        self._kind = "linha"
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, candles: list[dict], kind: str = "linha") -> None:
        self._candles = candles
        self._kind = kind
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 320)
        h = max(self.winfo_height(), 220)
        if not self._candles:
            self.create_text(w // 2, h // 2, text="Sem dados - aguardando...",
                             fill=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 11))
            return
        pad = 44
        lows = [c["low"] for c in self._candles]
        highs = [c["high"] for c in self._candles]
        lo = min(lows)
        hi = max(highs)
        rng = (hi - lo) or 1.0
        n = len(self._candles)
        def X(i):
            return pad + (w - 2 * pad) * i / max(1, n - 1)
        def Y(v):
            return h - pad - (h - 2 * pad) * (v - lo) / rng

        # Grade
        for i in range(5):
            gy = pad + (h - 2 * pad) * i / 4
            self.create_line(pad, gy, w - pad, gy, fill="#1e2a3a", width=1)
            val = hi - rng * i / 4
            self.create_text(w - pad + 4, gy, text=f"{val:.2f}", anchor="w",
                             fill=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8))

        if self._kind == "linha":
            pts = []
            for i, c in enumerate(self._candles):
                pts.extend([X(i), Y(c["close"])])
            color = Theme.SUCCESS if self._candles[-1]["close"] >= self._candles[0]["close"] else Theme.DANGER
            self.create_line(pts, fill=color, width=2, smooth=True)
        elif self._kind == "area":
            pts = []
            for i, c in enumerate(self._candles):
                pts.extend([X(i), Y(c["close"])])
            poly = list(pts) + [X(n - 1), Y(lo)] + [X(0), Y(lo)]
            self.create_polygon(poly, fill=Theme.PRIMARY, outline="", stipple="gray50")
            self.create_line(pts, fill=Theme.PRIMARY, width=2, smooth=True)
        else:  # candles
            bw = max(2.0, (w - 2 * pad) / max(1, n) * 0.6)
            for i, c in enumerate(self._candles):
                x = X(i)
                up = c["close"] >= c["open"]
                col = Theme.SUCCESS if up else Theme.DANGER
                self.create_line(x, Y(c["high"]), x, Y(c["low"]), fill=col, width=1)
                top, bot = Y(c["open"]), Y(c["close"])
                if abs(top - bot) < 1:
                    self.create_line(x - bw / 2, top, x + bw / 2, top, fill=col, width=2)
                else:
                    self.create_rectangle(x - bw / 2, top, x + bw / 2, bot, fill=col, outline=col)

        # Ultimo preco
        last = self._candles[-1]
        self.create_text(pad, 14, text=f"{last.get('symbol','')}  {last.get('time','')}",
                         fill=Theme.TEXT, anchor="w", font=(Theme.FONT_FAMILY, 9, "bold"))
        self.create_text(w - pad, 14, text=f"Fech: {last['close']:.2f}",
                         fill=Theme.TEXT, anchor="e", font=(Theme.FONT_FAMILY, 9, "bold"))


class ChartsTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._running = False
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Graficos", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Tempo real - estilo TradingView",
                 bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)

        # Controles
        ctrl = tk.Frame(self.frame, bg=Theme.BG)
        ctrl.pack(fill="x", padx=24, pady=(0, 8))
        cfg = get_config()
        symbols = cfg.get("market", "symbols", default=SYMBOLS_DEFAULT) or SYMBOLS_DEFAULT
        self.sym_var = tk.StringVar(value="XAUUSD")
        tk.Label(ctrl, text="Simbolo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        tk.OptionMenu(ctrl, self.sym_var, *symbols).pack(side="left", padx=4)

        self.tf_var = tk.StringVar(value="M5")
        tk.Label(ctrl, text="Timeframe", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        tk.OptionMenu(ctrl, self.tf_var, *list(TFMAP)).pack(side="left", padx=4)

        self.kind_var = tk.StringVar(value="candles")
        tk.Label(ctrl, text="Tipo", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        tk.OptionMenu(ctrl, self.kind_var, "candles", "linha", "area").pack(side="left", padx=4)

        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ctrl, text="Auto (1 min)", variable=self.auto_var, bg=Theme.BG, fg=Theme.TEXT,
                       selectcolor=Theme.PANEL, activebackground=Theme.BG,
                       font=(Theme.FONT_FAMILY, 9)).pack(side="left", padx=10)
        tk.Label(ctrl, text="s", bg=Theme.BG, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.interval_entry = tk.Entry(ctrl, width=6, bg=Theme.PANEL, fg=Theme.TEXT,
                                       relief="flat", highlightbackground=Theme.BORDER,
                                       highlightthickness=1)
        self.interval_entry.insert(0, "60")
        self.interval_entry.pack(side="left", padx=2)
        SecondaryButton(ctrl, text="Atualizar", command=self.refresh_now, width=10).pack(side="left", padx=8)

        # Canvas do grafico
        card = Card(self.frame, title="Grafico em tempo real")
        card.pack(fill="both", expand=True, padx=24, pady=10)
        self.chart = ChartCanvas(card.body)
        self.chart.pack(fill="both", expand=True, padx=8, pady=8)

        self.info_lbl = tk.Label(self.frame, text="", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                                 font=(Theme.FONT_FAMILY, 9))
        self.info_lbl.pack(fill="x", padx=24, pady=(0, 12))

    # ------------------------------------------------------------------
    def start_auto(self) -> None:
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()
        self.refresh_now()

    def stop_auto(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                interval = 60
                try:
                    interval = max(5, int(self.interval_entry.get()))
                except ValueError:
                    pass
                time.sleep(interval)
                if self.auto_var.get():
                    self.refresh_now()
            except Exception:
                time.sleep(10)

    def refresh_now(self) -> None:
        try:
            data = self._collect()
            self.frame.after(0, lambda d=data: self._apply(d))
        except Exception as e:  # noqa: BLE001
            self.on_status(f"Grafico: erro de leitura: {e}")

    def _collect(self) -> dict:
        symbol = self.sym_var.get()
        tf = self.tf_var.get()
        minutes = TFMAP.get(tf, 5)
        limit = max(30, min(500, 240 // max(1, minutes // 5)))
        candles: list[dict] = []
        source = "mt5"
        try:
            import MetaTrader5 as mt5  # noqa: PLC0415
            if not mt5.initialize():
                raise RuntimeError("MT5 nao inicializado")
            tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15,
                      30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4,
                      1440: mt5.TIMEFRAME_D1, 10080: mt5.TIMEFRAME_W1}
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(minutes, mt5.TIMEFRAME_M5), 0, limit)
            if rates is not None and len(rates):
                for r in rates[-limit:]:
                    candles.append({
                        "symbol": symbol, "time": datetime.fromtimestamp(int(r["time"])).strftime("%d/%m %H:%M"),
                        "open": float(r["open"]), "high": float(r["high"]),
                        "low": float(r["low"]), "close": float(r["close"]),
                    })
        except Exception:
            source = "csv"
        if not candles:
            candles = self._from_csv(symbol, limit)
            if candles:
                source = "csv(historico)"
        return {"candles": candles, "symbol": symbol, "tf": tf, "source": source}

    def _from_csv(self, symbol: str, limit: int) -> list[dict]:
        """Fallback: le dataset.csv local filtrado pelo simbolo."""
        base = Path(__file__).resolve().parent.parent.parent / "MQL5" / "Files" / "Data"
        ds = base / "dataset.csv"
        out: list[dict] = []
        if not ds.exists():
            return out
        try:
            with open(ds, encoding="utf-8", errors="ignore") as fh:
                for row in csv.DictReader(fh):
                    sym = (row.get("Symbol") or row.get("symbol") or "").strip()
                    if sym.upper() != symbol.upper():
                        continue
                    try:
                        out.append({
                            "symbol": symbol,
                            "time": row.get("Time", row.get("time", "")),
                            "open": float(row.get("Open", row.get("open", 0))),
                            "high": float(row.get("High", row.get("high", 0))),
                            "low": float(row.get("Low", row.get("low", 0))),
                            "close": float(row.get("Close", row.get("close", 0))),
                        })
                    except (TypeError, ValueError):
                        continue
        except Exception:
            return out
        return out[-limit:]

    def _apply(self, data: dict) -> None:
        candles = data.get("candles") or []
        self.chart.set_data(candles, self.kind_var.get())
        n = len(candles)
        self.info_lbl.configure(
            text=f"{data['symbol']} {data['tf']} | {n} candle(s) | fonte: {data.get('source', '-')} | "
                 f"atualizado: {datetime.now().strftime('%H:%M:%S')}")
        self.on_status(f"Grafico atualizado: {data['symbol']} {data['tf']} ({n} candles)")