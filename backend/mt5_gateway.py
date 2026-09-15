# -*- coding: utf-8 -*-
"""MT5 Gateway - servico local na porta 9001 (MCP HTTP).

Responde /api/health, /api/account, /api/positions, /api/history
usando o pacote MetaTrader5 da maquina. Nunca faz trades.
Rodar: python backend/mt5_gateway.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HOST = "127.0.0.1"
PORT = 9001


def _mt5():
    import MetaTrader5 as mt5  # noqa: PLC0415
    return mt5


def _ensure_mt5() -> bool:
    mt5 = _mt5()
    if not mt5.initialize():
        return False
    return True


def _payload() -> dict:
    mt5 = _mt5()
    out = {"ts": datetime.now().isoformat(), "gateway": "XAU_AI_PRO MT5 Gateway"}
    try:
        ti = mt5.terminal_info()
        out["terminal_connected"] = bool(ti.connected) if ti else False
    except Exception:
        out["terminal_connected"] = False
    try:
        info = mt5.account_info()
        if info:
            out["account"] = {
                "login": info.login, "name": info.name,
                "company": info.company, "server": info.server,
                "balance": info.balance,
                "equity": info.equity, "profit": info.profit,
                "margin": info.margin, "margin_free": info.margin_free,
                "margin_level": info.margin_level, "currency": info.currency,
                "trade_allowed": bool(getattr(ti, "trade_allowed", False)) if ti else False,
                "terminal_connected": bool(getattr(ti, "connected", False)) if ti else False,
            }
    except Exception:
        pass
    try:
        pos = mt5.positions_get()
        out["positions"] = [{
            "ticket": p.ticket, "symbol": p.symbol,
            "type": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume, "open_price": p.price_open,
            "price_current": p.price_current, "sl": p.sl, "tp": p.tp,
            "profit": p.profit, "magic": p.magic,
        } for p in (pos or [])]
    except Exception:
        out["positions"] = []
    try:
        deals = mt5.history_deals_get(datetime.now() - timedelta(days=7), datetime.now())
        out["history_count"] = len(deals or [])
    except Exception:
        out["history_count"] = 0
    return out


def _quote(symbol: str) -> dict:
    mt5 = _mt5()
    if not symbol:
        raise ValueError("symbol obrigatorio")
    if not mt5.symbol_select(symbol, True):
        raise LookupError(f"simbolo indisponivel no MT5: {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    info = mt5.symbol_info(symbol)
    bid = float(tick.bid or 0.0)
    ask = float(tick.ask or 0.0)
    return {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "last": float(getattr(tick, "last", 0.0) or 0.0),
        "volume": float(getattr(tick, "volume", 0) or 0),
        "high": float(getattr(info, "session_price_high", 0.0) or 0.0),
        "low": float(getattr(info, "session_price_low", 0.0) or 0.0),
        "change_pct": 0.0,
        "timestamp": datetime.now().isoformat(),
        "source": "mt5_gateway",
    }


def _history(days: int = 30, symbol: str = "") -> dict:
    """Retorna deals fechados reais do MT5; nunca cria dados de teste."""
    mt5 = _mt5()
    days = max(1, min(days, 3650))
    end = datetime.now()
    start = end - timedelta(days=days)
    deals = mt5.history_deals_get(start, end, group=f"*{symbol}*") if symbol else mt5.history_deals_get(start, end)
    rows = []
    for deal in deals or []:
        deal_type = getattr(deal, "type", None)
        entry = getattr(deal, "entry", None)
        # In/Out são mantidos para auditoria; somente saídas representam resultado realizado.
        rows.append({
            "ticket": int(getattr(deal, "ticket", 0)),
            "order": int(getattr(deal, "order", 0)),
            "position_id": int(getattr(deal, "position_id", 0)),
            "symbol": str(getattr(deal, "symbol", "")),
            "type": "BUY" if deal_type == getattr(mt5, "DEAL_TYPE_BUY", 0) else "SELL",
            "entry": "IN" if entry == getattr(mt5, "DEAL_ENTRY_IN", 0) else "OUT" if entry == getattr(mt5, "DEAL_ENTRY_OUT", 1) else str(entry),
            "volume": float(getattr(deal, "volume", 0.0) or 0.0),
            "price": float(getattr(deal, "price", 0.0) or 0.0),
            "profit": float(getattr(deal, "profit", 0.0) or 0.0),
            "commission": float(getattr(deal, "commission", 0.0) or 0.0),
            "swap": float(getattr(deal, "swap", 0.0) or 0.0),
            "fee": float(getattr(deal, "fee", 0.0) or 0.0),
            "magic": int(getattr(deal, "magic", 0)),
            "time": datetime.fromtimestamp(int(getattr(deal, "time", 0))).isoformat(),
        })
    rows.sort(key=lambda row: row["time"], reverse=True)
    return {"deals": rows, "count": len(rows), "days": days, "source": "mt5_gateway"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silencia log
        pass

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path in ("/", "/api/health"):
            self._send(200, {"ok": True, "uptime_sec": int(time.time() - _T0),
                             "source": "mt5_gateway"})
        elif path in ("/api/status", "/api/system"):
            ok = _ensure_mt5()
            self._send(200, {"ok": ok, **_payload()})
        elif path == "/api/account":
            self._send(200, _payload().get("account") or {"ok": False})
        elif path == "/api/positions":
            self._send(200, {"positions": _payload().get("positions", [])})
        elif path == "/api/history":
            try:
                days = int(query.get("days", ["30"])[0])
                symbol = query.get("symbol", [""])[0].strip()
                self._send(200, _history(days, symbol))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "deals": [], "count": 0})
        elif path == "/api/mt5/quote":
            try:
                self._send(200, _quote(query.get("symbol", [""])[0]))
            except (LookupError, ValueError) as exc:
                self._send(404, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
        elif path == "/api/mt5/quotes":
            symbols = query.get("symbols", ["XAUUSD"])[0].split(",")
            quotes = []
            errors = []
            for symbol in symbols:
                try:
                    quotes.append(_quote(symbol.strip()))
                except Exception as exc:
                    errors.append({"symbol": symbol, "error": str(exc)})
            self._send(200, {"quotes": quotes, "errors": errors})
        else:
            self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self):  # noqa: N802
        self._send(200, {"ok": True, "gateway": "post_aceito"})


_T0 = time.time()


def main() -> None:
    if not _ensure_mt5():
        print("[gateway] ERRO: MetaTrader5 nao inicializou. Inicie o MT5 primeiro.")
    srv = HTTPServer((HOST, PORT), Handler)
    print(f"[gateway] MT5 Gateway rodando em http://{HOST}:{PORT}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
