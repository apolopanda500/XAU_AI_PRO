"""
Aba Dashboard do app XAU_AI_PRO.
"""
from __future__ import annotations

import socket
import time
import tkinter as tk
from datetime import datetime
from typing import Any, Callable

from app.components.cards import Card, KPI, PrimaryButton
from app.components.charts import EquityChart
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.system_status_reader import read_system_status, summarize
from app.event_reader import event_status_lines
from app.backend_client import fetch_all, status_lines  # ETAPA 16.5  # ETAPA 15.6
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

        # ETAPA 16.5: seccao Backend API (16.4)
        api_card = Card(bottom, title='backend API (16.4)')
        api_card.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(10, 0))
        self.api_frame = tk.Frame(api_card.body, bg=Theme.CARD)
        self.api_frame.pack(fill='both', expand=True, padx=8, pady=8)

    def refresh(self) -> None:
        """Atualiza o dashboard SEM travar a GUI.

        Todo o trabalho pesado (MT5, sockets, backend, arquivos) roda em
        thread daemon; apenas a aplicacao dos resultados toca a GUI
        (na thread principal, via after). Elimina os travamentos periodicos
        de segundos causados pelo refresh sincrono na main thread.
        """
        self.last_update.configure(text="Atualizando...")
        from app.utils.async_ui import run_bg
        run_bg(
            self.frame,
            work=self._collect,
            apply_result=self._apply,
        )

    # ------------------------------------------------------------------
    # Auto-refresh (a cada 1 min)
    # ------------------------------------------------------------------
    def start_auto_refresh(self, interval_sec: int = 60) -> None:
        self._auto_running = True
        import threading as _t

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

        _t.Thread(target=loop, daemon=True).start()

    def stop_auto_refresh(self) -> None:
        self._auto_running = False

    # ------------------------- coletores (background) ---------------------

    def _collect(self) -> dict[str, Any]:
        """Coleta TUDO em background (sem tocar widgets)."""
        data: dict[str, Any] = {"ts": datetime.now().strftime("%H:%M:%S")}
        try:
            data["account"] = self._collect_account()
        except Exception:
            data["account"] = None
        try:
            data["services"] = self._collect_services()
        except Exception:
            data["services"] = {}
        try:
            data["system"] = self._collect_system()
        except Exception:
            data["system"] = []
        try:
            data["backend"] = self._collect_backend()
        except Exception:
            data["backend"] = []
        return data

    def _collect_account(self) -> dict[str, Any] | None:
        info = self.robot.account_info()
        if not info:
            return None
        out = dict(info)
        try:
            out["_positions"] = self.robot.get_positions()
        except Exception:
            out["_positions"] = []
        try:
            deals = self.robot.get_history(days=30)
            wins = sum(1 for d in deals if d.profit > 0)
            losses = sum(1 for d in deals if d.profit < 0)
            total = wins + losses
            out["_winrate"] = (wins / total * 100) if total else None
        except Exception:
            out["_winrate"] = None
        return out

    def _collect_services(self) -> dict[str, Any]:
        cfg = get_config()
        ports = {
            "backend": cfg.get("api", "backend_port", default=8000),
            "dashboard": cfg.get("api", "dashboard_port", default=8501),
            "litellm": cfg.get("api", "litellm_port", default=4000),
        }
        out: dict[str, Any] = {}
        connected = bool(self.robot.connected)
        out["mt5"] = connected
        out["mt5_warn"] = False
        if connected:
            try:
                info = self.robot.account_info()
                out["mt5_warn"] = bool(info and not info.get("trade_allowed", True))
            except Exception:
                out["mt5_warn"] = False
        for key, port in ports.items():
            out[key] = self._port_open(port)
        if connected:
            try:
                out["robot"] = bool(self.robot.is_ea_active().get("active", False))
            except Exception:
                out["robot"] = False
        else:
            out["robot"] = False
        return out

    def _collect_system(self) -> list[tuple[str, str, str]]:
        lines: list[tuple[str, str, str]] = []
        try:
            lines.extend(summarize(read_system_status()))
        except Exception:
            lines = [("EA Snapshot", "ERRO DE LEITURA", "bad")]
        lines.append(("", "", ""))
        try:
            lines.extend(event_status_lines())
        except Exception:
            lines.append(("Eventos", "ERRO DE LEITURA", "bad"))
        return [ln for ln in lines if ln != ("", "", "")]

    def _collect_backend(self) -> list[tuple[str, str, str]]:
        try:
            data = fetch_all()
            return status_lines(data)
        except Exception:
            return [("Backend API", "ERRO DE LEITURA", "bad")]

    # ------------------------- aplicadores (GUI thread) -------------------

    def _apply(self, data: dict[str, Any] | None) -> None:
        if not data:
            return
        self._apply_account(data.get("account"))
        self._apply_services(data.get("services") or {})
        self._apply_system(data.get("system") or [])
        self._apply_backend(data.get("backend") or [])
        self.last_update.configure(text=f"Atualizado: {data.get('ts', '')}")
        self.on_status("Dashboard atualizado")

    def _apply_account(self, acct: dict[str, Any] | None) -> None:
        if not acct:
            self.kpi_balance.set("--")
            self.kpi_equity.set("--")
            self.kpi_profit.set("--")
            self.kpi_margin.set("--")
            self.kpi_positions.set("--")
            return
        self.kpi_balance.set(f"{acct.get('balance', 0):,.2f}")
        self.kpi_equity.set(f"{acct.get('equity', 0):,.2f}")
        profit = acct.get("profit", 0)
        self.kpi_profit.set(f"{profit:,.2f}",
                            Theme.SUCCESS if profit >= 0 else Theme.DANGER)
        self.kpi_margin.set(f"{acct.get('margin_free', 0):,.2f}")
        positions = acct.get("_positions") or []
        self.kpi_positions.set(str(len(positions)))
        winrate = acct.get("_winrate")
        if winrate is None:
            self.kpi_winrate.set("--")
        else:
            self.kpi_winrate.set(f"{winrate:.1f}%",
                                 Theme.SUCCESS if winrate >= 50 else Theme.ACCENT)
        equity = acct.get("equity", 0)
        try:
            self._equity_values.append(float(equity))
            if len(self._equity_values) > 50:
                self._equity_values = self._equity_values[-50:]
            self.chart.update_data(list(self._equity_values))
        except Exception:
            pass

    def _apply_services(self, svc: dict[str, Any]) -> None:
        if svc.get("mt5"):
            self._set_service("mt5", True,
                              text="AUTOTRADING OFF" if svc.get("mt5_warn") else None,
                              color=Theme.WARNING if svc.get("mt5_warn") else None)
        else:
            self._set_service("mt5", False)
        for key in ("backend", "dashboard", "litellm"):
            self._set_service(key, bool(svc.get(key, False)))
        self._set_service("robot", bool(svc.get("robot", False)))

    def _apply_system(self, lines: list[tuple[str, str, str]]) -> None:
        for w in self.ea_frame.winfo_children():
            w.destroy()
        color_map = {
            "": Theme.TEXT,
            "ok": Theme.SUCCESS,
            "warn": Theme.WARNING,
            "bad": Theme.DANGER,
        }
        for name, value, color in lines:
            row = tk.Frame(self.ea_frame, bg=Theme.CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=Theme.CARD, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 10)).pack(side="left")
            tk.Label(row, text=value, bg=Theme.CARD,
                     fg=color_map.get(color, Theme.TEXT),
                     font=(Theme.FONT_FAMILY, 9, "bold")).pack(side="right")

    def _apply_backend(self, lines: list[tuple[str, str, str]]) -> None:
        for w in self.api_frame.winfo_children():
            w.destroy()
        color_map = {"": Theme.TEXT, "ok": Theme.SUCCESS,
                     "warn": Theme.WARNING, "bad": Theme.DANGER}
        for name, value, color in lines:
            row = tk.Frame(self.api_frame, bg=Theme.CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=Theme.CARD, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 10)).pack(side="left")
            tk.Label(row, text=value, bg=Theme.CARD,
                     fg=color_map.get(color, Theme.TEXT),
                     font=(Theme.FONT_FAMILY, 9, "bold")).pack(side="right")

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