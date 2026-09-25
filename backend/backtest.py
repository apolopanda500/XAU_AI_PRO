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


def run_backtest(
    candles: list[dict[str, Any]],
    *,
    initial_balance: float = 10_000.0,
    risk_pct: float = 1.0,
    stop_loss_points: float = 300.0,
    take_profit_points: float = 600.0,
    point: float = 0.01,
    contract_size: float = 100.0,
    spread_points: float = 0.0,
    max_volume: float = 0.10,
) -> dict[str, Any]:
    if len(candles) < 30:
        raise ValueError("são necessários pelo menos 30 candles")
    values = _normalise_candles(candles)
    if not all(math.isfinite(float(value)) and float(value) > 0 for value in (initial_balance, risk_pct, stop_loss_points, take_profit_points, point, contract_size, max_volume)):
        raise ValueError("parâmetros de risco inválidos")
    if risk_pct > 10 or stop_loss_points <= 0 or take_profit_points <= 0 or max_volume <= 0 or spread_points < 0:
        raise ValueError("parâmetros de risco fora do intervalo permitido")

    closes = [candle["close"] for candle in values]
    rsi = _rsi(closes)
    fast = _ema(closes, 12)
    slow = _ema(closes, 26)
    macd = [a - b for a, b in zip(fast, slow)]
    signal_line = _ema(macd, 9)
    balance = float(initial_balance)
    position: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    equity_curve = [balance]

    for index in range(26, len(values)):
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

        crossover_up = macd[index] > signal_line[index] and macd[index - 1] <= signal_line[index - 1]
        crossover_down = macd[index] < signal_line[index] and macd[index - 1] >= signal_line[index - 1]
        direction = "buy" if rsi[index] < 35 and crossover_up else "sell" if rsi[index] > 65 and crossover_down else None
        if direction is None:
            continue
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
    }
