# -*- coding: utf-8 -*-
"""Features ESTACIONARIAS para o modelo MULTI por classe.

POR QUE ISTO EXISTE (2026-10-02)
=================================
O dono pediu: *"cada modelo precisa ler todas corretoras ... forex ler usd
usdt usdc etc. mesma coisa as outras ... vai ficar mais simples e otimizado"*
e: *"modelos MULTI precisam operar todos os horarios; apenas os unitarios
serao separados por periodos"*.

O dataset medido tem 676.732 linhas em 17 simbolos, e as escalas sao
incomparaveis: XAUUSD ~2000, BTCUSD ~60.000, EURUSD ~1,08.

`train_v2.FEATURES` comeca com preco ABSOLUTO (`Open, High, Low, Close,
Volume, Spread`). Um modelo unico que recebe `Close=2000` do ouro e
`Close=1.08` do euro nao tem o que aprender: a arvore separa pela escala, nao
pelo comportamento. Nao e impreciso — e **sem sentido estatistico**.

A REGRA
=======
**TUDO vira razao do proprio ativo.** O que sobra e invariante a escala:

| Antes (absoluto) | Aqui (estacionario) |
|---|---|
| `Open, High, Low, Close` | `Open_ATR, High_ATR, Low_ATR, Close_ATR` |
| `Volume` | `Volume_Rel` |
| `Spread` | `Spread_ATR` |
| `ATR, ADX, RSI` | ja invariantes, mantidos |

O `Close_ATR` de um candle de ouro e o de um candle de euro passam a ter a
mesma interpretacao: "quantos ATR o preco se moveu".

O TIMEFRAME E A CLASSE ENTRAM COMO FEATURE
==========================================
O MULTI e um so por classe e opera M1 ate H4. O horizonte e a unica coisa
que **nao** esta na serie OHLCV, entao entra numerado — e nao one-hot,
porque 8 colunas esparsa por timeframe nao dao ganho em arvore.

O QUE NAO MUDA
==============
O `feature_version` muda (`25F-est-v1`). Os 36 modelos atuais usam
`25F-v2` e **continuam valendo**: sao artefatos com assinatura diferente, e
apagar trabalho valido seria perda, nao limpeza.
"""
from __future__ import annotations

import hashlib
from typing import Final

import numpy as np
import pandas as pd

#: Versao do conjunto. Diferente de `25F-v2` (absoluto) de proposito.
FEATURE_VERSION_ESTACIONARIA: Final[str] = "25F-est-v1"

#: Timeframe -> codigo numerico.
CODIGO_TIMEFRAME: Final[dict[str, int]] = {
    "M1": 1, "M5": 2, "M15": 3, "M30": 4,
    "H1": 5, "H4": 6, "D1": 7, "W1": 8,
}

#: Classe -> codigo numerico. O modelo ja sabe a classe, mas a feature deixa
#: explicito que metal nao se comporta como cripto e nao tem preco de forex.
CODIGO_CLASSE: Final[dict[str, int]] = {
    "CRYPTO": 1,
    "FIAT": 2,
    "METALS": 3,
    "INDICES": 4,
}

#: Ordem canonica. Nao embaralhar: o `.pkl` treina nesta ordem e a
#: inferencia monta nesta ordem. `feature_hash` detecta o descasamento.
FEATURES_ESTACIONARIAS: Final[list[str]] = [
    "Open_ATR", "High_ATR", "Low_ATR", "Close_ATR",
    "Volume_Rel", "Spread_ATR",
    "ATR_Pct", "ADX", "RSI",
    "KCI_VD_Inv", "KDI_Diff", "KCI_MAIN_Change",
    "Body_ATR", "Range_ATR", "UpperShadow_ATR", "LowerShadow_ATR",
    "RSI_Diff", "Close_Diff_Pct", "Volume_MA_Rel", "ADX_Change",
    "Timeframe_Cod", "Classe_Cod",
]

#: Piso do ATR para nao dividir por zero. `construir_target` usa a mesma
#: ordem de grandeza.
PISO_ATR: Final[float] = 1e-9


def feature_hash_estacionaria() -> str:
    """Hash do conjunto, para detectar drift entre treino e inferencia."""
    bruto = "|".join(FEATURES_ESTACIONARIAS) + "|" + str(sorted(CODIGO_CLASSE.items()))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16]


def _atr_seguro(atr: pd.Series) -> pd.Series:
    """ATR nunca zero nem negativo; o piso evita divisao por zero."""
    return atr.clip(lower=PISO_ATR)


def derivar_kci_estacionaria(df: pd.DataFrame) -> pd.DataFrame:
    """As 4 features KCI derivadas da propria serie OHLC.

    Igual a `train_v2.derivar_kci`, que ja explicava: no dataset as 4 colunas
    KCI vinham zeradas e o modelo aprendia com 7 das 25 features mortas. Aqui
    sao calculadas para nao repetir isso no esquema estacionario.
    """
    d = df.copy()
    hlc = (d["High"] + d["Low"] + d["Close"]) / 3.0

    # RCI do Williams: posicao do fechamento na faixa recente, em 0..1.
    maior = hlc.rolling(9, min_periods=1).max()
    menor = hlc.rolling(9, min_periods=1).min()
    faixa = (maior - menor).replace(0.0, np.nan)
    rci = ((hlc - menor) / faixa).fillna(0.5)
    d["KCI_MAIN"] = (rci - 0.5) * 100.0
    d["KCI_VD"] = d["KCI_MAIN"].diff().abs()

    # Momentum de Williams: posicao do fechamento na faixa de 14.
    maior_m = hlc.rolling(14, min_periods=1).max()
    menor_m = hlc.rolling(14, min_periods=1).min()
    faixa_m = (maior_m - menor_m).replace(0.0, np.nan)
    d["KDI_PLUS"] = ((hlc - menor_m) / faixa_m).fillna(0.5) * 100.0
    d["KDI_MINUS"] = 100.0 - d["KDI_PLUS"]
    return d


