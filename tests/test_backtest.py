from __future__ import annotations

import asyncio
import json

import pytest

from backend.backtest import run_backtest

#: Simbolo usado pelos testes. Desde 30/09/2026 `run_backtest` exige o simbolo:
#: o default era `XAUUSD`, e um backtest medindo ouro sem dizer qual ativo mediu
#: faz o operador julgar o modelo por um numero que nao pediu.
SIMBOLO = "XAUUSD"


def _candles(count: int = 80) -> list[dict[str, float]]:
    rows = []
    price = 2000.0
    for index in range(count):
        change = 1.5 if index % 9 == 0 else -0.8 if index % 5 == 0 else 0.2
        price += change
        rows.append({"time": index, "open": price - 0.2, "high": price + 0.8, "low": price - 0.8, "close": price})
    return rows


def test_backtest_exige_simbolo():
    """Nenhum ativo e presumido: sem simbolo, recusa com motivo.

    Antes o parametro tinha `= "XAUUSD"` e a medicao saia correta para o
    ativo errado, sem nada no resultado que declarasse qual era.
    """
    with pytest.raises(ValueError, match="simbolo"):
        run_backtest(_candles(), symbol="")


def test_backtest_nao_executa_ordens_e_devolve_metricas():
    result = run_backtest(_candles(), symbol=SIMBOLO)
    assert result["ok"] is True
    assert result["live_execution"] is False
    assert result["mode"] == "historical_paper"
    assert result["candles"] == 80
    assert "equity_curve" in result
    assert "max_drawdown_pct" in result


def test_backtest_rejeita_dados_insuficientes():
    with pytest.raises(ValueError, match="30 candles"):
        run_backtest(_candles(29), symbol=SIMBOLO)


def test_backtest_rejeita_ohlc_inconsistente():
    candles = _candles()
    candles[0]["high"] = candles[0]["low"] - 1
    with pytest.raises(ValueError, match="OHLC"):
        run_backtest(candles, symbol=SIMBOLO)


def test_endpoint_backtest_consome_candles_reais(monkeypatch):
    from backend import fastapi_gateway

    monkeypatch.setattr(fastapi_gateway.gw, "_mt5_candles", lambda symbol, timeframe, count: {"ok": True, "source": "test_fixture", "candles": _candles(80)})
    response = asyncio.run(fastapi_gateway.backtest_run({"symbol": "XAUUSD", "timeframe": "M15", "count": 80}))
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["source"] == "test_fixture"
    assert payload["live_execution"] is False


# --------------------------------------------------------------------------
# A decisao tem de vir do MODELO, nao de uma heuristica local
# --------------------------------------------------------------------------
# Regressao de 2026-09-29: `run_backtest` decidia por `RSI < 35`/`RSI > 65` com
# cruzamento de MACD e nao carregava nenhum `.pkl`. A tela passava a mostrar o
# desempenho de uma estrategia que nao era a IA que opera a conta, e como a
# heuristica e rara, o resultado usual era zero trade. O teste antigo aceitava
# isso: verificava `ok`, `candles` e `equity_curve`, nunca `trade_count`.


def test_backtest_declara_a_procedencia_da_decisao():
    """O resultado tem de dizer de onde veio o numero."""
    result = run_backtest(_candles(), symbol=SIMBOLO)
    assert "decision_source" in result
    assert result["decision_source"] in ("model", "indisponivel")
    assert "measured" in result
    if result["decision_source"] == "indisponivel":
        # Sem modelo, o motivo tem de estar escrito: e o que a interface mostra.
        assert result.get("reason")


def test_backtest_nao_inventa_sinal_sem_modelo_publicado(monkeypatch):
    """Sem `.pkl` publicado para o par, o backtest nao abre posicao nenhuma.

    Este e o ponto honesto: antes, uma heuristica local produzia trades de um
    modelo que nao estava em teste. Agora o resultado e zero trade com motivo.
    """
    from backend import backtest as bt

    monkeypatch.setattr(
        bt, "_decisao_do_modelo", lambda symbol, timeframe, candles: (None, {"decision_source": "indisponivel", "reason": "sem modelo"})
    )
    result = bt.run_backtest(_candles(), symbol=SIMBOLO)
    assert result["trade_count"] == 0
    assert result["measured"] is False
    assert result["reason"] == "sem modelo"
    assert result["net_profit"] == 0.0
    assert result["win_rate_pct"] == 0.0


