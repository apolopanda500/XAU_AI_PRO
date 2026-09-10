# -*- coding: utf-8 -*-
"""Aba Mercado - pagina dedicada ao mercado financeiro (sem grafico).

O grafico ficou EXCLUSIVAMENTE na aba "Graficos" para manter esta tela leve
e rapida (so cotacoes: MT5 local + fallback HTTP). Para analise tecnica
profissional externa, ha integracao direta com o TradingView no navegador.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
import webbrowser
from typing import Callable

from app.components.tables import MarketTable
from app.config_manager import get_config
from app.market_data import MarketData
from app.market_store import store_quotes
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme

DEFAULT_SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
                   "NZDUSD", "USDCHF", "BTCUSD", "ETHUSD", "SPX500", "NAS100"]

# Mapeamento para o TradingView (simbolo do app -> feed corretor/exchange).
TV_SYMBOL_MAP = {
    "XAUUSD": "OANDA:XAUUSD", "XAUUSDc": "OANDA:XAUUSD", "GOLD": "OANDA:XAUUSD",
    "BTCUSD": "BINANCE:BTCUSDT", "BTCUSDc": "BINANCE:BTCUSDT",
    "ETHUSD": "BINANCE:ETHUSDT", "ETHUSDc": "BINANCE:ETHUSDT",
    "EURUSD": "OANDA:EURUSD", "GBPUSD": "OANDA:GBPUSD", "USDJPY": "OANDA:USDJPY",
    "AUDUSD": "OANDA:AUDUSD", "USDCAD": "OANDA:USDCAD", "NZDUSD": "OANDA:NZDUSD",
    "USDCHF": "OANDA:USDCHF", "US30": "TVC:DJI", "SPX500": "TVC:SPX",
    "NAS100": "TVC:NDX", "GER40": "XETR:DAX", "UK100": "TVC:UKX",
}


def tv_symbol(sym: str) -> str:
    return TV_SYMBOL_MAP.get((sym or "").upper(), "OANDA:" + sym.upper())


class TradingViewMarket(tk.Frame):
    """Pagina do mercado financeiro: watchlist, detalhe do ativo e movers."""

    def __init__(self, parent, robot: MT5Robot, market: MarketData, on_status: Callable):
        super().__init__(parent, bg=Theme.BG)
        self.frame = self
        self.robot = robot; self.market = market; self.on_status = on_status
        self._running = False; self._quotes = {}; self._selected = "XAUUSD"
        self._watch_vars = {}; self._symbols = []
        self._build(); self._load_symbols()

    # ----------------------------------------------------------------- layout
    def _build(self):
        self._build_topbar()
        main = tk.Frame(self, bg=Theme.BG)
        main.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        self._build_watchlist(main, 0, 0)
        self._build_detail(main, 0, 1)
        self._build_movers(main, 1, 0)
        self._build_statusbar()

    def _build_topbar(self):
        bar = tk.Frame(self, bg=Theme.BG_SECONDARY, height=52)
        bar.pack(fill="x"); bar.pack_propagate(False)
        sym_frame = tk.Frame(bar, bg=Theme.BG_SECONDARY)
        sym_frame.pack(side="left", padx=(12, 8), pady=8)
        self.sym_var = tk.StringVar(value=self._selected)
        self.sym_entry = tk.Entry(sym_frame, textvariable=self.sym_var, width=14,
            bg=Theme.PANEL, fg=Theme.TEXT, relief="flat", insertbackground=Theme.TEXT,
            font=(Theme.FONT_FAMILY, 13, "bold"), justify="center")
        self.sym_entry.pack(side="left")
        self.sym_entry.bind("<Return>", lambda e: self._on_symbol_change())
        tk.Button(sym_frame, text="OK", command=self._on_symbol_change,
            bg=Theme.PRIMARY, fg="#fff", relief="flat", padx=8).pack(side="left", padx=(4, 0))
        self.price_label = tk.Label(bar, text="--", bg=Theme.BG_SECONDARY, fg=Theme.TEXT,
            font=(Theme.FONT_FAMILY, 16, "bold"))
        self.price_label.pack(side="left", padx=(16, 4))
        self.change_label = tk.Label(bar, text="(%)", bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 11))
        self.change_label.pack(side="left", padx=(0, 20))
        self.stat_high = self._stat_box(bar, "24h High", "--")
        self.stat_low = self._stat_box(bar, "24h Low", "--")
        self.stat_vol = self._stat_box(bar, "Volume", "--")
        self.stat_time = self._stat_box(bar, "Atualizado", "--")
        tk.Button(bar, text="Abrir TradingView", command=self._open_tradingview,
            bg=Theme.PRIMARY, fg="#ffffff", relief="flat", padx=12, pady=4,
            font=(Theme.FONT_FAMILY, 9, "bold"), cursor="hand2").pack(side="right", padx=12)

    def _stat_box(self, parent, label, value):
        f = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        f.pack(side="left", padx=(0, 16))
        tk.Label(f, text=label, bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8)).pack(anchor="w")
        lbl = tk.Label(f, text=value, bg=Theme.BG_SECONDARY, fg=Theme.TEXT,
            font=(Theme.FONT_MONO, 9, "bold"))
        lbl.pack(anchor="w")
        return lbl

    # ------------------------------------------------------------- construtores
    def _build_watchlist(self, main, row, col):
        card = tk.Frame(main, bg=Theme.CARD, highlightthickness=1,
                        highlightbackground=Theme.BORDER)
        card.grid(row=row, column=col, sticky="nsew", padx=(4, 4), pady=2)
        head = tk.Frame(card, bg=Theme.CARD)
        head.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(head, text="Vigilância de Mercado", bg=Theme.CARD, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 11, "bold")).pack(side="left")
        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(head, text="Auto", variable=self.auto_var, command=self._toggle_auto,
                       bg=Theme.CARD, fg=Theme.TEXT_MUTED, activebackground=Theme.CARD,
                       activeforeground=Theme.TEXT, selectcolor=Theme.PANEL,
                       font=(Theme.FONT_FAMILY, 9)).pack(side="right")
        self.watch_table = MarketTable(card, height=14)
        self.watch_table.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        self.watch_table.tree.bind("<ButtonRelease-1>", self._on_row_click)

    def _build_detail(self, main, row, col):
        card = tk.Frame(main, bg=Theme.CARD, highlightthickness=1,
                        highlightbackground=Theme.BORDER)
        card.grid(row=row, column=col, sticky="nsew", padx=(4, 4), pady=2)
        card.configure(width=320)
        card.pack_propagate(False)
        head = tk.Frame(card, bg=Theme.CARD)
        head.pack(fill="x", padx=12, pady=(10, 4))
        self.detail_title = tk.Label(head, text=self._selected, bg=Theme.CARD, fg=Theme.PRIMARY,
                                     font=(Theme.FONT_FAMILY, 14, "bold"))
        self.detail_title.pack(side="left")
        self.detail_source = tk.Label(head, text="", bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                                      font=(Theme.FONT_FAMILY, 9))
        self.detail_source.pack(side="right")
        body = tk.Frame(card, bg=Theme.CARD)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self._detail = {}
        rows = [("Bid", "bid"), ("Ask", "ask"), ("Spread", "spread"),
                ("Variação", "change"), ("% 24h", "change_pct"),
                ("24h High", "high"), ("24h Low", "low"),
                ("Volume", "volume"), ("Hora", "time")]
        for label, key in rows:
            line = tk.Frame(body, bg=Theme.CARD)
            line.pack(fill="x", pady=2)
            tk.Label(line, text=label, bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                     font=(Theme.FONT_FAMILY, 9)).pack(side="left")
            lbl = tk.Label(line, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                           font=(Theme.FONT_MONO, 10, "bold"))
            lbl.pack(side="right")
            self._detail[key] = lbl

    def _build_movers(self, main, row, col):
        card = tk.Frame(main, bg=Theme.CARD, highlightthickness=1,
                        highlightbackground=Theme.BORDER)
        card.grid(row=row, column=col, columnspan=2, sticky="nsew", padx=(4, 4), pady=(2, 4))
        card.configure(height=190)
        card.pack_propagate(False)
        tk.Label(card, text="Top Movimentações (24h)", bg=Theme.CARD, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.movers_table = MarketTable(card, height=4)
        self.movers_table.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=Theme.BG_SECONDARY, height=26)
        bar.pack(fill="x", side="bottom")
        self.status_label = tk.Label(bar, text="Pronto", bg=Theme.BG_SECONDARY,
                                     fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9))
        self.status_label.pack(side="left", padx=12)
        self.count_label = tk.Label(bar, text="", bg=Theme.BG_SECONDARY,
                                    fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9))
        self.count_label.pack(side="right", padx=12)

    # ----------------------------------------------------------------- dados
    def _load_symbols(self):
        try:
            cfg = get_config()
            # Aceita 'symbols' (padrao do config_manager) e 'watchlist' (legado).
            syms = cfg.get("market", "symbols", default=None)
            if syms is None:
                syms = cfg.get("market", "watchlist", default=None)
            syms = syms or DEFAULT_SYMBOLS
            if isinstance(syms, str):
                syms = [s.strip().upper() for s in syms.split(",") if s.strip()]
            self._symbols = [str(s).upper() for s in syms] or list(DEFAULT_SYMBOLS)
        except Exception:
            self._symbols = list(DEFAULT_SYMBOLS)
        if self._selected not in self._symbols:
            self._symbols.insert(0, self._selected)
        placeholder = ["--"] * 9
        rows = [[s] + placeholder[1:] for s in self._symbols]
        self.watch_table.set_rows(rows)
        self.movers_table.set_rows([["--"] + placeholder[1:]] * 3)
        self.count_label.configure(text="%d ativos" % len(self._symbols))
        self._select(self._selected)

    def _fmt(self, value, digits=2):
        if value in (None, "", 0):
            return "--"
        try:
            return ("%." + str(digits) + "f") % float(value)
        except Exception:
            return str(value)

    # ------------------------------------------------------------ atualizacao
    def refresh(self):
        """Dispara coleta de cotacoes em thread (nao trava a GUI)."""
        if getattr(self, "_busy", False):
            return
        self._busy = True
        self._running = True
        self.status_label.configure(text="Buscando cotações...")
        threading.Thread(target=self._collect_quotes, daemon=True).start()

    def refresh_now(self):
        self.refresh()

    def _collect_quotes(self):
        quotes = {}
        try:
            # Coleta o destaque primeiro (MT5 -> exchange -> HTTP) e depois
            # a lista completa. O modo 'mt5' puro quebrava tudo quando o
            # MT5 estava fora: usa 'auto' como fallback para HTTP/exchange.
            cached = self.market.get_quote(self._selected)
            provider = getattr(self.market, "provider", "auto") or "auto"
            if provider == "mt5" and not getattr(self.market, "_mt5_available", False):
                provider = "auto"
            # Símbolos terminados em 'c' (ex.: XAUUSDc) são aliases: tenta o
            # símbolo sem o sufixo final 'c', evitando linhas vazias quando o
            # MT5 não resolve a variante 'c' explicitamente. O resultado volta
            # rotulado com o símbolo original da watchlist (fallback no base).
            resolved_symbols = []
            for sym in self._symbols:
                suf = sym[-1].upper() if sym else ""
                base = sym[:-1] if (suf == "C" and len(sym) > 4) else sym
                resolved_symbols.append((sym, base))
            all_q = self.market.get_many([base for _, base in resolved_symbols], provider)
            for sym, base in resolved_symbols:
                q = all_q.get(sym)
                if q is None:
                    q = all_q.get(base)
                if q is not None:
                    qd = q.to_dict()
                    qd["symbol"] = sym
                    quotes[sym] = qd
            payload = (cached.to_dict() if cached is not None else None)
        except Exception as error:
            def _err(err=error):
                self.status_label.configure(
                    text="Mercado: " + type(err).__name__ + ": " + str(err))
            try:
                self.after(0, _err)
            except Exception:
                pass
            self._busy = False
            return
        try:
            self.after(0, lambda: self._apply_quotes(quotes, payload))
        except Exception:
            self._busy = False

    def _apply_quotes(self, quotes, cached):
        self._quotes = quotes
        rows, tags = [], []
        for sym in self._symbols:
            q = quotes.get(sym)
            if q:
                digits = int(q.get("digits") or 2)
                chg = q.get("change_pct") or 0.0
                rows.append([sym, self._fmt(q.get("price"), digits),
                             self._fmt(q.get("bid"), digits), self._fmt(q.get("ask"), digits),
                             self._fmt(q.get("change"), digits),
                             ("+%.2f%%" % chg) if chg >= 0 else ("%.2f%%" % chg),
                             self._fmt(q.get("spread"), 1), q.get("source", ""),
                             q.get("time", "")])
                tags.append("up" if chg >= 0 else "down")
            else:
                rows.append([sym] + ["--"] * 8)
                tags.append("even")
        self.watch_table.set_rows(rows, tags)
        self._apply_movers(quotes)
        filled = sum(1 for r in rows if r[1] != "--")
        self.count_label.configure(text="%d/%d com preço" % (filled, len(self._symbols)))
        if cached:
            self._apply_detail(cached)
        if filled:
            self.status_label.configure(text="Mercado actualizado " + time.strftime("%H:%M:%S"))
        else:
            self.status_label.configure(
                text="Sem cotações: verifique internet/MT5 (símbolo %s)" % self._selected)
        try:
            store_quotes(list(quotes.values()))
        except Exception:
            pass
        self._busy = False
        self._start_auto_if_needed()

    def _apply_movers(self, quotes):
        ranked = sorted(
            (q for q in quotes.values() if q.get("change_pct")),
            key=lambda q: abs(q.get("change_pct") or 0.0), reverse=True)[:3]
        if not ranked:
            self.movers_table.set_rows([["--"] + ["--"] * 8] * 3)
            return
        mrows, mtags = [], []
        for q in ranked:
            digits = int(q.get("digits") or 2)
            chg = q.get("change_pct") or 0.0
            mrows.append([q.get("symbol"), self._fmt(q.get("price"), digits),
                          "--", "--", self._fmt(q.get("change"), digits),
                          ("+%.2f%%" % chg) if chg >= 0 else ("%.2f%%" % chg),
                          "--", q.get("source", ""), q.get("time", "")])
            mtags.append("up" if chg >= 0 else "down")
        self.movers_table.set_rows(mrows, mtags)

# === PARTE3B ===
    def _apply_detail(self, q):
        data = q if isinstance(q, dict) else q.to_dict()
        digits = int(data.get("digits") or 2)
        self.sym_var.set(data.get("symbol", self._selected))
        self.price_label.configure(text=self._fmt(data.get("price"), digits))
        chg = data.get("change_pct") or 0.0
        self.change_label.configure(
            text=(("+%.2f%%" % chg) if chg >= 0 else ("%.2f%%" % chg)) +
                 ("  (" + self._fmt(data.get("change"), digits) + ")" if data.get("change") else ""),
            fg=Theme.BID if chg >= 0 else Theme.ASK)
        for key, lbl in self._detail.items():
            if key in ("change", "change_pct"):
                continue
            if key == "time":
                lbl.configure(text=data.get("time") or "--", fg=Theme.TEXT_MUTED)
            else:
                d = 1 if key == "spread" else digits
                lbl.configure(text=self._fmt(data.get(key), d))
        self.detail_title.configure(text=data.get("symbol", self._selected))
        self.detail_source.configure(text="Fonte: " + (data.get("source") or "--"))
        self.stat_high.configure(text=self._fmt(data.get("high"), digits))
        self.stat_low.configure(text=self._fmt(data.get("low"), digits))
        self.stat_vol.configure(text=self._fmt(data.get("volume"), 0))
        self.stat_time.configure(text=data.get("time") or "--")

    # ------------------------------------------------------------- interacao
    def _on_row_click(self, _event):
        item = self.watch_table.tree.focus()
        if not item:
            return
        values = self.watch_table.tree.item(item, "values")
        if values and values[0] and values[0] != "--":
            self._select(str(values[0]))

    def _select(self, symbol):
        self._selected = symbol.upper()
        cached = self._quotes.get(self._selected)
        if cached:
            self._apply_detail(cached)
        else:
            self.detail_title.configure(text=self._selected)
        self.refresh()

    def _on_symbol_change(self):
        sym = (self.sym_var.get() or "").strip().upper()
        if not sym:
            return
        if sym not in self._symbols:
            self._symbols.insert(0, sym)
            self.watch_table.set_rows(self._symbol_rows())
            self.count_label.configure(text="%d ativos" % len(self._symbols))
        self._select(sym)

    def _symbol_rows(self):
        return [[s] + ["--"] * 8 for s in self._symbols]

    def _open_tradingview(self):
        url = "https://www.tradingview.com/chart/?symbol=" + tv_symbol(self._selected)
        try:
            webbrowser.open(url)
            self.on_status("TradingView aberto para " + self._selected)
        except Exception as error:
            self.on_status("Nao foi possivel abrir o navegador: " + str(error))

    # ------------------------------------------------------------- auto loop
    def _toggle_auto(self):
        if self.auto_var.get():
            self._start_auto_if_needed(force=True)
        else:
            self._running = False

    def _start_auto_if_needed(self, force=False):
        if not (self.auto_var.get() or force):
            return
        try:
            self.after(3000, self._auto_loop)
        except Exception:
            pass

    def _auto_loop(self):
        try:
            if not self.auto_var.get():
                return
            if not getattr(self, "_busy", False):
                self.refresh()
        except Exception:
            pass

    def stop_auto_refresh(self):
        try:
            self.auto_var.set(False)
        except Exception:
            pass
        self._running = False
