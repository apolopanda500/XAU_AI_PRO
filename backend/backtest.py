from __future__ import annotations

import math
from typing import Any


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    multiplier = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append((value - result[-1]) * multiplier + result[-1])
    return result


def _rsi(values: list[float], period: int = 14) -> list[float]:
    if len(values) <= period:
        return [50.0] * len(values)
    result = [50.0] * len(values)
    gains = 0.0
    losses = 0.0
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    average_gain = gains / period
    average_loss = losses / period
    result[period] = 100.0 if average_loss == 0 else 100.0 - (100.0 / (1.0 + average_gain / average_loss))
    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        average_gain = (average_gain * (period - 1) + max(change, 0.0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0.0)) / period
        result[index] = 100.0 if average_loss == 0 else 100.0 - (100.0 / (1.0 + average_gain / average_loss))
    return result


def _normalise_candles(candles: list[dict[str, Any]]) -> list[dict[str, float]]:
    normalized: list[dict[str, float]] = []
    for candle in candles:
        values = {name: float(candle.get(name, 0)) for name in ("open", "high", "low", "close")}
        if not all(math.isfinite(value) and value > 0 for value in values.values()):
            raise ValueError("candle inválido")
        if values["high"] < max(values["open"], values["close"]) or values["low"] > min(values["open"], values["close"]):
            raise ValueError("candle OHLC inconsistente")
        normalized.append(values)
    return normalized


# --------------------------------------------------------------------------
# Decisao: o MODELO treinado, nao uma heuristica local
# --------------------------------------------------------------------------
# Antes desta mudanca, `run_backtest` decidia compra e venda por uma regra fixa
# (`RSI < 35` com cruzamento de MACD) e nao carregava nenhum `.pkl`. A tela
# mostrava, portanto, o desempenho de uma estrategia que NAO e a IA que opera
# a conta: o operador julgava o modelo por um numero sem relacao com ele. Pior,
# como a heuristica e rara, o resultado costumeiro era zero trade com 0% de
# acerto, e `tests/test_backtest.py` nunca verificou `trade_count`, entao um
# backtest que nao abre posicao nenhuma passava como saudavel.
#
# A decisao agora vem do mesmo artefato que `backend/ai_inference.py` usa ao
# vivo, pelas mesmas features e na mesma ordem do treino. Sem modelo publicado
# para o par pedido, o backtest NAO inventa sinal: devolve o motivo, para a
# interface dizer que nao mediu nada em vez de exibir um numero falso.


