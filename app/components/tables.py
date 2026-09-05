"""
Tabelas PRO estilo terminal de trading (MetaTrader 5 / TradingView).
Cores de bid/ask, formatação condicional e cabeçalho estilizado.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from app.theme.mexc import Theme


class MexcTreeview(ttk.Treeview):
    """Treeview com estilo terminal de trading (fundo escuro, grid sutil)."""

    def __init__(self, parent, columns: list[tuple[str, str, int]], height: int = 14, **kwargs):
        col_ids = [c[0] for c in columns]
        super().__init__(
            parent, columns=col_ids, show="headings", height=height,
            **kwargs
        )
        self._setup_style()
        for cid, heading, width in columns:
            self.heading(cid, text=heading)
            self.column(cid, width=width, anchor="center")

    def _setup_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        # Grid/trading terminal look
        style.configure(
            "Mexc.Treeview",
            background=Theme.CARD_ALT,
            foreground=Theme.TEXT,
            fieldbackground=Theme.CARD_ALT,
            bordercolor=Theme.BORDER,
            borderwidth=0,
            rowheight=32,
            font=(Theme.FONT_MONO, 10),  # Mono para alinhamento numérico
        )
        # Cabeçalho estilo terminal
        style.configure(
            "Mexc.Treeview.Heading",
            background=Theme.PANEL,
            foreground=Theme.TEXT_SECONDARY,
            bordercolor=Theme.BORDER,
            borderwidth=1,
            font=(Theme.FONT_FAMILY, 9, "bold"),
        )
        # Linhas alternadas (zebra)
        style.map(
            "Mexc.Treeview",
            background=[("selected", Theme.CARD_HOVER)],
            foreground=[("selected", Theme.TEXT)],
        )
        self.configure(style="Mexc.Treeview")

    def clear(self) -> None:
        for item in self.get_children():
            self.delete(item)

    def set_rows(self, rows: list[list[Any]], tags: list[str] | None = None) -> None:
        self.clear()
        for i, row in enumerate(rows):
            tag = (tags[i] if tags and i < len(tags) else "")
            # Alternar cor de fundo (zebra striping)
            if not tag:
                tag = "even" if i % 2 == 0 else "odd"
            self.insert("", "end", values=row, tags=(tag,))


class ScrollableTable(tk.Frame):
    """Tabela com scrollbars."""

    def __init__(self, parent, columns: list[tuple[str, str, int]], height: int = 14, **kwargs):
        super().__init__(parent, bg=Theme.CARD, **kwargs)
        self.tree = MexcTreeview(self, columns=columns, height=height)
        self.tree.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vs.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vs.set)


class MarketTable(ScrollableTable):
    """Tabela de mercado com colunas padrão (bid/ask colors)."""

    def __init__(self, parent, height: int = 16, **kwargs):
        columns = [
            ("symbol", "Simbolo", 100),
            ("price", "Preco", 110),
            ("bid", "Bid", 100),
            ("ask", "Ask", 100),
            ("chg", "Variacao", 100),
            ("chg_pct", "% 24h", 80),
            ("spread", "Spread", 70),
            ("source", "Fonte", 70),
            ("time", "Hora", 70),
        ]
        super().__init__(parent, columns=columns, height=height, **kwargs)
        self.tree.tag_configure("up", foreground=Theme.BID)
        self.tree.tag_configure("down", foreground=Theme.ASK)
        self.tree.tag_configure("even", background=Theme.CARD_ALT)
        self.tree.tag_configure("odd", background=Theme.CARD)


class PositionTable(ScrollableTable):
    """Tabela de posições abertas (profit/loss colors)."""

    def __init__(self, parent, height: int = 12, **kwargs):
        columns = [
            ("ticket", "Ticket", 80),
            ("symbol", "Simbolo", 90),
            ("type", "Tipo", 60),
            ("volume", "Volume", 80),
            ("open", "Abertura", 100),
            ("current", "Atual", 100),
            ("sl", "SL", 80),
            ("tp", "TP", 80),
            ("profit", "Lucro", 100),
        ]
        super().__init__(parent, columns=columns, height=height, **kwargs)
        self.tree.tag_configure("profit", foreground=Theme.SUCCESS)
        self.tree.tag_configure("loss", foreground=Theme.DANGER)
        self.tree.tag_configure("buy", foreground=Theme.BID)
        self.tree.tag_configure("sell", foreground=Theme.ASK)
        self.tree.tag_configure("even", background=Theme.CARD_ALT)
        self.tree.tag_configure("odd", background=Theme.CARD)


class HistoryTable(ScrollableTable):
    """Tabela de histórico de trades."""

    def __init__(self, parent, height: int = 12, **kwargs):
        columns = [
            ("time", "Data/Hora", 140),
            ("ticket", "Ticket", 80),
            ("symbol", "Simbolo", 90),
            ("type", "Tipo", 60),
            ("volume", "Volume", 80),
            ("price", "Preco", 100),
            ("profit", "Resultado", 100),
        ]
        super().__init__(parent, columns=columns, height=height, **kwargs)
        self.tree.tag_configure("profit", foreground=Theme.SUCCESS)
        self.tree.tag_configure("loss", foreground=Theme.DANGER)
        self.tree.tag_configure("even", background=Theme.CARD_ALT)
        self.tree.tag_configure("odd", background=Theme.CARD)
