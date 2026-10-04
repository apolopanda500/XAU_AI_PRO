# -*- coding: utf-8 -*-
"""Alias modelo -> corretora por configuracao, sem nomes de ativos no codigo."""
from __future__ import annotations

from backend import symbol_aliases as aliases


def test_sem_mapa_passa_intacto():
    assert aliases.para_corretora("mt5", "EURUSD", {}) == "EURUSD"
    assert aliases.para_modelo("mt5", "GOLD", {}) == "GOLD"
    assert aliases.para_corretora("mt5", "", {}) == ""


def test_alias_ida_e_volta():
    mapa = {"mt5": {"XAUUSD": "GOLD"}}
    assert aliases.para_corretora("mt5", "XAUUSD", mapa) == "GOLD"
    assert aliases.para_modelo("mt5", "GOLD", mapa) == "XAUUSD"
    assert aliases.para_corretora("mt5", "EURUSD", mapa) == "EURUSD"


def test_outra_corretora_nao_usa_o_alias():
    mapa = {"mt5": {"XAUUSD": "GOLD"}}
    assert aliases.para_corretora("mexc", "XAUUSD", mapa) == "XAUUSD"


def test_motor_envia_simbolo_da_corretora():
    from backend.auto_engine import LimitesAuto, MotorAuto

    m = MotorAuto()
    m.simbolo = "XAUUSD"
    m.timeframe = "H1"
    m.broker = "mt5"
    m.market = "metals"
    m.limites = LimitesAuto(
        banca=1000.0, risco_por_trade_pct=1.0, confianca_minima=55.0,
        edge_minimo=0.05, max_posicoes=2, max_operacoes_dia=20,
        perda_diaria_max_pct=2.0, sl_atr=1.5, tp_atr=3.0, intervalo_minutos=15,
    )
    import backend.symbol_aliases as mod
    real = mod.carregar
    mod.carregar = lambda: {"mt5": {"XAUUSD": "GOLD"}}
    try:
        from tests.test_auto_engine import InferenciaFalsa, risco, enviar_espiao

        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", confianca=72.0, edge=0.12),
            enviar_espiao(chamadas), risco)
    finally:
        mod.carregar = real
    assert d.agir is True
    assert chamadas[0]["symbol"] == "GOLD"
