"""
Aba Dashboard do app XAU_AI_PRO.
"""
from __future__ import annotations

import socket
import tkinter as tk
from datetime import datetime
from typing import Any, Callable

from app.components.cards import Card, KPI, PrimaryButton
from app.components.charts import EquityChart
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.system_status_reader import read_system_status, summarize
from app.event_reader import event_status_lines  # ETAPA 15.6
from app.theme.mexc import Theme


class DashboardTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._equity_values: list[float] = []
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Dashboard", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.last_update = tk.Label(header, text="Atualizado: --", bg=Theme.BG,
                                    fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 9))
        self.last_update.pack(side="right")
        PrimaryButton(header, text="Atualizar agora", command=self.refresh, width=16).pack(side="right", padx=12)

        kpi_card = Card(self.frame)
        kpi_card.pack(fill="x", padx=24, pady=10)
        self.kpi_balance = KPI(kpi_card.body, "Saldo", "--", Theme.TEXT)
        self.kpi_equity = KPI(kpi_card.body, "Equity", "--", Theme.TEXT)
        self.kpi_profit = KPI(kpi_card.body, "Lucro Flutuante", "--", Theme.SUCCESS)
        self.kpi_positions = KPI(kpi_card.body, "Posicoes Abertas", "--", Theme.PRIMARY)
        self.kpi_margin = KPI(kpi_card.body, "Margem Livre", "--", Theme.TEXT_SECONDARY)
        self.kpi_winrate = KPI(kpi_card.body, "Win Rate", "--", Theme.ACCENT)
        for kpi in [self.kpi_balance, self.kpi_equity, self.kpi_profit,
                    self.kpi_positions, self.kpi_margin, self.kpi_winrate]:
            kpi.pack(side="left", expand=True, fill="both", padx=8, pady=8)

        bottom = tk.Frame(self.frame, bg=Theme.BG)
        bottom.pack(fill="both", expand=True, padx=24, pady=10)
        bottom.grid_columnconfigure(0, weight=2)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        chart_card = Card(bottom, title="Evolucao do Equity")
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.chart = EquityChart(chart_card.body)
        self.chart.pack(fill="both", expand=True, padx=8, pady=8)

        status_card = Card(bottom, title="Status dos Servicos")
        status_card.grid(row=0, column=1, sticky="nsew")
        self.status_frame = tk.Frame(status_card.body, bg=Theme.CARD)
        self.status_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.service_labels: dict[str, tk.Label] = {}
        services = [
            ("mt5", "MetaTrader 5"),
            ("backend", "Backend API"),
            ("dashboard", "Dashboard Streamlit"),
            ("litellm", "LiteLLM Proxy"),
            ("robot", "Robo EA"),
        ]
        for key, name in services:
            row = tk.Frame(self.status_frame, bg=Theme.CARD)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=name, bg=Theme.CARD, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 10)).pack(side="left")
            lbl = tk.Label(row, text="OFFLINE", bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                           font=(Theme.FONT_FAMILY, 9, "bold"))
            lbl.pack(side="right")
            self.service_labels[key] = lbl

        # ETAPA 15.6/15.10: snapshot operacional do EA (system_status.json)
        ea_card = Card(bottom, title="EA Snapshot (system_status.json)")
        ea_card.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self.ea_frame = tk.Frame(ea_card.body, bg=Theme.CARD)
        self.ea_frame.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh(self) -> None:
        self._update_account()
        self._update_services()
        self._update_system_status()
        self.last_update.configure(text=f"Atualizado: {datetime.now().strftime('%H:%M:%S')}")
        self.on_status("Dashboard atualizado")

    def _update_system_status(self) -> None:
        """ETAPA 15.6/15.10: exibe o snapshot operacional do EA."""
        for w in self.ea_frame.winfo_children():
            w.destroy()

        color_map = {
            "": Theme.TEXT,
            "ok": Theme.SUCCESS,
            "warn": Theme.WARNING,
            "bad": Theme.DANGER,
        }

        try:
            lines = summarize(read_system_status())
        except Exception:
            lines = [("EA Snapshot", "ERRO DE LEITURA", "bad")]

        for name, value, color in lines:
            row = tk.Frame(self.ea_frame, bg=Theme.CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=name, bg=Theme.CARD, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 10)).pack(side="left")
            tk.Label(row, text=value, bg=Theme.CARD,
                     fg=color_map.get(color, Theme.TEXT),
                     font=(Theme.FONT_FAMILY, 9, "bold")).pack(side="right")

        # ETAPA 15.6: Event Stream (forward_test_events.csv)
        sep = tk.Frame(self.ea_frame, bg=Theme.CARD, height=1)
        sep.pack(fill="x", pady=6)
        tk.Label(self.ea_frame, text="Event Stream (15.6)", bg=Theme.CARD,
                 fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 10, "bold")).pack(anchor="w")
        try:
            ev_lines = event_status_lines()
        except Exception:
            ev_lines = [("Eventos", "ERRO DE LEITURA", "bad")]
        for name, value, color in ev_lines:
            row = tk.Frame(self.ea_frame, bg=Theme.CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=Theme.CARD, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 10)).pack(side="left")
            tk.Label(row, text=value, bg=Theme.CARD,
                     fg=color_map.get(color, Theme.TEXT),
                     font=(Theme.FONT_FAMILY, 9, "bold")).pack(side="right")

    def _update_account(self) -> None:
        info = self.robot.account_info()
        if info:
            self.kpi_balance.set(f"{info['balance']:,.2f}")
            self.kpi_equity.set(f"{info['equity']:,.2f}")
            self.kpi_profit.set(f"{info['profit']:,.2f}",
                                Theme.SUCCESS if info['profit'] >= 0 else Theme.DANGER)
            self.kpi_margin.set(f"{info['margin_free']:,.2f}")
            positions = self.robot.get_positions()
            self.kpi_positions.set(str(len(positions)))
            self._update_winrate()
            self._equity_values.append(info['equity'])
            if len(self._equity_values) > 50:
                self._equity_values = self._equity_values[-50:]
            self.chart.update_data(self._equity_values)
        else:
            self.kpi_balance.set("--")
            self.kpi_equity.set("--")
            self.kpi_profit.set("--")
            self.kpi_margin.set("--")
            self.kpi_positions.set("--")

    def _update_winrate(self) -> None:
        deals = self.robot.get_history(days=30)
        wins = sum(1 for d in deals if d.profit > 0)
        losses = sum(1 for d in deals if d.profit < 0)
        total = wins + losses
        if total == 0:
            self.kpi_winrate.set("--")
            return
        rate = wins / total * 100
        self.kpi_winrate.set(f"{rate:.1f}%",
                             Theme.SUCCESS if rate >= 50 else Theme.ACCENT)

    def _update_services(self) -> None:
        cfg = get_config()
        ports = {
            "backend": cfg.get("api", "backend_port", default=8000),
            "dashboard": cfg.get("api", "dashboard_port", default=8501),
            "litellm": cfg.get("api", "litellm_port", default=4000),
        }
        if self.robot.connected:
            info = self.robot.account_info()
            if info and not info.get("trade_allowed", True):
                self._set_service("mt5", True, text="AUTOTRADING OFF", color=Theme.WARNING)
            else:
                self._set_service("mt5", True)
        else:
            self._set_service("mt5", False)
        for key, port in ports.items():
            self._set_service(key, self._port_open(port))
        if self.robot.connected:
            ea = self.robot.is_ea_active()
            self._set_service("robot", ea.get("active", False))
        else:
            self._set_service("robot", False)

    def _set_service(self, key: str, online: bool, text: str | None = None, color: str | None = None) -> None:
        lbl = self.service_labels.get(key)
        if lbl:
            lbl.configure(text=text or ("ONLINE" if online else "OFFLINE"),
                          fg=color or (Theme.SUCCESS if online else Theme.TEXT_MUTED))

    @staticmethod
    def _port_open(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.4)
                return s.connect_ex(("127.0.0.1", int(port))) == 0
        except Exception:
            return False

