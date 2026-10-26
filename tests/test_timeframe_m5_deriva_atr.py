# -*- coding: utf-8 -*-
"""M5 nao pula a derivacao de indicadores (22/10/2026).

MEDIDO: `reamostrar("M5")` devolvia o DataFrame direto, sem passar pela
derivacao de ATR/ADX/RSI. Funcionava enquanto o dataset trazia ATR pronto;
um dataset com ATR zerado (o export do MT5) chegava ao target com `ATR = 0`,
`atr_seguro` caia no piso de 1e-9, o rotulo perdia a faixa NEUTRA e a
acuracia de duas classes (0,50) era comparada com o palpite de tres (0,33).
Resultado: edge falso de +0,16 em M5.

A trava mede o caminho inteiro: serie M5 com indicadores zerados tem de sair
com ATR derivado e rotulo de TRES classes. A prova negativa e a fonte que
traz o ATR real - ela nao pode ser sobrescrita.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from Python.ai import train_v2 as t  # noqa: E402


def serie_m5(linhas: int = 600, atr: float = 0.0) -> pd.DataFrame:
    """Serie M5 deterministica com tendencia, para o ATR nao ser degenerado."""
    rng = np.random.default_rng(7)
    preco = 2000.0 + np.cumsum(rng.normal(0, 0.8, linhas))
    abertura = preco
    fechamento = preco + rng.normal(0, 0.3, linhas)
    alto = np.maximum(abertura, fechamento) + rng.uniform(0.1, 1.2, linhas)
    baixo = np.minimum(abertura, fechamento) - rng.uniform(0.1, 1.2, linhas)
    return pd.DataFrame(
        {
            "Time": pd.date_range("2026-01-01", periods=linhas, freq="5min"),
            "Symbol": "XAUUSD",
            "Open": abertura,
            "High": alto,
            "Low": baixo,
            "Close": fechamento,
            "Volume": rng.integers(50, 500, linhas).astype(float),
            "Spread": 20.0,
            "ATR": atr,
            "ADX": 0.0,
            "RSI": 0.0,
            "KCI_VD": 0.0,
            "KCI_MAIN": 0.0,
            "KDI_PLUS": 0.0,
            "KDI_MINUS": 0.0,
        }
    )


class TestM5DerivaIndicadores:
    def test_atr_zerado_e_derivado_no_proprio_m5(self) -> None:
        saida = t.reamostrar(serie_m5(atr=0.0), "M5")
        assert float(saida["ATR"].abs().sum()) > 0.0, "M5 saiu com ATR zerado"
        assert float(saida["ADX"].abs().sum()) > 0.0, "M5 saiu com ADX zerado"
        assert float(saida["RSI"].abs().sum()) > 0.0, "M5 saiu com RSI zerado"

    def test_rotulo_m5_mantem_as_tres_classes(self) -> None:
        # Prova do defeito observado: sem ATR o `norm` explode e a classe
        # NEUTRA desaparece do rotulo, inflando a acuracia contra um palpite
        # de tres classes que nao existe na pratica.
        base = t.construir_target(t.reamostrar(serie_m5(atr=0.0), "M5"), 10)
        classes = set(base["Target"].unique())
        assert classes == {0, 1, 2}, f"rotulo M5 sem as tres classes: {classes}"
        neutro = float((base["Target"] == 1).mean())
        assert 0.05 < neutro < 0.90, f"faixa neutra degenerada: {neutro:.3f}"

    def test_PROVA_NEGATIVA_fonte_com_atr_real_nao_e_sobrescrita(self) -> None:
        entrada = serie_m5(atr=3.75)
        saida = t.reamostrar(entrada, "M5")
        assert np.allclose(saida["ATR"].to_numpy(), 3.75), "o ATR da fonte foi trocado"

    def test_timeframe_agregado_continua_derivando(self) -> None:
        saida = t.reamostrar(serie_m5(atr=0.0), "H1")
        assert float(saida["ATR"].abs().sum()) > 0.0
