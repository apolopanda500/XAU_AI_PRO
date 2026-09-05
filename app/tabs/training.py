"""
Aba de Treinamento / IA.
"""
from __future__ import annotations

import json
import threading
import tkinter as tk
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.learning_engine import get_learning_engine
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme
from app.utils.paths import get_data_dir


class TrainingTab:
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
        TabBanner(self.frame, "training")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Treinamento IA", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")

        ctrl = Card(self.frame, title="Controles")
        ctrl.pack(fill="x", padx=24, pady=10)
        row = tk.Frame(ctrl.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=8)
        PrimaryButton(row, text="Treinar + Predizer", command=self.full_cycle, width=18).pack(side="left", padx=4)
        SecondaryButton(row, text="Treinar", command=self.train_only, width=12).pack(side="left", padx=4)
        SecondaryButton(row, text="Predizer", command=self.predict_only, width=12).pack(side="left", padx=4)
        SecondaryButton(row, text="Iniciar agendador", command=self.start_scheduler, width=18).pack(side="left", padx=4)
        AccentButton(row, text="Baixar modelos", command=self.download_models, width=16).pack(side="left", padx=4)

        cfg = Card(self.frame, title="Configuracao de Aprendizado")
        cfg.pack(fill="x", padx=24, pady=10)
        cfg_grid = tk.Frame(cfg.body, bg=Theme.CARD)
        cfg_grid.pack(fill="x", padx=8, pady=8)
        c = get_config()
        tk.Label(cfg_grid, text="Horario diario", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, padx=4, pady=4)
        self.entry_time = tk.Entry(cfg_grid, width=8, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                   relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_time.insert(0, c.get("learning", "daily_time", default="02:00"))
        self.entry_time.grid(row=0, column=1, padx=4, pady=4)
        tk.Label(cfg_grid, text="Intervalo (min)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=2, padx=4, pady=4)
        self.entry_interval = tk.Entry(cfg_grid, width=8, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                       relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_interval.insert(0, str(c.get("learning", "interval_minutes", default=60)))
        self.entry_interval.grid(row=0, column=3, padx=4, pady=4)
        SecondaryButton(cfg_grid, text="Salvar", command=self.save_config, width=10).grid(row=0, column=4, padx=12, pady=4)

        hist = Card(self.frame, title="Historico de Treinamentos")
        hist.pack(fill="both", expand=True, padx=24, pady=10)
        self.hist_text = tk.Text(hist.body, bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_MONO, 9),
                                 relief="flat", highlightthickness=0, wrap="word")
        self.hist_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.refresh_history()

    def _threaded(self, fn) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def full_cycle(self) -> None:
        self.on_status("Iniciando ciclo completo de treinamento...")
        self._threaded(lambda: self._show_result(get_learning_engine().full_cycle()))

    def train_only(self) -> None:
        self.on_status("Iniciando treinamento...")
        self._threaded(lambda: self._show_result(get_learning_engine().run_training()))

    def predict_only(self) -> None:
        self.on_status("Gerando predicoes...")
        self._threaded(lambda: self._show_result(get_learning_engine().run_prediction()))

    def download_models(self) -> None:
        self.on_status("Baixando modelos pre-treinados...")
        self._threaded(lambda: self._show_result(get_learning_engine().download_models()))

    def start_scheduler(self) -> None:
        get_learning_engine().start_scheduler()
        self.on_status("Agendador de aprendizado iniciado")
        self.refresh_history()

    def save_config(self) -> None:
        c = get_config()
        c.set("learning", "daily_time", value=self.entry_time.get())
        c.set("learning", "interval_minutes", value=int(self.entry_interval.get()))
        self.on_status("Configuracao salva")

    def refresh_history(self) -> None:
        try:
            path = get_data_dir() / "learning_history.json"
            if not path.exists():
                text = "Nenhum historico ainda."
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
                runs = data.get("runs", [])
                text = json.dumps(runs[-5:], indent=2, ensure_ascii=False) if runs else "Nenhum historico."
            self.hist_text.delete("1.0", "end")
            self.hist_text.insert("1.0", text)
        except Exception as e:
            self.hist_text.delete("1.0", "end")
            self.hist_text.insert("1.0", f"Erro: {e}")

    def _show_result(self, result: dict) -> None:
        ok = result.get("ok", False)
        msg = "Concluido" if ok else f"Erro: {result.get('error', '')}"
        self.on_status(msg)
        self.refresh_history()
