"""Cobertura HTTP do gateway local: endpoints seguros, comandos e rejeições."""
from __future__ import annotations

import http.client
import importlib
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0

    def initialize(self):
        return True

    def terminal_info(self):
        return type("T", (), {"connected": True, "trade_allowed": True})()

    def account_info(self):
        return type(
            "A",
            (),
            {"login": 123, "name": "Demo", "company": "Broker", "server": "Demo-Server",
             "balance": 1000.0, "equity": 1000.0, "profit": 0.0, "margin": 0.0,
             "margin_free": 1000.0, "margin_level": 0.0, "currency": "USD",
             "trade_mode": 0, "trade_allowed": True},
        )()

    def positions_get(self, *args, **kwargs):
        return []

    def symbols_get(self):
        item = type("Y", (), {"name": "XAUUSD", "visible": True, "path": "Metals",
                              "currency_base": "XAU", "currency_profit": "USD",
                              "description": "Gold", "digits": 2, "point": 0.01,
                              "trade_mode": 4, "volume_min": 0.01,
                              "volume_max": 1.0, "volume_step": 0.01})()
        return [item]

    def orders_get(self, *args, **kwargs):
        return []

    def history_deals_get(self, *args, **kwargs):
        return []

    def symbol_select(self, symbol, enable=True):
        return True

    def symbol_info(self, symbol):
        return type("S", (), {"visible": True, "digits": 2, "volume_min": 0.01,
                              "volume_max": 1.0, "volume_step": 0.01, "point": 0.01})()

    def symbol_info_tick(self, symbol):
        return type("K", (), {"bid": 1.0, "ask": 1.0, "last": 1.0, "volume": 1.0})()


