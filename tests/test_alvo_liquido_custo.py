# -*- coding: utf-8 -*-
"""Alvo liquido de custo: movimento que nao paga o spread nao e direcao.

MEDIDO 22/10/2026: o rotulo antigo chamava de COMPRA qualquer alta acima de
0,4 ATR, mesmo quando essa alta era menor que o custo de entrar e sair. O
modelo aprendia a perseguir movimento que o operador nunca recebe. Aqui estao
os dois lados: o caso que deve virar NEUTRO e a prova negativa de que, sem
custo, ele era COMPRA.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from Python.ai import train_v2 as t


def _serie_degrau(n: int = 300, passo: float = 1000.6, inicio_degrau: int = 250) -> pd.DataFrame:
    """Preco parado em 1000 e um degrau de +0,06% no fim da serie."""
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    close = np.full(n, 1000.0)
    close[inicio_degrau:] = passo
    return pd.DataFrame(
        {
            "Time": idx, "Symbol": "EURUSD",
            "Open": close, "High": close, "Low": close, "Close": close,
            "Volume": 100.0,
            "Spread": 40.0,
            "ATR": 1.0,
            "ADX": 20.0, "RSI": 50.0,
            "KCI_VD": 0.0, "KCI_MAIN": 0.0, "KDI_PLUS": 0.0, "KDI_MINUS": 0.0,
        }
    )


def test_movimento_menor_que_o_custo_vira_neutro():
    base = t.construir_features(t.reamostrar(_serie_degrau(), "M5"))
    custo = t.custo_rel_de_spread(base, ponto=0.01)
    com_custo = t.construir_target(base, 1, custo_rel=custo)
    linha = com_custo.index[249]
    assert com_custo.loc[linha, "Target"] == 1, (
        "alta de 0,06% com custo de 0,04% do preco deveria ser NEUTRA"
    )


def test_prova_negativa_sem_custo_o_mesmo_movimento_e_compra():
    base = t.construir_features(t.reamostrar(_serie_degrau(), "M5"))
    sem_custo = t.construir_target(base, 1)
    linha = sem_custo.index[249]
    assert sem_custo.loc[linha, "Target"] == 2, (
        "sem custo o degrau de 0,06% era classificado como COMPRA; se isto "
        "reprovar, o teste acima nao esta medindo o custo"
    )


def test_movimento_grande_continua_direcao_mesmo_com_custo():
    base = t.construir_features(t.reamostrar(_serie_degrau(passo=1020.0), "M5"))
    custo = t.custo_rel_de_spread(base, ponto=0.01)
    d = t.construir_target(base, 1, custo_rel=custo)
    assert d.loc[d.index[249], "Target"] == 2


def test_custo_rel_usa_ponto_e_nao_numero_de_pontos():
    base = t.construir_features(t.reamostrar(_serie_degrau(), "M5"))
    # 40 pontos x 0,01 = 0,40 de preco; sobre Close 1000 = 0,0004.
    assert t.custo_rel_de_spread(base, ponto=0.01).iloc[0] == 0.0004
    # O mesmo Spread com ponto 0,001 vale 10x menos: a unidade importa.
    assert t.custo_rel_de_spread(base, ponto=0.001).iloc[0] == 0.00004


def test_sem_coluna_spread_o_custo_e_zero():
    base = t.construir_features(t.reamostrar(_serie_degrau(), "M5")).drop(columns=["Spread"])
    assert float(t.custo_rel_de_spread(base, ponto=0.01).abs().max()) == 0.0
