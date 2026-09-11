# -*- coding: utf-8 -*-
"""
Aba Pesquisa: busca global no XAU_AI_PRO (MCP, agentes, chats, ativos, calendario).
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class SearchTab:
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
        TabBanner(self.frame, "search")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Pesquisa Global", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Busque em MCP, agentes, chats, ativos e calendario",
                 bg=Theme.BG, fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 9)).pack(side="left", padx=12)

        card = Card(self.frame, title="Buscar no aplicativo")
        card.pack(fill="x", padx=24, pady=10)

        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=8)
        self.entry = tk.Entry(row, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                              relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1,
                              font=(Theme.FONT_FAMILY, 11))
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        self.entry.bind("<Return>", lambda e: self.search())
        PrimaryButton(row, text="Buscar", command=self.search, width=10).pack(side="left", padx=4)
        SecondaryButton(row, text="Limpar", command=self.clear, width=10).pack(side="left", padx=4)
        SecondaryButton(row, text="Atualizar índice", command=self.refresh_index, width=15).pack(side="left", padx=4)

        # Resultado
        res_card = Card(self.frame, title="Resultados")
        res_card.pack(fill="both", expand=True, padx=24, pady=10)
        self.text = tk.Text(res_card.body, bg=Theme.PANEL, fg=Theme.TEXT,
                            font=(Theme.FONT_FAMILY, 10), relief="flat", wrap="word",
                            state="disabled", height=24)
        self.text.pack(fill="both", expand=True, padx=8, pady=8)

        self._dica()

    def _print(self, txt: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", txt + "\n")
        self.text.configure(state="disabled")
        self.text.see("end")

    def _dica(self) -> None:
        self._print("Digite um termo (ex.: xau, mercado, posicao, FOMC, MCP) e clique em Buscar.\n"
                    "A pesquisa cobre: MCP servers, agentes/abas, chats (memoria), ativos e calendario.")

    def search(self) -> None:
        q = self.entry.get().strip()
        if not q:
            self.on_status("Informe um termo de busca")
            return
        import threading
        self.on_status("Pesquisando...")
        threading.Thread(target=self._worker, args=(q,), daemon=True).start()

    def refresh_index(self) -> None:
        """Reconstrói o índice em background e informa o resultado."""
        import threading
        self.on_status("Atualizando índice global...")
        threading.Thread(target=self._index_worker, daemon=True).start()

    def _index_worker(self) -> None:
        from app.search_hub import search_all
        result = search_all("")
        self.frame.after(0, lambda: self.on_status(f"Índice atualizado: {result.get('total', 0)} itens"))

    def _worker(self, q: str) -> None:
        from app.search_hub import search_all
        r = search_all(q)
        self.frame.after(0, lambda: self._apply(r))

    def _apply(self, r: dict) -> None:
        self.clear_text()
        self._print(f"=== Resultados para '{r.get('query')}' ({r.get('total')} itens) ===\n")
        sections = [
            ("🛠️ MCP", r.get("mcp", [])),
            ("🤖 Agentes / Abas", r.get("agentes", [])),
            ("💬 Chats / Memoria", r.get("chats", [])),
            ("📈 Ativos", r.get("ativos", [])),
            ("📅 Calendario", r.get("calendario", [])),
        ]
        for titulo, items in sections:
            self._print(f"\n[{titulo}]")
            if not items:
                self._print("  (nenhum resultado)")
                continue
            for it in items:
                self._print(f"  • {it.get('nome', '')} — {it.get('descricao', '')[:110]}")
        self.on_status(f"Pesquisa '{r.get('query')}': {r.get('total')} resultados")

    def clear(self) -> None:
        self.entry.delete(0, "end")
        self.clear_text()

    def clear_text(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")