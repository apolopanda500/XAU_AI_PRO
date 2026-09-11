# -*- coding: utf-8 -*-
"""Aba Mercado - pagina dedicada al mercado financiero (sin grafico).

El grafico esta EXCLUSIVAMENTE en la aba "Graficos" para mantener esta
pantalla liviana y rapida (solo cotizaciones: MT5 local + fallback HTTP).

Diseno de produccion:
  - Tkinter NO es thread-safe: los workers de red JAMAS tocan widgets ni
    llaman after(). Ponen resultados en self._queue y el hilo principal las
    vacia via _poll_results (after repetitivo iniciado UNA sola vez).
  - Un solo ciclo activo (guard _busy) y una sola fuente de cadencia
    (el _realtime_tick del core respeta el checkbox Auto).
  - Los fallos por simbolo se leen de market.errors() y se muestran
    concretos en la barra de estado (nada de "except: pass").
"""
from __future__ import annotations

import queue
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
from app.components.button import ProButton
from app.data.assets import get_default_symbols, search_assets, get_categories, get_assets_by_category

DEFAULT_SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
                   "NZDUSD", "USDCHF", "BTCUSD", "ETHUSD", "SPX500", "NAS100"]

# Mapeo para TradingView (simbolo del app -> feed corredor/exchange).
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
    """Pagina del mercado financiero: watchlist, detalle del activo y movers."""

    def __init__(self, parent, robot: MT5Robot, market: MarketData, on_status: Callable):
        super().__init__(parent, bg=Theme.BG)
        self.frame = self
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self._running = False
        self._busy = False
        self._quotes: dict = {}
        self._selected = "XAUUSD"
        self._watch_vars = {}
        self._symbols: list[str] = []
        # Cola thread-safe worker -> hilo principal (Tkinter).
        self._queue: queue.Queue = queue.Queue()
        self._polling = False
        self.auto_var = tk.BooleanVar(value=True)
        self._build()
        self._load_symbols()
        self._start_poller()

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
        bar.pack(fill="x")
        bar.pack_propagate(False)
        sym_frame = tk.Frame(bar, bg=Theme.BG_SECONDARY)
        sym_frame.pack(side="left", padx=(12, 8), pady=8)
        self.sym_var = tk.StringVar(value=self._selected)
        self.sym_entry = tk.Entry(sym_frame, textvariable=self.sym_var, width=14,
            bg=Theme.PANEL, fg=Theme.TEXT, relief="flat", insertbackground=Theme.TEXT,
            font=(Theme.FONT_FAMILY, 13, "bold"), justify="center")
        self.sym_entry.pack(side="left")
        self.sym_entry.bind("<Return>", lambda e: self._on_symbol_change())
        ProButton(sym_frame, "OK", self._on_symbol_change, padx=10, pady=4, radius=5).pack(side="left", padx=(4, 0))
        ProButton(sym_frame, "Buscar", self._show_asset_search, padx=8, pady=4, radius=5).pack(side="left", padx=(4, 0))
        self.price_label = tk.Label(bar, text="--", bg=Theme.BG_SECONDARY, fg=Theme.TEXT,
            font=(Theme.FONT_FAMILY, 16, "bold"))
        self.price_label.pack(side="left", padx=(16, 4))
        self.change_label = tk.Label(bar, text="(%)", bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 11))
        self.change_label.pack(side="left", padx=(0, 20))
        self.stat_high = self._stat_box(bar, "24h Alta", "--")
        self.stat_low = self._stat_box(bar, "24h Baixa", "--")
        self.stat_vol = self._stat_box(bar, "Volume", "--")
        self.stat_time = self._stat_box(bar, "Atualizado", "--")
        ProButton(bar, "Abrir TradingView", self._open_tradingview, bold=True, pady=5).pack(side="right", padx=12)

    def _show_asset_search(self):
        """Search dialog with 212+ assets."""
        from app.data.assets import search_assets, get_categories, get_assets_by_category
        popup = tk.Toplevel(self)
        popup.title("Buscar Ativos")
        popup.configure(bg=Theme.BG)
        popup.geometry("400x500")
        # Search
        sf = tk.Frame(popup, bg=Theme.BG_SECONDARY)
        sf.pack(fill="x", padx=10, pady=10)
        sv = tk.StringVar()
        se = tk.Entry(sf, textvariable=sv, bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 12), relief="flat")
        se.pack(fill="x", padx=5, pady=5)
        se.focus_set()
        # Category
        cf = tk.Frame(popup, bg=Theme.BG)
        cf.pack(fill="x", padx=10)
        cv = tk.StringVar(value="Todos")
        for c in ["Todos"] + get_categories():
            tk.Radiobutton(cf, text=c, variable=cv, value=c, bg=Theme.BG, fg=Theme.TEXT, selectcolor=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9)).pack(side="left", padx=3)
        # List
        lf = tk.Frame(popup, bg=Theme.CARD)
        lb = tk.Listbox(lf, bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 10), relief="flat", selectbackground=Theme.PRIMARY)
        sb = tk.Scrollbar(lf, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        lf.pack(fill="both", expand=True, padx=10, pady=10)
        assets = []
        for cat in get_categories():
            assets.extend(get_assets_by_category(cat))
        def fill(a):
            lb.delete(0, "end")
            for x in a[:200]:
                lb.insert("end", f"{x.icon} {x.symbol} - {x.name}")
        fill(assets)
        def on_search(*args):
            q, c = sv.get(), cv.get()
            if c == "Todos":
                r = search_assets(q) if q else assets
            else:
                r = [a for a in get_assets_by_category(c) if not q or q.upper() in a.symbol.upper()]
            fill(r)
        sv.trace_add("write", on_search)
        cv.trace_add("write", on_search)
        def on_pick(e):
            s = lb.curselection()
            if s:
                q, c = sv.get(), cv.get()
                r = search_assets(q) if c == "Todos" and q else get_assets_by_category(c) if c != "Todos" else assets
                if s[0] < len(r):
                    self.sym_var.set(r[s[0]].symbol)
                    self._on_symbol_change()
                    popup.destroy()
        lb.bind("<Double-1>", on_pick)

    def _stat_box(self, parent, label, value):
        f = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        f.pack(side="left", padx=(0, 16))
        tk.Label(f, text=label, bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8)).pack(anchor="w")
        lbl = tk.Label(f, text=value, bg=Theme.BG_SECONDARY, fg=Theme.TEXT,
            font=(Theme.FONT_MONO, 9, "bold"))
        lbl.pack(anchor="w")
        return lbl

    # ------------------------------------------------------------- constructores
    def _build_watchlist(self, main, row, col):
        card = tk.Frame(main, bg=Theme.CARD, highlightthickness=1,
                        highlightbackground=Theme.BORDER)
        card.grid(row=row, column=col, sticky="nsew", padx=(4, 4), pady=2)
        head = tk.Frame(card, bg=Theme.CARD)
        head.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(head, text="Vigilancia de Mercado", bg=Theme.CARD, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 11, "bold")).pack(side="left")
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
        self._detail: dict[str, tk.Label] = {}
        rows = [("Bid", "bid"), ("Ask", "ask"), ("Spread", "spread"),
                ("Variacion", "change"), ("% 24h", "change_pct"),
                ("24h High", "high"), ("24h Low", "low"),
                ("Volumen", "volume"), ("Hora", "time")]
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
        tk.Label(card, text="Top Movimientos (24h)", bg=Theme.CARD, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.movers_table = MarketTable(card, height=4)
        self.movers_table.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=Theme.BG_SECONDARY, height=26)
        bar.pack(fill="x", side="bottom")
        self.status_label = tk.Label(bar, text="Listo", bg=Theme.BG_SECONDARY,
                                     fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9))
        self.status_label.pack(side="left", padx=12)
        self.count_label = tk.Label(bar, text="", bg=Theme.BG_SECONDARY,
                                    fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9))
        self.count_label.pack(side="right", padx=12)

    # ----------------------------------------------------------------- datos
    def _load_symbols(self):
        try:
            cfg = get_config()
            # Acepta 'symbols' (estandar del config_manager) y 'watchlist' (legacy).
            syms = cfg.get("market", "symbols", default=None)
            if syms is None:
                syms = cfg.get("market", "watchlist", default=None)
            if isinstance(syms, str):
                syms = [s.strip().upper() for s in syms.split(",") if s.strip()]
            self._symbols = [str(s).upper() for s in (syms or DEFAULT_SYMBOLS)]
        except Exception as exc:  # noqa: BLE001 - config corrupta: defaults
            self._symbols = list(DEFAULT_SYMBOLS)
            self.status_label.configure(text="Config invalida: " + type(exc).__name__)
        if not self._symbols:
            self._symbols = list(DEFAULT_SYMBOLS)
        if self._selected not in self._symbols:
            self._symbols.insert(0, self._selected)
        placeholder = ["--"] * 8
        rows = [[s] + placeholder for s in self._symbols]
        self.watch_table.set_rows(rows)
        self.movers_table.set_rows([["--"] + placeholder] * 3)
        self.count_label.configure(text="%d activos" % len(self._symbols))
        self._select(self._selected)

    @staticmethod
    def _fmt(value, digits=2):
        if value in (None, ""):
            return "--"
        try:
            return ("%." + str(digits) + "f") % float(value)
        except (TypeError, ValueError):
            return str(value)

    # ------------------------------------------------- thread-safe poller
    def _start_poller(self) -> None:
        """Inicia el bucle que vacia self._queue en el hilo principal (una sola vez)."""
        if self._polling:
            return
        self._polling = True
        try:
            self.after(120, self._poll_results)
        except Exception:
            self._polling = False

    def _poll_results(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]
                if kind == "quotes":
                    self._apply_quotes(item[1], item[2])
                elif kind == "error":
                    self._show_fetch_error(item[1])
        except (queue.Empty, RuntimeError):
            pass
        except tk.TclError:
            # Ventana destruida durante la recoleccion: detener el poller.
            self._polling = False
            return
        try:
            if self._polling:
                self.after(120, self._poll_results)
        except tk.TclError:
            self._polling = False

    def _show_fetch_error(self, message: str) -> None:
        try:
            self.status_label.configure(text="Mercado: " + message)
        except tk.TclError:
            pass

    # ------------------------------------------------------------ actualizacion
    def refresh(self, force: bool = False) -> None:
        """Dispara una recoleccion en worker (nunca toca widgets desde el hilo).

        Respeta el checkbox Auto salvo en acciones explicitas (force=True:
        cambio de simbolo / click en fila / arranque inicial).
        """
        if self._busy:
            return
        if not self.auto_var.get() and not force:
            return
        self._busy = True
        try:
            self.status_label.configure(text="Buscando cotizaciones...")
        except tk.TclError:
            pass
        threading.Thread(target=self._collect_quotes, daemon=True).start()

    def refresh_now(self) -> None:
        self.refresh(force=True)

    def _collect_quotes(self) -> None:
        """Worker: SOLO lee de market_data y hace put() en la cola."""
        try:
            cached = self.market.get_quote(self._selected)
            provider = getattr(self.market, "provider", "auto") or "auto"
            if provider == "mt5" and not getattr(self.market, "_mt5_available", False):
                provider = "auto"
            # Simbolos con sufijo 'c' (XAUUSDc): el proveedor local suele
            # publicar la variante sin el sufijo; se resuelve y se rotula el
            # resultado con el simbolo original de la watchlist.
            resolved_symbols = []
            for sym in self._symbols:
                suf = sym[-1].upper() if sym else ""
                base = sym[:-1] if (suf == "C" and len(sym) > 4) else sym
                resolved_symbols.append((sym, base))
            all_q = self.market.get_many([base for _, base in resolved_symbols], provider)
            quotes: dict = {}
            for sym, base in resolved_symbols:
                q = all_q.get(sym) or all_q.get(base)
                if q is not None:
                    qd = q.to_dict()
                    qd["symbol"] = sym
                    quotes[sym] = qd
            payload = cached.to_dict() if cached is not None else None
            self._queue.put(("quotes", quotes, payload))
        except Exception as exc:  # noqa: BLE001 - error de red capturado
            self._queue.put(("error", type(exc).__name__ + ": " + str(exc)))
        finally:
            self._busy = False

    def _apply_quotes(self, quotes: dict, cached: dict | None) -> None:
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
        self.count_label.configure(text="%d/%d con precio" % (filled, len(self._symbols)))
        if cached:
            self._apply_detail(cached)
        errors = self.market.errors()
        if filled:
            self.status_label.configure(text="Mercado actualizado " + time.strftime("%H:%M:%S"))
        elif errors:
            # Muestra la causa mas comunes (sin abrir popups).
            sample = list(dict.fromkeys(errors.values()))[:2]
            self.status_label.configure(
                text="Sin cotizaciones: " + "; ".join(sample))
        else:
            self.status_label.configure(
                text="Sin cotizaciones: verificar internet/MT5 (%s)" % self._selected)
        try:
            store_quotes(list(quotes.values()))
        except Exception:  # noqa: BLE001 - persistencia opcional
            pass

    def _apply_movers(self, quotes: dict) -> None:
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
    def _apply_detail(self, q) -> None:
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
        self.detail_source.configure(text="Fuente: " + (data.get("source") or "--"))
        self.stat_high.configure(text=self._fmt(data.get("high"), digits))
        self.stat_low.configure(text=self._fmt(data.get("low"), digits))
        self.stat_vol.configure(text=self._fmt(data.get("volume"), 0))
        self.stat_time.configure(text=data.get("time") or "--")

    # ------------------------------------------------------------- interaccion
    def _on_row_click(self, _event):
        item = self.watch_table.tree.focus()
        if not item:
            return
        values = self.watch_table.tree.item(item, "values")
        if values and values[0] and values[0] != "--":
            self._select(str(values[0]))

    def _select(self, symbol: str) -> None:
        self._selected = symbol.upper()
        cached = self._quotes.get(self._selected)
        if cached:
            self._apply_detail(cached)
        else:
            self.detail_title.configure(text=self._selected)
        self.refresh(force=True)

    def _on_symbol_change(self):
        sym = (self.sym_var.get() or "").strip().upper()
        if not sym:
            return
        if sym not in self._symbols:
            self._symbols.insert(0, sym)
            self.watch_table.set_rows(self._symbol_rows())
            self.count_label.configure(text="%d activos" % len(self._symbols))
        self._select(sym)

    def _symbol_rows(self) -> list[list[str]]:
        return [[s] + ["--"] * 8 for s in self._symbols]

    def _open_tradingview(self):
        url = "https://www.tradingview.com/chart/?symbol=" + tv_symbol(self._selected)
        try:
            webbrowser.open(url)
            self.on_status("TradingView abierto para " + self._selected)
        except Exception as error:  # noqa: BLE001
            self.on_status("No se pudo abrir el navegador: " + str(error))

    # ------------------------------------------------------------- auto loop
    def _toggle_auto(self):
        if self.auto_var.get():
            self.refresh(force=True)
        else:
            self._running = False

    def stop_auto_refresh(self) -> None:
        try:
            self.auto_var.set(False)
        except tk.TclError:
            pass
        self._running = False
        self._polling = False