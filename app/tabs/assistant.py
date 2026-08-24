"""
Aba Assistente IA (chat simplificado).
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class AssistantTab:
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
        tk.Label(header, text="Assistente IA", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")

        card = Card(self.frame, title="Conversa")
        card.pack(fill="both", expand=True, padx=24, pady=10)
        self.chat = tk.Text(card.body, bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 10),
                            relief="flat", wrap="word", state="disabled", height=20)
        self.chat.pack(fill="both", expand=True, padx=8, pady=8)
        input_frame = tk.Frame(card.body, bg=Theme.CARD)
        input_frame.pack(fill="x", padx=8, pady=8)
        self.entry = tk.Entry(input_frame, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                              relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1,
                              font=(Theme.FONT_FAMILY, 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        self.entry.bind("<Return>", lambda e: self.send())
        PrimaryButton(input_frame, text="Enviar", command=self.send, width=10).pack(side="left", padx=4)
        SecondaryButton(input_frame, text="Limpar", command=self.clear, width=10).pack(side="left", padx=4)

        self.add_message("Assistente", "Ola! Sou o assistente do XAU AI PRO. Pergunte sobre o mercado, o robo ou o treinamento.")

    def add_message(self, sender: str, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{sender}: {text}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.add_message("Voce", text)
        self.entry.delete(0, "end")
        reply = self._generate_reply(text)
        self.add_message("Assistente", reply)
        self.on_status("Mensagem enviada ao assistente")

    def clear(self) -> None:
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")

    def _generate_reply(self, text: str) -> str:
        t = text.lower()
        if "conectar" in t or "mt5" in t:
            return "Va em 'Robo MT5' e clique em 'Conectar MT5'. Certifique-se de que o MetaTrader 5 esta aberto."
        if "trein" in t:
            return "Na aba 'IA / Treino', clique em 'Treinar + Predizer' para atualizar o modelo. O agendador automatico tambem esta disponivel."
        if "lote" in t or "risco" in t:
            return "Use a aba 'Configuracoes' para ajustar lote, risco percentual, SL e TP."
        if "pre" in t or "mercado" in t:
            return "A aba 'Mercado' mostra cotacoes em tempo real de spot e futuros."
        return "Entendido. Estou monitorando os mercados. Use as abas para acessar dashboard, mercado, carteira e robo."
