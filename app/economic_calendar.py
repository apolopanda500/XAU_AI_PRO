# -*- coding: utf-8 -*-
"""Calendario economico + conversao de fusos horarios para o XAU_AI_PRO.

Fornece eventos de alto impacto (semanal, com horarios estimados UTC),
conversao para qualquer fuso, alerta de proximidade e destaque de eventos
relevantes para ouro (USD, XAU). Nao depende de rede (tabela local baseada
em padroes de calendario de alto impacto).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# Eventos de alto impacto recorrentes (horarios aproximados UTC).
# Semana começa na segunda-feira. Usado para gerar agenda de proximas semanas.
_BASE_EVENTS: list[dict[str, Any]] = [
    {"title": "Federal Funds Rate (FOMC)", "currency": "USD", "impact": "alto",
     "day": 2, "hour_utc": 18, "note": "Decisao de juros do Fed."},
    {"title": "FOMC Press Conference", "currency": "USD", "impact": "alto",
     "day": 2, "hour_utc": 18, "note": "Coletiva do Fed."},
    {"title": "Nonfarm Payrolls (NFP)", "currency": "USD", "impact": "alto",
     "day": 4, "hour_utc": 12, "note": "Empregos fora do setor agro."},
    {"title": "Unemployment Rate", "currency": "USD", "impact": "alto",
     "day": 4, "hour_utc": 12, "note": "Taxa de desemprego dos EUA."},
    {"title": "CPI YoY", "currency": "USD", "impact": "alto",
     "day": 2, "hour_utc": 12, "note": "Inflacao ao consumidor."},
    {"title": "Core CPI MoM", "currency": "USD", "impact": "alto",
     "day": 2, "hour_utc": 12, "note": "Inflacao nucleo."},
    {"title": "Retail Sales MoM", "currency": "USD", "impact": "alto",
     "day": 3, "hour_utc": 13, "note": "Vendas no varejo."},
    {"title": "GDP QoQ (advance)", "currency": "USD", "impact": "alto",
     "day": 3, "hour_utc": 12, "note": "PIB americano."},
    {"title": "ISM Manufacturing PMI", "currency": "USD", "impact": "alto",
     "day": 0, "hour_utc": 14, "note": "Atividade industrial."},
    {"title": "Initial Jobless Claims", "currency": "USD", "impact": "medio",
     "day": 3, "hour_utc": 12, "note": "Pedidos de seguro-desemprego."},
    {"title": "ECB Main Refinancing Rate", "currency": "EUR", "impact": "alto",
     "day": 3, "hour_utc": 12, "note": "Juros do BCE."},
    {"title": "BOE Bank Rate", "currency": "GBP", "impact": "alto",
     "day": 3, "hour_utc": 11, "note": "Juros do Banco da Inglaterra."},
    {"title": "BOJ Policy Rate", "currency": "JPY", "impact": "alto",
     "day": 4, "hour_utc": 3, "note": "Juros do Banco do Japao."},
    {"title": "AUD CPI YoY", "currency": "AUD", "impact": "alto",
     "day": 2, "hour_utc": 0, "note": "Inflacao australiana."},
    {"title": "CAD CPI YoY", "currency": "CAD", "impact": "alto",
     "day": 1, "hour_utc": 12, "note": "Inflacao canadense."},
]

_TZ_OFFSETS = {
    "UTC": 0, "BRT": -3, "BRST": -2, "EST": -5, "EDT": -4,
    "CST": -6, "CDT": -5, "PST": -8, "PDT": -7,
    "GMT": 0, "CET": 1, "CEST": 2, "EET": 2, "EEST": 3,
    "JST": 9, "AEST": 10, "AEDT": 11, "NZT": 12, "IST": 5.5,
    "SGT": 8, "HKT": 8, "MSK": 3,
}

# Relevancia para ouro (XAU): eventos USD ou de grande porte.
_GOLD_CURRENCIES = {"USD", "EUR", "JPY", "GBP"}


def tz_list() -> list[str]:
    return sorted(_TZ_OFFSETS, key=lambda k: (_TZ_OFFSETS[k], k))


def convert_to_tz(dt: datetime, tz: str) -> datetime:
    """Converte um datetime (UTC) para o fuso alvo (offset fixo)."""
    offset = _TZ_OFFSETS.get((tz or "UTC").upper(), 0)
    return dt + timedelta(hours=offset)


def _next_occurrence(week_start: datetime, event: dict[str, Any]) -> datetime:
    """Proxima ocorrencia de um evento na semana de week_start."""
    target_day = event.get("day", 0)
    hour = event.get("hour_utc", 12)
    days_ahead = (target_day - week_start.weekday()) % 7
    base = week_start + timedelta(days=days_ahead)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


def upcoming_events(limit: int = 15, days: int = 14, tz: str = "UTC",
                    relevance: str = "all") -> list[dict[str, Any]]:
    """Lista eventos das proximas N semanas a partir de agora (UTC).

    relevance: 'all' | 'gold' (apenas relevantes para ouro).
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    # inicio da semana corrente (segunda 00:00 UTC)
    week_start = (now_utc - timedelta(days=now_utc.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)

    out: list[dict[str, Any]] = []
    for w in range(0, max(1, days // 7) + 1):
        ws = week_start + timedelta(weeks=w)
        for ev in _BASE_EVENTS:
            if relevance == "gold" and ev.get("currency") not in _GOLD_CURRENCIES:
                continue
            when_utc = _next_occurrence(ws, ev)
            if when_utc < now_utc:
                continue
            when_tz = convert_to_tz(when_utc, tz)
            out.append({
                "title": ev.get("title", ""),
                "currency": ev.get("currency", ""),
                "impact": ev.get("impact", "medio"),
                "note": ev.get("note", ""),
                "when_utc": when_utc.isoformat(timespec="minutes"),
                "when": when_tz.strftime("%d/%m %H:%M"),
                "gold_relevant": ev.get("currency") in _GOLD_CURRENCIES,
            })
    out.sort(key=lambda e: e["when_utc"])
    return out[:limit]


def next_events(limit: int = 6, tz: str = "UTC") -> list[dict[str, Any]]:
    """Proximos eventos (todos)."""
    return upcoming_events(limit=limit, tz=tz, relevance="all")


def gold_events(limit: int = 6, tz: str = "UTC") -> list[dict[str, Any]]:
    """Proximos eventos relevantes para ouro."""
    return upcoming_events(limit=limit, tz=tz, relevance="gold")


def alerts_within(hours: float = 6.0, tz: str = "UTC") -> list[dict[str, Any]]:
    """Eventos que ocorrem dentro das proximas N horas (para alerta)."""
    from datetime import datetime as _dt, timezone as _tz
    now = _dt.now(_tz.utc).replace(tzinfo=None)
    return [
        e for e in upcoming_events(limit=60, tz=tz)
        if now <= _dt.fromisoformat(e["when_utc"]) <= now + timedelta(hours=hours)
    ]


def event_summary(tz: str = "BRT") -> list[str]:
    """Linhas de texto prontas para GUI/dashboard."""
    lines = []
    for e in gold_events(limit=5, tz=tz):
        mark = "⭐" if e["gold_relevant"] else "  "
        lines.append(f"{mark} [{e['when']} {tz}] {e['title']} ({e['currency']}, {e['impact']})")
    if not lines:
        lines.append("Sem eventos relevantes nos proximos dias.")
    return lines