@pytest.fixture()
def gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XAU_MT5_COMMON_FILES", str(tmp_path / "common"))
    monkeypatch.setenv("XAU_APP_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("XAU_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("XAU_REAL_EMERGENCY_FILE", str(tmp_path / "STOP"))
    fake = ModuleType("MetaTrader5")
    fake_mt5 = FakeMT5()
    for name in dir(fake_mt5):
        if not name.startswith("_"):
            setattr(fake, name, getattr(fake_mt5, name))
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    import backend.mt5_gateway as gw

    gw = importlib.reload(gw)
    server = ThreadingHTTPServer(("127.0.0.1", 0), gw.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _request(base, method, path, payload=None):
    host, port = base.split(":")
    conn = http.client.HTTPConnection(host, int(port), timeout=10)
    body = json.dumps(payload) if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = json.loads(response.read() or b"{}")
    conn.close()
    return response.status, data


def test_status_e_conta_demo(gateway):
    status, data = _request(gateway, "GET", "/api/status")
    assert status == 200 and data["account"]["mode"] == "DEMO"
    status, data = _request(gateway, "GET", "/api/inventory")
    assert status == 200 and data["account"]["login"] == 123


def test_leituras_mt5_e_journal(gateway):
    for path in ("/api/health", "/api/symbols", "/api/assets", "/api/positions",
                 "/api/orders", "/api/journal?limit=3"):
        status, _ = _request(gateway, "GET", path)
        assert status == 200, path
    status, data = _request(gateway, "GET", "/api/mt5/quote?symbol=XAUUSD")
    assert status == 200 and data["bid"] == 1.0
    status, data = _request(gateway, "GET", "/api/mt5/quotes?symbols=XAUUSD,EURUSD")
    assert status == 200 and len(data["quotes"]) == 2
    status, data = _request(gateway, "GET", "/api/history?days=7&symbol=XAUUSD")
    assert status == 200 and data["count"] == 0


def test_configuracao_local(gateway):
    status, _ = _request(gateway, "GET", "/api/config")
    assert status == 200
    status, data = _request(gateway, "PUT", "/api/config", {"precision": 4})
    assert status == 200 and data["config"]["precision"] == 4
    status, _ = _request(gateway, "POST", "/api/config/reset", {})
    assert status == 200


def test_demo_bloqueado_sem_trava(gateway):
    payload = {"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
               "sl": 1.0, "tp": 2.0, "confirm_demo": True}
    status, data = _request(gateway, "POST", "/api/demo/order", payload)
    assert status in {403, 503}
    assert "demo" in json.dumps(data, ensure_ascii=False).lower()
    for path in ("/api/demo/positions", "/api/demo/orders",
                 "/api/demo/execution-status", "/api/demo/last-command"):
        status, _ = _request(gateway, "GET", path)
        assert status in {200, 403}, path
    status, data = _request(gateway, "POST", "/api/command/validate",
                            {"command": "/api/demo/close", "confirm_demo": True})
    assert status == 200 and data["valid"] is True


def test_universal_somente_leitura_e_previews(gateway, monkeypatch):
    from unittest.mock import patch

    import backend.connection_service as service

    class StubClient:
        def __init__(self, market="spot"):
            self.api_key = self.api_secret = self.secret = ""

        def account(self):
            return {"ok": True}

        def ticker(self, symbol):
            return {"bid": 1.0, "ask": 2.0}

        def depth(self, symbol):
            return {"bids": [[1.0, 1.0]], "asks": [[2.0, 1.0]]}

        def trades(self, symbol):
            return []

        def history(self, symbol=""):
            return []

    with patch.object(service, "MexcClient", StubClient), \
            patch("backend.mt5_gateway.MexcClient", StubClient):
        status, _ = _request(gateway, "GET",
                             "/api/universal/account?broker=mexc&market=crypto-spot")
        assert status == 200
        status, _ = _request(gateway, "GET",
                             "/api/universal/quote?broker=mexc&market=crypto-spot&symbol=BTCUSDT")
        assert status == 200
        status, _ = _request(gateway, "GET",
                             "/api/universal/history?broker=mexc&market=crypto-spot&symbol=BTCUSDT&days=1")
        assert status == 200
    payload = {"broker": "mexc", "market": "spot", "symbol": "BTCUSDT", "side": "buy",
               "order_type": "market", "quantity": 0.01, "request_id": "t1", "confirm": False}
    for path in ("/api/universal/order", "/api/universal/close",
                 "/api/universal/modify", "/api/universal/cancel"):
        status, data = _request(gateway, "POST", path, payload)
        assert status in {200, 422}, path
        assert "withdrawals" in json.dumps(data).lower()


def test_emergencia_e_real_bloqueados(gateway):
    status, _ = _request(gateway, "POST", "/api/universal/emergency-stop", {"confirm": True})
    assert status == 200
    status, _ = _request(gateway, "POST", "/api/universal/emergency-resume", {"confirm": True})
    assert status == 200
    status, data = _request(gateway, "POST", "/api/real/validate",
                            {"volume": 0.01, "daily_loss_pct": 0,
                             "exposure_pct": 0, "open_positions": 0})
    assert status == 200 and data["execution_enabled"] is False
    status, data = _request(gateway, "POST", "/api/real/request",
                            {"request_id": "r1", "account_id": "a",
                             "broker": "mt5", "market": "forex"})
    assert status == 202 and data["execution_enabled"] is False
    status, data = _request(gateway, "POST", "/api/real/order",
                            {"request_id": "r1", "confirm_real": True})
    assert status in {403, 503} and data.get("ok") is False


def test_cobertura_restante_sem_envio(gateway):
    for path in ("/api/account", "/api/system", "/api/audit", "/api/audit/commands",
                 "/api/errors", "/api/capabilities", "/api/sync/status",
                 "/api/stream/status", "/api/update/check", "/api/config/themes",
                 "/api/config/languages", "/api/assets/details",
                 "/api/execution/history", "/api/ea/status",
                 "/api/universal/depth?broker=mexc&market=crypto-spot&symbol=BTCUSDT",
                 "/api/universal/trades?broker=mexc&market=crypto-spot&symbol=BTCUSDT"):
        status, _ = _request(gateway, "GET", path)
        assert status in {200, 503}, path
    for path, payload in (("/api/assets/select", {"symbol": "XAUUSD"}),
                          ("/api/assets/enable", {"symbol": "XAUUSD"}),
                          ("/api/assets/disable", {"symbol": "XAUUSD"})):
        status, data = _request(gateway, "POST", path, payload)
        assert status == 200 and data["symbol"] == "XAUUSD", path
    for path in ("/api/demo/breakeven", "/api/demo/trailing"):
        status, data = _request(gateway, "POST", path, {"symbol": "XAUUSD"})
        assert status in {403, 503}
        assert "demo" in json.dumps(data, ensure_ascii=False).lower(), path
    status, data = _request(gateway, "POST", "/api/demo/close-all", {})
    assert status in {403, 503}

def test_rotas_restantes_sem_envio(gateway, monkeypatch):
    from unittest.mock import patch

    import backend.connection_service as service

    class StubClient:
        def __init__(self, market="spot"):
            self.api_key = self.api_secret = self.secret = ""

        def account(self):
            return {"ok": True}

        def ticker(self, symbol):
            return {"bid": 1.0, "ask": 2.0}

        def depth(self, symbol):
            return {"bids": [[1.0, 1.0]], "asks": [[2.0, 1.0]]}

        def trades(self, symbol):
            return []

        def history(self, symbol=""):
            return []

    with patch.object(service, "MexcClient", StubClient), \
            patch("backend.mt5_gateway.MexcClient", StubClient):
        for path in ("/api/universal/depth?broker=mexc&market=crypto-spot&symbol=BTCUSDT",
                     "/api/universal/trades?broker=mexc&market=crypto-spot&symbol=BTCUSDT"):
            status, _ = _request(gateway, "GET", path)
            assert status == 200, path
    for path in ("/api/assets/XAUUSD", "/api/assets/INVALIDO_XYZ"):
        status, _ = _request(gateway, "GET", path)
        assert status in {200, 404}, path
    status, _ = _request(gateway, "DELETE", "/api/connections/mexc:crypto-spot:inexistente")
    assert status == 200
    status, _ = _request(gateway, "POST", "/api/command/cancel",
                         {"command": "/api/demo/close", "confirm_demo": True})
    assert status == 200
    status, data = _request(gateway, "POST", "/api/demo/close", {"ticket": 1})
    assert status in {403, 503}
    assert "demo" in json.dumps(data, ensure_ascii=False).lower()
    status, _ = _request(gateway, "POST", "/api/demo/close-symbol", {"symbol": "XAUUSD"})
    assert status in {403, 503}
    status, _ = _request(gateway, "POST", "/api/demo/partial-close", {"ticket": 1, "volume": 0.01})
    assert status in {403, 503}
    for payload in ({"ticket": 1, "sl": 1.0, "tp": 2.0},
                    {"ticket": 1, "sl": 1.0, "tp": 2.0, "confirm_demo": True}):
        status, _ = _request(gateway, "POST", "/api/demo/set-protection", payload)
        assert status in {403, 503}
    status, _ = _request(gateway, "POST", "/api/demo/remove-protection", {"ticket": 1})
    assert status in {403, 503}
    status, _ = _request(gateway, "POST", "/api/demo/modify-position",
                         {"ticket": 1, "sl": 1.0, "tp": 2.0})
    assert status in {403, 503}
    status, _ = _request(gateway, "POST", "/api/demo/cancel-order", {"ticket": 1})
    assert status in {403, 503}
    status, _ = _request(gateway, "POST", "/api/demo/cancel-all-orders", {})
    assert status in {403, 503}
    status, _ = _request(gateway, "POST", "/api/ea/start", {})

def test_rotas_finais_ea_e_conexoes(gateway):
    for path in ("/api/ea/resume", "/api/ea/stop", "/api/ea/set-symbol",
                 "/api/ea/set-mode", "/api/ea/set-timeframe", "/api/ea/set-autotrading"):
        status, _ = _request(gateway, "POST", path, {"value": "XAUUSD"})
        assert status in {202, 503}, path
    payload = {"id": "mexc:crypto-spot:tmp", "broker": "mexc",
               "market": "crypto-spot", "api_key": "KEY", "api_secret": "SECRET"}
    status, _ = _request(gateway, "POST", "/api/connections", payload)
    assert status == 201
    status, _ = _request(gateway, "GET", "/api/connections")
    assert status == 200
    status, _ = _request(gateway, "POST",
                         "/api/connections/mexc:crypto-spot:tmp/deactivate", {})
    assert status == 200
    status, _ = _request(gateway, "DELETE", "/api/connections/mexc:crypto-spot:tmp")
    assert status == 200
    status, _ = _request(gateway, "DELETE", "/api/connections/")
    assert status == 200
    status, _ = _request(gateway, "POST", "/api/ea/pause", {})
    assert status in {202, 503}




