# -*- coding: utf-8 -*-
"""MCP Server de trading do XAU AI PRO (stdio, JSON-RPC 2.0, stdlib puro).

Permite que clientes MCP (Claude, Codex, outros) operem e consultem a mesa do
trader passando OBRIGATORIAMENTE pelo gateway local (9001) - herdando assim
risk_gate, auditoria e emergency-stop ja existentes.

Seguranca (3 freios independentes):
  1. Toda ordem nasce em dry-run (execute=False -> so registra e valida).
  2. Execucao real exige execute=True na chamada E a env XAU_MCP_TRADING=1.
  3. Emergency-stop corta tudo no gateway (independe do MCP).

Execucao: .venv\\Scripts\\python.exe -m backend.trading_mcp
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

GATEWAY = os.environ.get("XAU_MCP_GATEWAY", "http://127.0.0.1:9001").rstrip("/")
TRADING_HABILITADO = os.environ.get("XAU_MCP_TRADING") == "1"
PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "xau-ai-pro-trading", "version": "1.2.3"}
# Contador monotônico: garante request_id único mesmo com clock de baixa resolução.
_SEQ = itertools.count(1)


def _http(path, payload=None, timeout=10.0):
    """GET/POST no gateway; nunca lanca - devolve dict com erro marcado."""
    url = f"{GATEWAY}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"http": resp.status, **json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return {"http": exc.code, "error": body or str(exc)}
    except Exception as exc:
        return {"error": f"gateway inacessivel: {exc}"}


def _acao_universal(args, acao, path):
    corpo = {
        "broker": args.get("broker", "mt5"),
        "market": args.get("market", "forex"),
        "symbol": args.get("symbol", ""),
        "side": args.get("side", "buy"),
        "order_type": args.get("order_type", "market"),
        "quantity": float(args.get("quantity", 0.01) or 0.01),
        "request_id": f"mcp-{acao}-{os.getpid()}-{time.time_ns()}-{next(_SEQ)}",
        "confirm": True,
        "action": acao,
        "execute": bool(args.get("execute")) and TRADING_HABILITADO,
    }
    for campo in ("price", "sl", "tp"):
        if args.get(campo) is not None:
            corpo[campo] = args[campo]
    return _http(path, corpo)


def _cortar_execucao(args):
    if bool(args.get("execute")) and not TRADING_HABILITADO:
        return {"bloqueado": True, "motivo": "XAU_MCP_TRADING != 1: execucao real desabilitada neste servidor MCP"}
    return {}


TOOLS = [
    {"name": "health", "description": "Verifica se o gateway local esta no ar.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "account_summary", "description": "Saldo, patrimonio, margem e moeda da conta ativa.",
     "inputSchema": {"type": "object", "properties": {"broker": {"type": "string", "enum": ["mt5", "binance", "mexc"]}, "market": {"type": "string"}}}},
    {"name": "list_positions", "description": "Posicoes abertas com PnL por ticket.",
     "inputSchema": {"type": "object", "properties": {"broker": {"type": "string"}, "market": {"type": "string"}}}},
    {"name": "get_quote", "description": "Cotacao atual (bid/ask) de um simbolo.",
     "inputSchema": {"type": "object", "required": ["symbol"], "properties": {"symbol": {"type": "string"}, "broker": {"type": "string"}, "market": {"type": "string"}}}},
    {"name": "place_order", "description": "Envia ordem. POR PADRAO e dry-run. Execucao real: execute=true E servidor com XAU_MCP_TRADING=1.",
     "inputSchema": {"type": "object", "required": ["symbol"], "properties": {"symbol": {"type": "string"}, "side": {"type": "string", "enum": ["buy", "sell"]}, "order_type": {"type": "string", "enum": ["market", "limit"]}, "quantity": {"type": "number", "minimum": 0.01}, "price": {"type": "number"}, "sl": {"type": "number"}, "tp": {"type": "number"}, "broker": {"type": "string"}, "market": {"type": "string"}, "execute": {"type": "boolean", "default": False}}}},
    {"name": "close_position", "description": "Fecha posicao por ticket (mesmas travas do place_order).",
     "inputSchema": {"type": "object", "required": ["ticket", "symbol"], "properties": {"ticket": {}, "symbol": {"type": "string"}, "broker": {"type": "string"}, "market": {"type": "string"}, "execute": {"type": "boolean", "default": False}}}},
    {"name": "emergency_stop", "description": "Corta imediatamente toda execucao no gateway.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "emergency_resume", "description": "Retoma a execucao apos um emergency_stop.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "journal_tail", "description": "Ultimas linhas do journal MT5.",
     "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}}},
    {"name": "fear_greed_index", "description": "Indice global de Medo e Ganancia do mercado cripto (0-100, alternative.me). Leitura apenas.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "crypto_ticker", "description": "Ticker 24h real da Binance (ultimo, variacao, maximo, minimo, volume). Leitura apenas.",
     "inputSchema": {"type": "object", "required": ["symbol"], "properties": {"symbol": {"type": "string", "description": "Par da Binance, ex: BTCUSDT"}}}},
]
def tool_call(name, args):
    """Despacha uma ferramenta (funcao pura de roteamento, facil de testar)."""
    acao = args.pop("_seq", 0)
    if name == "health":
        return _http("/api/health")
    if name == "account_summary":
        b = args.get("broker", "mt5")
        path = f"/api/universal/account?broker={b}&market={args.get('market', 'forex')}" if b != "mt5" else "/api/account"
        return _http(path)
    if name == "list_positions":
        b = args.get("broker", "mt5")
        path = f"/api/universal/positions?broker={b}&market={args.get('market', 'forex')}" if b != "mt5" else "/api/positions"
        return _http(path)
    if name == "get_quote":
        b = args.get("broker", "mt5")
        path = f"/api/universal/quote?broker={b}&market={args.get('market', 'forex')}&symbol={args['symbol']}" if b != "mt5" else f"/api/mt5/quote?symbol={args['symbol']}"
        return _http(path)
    if name == "place_order":
        if bloqueio := _cortar_execucao(args):
            return {**bloqueio, "dry_run": not bool(args.get("execute"))}
        return _acao_universal(args, "order", "/api/universal/order")
    if name == "close_position":
        if bloqueio := _cortar_execucao(args):
            return {**bloqueio}
        corpo = {"broker": args.get("broker", "mt5"), "market": args.get("market", "forex"),
                 "symbol": args.get("symbol", ""), "ticket": args.get("ticket"),
                 "request_id": f"mcp-close-{os.getpid()}-{time.time_ns()}-{next(_SEQ)}", "confirm": True,
                 "action": "close",
                 "execute": bool(args.get("execute")) and TRADING_HABILITADO}
        return _http("/api/universal/close", corpo)
    if name == "emergency_stop":
        return _http("/api/universal/emergency-stop", {})
    if name == "emergency_resume":
        return _http("/api/universal/emergency-resume", {})
    if name == "journal_tail":
        return _http(f"/api/journal?limit={int(args.get('limit', 20))}")
    if name == "fear_greed_index":
        return _http("https://api.alternative.me/fng/?limit=1")
    if name == "crypto_ticker":
        simbolo = str(args.get("symbol", "BTCUSDT")).strip().upper()
        return _http(f"https://api.binance.com/api/v3/ticker/24hr?symbol={simbolo}")
    return {"error": f"ferramenta desconhecida: {name}"}


def processar(mensagem):
    """Processa mensagem JSON-RPC; devolve resposta (None p/ notificacoes)."""
    metodo = mensagem.get("method", "")
    msg_id = mensagem.get("id")
    if metodo == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id,
                "result": {"protocolVersion": PROTOCOL_VERSION,
                           "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}}
    if metodo.startswith("notifications/"):
        return None
    if metodo == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if metodo == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if metodo == "tools/call":
        params = mensagem.get("params") or {}
        try:
            resultado = tool_call(params.get("name", ""), dict(params.get("arguments") or {}))
            texto = json.dumps(resultado, ensure_ascii=False)
            erro = "error" in resultado or "bloqueado" in resultado
        except Exception as exc:
            texto, erro = f"falha interna: {exc}", True
        return {"jsonrpc": "2.0", "id": msg_id,
                "result": {"content": [{"type": "text", "text": texto}], "isError": erro}}
    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"metodo nao suportado: {metodo}"}}
    return None


def main():
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            mensagem = json.loads(linha)
        except json.JSONDecodeError:
            continue
        resposta = processar(mensagem)
        if resposta is not None:
            sys.stdout.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
