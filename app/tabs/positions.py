"""
Aba Carteira: saldos, posicoes abertas e historico de trades.
"""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox
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
        from app.components.banner import TabBanner
        TabBanner(self.frame, "positions")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Carteira", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.last_update = tk.Label(header, text="Aguardando primeira leitura", bg=Theme.BG,
                                    fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 9))
        self.last_update.pack(side="right", padx=(8, 0))
        PrimaryButton(header, text="Atualizar", command=self.refresh, width=12).pack(side="right")
        DangerButton(header, text="Fechar tudo", command=self.close_all, width=12).pack(side="right", padx=8)

        # Resumo
        summary = Card(self.frame, title="Resumo da Conta")
        summary.pack(fill="x", padx=24, pady=10)
        self.account_identity = tk.Label(summary.body, text="Conta MT5: desconectada", bg=Theme.CARD,
                                         fg=Theme.WARNING, font=(Theme.FONT_FAMILY, 9, "bold"))
        self.account_identity.pack(fill="x", padx=8, pady=(4, 0))
        self.kpi_balance = KPI(summary.body, "Saldo", "MT5 offline", Theme.TEXT)
        self.kpi_equity = KPI(summary.body, "Equity", "MT5 offline", Theme.TEXT)
        self.kpi_margin_level = KPI(summary.body, "Nivel Margem", "MT5 offline", Theme.PRIMARY)
        self.kpi_floating = KPI(summary.body, "Lucro Flutuante", "MT5 offline", Theme.SUCCESS)
        self.kpi_open = KPI(summary.body, "Posicoes", "MT5 offline", Theme.ACCENT)
        self.kpi_day = KPI(summary.body, "Resultado 7d", "Sem historico", Theme.TEXT)
        for kpi in [self.kpi_balance, self.kpi_equity, self.kpi_margin_level,
                    self.kpi_floating, self.kpi_open, self.kpi_day]:
            kpi.pack(side="left", expand=True, fill="both", padx=8, pady=8)

        # Posicoes abertas
        pos_card = Card(self.frame, title="Posicoes Abertas")
        pos_card.pack(fill="both", expand=True, padx=24, pady=(10, 5))
        self.pos_table = PositionTable(pos_card.body)
        self.pos_table.pack(fill="both", expand=True, padx=8, pady=8)
        self.pos_status = tk.Label(pos_card.body, text="Aguardando dados do MT5", bg=Theme.CARD,
                                   fg=Theme.TEXT_SECONDARY)
        self.pos_status.pack(anchor="w", padx=8)
        SecondaryButton(pos_card.body, text="Fechar posicao selecionada",
                        command=self.close_selected, width=24).pack(anchor="e", padx=8, pady=8)

        # Historico
        hist_card = Card(self.frame, title="Historico de Trades (7 dias)")
        hist_card.pack(fill="both", expand=True, padx=24, pady=(5, 10))
        self.hist_table = HistoryTable(hist_card.body)
        self.hist_table.pack(fill="both", expand=True, padx=8, pady=8)
        self.hist_status = tk.Label(hist_card.body, text="Aguardando historico do MT5", bg=Theme.CARD,
                                    fg=Theme.TEXT_SECONDARY)
        self.hist_status.pack(anchor="w", padx=8, pady=(0, 8))

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
            currency = str(info.get("currency") or "").strip()
            suffix = f" {currency}" if currency else ""
            margin_level = float(info.get("margin_level") or 0)
            profit = float(info.get("profit") or 0)
            self.kpi_balance.set(f"{float(info.get('balance') or 0):,.2f}{suffix}")
            self.kpi_equity.set(f"{float(info.get('equity') or 0):,.2f}{suffix}")
            self.kpi_margin_level.set(f"{margin_level:.1f}%",
                                      Theme.WARNING if margin_level < 200 else Theme.PRIMARY)
            self.kpi_floating.set(f"{profit:,.2f}",
                                  Theme.SUCCESS if profit >= 0 else Theme.DANGER)
            self.account_identity.configure(
                text=f"Conta {info.get('login') or 'nao informada'} | {info.get('name') or 'titular nao informado'} | {info.get('server') or 'servidor nao informado'}",
                fg=Theme.SUCCESS,
            )
        else:
            self.kpi_balance.set("MT5 offline")
            self.kpi_equity.set("MT5 offline")
            self.kpi_margin_level.set("MT5 offline")
            self.kpi_floating.set("MT5 offline")
            self.kpi_open.set("MT5 offline")
            self.kpi_day.set("Sem historico")
            self.account_identity.configure(text="Conta MT5: desconectada", fg=Theme.WARNING)

        positions = data.get("positions") or []
        self.kpi_open.set(str(len(positions)), Theme.ACCENT if positions else Theme.TEXT_SECONDARY)
        rows = []
        tags = []
        for p in positions:
            rows.append([p.ticket, p.symbol, p.type, p.volume, p.open_price,
                         p.current_price, p.sl, p.tp, p.profit])
            tags.append("profit" if p.profit >= 0 else "loss")
        self.pos_table.tree.set_rows(rows, tags)
        self.pos_status.configure(
            text=f"{len(positions)} posicao(oes) aberta(s)" if info else "Posicoes indisponiveis: MT5 desconectado",
            fg=Theme.SUCCESS if positions else Theme.TEXT_SECONDARY,
        )

        deals = data.get("deals") or []
        pnl_7d = sum(getattr(d, "profit", 0.0) for d in deals)
        self.kpi_day.set(f"{pnl_7d:,.2f}", Theme.SUCCESS if pnl_7d >= 0 else Theme.DANGER)
        rows2 = []
        tags2 = []
        for d in deals:
            rows2.append([d.time, d.ticket, d.symbol, d.type, d.volume, d.price, d.profit])
            tags2.append("profit" if d.profit >= 0 else "loss")
        self.hist_table.tree.set_rows(rows2, tags2)
        self.hist_status.configure(
            text=f"{len(deals)} negocio(s) nos ultimos 7 dias" if info else "Historico indisponivel: MT5 desconectado",
            fg=Theme.TEXT_SECONDARY,
        )
        self.last_update.configure(text=f"Atualizado: {time.strftime('%H:%M:%S')}")
        self.on_status(f"Carteira atualizada: {len(positions)} posicoes")

    def close_selected(self) -> None:
        sel = self.pos_table.tree.tree.selection()
        if not sel:
            self.on_status("Nenhuma posicao selecionada")
            return
        values = self.pos_table.tree.tree.item(sel[0], "values")
        ticket = int(values[0])
        if not messagebox.askyesno("Confirmar fechamento", f"Fechar a posicao real #{ticket}?"):
            return
        res = self.robot.close_position(ticket)
        if res.get("ok"):
            self.on_status(f"Posicao #{ticket} fechada")
        else:
            self.on_status(f"Erro ao fechar #{ticket}: {res.get('error')}")
        self.refresh()

    def close_all(self) -> None:
        if not messagebox.askyesno("Confirmar fechamento", "Fechar TODAS as posicoes reais abertas?"):
            return
        res = self.robot.close_all_positions()
        self.on_status(f"Fechadas {res.get('closed', 0)} posicoes")
        self.refresh()
