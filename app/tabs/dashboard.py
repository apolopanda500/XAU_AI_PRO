"""
Aba Dashboard PRO do app XAU_AI_PRO.
Layout profissional com KPIs, gráfico de equity e status de operações.
"""
from __future__ import annotations

import socket
import time
import tkinter as tk
from datetime import datetime
from typing import Any, Callable

from app.components.cards import Card, KPI, PrimaryButton, SecondaryButton, TerminalKPI, StatusBadge
from app.tabs.charts import ChartCanvas
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
        self._build()

    def _build(self) -> None:
        # Header com título e botão de atualização
        header = Card(self.frame)
        header.pack(fill="x", padx=24, pady=(20, 10))
        header.body.pack_forget()
        tk.Label(header, text="Professional Control Center", bg=Theme.CARD, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(anchor="w", padx=20, pady=(14, 0))
        tk.Label(header, text="MT5 sync, risk overview, execution status and chart intelligence",
                 bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 9)).pack(anchor="w", padx=20, pady=(2, 14))
        self.last_update = tk.Label(header, text="Aguardando primeira leitura", bg=Theme.CARD,
                                    fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 9))
        self.last_update.pack(side="right", padx=20, pady=12)
        PrimaryButton(header, text="Atualizar agora", command=self.refresh, width=16).place(relx=1, x=-120, y=13)

        # KPIs em grid (4 principais + 2 secundários)
        kpi_card = tk.Frame(self.frame, bg=Theme.BG)
        kpi_card.pack(fill="x", padx=24, pady=(0, 10))
        self.kpi_balance = TerminalKPI(kpi_card, "Saldo", "MT5 offline", Theme.PRIMARY)
        self.kpi_equity = TerminalKPI(kpi_card, "Equity", "MT5 offline", Theme.SUCCESS)
        self.kpi_profit = TerminalKPI(kpi_card, "PnL Flutuante", "MT5 offline", Theme.SUCCESS)
        self.kpi_positions = TerminalKPI(kpi_card, "Posicoes", "MT5 offline", Theme.WARNING)
        self.kpi_margin = TerminalKPI(kpi_card, "Margem Livre", "MT5 offline", Theme.TEXT_SECONDARY)
        self.kpi_winrate = TerminalKPI(kpi_card, "Win Rate", "Sem historico", Theme.ACCENT)
        for kpi in [self.kpi_balance, self.kpi_equity, self.kpi_profit, self.kpi_positions,
                    self.kpi_margin, self.kpi_winrate]:
            kpi.pack(side="left", expand=True, fill="both", padx=(0, 10), pady=0)

        # Área inferior: gráfico + snapshot
        bottom = tk.Frame(self.frame, bg=Theme.BG)
        bottom.pack(fill="both", expand=True, padx=24, pady=10)
        bottom.grid_columnconfigure(0, weight=2)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        # Card do gráfico
        chart_card = Card(bottom, title="XAUUSD M5 | Bollinger + RSI + Execution Zones")
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.chart = ChartCanvas(chart_card.body)
        self.chart.pack(fill="both", expand=True, padx=8, pady=8)

        ea_card = Card(bottom, title="EA Snapshot")
        ea_card.grid(row=0, column=1, sticky="nsew")
        self.account_label = tk.Label(
            ea_card.body, text="Conta MT5: desconectada", bg=Theme.CARD,
            fg=Theme.WARNING, font=(Theme.FONT_FAMILY, 9, "bold"), anchor="w",
        )
        self.account_label.pack(fill="x", padx=8, pady=(8, 2))
        self.status_frame = tk.Frame(ea_card.body, bg=Theme.CARD)
        self.status_frame.pack(fill="x", padx=8, pady=(8, 0))
        self.service_labels: dict[str, tk.Label] = {}
        services = [("mt5", "MetaTrader 5"), ("robot", "Robo EA"),
                    ("backend", "Backend API"), ("dashboard", "Dashboard Web"),
                    ("litellm", "LiteLLM")]
        for key, name in services:
            row = tk.Frame(self.status_frame, bg=Theme.CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=Theme.CARD, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 9)).pack(side="left")
            lbl = tk.Label(row, text="OFFLINE", bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                           font=(Theme.FONT_FAMILY, 8, "bold"))
            lbl.pack(side="right")
            self.service_labels[key] = lbl
        self.ea_frame = tk.Frame(ea_card.body, bg=Theme.CARD)
        self.ea_frame.pack(fill="x", padx=8, pady=8)
        self.ops_frame = tk.Frame(ea_card.body, bg=Theme.CARD)
        self.ops_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))


    def _on_banner_resize(self, event: tk.Event) -> None:
        """Redimensiona o banner cripto conforme a largura da janela."""
        if self._banner_pil is None or self._banner_label is None:
            return
        w = int(event.width) - 48  # desconta padx=24 de cada lado
        if w < 240 or w == self._banner_last_w:
            return
        self._banner_last_w = w
        try:
            from PIL import Image, ImageTk
            ratio = w / self._banner_pil.width
            h = max(1, min(int(self._banner_pil.height * ratio), 260))
            img = self._banner_pil.resize((w, h), Image.LANCZOS)
            self._banner_photo = ImageTk.PhotoImage(img)
            self._banner_label.configure(image=self._banner_photo, height=h)
        except Exception:
            pass

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
        try:
            data["calendar"] = self._collect_calendar()
        except Exception:
            data["calendar"] = []
        try:
            data["sync"] = self._collect_sync()
        except Exception:
            data["sync"] = {}
        try:
            data["candles"] = self._collect_candles()
        except Exception:
            data["candles"] = []
        return data

    def _collect_candles(self) -> list[dict[str, Any]]:
        """Obtém uma janela curta para o gráfico do desk sem bloquear o Tk."""
        mt5 = getattr(self.market, "_mt5", None)
        if mt5 is None:
            return []
        rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 120)
        if rates is None:
            return []
        return [
            {
                "symbol": "XAUUSD",
                "time": datetime.fromtimestamp(int(row["time"])).strftime("%d/%m %H:%M"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            for row in rates[-120:]
        ]

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

    def _collect_calendar(self) -> list[str]:
        from app.economic_calendar import event_summary
        return event_summary(tz="BRT")

    def _collect_sync(self) -> dict[str, Any]:
        from app.mt5_sync import to_export
        return to_export()

    # ------------------------- aplicadores (GUI thread) -------------------

    def _apply(self, data: dict[str, Any] | None) -> None:
        if not data:
            self.last_update.configure(text="Falha ao coletar dados reais")
            self.on_status("Dashboard sem resposta das fontes de dados")
            return
        self._apply_account(data.get("account"))
        self._apply_services(data.get("services") or {})
        self._apply_system(data.get("system") or [])
        self._apply_ops(data)
        candles = data.get("candles") or []
        if candles:
            self.chart.set_data(candles, "candles")
            self.chart.set_indicator("bollinger", {"type": "bollinger", "period": 20})
        self.last_update.configure(text=f"Atualizado: {data.get('ts', '')}")
        self.on_status("Dashboard atualizado")

    def _apply_account(self, acct: dict[str, Any] | None) -> None:
        if not acct:
            self.kpi_balance.set("MT5 offline")
            self.kpi_equity.set("MT5 offline")
            self.kpi_profit.set("MT5 offline")
            self.kpi_margin.set("MT5 offline")
            self.kpi_positions.set("MT5 offline")
            self.kpi_winrate.set("Sem historico")
            self.account_label.configure(text="Conta MT5: desconectada", fg=Theme.WARNING)
            return
        currency = str(acct.get("currency") or "").strip()
        suffix = f" {currency}" if currency else ""
        self.kpi_balance.set(f"{float(acct.get('balance') or 0):,.2f}{suffix}")
        self.kpi_equity.set(f"{float(acct.get('equity') or 0):,.2f}{suffix}")
        profit = float(acct.get("profit") or 0)
        self.kpi_profit.set(f"{profit:,.2f}",
                            Theme.SUCCESS if profit >= 0 else Theme.DANGER)
        self.kpi_margin.set(f"{float(acct.get('margin_free') or 0):,.2f}{suffix}")
        positions = acct.get("_positions") or []
        self.kpi_positions.set(str(len(positions)))
        winrate = acct.get("_winrate")
        if winrate is None:
            self.kpi_winrate.set("Sem historico")
        else:
            self.kpi_winrate.set(f"{winrate:.1f}%",
                                 Theme.SUCCESS if winrate >= 50 else Theme.ACCENT)
        login = acct.get("login") or "nao informado"
        server = acct.get("server") or "servidor nao informado"
        owner = acct.get("name") or "titular nao informado"
        self.account_label.configure(
            text=f"Conta {login} | {owner} | {server}",
            fg=Theme.SUCCESS if acct.get("terminal_connected", True) else Theme.WARNING,
        )

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

    def _apply_ops(self, data: dict[str, Any]) -> None:
        for w in self.ops_frame.winfo_children():
            w.destroy()
        self._ops_section("Backend", data.get("backend") or [])
        self._ops_section("Calendario", self._calendar_to_lines(data.get("calendar") or []))
        self._ops_section("Sync MT5", self._sync_to_lines(data.get("sync") or {}))

    def _ops_section(self, title: str, lines: list[tuple[str, str, str]]) -> None:
        title_row = tk.Frame(self.ops_frame, bg=Theme.CARD)
        title_row.pack(fill="x", pady=(4, 2))
        tk.Label(title_row, text=title, bg=Theme.CARD, fg=Theme.ACCENT,
                 font=(Theme.FONT_FAMILY, 10, "bold")).pack(side="left")
        if not lines:
            lines = [("Status", "SEM DADOS", "warn")]
        color_map = {
            "": Theme.TEXT_SOFT,
            "ok": Theme.SUCCESS,
            "warn": Theme.WARNING,
            "bad": Theme.DANGER,
        }
        for name, value, color in lines[:8]:
            row = tk.Frame(self.ops_frame, bg=Theme.CARD)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=name, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(side="left")
            tk.Label(row, text=value, bg=Theme.CARD,
                     fg=color_map.get(color, Theme.TEXT_SOFT),
                     font=(Theme.FONT_FAMILY, 9, "bold"),
                     wraplength=340, justify="right").pack(side="right")

    @staticmethod
    def _calendar_to_lines(items: list[str]) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        for item in items[:5]:
            text = (item or "").strip()
            if not text:
                continue
            color = "warn" if any(k in text.upper() for k in ("ALTA", "HIGH", "IMPACT")) else ""
            out.append(("Evento", text[:90], color))
        return out

    @staticmethod
    def _sync_to_lines(sync: dict[str, Any]) -> list[tuple[str, str, str]]:
        if not sync:
            return []
        account = sync.get("account") or {}
        lines = [
            ("Conectado", "SIM" if sync.get("conectado") else "NAO", "ok" if sync.get("conectado") else "bad"),
            ("Login", str(account.get("login") or "--"), ""),
            ("Servidor", str(account.get("server") or "--"), ""),
            ("Posicoes", str(sync.get("positions_count", 0)), ""),
            ("Historico 30d", str(sync.get("history_count", 0)), ""),
        ]
        return lines

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
