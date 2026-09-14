# -*- coding: utf-8 -*-
"""Testes da barra superior (TopNav): destinos sincronizados, sem travas."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.topnav import TopNav, TOP_ITEMS


def test_topnav_tem_todos_os_destinos(root_tk):
    nav = TopNav(root_tk, on_navigate=lambda k: None)
    nav.pack(fill="x")
    root_tk.update_idletasks()
    assert set(nav._buttons.keys()) == {k for k, _ in TOP_ITEMS}
    assert "positions" in nav._buttons and "charts" in nav._buttons
    assert "audit" in nav._buttons and "connections" in nav._buttons


def test_topnav_clique_navega_e_marca_ativo(root_tk):
    calls: list[str] = []
    nav = TopNav(root_tk, on_navigate=lambda k: calls.append(k))
    nav.pack(fill="x")
    root_tk.update_idletasks()
    nav._click("market")
    assert calls == ["market"]
    nav.set_active("market")
    assert nav._active == "market"
    # Clique repetido no ativo e ignorado (anti-trava, sem empilhar).
    nav._click("market")
    assert calls == ["market"]


def test_topnav_sem_combinedtab_aninhado():
    import pathlib
    core = (ROOT / "app" / "core.py").read_text(encoding="utf-8")
    assert "CombinedTab(self.tab_container" not in core
    assert '"positions": lambda' in core and '"charts": lambda' in core
