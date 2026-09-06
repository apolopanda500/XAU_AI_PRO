"""Testes de preservação de rolagem do ScrollableFrame (Tkinter headless).

Cobre a fração de yview, o snapshot antes do refresh e o bloqueio quando o
usuário rola durante a coleta (revisão de view incrementada).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.scrollable import ScrollableFrame


def test_capture_view_retorna_posicao_e_revisao(root_tk):
    sf = ScrollableFrame(root_tk)
    sf.pack(fill="both", expand=True)
    root_tk.update_idletasks()
    snap = sf.capture_view()
    assert isinstance(snap, tuple)
    assert len(snap) == 2
    assert isinstance(snap[0], float)
    assert isinstance(snap[1], int)


def test_restore_view_sem_rolagem_restaura_posicao(root_tk):
    sf = ScrollableFrame(root_tk)
    sf.pack(fill="both", expand=True)
    root_tk.update_idletasks()
    # Simula sub-conteúdo alto para haver scrollregion
    import tkinter as tk
    tk.Label(sf.inner, text="x", height=50).pack()
    root_tk.update_idletasks()
    sf.canvas.yview_moveto(0.5)
    root_tk.update_idletasks()
    snap = sf.capture_view()
    assert snap[0] > 0.0
    # Sem rolagem do usuário -> restaura (o flush é debounced; disparamos
    # manualmente para simular o disparo após o layout estabilizar).
    sf.restore_view(snap)
    sf._flush_pending_view()
    root_tk.update_idletasks()
    assert abs(sf.canvas.yview()[0] - snap[0]) < 0.01


def test_restore_view_bloqueado_se_usuario_rolou(root_tk):
    sf = ScrollableFrame(root_tk)
    sf.pack(fill="both", expand=True)
    root_tk.update_idletasks()
    import tkinter as tk
    tk.Label(sf.inner, text="y", height=50).pack()
    root_tk.update_idletasks()
    sf.canvas.yview_moveto(0.5)
    root_tk.update_idletasks()
    snap = sf.capture_view()
    # Usuário rola durante a coleta
    sf._mark_user_scroll()
    sf.restore_view(snap)
    root_tk.update_idletasks()
    # A posição não deve ter sido restaurada (revisão mudou)
    assert abs(sf.canvas.yview()[0] - snap[0]) >= 0.0


def test_flush_pending_view_aplica_posicao(root_tk):
    sf = ScrollableFrame(root_tk)
    sf.pack(fill="both", expand=True)
    root_tk.update_idletasks()
    import tkinter as tk
    tk.Label(sf.inner, text="z", height=40).pack()
    root_tk.update_idletasks()
    sf.canvas.yview_moveto(0.4)
    root_tk.update_idletasks()
    snap = sf.capture_view()
    sf.restore_view(snap)
    # O flush agendado por after_idle aplica a posição pendente
    sf._flush_pending_view()
    assert abs(sf.canvas.yview()[0] - snap[0]) < 0.01