# -*- coding: utf-8 -*-
"""Quote por corretora: USDT na exchange, USD no MT5, forex recusado com motivo.

A MEXC opera `BTCUSDT`, o MT5 (XM) opera `BTCUSD`. A normalizacao mora nos
clientes (`exchange_symbols.par_exchange`); este arquivo trava o contrato de
ponta a ponta SEM rede: par certo por corretora, recusa acionavel quando nao
ha par, e `market_access.candles` dizendo ONDE recusou.

Sem nomes de ativos no codigo de producao: so sufixo de quote e classe.
"""
from __future__ import annotations

import pytest

from backend.binance_client import BinanceClient
from backend.bybit_client import BybitClient
from backend.exchange_symbols import ParInvalido
from backend.market_access import SemCaminhoError, candles
from backend.mexc_client import MexcClient
from backend.okx_client import OkxClient


class TestParPorCorretora:
    def test_mexc_opera_usdt(self):
        assert MexcClient._symbol("BTCUSD") == "BTCUSDT"
        assert MexcClient._symbol("BTCUSDT") == "BTCUSDT"

    def test_binance_e_bybit_operam_usdt(self):
        assert BinanceClient._symbol("BTCUSD") == "BTCUSDT"
        assert BybitClient._symbol("BTCUSD") == "BTCUSDT"

    def test_okx_usa_hifen(self):
        assert OkxClient._symbol("BTCUSD") == "BTC-USDT"

    def test_usdc_preservado(self):
        assert MexcClient._symbol("BTCUSDC") == "BTCUSDC"

    def test_forex_recusa_com_motivo_mt5(self):
        with pytest.raises(ParInvalido, match="MT5"):
            MexcClient._symbol("EURUSD")


class TestMarketAccessDizOndeRecusou:
    def test_par_recusado_vira_sem_caminho_com_corretora(self, monkeypatch):
        import backend.market_access as acesso

        def _recusa(*args, **kwargs):
            raise ParInvalido("EURUSD nao opera em exchange")

        monkeypatch.setattr("backend.mt5_gateway._universal_candles", _recusa)
        with pytest.raises(SemCaminhoError, match="MEXC"):
            acesso.candles("mexc", "crypto-spot", "EURUSD", "H1")

    def test_simbolo_passa_intacto_para_o_cliente(self, monkeypatch):
        import backend.market_access as acesso

        recebido: dict = {}

        def _ok(broker, market, symbol, timeframe, limit):
            recebido.update(broker=broker, symbol=symbol, timeframe=timeframe)
            return {"candles": []}

        monkeypatch.setattr("backend.mt5_gateway._universal_candles", _ok)
        with pytest.raises(SemCaminhoError):  # sem candles: motivo, nao vazio
            acesso.candles("mexc", "crypto-spot", "BTCUSDT", "H1")
        assert recebido["broker"] == "mexc"
        assert recebido["symbol"] == "BTCUSDT"

    def test_sem_corretora_recusa(self):
        with pytest.raises(SemCaminhoError):
            candles("", "crypto-spot", "BTCUSDT", "H1")

    def test_sem_ativo_recusa(self):
        with pytest.raises(SemCaminhoError):
            candles("mexc", "crypto-spot", "", "H1")