def _decisao_do_modelo(
    symbol: str,
    timeframe: str,
    candles: list[dict[str, float]],
) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    """Sinais do modelo publicado e a procedencia da decisao.

    Retorna `(sinais, info)`. `sinais` e None quando nao ha modelo publicado,
    e `info["reason"]` diz exatamente por que.
    """
    info: dict[str, Any] = {
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "decision_source": "model",
        "model": "",
        "feature_hash": "",
    }
    try:
        import numpy as np
        import pandas as pd

        from backend import ai_inference
        from Python.ai import train_v2 as t
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        info.update(decision_source="indisponivel", reason=f"dependencia ausente: {exc}")
        return None, info

    if timeframe.upper() not in t.MINUTOS_TIMEFRAME:
        info.update(decision_source="indisponivel", reason=f"timeframe nao suportado: {timeframe.upper()}")
        return None, info

    modelo, meta = ai_inference._carregar(symbol, timeframe)
    if modelo is None:
        info.update(
            decision_source="indisponivel",
            reason=meta.get("publish_reason") or "modelo nao publicado ou ausente",
        )
        return None, info

    try:
        # Mesmo DataFrame que o treino e a inferencia ao vivo usam.
        base = pd.DataFrame(candles)
        for coluna, valor in (
            ("Time", pd.RangeIndex(len(base))),
            ("Open", base["open"]),
            ("High", base["high"]),
            ("Low", base["low"]),
            ("Close", base["close"]),
            ("Volume", 0.0),
            ("ATR", np.nan),
            ("ADX", np.nan),
            ("RSI", np.nan),
        ):
            if coluna not in base.columns:
                base[coluna] = valor

        janela = t.reamostrar(base, timeframe)
        derivada = t.construir_features(janela)
        derivada = derivada.replace([np.inf, -np.inf], np.nan).dropna(subset=t.FEATURES)
        if derivada.empty:
            info.update(decision_source="indisponivel", reason="features incompletas apos derivacao")
            return None, info

        try:
            modelo.n_jobs = 1
        except Exception:
            pass
        probs = modelo.predict_proba(derivada[t.FEATURES])
        decisoes = probs.argmax(axis=1)

        sinais: list[dict[str, Any]] = []
        # Deslocamento entre a serie de entrada e a serie derivada: as
        # primeiras linhas morrem no warm-up das features. Sem isso, a decisao
        # do modelo seria lida no candle errado.
        offset = len(base) - len(derivada)
        for posicao in range(len(derivada)):
            probs_linha = probs[posicao]
            sinais.append({
                "index": posicao + offset,
                "signal": {0: "SELL", 1: "NEUTRAL", 2: "BUY"}.get(int(decisoes[posicao]), "NEUTRAL"),
                "confidence": float(max(probs_linha)) * 100.0,
            })
        info.update(
            model=f"{symbol.upper()}_{timeframe.upper()}",
            feature_hash=str(t.feature_hash()),
            edge=(meta.get("metrics") or {}).get("edge"),
            accuracy=(meta.get("metrics") or {}).get("accuracy"),
            min_edge=meta.get("min_edge"),
            publicable=bool(meta.get("publicable")),
            rows_evaluated=len(derivada),
            warmup_offset=offset,
        )
        return sinais, info
    except Exception as exc:  # pragma: no cover - defensivo
        info.update(decision_source="indisponivel", reason=f"falha ao inferir: {exc}")
        return None, info


