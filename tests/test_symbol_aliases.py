# -*- coding: utf-8 -*-
"""Alias modelo -> corretora por configuracao, sem nomes de ativos no codigo."""
from __future__ import annotations

import pytest

from backend import symbol_aliases as aliases
from backend.symbols import canonico, formas


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


class TestSufixosDaXMGlobal:
    """Os nomes que a XM Global USA de verdade, medidos no terminal.

    POR QUE ESTE TESTE EXISTE
    =========================
    A XM escreve os pares de forex com ponto: `EURUSD.m`, `GBPUSD.c`. O
    `canonico` tirava `.PRO`, `_M`, `_C`, `MICRO` e `MINI` — e nao `.M`/`.C`.
    O ponto NAO esta em `SEPARADORES` (de proposito), entao o resultado era
    `EURUSD.`, com o ponto grudado no nome.

    Efeito medido: o par nao casava com nenhum modelo do catalogo, e a tela
    mostrava "sem modelo carregado" para um ativo que existe na conta. O
    operador via a lista de modelos vazia e nao tinha como escolher.

    A regra do modulo: o ponto faz parte do NOME do contrato na XM. Por isso
    ele nao entra como separador — se entrasse, remover o ponto antes de tirar
    o sufixo apagaria o proprio sufixo (`EURUSD.m` -> `EURUSDm`).
    """

    @pytest.mark.parametrize("entrada,esperado", [
        ("EURUSD.m", "EURUSD"),
        ("GBPUSD.c", "GBPUSD"),
        ("XAUUSD.m", "XAUUSD"),
        ("GBPUSD.ecn", "GBPUSD"),
        ("XAUUSD.raw", "XAUUSD"),
        ("USDJPY.m", "USDJPY"),
        ("AUDUSD.c", "AUDUSD"),
    ])
    def test_sufixo_com_ponto_some(self, entrada, esperado):
        assert canonico(entrada) == esperado

    def test_o_ponto_nunca_sobra_no_nome(self):
        """`EURUSD.` nao e um ativo. Um nome terminado em ponto nao casa com
        nada, e o operador veria "sem modelo" sem entender por que."""
        for entrada in ("EURUSD.m", "GBPUSD.c", "XAUUSD.pro.m", "USDJPY.ecn"):
            assert not canonico(entrada).endswith("."), entrada

    def test_o_ponto_continua_fazendo_parte_do_nome(self):
        """Regressao do outro lado: `EURUSD.EUR` e um par da XM cujo quote
        NAO e USD. Se o ponto virasse separador, isso viraria `EURUSDEUR` e
        o ativo errado seria procurado — pior que nao reconhecer."""
        assert canonico("EURUSD.EUR") == "EURUSD.EUR"

    def test_as_formas_continuam_cobrindo_o_ativo_canonico(self):
        """A forma canonica tem de aparecer entre as formas, senao a busca por
        artefato nao encontra o modelo mesmo com o nome certo."""
        for entrada in ("EURUSD.m", "XAUUSD.pro", "BTCUSD_MICRO"):
            c = canonico(entrada)
            assert c in formas(entrada), entrada

