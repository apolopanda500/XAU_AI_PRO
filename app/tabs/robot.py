"""
Aba de controle do Robo MT5.
"""
from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, DangerButton, AccentButton
from app.config_manager import get_config
from app.learning_engine import get_learning_engine
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class RobotTab:
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
        tk.Label(header, text="Controle do Robo MT5", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")

        self.status_card = Card(self.frame, title="Status do Robo")
        self.status_card.pack(fill="x", padx=24, pady=10)
        self.status_text = tk.Label(self.status_card.body, text="Desconectado", bg=Theme.CARD,
                                    fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 11),
                                    anchor="w", justify="left")
        self.status_text.pack(fill="x", padx=8, pady=8)
        btn_row = tk.Frame(self.status_card.body, bg=Theme.CARD)
        btn_row.pack(fill="x", padx=8, pady=8)
        PrimaryButton(btn_row, text="Conectar MT5", command=self.connect, width=16).pack(side="left", padx=4)
        SecondaryButton(btn_row, text="Desconectar", command=self.disconnect, width=16).pack(side="left", padx=4)
        SecondaryButton(btn_row, text="Verificar EA", command=self.check_ea, width=16).pack(side="left", padx=4)

        action_card = Card(self.frame, title="Acoes Manuais")
        action_card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(action_card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Simbolo", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, padx=4)
        self.entry_symbol = tk.Entry(form, width=12, bg=Theme.PANEL, fg=Theme.TEXT,
                                     insertbackground=Theme.TEXT, relief="flat",
                                     highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_symbol.insert(0, get_config().get("trading", "default_symbol", default="XAUUSD"))
        self.entry_symbol.grid(row=0, column=1, padx=4)
        tk.Label(form, text="Lote", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=2, padx=4)
        self.entry_volume = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                     insertbackground=Theme.TEXT, relief="flat",
                                     highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_volume.insert(0, "0.01")
        self.entry_volume.grid(row=0, column=3, padx=4)
        tk.Label(form, text="SL", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=4, padx=4)
        self.entry_sl = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                 insertbackground=Theme.TEXT, relief="flat",
                                 highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_sl.insert(0, "0")
        self.entry_sl.grid(row=0, column=5, padx=4)
        tk.Label(form, text="TP", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=6, padx=4)
        self.entry_tp = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                 insertbackground=Theme.TEXT, relief="flat",
                                 highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_tp.insert(0, "0")
        self.entry_tp.grid(row=0, column=7, padx=4)
        AccentButton(form, text="Comprar", command=self.buy, width=10).grid(row=0, column=8, padx=4)
        DangerButton(form, text="Vender", command=self.sell, width=10).grid(row=0, column=9, padx=4)

        ai_card = Card(self.frame, title="Aprendizado Continuo")
        ai_card.pack(fill="x", padx=24, pady=10)
        ai_row = tk.Frame(ai_card.body, bg=Theme.CARD)
        ai_row.pack(fill="x", padx=8, pady=8)
        PrimaryButton(ai_row, text="Treinar agora", command=self.train_now, width=16).pack(side="left", padx=4)
        SecondaryButton(ai_row, text="Sincronizar predicoes", command=self.sync_predictions, width=20).pack(side="left", padx=4)
        self.ai_status = tk.Label(ai_row, text="Parado", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                                  font=(Theme.FONT_FAMILY, 10))
        self.ai_status.pack(side="left", padx=16)


    def connect(self) -> None:
        cfg_path = get_config().get("mt5", "terminal_path", default="")
        if self.robot.connect(path=cfg_path if cfg_path else None):
            self.on_status("MT5 conectado")
        else:
            self.on_status(f"Falha MT5: {self.robot.last_error}")
        self.check_ea()

    def disconnect(self) -> None:
        self.robot.disconnect()
        self.on_status("MT5 desconectado")
        self.check_ea()

    def check_ea(self) -> None:
        if not self.robot.connected:
            self.status_text.configure(text="Desconectado", fg=Theme.TEXT_MUTED)
            return
        ea = self.robot.is_ea_active()
        lines = [
            f"Terminal: {'conectado' if ea.get('connected') else 'desconectado'}",
            f"Posicoes com magic: {ea.get('positions_with_magic', 0)}",
            f"Predicoes recentes: {'sim' if ea.get('predictions_recent') else 'nao'}",
            f"Motivo: {ea.get('reason')}",
        ]
        self.status_text.configure(text="\n".join(lines),
                                   fg=Theme.SUCCESS if ea.get("active") else Theme.WARNING)

    def buy(self) -> None:
        self._send("BUY")

    def sell(self) -> None:
        self._send("SELL")

    def _send(self, side: str) -> None:
        symbol = self.entry_symbol.get().strip()
        try:
            volume = float(self.entry_volume.get())
            sl = float(self.entry_sl.get())
            tp = float(self.entry_tp.get())
        except ValueError:
            self.on_status("Valores invalidos")
            return
        res = self.robot.send_order(symbol, side, volume, sl=sl, tp=tp)
        if res.get("ok"):
            self.on_status(f"Ordem {side} {symbol} enviada, ticket {res['ticket']}")
        else:
            self.on_status(f"Erro ordem: {res.get('error')}")

    def train_now(self) -> None:
        self.ai_status.configure(text="Treinando...", fg=Theme.WARNING)
        self.on_status("Iniciando treinamento...")
        def run():
            result = get_learning_engine().full_cycle()
            self.ai_status.configure(text="Concluido" if result.get("ok") else "Erro",
                                     fg=Theme.SUCCESS if result.get("ok") else Theme.DANGER)
            self.on_status(result.get("predict", {}).get("sync", {}).get("error", "Treinamento finalizado"))
        threading.Thread(target=run, daemon=True).start()

    def sync_predictions(self) -> None:
        res = self.robot.sync_predictions()
        if res.get("ok"):
            self.on_status(f"{res.get('copied', 0)} predicoes sincronizadas")
        else:
            self.on_status(f"Erro sync: {res.get('error')}")