def run_backtest(
    candles: list[dict[str, Any]],
    *,
    symbol: str,
    timeframe: str = "M15",
    initial_balance: float = 10_000.0,
    risk_pct: float = 1.0,
    stop_loss_points: float = 300.0,
    take_profit_points: float = 600.0,
    point: float = 0.01,
    contract_size: float = 100.0,
    spread_points: float = 0.0,
    max_volume: float = 0.10,
) -> dict[str, Any]:
    """Mede o MODELO publicado, nao uma heuristica local.

    `symbol` e OBRIGATORIO (antes tinha `= "XAUUSD"`). Um backtest de ouro
    apresentado sem dizer qual ativo mediu faz o operador julgar o modelo por
    um numero que nao pediu. A regra do projeto: nenhum simbolo e presumido.

    O backtest tambem nao decide sozinho: `point` e `contract_size` variam por
    classe de ativo (forex tem pip e swap, metal tem contrato de 100 oz,
    indice tem tick de 0,5). Deixados no padrao, sao o chamador que tem de
    dizer — e enquanto ele nao disser, o resultado declara os valores usados
    em `params`, para nenhum numero aparecer sem contexto.
    """
    simbolo = str(symbol or "").strip().upper()
    if not simbolo:
        raise ValueError("informe o simbolo: o projeto nao presume ativo padrao")
    if len(candles) < 30:
        raise ValueError("são necessários pelo menos 30 candles")
    values = _normalise_candles(candles)
    if not all(math.isfinite(float(value)) and float(value) > 0 for value in (initial_balance, risk_pct, stop_loss_points, take_profit_points, point, contract_size, max_volume)):
        raise ValueError("parâmetros de risco inválidos")
    if risk_pct > 10 or stop_loss_points <= 0 or take_profit_points <= 0 or max_volume <= 0 or spread_points < 0:
        raise ValueError("parâmetros de risco fora do intervalo permitido")

    # O sinal vem do modelo publicado. Sem modelo, NAO existe sinal: o
    # resultado sai honesto, com zero trades e o motivo, em vez de uma curva
    # de equidade que sobe porque um gerador de numero aleatorio foi usado
    # como se fosse estrategia.
    # `t.construir_features` descarta as primeiras linhas (janelas de
    # warm-up do RSI/ATR/ewm). Como os sinais ficam indexados pela posicao da
    # serie derivada, o deslocamento tem de ser conhecido senao a decisao do
    # modelo seria atribuida ao candle errado.
    # Usa `simbolo` (normalizado e validado), nao o `symbol` cru: e o mesmo
    # ativo, mas um so caminho de normalizacao no arquivo inteiro.
    sinais, info = _decisao_do_modelo(simbolo, timeframe, values)
    sinais_por_indice = {s["index"]: s for s in (sinais or [])}

    balance = float(initial_balance)
    position: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    equity_curve = [balance]

    total = len(values)
    for index in range(total):
        candle = values[index]
        if position is not None:
            direction = position["direction"]
            stop_hit = candle["low"] <= position["stop"] if direction == "buy" else candle["high"] >= position["stop"]
            target_hit = candle["high"] >= position["target"] if direction == "buy" else candle["low"] <= position["target"]
            if stop_hit or target_hit:
                exit_price = position["stop"] if stop_hit else position["target"]
                direction_multiplier = 1 if direction == "buy" else -1
                gross = (exit_price - position["entry"]) * position["quantity"] * contract_size * direction_multiplier
                cost = spread_points * point * position["quantity"] * contract_size
                pnl = gross - cost
                balance += pnl
                trades.append({**position, "exit_index": index, "exit_price": exit_price, "pnl": pnl, "reason": "stop" if stop_hit else "target"})
                position = None
                equity_curve.append(balance)
            continue

        # Entrada somente onde o modelo publicado decidiu. `indices` mapeia a
        # posicao na serie de features para o candle original; a serie
        # derivada pode ser menor que a serie de entrada.
        sinal = sinais_por_indice.get(index)
        if sinal is None or sinal["signal"] not in ("BUY", "SELL"):
            continue
        direction = "buy" if sinal["signal"] == "BUY" else "sell"
        stop_distance = stop_loss_points * point
        target_distance = take_profit_points * point
        risk_amount = balance * risk_pct / 100.0
        quantity = min(max_volume, risk_amount / (stop_distance * contract_size))
        entry = candle["close"]
        position = {
            "direction": direction,
            "entry_index": index,
            "entry": entry,
            "quantity": quantity,
            "confidence": sinal["confidence"],
            "stop": entry - stop_distance if direction == "buy" else entry + stop_distance,
            "target": entry + target_distance if direction == "buy" else entry - target_distance,
        }

    if position is not None:
        index = len(values) - 1
        exit_price = values[index]["close"]
        gross = (exit_price - position["entry"]) * position["quantity"] * contract_size * (1 if position["direction"] == "buy" else -1)
        pnl = gross - spread_points * point * position["quantity"] * contract_size
        balance += pnl
        trades.append({**position, "exit_index": index, "exit_price": exit_price, "pnl": pnl, "reason": "end"})
        equity_curve.append(balance)

    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100.0)
    wins = [trade["pnl"] for trade in trades if trade["pnl"] > 0]
    losses = [trade["pnl"] for trade in trades if trade["pnl"] < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "ok": True,
        "mode": "historical_paper",
        "live_execution": False,
        "candles": len(values),
        "trades": trades,
        "trade_count": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "net_profit": balance - initial_balance,
        "ending_balance": balance,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "max_drawdown_pct": max_drawdown,
        "equity_curve": equity_curve,
        # Procedencia da decisao. A interface tem de poder dizer de onde veio
        # o numero: `decision_source` = "model" significa que o .pkl publicado
        # decidiu; "indisponivel" significa que NAO foi medido o modelo, e o
        # motivo esta em `reason`. Sem isso a tela mostra uma curva e o
        # operador a le como desempenho da IA.
        **info,
        "measured": info.get("decision_source") == "model",
    }
