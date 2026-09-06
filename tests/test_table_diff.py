"""Testes de atualização diferencial da tabela (MexcTreeview.set_rows).

Confirma que preço/PNL alterado, inclusão e remoção de linhas preservam a
seleção e a fração de yview, sem destruir/recriar o conteúdo desnecessariamente.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.tables import MexcTreeview


def _make(root_tk):
    columns = [("s", "Simbolo", 100), ("p", "Preco", 110)]
    tv = MexcTreeview(root_tk, columns=columns, height=10)
    tv.pack(fill="both", expand=True)
    root_tk.update_idletasks()
    return tv


def test_set_rows_preserva_selecao_e_rolagem(root_tk):
    tv = _make(root_tk)
    rows = [[f"S{i}", f"1.{i:03d}"] for i in range(60)]
    tv.set_rows(rows, tags=["even"] * len(rows))
    root_tk.update_idletasks()
    # seleciona uma linha no meio
    target = "S30"
    for item in tv.get_children():
        if tv.item(item, "values")[0] == target:
            tv.selection_set(item)
            break
    before_sel = [tv.item(i, "values") for i in tv.selection()]
    tv.yview_moveto(0.5)
    root_tk.update_idletasks()
    view_before = tv.yview()[0]

    # Atualização por diferença: mesmo nº de linhas, preço alterado
    rows2 = [[f"S{i}", f"2.{i:03d}" if i != 30 else f"99.{i:03d}"] for i in range(60)]
    tv.set_rows(rows2, tags=["even"] * len(rows2))
    root_tk.update_idletasks()

    after_sel = [tv.item(i, "values") for i in tv.selection()]
    assert any(v[0] == target for v in after_sel), "seleção não preservada"
    assert abs(tv.yview()[0] - view_before) < 0.02, "rolagem saltou"


def test_set_rows_inclusao_e_remocao_linhas(root_tk):
    tv = _make(root_tk)
    rows = [[f"S{i}", f"1.{i:03d}"] for i in range(10)]
    tv.set_rows(rows)
    root_tk.update_idletasks()
    assert len(tv.get_children()) == 10

    # Remove 4, adiciona 2 -> 8 linhas
    rows2 = [[f"S{i}", f"2.{i:03d}"] for i in range(4, 12)]
    tv.set_rows(rows2)
    root_tk.update_idletasks()
    assert len(tv.get_children()) == 8


def test_set_rows_nao_recria_sem_necessidade(root_tk):
    tv = _make(root_tk)
    rows = [[f"S{i}", f"1.{i:03d}"] for i in range(10)]
    tv.set_rows(rows)
    root_tk.update_idletasks()
    first_pass_items = list(tv.get_children())
    # Mesmas linhas (sem mudança) -> mesmo conjunto de itens
    tv.set_rows(rows)
    root_tk.update_idletasks()
    assert list(tv.get_children()) == first_pass_items