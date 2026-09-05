"""
Sidebar de navegacao PRO estilo TradingView para o app XAU_AI_PRO.
Agrupa abas relacionadas em secoes colapsaveis com indicadores de status.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.theme.mexc import Theme


class SidebarButton(tk.Button):
    """Botao de menu lateral com icone/emoji, indicador ativo e badge de status."""

    def __init__(self, parent, text: str, icon: str, command: Callable, **kwargs):
        super().__init__(
            parent, text=f"{icon}  {text}", anchor="w",
            bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 11), relief="flat", cursor="hand2",
            borderwidth=0, highlightthickness=0, padx=20, pady=10,
            command=command, **kwargs
        )
        self.active = False
        self.bind("<Enter>", lambda e: self._on_enter())
        self.bind("<Leave>", lambda e: self._on_leave())

    def _on_enter(self) -> None:
        if not self.active:
            self.config(bg=Theme.CARD_HOVER, fg=Theme.TEXT)

    def _on_leave(self) -> None:
        if not self.active:
            self.config(bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY)

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            self.config(bg=Theme.CARD, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 11, "bold"))
        else:
            self.config(bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 11))


class SidebarGroup(tk.Frame):
    """Grupo colapsavel de botoes no sidebar."""

    def __init__(self, parent, title: str, icon: str,
                 items: list[tuple[str, str, str]],
                 on_navigate: Callable[[str], None], default_open: bool = False):
        super().__init__(parent, bg=Theme.PANEL)
        self.on_navigate = on_navigate
        self._buttons: dict[str, SidebarButton] = {}
        self._open = default_open

        self.header = tk.Frame(self, bg=Theme.PANEL, cursor="hand2")
        self.header.pack(fill="x")
        self.header.bind("<Button-1>", lambda e: self.toggle())
        self.indicator = tk.Label(self.header, text="v" if default_open else ">",
                                  bg=Theme.PANEL, fg=Theme.TEXT_MUTED,
                                  font=(Theme.FONT_FAMILY, 8), cursor="hand2")
        self.indicator.pack(side="left", padx=(16, 0))
        self.indicator.bind("<Button-1>", lambda e: self.toggle())
        self.title_label = tk.Label(
            self.header,
            text=f"{icon}  {title}",
            bg=Theme.PANEL,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 11, "bold"),
            anchor="w",
            cursor="hand2",
        )
        self.title_label.pack(side="left", padx=8, pady=10)
        self.title_label.bind("<Button-1>", lambda e: self.toggle())

        self.body = tk.Frame(self, bg=Theme.PANEL)
        if default_open:
            self.body.pack(fill="x")

        for key, label, item_icon in items:
            btn = SidebarButton(self.body, label, item_icon,
                                command=lambda k=key: self._navigate(k))
            btn.pack(fill="x")
            self._buttons[key] = btn

    def toggle(self) -> None:
        self._open = not self._open
        self.indicator.config(text="v" if self._open else ">")
        if self._open:
            self.body.pack(fill="x")
        else:
            self.body.pack_forget()

    def _navigate(self, key: str) -> None:
        self.on_navigate(key)

    def set_active(self, key: str) -> None:
        for k, btn in self._buttons.items():
            btn.set_active(k == key)


class Sidebar(tk.Frame):
    """Menu lateral com logo, grupos de navegacao e rodape."""

    def __init__(self, parent, on_navigate: Callable[[str], None], **kwargs):
        super().__init__(parent, bg=Theme.PANEL, width=240, **kwargs)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self._groups: dict[str, SidebarGroup] = {}

        # Logo
        logo_frame = tk.Frame(self, bg=Theme.PANEL, height=96, cursor="hand2")
        logo_frame.pack(fill="x", pady=(20, 12))
        logo_frame.bind("<Button-1>", lambda e: self._show_about())
        tk.Frame(logo_frame, bg=Theme.PRIMARY, height=3).pack(fill="x", padx=20, pady=(0, 14))
        self.logo_title = tk.Label(
            logo_frame, text="XAU AI PRO", bg=Theme.PANEL, fg=Theme.TEXT,
            font=(Theme.FONT_FAMILY, 18, "bold"), cursor="hand2"
        )
        self.logo_title.pack(anchor="w", padx=20)
        self.logo_title.bind("<Button-1>", lambda e: self._show_about())
        self.logo_sub = tk.Label(
            logo_frame, text="Trading Desk v1.2.0", bg=Theme.PANEL, fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9), cursor="hand2"
        )
        self.logo_sub.pack(anchor="w", padx=20)
        self.logo_sub.bind("<Button-1>", lambda e: self._show_about())
        self.logo_meta = tk.Label(
            logo_frame, text="MT5 sync  |  audit trail  |  professional mode",
            bg=Theme.PANEL, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)
        )
        self.logo_meta.pack(anchor="w", padx=20, pady=(6, 0))

        # Separador
        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill="x", padx=16, pady=10)

        # Grupos de navegação em área rolável; logo e rodapé permanecem fixos.
        nav = tk.Frame(self, bg=Theme.PANEL)
        nav.pack(fill="both", expand=True)
        nav_canvas = tk.Canvas(nav, bg=Theme.PANEL, highlightthickness=0, bd=0)
        nav_scroll = tk.Scrollbar(nav, orient="vertical", command=nav_canvas.yview)
        nav_body = tk.Frame(nav_canvas, bg=Theme.PANEL)
        nav_window = nav_canvas.create_window((0, 0), window=nav_body, anchor="nw")
        nav_canvas.configure(yscrollcommand=nav_scroll.set)
        nav_canvas.pack(side="left", fill="both", expand=True)
        nav_scroll.pack(side="right", fill="y")
        nav_body.bind("<Configure>", lambda e: nav_canvas.configure(scrollregion=nav_canvas.bbox("all")))
        nav_canvas.bind("<Configure>", lambda e: nav_canvas.itemconfigure(nav_window, width=e.width))
        nav_canvas.bind("<Enter>", lambda e: nav_canvas.bind_all("<MouseWheel>", lambda ev: nav_canvas.yview_scroll(-1 if ev.delta > 0 else 1, "units"), add="+"))
        nav_canvas.bind("<Leave>", lambda e: nav_canvas.unbind_all("<MouseWheel>"))

        self._sections = [
            ("principal", "Principal", "TR", [
                ("dashboard", "Dashboard", "DB"),
                ("market", "Mercado e Graficos", "MK"),
                ("robot", "Robo MT5", "EA"),
            ], True),
            ("ia", "IA Lab", "AI", [
                ("assistant", "Chat, Treino e Busca", "IA"),
            ], False),
            ("analise", "Analise", "AN", [
                ("audit", "Auditoria", "AU"),
            ], False),
            ("sistema", "Sistema", "SY", [
                ("integrations", "Integracoes", "IN"),
                ("system", "Monitor e Configuracoes", "MS"),
            ], False),
        ]

        for gid, title, icon, items, default_open in self._sections:
            grp = SidebarGroup(nav_body, title, icon, items, on_navigate,
                               default_open=default_open)
            grp.pack(fill="x", pady=2)
            self._groups[gid] = grp

        # Rodape
        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill="x", padx=16, pady=10)
        self.footer_status = tk.Label(
            self, text="Status: offline", bg=Theme.PANEL, fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9), anchor="w", padx=20
        )
        self.footer_status.pack(fill="x", side="bottom", pady=10)

        # Rodape institucional
        self.dev_frame = tk.Frame(self, bg=Theme.PANEL)
        self.dev_frame.pack(fill="x", side="bottom", pady=(0, 10))
        tk.Label(self.dev_frame, text="Workspace sincronizado com MT5 e MCP",
                 bg=Theme.PANEL, fg=Theme.TEXT_MUTED,
                 font=(Theme.FONT_FAMILY, 8)).pack(anchor="w", padx=20)
        self.dev_contact = tk.Label(
            text="Figma, GitLab, Slack e auditoria operacional",
            bg=Theme.PANEL, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 8)
        )
        self.dev_contact.pack(anchor="w", padx=20)

    def _show_about(self) -> None:
        top = tk.Toplevel(self, bg=Theme.BG)
        top.title("Sobre - XAU AI PRO")
        top.geometry("420x260")
        top.transient(self)
        top.grab_set()

        frame = tk.Frame(top, bg=Theme.BG, padx=24, pady=24)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="XAU AI PRO", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(anchor="w")
        tk.Label(frame, text="Trading Desk v1.2.0", bg=Theme.BG, fg=Theme.PRIMARY,
                 font=(Theme.FONT_FAMILY, 11)).pack(anchor="w", pady=(0, 12))

        lines = [
            "Plataforma desktop para acompanhamento do MetaTrader 5,",
            "analise de mercado, treinamento local de modelos de IA",
            "e execucao de estrategias de trading com governanca.",
            "",
            "Desenvolvido por: Henrique Carvalho",
            "Contato: rickjax123@gmail.com | 55 (21983158911)",
            "",
            "Trading envolve risco. Valide estrategias em backtest",
            "e conta demo antes de operar com capital real.",
        ]
        for line in lines:
            tk.Label(frame, text=line, bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9), justify="left").pack(anchor="w")

        btn = tk.Button(frame, text="Fechar", bg=Theme.PRIMARY, fg=Theme.TEXT,
                        font=(Theme.FONT_FAMILY, 10, "bold"), relief="flat",
                        cursor="hand2", command=top.destroy)
        btn.pack(anchor="e", pady=(16, 0))


    def set_active(self, key: str) -> None:
        for grp in self._groups.values():
            grp.set_active(key)

    def set_status(self, text: str, color: str = Theme.TEXT_MUTED) -> None:
        self.footer_status.configure(text=text, fg=color)
