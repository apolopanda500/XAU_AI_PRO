"""Testes do diagnostico de candles do MT5.

O endpoint /api/backtest/run devolvia 503 com a mensagem "sem candles para X" e
mais nada. O operator nao conseguia distinguir terminal fechado de simbolo
invalido, e por isso a pendencia "capturar a excecao original do copy_rates"
ficou aberta por semanas. Agora a resposta carrega `reason_code`,
`terminal_open` e `mt5_last_error`.
"""
from __future__ import annotations

import pytest

import backend.mt5_gateway as gw


class _Mt5Falso:
    """Dublê do modulo MetaTrader5."""

    def __init__(self, rates=None, terminal=True, last_error=(0, "sem erro")) -> None:
        self._rates = rates
        self._terminal = terminal
        self._last_error = last_error
        self.chamadas: list[tuple] = []

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        self.chamadas.append((symbol, timeframe, start, count))
        return self._rates

    def terminal_info(self):
        return object() if self._terminal else None

    def last_error(self):
        return self._last_error


@pytest.fixture
def mt5_falso(monkeypatch):
    def instalar(dublê: _Mt5Falso) -> _Mt5Falso:
        monkeypatch.setattr(gw, "_mt5", lambda: dublê)
        return dublê

    return instalar


def test_terminal_fechado_e_identificado(mt5_falso):
    dublê = mt5_falso(_Mt5Falso(rates=None, terminal=False, last_error=(1, "Falha ao conectar")))
    result = gw._mt5_candles("XAUUSD", "M15", 500)

    assert result["ok"] is False
    assert result["reason_code"] == "terminal_disconnected"
    assert result["terminal_open"] is False
    assert result["mt5_last_error"] == [1, "Falha ao conectar"]
    assert result["count"] == 0
    assert result["live_execution"] if "live_execution" in result else True


def test_terminal_aberto_sem_candles_do_simbolo(mt5_falso):
    dublê = mt5_falso(_Mt5Falso(rates=None, terminal=True, last_error=(2, "Symbol not found")))
    result = gw._mt5_candles("XAUUSDc", "M15", 500)

    assert result["ok"] is False
    assert result["reason_code"] == "no_candles_for_symbol"
    assert result["terminal_open"] is True
    assert result["mt5_last_error"] == [2, "Symbol not found"]
    # A mensagem deixa claro que o simbolo e o suspect, nao o terminal.
    assert "XAUUSDC" in result["error"]


def test_biblioteca_sem_copy_rates(mt5_falso):
    class _SemRates:
        def terminal_info(self):
            return object()

        def last_error(self):
            return (0, "")

    mt5_falso(_SemRates())
    result = gw._mt5_candles("XAUUSD", "M5", 100)
    assert result["ok"] is False
    assert result["reason_code"] == "mt5_api_missing"


def test_last_error_quebrado_nao_derruba_a_rota(mt5_falso):
    dublê = _Mt5Falso(rates=None, terminal=False)

    def _explode():
        raise RuntimeError("falha interna do terminal")

    dublê.last_error = _explode  # type: ignore[method-assign]
    mt5_falso(dublê)

    result = gw._mt5_candles("XAUUSD", "M5", 100)
    # O diagnostico e acessorio: nunca pode transformar um 503 em 500.
    assert result["ok"] is False
    assert result["reason_code"] == "terminal_disconnected"
    assert result["mt5_last_error"] is None


def test_candles_reais_sao_ordenados_e_contados(mt5_falso):
    linhas = [
        {"time": 200, "open": 2.0, "high": 2.5, "low": 1.5, "close": 2.2, "tick_volume": 10, "spread": 5},
        {"time": 100, "open": 1.0, "high": 1.5, "low": 0.5, "close": 1.2, "tick_volume": 8, "spread": 4},
        {"time": 150, "open": 1.5, "high": 2.0, "low": 1.0, "close": 1.8, "tick_volume": 9, "spread": 4},
    ]
    mt5_falso(_Mt5Falso(rates=linhas, terminal=True))
    result = gw._mt5_candles("XAUUSD", "M15", 500)

    assert result["ok"] is True
    assert result["count"] == 3
    assert [c["time"] for c in result["candles"]] == [100, 150, 200]
    assert result["source"] == "mt5_gateway"


def test_timeframe_invalido_falha_explicito(mt5_falso):
    mt5_falso(_Mt5Falso(rates=[]))
    with pytest.raises(ValueError, match="timeframe MT5 invalido"):
        gw._mt5_candles("XAUUSD", "M2", 100)


def test_simbolo_e_normalizado(mt5_falso):
    dublê = mt5_falso(_Mt5Falso(rates=[], terminal=True))
    gw._mt5_candles("  xauusd  ", "M5", 100)
    assert dublê.chamadas[0][0] == "XAUUSD"
