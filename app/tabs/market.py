# -*- coding: utf-8 -*-
"""Aba Mercado - estilo TradingView (watchlist, chart, info lateral)."""
from __future__ import annotations

import threading
import time
import tkinter as tk
from datetime import datetime
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.market_data import MarketData
from app.market_store import store_quotes
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme
from app.tabs.charts import ChartCanvas, TFMAP, TFORDER, _sma, _ema, _bb

DEFAULT_SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
                   "NZDUSD", "USDCHF", "BTCUSD", "ETHUSD", "SPX500", "NAS100"]


class TradingViewMarket(tk.Frame):
    """Aba Mercado estilo TradingView."""
    def __init__(self, parent, robot: MT5Robot, market: MarketData, on_status: Callable):
        super().__init__(parent, bg=Theme.BG)
        self.robot = robot; self.market = market; self.on_status = on_status
        self._running = False; self._quotes = {}; self._selected = "XAUUSD"
        self._watch_vars = {}; self._symbols = []
        self._build(); self._load_symbols()

    def _build(self):
        self._build_topbar()
        main = tk.Frame(self, bg=Theme.BG)
        main.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        main.columnconfigure(1, weight=1); main.rowconfigure(0, weight=1)
        self._build_watchlist(main, 0, 0)
        self._build_chart_area(main, 1, 0)
        self._build_right_panel(main, 2, 0)
        self._build_statusbar()

    def _build_topbar(self):
        bar = tk.Frame(self, bg=Theme.BG_SECONDARY, height=52)
        bar.pack(fill="x"); bar.pack_propagate(False)
        sym_frame = tk.Frame(bar, bg=Theme.BG_SECONDARY); sym_frame.pack(side="left", padx=(12, 8), pady=8)
        self.sym_var = tk.StringVar(value=self._selected)
        self.sym_entry = tk.Entry(sym_frame, textvariable=self.sym_var, width=14,
            bg=Theme.PANEL, fg=Theme.TEXT, relief="flat", font=(Theme.FONT_FAMILY, 13, "bold"), justify="center")
        self.sym_entry.pack(side="left")
        self.sym_entry.bind("<Return>", lambda e: self._on_symbol_change())
        tk.Button(sym_frame, text="OK", command=self._on_symbol_change,
            bg=Theme.PRIMARY, fg="#fff", relief="flat", padx=8).pack(side="left", padx=(4, 0))
        self.price_label = tk.Label(bar, text="--", bg=Theme.BG_SECONDARY, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 16, "bold"))
        self.price_label.pack(side="left", padx=(16, 4))
        self.change_label = tk.Label(bar, text="(--)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 11))
        self.change_label.pack(side="left", padx=(0, 20))
        self.stat_high = self._stat_box(bar, "24h High", "--")
        self.stat_low = self._stat_box(bar, "24h Low", "--")
        self.stat_vol = self._stat_box(bar, "Volume", "--")
        self.stat_time = self._stat_box(bar, "Atualizado", "--")
        tf_frame = tk.Frame(bar, bg=Theme.BG_SECONDARY); tf_frame.pack(side="right", padx=12)
        self.tf_var = tk.StringVar(value="M5")
        for tf in TFORDER:
            tk.Radiobutton(tf_frame, text=tf, variable=self.tf_var, value=tf,
                bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, selectcolor=Theme.PANEL,
                activebackground=Theme.BG_SECONDARY, font=(Theme.FONT_FAMILY, 8),
                command=self._on_tf_change).pack(side="left")

    def _stat_box(self, parent, label, value):
        f = tk.Frame(parent, bg=Theme.BG_SECONDARY); f.pack(side="left", padx=(0, 16))
        tk.Label(f, text=label, bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(anchor="w")
        lbl = tk.Label(f, text=value, bg=Theme.BG_SECONDARY, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 10, "bold"))
        lbl.pack(anchor="w"); return lbl

    def _build_watchlist(self, main, col, row):
        wl = tk.Frame(main, bg=Theme.BG_SECONDARY, width=220)
        wl.grid(column=col, row=row, sticky="nsew", padx=(0, 4)); wl.pack_propagate(False)
        search = tk.Frame(wl, bg=Theme.BG_SECONDARY); search.pack(fill="x", padx=6, pady=6)
        tk.Label(search, text="WATCHLIST", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8, "bold")).pack(side="left")
        self.watch_search = tk.Entry(search, bg=Theme.PANEL, fg=Theme.TEXT, relief="flat", font=(Theme.FONT_FAMILY, 9), width=10)
        self.watch_search.pack(side="right")
        self.watch_search.bind("<KeyRelease>", lambda e: self._filter_watchlist())
        self.watch_canvas = tk.Canvas(wl, bg=Theme.BG_SECONDARY, highlightthickness=0)
        self.watch_canvas.pack(fill="both", expand=True, padx=0, pady=(0, 4))
        self.watch_inner = tk.Frame(self.watch_canvas, bg=Theme.BG_SECONDARY)
        self.watch_canvas.create_window((0, 0), window=self.watch_inner, anchor="nw")
        self.watch_inner.bind("<Configure>", lambda e: self.watch_canvas.configure(scrollregion=self.watch_canvas.bbox("all")))

    def _build_chart_area(self, main, col, row):
        cf = tk.Frame(main, bg=Theme.BG); cf.grid(column=col, row=row, sticky="nsew")
        toolbar = tk.Frame(cf, bg=Theme.BG, height=32); toolbar.pack(fill="x", pady=(0, 2)); toolbar.pack_propagate(False)
        self.kind_var = tk.StringVar(value="candles")
        for k, lbl in [("candles", "Candle"), ("line", "Linha"), ("bar", "OHLC")]:
            tk.Radiobutton(toolbar, text=lbl, variable=self.kind_var, value=k,
                bg=Theme.BG, fg=Theme.TEXT_MUTED, selectcolor=Theme.PANEL, activebackground=Theme.BG,
                font=(Theme.FONT_FAMILY, 8), command=self._refresh_chart).pack(side="left", padx=2)
        tk.Label(toolbar, text="  |  ", bg=Theme.BG, fg=Theme.TEXT_MUTED).pack(side="left")
        self.sma_var = tk.BooleanVar(value=False); self.ema_var = tk.BooleanVar(value=False)
        self.bb_var = tk.BooleanVar(value=False); self.vol_var = tk.BooleanVar(value=True)
        for txt, var in [("SMA", self.sma_var), ("EMA", self.ema_var), ("Bollinger", self.bb_var), ("Volume", self.vol_var)]:
            tk.Checkbutton(toolbar, text=txt, variable=var, bg=Theme.BG, fg=Theme.TEXT_MUTED,
                selectcolor=Theme.PANEL, activebackground=Theme.BG, command=self._refresh_chart,
                font=(Theme.FONT_FAMILY, 8)).pack(side="left", padx=2)
        self.chart = ChartCanvas(cf, bg=Theme.CARD, height=380)
        self.chart.pack(fill="both", expand=True)

    def _build_right_panel(self, main, col, row):
        rp = tk.Frame(main, bg=Theme.BG_SECONDARY, width=180)
        rp.grid(column=col, row=row, sticky="nsew", padx=(4, 0)); rp.pack_propagate(False)
        tk.Label(rp, text="INFO", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        self.info_name = tk.Label(rp, text="--", bg=Theme.BG_SECONDARY, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 12, "bold"))
        self.info_name.pack(anchor="w", padx=8)
        self.info_bid = self._info_row(rp, "Bid", "--")
        self.info_ask = self._info_row(rp, "Ask", "--")
        self.info_spread = self._info_row(rp, "Spread", "--")
        self.info_change = self._info_row(rp, "Variacao", "--")
        self.info_high = self._info_row(rp, "High", "--")
        self.info_low = self._info_row(rp, "Low", "--")
        tk.Frame(rp, bg=Theme.BORDER, height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(rp, text="MERCADO", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8, "bold")).pack(anchor="w", padx=8, pady=(0, 4))
        self.mkt_up = self._info_row(rp, "Altas", "--")
        self.mkt_down = self._info_row(rp, "Baixas", "--")
        self.mkt_total = self._info_row(rp, "Total", "--")

    def _info_row(self, parent, label, value):
        f = tk.Frame(parent, bg=Theme.BG_SECONDARY); f.pack(fill="x", padx=8, pady=1)
        tk.Label(f, text=label, bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(side="left")
        lbl = tk.Label(f, text=value, bg=Theme.BG_SECONDARY, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9, "bold"))
        lbl.pack(side="right"); return lbl

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=Theme.BG_SECONDARY, height=22); bar.pack(fill="x", side="bottom"); bar.pack_propagate(False)
        self.status_label = tk.Label(bar, text="Pronto", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8))
        self.status_label.pack(side="left", padx=8)

    def _load_symbols(self):
        cfg = get_config()
        syms = cfg.get("market", "symbols", default=[]) or []
        self._symbols = syms if syms else DEFAULT_SYMBOLS
        self._rebuild_watchlist(); self.refresh()

    def _rebuild_watchlist(self):
        for w in self.watch_inner.winfo_children(): w.destroy()
        self._watch_vars.clear()
        search = self.watch_search.get().strip().upper()
        for sym in self._symbols:
            if search and search not in sym.upper(): continue
            row = tk.Frame(self.watch_inner, bg=Theme.BG_SECONDARY, cursor="hand2")
            row.pack(fill="x", padx=4, pady=1)
            name_lbl = tk.Label(row, text=sym, bg=Theme.BG_SECONDARY, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 9), anchor="w")
            name_lbl.pack(side="left", padx=(4, 2))
            price_lbl = tk.Label(row, text="--", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_MONO, 9), anchor="e")
            price_lbl.pack(side="right", padx=(2, 4))
            chg_lbl = tk.Label(row, text="--", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED, font=(Theme.FONT_MONO, 8), anchor="e", width=7)
            chg_lbl.pack(side="right", padx=2)
            self._watch_vars[sym] = (price_lbl, chg_lbl)
            for w in (row, name_lbl, price_lbl, chg_lbl):
                w.bind("<Button-1>", lambda e, s=sym: self._select_symbol(s))

    def _filter_watchlist(self): self._rebuild_watchlist()

    def _select_symbol(self, sym):
        self._selected = sym; self.sym_var.set(sym); self._refresh_chart()
        self.on_status(f"Selecionado: {sym}")

    def _on_symbol_change(self):
        sym = self.sym_var.get().strip().upper()
        if sym and sym != self._selected:
            if sym not in self._symbols:
                self._symbols.append(sym); self._rebuild_watchlist()
            self._select_symbol(sym)

    def _on_tf_change(self): self._refresh_chart()

    def _refresh_chart(self):
        tf = self.tf_var.get(); minutes = TFMAP.get(tf, 5)
        limit = max(60, min(500, 240 // max(1, minutes // 5)))
        threading.Thread(target=self._load_chart, args=(self._selected, tf, minutes, limit), daemon=True).start()

