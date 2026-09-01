"""
Nucleo do app XAU_AI_PRO v1.2.0 com design MEXC.
"""
from __future__ import annotations

import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Any

from app.components.sidebar import Sidebar
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
from app.tabs.subgraph import SubgraphTab
from app.tabs.tools import ToolsTab
from app.tabs.training import TrainingTab
from app.theme.mexc import Theme
from app.utils.paths import ensure_paths


class XAUAProApp:
    def __init__(self) -> None:
        ensure_paths()
        self.cfg = get_config()
        self.cfg.ensure_default_user()
        self.root = tk.Tk()
        self.root.title("XAU AI PRO v1.2.0 - Trading Desk")
        self.root.configure(bg=Theme.BG)
        self.root.geometry(f"{self.cfg.get('window', 'width', default=1280)}x{self.cfg.get('window', 'height', default=800)}")
        if self.cfg.get("window", "maximized", default=False):
            self.root.state("zoomed")

        self.robot = MT5Robot()
        self.market = MarketData(provider=self.cfg.get("market", "provider", default="auto"))
        self.tabs: dict[str, Any] = {}
        self._current_tab = ""
        self._running = True

        self._build_login()

    def _build_login(self) -> None:
        self.login_frame = tk.Frame(self.root, bg=Theme.BG)
        self.login_frame.pack(fill="both", expand=True)
        box = tk.Frame(self.login_frame, bg=Theme.CARD, highlightbackground=Theme.BORDER,
                       highlightthickness=1, width=360, height=340)
        box.pack(expand=True)
        box.pack_propagate(False)
        tk.Label(box, text="XAU AI PRO", bg=Theme.CARD, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 22, "bold")).pack(pady=(40, 8))
        tk.Label(box, text="Login", bg=Theme.CARD, fg=Theme.PRIMARY,
                 font=(Theme.FONT_FAMILY, 10)).pack(pady=(0, 20))
        tk.Label(box, text="Usuario", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).pack(anchor="w", padx=40, pady=(8, 2))
        self.entry_user = tk.Entry(box, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                   relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1, width=32)
        self.entry_user.pack(padx=40, pady=2)
        tk.Label(box, text="Senha", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).pack(anchor="w", padx=40, pady=(12, 2))
        self.entry_pass = tk.Entry(box, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                   relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1,
                                   width=32, show="*")
        self.entry_pass.pack(padx=40, pady=2)
        self.entry_pass.bind("<Return>", lambda e: self._do_login())
        tk.Button(box, text="Entrar", command=self._do_login, bg=Theme.PRIMARY, fg=Theme.TEXT,
                  font=(Theme.FONT_FAMILY, 10, "bold"), relief="flat", cursor="hand2",
                  width=20, height=2).pack(pady=24)
        self.login_status = tk.Label(box, text="", bg=Theme.CARD, fg=Theme.DANGER, font=(Theme.FONT_FAMILY, 9))
        self.login_status.pack()

    def _do_login(self) -> None:
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get()
        if self.cfg.authenticate(user, pwd):
            self.cfg.set_session(user)
            self.login_frame.destroy()
            self._build_main()
        else:
            self.login_status.configure(text="Usuario ou senha invalidos")

    def _build_main(self) -> None:
        self.sidebar = Sidebar(self.root, on_navigate=self._navigate)
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(self.root, bg=Theme.BG)
        self.content.pack(side="right", fill="both", expand=True)

        self.header = tk.Frame(self.content, bg=Theme.BG, height=56)
        self.header.pack(fill="x", padx=24, pady=(12, 0))
        self.header.pack_propagate(False)
        self.header_title = tk.Label(self.header, text="Dashboard", bg=Theme.BG, fg=Theme.TEXT,
                                     font=(Theme.FONT_FAMILY, 16, "bold"))
        self.header_title.pack(side="left")
        self.status_label = tk.Label(self.header, text="Pronto", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                                     font=(Theme.FONT_FAMILY, 9))
        self.status_label.pack(side="right")

        self.tab_container = tk.Frame(self.content, bg=Theme.BG)
        self.tab_container.pack(fill="both", expand=True)

        self.tabs["dashboard"] = DashboardTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["market"] = MarketTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["positions"] = PositionsTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["robot"] = RobotTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["training"] = TrainingTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["assistant"] = AssistantTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["tools"] = ToolsTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["integrations"] = IntegrationsTab(self.tab_container, self.robot, self.market, self._set_status)
        self.tabs["subgraph"] = SubgraphTab(self.tab_container, self)
        self.tabs["settings"] = SettingsTab(self.tab_container, self.robot, self.market, self._set_status)

        for key in self.tabs:
            self.tabs[key].frame.pack_forget()

        self._navigate("dashboard")
        self._start_threads()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _navigate(self, key: str) -> None:
        if self._current_tab and self._current_tab in self.tabs:
            self.tabs[self._current_tab].frame.pack_forget()
        self._current_tab = key
        self.tabs[key].frame.pack(fill="both", expand=True)
        self.sidebar.set_active(key)
        titles = {
            "dashboard": "Dashboard",
            "market": "Mercado",
            "positions": "Carteira",
            "robot": "Controle do Robo",
            "training": "Treinamento IA",
            "assistant": "Assistente",
            "tools": "Ferramentas",
            "integrations": "Integracoes",
            "subgraph": "Subgraph",
            "settings": "Configuracoes",
        }
        self.header_title.configure(text=titles.get(key, key))

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)
        self.sidebar.set_status(text, Theme.TEXT_SECONDARY)

    def _start_threads(self) -> None:
        threading.Thread(target=self._auto_refresh, daemon=True).start()
        if self.cfg.get("learning", "enabled", default=True):
            get_learning_engine().start_scheduler()
        if self.cfg.get("mt5", "auto_connect", default=True):
            threading.Thread(target=self.robot.connect, daemon=True).start()
        self.tabs["market"].start_auto_refresh()

    def _auto_refresh(self) -> None:
        while self._running:
            try:
                if self._current_tab == "dashboard":
                    self.root.after(0, self.tabs["dashboard"].refresh)
                elif self._current_tab == "positions":
                    self.root.after(0, self.tabs["positions"].refresh)
                elif self._current_tab == "robot":
                    self.root.after(0, self.tabs["robot"].check_ea)
                time.sleep(10)
            except Exception:
                time.sleep(10)

    def _on_close(self) -> None:
        if messagebox.askyesno("Sair", "Deseja realmente fechar o XAU AI PRO?"):
            self._running = False
            self.tabs["market"].stop_auto_refresh()
            get_learning_engine().stop_scheduler()
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

