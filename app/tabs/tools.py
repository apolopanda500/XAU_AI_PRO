"""
Aba Ferramentas do app XAU_AI_PRO.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class ToolsTab:
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
        tk.Label(header, text="Ferramentas", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")

        # Calculadora de lote
        lot_card = Card(self.frame, title="Calculadora de Lote")
        lot_card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(lot_card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Saldo", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, padx=4, pady=4)
        self.entry_balance = tk.Entry(form, width=14, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                      relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_balance.grid(row=0, column=1, padx=4)
        tk.Label(form, text="Risco %", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=2, padx=4)
        self.entry_risk = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                   relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_risk.insert(0, "1.0")
        self.entry_risk.grid(row=0, column=3, padx=4)
        tk.Label(form, text="SL pontos", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=4, padx=4)
        self.entry_sl_points = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                        relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_sl_points.insert(0, "300")
        self.entry_sl_points.grid(row=0, column=5, padx=4)
        tk.Label(form, text="Ponto ($)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=6, padx=4)
        self.entry_point = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                    relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_point.insert(0, "0.01")
        self.entry_point.grid(row=0, column=7, padx=4)
        PrimaryButton(form, text="Calcular", command=self.calc_lot, width=10).grid(row=0, column=8, padx=8)
        self.lot_result = tk.Label(form, text="Lote = --", bg=Theme.CARD, fg=Theme.PRIMARY,
                                   font=(Theme.FONT_FAMILY, 11, "bold"))
        self.lot_result.grid(row=1, column=0, columnspan=9, pady=8)

        # Notas diarias
        notes_card = Card(self.frame, title="Notas Diarias")
        notes_card.pack(fill="both", expand=True, padx=24, pady=10)
        self.notes = tk.Text(notes_card.body, bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 10),
                             relief="flat", wrap="word", height=10)
        self.notes.pack(fill="both", expand=True, padx=8, pady=8)
        SecondaryButton(notes_card.body, text="Salvar notas", command=self.save_notes, width=14).pack(anchor="e", padx=8, pady=8)

    def calc_lot(self) -> None:
        try:
            balance = float(self.entry_balance.get())
            risk = float(self.entry_risk.get()) / 100.0
            sl_points = float(self.entry_sl_points.get())
            point_value = float(self.entry_point.get())
            if sl_points <= 0 or point_value <= 0 or balance <= 0:
                raise ValueError
            risk_amount = balance * risk
            lot = risk_amount / (sl_points * point_value)
            self.lot_result.configure(text=f"Lote = {lot:.2f}")
            self.on_status(f"Lote calculado: {lot:.2f}")
        except ValueError:
            self.lot_result.configure(text="Lote = valores invalidos")

    def save_notes(self) -> None:
        text = self.notes.get("1.0", "end")
        self.on_status(f"Notas salvas ({len(text)} caracteres)")
