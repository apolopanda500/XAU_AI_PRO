# -*- coding: utf-8 -*-
"""Perfil de spread por hora do servidor, construido com ticks reais da corretora.

REFINE 23/11/2026 - inspirado no indicador gratuito `SpreadProfileByHour.mq5`
(Quoc Dat Quach, 2026) ja instalado em MQL5\\Indicators\\Downloads.

O que faz:
  - le os ticks dos ultimos INP_DIAS dias com MetaTrader5.copy_ticks_range();
  - agrupa o spread (ask-bid, em PONTOS do simbolo) por hora do SERVIDOR;
  - calcula mediana e percentil 90 (p90) por hora;
  - escolhe a "melhor hora" (menor mediana) e a "pior hora" (maior p90);
  - calcula quanto do stop (1R, em pontos) o spread consome: custo = p90/R*100.

Nao negocia, nao decide, nao altera risco/lote/alvo/stop: e apenas MEDICAO
que viaja no corpo de /api/ai/predict ate ao EA (atraves do servico
XAI_RefreshPredictions, que grava o corpo tal qual em prediction_<SIM>.json).

Fail-closed: sem ticks ou sem terminal, devolve disponivel=False e numeros
zerados - o EA continua a usar o seu proprio filtro MaxSpreadPct.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5

DIAS = 20
CACHE_SEG = 3600          # 1 hora: o perfil muda devagar
MAX_HORAS = 24


def _percentil(valores: list[float], pct: float) -> float:
    if not valores:
        return 0.0
    s = sorted(valores)
    if len(s) == 1:
        return float(s[0])
    pos = (len(s) - 1) * pct
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(s[lo])
    return float(s[lo] + (s[hi] - s[lo]) * (pos - lo))


_mem: dict[str, tuple[float, dict[str, Any]]] = {}


def cache(symbol: str) -> dict[str, Any] | None:
    """Devolve o perfil ja calculado (SEM ler ticks). Nunca bloqueia."""
    dado = _mem.get(str(symbol or "").strip().upper())
    if dado is None:
        return None
    timestamp, dados = dado
    if time.time() - timestamp > CACHE_SEG:
        return None
    return dict(dados)


def perfil(symbol: str, stop_points: float = 0.0, force: bool = False) -> dict[str, Any]:
    """Devolve o perfil de spread por hora. Nunca lanca para o chamador."""
    simbolo = str(symbol or "").strip().upper()
    vazio: dict[str, Any] = {
        "available": False,
        "reason": "sem ticks ou terminal indisponivel",
        "symbol": simbolo,
        "days": DIAS,
        "samples": 0,
        "hours": [],
        "best_hour": -1,
        "worst_hour": -1,
        "spread_median_points": 0.0,
        "spread_p90_points": 0.0,
        "spread_cost_1r_pct": 0.0,
    }
    if not simbolo:
        return vazio

    agora = time.time()
    cached = _mem.get(simbolo)
    if cached and not force and (agora - cached[0]) < CACHE_SEG:
        dados = dict(cached[1])
        if stop_points > 0:
            p90 = float(dados.get("spread_p90_points", 0.0))
            dados["spread_cost_1r_pct"] = round(100.0 * p90 / stop_points, 2)
        return dados

    try:
        if not mt5.initialize():
            return vazio
        info = mt5.symbol_info(simbolo)
        if info is None:
            return vazio
        point = float(info.point or 0.0)
        if point <= 0:
            return vazio

        ate = datetime.now(timezone.utc) + timedelta(days=1)
        de = ate - timedelta(days=DIAS)
        ticks = mt5.copy_ticks_range(simbolo, de, ate, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            return vazio

        por_hora: dict[int, list[float]] = defaultdict(list)
        for t in ticks:
            ask = float(t["ask"] or 0.0)
            bid = float(t["bid"] or 0.0)
            if ask <= 0 or bid <= 0:
                continue
            spread = (ask - bid) / point
            if spread < 0 or spread > 100000:
                continue
            hora = int(datetime.fromtimestamp(int(t["time"]), tz=timezone.utc).hour)
            por_hora[hora].append(spread)

        if not por_hora:
            return vazio

        horas: list[dict[str, Any]] = []
        for h in range(MAX_HORAS):
            vals = por_hora.get(h, [])
            if len(vals) < 20:      # amostra minima, como no indicador original
                continue
            horas.append({
                "hour": h,
                "samples": len(vals),
                "median": round(_percentil(vals, 0.50), 2),
                "p90": round(_percentil(vals, 0.90), 2),
            })
        if not horas:
            return vazio

        melhor = min(horas, key=lambda x: x["median"])
        pior = max(horas, key=lambda x: x["p90"])
        total = sum(len(v) for v in por_hora.values())
        dados = {
            "available": True,
            "reason": "tick history real",
            "symbol": simbolo,
            "days": DIAS,
            "samples": int(total),
            "hours": horas,
            "best_hour": int(melhor["hour"]),
            "worst_hour": int(pior["hour"]),
            "spread_median_points": float(melhor["median"]),
            "spread_p90_points": float(pior["p90"]),
            "spread_cost_1r_pct": (
                round(100.0 * float(pior["p90"]) / stop_points, 2)
                if stop_points > 0 else 0.0
            ),
            "source": "copy_ticks_range",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _mem[simbolo] = (agora, dados)
        return dict(dados)
    except Exception as exc:                       # pragma: no cover
        return {**vazio, "reason": f"erro: {type(exc).__name__}: {exc}"}