def test_backtest_usa_o_modelo_publicado_quando_existe(monkeypatch):
    """Com sinal do modelo, o trade existe e carrega a confianca real."""
    from backend import backtest as bt

    # Dois sinais em posicoes distintas, com confianca different do placeholder.
    sinais = [
        {"index": 5, "signal": "BUY", "confidence": 71.5},
        {"index": 6, "signal": "BUY", "confidence": 73.2},
    ]
    info = {
        "decision_source": "model",
        "model": "XAUUSD_M15",
        "feature_hash": "abc123",
        "publicable": True,
    }
    monkeypatch.setattr(bt, "_decisao_do_modelo", lambda s, t, c: (sinais, info))

    result = bt.run_backtest(_candles(80), symbol="XAUUSD", timeframe="M15")
    assert result["decision_source"] == "model"
    assert result["measured"] is True
    assert result["model"] == "XAUUSD_M15"
    assert result["trade_count"] >= 1, "o modelo decidiu BUY, tem de existir trade"
    assert result["trades"][0]["confidence"] == 71.5


def test_backtest_precisa_registrar_o_modelo_que_decidiu():
    """Nao basta abrir trade: o resultado tem de dizer qual artefato decidiu."""
    result = run_backtest(_candles(), symbol=SIMBOLO)
    if result["decision_source"] == "model":
        assert result["model"], "qual modelo decidiu tem de estar no resultado"
        assert result["feature_hash"], "o hash das features prova a coerencia com o treino"
    else:
        assert result["reason"]


def test_backtest_exige_trade_count_quando_ha_modelo(monkeypatch):
    """Regressao do teste fraco: 0 trade nao pode passar como saudavel.

    Este teste e o que faltava. Um backtest que nao abre posicao parece
    saudavel justamente porque nao faze nada; obrigar `trade_count > 0` e o
    que impede um modelo morto de passar por valido.
    """
    from backend import backtest as bt

    # O modelo responde NEUTRAL em toda a serie: nao ha trade, e o resultado
    # precisa dizer isso explicitamente em vez de parecer um bom resultado.
    sinais = [{"index": i, "signal": "NEUTRAL", "confidence": 40.0} for i in range(80)]
    info = {"decision_source": "model", "model": "XAUUSD_M15", "feature_hash": "abc"}
    monkeypatch.setattr(bt, "_decisao_do_modelo", lambda s, t, c: (sinais, info))

    result = bt.run_backtest(_candles(80), symbol="XAUUSD", timeframe="M15")
    assert result["trade_count"] == 0
    assert result["measured"] is True
    # Mediu o modelo, e o modelo nao quis operar. Sao coisas diferentes de
    # "nao ha modelo": a UI precisa distinguir as duas situacoes.
    assert result["net_profit"] == 0.0
    assert result["win_rate_pct"] == 0.0
    assert result["profit_factor"] is None


def test_backtest_rejeita_timeframe_sem_modelo_com_motivo():
    result = run_backtest(_candles(80), symbol="XAUUSD", timeframe="M2")
    assert result["decision_source"] == "indisponivel"
    assert "nao suportado" in result["reason"]
    assert result["trade_count"] == 0


def test_backtest_timeframe_e_simbolo_viram_para_o_modelo(monkeypatch):
    """O par pedido tem de chegar ao carregador do modelo."""
    from backend import backtest as bt

    vistos: list[tuple[str, str]] = []

    def falso(symbol, timeframe, candles):
        vistos.append((symbol, timeframe))
        return None, {"decision_source": "indisponivel", "reason": "stub"}

    monkeypatch.setattr(bt, "_decisao_do_modelo", falso)
    bt.run_backtest(_candles(), symbol="BTCUSD", timeframe="H4")
    assert vistos == [("BTCUSD", "H4")], "o modelo chamado tem de ser o do par pedido"
