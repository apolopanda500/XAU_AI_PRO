# -*- coding: utf-8 -*-
"""Par de exchange: USDT, USDC e o resto, nas quatro corretoras.

O QUE ESTE TESTE TRAVA
======================
O dono reportou *"os ativos sao negociados em USDT"* e *"o robo e os modelos
nao conseguem operar em outras corretoras"*. A causa era `_symbol()` fazendo
so `.upper()`: o que o operador digitasse ia literal para a exchange, e
`BTC/USD`, `XAUUSD` e `EURUSD` voltavam **HTTP 400** sem explicar o motivo.

`backend/exchange_symbols.py` e a fonte unica da regra; os quatro clientes
delegam a ele. Estes testes medem o comportamento **de cada cliente**, nao
apenas do normalizador — porque um cliente que esquece de delegar continua
enviando o par cru.
"""
from __future__ import annotations

import pytest

from backend.binance_client import BinanceClient
from backend.bybit_client import BybitClient
from backend.exchange_symbols import ParInvalido, e_forex, normalizar_par
from backend.mexc_client import MexcClient
from backend.okx_client import OkxClient

#: (normalizador do cliente, True quando a exchange usa hifen)
CLIENTES = [
    (lambda c: MexcClient._symbol(c), False),      # BTCUSDT
    (lambda c: BinanceClient._symbol(c), False),   # BTCUSDT
    (lambda c: BybitClient._symbol(c), False),     # BTCUSDT
    (lambda c: OkxClient._symbol(c), True),         # BTC-USDT
]

IDS = ["mexc", "binance", "bybit", "okx"]


class TestParJaNoFormato:
    """O caso que ja funcionava — a correcao nao pode quebrar."""

    @pytest.mark.parametrize("normaliza,hifen", CLIENTES, ids=IDS)
    def test_btcusdt_passa_intacto(self, normaliza, hifen):
        assert normaliza("BTCUSDT") == ("BTC-USDT" if hifen else "BTCUSDT")

    @pytest.mark.parametrize("normaliza,hifen", CLIENTES, ids=IDS)
    def test_caixa_baixa_e_aceita(self, normaliza, hifen):
        assert normaliza("btcusdt") == ("BTC-USDT" if hifen else "BTCUSDT")


class TestSeparadores:
    """O que o operador digita na tela nao vem padronizado."""

    @pytest.mark.parametrize("entrada", ["BTC/USDT", "BTC-USDT", "BTC_USDT", "BTC USDT"])
    def test_separador_vira_nada(self, entrada):
        assert normalizar_par(entrada) == "BTCUSDT"

    def test_espaco_em_volta(self):
        assert normalizar_par("  BTCUSDT  ") == "BTCUSDT"
class TestQuoteEmUsdt:
    """O pedido do dono: o par cripto e contra USDT."""

    @pytest.mark.parametrize("entrada,saida", [
        ("BTCUSD", "BTCUSDT"),   # par MT5/forex trazido para a exchange
        ("ETHUSD", "ETHUSDT"),
        ("XAUUSD", "XAUUSDT"),   # spot de metais existe na exchange
        ("XAGUSD", "XAGUSDT"),
        ("SOLUSD", "SOLUSDT"),
    ])
    def test_sufixo_usd_vira_usdt(self, entrada, saida):
        assert normalizar_par(entrada) == saida

    @pytest.mark.parametrize("entrada", ["BTCUSDC", "ETHUSDC", "BTCBTC", "ETHETH", "BTCEUR"])
    def test_quote_alternativo_e_preservado(self, entrada):
        assert normalizar_par(entrada) == entrada


class TestForexRecusa:
    """Forex NAO vira par de exchange — recusa, e nao inventa."""

    @pytest.mark.parametrize("entrada", ["EURUSD", "GBPUSD", "USDJPY", "EURUSDT", "GBPUSDT"])
    def test_forex_recusa(self, entrada):
        with pytest.raises(ParInvalido):
            normalizar_par(entrada)

    def test_mensagem_diz_onde_operar_forex(self):
        # A recusa precisa ser actionable: sem isto o operador nao sabe
        # que forex vive no gateway MT5.
        with pytest.raises(ParInvalido, match="MT5"):
            normalizar_par("EURUSD")


class TestRecusaComMotivo:
    def test_vazio_recusa(self):
        with pytest.raises(ParInvalido):
            normalizar_par("")

    def test_sem_base_recusa(self):
        with pytest.raises(ParInvalido):
            normalizar_par("USDT")

    def test_sem_quote_reconhecido_recusa(self):
        # `BTCXYZ` nao tem quote conhecido; devolver cru seria mandar lixo.
        with pytest.raises(ParInvalido, match="quote"):
            normalizar_par("BTCXYZ")

    def test_erro_diz_qual_exchange_recusou(self):
        with pytest.raises(ParInvalido, match="MEXC spot"):
            normalizar_par("EURUSD", contexto="MEXC spot")

    def test_erro_herda_value_error(self):
        # `_universal_run` mapeia `ValueError` para `rejected`. Sem herdar, o
        # gateway levantaria 500 em vez de recusar a ordem.
        assert issubclass(ParInvalido, ValueError)


class TestCadaClienteDelegou:
    """Um cliente que esquece de delegar continua enviando o par cru.

    Este e o teste que teria pegado o bug: `normalizar_par` pode estar
    perfeito e `BinanceClient._symbol` continuar com `.upper()`.
    """

    @pytest.mark.parametrize("normaliza,hifen", CLIENTES, ids=IDS)
    def test_cliente_normaliza_o_forex_como_usdt(self, normaliza, hifen):
        assert normaliza("BTCUSD") == ("BTC-USDT" if hifen else "BTCUSDT")

    @pytest.mark.parametrize("normaliza,hifen", CLIENTES, ids=IDS)
    def test_cliente_recusa_forex(self, normaliza, hifen):
        with pytest.raises(ParInvalido):
            normaliza("EURUSD")

    @pytest.mark.parametrize("normaliza,hifen", CLIENTES, ids=IDS)
    def test_cliente_recusa_vazio(self, normaliza, hifen):
        with pytest.raises(ParInvalido):
            normaliza("")

    def test_okx_usa_hifen_e_as_outras_usam_concatenado(self):
        # A unica diferenca de formato entre as quatro. Se isso mudar, o
        # `inst_id` da OKX passa a devolver par invalido.
        assert OkxClient._symbol("BTCUSDT") == "BTC-USDT"
        assert MexcClient._symbol("BTCUSDT") == "BTCUSDT"
        assert BinanceClient._symbol("BTCUSDT") == "BTCUSDT"
        assert BybitClient._symbol("BTCUSDT") == "BTCUSDT"


@pytest.mark.parametrize("entrada,esperado", [
    ("EURUSD", True), ("GBPUSD", True), ("USDJPY", True), ("EUR/USDT", True),
    ("BTCUSDT", False), ("ETHBTC", False), ("XAUUSDT", False),
])
def test_e_forex_classifica(entrada, esperado):
    assert e_forex(entrada) is esperado