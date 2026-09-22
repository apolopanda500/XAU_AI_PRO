# -*- coding: utf-8 -*-
"""
Tela de Login do XAU_AI_PRO - producao real com contas reais e sessao demo.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.components.cards import Card
from app.components.button import PrimaryButton, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.theme.mexc import Theme

class LoginScreen(tk.Frame):
    """Tela de login com opcoes: login normal, conta demo e cadastro."""

    def __init__(self, parent, on_login_success: Callable[[str], None],
                 on_switch_to_settings: Callable[[], None]) -> None:
        super().__init__(parent, bg=Theme.BG)
        self._on_success = on_login_success
        self._on_settings = on_switch_to_settings
        self._build()

    def _build(self) -> None:
        self._bg_canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                                     relief="flat", bg=Theme.BG)
        self._bg_canvas.pack(fill="both", expand=True)
        header = tk.Frame(self._bg_canvas, bg=Theme.BG_SECONDARY)
        header.pack(fill="x", padx=40, pady=(60, 8))
        tk.Label(header, text="XAU AI PRO", bg=Theme.BG_SECONDARY,
                 fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 32, "bold"),
                 anchor="w").pack(side="left")
        tk.Label(header, text="v1.2.3  ·  Trading Desk PRO",
                 bg=Theme.BG_SECONDARY, fg=Theme.TEXT_MUTED,
                 font=(Theme.FONT_FAMILY, 11)).pack(side="left", padx=(12, 0))
        self.card = Card(self._bg_canvas, title="Acesso à Plataforma")
        self.card.pack(fill="x", padx=40, pady=(8, 16))
        form = tk.Frame(self.card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=16, pady=(16, 4))
        tk.Label(form, text="Usuário", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 10)).grid(row=0, column=0, padx=4, sticky="w")
        self._user_var = tk.StringVar()
        self._user_entry = tk.Entry(form, width=30, bg=Theme.PANEL, fg=Theme.TEXT,
                                    relief="flat", highlightbackground=Theme.BORDER,
                                    highlightthickness=1, insertbackground=Theme.TEXT,
                                    textvariable=self._user_var)
        self._user_entry.grid(row=0, column=1, padx=4, pady=4)
        self._user_entry.bind("<Return>", lambda _: self._do_login())
        tk.Label(form, text="Senha", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 10)).grid(row=1, column=0, padx=4, sticky="w", pady=(4, 0))
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(form, width=30, bg=Theme.PANEL, fg=Theme.TEXT,
                                    relief="flat", highlightbackground=Theme.BORDER,
                                    highlightthickness=1, insertbackground=Theme.TEXT,
                                    show="•", textvariable=self._pass_var)
        self._pass_entry.grid(row=1, column=1, padx=4, pady=(4, 0))
        self._pass_entry.bind("<Return>", lambda _: self._do_login())
        self._status_label = tk.Label(self.card.body, text="", bg=Theme.CARD,
                                       fg=Theme.DANGER, font=(Theme.FONT_FAMILY, 9),
                                       anchor="w")
        self._status_label.pack(fill="x", padx=16, pady=(8, 4))
