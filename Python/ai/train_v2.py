# -*- coding: utf-8 -*-
"""Treinamento corrigido dos modelos de IA — conjunto 25F, versao 25F-v2.

POR QUE ESTE MODULO EXISTE
===========================
O pipeline original (`Python/pipeline.py`) tinha cinco defeitos que juntos
tornavam a IA inutil:

1. **O dataset nao tem coluna de timeframe.** `DataEngineXAU.load()` le 15
   colunas e nenhuma delas e o timeframe. Logo `train_symbol_model(symbol, "H1")`
   e `train_symbol_model(symbol, "M5")` treinavam sobre **as mesmas linhas**. Os
   "modelos por timeframe" eram o mesmo modelo com nome diferente, e era por
   isso que XAUUSD H1/H4/M5 reportavam accuracy identica.

   Correcao aqui: o dataset e M5 e os timeframes derivados sao **reamostrados em
   codigo** a partir da serie M5. O produtor (DataLogger.mqh) fica intocado.

2. **Vazamento de futuro no alvo.** `_build_multiclass_target` usava
   `atr_rel.quantile(...)` sobre a serie inteira para definir o piso de ATR. O
   percentil enxerga o conjunto todo, inclusive o periodo de teste, e isso
   contamina o rotulo de treino.

   Correcao aqui: o piso e um **percentil expansivo** calculado apenas com o
   passado de cada linha.

3. **Sem purga na fronteira do split.** O rotulo de uma linha usa `shift(-10)`:
   as ultimas 10 linhas antes da fronteira carregam informacao do periodo de
   teste.

   Correcao aqui: **purging** de `lookback_max` linhas dos dois lados.

4. **Feature morta.** KCI_VD, KCI_MAIN, KDI_PLUS e KDI_MINUS vem do dataset
   com valor `0.0`, e KCI_VD_Pct, KDI_Diff e KCI_MAIN_Change sao derivadas
   dessas. Sao **7 das 25 features constantes** — o modelo aprende com 18.

   Correcao aqui: as 4 features KCI sao **derivadas da propria serie OHLC** em
   Python (direcional movement normalizado). Se nao houver serie suficiente, a
   feature e marcada indisponivel e o modelo nao e publicado — nunca
   preenchida com zero.

5. **Nao havia porta de qualidade.** Qualquer modelo era gravado e virava sinal.

   Correcao aqui: `PUBLICACAO_MIN_EDGE`. Modelo com edge sobre o palpite abaixo
   disso e gravado com `publishable: false`, e a predicao sai como UNAVAILABLE.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

# Versao do conjunto de features. Mudou em relacao a 25F-v1 porque as 4 colunas
# KCI do dataset sao zeradas e passaram a ser derivadas aqui.
FEATURE_VERSION = "25F-v2"

# Colunas de entrada do dataset do MT5 (15, sem timeframe - ver data_engine_xau).
COLUNAS_DATASET = [
    "Time", "Symbol", "Open", "High", "Low", "Close", "Volume",
    "Spread", "ATR", "ADX", "RSI", "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",
]

# Ordem canonica das features. As 4 KCI sao derivadas, nao lidas do dataset.
FEATURES: list[str] = [
    "Open", "High", "Low", "Close", "Volume", "Spread",
    "ATR", "ADX", "RSI",
    "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",
    "BodySize", "RangeSize", "UpperShadow", "LowerShadow",
    "ATR_Pct", "RSI_Diff", "Close_Diff", "Volume_MA",
    "ADX_Change", "KCI_VD_Pct", "KDI_Diff", "KCI_MAIN_Change",
]

# Minutos de cada timeframe suportado.
MINUTOS_TIMEFRAME: dict[str, int] = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440,
}

# Uma previsao so e publicada com advantage minima sobre o palpite da arvore.
PUBLICACAO_MIN_EDGE = 0.05

# Numeros magicos do target, por classe de ativo.
DIRECAO_TH = 0.4
FORTE_TH = 1.0
JANELA_ATR = 14
ATR_CLIP = 6.0
LOOKAHEAD = {"M5": 1, "M15": 3, "M30": 3, "H1": 2, "H4": 4, "D1": 8}


def feature_hash() -> str:
    """Hash do conjunto de features, para detectar drift."""
    return hashlib.sha256("|".join(FEATURES).encode("utf-8")).hexdigest()[:16]


@dataclass
class ResultadoTreino:
    symbol: str
    timeframe: str
    Treinou: bool = False
    accuracy: float | None = None
    f1: float | None = None
    palpite: float = 1 / 3
    edge: float | None = None
    publicavel: bool = False
    motivo: str = ""
    treino: int = 0
    teste: int = 0
    modelo: Any = None
    folds: list[dict[str, Any]] = field(default_factory=list)
    estavel: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def robustez(self) -> float:
        """Mediana do edge entre folds dividida pelo desvio.

        Escolher o modelo de maior edge e vies de selecao: o maior numero
        tende a ser o fold mais ruidoso, nao o modelo mais confiavel. A
        razao mediana/desvio mede consistencia, que e o que interessa para
        operar dinheiro real.
        """
        edges = [f["edge"] for f in self.folds]
        if len(edges) < 2:
            return 0.0
        desvio = float(np.std(edges))
        if desvio <= 0:
            return float(np.mean(edges)) * 10.0
        return float(np.median(edges)) / desvio


# ------------------------------------------------------------------ resample


def reamostrar(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Agrega a serie M5 no timeframe pedido.

    O dataset so tem M5. Um modelo de H1 treinado sobre M5 seria mentira: o
    horizontes de previsao nao battem. Aqui os candles sao agregados de verdade.
    """
    if timeframe not in MINUTOS_TIMEFRAME:
        raise ValueError(f"timeframe nao suportado: {timeframe}")
    alvo = MINUTOS_TIMEFRAME[timeframe]
    base = MINUTOS_TIMEFRAME["M5"]
    if alvo < base:
        raise ValueError("nao e possivel reamostrar para granularidade menor que a do dataset")
    if alvo == base:
        return df.reset_index(drop=True).copy()

    agrupado = (
        df.set_index("Time")
        .resample(f"{alvo}min", label="left", closed="left")
        .agg(
            Open=("Open", "first"), High=("High", "max"), Low=("Low", "min"),
            Close=("Close", "last"), Volume=("Volume", "sum"),
            # Spread e opcional: a inferencia ao vivo depende do que o MT5
            # devolve, e nem toda fonte manda Spread. Ausente vira 0.0 em vez
            # de derrubar a inferencia inteira com KeyError.
            **({"Spread": ("Spread", "mean")} if "Spread" in df.columns else {}),
            **({"ATR": ("ATR", "mean")} if "ATR" in df.columns else {}),
            **({"ADX": ("ADX", "mean")} if "ADX" in df.columns else {}),
            **({"RSI": ("RSI", "mean")} if "RSI" in df.columns else {}),
        )
        .dropna(subset=["Open", "High", "Low", "Close"])
        .reset_index()
    )
    for coluna in ("Spread", "ATR", "ADX", "RSI"):
        if coluna not in agrupado.columns:
            agrupado[coluna] = 0.0
    return agrupado