def _coluna(d: pd.DataFrame, nome: str, padrao: float) -> pd.Series:
    """Coluna existente ou serie com o padrao. Ausente nao vira zero mudo."""
    if nome in d.columns:
        return d[nome]
    return pd.Series(float(padrao), index=d.index)


def construir_features_estacionarias(
    df: pd.DataFrame,
    timeframe: str = "H1",
    classe: str = "CRYPTO",
) -> pd.DataFrame:
    """Monta as features estacionarias, ja com horizonte e classe.

    `df` precisa de `Time, Open, High, Low, Close, Volume` e, se houver,
    `Spread, ATR, ADX, RSI`. Ausente usa a conta derivavel (ATR pelo range,
    RSI neutro) — nunca zero silencioso.
    """
    tf = str(timeframe or "H1").strip().upper()
    cl = str(classe or "CRYPTO").strip().upper()
    if tf not in CODIGO_TIMEFRAME:
        raise ValueError(f"timeframe sem codigo: {tf!r}. Use {sorted(CODIGO_TIMEFRAME)}")
    if cl not in CODIGO_CLASSE:
        raise ValueError(f"classe sem codigo: {cl!r}. Use {sorted(CODIGO_CLASSE)}")

    d = derivar_kci_estacionaria(df)

    # ATR: usa a coluna do dataset quando existe; senao deriva do range, que
    # e a definicao classica de True Range.
    if "ATR" in d.columns:
        atr = _atr_seguro(d["ATR"])
    else:
        anterior = d["Close"].shift(1)
        true_range = pd.concat(
            [d["High"] - d["Low"], (d["High"] - anterior).abs(), (d["Low"] - anterior).abs()],
            axis=1,
        ).max(axis=1)
        atr = _atr_seguro(true_range.rolling(14, min_periods=1).mean())

    close = d["Close"].replace(0.0, np.nan)
    anterior = close.shift(1)

    # Preco em unidades de ATR: mesma escala para ouro, euro e bitcoin.
    d["Open_ATR"] = (d["Open"] - anterior) / atr
    d["High_ATR"] = (d["High"] - anterior) / atr
    d["Low_ATR"] = (d["Low"] - anterior) / atr
    d["Close_ATR"] = (d["Close"] - anterior) / atr

    # Volume contra a propria media: um pico significa a mesma coisa no
    # ativo de 60.000 e no de 1,08.
    vol = _coluna(d, "Volume", 0.0)
    vol_ma5 = vol.rolling(5, min_periods=1).mean().replace(0.0, np.nan)
    vol_ma50 = vol.rolling(50, min_periods=1).mean().replace(0.0, np.nan)
    d["Volume_Rel"] = (vol - vol_ma5) / vol_ma5
    d["Volume_MA_Rel"] = vol_ma5 / vol_ma50

    # Custo relativo ao movimento: o spread sobre o ATR.
    d["Spread_ATR"] = _coluna(d, "Spread", 0.0) / atr

    d["ATR_Pct"] = (atr / close) * 100.0
    d["ADX"] = _coluna(d, "ADX", 0.0)
    d["RSI"] = _coluna(d, "RSI", 50.0)
    d["RSI_Diff"] = d["RSI"].diff()
    d["ADX_Change"] = d["ADX"].diff()
    d["Close_Diff_Pct"] = close.pct_change() * 100.0

    # `KCI_VD` ja e INVARIANTE a escala: `KCI_MAIN` e o RCI de Williams em
    # 0..100, e `KCI_VD` e a variacao dele. Dividir por `ATR` (medido:
    # dava 12,5 no ouro e 23.148 no euro para o MESMO padrao) e dividir por
    # `Close` (dava 1,66 contra 3080) reintroduzem exatamente a escala que
    # este esquema existe para tirar. Fica sem normalizar.
    d["KCI_VD_Inv"] = d["KCI_VD"]
    d["KDI_Diff"] = d["KDI_PLUS"] - d["KDI_MINUS"]
    d["KCI_MAIN_Change"] = d["KCI_MAIN"].diff()

    # Candle em unidades de ATR.
    d["Body_ATR"] = (d["Close"] - d["Open"]) / atr
    d["Range_ATR"] = (d["High"] - d["Low"]) / atr
    d["UpperShadow_ATR"] = (d["High"] - d[["Open", "Close"]].max(axis=1)) / atr
    d["LowerShadow_ATR"] = (d[["Open", "Close"]].min(axis=1) - d["Low"]) / atr

    # Horizonte e classe: o que a serie OHLCV nao diz.
    d["Timeframe_Cod"] = float(CODIGO_TIMEFRAME[tf])
    d["Classe_Cod"] = float(CODIGO_CLASSE[cl])

    return d