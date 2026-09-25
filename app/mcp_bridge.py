# -*- coding: utf-8 -*-
"""Bridge de pipelines entre conectores MCP aprovados.

Pipelines nunca inventam fallback: servidores ausentes são reportados como
indisponíveis e a memória é usada apenas com dados recebidos de fontes reais.
"""
from __future__ import annotations

import json
import time
from typing import Any


def _call(server_id: str, action: str = "quote", **kw: Any) -> dict[str, Any]:
    from app.mcp_tools import call_tool
    return call_tool(server_id, action, **kw)


def bridge_sequential_to_db(thought: str, query: str | None = None) -> dict[str, Any]:
    """Pipeline opcional; servidores ausentes são reportados sem fallback falso."""
    from app.mcp_tools import enabled_tools

    enabled = set(enabled_tools())
    steps: list[dict[str, Any]] = []
    if "sequential_thinking" in enabled:
        r_seq = _call("sequential_thinking", thought=thought, thoughtNumber=1, totalThoughts=5)
        steps.append({"server": "sequential_thinking", "ok": r_seq.get("ok"), "result": r_seq.get("result", r_seq.get("error", ""))})
    else:
        steps.append({"server": "sequential_thinking", "ok": False, "error": "servidor não habilitado"})

    if "postgres_sqlite" in enabled:
        try:
            r_db = _call("postgres_sqlite", "query", query=query or "SELECT name FROM sqlite_master WHERE type='table' LIMIT 10")
            steps.append({"server": "postgres_sqlite", "ok": r_db.get("ok"), "result": r_db.get("result", r_db.get("error", ""))})
        except Exception as exc:
            steps.append({"server": "postgres_sqlite", "ok": False, "error": str(exc)})
    else:
        steps.append({"server": "postgres_sqlite", "ok": False, "error": "servidor não habilitado"})

    return {"ok": bool(steps) and all(step.get("ok") for step in steps), "steps": steps, "ts": time.time()}


def bridge_market_to_memory(symbol: str = "XAUUSD") -> dict[str, Any]:
    """Pipeline: cotacao (TradingView/AlphaVantage/MT5) -> memoria."""
    steps: list[dict[str, Any]] = []
    quote = None

    # Tenta TradingView, depois Alpha Vantage, depois MT5
    for sid in ("tradingview", "alpha_vantage"):
        try:
            r = _call(sid, symbol=symbol)
            if r.get("ok"):
                res = r.get("result") or {}
                if isinstance(res, dict) and res.get("price"):
                    quote = res
                    steps.append({"server": sid, "ok": True, "result": quote})
                    break
            steps.append({"server": sid, "ok": False,
                          "error": (r.get("error") or "sem dados")[:80]})
        except Exception as exc:
            steps.append({"server": sid, "ok": False, "error": str(exc)[:80]})

    if quote is None:
        try:
            from app.mt5_sync import _snapshot_account
            from app.market_data import MarketData
            md = MarketData()
            q = md.get_quote(symbol)
            if q:
                quote = q.to_dict() if hasattr(q, "to_dict") else dict(q)
                steps.append({"server": "mt5", "ok": True, "result": quote})
            md.disconnect()
        except Exception as exc:
            steps.append({"server": "mt5", "ok": False, "error": str(exc)[:80]})

    if quote:
        try:
            from app.ai_memory import remember
            remember("fact", f"Cotacao {symbol}: {json.dumps(quote, ensure_ascii=False, default=str)[:200]}",
                     {"bridge": "market->memory"})
        except Exception:
            pass

    return {"ok": quote is not None, "steps": steps, "quote": quote, "ts": time.time()}


def bridge_analysis_pipeline(thought: str, symbol: str = "XAUUSD") -> dict[str, Any]:
    """Pipeline completa: pensamento + cotacao + sincronizacao MT5 + memoria."""
    steps: list[dict[str, Any]] = [{"server": "agent_reasoning", "ok": True, "result": thought}]
    r_mkt = bridge_market_to_memory(symbol)
    steps.append({"server": "market", "ok": r_mkt.get("ok"), "result": r_mkt.get("quote")})

    # 3) Sincronizacao MT5 (saldo/posicoes)
    try:
        from app.mt5_sync import sync_account, sync_positions
        r_acc = sync_account()
        r_pos = sync_positions()
        steps.append({"server": "mt5_sync", "ok": r_acc.get("ok"),
                      "account": r_acc.get("account", {}),
                      "positions_count": r_pos.get("count", 0)})
    except Exception as exc:
        steps.append({"server": "mt5_sync", "ok": False, "error": str(exc)[:80]})

    # 4) Memoria
    try:
        from app.ai_memory import remember
        remember("thought", f"{symbol}: {thought}", {"pipeline": "analysis"})
    except Exception:
        pass

    return {"ok": bool(r_mkt.get("ok")), "steps": steps, "symbol": symbol, "ts": time.time()}


def cross_mcp_search(query: str) -> dict[str, Any]:
    """Busca 'multi-MCP': pergunta a cada servidor habilitado e consolida."""
    from app.mcp_tools import enabled_tools
    enabled = enabled_tools()
    results: dict[str, Any] = {}

    if "postgres_sqlite" in enabled:
        try:
            r = _call("postgres_sqlite", "query",
                      query=f"SELECT content FROM memories WHERE content LIKE '%{query}%' LIMIT 5")
            results["postgres_sqlite"] = r.get("result", r.get("error", ""))
        except Exception as exc:
            results["postgres_sqlite"] = str(exc)[:100]

    if "mt5_gateway" in enabled:
        try:
            r = _call("mt5_gateway", "health")
            results["mt5_gateway"] = r.get("result", r.get("error", ""))
        except Exception as exc:
            results["mt5_gateway"] = str(exc)[:100]

    # pesquisa na memoria local
    try:
        from app.ai_memory import recall
        results["memoria"] = [m["content"][:150] for m in recall(query=query, limit=5)]
    except Exception:
        pass

    return {"query": query, "servidores": enabled, "results": results, "ts": time.time()}


def pipeline_summary() -> dict[str, Any]:
    """Resumo das MCPs disponiveis para o painel de integracoes."""
    from app.mcp_tools import enabled_tools
    enabled = enabled_tools()
    return {
        "enabled": enabled,
        "count": len(enabled),
        "pipelines": {
            "market_to_memory": "tradingview/mt5 -> memoria",
            "analysis": "agent_reasoning + market + mt5_sync + memoria",
            "cross_search": "busca multi-servidor",
        },
    }