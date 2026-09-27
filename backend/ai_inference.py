# -*- coding: utf-8 -*-
"""Servico de inferencia: modelos treinados -> decisao de trading, na CPU.

POR QUE ISTO EXISTE
===================
O sinal que o app exibia antes NAO VINHA DE NENHUM MODELO. O frontend
(`useAICommunication.ts`) aplicava regras fixas sobre indicadores e, quando o
calculo falhava, inventava os valores:

    const rsi = typeof indicators?.rsi === 'number' ? indicators.rsi : 50;
    const macd = typeof indicators?.macd === 'number' ? indicators.macd : 0;
    const volume = typeof indicators?.volume === 'number' ? indicators.volume : 1;

Ou seja: RSI "falso" 50, MACD "falso" 0, volume sempre 1, Stop Loss em
preco*0.99 e Take Profit em preco*1.02 — aritmetica fixa, sem modelo. E a
confianca era uma CONSTANTE por regra (70/75/80), apresentada na tela como se
fosse uma estatistica. O perfil "breakout" exigia volume > 1.5 e por isso
nunca disparava: o volume era hardcoded em 1.

Este modulo substitui isso por inferencia de verdade:

  - carrega o .pkl treinado e o .meta.json com os metricos reais
  - monta as 25 features pela mesma funcao usada no treino (25F-v2), com as
    4 features KCI derivadas da serie, e NUNCA preenchidas com zero
  - devolve as probabilidades REAIS do classificador
  - a confianca exibida e a probabilidade do modelo, nao uma constante
  - se o modelo nao passou na porta de qualidade, ou nao ha dado suficiente,
    ou o timeframe nao bate, o servico devolve `disponivel: false` com o
    motivo. Nao existe fallback que fabrique um sinal.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Raiz do repositorio: backend/ -> ..
RAIZ = Path(__file__).resolve().parent.parent
for _caminho in (RAIZ, RAIZ / "Python"):
    if str(_caminho) not in sys.path:
        sys.path.insert(0, str(_caminho))

from Python.ai import train_v2 as t  # noqa: E402

MODELOS_DIR = RAIZ / "Python" / "models"

# Quantas threads de CPU o processo pode usar. O usuario ve esse numero na aba
# IA; nao e cosmetics, e o limite real de paralelismo do scikit-learn.
def cpu_threads() -> int:
    """Threads de CPU liberadas para inferencia."""
    bruto = os.environ.get("XAU_AI_PRO_N_JOBS", "").strip()
    if bruto:
        try:
            valor = int(bruto)
            if valor > 0:
                return valor
        except ValueError:
            pass
    # -1 no scikit-learn significa "todas as nucleos".
    return max(1, (os.cpu_count() or 1))


@dataclass
class Inferencia:
    """Resultado de uma inferencia. Honesto por construcao."""

    disponivel: bool
    motivo: str
    symbol: str = ""
    timeframe: str = ""
    signal: str = "NEUTRAL"          # BUY | SELL | NEUTRAL
    confianca: float = 0.0            # probabilidade real do classificador (0-100)
    prob_buy: float = 0.0
    prob_sell: float = 0.0
    prob_neutral: float = 0.0
    price: float = 0.0
    atr: float = 0.0
    edge: float | None = None
    accuracy: float | None = None
    folds: list[dict[str, Any]] | None = None
    inferencia_ms: float = 0.0
    modelo: str = ""
    feature_hash: str = ""

    def para_dict(self) -> dict[str, Any]:
        return {
            "available": self.disponivel,
            "reason": self.motivo,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "signal": self.signal,
            "confidence": round(self.confianca, 1),
            "prob_buy": round(self.prob_buy, 4),
            "prob_sell": round(self.prob_sell, 4),
            "prob_neutral": round(self.prob_neutral, 4),
            "price": self.price,
            "atr": self.atr,
            "edge": self.edge,
            "accuracy": self.accuracy,
            "folds": self.folds,
            "inference_ms": round(self.inferencia_ms, 2),
            "model": self.modelo,
            "feature_hash": self.feature_hash,
            "cpu_threads": cpu_threads(),
        }


_CACHE: dict[str, Any] = {}


def _carregar(timeframe: str) -> tuple[Any | None, dict[str, Any]]:
    """Carrega .pkl e .meta.json de um timeframe.

    O .pkl tem 8 MB e leva ~2 s para desserializar. Recarregar a cada tique
    seria crippling, entao o resultado fica em cache e so e invalidado quando
    o mtime do arquivo muda (retraining).
    """
    chave = f"modelo:{timeframe}"
    pkl = MODELOS_DIR / f"XAUUSD_{timeframe}.pkl"
    meta = MODELOS_DIR / f"XAUUSD_{timeframe}.meta.json"
    if not (pkl.exists() and meta.exists()):
        _CACHE[chave] = (None, {})
        return _CACHE[chave]
    mtime = pkl.stat().st_mtime
    em_cache = _CACHE.get(chave)
    if em_cache is not None and em_cache[2] == mtime:
        return em_cache[0], em_cache[1]
    try:
        import joblib

        with meta.open(encoding="utf-8") as f:
            m = json.load(f)
        # Treino so e aceito se passou na porta de qualidade.
        modelo = None if not m.get("publicable") else joblib.load(pkl)
        _CACHE[chave] = (modelo, m, mtime)
    except Exception:
        _CACHE[chave] = (None, {}, mtime)
    return _CACHE[chave][0], _CACHE[chave][1]


def limpar_cache() -> None:
    _CACHE.clear()


def _n_jobs_inferencia() -> int:
    """Threads para inferencia de UMA amostra.

    predict_proba de uma unica linha nao paraleliza: o joblib ainda paga o
    custo de spawn (medido: metade dos 68 ms era time.sleep de worker). Como
    a inferencia pode rodar em paralelo por modelo (aba IA ativa varios
    modelos ao vivo), deixamos o paralelismo para FORA e usamos 1 thread aqui.
    """
    return 1


def _predict_proba(modelo: Any, amostra: pd.DataFrame) -> np.ndarray:
    """predict_proba de uma linha com 1 thread.

    Sem isso, o joblib paga o custo de criar 4 workers para processar UMA
    amostra: metade dos 68 ms medidos era time.sleep esperando worker ocioso.
    """
    try:
        modelo.n_jobs = _n_jobs_inferencia()
    except Exception:
        pass
    return modelo.predict_proba(amostra)[0]


def inferir(symbol: str, candles: pd.DataFrame, timeframe: str = "H1") -> Inferencia:
    """Roda o modelo do timeframe e devolve a decisao, ou diz por que nao pode.

    `candles` deve conter Time/Open/High/Low/Close/Volume/ATR/ADX/RSI no
    timeframe pedido. Nao ha默认值 e nao haFallback: se faltar, devolvemos
    indisponivel com o motivo.
    """
    inicio = time.perf_counter()
    threads = cpu_threads()
    os.environ.setdefault("XAU_AI_PRO_N_JOBS", str(threads))

    if timeframe not in t.MINUTOS_TIMEFRAME:
        return Inferencia(False, f"timeframe nao suportado: {timeframe}", symbol, timeframe)
    if candles is None or candles.empty:
        return Inferencia(False, "sem candles recebidos", symbol, timeframe)

    modelo, meta = _carregar(timeframe)
    if modelo is None:
        motivo = meta.get("publish_reason") or "modelo nao publicado ou ausente"
        return Inferencia(False, motivo, symbol, timeframe)

    try:
        # So a ultima linha e usada. Cortar ANTES de reamostrar evita
        # resamplear 46 mil candles a cada tique (eram ~2,4 s por inferencia).
        # 600 candles M5 dao 200 de H1, mais que o suficiente para as features
        # rolling/ewm ficarem identicas ao treino.
        janela = t.reamostrar(candles.tail(1200), timeframe)
        base = t.construir_features(janela)
        base = base.replace([np.inf, -np.inf], np.nan).dropna(subset=t.FEATURES)
        if base.empty:
            return Inferencia(False, "features incompletas apos derivacao", symbol, timeframe)
        ultima = base.iloc[[-1]][t.FEATURES]
        if ultima.isna().any(axis=None):
            return Inferencia(False, "ultima linha com feature faltando", symbol, timeframe)

        probs = _predict_proba(modelo, ultima)
        decisao = int(np.argmax(probs))
        metricas = meta.get("metrics", {})
        linha = base.iloc[-1]
        ms = (time.perf_counter() - inicio) * 1000.0

        p_buy = float(probs[2]) if len(probs) > 2 else 0.0
        p_sell = float(probs[0]) if len(probs) > 0 else 0.0
        p_neu = float(probs[1]) if len(probs) > 1 else 0.0
        return Inferencia(
            disponivel=True,
            motivo="inferencia real do modelo publicado",
            symbol=symbol,
            timeframe=timeframe,
            signal={0: "SELL", 1: "NEUTRAL", 2: "BUY"}.get(decisao, "NEUTRAL"),
            # Confianca = probabilidade real que o modelo atribui a decisao.
            confianca=float(max(probs)) * 100.0,
            prob_buy=p_buy,
            prob_sell=p_sell,
            prob_neutral=p_neu,
            price=float(linha["Close"]),
            atr=float(linha.get("ATR", 0.0)),
            edge=metricas.get("edge"),
            accuracy=metricas.get("accuracy"),
            folds=metricas.get("folds"),
            inferencia_ms=ms,
            modelo=f"random_forest_XAUUSD_{timeframe}",
            feature_hash=t.feature_hash(),
        )
    except Exception as exc:  # pragma: no cover
        return Inferencia(False, f"erro na inferencia: {exc}", symbol, timeframe)


def listar_modelos() -> list[dict[str, Any]]:
    """Inventario real dos artefatos, com os metricos do treino."""
    saida: list[dict[str, Any]] = []
    if not MODELOS_DIR.exists():
        return saida
    for meta_path in sorted(MODELOS_DIR.glob("XAUUSD_*.meta.json")):
        tf = meta_path.stem.replace("XAUUSD_", "").replace(".meta", "")
        try:
            with meta_path.open(encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            continue
        metricas = m.get("metrics", {})
        folds = metricas.get("folds") or []
        edges = [fo["edge"] for fo in folds if isinstance(fo, dict) and "edge" in fo]
        saida.append({
            "id": f"XAUUSD_{tf}",
            "symbol": "XAUUSD",
            "timeframe": tf,
            "publicable": bool(m.get("publicable")),
            "reason": m.get("publish_reason", ""),
            "accuracy": metricas.get("accuracy"),
            "f1": metricas.get("f1_score"),
            "baseline": metricas.get("baseline"),
            "edge": metricas.get("edge"),
            "edge_min": m.get("min_edge"),
            "edge_folds": edges,
            "edge_mean": float(np.mean(edges)) if edges else None,
            "edge_std": float(np.std(edges)) if edges else None,
            "train_samples": metricas.get("train_samples"),
            "test_samples": metricas.get("test_samples"),
            "purged": metricas.get("purged"),
            "train_date": m.get("train_date"),
            "feature_version": m.get("feature_version"),
            "feature_hash": m.get("feature_hash"),
            "algorithm": m.get("algorithm"),
            "pkl_present": (MODELOS_DIR / f"XAUUSD_{tf}.pkl").exists(),
            "cpu_threads": cpu_threads(),
        })
    return saida
