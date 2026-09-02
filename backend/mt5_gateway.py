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
                "login": info.login, "balance": info.balance,
                "equity": info.equity, "profit": info.profit,
                "margin_level": info.margin_level, "currency": info.currency,
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
        path = self.path.split("?")[0]
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
            self._send(200, {"count": _payload().get("history_count", 0)})
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