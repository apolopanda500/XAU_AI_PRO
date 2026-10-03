# -*- coding: utf-8 -*-
"""Testes do pipeline corrigido (Python/ai/train_v2.py).

Estes testes nao verificam "o modelo acerta muito". Verificam os defeitos
concretos que existiam antes:

- series reamostradas de verdade, nao o M5 com nome de H1
- rotulo sem vazamento de futuro
- purga na fronteira do split
- features KCI com variacao real, em vez de 4 colunas zeradas
- porta de qualidade barrando publicacao de modelo sem advantage
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from Python.ai import train_v2 as t


def _serie(n: int = 3000, seed: int = 7) -> pd.DataFrame:
    """Serie M5 sintetica com vol e ATR coerentes entre si.

    Importante: o preco anda em *retorno relativo* (~0,06% por candle de 5min,
    tipico de ouro) e o ATR e da mesma ordem. Se o preco andar em unidades
    absolutas minimas, o alvo normalizado por ATR fica praticamente zero e
    nenhuma classe e gerada — o teste passaria a medir a fixture, nao o codigo.
    """
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    # Volatilidade varia lentamente para exercitar o piso expansivo de ATR.
    fator_vol = 1.0 + 0.6 * np.sin(np.linspace(0, 6 * np.pi, n))
    ret = rng.normal(0, 0.0006, n) * fator_vol
    preco = 2000.0 * np.exp(np.cumsum(ret))
    wiggle = np.abs(rng.normal(0, 0.0004, n)) * preco
    df = pd.DataFrame(
        {
            "Time": idx, "Symbol": "XAUUSD",
            "Open": preco, "High": preco + wiggle, "Low": preco - wiggle,
            "Close": preco * (1.0 + rng.normal(0, 0.0002, n)),
            "Volume": rng.integers(50, 500, n).astype(float),
            "Spread": rng.uniform(0.15, 0.35, n),
            "ATR": (np.abs(rng.normal(0, 1.2, n)) * fator_vol).clip(0.3, None),
            "ADX": rng.uniform(10, 40, n),
            "RSI": rng.uniform(20, 80, n),
            # o dataset real vem com estes 4 zerados
            "KCI_VD": 0.0, "KCI_MAIN": 0.0, "KDI_PLUS": 0.0, "KDI_MINUS": 0.0,
        }
    )
    return df


# --------------------------------------------------------------- contrato


def test_contrato_tem_25_features_em_ordem_canonica():
    assert len(t.FEATURES) == 25
    assert len(set(t.FEATURES)) == 25
    assert t.FEATURES[0] == "Open"
    assert t.FEATURES[-1] == "KCI_MAIN_Change"


def test_hash_muda_se_mudar_o_contrato():
    original = t.feature_hash()
    try:
        t.FEATURES.append("FeatureInventada")
        assert t.feature_hash() != original
    finally:
        t.FEATURES.pop()


# -------------------------------------------------------------- resample


def test_reamostrar_h1_agrega_doze_candles_m5():
    df = _serie(120)  # 120 candles de 5min = 10 horas
    h1 = t.reamostrar(df, "H1")
    # 120 candles M5 = 600 min = 10 candles H1
    assert len(h1) == 10
    # cada candle H1 cobre 12 candles M5
    assert h1["Time"].iloc[1] - h1["Time"].iloc[0] == pd.Timedelta(hours=1)


def test_reamostrar_preserva_extremos_de_preco():
    df = _serie(120)
    h1 = t.reamostrar(df, "H1")
    primeiro_bloco = df.iloc[:12]
    assert h1["Open"].iloc[0] == pytest.approx(primeiro_bloco["Open"].iloc[0])
    assert h1["High"].iloc[0] == pytest.approx(primeiro_bloco["High"].max())
    assert h1["Low"].iloc[0] == pytest.approx(primeiro_bloco["Low"].min())
    assert h1["Close"].iloc[0] == pytest.approx(primeiro_bloco["Close"].iloc[-1])
    assert h1["Volume"].iloc[0] == pytest.approx(primeiro_bloco["Volume"].sum())


def test_reamostrar_m5_devolve_a_serie_original():
    df = _serie(200)
    m5 = t.reamostrar(df, "M5")
    assert len(m5) == len(df)
    assert m5["Close"].tolist() == df["Close"].tolist()


def test_reamostrar_recusa_timeframe_invalido():
    with pytest.raises(ValueError):
        t.reamostrar(_serie(50), "M3")
    with pytest.raises(ValueError):
        t.reamostrar(_serie(50), "S5")


# -------------------------------------------------- features sem feature morta


def test_kci_derivado_tem_variacao_real():
    """O defeito original: as 4 colunas KCI vinham com 0.0 do dataset."""
    df = _serie(1500)
    derivados = t.derivar_kci(df)
    for coluna in ("KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS"):
        valores = derivados[coluna].dropna()
        assert len(valores) > 0, f"{coluna} ficou toda nula"
        assert valores.std() > 0, f"{coluna} ficou constante: nao carrega informacao"


def test_nenhuma_feature_fica_constante_na_serie_completa():
    feats = t.construir_features(_serie(1500))
    for coluna in t.FEATURES:
        assert feats[coluna].dropna().std() > 0, f"{coluna} e constante"


# ------------------------------------------------- rotulo sem vazamento futuro


def test_rotulo_do_passado_nao_muda_quando_o_futuro_muda():
    """Regressao do vazamento.

    Se o piso de ATR do rotulo usasse a serie inteira, truncar o futuro
    mudaria o rotulo do passado. Aqui os rotulos do passado tem de ser
    identicos com e sem a cauda.
    """
    df = _serie(3000)
    lookahead = 10
    completo = t.construir_target(df, lookahead)

    # Recorta a serie no meio, mantendo bem mais history do que o lookahead.
    corte = 2000
    parcial = t.construir_target(df.iloc[:corte], lookahead)

    # Compara a mesma janela de tempo nos dois rotulos.
    janela = completo[completo["Time"] < df["Time"].iloc[corte - 100]]
    por_tempo_completo = janela.set_index("Time")["Target"]
    por_tempo_parcial = parcial[parcial["Time"] < df["Time"].iloc[corte - 100]].set_index("Time")["Target"]

    comum = por_tempo_completo.index.intersection(por_tempo_parcial.index)
    assert len(comum) > 100, "janela de comparacao pequena demais para o teste"
    assert por_tempo_completo.loc[comum].equals(por_tempo_parcial.loc[comum]), (
        "o rotulo do passado mudou quando o futuro mudou: ha vazamento"
    )


def test_rotulo_tem_tres_classes_dentro_do_esperado():
    df = t.construir_target(_serie(3000), 1)
    classes = set(df["Target"].unique())
    assert classes <= {0, 1, 2}, f"classes fora do contrato SELL/NEUTRAL/BUY: {classes}"
    assert len(classes) == 3, "serie sintetica deveria exercitar as 3 classes"


# ------------------------------------------------------------------ treino


def test_split_e_cronologico_com_purga():
    """O treino tem que estar no passado e separado do teste por lookahead."""
    df = _serie(3000)
    base = t.construir_features(t.reamostrar(df, "M5"))
    base = t.construir_target(base, t.LOOKAHEAD["M5"])
    base = base.replace([np.inf, -np.inf], np.nan).dropna(subset=t.FEATURES)

    fronteira = int(len(base) * 0.8)
    purga = 10
    fim_treino = fronteira - purga
    inicio_teste = fronteira + purga
    # Nenhuma linha de treino pode ser posterior a qualquer linha de teste.
    assert base["Time"].iloc[fim_treino - 1] < base["Time"].iloc[inicio_teste]
    # E o buraco entre os dois conjuntos e de 2x o lookahead, para que o
    # rotulo das ultimas linhas de treino nao enxergue o periodo de teste.
    buraco = base["Time"].iloc[inicio_teste] - base["Time"].iloc[fim_treino - 1]
    assert buraco >= pd.Timedelta(minutes=2 * 10 * 5)


def test_treino_reprova_serie_curta_sem_tentar_publicar():
    r = t.treinar(_serie(120), "XAUUSD", "M5", min_amostras=800)
    assert r.Treinou is False
    assert r.publicavel is False
    assert "insuficientes" in r.motivo


def test_treino_reprova_sem_dados():
    r = t.treinar(pd.DataFrame(), "XAUUSD", "M5")
    assert r.Treinou is False
    assert r.publicavel is False


def test_treino_reprova_timeframe_invalido():
    r = t.treinar(_serie(3000), "XAUUSD", "M2")
    assert r.Treinou is False
    assert r.publicavel is False
    assert "nao suportado" in r.motivo


def test_requer_minimo_de_amostras_apos_reamostragem():
    """H1 a partir de M5 reduz muito a contagem; o erro tem de ser claro."""
    r = t.treinar(_serie(3000), "XAUUSD", "H1", min_amostras=800)
    assert r.Treinou is False
    assert "insuficientes" in r.motivo


# --------------------------------------------------------- porta de qualidade


def test_porta_de_qualidade_bloqueia_edge_insuficiente():
    """Com min_edge impossivel, nenhum modelo pode ser publicado."""
    r = t.treinar(_serie(3000), "XAUUSD", "M5", min_edge=0.99)
    assert r.Treinou is True, "o treino deveria rodar; o bloqueio e so na publicacao"
    assert r.publicavel is False
    assert r.edge is not None and r.edge < 0.99
    assert "abaixo do minimo" in r.motivo


def test_porta_de_qualidade_libera_quando_edge_supera_minimo():
    r = t.treinar(_serie(3000), "XAUUSD", "M5", min_edge=-1.0)
    assert r.Treinou is True
    assert r.publicavel is True, r.motivo
    assert r.edge is not None and r.edge >= -1.0


def test_edge_e_calculado_contra_o_palpite_da_arvore():
    r = t.treinar(_serie(3000), "XAUUSD", "M5", min_edge=-1.0)
    assert r.palpite == pytest.approx(1 / 3)
    assert r.edge == pytest.approx(r.accuracy - r.palpite)


def test_meta_publicavel_false_tem_motivo_explicito():
    r = t.treinar(_serie(3000), "XAUUSD", "M5", min_edge=0.99)
    assert r.meta["publicable"] is False
    assert r.meta["publish_reason"]
    assert r.meta["metrics"]["edge"] == pytest.approx(r.edge)
    assert r.meta["feature_version"] == t.FEATURE_VERSION


# ------------------------------------------------- walk-forward / selection bias


def _base_pronta(n: int = 6000) -> pd.DataFrame:
    base = t.construir_features(t.reamostrar(_serie(n), "M5"))
    base = t.construir_target(base, t.LOOKAHEAD["M5"])
    return base.replace([np.inf, -np.inf], np.nan).dropna(subset=t.FEATURES)


def test_walk_forward_gera_varios_folds_cronologicos():
    folds = t.walk_forward(_base_pronta(), n_folds=4)
    assert len(folds) == 4
    for f in folds:
        assert f["edge"] == pytest.approx(f["accuracy"] - f["baseline"])
        assert f["train"] > 0 and f["test"] > 0


def test_walk_forward_cresce_a_janela_de_treino():
    """Expanding window: cada fold ve mais historico que o anterior."""
    folds = t.walk_forward(_base_pronta(), n_folds=4)
    tamanhos = [f["train"] for f in folds]
    assert tamanhos == sorted(tamanhos)
    assert tamanhos[-1] > tamanhos[0]


def test_walk_forward_nao_fala_com_serie_curta():
    assert t.walk_forward(_base_pronta(n=300), n_folds=4) == []


def test_edge_consistente_recusa_folds_mistos():
    folds = [
        {"edge": 0.20}, {"edge": -0.10}, {"edge": 0.05}, {"edge": -0.08}, {"edge": 0.02},
    ]
    ok, motivo = t.edge_consistente(folds)
    assert ok is False
    assert "instavel" in motivo or "nao positivo" in motivo


def test_edge_consistente_recusa_media_negativa():
    """3 de 5 positivos, mas a media e negativa: nao e advantage."""
    folds = [{"edge": 0.30}, {"edge": 0.20}, {"edge": 0.10}, {"edge": -0.40}, {"edge": -0.35}]
    ok, _ = t.edge_consistente(folds)
    assert ok is False


def test_edge_consistente_aceita_edge_robusto():
    folds = [{"edge": 0.12}, {"edge": 0.09}, {"edge": 0.14}, {"edge": 0.07}, {"edge": 0.11}]
    ok, motivo = t.edge_consistente(folds)
    assert ok is True
    assert "media" in motivo


def test_edge_consistente_sem_folds_nao_aprova():
    ok, motivo = t.edge_consistente([])
    assert ok is False
    assert "sem folds" in motivo


def test_publicacao_exige_edge_e_consistencia():
    """A porta e as duas condicoes: edge no split E edge estavel nos folds."""
    r = t.treinar(_serie(6000), "XAUUSD", "M5", min_edge=-1.0)
    assert r.Treinou is True
    assert r.folds, "o treino tem de produzir folds para validar estabilidade"
    # Com min_edge=-1.0 o edge passa; a decisao fica so com a consistencia.
    assert r.publicavel == r.estavel
    assert r.meta["metrics"]["edge_estavel"] is r.estavel
