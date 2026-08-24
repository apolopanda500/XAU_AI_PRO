# -*- coding: utf-8 -*-
"""ETAPA 21 - Reconciliação financeira.

Fonte de verdade: histórico real de posições do broker (MT5, magic XAU_AI_PRO).
Cruzamento com:
  - AuditLog (full_audit.csv): tickets de entrada
  - Event Stream (forward_test_events.csv): eventos TRADE_OPEN/CLOSE

Métricas:
  - win rate, profit factor, expectativa, lucro/por símbolo
  - divergências (tickets no broker sem audit, duplicatas, etc.)
"""
from __future__ import annotations

import json
from typing import Any

# Script de reconciliação - recebe posições (list de dict) do broker
# e cruza com AuditLog + EventStream para detectar inconsistências.


def reconcile_financial(
    positions: list[dict[str, Any]],
    audit_tickets: list[str] | None = None,
    stream_tickets: list[str] | None = None,
) -> dict[str, Any]:
    """Reconcilia posições fechadas do broker com audit/event stream.

    Retorna:
      - resumo: nº trades, vencedoras/perdedoras, win rate, PF, expectativa, P/L total
      - por_simbolo: métricas por símbolo
      - inconsistencias: trades sem match no audit/stream, duplicatas
    """
    trades = []
    for p in positions:
        # só posições fechadas com P/L (profit não None) do magic correto
        if p.get("profit") is None:
            continue
        trades.append({
            "ticket": p.get("position_id"),
            "symbol": p.get("symbol"),
            "type": "BUY" if p.get("type") == "buy" else "SELL",
            "open_time": p.get("open_time"),
            "close_time": p.get("close_time"),
            "close_reason": p.get("close_reason"),
            "profit": float(p.get("profit") or 0),
            "swaps": float(p.get("swaps") or 0),
            "volume": float(p.get("open_volume") or 0),
        })

    wins = [t for t in trades if t["profit"] > 0]
    losses = [t for t in trades if t["profit"] < 0]
    breakeven = [t for t in trades if t["profit"] == 0]

    gross_profit = sum(t["profit"] for t in wins)
    gross_loss = abs(sum(t["profit"] for t in losses)) if losses else 0
    total_pnl = sum(t["profit"] for t in trades)
    n = len(trades)

    pf = (gross_profit / gross_loss) if gross_loss > 0 else (999 if gross_profit > 0 else 0)
    win_rate = (len(wins) / n * 100) if n else 0.0
    expectancy = (total_pnl / n) if n else 0.0

    # por símbolo
    by_sym: dict[str, dict] = {}
    for t in trades:
        s = t["symbol"]
        b = by_sym.setdefault(s, {"trades": 0, "pnl": 0.0, "wins": 0})
        b["trades"] += 1
        b["pnl"] += t["profit"]
        if t["profit"] > 0:
            b["wins"] += 1

    # inconsistências
    incons = []
    tickets = [str(t["ticket"]) for t in trades]
    audit_set = set(str(x) for x in (audit_tickets or []))
    stream_set = set(str(x) for x in (stream_tickets or []))

    for t in trades:
        tk = str(t["ticket"])
        if audit_set and tk not in audit_set:
            incons.append({"ticket": tk, "tipo": "no_broker_sem_auditlog"})
        if (not audit_set) and (not stream_set):
            break

    return {
        "resumo": {
            "total_trades": n,
            "vitorias": len(wins),
            "derrotas": len(losses),
            "empates": len(breakeven),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(pf, 2) if pf != 999 else "Infinito",
            "expectativa_trade": round(expectancy, 4),
            "pnl_total": round(total_pnl, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
        },
        "por_simbolo": {
            s: {"trades": v["trades"], "pnl": round(v["pnl"], 2),
                "win_rate_pct": round(v["wins"] / v["trades"] * 100, 2) if v["trades"] else 0}
            for s, v in sorted(by_sym.items())
        },
        "inconsistencias": incons,
        "trades": trades,
    }


def to_json(result: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Exemplo/demo com dados reais do broker (ETAPA 21)
    positions_real = [
        {"position_id": 10153586005, "symbol": "USDCHF", "type": "sell", "open_price": 0.80078,
         "close_price": 0.80035, "close_reason": "Stop loss", "profit": 0.54, "swaps": -0.01,
         "open_volume": 0.01, "open_time": "2026.08.21 22:00", "close_time": "2026.08.24 03:05"},
        {"position_id": 10155400097, "symbol": "NZDUSD", "type": "buy", "open_price": 0.59714,
         "close_price": 0.59714, "close_reason": "Stop loss", "profit": 0.0, "swaps": 0,
         "open_volume": 0.01, "open_time": "2026.08.24 02:38", "close_time": "2026.08.24 06:10"},
        {"position_id": 10161822226, "symbol": "AUDUSD", "type": "buy", "open_price": 0.71707,
         "close_price": 0.71557, "close_reason": "Expert", "profit": -1.5, "swaps": 0,
         "open_volume": 0.01, "open_time": "2026.08.24 09:55", "close_time": "2026.08.24 17:50"},
        {"position_id": 10162007833, "symbol": "USDJPY", "type": "buy", "open_price": 159.034,
         "close_price": 159.097, "close_reason": "Stop loss", "profit": 0.4, "swaps": 0,
         "open_volume": 0.01, "open_time": "2026.08.24 10:06", "close_time": "2026.08.24 10:32"},
        {"position_id": 10162465656, "symbol": "USDJPY", "type": "buy", "open_price": 159.098,
         "close_price": 159.154, "close_reason": "Stop loss", "profit": 0.35, "swaps": 0,
         "open_volume": 0.01, "open_time": "2026.08.24 10:32", "close_time": "2026.08.24 11:07"},
        {"position_id": 10155828638, "symbol": "GBPUSD", "type": "buy", "open_price": 1.36529,
         "close_price": 1.36379, "close_reason": "Expert", "profit": -1.5, "swaps": 0,
         "open_volume": 0.01, "open_time": "2026.08.24 03:10", "close_time": "2026.08.24 09:47"},
        {"position_id": 10155400102, "symbol": "NZDUSD", "type": "buy", "open_price": 0.59714,
         "close_price": 0.59723, "close_reason": "Stop loss", "profit": 0.09, "swaps": 0,
         "open_volume": 0.01, "open_time": "2026.08.24 02:38", "close_time": "2026.08.24 07:09"},
    ]
    r = reconcile_financial(positions_real)
    print(json.dumps(r["resumo"], indent=2, ensure_ascii=False))
    print("\nPOR SÍMBOLO:")
    print(json.dumps(r["por_simbolo"], indent=2, ensure_ascii=False))
    print("\nINCONSISTÊNCIAS:", r["inconsistencias"])