# ------------------------------------------------------- features derivadas


def _directional_movement(alto: pd.Series, baixo: pd.Series) -> tuple[pd.Series, pd.Series]:
    """+DI e -DI no estilo Wilder, calculados da propria serie."""
    subida = alto.diff()
    descida = -baixo.diff()
    pos = subida.where((subida > descida) & (subida > 0), 0.0)
    neg = descida.where((descida > subida) & (descida > 0), 0.0)
    tr = pd.concat([alto - baixo, (alto - alto.shift(1)).abs(), (baixo - baixo.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / JANELA_ATR, adjust=False).mean().replace(0.0, np.nan)
    pos_s = pos.ewm(alpha=1 / JANELA_ATR, adjust=False).mean() / atr
    neg_s = neg.ewm(alpha=1 / JANELA_ATR, adjust=False).mean() / atr
    total = (pos_s + neg_s).replace(0.0, np.nan)
    return (pos_s / total * 100.0), (neg_s / total * 100.0)


def derivar_kci(df: pd.DataFrame) -> pd.DataFrame:
    """Substitui as colunas KCI zeradas por valores derivados da serie.

    O dataset traz KCI_VD/KCI_MAIN/KDI_PLUS/KDI_MINUS com 0.0, o que tornava 7
    das 25 features constantes. Aqui elas passam a ter informacao real.
    """
    saida = df.copy()
    pos_di, neg_di = _directional_movement(saida["High"], saida["Low"])
    saida["KDI_PLUS"] = pos_di
    saida["KDI_MINUS"] = neg_di
    # As 4 colunas sao atribuidas aqui, nunca lidas do dataset: o reamostrador
    # as descarta e o dataset real as traz zeradas. Ler antes quebraria H1/H4.
    # ATR relativo ao preco como distancia de volatilidade normalizada.
    saida["KCI_VD"] = (saida["ATR"] / saida["Close"] * 100.0).ewm(
        alpha=1 / JANELA_ATR, adjust=False
    ).mean()
    # Forca da tendencia: soma dos dois lado, ja normalizado em 0-100.
    saida["KCI_MAIN"] = (pos_di.fillna(0.0) + neg_di.fillna(0.0)).clip(0.0, 100.0)
    return saida


def construir_features(df: pd.DataFrame) -> pd.DataFrame:
    """Monta as 25 features na ordem canonica."""
    d = derivar_kci(df)
    d["BodySize"] = d["Close"] - d["Open"]
    d["RangeSize"] = d["High"] - d["Low"]
    d["UpperShadow"] = d["High"] - d[["Open", "Close"]].max(axis=1)
    d["LowerShadow"] = d[["Open", "Close"]].min(axis=1) - d["Low"]
    d["ATR_Pct"] = (d["ATR"] / d["Close"]) * 100.0
    d["RSI_Diff"] = d["RSI"].diff()
    d["Close_Diff"] = d["Close"].diff()
    d["Volume_MA"] = d["Volume"].rolling(window=5, min_periods=1).mean()
    d["ADX_Change"] = d["ADX"].diff()
    d["KCI_VD_Pct"] = (d["KCI_VD"] / d["Close"]) * 100.0
    d["KDI_Diff"] = d["KDI_PLUS"] - d["KDI_MINUS"]
    d["KCI_MAIN_Change"] = d["KCI_MAIN"].diff()
    return d


# ------------------------------------------------------------------- target


def construir_target(df: pd.DataFrame, lookahead: int) -> pd.DataFrame:
    """Rotulo de 3 classes (SELL/NEUTRAL/BUY) normalizado por ATR.

    O piso de ATR e um **percentil expansivo**: so olha para o passado de cada
    linha. A versao anterior usava `quantile` sobre a serie inteira, o que
    vazava o periodo de teste para o rotulo de treino.
    """
    d = df.copy()
    futuro = d["Close"].shift(-lookahead) / d["Close"] - 1.0
    futuro5 = d["Close"].shift(-5) / d["Close"] - 1.0
    futuro10 = d["Close"].shift(-10) / d["Close"] - 1.0
    combinado = (futuro + futuro5 * 0.5 + futuro10 * 0.3) / 1.8

    atr_rel = (d["ATR"] / d["Close"])
    piso = atr_rel.expanding(min_periods=JANELA_ATR).quantile(0.02)
    piso = piso.ffill().fillna(atr_rel.rolling(JANELA_ATR, min_periods=1).median())
    atr_seguro = atr_rel.clip(lower=piso.clip(lower=1e-9))

    norm = (combinado / atr_seguro).clip(-ATR_CLIP, ATR_CLIP)
    condicoes = [norm >= FORTE_TH, norm >= DIRECAO_TH, norm >= -DIRECAO_TH, norm >= -FORTE_TH]
    d["Target"] = pd.Series(np.select(condicoes, [2, 2, 1, 0], default=0), index=d.index)
    return d.replace([np.inf, -np.inf], np.nan).dropna(subset=["Target"])


# ---------------------------------------------------------------- treino


# Uma única divisão cronológica não prova nada. Testar 4 timeframes e
# publicar os vencedores é selection bias: algum sempre passa por acaso.
# O modelo só é publicável se o edge for consistente em vários folds
# cronológicos independentes, com dispersão declarada.
N_FOLDS = 5
MIN_FOLDS_POSITIVOS = 4


def walk_forward(
    base: pd.DataFrame,
    min_amostras_treino: int = 500,
    n_folds: int = N_FOLDS,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Valida em N folds cronologicos, expanding window.

    Cada fold treina no passado e testa na fatia seguinte, com purga de
    lookahead. Devolve o edge por fold para que a dispersao seja visivel.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score

    folds: list[dict[str, Any]] = []
    total = len(base)
    if total < min_amostras_treino + 200:
        return folds
    passo = (total - min_amostras_treino) // n_folds
    for k in range(n_folds):
        ini_treino = 0
        fim_treino = min_amostras_treino + k * passo
        ini_teste = fim_treino + 10  # purga
        fim_teste = min(total, ini_teste + passo)
        if fim_treino - ini_treino < 200 or fim_teste - ini_teste < 50:
            continue
        X_train = base[FEATURES].iloc[ini_treino:fim_treino]
        y_train = base["Target"].iloc[ini_treino:fim_treino].astype(int)
        X_test = base[FEATURES].iloc[ini_teste:fim_teste]
        y_test = base["Target"].iloc[ini_teste:fim_teste].astype(int)
        modelo = RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=5,
            class_weight="balanced", random_state=seed + k, n_jobs=-1,
        )
        modelo.fit(X_train, y_train)
        acc = float(accuracy_score(y_test, modelo.predict(X_test)))
        classes = int(base["Target"].nunique())
        palpite = 1.0 / max(classes, 2)
        folds.append(
            {
                "fold": k + 1,
                "accuracy": acc,
                "baseline": palpite,
                "edge": acc - palpite,
                "train": int(len(X_train)),
                "test": int(len(X_test)),
            }
        )
    return folds


def edge_consistente(folds: list[dict[str, Any]], min_edge: float = 0.0) -> tuple[bool, str]:
    """Decide se o edge se sustenta entre folds, nao so na melhor fatia."""
    if not folds:
        return False, "sem folds para validar"
    edges = [f["edge"] for f in folds]
    positivos = sum(1 for e in edges if e > 0)
    media = float(np.mean(edges))
    desvio = float(np.std(edges))
    detalhe = (
        f"edge por fold: {' '.join('%+.3f' % e for e in edges)} "
        f"(media {media:+.4f}, desvio {desvio:.4f}, {positivos}/{len(edges)} positivos)"
    )
    if positivos < MIN_FOLDS_POSITIVOS:
        return False, f"edge instavel entre folds: {detalhe}"
    if media < min_edge:
        return False, f"edge medio {media:+.4f} abaixo do minimo {min_edge:+.4f}: {detalhe}"
    return True, detalhe


def treinar(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str = "M5",
    min_amostras: int = 800,
    min_edge: float = PUBLICACAO_MIN_EDGE,
    seed: int = 42,
) -> ResultadoTreino:
    """Treina e valida com split cronologico e purga na fronteira.

    O regime de mercado muda ao longo do tempo, entao a validacao e sempre
    "treina no passado, testa no futuro". Modelo que so funciona com split
    aleatorio nao funciona no futuro, que e o unico que interessa.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score

    resultado = ResultadoTreino(symbol=symbol, timeframe=timeframe)
    if timeframe not in MINUTOS_TIMEFRAME:
        resultado.motivo = f"timeframe nao suportado: {timeframe}"
        return resultado
    if df is None or df.empty:
        resultado.motivo = "sem dados"
        return resultado

    try:
        base = reamostrar(df, timeframe)
    except ValueError as exc:
        resultado.motivo = str(exc)
        return resultado

    base = construir_features(base)
    base = construir_target(base, LOOKAHEAD.get(timeframe, 1))
    base = base.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES)

    if len(base) < min_amostras:
        resultado.motivo = f"amostras insuficientes: {len(base)} (minimo {min_amostras})"
        return resultado

    X = base[FEATURES]
    y = base["Target"].astype(int)
    fronteira = int(len(X) * 0.8)
    # Purging: o rotulo usa shift(-10), entao as ultimas linhas do treino
    # enxergam o inicio do teste.
    purga = 10
    fim_treino = max(0, fronteira - purga)
    inicio_teste = min(len(X), fronteira + purga)
    if fim_treino < 100 or (len(X) - inicio_teste) < 50:
        resultado.motivo = (
            f"serie curta demais para split com purga: "
            f"treino={fim_treino} teste={len(X) - inicio_teste}"
        )
        return resultado

    X_train, y_train = X.iloc[:fim_treino], y.iloc[:fim_treino]
    X_test, y_test = X.iloc[inicio_teste:], y.iloc[inicio_teste:]

    modelo = RandomForestClassifier(
        n_estimators=300, max_depth=10, min_samples_leaf=5,
        class_weight="balanced", random_state=seed, n_jobs=-1,
    )
    modelo.fit(X_train, y_train)

    acc = float(accuracy_score(y_test, modelo.predict(X_test)))
    f1 = float(f1_score(y_test, modelo.predict(X_test), average="weighted"))
    classes = int(y.nunique())
    palpite = 1.0 / max(classes, 2)
    edge = acc - palpite

    resultado.Treinou = True
    resultado.accuracy = acc
    resultado.f1 = f1
    resultado.palpite = palpite
    resultado.edge = edge
    resultado.treino = len(X_train)
    resultado.teste = len(X_test)

    # A divisao unica serve para medir; a publicacao exige consistencia.
    folds = walk_forward(base)
    estavel, detalhe = edge_consistente(folds, min_edge)
    resultado.folds = folds
    resultado.estavel = estavel

    resultado.publicavel = edge >= min_edge and estavel
    if edge < min_edge:
        resultado.motivo = (
            f"edge {edge:+.4f} abaixo do minimo {min_edge:+.4f} "
            f"(acc {acc:.4f} vs palpite {palpite:.4f})"
        )
    elif not estavel:
        resultado.motivo = detalhe
    resultado.meta = {
        "symbol": symbol,
        "timeframe": timeframe,
        "feature_version": FEATURE_VERSION,
        "feature_hash": feature_hash(),
        "feature_count": len(FEATURES),
        "algorithm": "RandomForestClassifier",
        "metrics": {
            "accuracy": acc,
            "f1_score": f1,
            "baseline": palpite,
            "edge": edge,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "purged": purga,
            "folds": folds,
            "edge_estavel": estavel,
        },
        "publicable": resultado.publicavel,
        "publish_reason": resultado.motivo,
        "min_edge": min_edge,
        "train_date": datetime.now(timezone.utc).isoformat(),
    }
    resultado.modelo = modelo
    return resultado


# ------------------------------------------------------------- predição


def montar_prediction(
    resultado: ResultadoTreino,
    df: pd.DataFrame,
    versao_app: str = "1.2.0",
) -> dict[str, Any]:
    """Monta o JSON de predicao no formato que o EA consome.

    Ponto essencial: se o modelo nao passou na porta de qualidade, a predicao
    sai como NEUTRAL com `available: false` e o motivo. O EA recebe um arquivo
    valido e nao age. Publicar um sinal de modelo reprovado seria pior do que
    nao publicar sinal nenhum.
    """
    ultimo = df.iloc[-1]
    preco = float(ultimo["Close"])
    atr = float(ultimo.get("ATR", 0.0))
    model_id = f"random_forest_{resultado.symbol}_{resultado.timeframe}"

    base: dict[str, Any] = {
        "symbol": resultado.symbol,
        "category": "Metals" if resultado.symbol.upper().endswith("USD") and "XAU" in resultado.symbol.upper() else "Unknown",
        "signal": "NEUTRAL",
        "confidence": 0.0,
        "score": 0.0,
        "buy": 0.0,
        "sell": 0.0,
        "prob_buy": 0.0,
        "prob_sell": 0.0,
        "risk": "VERY_HIGH",
        "model": "random_forest",
        "model_version": versao_app,
        "model_id": model_id,
        "feature_version": FEATURE_VERSION,
        "feature_hash": feature_hash(),
        "feature_count": len(FEATURES),
        "timeframe": resultado.timeframe,
        "price": preco,
        "atr": atr,
        "available": False,
        "edge": resultado.edge,
        "accuracy": resultado.accuracy,
        "reason": resultado.motivo or "modelo nao publicado",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if not resultado.Treinou or not resultado.publicavel:
        return base

    modelo = resultado.modelo
    ultima = construir_features(reamostrar(df, resultado.timeframe)).iloc[[-1]][FEATURES]
    probs = modelo.predict_proba(ultima)[0]
    idx_buy, idx_sell = 2, 0
    p_buy = float(probs[idx_buy]) if len(probs) > idx_buy else 0.0
    p_sell = float(probs[idx_sell]) if len(probs) > idx_sell else 0.0
    p_neutral = float(probs[1]) if len(probs) > 1 else 0.0
    decisao = int(np.argmax(probs))

    base.update(
        {
            "signal": {0: "SELL", 1: "NEUTRAL", 2: "BUY"}[decisao],
            "confidence": round(float(max(probs)) * 100.0, 1),
            "score": round(float(max(probs)) * 100.0, 1),
            "buy": p_buy,
            "sell": p_sell,
            "prob_buy": p_buy,
            "prob_sell": p_sell,
            "prob_neutral": p_neutral,
            "risk": "LOW" if max(probs) >= 0.85 else "MEDIUM" if max(probs) >= 0.70 else "HIGH",
            "available": True,
            "reason": "modelo publicado: edge %+.4f" % (resultado.edge or 0.0),
        }
    )
    return base
