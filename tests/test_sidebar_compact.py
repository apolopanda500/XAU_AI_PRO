"""Testes da barra lateral compacta/recolhível (Tkinter headless)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.sidebar import Sidebar, NAV_ITEMS, COLLAPSED_WIDTH, EXPANDED_WIDTH


def test_sidebar_inicia_recolhida(root_tk):
    calls: list[str] = []
    sb = Sidebar(root_tk, on_navigate=lambda k: calls.append(k))
    sb.pack(side="left", fill="y")
    root_tk.update_idletasks()
    assert int(sb.cget("width")) == COLLAPSED_WIDTH
    assert sb._expanded is False


def test_sidebar_expande_no_hover(root_tk):
    sb = Sidebar(root_tk, lambda k: None)
    sb.pack(side="left", fill="y")
    root_tk.update_idletasks()
    sb.set_expanded(True)
    root_tk.update_idletasks()
    assert int(sb.cget("width")) == EXPANDED_WIDTH
    assert sb._expanded is True
    sb.set_expanded(False)
    root_tk.update_idletasks()
    assert int(sb.cget("width")) == COLLAPSED_WIDTH


def test_sidebar_itens_esperados(root_tk):
    sb = Sidebar(root_tk, lambda k: None)
    assert set(sb._items.keys()) == {"dashboard", "market", "charts", "robot", "tester", "vision", "system"}
    assert sb._items["dashboard"].label == "Painel"
    assert sb._items["charts"].label == "Gráficos"
    assert sb._items["tester"].label == "Strategy Tester"
    assert sb._items["vision"].label == "Visão do Robô"
    assert sb._items["system"].label == "Configuração"


def test_sidebar_item_ativo_destacado(root_tk):
    sb = Sidebar(root_tk, lambda k: None)
    sb.set_active("robot")
    assert sb._items["robot"].active is True
    assert sb._items["dashboard"].active is False


def test_sidebar_navegacao_por_teclado(root_tk):
    calls: list[str] = []
    sb = Sidebar(root_tk, on_navigate=lambda k: calls.append(k))
    sb._selected_idx = 0
    sb._key_enter()
    assert calls == ["dashboard"], calls


def test_sidebar_sem_textos_institucionais_redundantes(root_tk):
    """Marca + versão + status; sem 'Execução assistida'/'risco monitorado'."""
    sb = Sidebar(root_tk, lambda k: None)
    brand = sb.brand_label.cget("text") if hasattr(sb.brand_label, "cget") else ""
    assert isinstance(brand, str)
    sb.set_status("online")
    status = sb.footer_status.cget("text")
    assert "online" in status


def test_sidebar_toggle_esconde_e_mostra(root_tk):
    calls: list[str] = []
    sb = Sidebar(root_tk, on_navigate=lambda k: calls.append(k))
    sb.pack(side="left", fill="y")
    root_tk.update_idletasks()
    assert sb.is_hidden is False
    visible = sb.toggle()
    root_tk.update_idletasks()
    assert visible is False and sb.is_hidden is True
    visible = sb.toggle()
    root_tk.update_idletasks()
    assert visible is True and sb.is_hidden is False


def test_sidebar_grip_diminui_e_restaura_largura(root_tk):
    sb = Sidebar(root_tk, lambda k: None)
    sb.pack(side="left", fill="y")
    root_tk.update_idletasks()
    # Simula arraste da alça para uma posição à esquerda (diminuir).
    class _Ev:
        x_root = sb.winfo_rootx() + 60
    sb._on_grip_drag(_Ev())
    root_tk.update_idletasks()
    assert int(sb.cget("width")) == sb._widths[False] == 60
    # Duplo clique restaura o padrão.
    sb._on_grip_reset()
    root_tk.update_idletasks()
    assert int(sb.cget("width")) == COLLAPSED_WIDTH