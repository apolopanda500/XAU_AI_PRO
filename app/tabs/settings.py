"""
Aba Configuracoes do app XAU_AI_PRO.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class SettingsTab:
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
        tk.Label(header, text="Configuracoes", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")

        # MT5
        mt5_card = Card(self.frame, title="MetaTrader 5")
        mt5_card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(mt5_card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Caminho terminal", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.entry_terminal = tk.Entry(form, width=70, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                       relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_terminal.insert(0, get_config().get("mt5", "terminal_path", default=""))
        self.entry_terminal.grid(row=0, column=1, padx=4, pady=4)
        SecondaryButton(form, text="Procurar", command=self.browse_terminal, width=10).grid(row=0, column=2, padx=4)
        tk.Label(form, text="Magic Number", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4)
        self.entry_magic = tk.Entry(form, width=20, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                    relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_magic.insert(0, str(get_config().get("mt5", "magic_number", default=2026001)))
        self.entry_magic.grid(row=1, column=1, sticky="w", padx=4)

        # Trading
        trade_card = Card(self.frame, title="Trading")
        trade_card.pack(fill="x", padx=24, pady=10)
        tf = tk.Frame(trade_card.body, bg=Theme.CARD)
        tf.pack(fill="x", padx=8, pady=8)
        labels = [("Risco %", "risk_percent"), ("Max lote", "max_lot"),
                  ("SL pontos", "stop_loss_points"), ("TP pontos", "take_profit_points"),
                  ("Spread max", "max_spread_points"), ("Max DD %", "max_drawdown_pct")]
        self.trading_entries: dict[str, tk.Entry] = {}
        for i, (label, key) in enumerate(labels):
            tk.Label(tf, text=label, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=i//3, column=(i%3)*2, padx=4, pady=4, sticky="w")
            e = tk.Entry(tf, width=14, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                         relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
            e.insert(0, str(get_config().get("trading", key, default="")))
            e.grid(row=i//3, column=(i%3)*2+1, padx=4, pady=4, sticky="w")
            self.trading_entries[key] = e

        # Botoes
        btn_row = tk.Frame(self.frame, bg=Theme.BG)
        btn_row.pack(fill="x", padx=24, pady=20)
        PrimaryButton(btn_row, text="Salvar Configuracoes", command=self.save, width=22).pack(side="left", padx=4)
        AccentButton(btn_row, text="Testar Conexao MT5", command=self.test_mt5, width=20).pack(side="left", padx=8)

    def browse_terminal(self) -> None:
        path = tk.filedialog.askopenfilename(filetypes=[("Executavel", "*.exe")])
        if path:
            self.entry_terminal.delete(0, "end")
            self.entry_terminal.insert(0, path)

    def save(self) -> None:
        c = get_config()
        c.set("mt5", "terminal_path", value=self.entry_terminal.get())
        c.set("mt5", "magic_number", value=int(self.entry_magic.get()))
        for key, entry in self.trading_entries.items():
            try:
                c.set("trading", key, value=float(entry.get()))
            except ValueError:
                pass
        self.on_status("Configuracoes salvas")

    def test_mt5(self) -> None:
        if self.robot.connect():
            info = self.robot.account_info()
            if info:
                self.on_status(f"Conectado: {info['name']} | Saldo {info['balance']}")
            else:
                self.on_status("Conectado, mas sem info da conta")
        else:
            self.on_status(f"Falha conexao MT5: {self.robot.last_error}")
