# -*- coding: utf-8 -*-
"""Testes da inferencia real (backend/ai_inference.py).

O ponto central destes testes e a AUSENCIA DE FALLBACK. O sinal antigo
usava `rsi ?? 50`, `macd ?? 0`, `volume ?? 1` e confianca constante. Aqui a
exigencia e o contrario: quando nao ha dado, o servico tem de dizer que nao
tem, e nunca fabricar numero para preencher a tela.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend import ai_inference as ai


def _candles(n: int = 1200, seed: int = 11) -> pd.DataFrame:
    """Serie M5 com vol coerente com o ATR (ver train_v2 para o porque)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    preco = 2000.0 * np.exp(np.cumsum(rng.normal(0, 0.0006, n)))
    wiggle = np.abs(rng.normal(0, 0.0004, n)) * preco
    return pd.DataFrame({
        "Time": idx, "Open": preco, "High": preco + wiggle, "Low": preco - wiggle,
        "Close": preco * (1 + rng.normal(0, 0.0002, n)),
        "Volume": rng.integers(50, 500, n).astype(float),
        "ATR": np.abs(rng.normal(0, 1.2, n)).clip(0.3, None),
        "ADX": rng.uniform(10, 40, n), "RSI": rng.uniform(20, 80, n),
    })


# ------------------------------------------------------------- sem fallback


def test_sem_candles_nao_inventa_sinal():
    r = ai.inferir("XAUUSD", pd.DataFrame(), "H1")
    assert r.disponivel is False
    assert r.signal == "NEUTRAL"
    assert r.confianca == 0.0
    assert "candles" in r.motivo


def test_timeframe_sem_modelo_publicado_e_recusado():
    # M5 tem edge negativo: o servico tem de recusar, nao estimar.
    r = ai.inferir("XAUUSD", _candles(), "M5")
    assert r.disponivel is False
    assert r.confianca == 0.0
    assert r.motivo


def test_timeframe_invalido_e_recusado():
    r = ai.inferir("XAUUSD", _candles(), "M2")
    assert r.disponivel is False
    assert "nao suportado" in r.motivo


def test_resultado_indisponivel_nao_tem_probabilidade():
    """A tela nao pode exibir 50%/'vazio' como se fosse leitura do modelo."""
    r = ai.inferir("XAUUSD", pd.DataFrame(), "H1")
    d = r.para_dict()
    assert d["available"] is False
    assert d["confidence"] == 0.0
    assert d["prob_buy"] == 0.0 and d["prob_sell"] == 0.0
    assert d["reason"], "sempre haver um motivo legivel"


# ------------------------------------------------------------- inventario


def test_listar_modelos_traz_metricos_reais():
    modelos = ai.listar_modelos()
    assert modelos, "deveria haver metadados de modelo no repositorio"
    simbolos = set()
    for m in modelos:
        # O catalogo cobre todos os simbolos treinados (9), nao so XAUUSD.
        # O que nao pode e vazio ou sem simbolo: a interface precisa saber
        # qual ativo cada artefato decide.
        assert m["symbol"], m
        simbolos.add(m["symbol"])
        assert "_" in m["id"] and m["id"].startswith(m["symbol"]), m
        assert "accuracy" in m and "edge" in m
        assert m["edge_min"] is not None
        assert isinstance(m["publicable"], bool)
    assert len(simbolos) >= 2, f"catalogo deveria cobrir varios simbolos: {simbolos}"


def test_modelo_publicado_tem_edge_acima_do_minimo():
    for m in ai.listar_modelos():
        if m["publicable"]:
            assert m["edge"] is not None
            assert m["edge"] >= m["edge_min"], (
                f"{m['id']} marcado publicavel com edge {m['edge']} < {m['edge_min']}"
            )


def test_modelo_reprovado_expoe_o_motivo():
    for m in ai.listar_modelos():
        if not m["publicable"]:
            assert m["reason"], f"{m['id']} reprovado sem motivo registrado"


def test_inventario_informa_threads_de_cpu():
    modelos = ai.listar_modelos()
    assert all(m["cpu_threads"] >= 1 for m in modelos)
    assert ai.cpu_threads() >= 1


# ----------------------------------------------------------------- cache


def test_limpar_cache_nao_quebra():
    ai.limpar_cache()
    r = ai.inferir("XAUUSD", _candles(), "H1")
    # Pode estar disponivel ou nao (depende do .pkl publicado no ambiente),
    # mas nunca pode quebrar nem inventar.
    assert isinstance(r.disponivel, bool)
    assert r.confianca >= 0.0


# ------------------------------------------- coerencia com o treino


def test_inferencia_usa_as_mesmas_features_do_treino():
    """Se a ordem das features divergir do treino, o modelo ve outra coisa."""
    from Python.ai import train_v2 as t
    r = ai.inferir("XAUUSD", _candles(), "H1")
    if not r.disponivel:
        pytest.skip("modelo H1 nao publicado neste ambiente")
    # O hash sai do mesmo modulo usado no treino.
    assert r.feature_hash == t.feature_hash()
    assert r.modelo.endswith("_H1")


def test_confianca_e_probabilidade_do_classificador():
    """Confianca nao pode ser constante: tem que bater com as probabilidades."""
    r = ai.inferir("XAUUSD", _candles(), "H1")
    if not r.disponivel:
        pytest.skip("modelo H1 nao publicado neste ambiente")
    probs = [r.prob_buy, r.prob_sell, r.prob_neutral]
    assert abs(sum(probs) - 1.0) < 0.01, "probabilidades devem somar 1"
    assert r.confianca == pytest.approx(max(probs) * 100.0, rel=1e-3)
    # E nao pode ser uma das constantes do gerador antigo (50/60/70/75/80).
    assert r.confianca not in (50.0, 60.0, 70.0, 75.0, 80.0)


def test_decisao_corresponde_a_probabilidade_maior():
    r = ai.inferir("XAUUSD", _candles(), "H1")
    if not r.disponivel:
        pytest.skip("modelo H1 nao publicado neste ambiente")
    probs = {0: r.prob_sell, 1: r.prob_neutral, 2: r.prob_buy}
    esperado = {0: "SELL", 1: "NEUTRAL", 2: "BUY"}[max(probs, key=lambda k: probs[k])]
    assert r.signal == esperado
