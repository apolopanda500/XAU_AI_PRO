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

from app.components.animated_bg import AnimatedBackground
from app.components.sidebar import Sidebar
from app.components.scrollable import ScrollableFrame
from app.config_manager import get_config
from app.learning_engine import get_learning_engine
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.tabs.assistant import AssistantTab
from app.tabs.dashboard import DashboardTab
from app.tabs.integrations import IntegrationsTab
from app.tabs.market import MarketTab
from app.tabs.positions import PositionsTab
from app.tabs.robot import RobotTab
from app.tabs.settings import SettingsTab
from app.tabs.search import SearchTab
from app.tabs.community import CommunityTab
from app.tabs.subgraph import SubgraphTab
from app.tabs.system import SystemTab
from app.tabs.charts import ChartsTab
from app.tabs.tools import ToolsTab
from app.tabs.training import TrainingTab
from app.tabs.combined import CombinedTab
from app.theme.mexc import Theme
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
        self._navigation_pending: str | None = None

        # Login removido: o app abre direto na interface principal.
        self._build_main()

    def _build_main(self) -> None:
        self.sidebar = Sidebar(self.root, on_navigate=self._navigate)
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(self.root, bg=Theme.BG)
        self.content.pack(side="right", fill="both", expand=True)

        # Plano de fundo animado (camada inferior)
        self.animated_bg = AnimatedBackground(self.content)
        self.animated_bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.animated_bg.start()

        self.header = tk.Frame(self.content, bg=Theme.BG, height=56)
        self.header.pack(fill="x", padx=24, pady=(12, 0))
        self.header.pack_propagate(False)
        self.header_title = tk.Label(self.header, text="Dashboard", bg=Theme.BG, fg=Theme.TEXT,
                                     font=(Theme.FONT_FAMILY, 16, "bold"))
        self.header_title.pack(side="left")

        # Status indicators (right side)
        self.status_frame = tk.Frame(self.header, bg=Theme.BG)
        self.status_frame.pack(side="right")

        # MT5 connection status
        self.mt5_status = tk.Label(self.status_frame, text="● MT5", bg=Theme.BG, fg=Theme.TEXT_MUTED,
                                   font=(Theme.FONT_FAMILY, 9))
        self.mt5_status.pack(side="left", padx=(0, 12))

        # Market status
        self.market_status = tk.Label(self.status_frame, text="● Market", bg=Theme.BG, fg=Theme.TEXT_MUTED,
                                      font=(Theme.FONT_FAMILY, 9))
        self.market_status.pack(side="left", padx=(0, 12))

        # Clock
        self.clock_label = tk.Label(self.status_frame, text="", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                                    font=(Theme.FONT_MONO, 10))
        self.clock_label.pack(side="left", padx=(0, 12))
        self._update_clock()

        # Status label (existing)
        self.status_label = tk.Label(self.status_frame, text="Pronto", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                                     font=(Theme.FONT_FAMILY, 9))
        self.status_label.pack(side="left")

        self.scroll = ScrollableFrame(self.content, bg=Theme.BG)
        self.scroll.pack(fill="both", expand=True)
        self.tab_container = self.scroll.inner

        # Todas as abas são lazy-loaded. Construtores podem criar widgets,
        # imagens e controles; fazê-los no boot bloqueava a thread Tk e fazia
        # os botões parecerem travados.
        self._tab_factories = {
            "dashboard": lambda: CombinedTab(self.tab_container, [
                ("Visao geral", lambda parent: DashboardTab(parent, self.robot, self.market, self._set_status)),
                ("Carteira", lambda parent: PositionsTab(parent, self.robot, self.market, self._set_status)),
            ]),
            "market": lambda: CombinedTab(self.tab_container, [
                ("Mercado", lambda parent: MarketTab(parent, self.robot, self.market, self._set_status)),
                ("Graficos", lambda parent: ChartsTab(parent, self.robot, self.market, self._set_status)),
                ("Subgraph", lambda parent: SubgraphTab(parent, self.robot, self.market, self._set_status)),
            ]),
            "robot": lambda: RobotTab(self.tab_container, self.robot, self.market, self._set_status),
            "assistant": lambda: CombinedTab(self.tab_container, [
                ("Chat IA", lambda parent: AssistantTab(parent, self.robot, self.market, self._set_status)),
                ("Treinamento", lambda parent: TrainingTab(parent, self.robot, self.market, self._set_status)),
                ("Pesquisa", lambda parent: SearchTab(parent, self.robot, self.market, self._set_status)),
                ("Comunidade", lambda parent: CommunityTab(parent, self.robot, self.market, self._set_status)),
            ]),
            "tools": lambda: ToolsTab(self.tab_container, self.robot, self.market, self._set_status),
            "audit": lambda: ToolsTab(self.tab_container, self.robot, self.market, self._set_status),
            "integrations": lambda: IntegrationsTab(self.tab_container, self.robot, self.market, self._set_status),
            "system": lambda: CombinedTab(self.tab_container, [
                ("Monitor", lambda parent: SystemTab(parent, self.robot, self.market, self._set_status)),
                ("Configuracoes", lambda parent: SettingsTab(parent, self.robot, self.market, self._set_status)),
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
            # de construir a aba. Isso evita a sensação de botão congelado.
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
        if self._current_tab and self._current_tab in self.tabs:
            self.tabs[self._current_tab].frame.pack_forget()
        self._current_tab = key
        self.tabs[key].frame.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.scroll.canvas.yview_moveto(0)
        self.sidebar.set_active(key)
        titles = {
            "dashboard": "Dashboard",
            "market": "Mercado",
            "positions": "Carteira",
            "robot": "Controle do Robo",
            "training": "Treinamento IA",
            "assistant": "Assistente",
            "tools": "Ferramentas",
            "audit": "Auditoria",
            "integrations": "Integracoes",
            "subgraph": "Subgraph",
            "settings": "Configuracoes",
            "system": "Sistema",
            "charts": "Graficos",
            "search": "Pesquisa",
            "community": "Comunidade",
        }
        self.header_title.configure(text=titles.get(key, key))

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)
        self.sidebar.set_status(text, Theme.TEXT_SECONDARY)

    def _update_clock(self) -> None:
        """Atualiza o relogio a cada segundo."""
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.configure(text=now)
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
        """Atualiza somente a tela visivel, sem empilhar consultas em background."""
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
                try:
                    if key == "robot":
                        tab.check_ea()
                    elif key == "system":
                        tab.refresh_now()
                    else:
                        tab.refresh()
                except Exception as error:
                    self._set_status(f"Atualizacao em tempo real: {error}")
            self._realtime_due[key] = now + intervals[key]
        self.root.after(250, self._realtime_tick)

    def _start_threads(self) -> None:
        # v1.2.0 - Auto-refresh removido: o loop de 10s acumulava chamadas em
        # background e travava a GUI (freeze). Atualizacao agora e MANUAL.
        # Opcoes de CPU (prioridade/afinidade) definidas na aba Configuracoes.
        try:
            from app.cpu import apply_cpu_options, apply_model_limits
            ok_p, ok_a = apply_cpu_options(self.cfg)
            n_jobs, max_ram = apply_model_limits(self.cfg)
            self._set_status(
                f"CPU: prioridade {'ok' if ok_p else 'falhou'}, afinidade {'ok' if ok_a else 'falhou'}"
                f", modelos: {n_jobs} nucleo(s), RAM {max_ram} MB"
            )
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
