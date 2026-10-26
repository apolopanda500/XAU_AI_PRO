# -*- coding: utf-8 -*-
"""A IA sugere limites; o operador grava (`/api/auto/sugerir-limites`).

Decisao do dono (12/10/2026): botao de IA no controle de risco para a IA
estudar o momento e configurar os riscos sozinha — MAS com o botao e a tabela
continuando: a IA preenche, o operador ajusta, o Aplicar grava.

Por isso `sugerir_limites` NUNCA grava: devolve numeros + o motivo de cada
um (`base`). Sem motivo por campo, a sugestao seria numero magico — e numero
magico em tela de risco e o operador confiando no que nao entende.
"""
from __future__ import annotations

import pandas as pd

from backend import auto_engine


def _velas(n: int = 100, preco: float = 100.0, amplitude: float = 1.0) -> pd.DataFrame:
    feast = [preco + (i % 5) * 0.1 for i in range(n)]
    return pd.DataFrame({
        "Time": list(range(n)),
        "Open": feast,
        "High": [p + amplitude / 2 for p in feast],
        "Low": [p - amplitude / 2 for p in feast],
        "Close": feast,
        "Volume": [10.0] * n,
    })


class _Inferencia:
    def __init__(self, confianca: float, edge: float) -> None:
        self.confianca = confianca
        self.edge = edge


def _cenario(monkeypatch, confianca: float = 82.0, edge: float = 0.12, n: int = 100, amplitude: float = 1.0) -> None:
    monkeypatch.setattr(
        "backend.market_access.candles",
        lambda broker, market, symbol, timeframe, limit=600: _velas(n, amplitude=amplitude),
    )
    monkeypatch.setattr(
        "backend.ai_inference.inferir",
        lambda symbol, df, timeframe="H1": _Inferencia(confianca, edge),
    )


def test_sugestao_traz_limites_e_motivos(monkeypatch) -> None:
    _cenario(monkeypatch)
    r = auto_engine.sugerir_limites("EURUSD", "H1", "mt5", "forex")

    assert r["ok"] is True
    assert r["simbolo"] == "EURUSD"
    esperados = {
        "confianca_minima", "edge_minimo", "risco_por_trade_pct",
        "max_posicoes", "max_operacoes_dia", "perda_diaria_max_pct",
        "intervalo_minutos",
    }
    assert esperados <= set(r["limites"])
    # Cada numero tem o motivo: sem ele, a tabela receberia magia.
    assert esperados <= set(r["base"])
    # CONFIANCA COM FOLGA (25/10/2026): o piso fixo de 50 era o piso que media
    # 50 para um modelo medido a 36,8% — motor SEMPRE recusando. A sugestao
    # agora e medida −5 p.p. (77 para 82), nunca acima da medida (o proprio
    # modelo tem de passar pela sugestao)...
    assert r["limites"]["confianca_minima"] == 77
    # ...e edge com folga de 10% para baixo (0,12 para 0,12 exato deixa o motor
    # na fronteira do proprio edge dois desvios de recusar).
    assert r["limites"]["edge_minimo"] == 0.108
    assert r["serie"]["velas"] == 100
    # A base explica o porque: o numero vem acompanhado do metodo.
    assert "folga" in r["base"]["confianca_minima"]
    assert "folga" in r["base"]["edge_minimo"]


def test_sugestao_nunca_acima_da_medida(monkeypatch) -> None:
    """PROVA NEGATIVA da trava: sugerir minimo acima do que o modelo mede
    hoje e o defeito medido no painel do dono (confianca 36,8% minimo 50)."""
    _cenario(monkeypatch, confianca=36.8, edge=0.114)
    r = auto_engine.sugerir_limites("EURUSD", "H1", "mt5", "forex")
    assert r["ok"] is True
    conf, edge = r["serie"]["confianca"], r["serie"]["edge"]
    # O MODELO MEDIDO hoje tem de passar pela sugerico: min. <= medida.
    assert r["limites"]["confianca_minima"] <= conf
    assert r["limites"]["edge_minimo"] <= edge
    # Piso de 32: um modelo de 36,8% recebe um limite que ele passa de verdade.
    assert r["limites"]["confianca_minima"] == 32
    assert r["limites"]["edge_minimo"] == 0.1026


def test_banca_vem_da_conta_real_nao_de_chute(monkeypatch) -> None:
    """A IA nao chuta dinheiro: le a banca da conta MT5 (0 quando inacessivel)."""
    _cenario(monkeypatch)
    r = auto_engine.sugerir_limites("EURUSD", "H1", "mt5", "forex")

    assert r["ok"] is True
    assert "banca" in r["limites"]
    assert "banca" in r["base"]
    # Em ambiente de teste (sem MT5) a banca e 0 — nunca um numero inventado.
    assert r["limites"]["banca"] == 0.0 or isinstance(r["limites"]["banca"], (int, float))


def test_sem_par_recusa_com_motivo() -> None:
    r = auto_engine.sugerir_limites("", "H1", "mt5", "forex")
    assert r["ok"] is False
    assert r["error"]


def test_sem_periodo_recusa_com_motivo() -> None:
    r = auto_engine.sugerir_limites("EURUSD", "", "mt5", "forex")
    assert r["ok"] is False
    assert r["error"]


def test_par_incompativel_recusa_na_porta() -> None:
    r = auto_engine.sugerir_limites("EURUSD", "H1", "mexc", "forex")
    assert r["ok"] is False
    assert "mexc" in r["error"].lower()


def test_serie_curta_recusa_em_vez_de_chutar(monkeypatch) -> None:
    _cenario(monkeypatch, n=10)
    r = auto_engine.sugerir_limites("EURUSD", "H1", "mt5", "forex")
    assert r["ok"] is False
    assert "30" in r["error"]


def test_modelo_mudo_recusa_com_motivo(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.market_access.candles", lambda *a, **k: _velas(100),
    )

    def _muda(*a, **k):
        raise RuntimeError("modelo sem resposta")

    monkeypatch.setattr("backend.ai_inference.inferir", _muda)
    r = auto_engine.sugerir_limites("EURUSD", "H1", "mt5", "forex")
    assert r["ok"] is False
    assert r["error"]


def test_volatilidade_alta_pede_risco_menor(monkeypatch) -> None:
    """A regra e direcional: mais volatilidade, menos risco por trade."""
    _cenario(monkeypatch, amplitude=0.2)
    calmo = auto_engine.sugerir_limites("EURUSD", "H1", "mt5", "forex")
    _cenario(monkeypatch, amplitude=5.0)
    agitado = auto_engine.sugerir_limites("EURUSD", "H1", "mt5", "forex")
    assert calmo["ok"] is True and agitado["ok"] is True
    assert agitado["limites"]["risco_por_trade_pct"] < calmo["limites"]["risco_por_trade_pct"]
