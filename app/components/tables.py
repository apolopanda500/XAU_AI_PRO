"""
Tabelas estilo exchange MEXC usando Treeview customizado.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from app.theme.mexc import Theme


class MexcTreeview(ttk.Treeview):
    """Treeview com estilo MEXC escuro."""

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
        style.configure(
            "Mexc.Treeview",
            background=Theme.CARD,
            foreground=Theme.TEXT,
            fieldbackground=Theme.CARD,
            bordercolor=Theme.BORDER,
            borderwidth=0,
            rowheight=32,
            font=(Theme.FONT_FAMILY, 10),
        )
        style.configure(
            "Mexc.Treeview.Heading",
            background=Theme.PANEL,
            foreground=Theme.TEXT_SECONDARY,
            bordercolor=Theme.BORDER,
            borderwidth=0,
            font=(Theme.FONT_FAMILY, 9, "bold"),
        )
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
    """Tabela de mercado com colunas padrao."""

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
        self.tree.tag_configure("up", foreground=Theme.CHART_UP)
        self.tree.tag_configure("down", foreground=Theme.CHART_DOWN)


class PositionTable(ScrollableTable):
    """Tabela de posicoes abertas."""

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


class HistoryTable(ScrollableTable):
    """Tabela de historico de trades."""

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
