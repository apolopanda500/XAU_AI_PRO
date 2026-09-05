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
        from app.components.banner import TabBanner
        TabBanner(self.frame, "market")
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

        summary = Card(self.frame, title="Radar de Mercado")
        summary.pack(fill="x", padx=24, pady=(0, 10))
        self.market_stats = {}
        for label in ("Ativos", "Altas", "Baixas", "Fonte"):
            box = tk.Frame(summary.body, bg=Theme.CARD)
            box.pack(side="left", expand=True, fill="both", padx=8, pady=8)
            tk.Label(box, text=label, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(anchor="w")
            val = tk.Label(box, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                           font=(Theme.FONT_FAMILY, 18, "bold"))
            val.pack(anchor="w", pady=(4, 0))
            self.market_stats[label] = val

        # Importar novos ativos
        imp = tk.Frame(self.frame, bg=Theme.BG)
        imp.pack(fill="x", padx=24, pady=(0, 6))
        tk.Label(imp, text="Importar ativo:", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 9)).pack(side="left")
        self.import_entry = tk.Entry(imp, bg=Theme.PANEL, fg=Theme.TEXT,
                                     insertbackground=Theme.TEXT, relief="flat",
                                     highlightbackground=Theme.BORDER, highlightthickness=1,
                                     width=18, font=(Theme.FONT_FAMILY, 10))
        self.import_entry.pack(side="left", padx=6)
        self.import_entry.bind("<Return>", lambda e: self.import_symbol())
        SecondaryButton(imp, text="Adicionar", command=self.import_symbol, width=10).pack(side="left")
        SecondaryButton(imp, text="Buscar no MT5", command=self.search_mt5, width=12).pack(side="left", padx=6)
        self.import_status = tk.Label(imp, text="", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                                      font=(Theme.FONT_FAMILY, 9))
        self.import_status.pack(side="left", padx=8)

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
        up_count = 0
        down_count = 0
        sources = set()
        for q in rows:
            out_rows.append([
                q["symbol"], q["price"], q["bid"], q["ask"],
                q["change"], f"{q['change_pct']:+.2f}%", q["spread"],
                q["source"], q["time"],
            ])
            is_up = q["change_pct"] >= 0
            tags.append("up" if is_up else "down")
            up_count += 1 if is_up else 0
            down_count += 0 if is_up else 1
            sources.add(str(q.get("source") or "--"))
        self.table.tree.set_rows(out_rows, tags)
        self.market_stats["Ativos"].configure(text=str(len(out_rows)), fg=Theme.TEXT)
        self.market_stats["Altas"].configure(text=str(up_count), fg=Theme.SUCCESS)
        self.market_stats["Baixas"].configure(text=str(down_count), fg=Theme.DANGER)
        self.market_stats["Fonte"].configure(text=", ".join(sorted(sources)[:2]) if sources else "--",
                                              fg=Theme.PRIMARY)
        self.on_status(f"Mercado atualizado: {len(out_rows)} ativos")

    def start_auto_refresh(self, interval_sec: int = 60) -> None:
        """Auto-refresh a cada 1 min (sem travar a GUI)."""
        self._running = True
        self._thread = threading.Thread(
            target=self._auto_loop,
            args=(interval_sec,),
            daemon=True,
        )
        self._thread.start()

    def stop_auto_refresh(self) -> None:
        self._running = False

    def _auto_loop(self, interval_sec: int = 60) -> None:
        interval = interval_sec
        while self._running:
            try:
                self.refresh()
                time.sleep(max(1, interval))
            except Exception:
                time.sleep(5)

    def import_symbol(self) -> None:
        """Adiciona um novo ativo aos simbolos monitorados (spot) e atualiza."""
        sym = self.import_entry.get().strip().upper()
        if not sym:
            self.import_status.configure(text="Informe o simbolo", fg=Theme.WARNING)
            return
        threading.Thread(target=self._do_import, args=(sym,), daemon=True).start()

    def _do_import(self, sym: str) -> None:
        cfg = get_config()
        symbols = list(cfg.get("market", "symbols", default=[]) or [])
        if sym in symbols:
            msg, fg = f"{sym} ja esta na lista", Theme.WARNING
        else:
            symbols.append(sym)
            try:
                cfg.set("market", "symbols", value=symbols)
                msg, fg = f"{sym} adicionado", Theme.SUCCESS
            except Exception:
                msg, fg = "erro ao salvar config", Theme.DANGER
        self.frame.after(0, lambda: self._import_done(msg, fg, sym))

    def _import_done(self, msg: str, fg: str, sym: str) -> None:
        self.import_status.configure(text=msg, fg=fg)
        if "adicionado" in msg:
            self.import_entry.delete(0, "end")
            self.refresh()

    def search_mt5(self) -> None:
        """Pesquisa simbolos no terminal MT5 (por fragmento)."""
        frag = self.import_entry.get().strip().upper()
        threading.Thread(target=self._search_mt5, args=(frag,), daemon=True).start()

    def _search_mt5(self, frag: str) -> None:
        try:
            import MetaTrader5 as mt5  # noqa: PLC0415
            from app.mt5_robot import get_robot
            robot = get_robot()
            if not (robot and robot.account_info()):
                self.frame.after(0, lambda: self.import_status.configure(
                    text="MT5 offline", fg=Theme.WARNING))
                return
            syms = mt5.symbols_get()
            out = [s.name for s in (syms or []) if not frag or frag in s.name.upper()]
            mt5.shutdown()
            found = out[:20]
            if not found:
                self.frame.after(0, lambda: self.import_status.configure(
                    text="Nada encontrado", fg=Theme.WARNING))
            else:
                txt = f"Encontrados: {', '.join(found[:6])}{'...' if len(found) > 6 else ''}"
                self.frame.after(0, lambda: self.import_status.configure(text=txt, fg=Theme.TEXT))
        except Exception:
            self.frame.after(0, lambda: self.import_status.configure(
                text="Erro na busca MT5", fg=Theme.DANGER))
