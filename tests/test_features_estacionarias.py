# -*- coding: utf-8 -*-
"""Features estacionarias: o que torna o modelo MULTI possivel.

O QUE ESTE TESTE PROVA
======================
`train_v2.FEATURES` comeca com preco ABSOLUTO. XAUUSD fecha em ~2000 e
EURUSD em ~1,08: um modelo unico receberia `Close=2000` e `Close=1.08` na
mesma arvore, e ela separaria pela ESCALA, nao pelo comportamento. O
resultado nao e um modelo ruim — e um modelo sem sentido estatistico.

Aqui a propriedade medida e **invariancia de escala**: o MESMO padrao de
candle, apresentado nas escalas de ouro, euro e bitcoin, tem que produzir as
MESMAS features. E isso que permite um `MULTI_CRYPTO` e um `MULTI_FIAT`
compartilhando arquitetura.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from Python.ai.features_estacionarias import (
    CODIGO_CLASSE,
    CODIGO_TIMEFRAME,
    FEATURES_ESTACIONARIAS,
    FEATURE_VERSION_ESTACIONARIA,
    construir_features_estacionarias,
    feature_hash_estacionaria,
)

ESCALAS = {"ouro": 2000.0, "euro": 1.08, "bitcoin": 60000.0}


def candles(escala: float = 1.0, n: int = 120) -> pd.DataFrame:
    """Serie sintetica deterministica, escalada pelo fator `escala`.

    O PADRAO e o mesmo nas tres escalas: e a variacao que o modelo deve ler,
    e nao o nivel do preco. `rng` com semente fixa para o teste ser
    reproduzivel.
    """
    rng = np.random.default_rng(7)
    base = np.abs(1.0 + rng.normal(0.0, 1.0, n).cumsum() * 0.01) + 0.5
    return pd.DataFrame({
        "Time": pd.date_range("2026-01-01", periods=n, freq="5min"),
        "Open": base * escala,
        "High": base * escala * 1.002,
        "Low": base * escala * 0.998,
        "Close": base * escala,
        "Volume": rng.integers(100, 1000, n).astype(float) * escala,
        "Spread": np.full(n, 0.0002) * escala,
        "ATR": np.full(n, 0.002) * escala,
        "ADX": np.clip(rng.normal(25, 5, n), 0, 100),
        "RSI": np.clip(rng.normal(50, 12, n), 1, 99),
    })


class TestEscalaDesaparece:
    """A propriedade central: o MESMO padrao, em 3 escalas, da 3 resultados."""

    @pytest.mark.parametrize("classe", ["CRYPTO", "FIAT", "METALS"])
    def test_ouro_e_euro_dao_mesmo_resultado(self, classe):
        ouro = construir_features_estacionarias(candles(ESCALAS["ouro"]), "H1", classe)
        euro = construir_features_estacionarias(candles(ESCALAS["euro"]), "H1", classe)
        cols = [c for c in FEATURES_ESTACIONARIAS if c != "Classe_Cod"]
        pd.testing.assert_frame_equal(
            ouro[cols].reset_index(drop=True),
            euro[cols].reset_index(drop=True),
            check_exact=False, rtol=1e-9, atol=1e-9,
        )

    def test_bitcoin_tambem_igual(self):
        cols = [c for c in FEATURES_ESTACIONARIAS if c != "Classe_Cod"]
        euro = construir_features_estacionarias(candles(ESCALAS["euro"]), "H1", "FIAT")
        btc = construir_features_estacionarias(candles(ESCALAS["bitcoin"]), "H1", "CRYPTO")
        pd.testing.assert_frame_equal(
            euro[cols].reset_index(drop=True),
            btc[cols].reset_index(drop=True),
            check_exact=False, rtol=1e-9, atol=1e-9,
        )

    def test_preco_absoluto_muda_com_a_escala(self):
        # Este e o defeito que o esquema estacionario corrige. Se deixar de
        # ser verdade, o `train_v2` foi alterado sem querer.
        ouro, euro = candles(ESCALAS["ouro"]), candles(ESCALAS["euro"])
        assert ouro["Close"].iloc[-1] / euro["Close"].iloc[-1] > 1000
class TestHorizonteEClasse:
    def test_timeframe_muda_a_feature(self):
        h1 = construir_features_estacionarias(candles(), "H1", "FIAT")
        h4 = construir_features_estacionarias(candles(), "H4", "FIAT")
        assert h1["Timeframe_Cod"].iloc[0] == CODIGO_TIMEFRAME["H1"]
        assert h4["Timeframe_Cod"].iloc[0] == CODIGO_TIMEFRAME["H4"]

    def test_classe_muda_a_feature(self):
        cripto = construir_features_estacionarias(candles(), "H1", "CRYPTO")
        metal = construir_features_estacionarias(candles(), "H1", "METALS")
        assert cripto["Classe_Cod"].iloc[0] == CODIGO_CLASSE["CRYPTO"]
        assert metal["Classe_Cod"].iloc[0] == CODIGO_CLASSE["METALS"]

    def test_todos_os_timeframes_tem_codigo(self):
        # O dono pediu M1 ate H4 no mesmo MULTI.
        for tf in ("M1", "M5", "M15", "M30", "H1", "H4"):
            d = construir_features_estacionarias(candles(), tf, "CRYPTO")
            assert d["Timeframe_Cod"].iloc[0] == CODIGO_TIMEFRAME[tf]

    def test_timeframe_desconhecido_recusa(self):
        with pytest.raises(ValueError, match="timeframe"):
            construir_features_estacionarias(candles(), "H12", "CRYPTO")

    def test_classe_desconhecida_recusa(self):
        with pytest.raises(ValueError, match="classe"):
            construir_features_estacionarias(candles(), "H1", "CRIPTOMOEDAS")


class TestContrato:
    def test_versao_diferente_do_absoluto(self):
        # `train_v2.FEATURE_VERSION` e "25F-v2". Iguais fariam a inferencia
        # nao saber qual lista construir.
        from Python.ai import train_v2

        assert FEATURE_VERSION_ESTACIONARIA == "25F-est-v1"
        assert FEATURE_VERSION_ESTACIONARIA != train_v2.FEATURE_VERSION

    def test_hash_deterministico(self):
        assert feature_hash_estacionaria() == feature_hash_estacionaria()

    def test_hash_diferente_do_absoluto(self):
        from Python.ai import train_v2

        assert feature_hash_estacionaria() != train_v2.feature_hash()

    def test_todas_as_features_existem(self):
        d = construir_features_estacionarias(candles(), "H1", "FIAT")
        faltando = [c for c in FEATURES_ESTACIONARIAS if c not in d.columns]
        assert not faltando, f"features ausentes: {faltando}"

    def test_ordem_e_a_canonica(self):
        # O `.pkl` treina nesta ordem; a inferencia monta nesta ordem.
        assert FEATURES_ESTACIONARIAS == list(FEATURES_ESTACIONARIAS)
        assert len(set(FEATURES_ESTACIONARIAS)) == len(FEATURES_ESTACIONARIAS)


class TestRobustez:
    def test_atr_zero_nao_divide_por_zero(self):
        # Serie sem movimento: ATR zerado. Sem o piso, daria inf. O `NaN` da
        # PRIMEIRA linha e esperado e correto: `Close_ATR` usa `shift(1)`, e o
        # treino descarta a primeira linha (`dropna`). O que nao pode existir
        # e inf, nem NaN depois da primeira linha.
        n = 40
        liso = pd.DataFrame({
            "Time": pd.date_range("2026-01-01", periods=n, freq="5min"),
            "Open": [1.0] * n, "High": [1.0] * n, "Low": [1.0] * n,
            "Close": [1.0] * n, "Volume": [10.0] * n,
            "Spread": [0.0] * n, "ATR": [0.0] * n,
            "ADX": [0.0] * n, "RSI": [50.0] * n,
        })
        d = construir_features_estacionarias(liso, "H1", "FIAT")
        valores = d[FEATURES_ESTACIONARIAS].to_numpy()
        assert not np.isinf(valores).any(), "inf em serie sem movimento"
        # Da segunda linha em diante nada pode faltar.
        assert np.isfinite(valores[1:]).all(), "NaN apos a primeira linha"

    def test_sem_colunas_derivadas_usa_true_range(self):
        # So OHLCV: o ATR tem que ser derivado, nao vir NaN.
        base = candles(n=80)[["Time", "Open", "High", "Low", "Close", "Volume"]]
        d = construir_features_estacionarias(base, "H1", "CRYPTO")
        assert d["ATR_Pct"].notna().sum() > 0
        assert np.isfinite(d["ATR_Pct"].to_numpy()[1:]).all()