# -*- coding: utf-8 -*-
"""Barra lateral compacta e recolhível do XAU_AI_PRO.

Design:
  - Recolhida por padrão (faixa de ícones à esquerda); expande ao passar o
    mouse (hover) mostrando os rótulos.
  - Itens de navegação: Painel, Mercado, Robô, Assistente e Configuração,
    cada qual com ícone próprio e destaque do item ativo.
  - Mantém apenas marca, versão e um indicador compacto de estado — sem os
    textos institucionais redundantes (execução assistida, risco monitorado,
    trilha de auditoria).
  - Navegação também por teclado (Up/Down/Enter) quando a lateral tem foco.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.theme.mexc import Theme

# (chave, rótulo, ícone)
NAV_ITEMS: list[tuple[str, str, str]] = [
    ("dashboard", "Painel", "📊"),
    ("market", "Mercado", "📈"),
    ("charts", "Gráficos", "📉"),
    ("robot", "Robô", "🤖"),
    ("tester", "Strategy Tester", "🧪"),
    ("vision", "Visão do Robô", "👁️"),
    ("system", "Configuração", "⚙️"),
]

COLLAPSED_WIDTH = 74
EXPANDED_WIDTH = Theme.SIDEBAR_WIDTH  # 260


class SidebarItem(tk.Frame):
    """Item de navegação da lateral: ícone (+ rótulo quando expandido)."""

    def __init__(self, parent, key: str, label: str, icon: str,
                 command: Callable[[str], None]) -> None:
        super().__init__(parent, bg=Theme.PANEL, cursor="hand2")
        self.key = key
        self.label = label
        self.icon = icon
        self.command = command
        self.active = False

        self.body = tk.Frame(self, bg=Theme.PANEL)
        self.body.pack(fill="x", padx=6, pady=2)
        self.icon_lbl = tk.Label(
            self.body, text=icon, bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 14), width=3, anchor="center"
        )
        self.icon_lbl.pack(side="left", pady=8)
        self.text_lbl = tk.Label(
            self.body, text=label, bg=Theme.PANEL, fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 11), anchor="w"
        )
        self.text_lbl.pack(side="left", padx=(4, 12))

        for w in (self, self.body, self.icon_lbl, self.text_lbl):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", lambda e: self._on_enter())
            w.bind("<Leave>", lambda e: self._on_leave())

    def _on_click(self, _event=None) -> None:
        self.command(self.key)

    def _on_enter(self) -> None:
        if not self.active:
            self._set_bg(Theme.CARD_HOVER, hover=True)

    def _on_leave(self) -> None:
        if not self.active:
            self._set_bg(Theme.PANEL, hover=False)

    def _set_bg(self, bg, hover: bool) -> None:
        for w in (self, self.body, self.icon_lbl, self.text_lbl):
            w.configure(bg=bg)
        fg = Theme.TEXT if hover or not self.active else Theme.TEXT_SECONDARY
        self.icon_lbl.configure(fg=Theme.PRIMARY if self.active else fg)
        self.text_lbl.configure(fg=Theme.TEXT if self.active else fg)

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            for w in (self, self.body, self.icon_lbl, self.text_lbl):
                w.configure(bg=Theme.CARD)
            self.icon_lbl.configure(fg=Theme.PRIMARY)
            self.text_lbl.configure(fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 11, "bold"))
        else:
            for w in (self, self.body, self.icon_lbl, self.text_lbl):
                w.configure(bg=Theme.PANEL)
            self.icon_lbl.configure(fg=Theme.TEXT_SECONDARY)
            self.text_lbl.configure(fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 11))

    def show_text(self, visible: bool) -> None:
        """Mostra/oculta o rótulo (expansão por hover)."""
        if visible:
            self.text_lbl.pack(side="left", padx=(4, 12))
        else:
            self.text_lbl.pack_forget()
        self.text_lbl.configure(
            font=(Theme.FONT_FAMILY, 11, "bold") if self.active and visible
            else (Theme.FONT_FAMILY, 11)
        )
class Sidebar(tk.Frame):
    """Barra lateral compacta e recolhível com ícones de navegação."""

    def __init__(self, parent, on_navigate: Callable[[str], None], **kwargs) -> None:
        super().__init__(parent, bg=Theme.PANEL, width=COLLAPSED_WIDTH, **kwargs)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self._expanded = False
        self._hidden = False
        # Larguras por estado (False=recolhida, True=expandida). O grip de
        # arraste atualiza o estado atual e a escolha fica persistente.
        self._widths: dict[bool, int] = {False: COLLAPSED_WIDTH, True: EXPANDED_WIDTH}
        self._items: dict[str, SidebarItem] = {}
        self._order = [key for key, _label, _icon in NAV_ITEMS]
        self._index: dict[str, int] = {k: i for i, (k, _l, _i) in enumerate(NAV_ITEMS)}

        # ---- Marca + versão (compacto) ---------------------------------
        logo = tk.Frame(self, bg=Theme.PANEL)
        logo.pack(fill="x", pady=(14, 6))
        self.logo_label = tk.Label(logo, text="XAU", bg=Theme.PANEL,
                                   fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 16, "bold"))
        self.logo_label.pack(anchor="w", padx=16)
        self.brand_label = tk.Label(logo, text="v1.2.0", bg=Theme.PANEL,
                                    fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8))
        self.brand_label.pack(anchor="w", padx=16)
        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill="x", padx=10, pady=8)

        # ---- Navegação -------------------------------------------------
        nav = tk.Frame(self, bg=Theme.PANEL)
        nav.pack(fill="both", expand=True)
        for key, label, icon in NAV_ITEMS:
            item = SidebarItem(nav, key, label, icon, self._navigate)
            item.pack(fill="x")
            self._items[key] = item

        # ---- Rodapé: indicador compacto de estado -----------------------
        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill="x", padx=10, pady=8)
        self.footer_status = tk.Label(
            self, text="● offline", bg=Theme.PANEL, fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9), anchor="w", padx=16
        )
        self.footer_status.pack(fill="x", side="bottom", pady=(0, 14))

        # ---- Expansão por hover (MANUTIDA SEM ESCONDER AO SAIR DO MOUSE) ----
        #self.bind("<Enter>", self._on_enter_self)
        #self.bind("<Leave>", self._on_leave_self)
        #for w in (logo, nav, self.brand_label, self.logo_label, self.footer_status):
        #    w.bind("<Enter>", self._on_enter_self)
        #    w.bind("<Leave>", self._on_leave_self)

        # ---- Lado aberto/fechado por botao ☰ (so pode diminuir ou aumentar)
        self.bind("<Button-1>", self._on_toggle_click)

        # ---- Navegação por teclado (quando a lateral tem foco) ----------
        self._selected_idx = 0
        self.bind("<Up>", self._key_up)
        self.bind("<Down>", self._key_down)
        self.bind("<Return>", self._key_enter)
        self.bind("<space>", self._key_enter)

        # ---- Alça de redimensionamento (arraste para diminuir/aumentar) --
        self.grip = tk.Frame(self, bg=Theme.BORDER, width=4,
                             cursor="sb_h_double_arrow")
        self.grip.pack(side="right", fill="y")
        self.grip.bind("<B1-Motion>", self._on_grip_drag)
        self.grip.bind("<Double-Button-1>", self._on_grip_reset)

    # ------------------------------------------------------------------
    def _navigate(self, key: str) -> None:
        self.on_navigate(key)

    # ------------------------------------------------------------------
    # Botão ☰: alterna entre expansão (completo) e mini (ícones compactos)
    # (so pode diminuir ou aumentar, sem hover collapse)
    # ------------------------------------------------------------------
    def _on_toggle_click(self, _event=None) -> None:
        """Alterna aba aberta/fechada por clique no botao (hover sem efeito)."""
        if self._expanded:
            self.set_expanded(False)
        else:
            self.set_expanded(True)

    def _on_enter_self(self, _event=None) -> None:
        self.set_expanded(True)

    def _on_leave_self(self, _event=None) -> None:
        self.set_expanded(False)

    def set_expanded(self, expanded: bool) -> None:
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self.configure(width=self._widths[expanded])
        for _key, item in self._items.items():
            item.show_text(expanded)
        if expanded:
            self.brand_label.configure(text="v1.2.0 · Trading Desk")
            self.logo_label.configure(text="XAU AI PRO")
        else:
            self.brand_label.configure(text="v1.2.0")
            self.logo_label.configure(text="XAU")

    # ------------------------------------------------------------------
    def set_active(self, key: str) -> None:
        for k, item in self._items.items():
            item.set_active(k == key)
        try:
            self._selected_idx = self._index.get(key, 0)
        except Exception:
            pass

    def set_status(self, text: str, color: str = Theme.TEXT_MUTED) -> None:
        status = str(text or "")
        prefix = "" if status.startswith(("●", "○")) else "● "
        self.footer_status.configure(text=f"{prefix}{status}", fg=color)

    # ------------------------------------------------------------------
    # Navegação por teclado
    # ------------------------------------------------------------------
    def _key_up(self, _event=None) -> None:
        self._selected_idx = (self._selected_idx - 1) % len(self._order)
        self._highlight_sel()

    def _key_down(self, _event=None) -> None:
        self._selected_idx = (self._selected_idx + 1) % len(self._order)
        self._highlight_sel()

    def _key_enter(self, _event=None) -> None:
        self._navigate(self._order[self._selected_idx])

    def _highlight_sel(self) -> None:
        target = self._order[self._selected_idx]
        for key, item in self._items.items():
            item.configure(bg=Theme.CARD_HOVER if key == target else Theme.PANEL)

    # ------------------------------------------------------------------
    # Exibir/esconder a lateral (botao hamburger) e redimensionar (grip)
    # ------------------------------------------------------------------
    def toggle(self) -> bool:
        """Esconde ou mostra a lateral. Retorna True se ficou VISÍVEL."""
        if self._hidden:
            self.pack(side="left", fill="y")
            self._hidden = False
        else:
            self.pack_forget()
            self._hidden = True
        return not self._hidden

    @property
    def is_hidden(self) -> bool:
        return self._hidden

    MIN_WIDTH = 56
    MAX_WIDTH = 420

    def _on_grip_drag(self, event) -> None:
        """Arraste da alça: define a largura do estado atual (com limites)."""
        try:
            new_w = int(event.x_root - self.winfo_rootx())
        except Exception:
            return
        new_w = max(self.MIN_WIDTH, min(self.MAX_WIDTH, new_w))
        # Evita reconfigurar a cada pixel sem mudança real.
        if new_w != self._widths[self._expanded]:
            self._widths[self._expanded] = new_w
            self.configure(width=new_w)

    def _on_grip_reset(self, _event=None) -> None:
        """Duplo clique na alça: volta à largura padrão do estado atual."""
        default = COLLAPSED_WIDTH if not self._expanded else EXPANDED_WIDTH
        self._widths[self._expanded] = default
        self.configure(width=default)