"""
Aba Carteira: saldos, posicoes abertas e historico de trades.
"""
from __future__ import annotations

import time
import tkinter as tk
from typing import Callable

from app.components.cards import Card, KPI, PrimaryButton, SecondaryButton, DangerButton
from app.components.tables import HistoryTable, PositionTable
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class PositionsTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Carteira", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        PrimaryButton(header, text="Atualizar", command=self.refresh, width=12).pack(side="right")
        DangerButton(header, text="Fechar tudo", command=self.close_all, width=12).pack(side="right", padx=8)

        # Resumo
        summary = Card(self.frame, title="Resumo da Conta")
        summary.pack(fill="x", padx=24, pady=10)
        self.kpi_balance = KPI(summary.body, "Saldo", "--", Theme.TEXT)
        self.kpi_equity = KPI(summary.body, "Equity", "--", Theme.TEXT)
        self.kpi_margin_level = KPI(summary.body, "Nivel Margem", "--", Theme.PRIMARY)
        self.kpi_floating = KPI(summary.body, "Lucro Flutuante", "--", Theme.SUCCESS)
        for kpi in [self.kpi_balance, self.kpi_equity, self.kpi_margin_level, self.kpi_floating]:
            kpi.pack(side="left", expand=True, fill="both", padx=8, pady=8)

        # Posicoes abertas
        pos_card = Card(self.frame, title="Posicoes Abertas")
        pos_card.pack(fill="both", expand=True, padx=24, pady=(10, 5))
        self.pos_table = PositionTable(pos_card.body)
        self.pos_table.pack(fill="both", expand=True, padx=8, pady=8)
        SecondaryButton(pos_card.body, text="Fechar posicao selecionada",
                        command=self.close_selected, width=24).pack(anchor="e", padx=8, pady=8)

        # Historico
        hist_card = Card(self.frame, title="Historico de Trades (7 dias)")
        hist_card.pack(fill="both", expand=True, padx=24, pady=(5, 10))
        self.hist_table = HistoryTable(hist_card.body)
        self.hist_table.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh(self) -> None:
        """Atualiza a carteira SEM travar a GUI (coleta em background)."""
        from app.utils.async_ui import run_bg
        run_bg(
            self.frame,
            work=self._collect,
            apply_result=self._apply,
        )

    # ------------------------------------------------------------------
    # Auto-refresh (a cada 1 min) - posicoes sao criticas p/ possivel fechamento
    # ------------------------------------------------------------------
    def start_auto_refresh(self, interval_sec: int = 60) -> None:
        """Inicia loop em thread daemon que atualiza a carteira a cada 1 min."""
        self._auto_running = True
        import threading

        def loop() -> None:
            while self._auto_running:
                try:
                    interval = interval_sec
                    try:
                        interval = max(30, int(self.interval_entry.get()))
                    except (AttributeError, ValueError):
                        pass
                    time.sleep(interval)
                    if self._auto_running:
                        self.refresh()
                except Exception:
                    time.sleep(10)

        threading.Thread(target=loop, daemon=True).start()

    def stop_auto_refresh(self) -> None:
        self._auto_running = False

    def _collect(self) -> dict:
        out = {"info": None, "positions": [], "deals": []}
        try:
            out["info"] = self.robot.account_info()
        except Exception:
            out["info"] = None
        try:
            out["positions"] = self.robot.get_positions()
        except Exception:
            out["positions"] = []
        try:
            out["deals"] = self.robot.get_history(days=7)
        except Exception:
            out["deals"] = []
        return out

    def _apply(self, data: dict) -> None:
        info = data.get("info")
        if info:
            self.kpi_balance.set(f"{info['balance']:,.2f}")
            self.kpi_equity.set(f"{info['equity']:,.2f}")
            self.kpi_margin_level.set(f"{info['margin_level']:.1f}%",
                                      Theme.WARNING if info['margin_level'] < 200 else Theme.PRIMARY)
            self.kpi_floating.set(f"{info['profit']:,.2f}",
                                  Theme.SUCCESS if info['profit'] >= 0 else Theme.DANGER)
        else:
            self.kpi_balance.set("--")
            self.kpi_equity.set("--")
            self.kpi_margin_level.set("--")
            self.kpi_floating.set("--")

        positions = data.get("positions") or []
        rows = []
        tags = []
        for p in positions:
            rows.append([p.ticket, p.symbol, p.type, p.volume, p.open_price,
                         p.current_price, p.sl, p.tp, p.profit])
            tags.append("profit" if p.profit >= 0 else "loss")
        self.pos_table.tree.set_rows(rows, tags)

        deals = data.get("deals") or []
        rows2 = []
        tags2 = []
        for d in deals:
            rows2.append([d.time, d.ticket, d.symbol, d.type, d.volume, d.price, d.profit])
            tags2.append("profit" if d.profit >= 0 else "loss")
        self.hist_table.tree.set_rows(rows2, tags2)
        self.on_status(f"Carteira atualizada: {len(positions)} posicoes")

    def close_selected(self) -> None:
        sel = self.pos_table.tree.tree.selection()
        if not sel:
            self.on_status("Nenhuma posicao selecionada")
            return
        values = self.pos_table.tree.tree.item(sel[0], "values")
        ticket = int(values[0])
        res = self.robot.close_position(ticket)
        if res.get("ok"):
            self.on_status(f"Posicao #{ticket} fechada")
        else:
            self.on_status(f"Erro ao fechar #{ticket}: {res.get('error')}")
        self.refresh()

    def close_all(self) -> None:
        res = self.robot.close_all_positions()
        self.on_status(f"Fechadas {res.get('closed', 0)} posicoes")
        self.refresh()
