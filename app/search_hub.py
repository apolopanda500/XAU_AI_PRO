# -*- coding: utf-8 -*-
"""Search Hub - busca global dentro do XAU_AI_PRO.

Pesquisa unificada em: MCP (instalados/catalogo/ferramentas), agentes
(abas/comandos), chats (memoria), ativos (simbolos MT5/MarketData) e
calendario economico. Usada pela GUI (aba de busca) e pelo dashboard web.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

_APP_ROOT = Path(__file__).resolve().parent.parent


def search_mcp(query: str) -> list[dict[str, Any]]:
    """Pesquisa servidores e ferramentas MCP."""
    query = (query or "").strip().lower()
    out: list[dict[str, Any]] = []
    try:
        from app.mcp_marketplace import catalogo, instalados
        for item in catalogo():
            hay = f"{item.get('name','')} {item.get('id','')} {item.get('description','')}".lower()
            if not query or query in hay:
                out.append({"tipo": "mcp", "nome": item.get("name", item.get("id", "")),
                            "descricao": item.get("description", ""), "origem": "catalogo"})
        for sid in instalados():
            out.append({"tipo": "mcp", "nome": sid, "descricao": "instalado",
                        "origem": "instalados"})
    except Exception:
        pass
    try:
        from app.mcp_tools import enabled_tools
        for t in enabled_tools():
            if not query or query in t.lower():
                out.append({"tipo": "mcp", "nome": t, "descricao": "ferramenta ativa",
                            "origem": "tools"})
    except Exception:
        pass
    return out


def search_agents(query: str) -> list[dict[str, Any]]:
    """Pesquisa 'agentes'/abas e comandos disponiveis no app."""
    query = (query or "").strip().lower()
    agents = [
        ("dashboard", "Painel principal com predicoes e metricas"),
        ("market", "Mercado: cotacoes em tempo real e graficos"),
        ("positions", "Posicoes: carteira aberta e historico"),
        ("robot", "Robo MT5: conexao, status e acoes"),
        ("training", "IA/Treino: pipeline de modelos e predicoes"),
        ("assistant", "Assistente IA: chat com memoria e pensamentos"),
        ("tools", "Ferramentas: utilitarios e operacoes"),
        ("integrations", "Integracoes: MCP, GitHub, Slack, Sentry"),
        ("subgraph", "Subgraph: analise por correlacoes de ativos"),
        ("system", "Sistema: monitoramento, logs e diagnostico"),
        ("charts", "Graficos: analise tecnica visual"),
        ("search", "Pesquisa global: MCP, agentes, chats, ativos, calendario"),
    ]
    out = []
    for name, desc in agents:
        if not query or query in name or query in desc.lower():
            out.append({"tipo": "agente", "nome": name, "descricao": desc, "origem": "abas"})
    return out


def search_chats(query: str) -> list[dict[str, Any]]:
    """Pesquisa o historico de conversas e pensamentos na memoria."""
    query = (query or "").strip()
    out: list[dict[str, Any]] = []
    try:
        from app.ai_memory import recall
        for m in recall(limit=100, query=query) if query else recall(limit=30):
            out.append({"tipo": "chat", "nome": m["kind"], "descricao": m["content"][:180],
                        "origem": m.get("ts", "")})
    except Exception:
        pass
    return out


def search_symbols(query: str) -> list[dict[str, Any]]:
    """Pesquisa ativos: simbolos MT5 (se conectado) + lista padrao."""
    query = (query or "").strip().upper()
    default = ["XAUUSD", "XAUUSDc", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD",
               "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "US30",
               "NAS100", "SPX500", "GER40", "UK100"]
    out = []
    for s in default:
        if not query or query in s:
            out.append({"tipo": "ativo", "nome": s, "descricao": "lista padrao",
                        "origem": "default"})
    try:
        import MetaTrader5 as mt5  # noqa: PLC0415
        from app.mt5_robot import get_robot
        robot = get_robot()
        if robot and robot.account_info():
            syms = mt5.symbols_get()
            for sym in (syms or [])[:500]:
                name = sym.name
                if not query or query in name.upper():
                    out.append({"tipo": "ativo", "nome": name,
                                "descricao": "do terminal MT5", "origem": "mt5"})
        mt5.shutdown()
    except Exception:
        pass
    return out[:60]


def search_calendar(query: str = "") -> list[dict[str, Any]]:
    """Pesquisa eventos do calendario economico proximos."""
    out: list[dict[str, Any]] = []
    try:
        from app.economic_calendar import upcoming_events
        for ev in upcoming_events(limit=12):
            hay = f"{ev.get('title','')} {ev.get('currency','')}".lower()
            if not query or query.lower() in hay:
                out.append({"tipo": "calendario", "nome": ev.get("title", ""),
                            "descricao": f"{ev.get('currency','')} impacto {ev.get('impact','')}",
                            "origem": ev.get("when", "")})
    except Exception:
        pass
    return out


def search_all(query: str, max_per: int = 10) -> dict[str, Any]:
    """Busca global em todas as fontes. Retorna dict por categoria."""
    q = (query or "").strip()
    result = {
        "query": q,
        "mcp": search_mcp(q)[:max_per],
        "agentes": search_agents(q)[:max_per],
        "chats": search_chats(q)[:max_per],
        "ativos": search_symbols(q)[:max_per],
        "calendario": search_calendar(q)[:max_per],
        "ts": time.time(),
    }
    result["total"] = sum(len(v) for k, v in result.items() if isinstance(v, list))
    return result


def quick_summary() -> dict[str, Any]:
    """Resumo rapido do estado (usado no dashboard/statusbar)."""
    summary = {"mcp": len(search_mcp("")), "agentes": len(search_agents("")),
               "chats": len(search_chats("")), "ativos": len(search_symbols(""))}
    try:
        import MetaTrader5 as mt5  # noqa: PLC0415
        from app.mt5_robot import get_robot
        robot = get_robot()
        summary["conectado_mt5"] = bool(robot and robot.account_info())
        mt5.shutdown()
    except Exception:
        summary["conectado_mt5"] = False
    return summary