"""
XAU AI PRO - Ferramentas do dia a dia
Calculadora de lote, relogio mundial, calendario economico e agenda.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests


def calculate_lot(balance: float, risk_pct: float, stop_loss_points: float,
                  tick_value: float, tick_size: float = 0.01, min_lot: float = 0.01,
                  max_lot: float = 100.0, step: float = 0.01) -> dict[str, Any]:
    """Calcula o lote ideal com base no risco percentual."""
    risk_amount = balance * (risk_pct / 100.0)
    if stop_loss_points <= 0 or tick_value <= 0 or tick_size <= 0:
        return {"lot": 0.0, "risk_amount": risk_amount, "error": "Parametros invalidos"}

    ticks_at_risk = stop_loss_points / tick_size
    monetary_risk_per_lot = ticks_at_risk * tick_value
    if monetary_risk_per_lot <= 0:
        return {"lot": 0.0, "risk_amount": risk_amount, "error": "Risco monetario invalido"}

    raw_lot = risk_amount / monetary_risk_per_lot
    normalized = int(raw_lot / step) * step
    lot = max(min_lot, min(max_lot, normalized))
    return {
        "lot": round(lot, 2),
        "risk_amount": round(risk_amount, 2),
        "monetary_risk_per_lot": round(monetary_risk_per_lot, 2),
        "raw_lot": round(raw_lot, 4),
    }


def world_clocks() -> dict[str, str]:
    """Retorna hora em principais centros financeiros."""
    fmt = "%H:%M:%S"
    return {
        "Sao Paulo": datetime.now(timezone(timedelta(hours=-3))).strftime(fmt),
        "Nova York": datetime.now(timezone(timedelta(hours=-4))).strftime(fmt),
        "Londres": datetime.now(timezone(timedelta(hours=1))).strftime(fmt),
        "Frankfurt": datetime.now(timezone(timedelta(hours=2))).strftime(fmt),
        "Toquio": datetime.now(timezone(timedelta(hours=9))).strftime(fmt),
        "Sydney": datetime.now(timezone(timedelta(hours=10))).strftime(fmt),
    }


def market_session_status() -> dict[str, str]:
    """Retorna status aproximado das sessoes de forex."""
    now = datetime.utcnow()
    hour = now.hour

    def status(open_h: int, close_h: int, name: str) -> str:
        if close_h < open_h:
            active = hour >= open_h or hour < close_h
        else:
            active = open_h <= hour < close_h
        return "ABERTA" if active else "FECHADA"

    return {
        "Sydney": status(22, 7, "Sydney"),
        "Toquio": status(0, 9, "Toquio"),
        "Londres": status(8, 17, "Londres"),
        "Nova York": status(13, 22, "Nova York"),
    }


def economic_calendar_simple() -> list[dict[str, str]]:
    """Calendario economico simples baseado em dia da semana."""
    now = datetime.now()
    weekday = now.weekday()
    events = []

    if weekday == 1:  # terca
        events.append({"time": "08:30 NY", "event": "Inflacao EUA (CPI) - alta volatilidade", "impact": "ALTO"})
    if weekday == 2:
        events.append({"time": "14:00 NY", "event": "Relatorio FOMC / Powell", "impact": "ALTO"})
    if weekday == 3:
        events.append({"time": "08:30 NY", "event": "Pedidos de auxilio-desemprego", "impact": "MEDIO"})
    if weekday == 4:
        events.append({"time": "10:00 NY", "event": "PMI manufatureiro", "impact": "MEDIO"})
    if weekday == 0:
        events.append({"time": "09:45 NY", "event": "PMI servicos China", "impact": "MEDIO"})

    events.append({"time": "Continuo", "event": "Monitorar noticias de Ouro (XAU) e Crypto", "impact": "MEDIO"})
    return events


def fibonacci_levels(low: float, high: float) -> dict[str, float]:
    """Retorna niveis de retracao de Fibonacci."""
    diff = high - low
    ratios = {
        "0%": 0.0,
        "23.6%": 0.236,
        "38.2%": 0.382,
        "50%": 0.5,
        "61.8%": 0.618,
        "78.6%": 0.786,
        "100%": 1.0,
        "138.2%": 1.382,
        "161.8%": 1.618,
    }
    return {k: round(high - diff * v, 5) for k, v in ratios.items()}


def pip_value(lot_size: float, pip: float = 0.0001, contract_size: float = 100_000) -> float:
    """Valor aproximado de 1 pip para o lote informado."""
    return round(lot_size * contract_size * pip, 2)
