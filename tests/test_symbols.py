# -*- coding: utf-8 -*-
"""Simbolo canonico para todas as corretoras e todos os formatos.

Uma fonte so (`backend/symbols`): o mesmo ativo em qualquer roupagem
resolve igual. Sem nomes de ativos no codigo — so quote, sufixo e
separador.
"""
from __future__ import annotations

import pytest

from backend.symbols import base, canonico, formas, mesmo_ativo, quote


@pytest.mark.parametrize("entrada,saida", [
    ("BTCUSDT", "BTCUSDT"),
    ("btcusdt", "BTCUSDT"),
    ("BTC/USDT", "BTCUSDT"),
    ("BTC-USDT", "BTCUSDT"),
    ("BTC_USDT", "BTCUSDT"),
    ("BTC USDT", "BTCUSDT"),
    ("XAUUSD.pro", "XAUUSD"),
    ("EURUSD_M", "EURUSD"),
    ("EURUSDc", "EURUSD"),
    ("BTCUSDT_PERP", "BTCUSDT"),
    ("", ""),
])
def test_canonico(entrada, saida):
    assert canonico(entrada) == saida


@pytest.mark.parametrize("entrada,saida", [
    ("BTCUSDT", "BTC"), ("BTCUSD", "BTC"), ("EURUSD", "EUR"),
    ("XAUUSD", "XAU"), ("BTCUSDC", "BTC"),
])
def test_base(entrada, saida):
    assert base(entrada) == saida


def test_mesmo_ativo_entre_venues():
    assert mesmo_ativo("BTCUSDT", "BTCUSD")
    assert mesmo_ativo("BTCUSD", "BTCUSDT")
    assert mesmo_ativo("ETHUSDT", "ETHUSD")


def test_mesmo_ativo_nunca_troca():
    assert not mesmo_ativo("BTCUSDT", "EURUSD")
    assert not mesmo_ativo("BTCUSDT", "ETHUSDT")
    assert not mesmo_ativo("", "BTCUSD")
    assert not mesmo_ativo("BTCUSD", "")
    assert not mesmo_ativo("", "")


def test_formas_traz_literal_primeiro():
    f = formas("BTCUSDT")
    assert f[0] == "BTCUSDT"
    assert "BTCUSD" in f


def test_scope_tem_canonico_sem_trocar_ordem():
    from backend.broker_registry import normalize_read_scope

    scope = normalize_read_scope("mt5", "forex", "btc/usdt")
    assert scope["symbol"] == "BTC/USDT"  # exato p/ corretora, sem corte
    assert scope["symbol_canonical"] == "BTCUSDT"
    # Contrato fracionario preservado na ordem, canonico sem sufixo.
    scope2 = normalize_read_scope("mt5", "metals", "XAUUSD.pro")
    assert scope2["symbol"] == "XAUUSD.PRO"
    assert scope2["symbol_canonical"] == "XAUUSD"
