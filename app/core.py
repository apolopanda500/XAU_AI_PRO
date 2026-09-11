# -*- coding: utf-8 -*-
"""
Nucleo do app XAU_AI_PRO v1.2.0 com design PRO estilo TradingView/Binance.
"""
from __future__ import annotations

import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Any

from app.components.sidebar import Sidebar
from app.components.scrollable import ScrollableFrame
from app.config_manager import get_config
from app.learning_engine import get_learning_engine
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.tabs.dashboard import DashboardTab
from app.tabs.integrations import IntegrationsTab
from app.tabs.market import TradingViewMarket
from app.tabs.positions import PositionsTab
from app.tabs.robot import RobotTab
from app.tabs.settings import SettingsTab
from app.tabs.subgraph import SubgraphTab
from app.tabs.charts import ChartsTab
from app.tabs.tools import ToolsTab
from app.tabs.combined import CombinedTab
from app.tabs.strategy_tester import StrategyTester
from app.tabs.robot_vision import RobotVision
from app.theme.mexc import Theme
from app.components.button import ProButton
from app.utils.paths import ensure_paths
from app.runtime_metrics import set_gui_fps


class XAUAProApp:
    def __init__(self) -> None:
        ensure_paths()
        self.cfg = get_config()
        self.root = tk.Tk()
        self.root.title("XAU AI PRO v1.2.0 - Trading Desk")
        self.root.configure(bg=Theme.BG)

        # Centraliza a janela
        width = self.cfg.get('window', 'width', default=1280)
        height = self.cfg.get('window', 'height', default=800)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        # Garante que as coordenadas sejam positivas
        x = max(0, x)
        y = max(0, y)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(1120, 720)

        if self.cfg.get("window", "maximized", default=False):
            self.root.state("zoomed")

        # Força a janela a ficar visível
        self.root.deiconify()
        self.root.focus_force()

        self.robot = MT5Robot()
        self.market = MarketData(provider=self.cfg.get("market", "provider", default="auto"))
        self.tabs: dict[str, Any] = {}
        self._running = True
        self._frame_count = 0
        self._frame_window_started = time.perf_counter()
        self._xau_gui_fps = 0.0
        self._realtime_due: dict[str, float] = {}
        self._current_tab = ""
        self._scroll_positions: dict[str, float] = {}
        self._navigation_pending: str | None = None

        # Login removido: o app abre direto na interface principal.
        self._build_main()

    def _build_main(self) -> None:
        self.sidebar = Sidebar(self.root, on_navigate=self._navigate)
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(self.root, bg=Theme.BG)
        self.content.pack(side="right", fill="both", expand=True)

        self.header = tk.Frame(
            self.content,
            bg=Theme.BG_SECONDARY,
            height=Theme.HEADER_HEIGHT,
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
        )
        self.header.pack(fill="x", padx=24, pady=(16, 0))
        self.header.pack_propagate(False)

        # Clock widget (digital) no canto direito do header
        self.clock_frame = tk.Frame(self.header, bg=Theme.BG_SECONDARY)
        self.clock_frame.pack(side="right", padx=16, pady=4)
        self.clock_label = tk.Label(
            self.clock_frame,
            text="--:--  --/--",
            bg=Theme.BG_SECONDARY,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_MONO, 13, "bold"),
        )
        self.clock_label.pack(side="right")
        # Botao hamburger: puxa/esconde a barra lateral de abas.
        self.btn_sidebar = ProButton(
            self.header, "☰", self._toggle_sidebar,
            variant="GHOST", font_size=12, bold=True,
            padx=12, pady=8, width=44,
        )
        self.btn_sidebar.pack(side="left", padx=(12, 8), pady=12)
        self.header_context = tk.Frame(self.header, bg=Theme.BG_SECONDARY)
        self.header_context.pack(side="left", padx=18, pady=10)
        tk.Label(
            self.header_context,
            text="DESK OPERACIONAL",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8, "bold"),
        ).pack(anchor="w")
        self.header_title = tk.Label(
            self.header_context,
            text="Dashboard",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT,
            font=(Theme.FONT_FAMILY, 16, "bold"),
        )
        self.header_title.pack(anchor="w")

        # Status indicators (right side)
        self.status_frame = tk.Frame(self.header, bg=Theme.BG_SECONDARY)
        self.status_frame.pack(side="right", padx=18, pady=12)

        # MT5 connection status
        self.mt5_status = tk.Label(self.status_frame, text="● MT5", bg=Theme.CARD_ALT, fg=Theme.TEXT_MUTED,
                                   font=(Theme.FONT_FAMILY, 9, "bold"), padx=9, pady=4)
        self.mt5_status.pack(side="left", padx=(0, 12))

        # Market status
        self.market_status = tk.Label(self.status_frame, text="● Mercado", bg=Theme.CARD_ALT, fg=Theme.TEXT_MUTED,
                                      font=(Theme.FONT_FAMILY, 9, "bold"), padx=9, pady=4)
        self.market_status.pack(side="left", padx=(0, 12))

        # Clock digital em tempo real: chip com borda, HH:MM grande,
        # segundos em destaque (accent), data compacta e ":" piscando.
        clock_chip = tk.Frame(self.status_frame, bg=Theme.BG_SECONDARY,
                              highlightbackground=Theme.BORDER, highlightthickness=1)
        clock_chip.pack(side="left", padx=(0, 12))
        self.clock_time = tk.Label(clock_chip, text="--:--", bg=Theme.BG_SECONDARY,
                                   fg=Theme.TEXT, font=(Theme.FONT_MONO, 15, "bold"))
        self.clock_time.pack(side="left", padx=(10, 2), pady=4)
        self.clock_secs = tk.Label(clock_chip, text="--", bg=Theme.BG_SECONDARY,
                                   fg=Theme.ACCENT, font=(Theme.FONT_MONO, 11, "bold"))
        self.clock_secs.pack(side="left", padx=(0, 8), pady=4)
        self.clock_date = tk.Label(clock_chip, text="", bg=Theme.BG_SECONDARY,
                                   fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8))
        self.clock_date.pack(side="left", padx=(0, 10))
        self._update_clock()

        # Status label (existing)
        self.status_label = tk.Label(self.status_frame, text="Pronto", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY,
                                     font=(Theme.FONT_FAMILY, 9))
        self.status_label.pack(side="left")

        self.scroll = ScrollableFrame(self.content, bg=Theme.BG)
        self.scroll.pack(fill="both", expand=True)
        self.tab_container = self.scroll.inner
        self.tab_container._scroll_host = self.scroll

        # Todas as abas sÃ£o lazy-loaded. Construtores podem criar widgets,
        # imagens e controles; fazÃª-los no boot bloqueava a thread Tk e fazia
        # os botÃµes parecerem travados.
        self._tab_factories = {
            "dashboard": lambda: CombinedTab(self.tab_container, [
                ("Painel", lambda parent: DashboardTab(parent, self.robot, self.market, self._set_status)),
                ("Carteira", lambda parent: PositionsTab(parent, self.robot, self.market, self._set_status)),
            ]),
            "market": lambda: CombinedTab(self.tab_container, [
                ("Mercado", lambda parent: TradingViewMarket(parent, self.robot, self.market, self._set_status)),
                ("Graficos", lambda parent: ChartsTab(parent, self.robot, self.market, self._set_status)),
                ("AnÃ¡lise", lambda parent: SubgraphTab(parent, self.robot, self.market, self._set_status)),
            ]),
            "robot": lambda: CombinedTab(self.tab_container, [
                ("Controle", lambda parent: RobotTab(parent, self.robot, self.market, self._set_status)),
                ("Auditoria", lambda parent: ToolsTab(parent, self.robot, self.market, self._set_status)),
            ]),
                        "charts": lambda: CombinedTab(self.tab_container, [
                ("Grafico Avancado", lambda parent: ChartsTab(parent, self.robot, self.market, self._set_status)),
                ("Mercado", lambda parent: TradingViewMarket(parent, self.robot, self.market, self._set_status)),
            ]),
            "tester": lambda: CombinedTab(self.tab_container, [
                ("Strategy Tester", lambda parent: StrategyTester(parent, self._set_status)),
            ]),
            "vision": lambda: CombinedTab(self.tab_container, [
                ("Visao do Robo", lambda parent: RobotVision(parent, self.robot, self.market, self._set_status)),
            ]),
            "system": lambda: CombinedTab(self.tab_container, [
                ("Configuracoes", lambda parent: SettingsTab(parent, self.robot, self.market, self._set_status)),
                ("ConexÃµes", lambda parent: IntegrationsTab(parent, self.robot, self.market, self._set_status)),
            ]),
        }
        self._navigate("dashboard")
        self._start_threads()
        self._frame_tick()
        self._realtime_tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _navigate(self, key: str) -> None:
        if key not in self._tab_factories:
            return
        if key not in self.tabs:
            # Mostra feedback imediato e deixa o Tk processar o clique antes
            # de construir a aba. Isso evita a sensaÃ§Ã£o de botÃ£o congelado.
            self._navigation_pending = key
            self._set_status("Carregando aba...")
            self.root.after_idle(lambda: self._load_and_navigate(key))
            return
        self._show_tab(key)

    def _load_and_navigate(self, key: str) -> None:
        if key not in self._tab_factories:
            return
        if key not in self.tabs:
            self.tabs[key] = self._tab_factories[key]()
            self.tabs[key].frame.pack_forget()
            if key == "system":
                self.tabs[key].start_monitor()
            elif key == "charts":
                self.tabs[key].start_auto()
        self._navigation_pending = None
        self._show_tab(key)

    def _show_tab(self, key: str) -> None:
        if key == self._current_tab:
            return
        if self._current_tab and self._current_tab in self.tabs:
            self._scroll_positions[self._current_tab] = self.scroll.canvas.yview()[0]
            self.tabs[self._current_tab].frame.pack_forget()
        self._current_tab = key
        self.tabs[key].frame.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.scroll.canvas.yview_moveto(self._scroll_positions.get(key, 0.0))
        self.sidebar.set_active(key)
        titles = {
            "dashboard": "Painel",
            "market": "Mercado",
            "positions": "Carteira",
            "robot": "RobÃ´",
            "subgraph": "Subgraph",
            "settings": "ConfiguraÃ§Ã£o",
            "system": "Sistema",
            "charts": "Graficos",
        }
        self.header_title.configure(text=titles.get(key, key))

    def _toggle_sidebar(self) -> None:
        """Mostra/esconde a barra lateral (botao hamburger do header)."""
        visible = self.sidebar.toggle()
        self.btn_sidebar.set_text("⟮" if visible else "☰")

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)
        self.sidebar.set_status(text, Theme.TEXT_SECONDARY)

    def _update_clock(self) -> None:
        """Atualiza o relogio digital a cada segundo (dois pontos piscando)."""
        from datetime import datetime
        now = datetime.now()
        sep = ":" if now.second % 2 == 0 else " "
        try:
            self.clock_time.configure(text=f"{now:%H}{sep}{now:%M}")
            self.clock_secs.configure(text=f"{now:%S}")
            self.clock_date.configure(text=f"{now:%d/%m}")
        except Exception:
            return  # janela encerrada
        self.root.after(1000, self._update_clock)

    def _frame_tick(self) -> None:
        """Relogio da GUI a 30 FPS e medicao da cadencia efetivamente entregue."""
        if not self._running:
            return
        self._frame_count += 1
        now = time.perf_counter()
        elapsed = now - self._frame_window_started
        if elapsed >= 1.0:
            self._xau_gui_fps = self._frame_count / elapsed
            set_gui_fps(self._xau_gui_fps)
            self._frame_count = 0
            self._frame_window_started = now
        self.root.after(33, self._frame_tick)

    def _realtime_tick(self) -> None:
        """Atualiza somente a tela visivel, sem empilhar consultas em background.

        Preserva a posiÃ§Ã£o de leitura: tiramos um snapshot da rolagem antes do
        refresh e o ScrollableFrame restaura a fraÃ§Ã£o de yview apÃ³s o recÃ¡lculo
        final do layout (a menos que o usuÃ¡rio tenha rolado durante a coleta).
        """
        if not self._running:
            return
        intervals = {
            "dashboard": 2.0,
            "market": max(1.0, float(self.cfg.get("market", "refresh_seconds", default=3))),
            "robot": 2.0,
            "tools": 5.0,
            "system": 2.0,
        }
        key = self._current_tab
        now = time.monotonic()
        if key in intervals and now >= self._realtime_due.get(key, 0.0):
            tab = self.tabs.get(key)
            if tab is not None:
                snapshot = self.scroll.capture_view()
                try:
                    if key == "robot":
                        tab.check_ea()
                    elif key == "system":
                        tab.refresh_now()
                    else:
                        tab.refresh()
                except Exception as error:
                    self._set_status(f"Atualizacao em tempo real: {error}")
                # Restaura a leitura apÃ³s o conteÃºdo ser recalculado, saltando
                # apenas se o usuÃ¡rio rolou enquanto a coleta rodava.
                self.scroll.restore_view(snapshot)
            self._realtime_due[key] = now + intervals[key]
        self.root.after(250, self._realtime_tick)

    def _start_threads(self) -> None:
        # v1.2.0 - Auto-refresh removido: o loop de 10s acumulava chamadas em
        # background e travava a GUI (freeze). Atualizacao agora e MANUAL.
                # Opcoes de CPU (prioridade/afinidade) definidas na aba Configuracoes.
        try:
            from app.cpu import apply_cpu_options, apply_model_limits
            apply_cpu_options(self.cfg)
            apply_model_limits(self.cfg)
        except Exception:
            pass
        if self.cfg.get("learning", "enabled", default=True):
            get_learning_engine().start_scheduler()
        if self.cfg.get("mt5", "auto_connect", default=True):
            threading.Thread(target=self.robot.connect, daemon=True).start()
        # MT5 Gateway local (porta 9001) - MCP em background, junto com o app.
        try:
            from app.mt5_gateway import start_gateway
            threading.Thread(target=start_gateway, daemon=True).start()
        except Exception:
            pass
        # IA em camadas: mantem o assistente vivo enquanto o app estiver aberto.
        try:
            from app.ai_memory import start_keepalive
            self._ai_keepalive = start_keepalive(interval=300.0)
        except Exception:
            self._ai_keepalive = None

        # Refresh inicial (1x) ao entrar no app para iniciar as funcoes.
        self.root.after(2000, self._initial_refresh)

    def _initial_refresh(self) -> None:
        """Atualiza uma unica vez as abas principais na abertura do app."""
        for key in ("dashboard", "positions", "market"):
            try:
                tab = self.tabs.get(key)
                if tab is not None:
                    tab.refresh()
            except Exception:
                pass
        try:
            robot_tab = self.tabs.get("robot")
            if robot_tab is not None:
                robot_tab.check_ea()
        except Exception:
            pass
        try:
            system_tab = self.tabs.get("system")
            if system_tab is not None:
                system_tab.refresh_now()
        except Exception:
            pass
        try:
            charts_tab = self.tabs.get("charts")
            if charts_tab is not None:
                charts_tab.refresh_now()
        except Exception:
            pass

    def _on_close(self) -> None:
        if messagebox.askyesno("Sair", "Deseja realmente fechar o XAU AI PRO?"):
            self._running = False
            # self.tabs["market"].stop_auto_refresh()  # desativado
            system_tab = self.tabs.get("system")
            if system_tab is not None:
                system_tab.stop_monitor()
            charts_tab = self.tabs.get("charts")
            if charts_tab is not None:
                charts_tab.stop_auto()
            try:
                self.tabs["positions"].stop_auto_refresh()
            except Exception:
                pass
            try:
                self.tabs["dashboard"].stop_auto_refresh()
            except Exception:
                pass
            try:
                self.tabs["market"].stop_auto_refresh()
            except Exception:
                pass
            try:
                self.tabs["tools"].stop_auto_refresh()
            except Exception:
                pass
            try:
                from app.mt5_gateway import stop_gateway
                stop_gateway()
            except Exception:
                pass
            get_learning_engine().stop_scheduler()
            try:
                from app.ai_memory import stop_keepalive
                stop_keepalive()
            except Exception:
                pass
            try:
                self.animated_bg.stop()
            except Exception:
                pass
            self.market.disconnect()
            self.robot.disconnect()
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = XAUAProApp()
    app.run()


if __name__ == "__main__":
    main()
