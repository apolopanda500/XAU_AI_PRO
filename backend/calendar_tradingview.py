# -*- coding: utf-8 -*-
"""Calendario economico TradingView (publico, sem chave) portado do Android.

REFINE 23/11/2026: o app Android (MarketData.kt: calendarioTradingView) ja
consumia este feed com resultado/unidade/19 paises, mas o gateway Python so
tinha ForexFactory (sem `actual`). Agora o gateway tambem tem, com fallback
para o feed ForexFactory ja existente em economic_calendar_publica.py.

Nao negocia e nao altera risco/lote/alvo/stop: e contexto de mercado.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

URL = "https://economic-calendar.tradingview.com/events"
PAISES = "US,BR,EU,GB,JP,CA,AU,CN,DE,FR,IT,CH,NZ,MX,AR,ZA,IN,KR,TR"
_cache: tuple[float, list[dict[str, Any]], str] | None = None
TTL = 1800      # 30 min, igual ao cache ForexFactory do gateway


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _fmt(valor: Any, unidade: str) -> str:
    if valor is None:
        return ""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if unidade == "Percent":
        return f"{v:.2f}%"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.2f}"


def _fetch() -> tuple[list[dict[str, Any]], str]:
    agora = datetime.now(timezone.utc)
    query = urllib.parse.urlencode({
        "from": _iso(agora - timedelta(days=2)),
        "to": _iso(agora + timedelta(days=8)),
        "countries": PAISES,
    })
    req = urllib.request.Request(
        f"{URL}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        dados = json.loads(resp.read().decode("utf-8"))
    arr = dados.get("result") or []
    out: list[dict[str, Any]] = []
    for ev in arr:
        titulo = str(ev.get("title") or "").strip()
        if not titulo:
            continue
        moeda = str(ev.get("currency") or "").upper()
        data = str(ev.get("date") or "")
        try:
            quando = datetime.fromisoformat(data.replace("Z", "+00:00"))
        except ValueError:
            continue
        imp = int(ev.get("importance") or 0)
        impacto = "ALTO" if imp >= 1 else ("MEDIO" if imp == 0 else "BAIXO")
        unidade = str(ev.get("unit") or "")
        out.append({
            "title": titulo,
            "currency": moeda,
            "impact": impacto,
            "date": quando.isoformat(),
            "forecast": _fmt(ev.get("forecast"), unidade),
            "previous": _fmt(ev.get("previous"), unidade),
            "actual": _fmt(ev.get("actual"), unidade),
            "unit": unidade,
            "period": str(ev.get("period") or ""),
            "source": "TradingView Economics",
        })
    out.sort(key=lambda x: x["date"])
    return out, "TradingView Economics (publico, sem chave)"


def eventos(force: bool = False) -> dict[str, Any]:
    global _cache
    agora = time.time()
    if _cache and not force and (agora - _cache[0]) < TTL:
        itens, fonte = _cache[1], _cache[2]
    else:
        try:
            itens, fonte = _fetch()
        except Exception:
            # Fallback: feed ForexFactory ja existente no gateway.
            try:
                from backend import economic_calendar_publica as ff
                bruto = ff.buscar_eventos() if hasattr(ff, "buscar_eventos") else []
                itens = [
                    {
                        "title": str(e.get("title") or ""),
                        "currency": str(e.get("currency") or ""),
                        "impact": str(e.get("impact") or "MEDIO"),
                        "date": str(e.get("date") or ""),
                        "forecast": str(e.get("forecast") or ""),
                        "previous": str(e.get("previous") or ""),
                        "actual": str(e.get("actual") or ""),
                        "unit": "",
                        "period": str(e.get("period") or ""),
                        "source": "ForexFactory (fallback)",
                    }
                    for e in bruto[:60]
                ]
                fonte = "ForexFactory (fallback)"
            except Exception:
                itens, fonte = [], "sem fonte disponivel"
        _cache = (agora, itens, fonte)
    return {
        "ok": True,
        "count": len(itens),
        "source": fonte,
        "events": itens,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
