# -*- coding: utf-8 -*-
"""Candles publicos sem conta: o grafico vive sem API conectada.

MEDIDO nas capturas do dono em 12/10/2026: com o MT5 fechado e sem chave de
exchange valida, o grafico mostrava "Candles reais indisponíveis" — e a
decisao do dono e que o grafico NUNCA morre: "ligando ou nao api de contas,
o grafico precisar sempre estar vivo com valores reais".

A cadeia de LEITURA publica ja existe e nao pede credencial: os clientes de
exchange expoem `klines` no endpoint publico, `_exchange_client` so le o
cofre quando `private=True`, e `_universal_candles` chama sem `private`.
Este arquivo trava isso: com o cofre VAZIO (e ate QUEBRADO), os candles
publicos continuam saindo.

Sem rede de verdade aqui: `klines` e duble (formato real da API), e o resto
e o caminho de producao (`_universal_candles` -> `_candles_from_raw`). Um
teste que batesse na api.mexc.com passaria sem internet? Nao — e o CI roda
sem ela. O que se mede e que a CAMADA nao exige credencial, nao a venue.
"""
from __future__ import annotations

import pytest

import backend.mt5_gateway as gw


def _klines_mexc(n: int = 5) -> list[list]:
    """Formato real de `/api/v3/klines`: listas `[openTime, o, h, l, c, v, ...]`."""
    base = 1_769_000_000_000
    return [
        [base + i * 900_000, "85000.5", "85100.0", "84900.0", "85050.0", "12.5", base + (i + 1) * 900_000]
        for i in range(n)
    ]


def _klines_binance(n: int = 5) -> list[list]:
    base = 1_769_000_000_000
    return [
        [base + i * 3_600_000, "85000.50", "85100.00", "84900.00", "85050.00", "80.22",
         base + (i + 1) * 3_600_000, "0", 0, "0", "0", "0"]
        for i in range(n)
    ]


@pytest.fixture
def sem_cofre(monkeypatch):
    """O cofre de credenciais nao existe — e nem pode ser consultado.

    Se qualquer ponto do caminho de LEITURA encostar no cofre, este dublê
    levanta e o teste reprova com o nome de quem chamou.
    """
    def _proibido(*args, **kwargs):
        raise AssertionError(
            "leitura publica encostou no cofre de credenciais: "
            f"args={args} kwargs={kwargs}"
        )

    monkeypatch.setattr(gw, "_stored_exchange_credentials", _proibido)


def test_candles_mexc_saem_sem_credencial(monkeypatch, sem_cofre):
    monkeypatch.setattr(
        "backend.mexc_client.MexcClient.klines", lambda self, *a, **k: _klines_mexc()
    )
    resposta = gw._universal_candles("mexc", "crypto-spot", "BTCUSDT", "M15", 5)

    assert resposta["candles"], "sem candles publicos, o grafico morre sem conta"
    assert resposta["count"] == 5
    assert resposta.get("error") is None
    primeira = resposta["candles"][0]
    assert primeira["close"] == 85050.0
    # Tempo em ISO real (ms da venue viram segundos): nunca "agora" inventado.
    assert str(primeira["timestamp"]).startswith("2026-")


def test_candles_binance_saem_sem_credencial(monkeypatch, sem_cofre):
    monkeypatch.setattr(
        "backend.binance_client.BinanceClient.klines", lambda self, *a, **k: _klines_binance()
    )
    resposta = gw._universal_candles("binance", "crypto-spot", "BTCUSDT", "M15", 5)

    assert resposta["count"] == 5
    assert resposta.get("error") is None


def test_conta_ainda_exige_credencial(monkeypatch):
    """PROVA NEGATIVA: liberar leitura nao libera conta.

    O `private=True` continua lendo o cofre: este teste falha se a leitura
    publica e a privada passarem a usar o mesmo caminho sem distinguir.
    """
    chamadas: list = []

    def _cofre(*args, **kwargs):
        chamadas.append(args)
        return None

    monkeypatch.setattr(gw, "_stored_exchange_credentials", _cofre)
    cliente = gw._exchange_client("mexc", "crypto-spot", private=True)
    assert chamadas, "caminho privado nao consultou o cofre"
    assert cliente.account_id == ""
