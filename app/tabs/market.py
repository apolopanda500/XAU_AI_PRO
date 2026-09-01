"""
Aba Mercado em tempo real com modo Spot e Futuros.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.components.tables import MarketTable
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class MarketTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._running = False
        self._thread: threading.Thread | None = None
        self._mode = "spot"
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Mercado", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.mode_label = tk.Label(header, text="Spot", bg=Theme.BG, fg=Theme.PRIMARY,
                                   font=(Theme.FONT_FAMILY, 12, "bold"))
        self.mode_label.pack(side="left", padx=16)
        self.btn_spot = SecondaryButton(header, text="Spot", command=lambda: self.set_mode("spot"), width=10)
        self.btn_spot.pack(side="left", padx=4)
        self.btn_futures = SecondaryButton(header, text="Futuros", command=lambda: self.set_mode("futures"), width=10)
        self.btn_futures.pack(side="left", padx=4)
        self.btn_all = SecondaryButton(header, text="Todos", command=lambda: self.set_mode("all"), width=10)
        self.btn_all.pack(side="left", padx=4)
        PrimaryButton(header, text="Atualizar", command=self.refresh, width=12).pack(side="right")

        self.card = Card(self.frame, title="Cotacoes em tempo real")
        self.card.pack(fill="both", expand=True, padx=24, pady=10)
        self.table = MarketTable(self.card.body)
        self.table.pack(fill="both", expand=True, padx=8, pady=8)

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.mode_label.configure(text=mode.upper())
        self.refresh()

    def refresh(self) -> None:
        """Dispara coleta em background; atualiza a tabela na GUI thread.

        Nunca toca widgets de thread secundaria e nunca bloqueia a main
        thread com chamadas de rede/MT5 (evita travamentos periodicos).
        """
        from app.utils.async_ui import run_bg
        run_bg(
            self.frame,
            work=self._collect_quotes,
            apply_result=self._apply_quotes,
        )

    def _collect_quotes(self) -> list[dict]:
        cfg = get_config()
        if self._mode == "spot":
            symbols = cfg.get("market", "symbols", default=[])
        elif self._mode == "futures":
            symbols = cfg.get("market", "futures", default=[])
        else:
            symbols = cfg.get("market", "symbols", default=[]) + cfg.get("market", "futures", default=[])
        quotes = self.market.get_many(symbols)
        rows: list[dict] = []
        for sym in symbols:
            q = quotes.get(sym)
            if q:
                rows.append({
                    "symbol": q.symbol, "price": q.price, "bid": q.bid,
                    "ask": q.ask, "change": q.change,
                    "change_pct": q.change_pct, "spread": q.spread,
                    "source": q.source, "time": q.time,
                })
        return rows

    def _apply_quotes(self, rows: list[dict]) -> None:
        out_rows = []
        tags = []
        for q in rows:
            out_rows.append([
                q["symbol"], q["price"], q["bid"], q["ask"],
                q["change"], f"{q['change_pct']:+.2f}%", q["spread"],
                q["source"], q["time"],
            ])
            tags.append("up" if q["change_pct"] >= 0 else "down")
        self.table.tree.set_rows(out_rows, tags)
        self.on_status(f"Mercado atualizado: {len(out_rows)} ativos")

    def start_auto_refresh(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._auto_loop, daemon=True)
        self._thread.start()

    def stop_auto_refresh(self) -> None:
        self._running = False

    def _auto_loop(self) -> None:
        cfg = get_config()
        interval = int(cfg.get("market", "refresh_seconds", default=5))
        while self._running:
            try:
                self.refresh()
                time.sleep(max(1, interval))
            except Exception:
                time.sleep(5)