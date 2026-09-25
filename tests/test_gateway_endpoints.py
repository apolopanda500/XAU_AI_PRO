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


def _request(base, method, path, payload=None, headers=None):
    host, port = base.split(":")
    conn = http.client.HTTPConnection(host, int(port), timeout=10)
    body = json.dumps(payload) if payload is not None else None
    request_headers = {"Content-Type": "application/json"} if body else {}
    request_headers.update(headers or {})
    conn.request(method, path, body=body, headers=request_headers)
    response = conn.getresponse()
    data = json.loads(response.read() or b"{}")
    conn.close()
    return response.status, data


def test_status_e_conta_demo(gateway):
    status, data = _request(gateway, "GET", "/api/status")
    assert status == 200 and data["account"]["mode"] == "DEMO"
    status, data = _request(gateway, "GET", "/api/inventory")
    assert status == 200 and data["account"]["login"] == 123


def test_catalogo_modelos_somente_leitura(gateway, tmp_path, monkeypatch):
    from Python import model_registry

    monkeypatch.setattr(model_registry, "MODELS_DIR", tmp_path)
    (tmp_path / "XAUUSD_M5.pkl").write_bytes(b"artefato de teste")
    (tmp_path / "XAUUSD_M5.meta.json").write_text(
        json.dumps({"symbol": "XAUUSD", "timeframe": "M5"}), encoding="utf-8"
    )
    status, data = _request(gateway, "GET", "/api/ai/models")
    assert status == 200
    assert data["models"][0]["trained_symbol"] == "XAUUSD"
    assert data["models"][0]["training_verified"] is False


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


def test_demo_leituras_e_validate(gateway):
    """GETs demo e validate espelham os mesmos limites do painel DemoOrderPanel."""
    for path in ("/api/demo/positions", "/api/demo/orders",
                 "/api/demo/execution-status", "/api/demo/last-command"):
        status, _ = _request(gateway, "GET", path)
        assert status in {200, 403}, path
    status, data = _request(gateway, "POST", "/api/command/validate",
                            {"command": "/api/demo/close", "confirm_demo": True})
    assert status == 200 and data["valid"] is True


def test_demo_rejeita_limites_do_painel(gateway, monkeypatch):
    """Volume > 0.10, SL/TP ausentes e confirm ausente: 403/503 sem enfileirar.

    Espelha as regras do DemoOrderPanel (fieldsValid) + _demo_order.
    A trava XAU_ENABLE_DEMO_ORDERS fica LIGADA aqui para provar que a
    rejeicao vem da validacao, nao da trava.
    """
    monkeypatch.setenv("XAU_ENABLE_DEMO_ORDERS", "1")
    base = {"symbol": "XAUUSD", "side": "BUY", "confirm_demo": True}
    casos = [
        {**base, "volume": 0.11, "sl": 1.0, "tp": 2.0},   # acima do max
        {**base, "volume": 0.01, "sl": 0, "tp": 2.0},     # SL ausente
        {**base, "volume": 0.01, "sl": 1.0, "tp": 0},     # TP ausente
        {**base, "volume": 0.01, "sl": 1.0, "tp": 2.0,
         "confirm_demo": False},                           # sem confirmacao
        {**base, "volume": 0, "sl": 1.0, "tp": 2.0},      # volume zero
    ]
    for payload in casos:
        status, data = _request(gateway, "POST", "/api/demo/order", payload)
        assert status in {403, 503}, payload
        assert "demo" in json.dumps(data, ensure_ascii=False).lower()


def test_demo_recusa_conta_real(gateway, monkeypatch):
    """Conta REAL: ordem demo recusada mesmo com trava ligada e campos validos."""
    monkeypatch.setenv("XAU_ENABLE_DEMO_ORDERS", "1")
    import backend.mt5_gateway as gw

    real = type("A", (), {"login": 999, "trade_mode": 1,
                          "trade_allowed": True})()
    monkeypatch.setattr(gw._mt5(), "account_info", lambda: real)
    payload = {"symbol": "XAUUSD", "side": "SELL", "volume": 0.01,
               "sl": 1.0, "tp": 2.0, "confirm_demo": True}
    status, data = _request(gateway, "POST", "/api/demo/order", payload)
    assert status in {403, 503}
    texto = json.dumps(data, ensure_ascii=False).lower()
    assert "demo" in texto or "real" in texto



@pytest.mark.parametrize("failed_method", ["positions_get", "history_deals_get"])
@pytest.mark.parametrize("route", ["/api/demo/order", "/api/demo/pending"])
def test_demo_bloqueia_quando_leitura_de_risco_falha(gateway, monkeypatch, failed_method, route):
    """Erro de leitura do MT5 nunca equivale a risco zerado."""
    monkeypatch.setenv("XAU_ENABLE_DEMO_ORDERS", "1")
    import backend.mt5_gateway as gw

    mt5 = gw._mt5()
    monkeypatch.setattr(mt5, failed_method, lambda *args, **kwargs: None)
    sent = []
    monkeypatch.setattr(mt5, "order_send", lambda request: sent.append(request), raising=False)
    payload = {"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
               "sl": 0.5, "tp": 2.0, "confirm_demo": True}
    if route.endswith("pending"):
        payload.update({"kind": "limit", "price": 0.9})
    status, data = _request(gateway, "POST", route, payload)
    assert status == 503
    assert data["ok"] is False
    assert not sent


@pytest.mark.parametrize("route", ["/api/demo/order", "/api/demo/pending"])
def test_demo_bloqueia_limites_de_operacoes_e_drawdown(gateway, monkeypatch, route):
    import backend.mt5_gateway as gw

    monkeypatch.setenv("XAU_ENABLE_DEMO_ORDERS", "1")
    mt5 = gw._mt5()
    deals = [
        type("D", (), {"profit": 0.0, "commission": 0.0, "swap": 0.0, "entry": 0, "position_id": index, "ticket": index})()
        for index in range(1, 21)
    ]
    monkeypatch.setattr(mt5, "history_deals_get", lambda *args, **kwargs: deals)
    monkeypatch.setattr(gw.watchdog, "history", lambda limit=120: {"snapshots": [{"equity": 1200.0}], "last": {"equity": 1200.0}})
    sent = []
    monkeypatch.setattr(mt5, "order_send", lambda request: sent.append(request), raising=False)
    payload = {"symbol": "XAUUSD", "side": "BUY", "volume": 0.01, "sl": 0.5, "tp": 2.0, "confirm_demo": True}
    if route.endswith("pending"):
        payload.update({"kind": "limit", "price": 0.9})
    status, data = _request(gateway, "POST", route, payload)
    assert status == 403
    assert "operações" in data["error"] or "drawdown" in data["error"]
    assert not sent


def test_risk_state_calcula_operacoes_e_drawdown(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    mt5 = gw._mt5()
    deal = type("D", (), {"profit": 0.0, "commission": 0.0, "swap": 0.0, "entry": 0, "position_id": 10, "ticket": 20})()
    monkeypatch.setattr(mt5, "history_deals_get", lambda *args, **kwargs: [deal, deal])
    monkeypatch.setattr(gw.watchdog, "history", lambda limit=120: {"snapshots": [{"equity": 1200.0}], "last": {"equity": 1200.0}})
    state = gw._risk_state(mt5)
    assert state["daily_trades"] == 1
    assert state["drawdown_pct"] == 16.6667
    assert state["limits"]["max_daily_trades"] == 20
    assert state["limits"]["max_drawdown_pct"] == 15.0


def test_risk_state_recusa_saldo_indisponivel(gateway, monkeypatch):
    """A leitura direta de risco nao apresenta zeros falsos sem conta MT5."""
    import backend.mt5_gateway as gw

    monkeypatch.setattr(gw._mt5(), "account_info", lambda: None)
    with pytest.raises(RuntimeError, match="conta MT5 indisponivel"):
        gw._risk_state(gw._mt5())


def test_universal_somente_leitura_e_previews(gateway, monkeypatch):
    from unittest.mock import patch

    import backend.connection_service as service
    import backend.mt5_gateway as gw

    monkeypatch.setattr(gw, "_stored_exchange_credentials", lambda account_id, broker, market: ("key", "secret", "", account_id))
    monkeypatch.setattr(gw, "resolve_connection", lambda account_id, broker, market: {"id": account_id})

    class StubClient:
        def __init__(self, market="spot", *args):
            self.api_key = self.api_secret = self.secret = ""

        def account(self):
            return {"ok": True}

        def ticker(self, symbol):
            return {"bid": 1.0, "ask": 2.0}

        def depth(self, symbol, limit=20):
            return {"bids": [[1.0, 1.0]], "asks": [[2.0, 1.0]]}

        def trades(self, symbol, limit=20):
            return []

        def history(self, symbol=""):
            return []

    with patch.object(service, "MexcClient", StubClient), \
            patch("backend.mt5_gateway.MexcClient", StubClient):
        status, _ = _request(gateway, "GET",
                             "/api/universal/account?broker=mexc&market=crypto-spot&account_id=mexc%3Acrypto-spot%3Atest")
        assert status == 200
        status, _ = _request(gateway, "GET",
                             "/api/universal/quote?broker=mexc&market=crypto-spot&symbol=BTCUSDT")
        assert status == 200
        status, _ = _request(gateway, "GET",
                             "/api/universal/history?broker=mexc&market=crypto-spot&symbol=BTCUSDT&days=1&account_id=mexc%3Acrypto-spot%3Atest")
        assert status == 200
    payload = {"broker": "mexc", "market": "spot", "symbol": "BTCUSDT", "side": "buy",
               "order_type": "market", "quantity": 0.01, "account_id": "mexc:crypto-spot:test",
               "request_id": "t1", "confirm": False}
    for path in ("/api/universal/order", "/api/universal/close",
                 "/api/universal/modify", "/api/universal/cancel"):
        status, data = _request(gateway, "POST", path, payload)
        assert status in {200, 422}, path
        assert "withdrawals" in json.dumps(data).lower()


def test_emergencia_e_real_bloqueados(gateway, monkeypatch):
    status, _ = _request(gateway, "POST", "/api/universal/emergency-stop", {"confirm": True})
    assert status == 200
    status, _ = _request(gateway, "POST", "/api/demo/order", {"symbol": "XAUUSD", "confirm_demo": True})
    assert status == 403
    status, _ = _request(gateway, "POST", "/api/universal/emergency-resume", {"confirm": True})
    assert status == 403
    monkeypatch.setenv("XAU_ENABLE_EMERGENCY_RESUME", "1")
    status, _ = _request(gateway, "POST", "/api/universal/emergency-resume", {"confirm": True})
    assert status == 200
    status, data = _request(gateway, "POST", "/api/real/validate",
                            {"volume": 0.01, "daily_loss_pct": 0,
                             "exposure_pct": 0, "open_positions": 0,
                             "daily_trades": 0, "drawdown_pct": 0})
    assert status == 200 and data["execution_enabled"] is False
    status, data = _request(gateway, "POST", "/api/real/request",
                            {"request_id": "r1", "account_id": "a",
                             "broker": "mt5", "market": "forex"})
    assert status == 202 and data["execution_enabled"] is False
    status, data = _request(gateway, "POST", "/api/real/order",
                            {"request_id": "r1", "confirm_real": True})
    assert status in {403, 503} and data.get("ok") is False


@pytest.mark.parametrize("path", ["/api/universal/order", "/api/universal/close",
                                   "/api/universal/modify", "/api/universal/cancel"])
def test_execucao_universal_bloqueada_antes_do_roteador(gateway, monkeypatch, path):
    from backend.universal_router import UniversalRouter

    def proibido(*args, **kwargs):
        raise AssertionError("roteador de execução não pode ser chamado")

    monkeypatch.setattr(UniversalRouter, "execute", proibido)
    status, data = _request(gateway, "POST", path, {
        "execute": True, "authorize_execution": True, "confirm_live": True,
        "confirm": True, "request_id": "teste-bloqueio", "broker": "mexc",
        "market": "spot", "symbol": "BTCUSDT", "side": "buy", "quantity": 1,
    })
    assert status == 403
    assert data["status"] == "blocked" and data["execution_enabled"] is False


def test_real_bloqueado_mesmo_com_variavel_ligada(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    monkeypatch.setenv("XAU_ENABLE_REAL_ORDERS", "1")
    monkeypatch.setattr(gw, "_mt5", lambda: (_ for _ in ()).throw(AssertionError("MT5 não pode ser chamado")))
    status, data = _request(gateway, "POST", "/api/real/order", {
        "request_id": "teste-real", "confirm_real": True, "symbol": "XAUUSD",
        "side": "BUY", "volume": 0.01, "sl": 1, "tp": 2,
    })
    assert status == 403 and data["ok"] is False
    assert "indisponíveis" in data["error"]


def test_cobertura_restante_sem_envio(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    class PublicStub:
        def depth(self, symbol, limit=20):
            return {"bids": [[1.0, 1.0]], "asks": [[2.0, 1.0]]}

        def trades(self, symbol, limit=20):
            return []

    monkeypatch.setattr(gw, "_exchange_client", lambda *args, **kwargs: PublicStub())
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


def test_capabilities_declara_trava_real(gateway):
    status, data = _request(gateway, "GET", "/api/capabilities")
    assert status == 200
    assert data["real_orders_enabled"] is False
    assert data["real_commands"] == []

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

        def depth(self, symbol, limit=20):
            return {"bids": [[1.0, 1.0]], "asks": [[2.0, 1.0]]}

        def trades(self, symbol, limit=20):
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


def test_quote_read_only_nao_habilita_simbolo(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    monkeypatch.setattr(gw._mt5(), "symbol_select", lambda *args: (_ for _ in ()).throw(
        AssertionError("GET não pode habilitar símbolo")))
    status, data = _request(gateway, "GET", "/api/mt5/quote?symbol=XAUUSD")
    assert status == 200 and data["bid"] == 1.0


def test_put_e_delete_exigem_token(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    monkeypatch.setattr(gw, "API_TOKEN", "segredo-local")
    status, _ = _request(gateway, "GET", "/api/health")
    assert status == 401
    status, _ = _request(gateway, "GET", "/api/health", headers={"Authorization": "Bearer segredo-local"})
    assert status == 200
    status, _ = _request(gateway, "PUT", "/api/config", {"precision": 3})
    assert status == 401
    status, _ = _request(gateway, "PUT", "/api/config", {"precision": 3}, {"Authorization": "Bearer segredo-local"})
    assert status == 200
    status, _ = _request(gateway, "DELETE", "/api/connections/inexistente")
    assert status == 401


def test_escopo_invalido_retorna_422(gateway):
    status, data = _request(gateway, "GET", "/api/universal/quote?broker=binance&market=forex&symbol=EURUSD")
    assert status == 422
    assert data["status"] == "invalid"
    assert data["error_code"] == "invalid_request"


def test_matriz_de_capacidades_por_ativo(gateway):
    status, data = _request(gateway, "GET", "/api/universal/capabilities?broker=mt5&market=metals&symbol=XAUUSD")
    assert status == 200
    assert data["symbol"] == "XAUUSD"
    assert data["matrix"][0]["symbol"] == "XAUUSD"
    assert data["matrix"][0]["capability_matrix"]


def test_perfil_ea_externo_bloqueia_comandos_e_mantem_leitura(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    monkeypatch.setattr(gw, "THIRD_PARTY_READ_ONLY", True)
    status, _ = _request(gateway, "GET", "/api/capabilities")
    assert status == 200
    status, data = _request(gateway, "POST", "/api/demo/order", {"symbol": "XAUUSD", "confirm_demo": True})
    assert status == 403
    assert data["commands_enabled"] is False
    status, _ = _request(gateway, "POST", "/api/universal/emergency-stop", {"confirm": True})
    assert status == 200
    status, _ = _request(gateway, "PUT", "/api/config", {"precision": 3})
    assert status == 403


def test_comando_ea_rejeita_injecao_de_linha(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    monkeypatch.setenv("XAU_ENABLE_DEMO_ORDERS", "1")
    monkeypatch.setattr(gw, "_read_ea_heartbeat", lambda: {"live": True})
    with pytest.raises(ValueError, match="parâmetros"):
        gw._ea_command({"confirm_demo": True, "value": "M5\ncommand=close-all"}, "set-timeframe")
    assert not (gw.COMMON_FILES / "XAU_AI_PRO_ea_command.json").exists()


def test_endpoint_compatibilidade_ea_externo(gateway, monkeypatch):
    import backend.mt5_gateway as gw

    expected = {"ok": True, "status": "ok", "read_only": True, "commands_enabled": False, "adapters": [], "matched": 0}
    monkeypatch.setattr(gw, "evaluate_third_party_ea", lambda mt5: expected)
    status, data = _request(gateway, "GET", "/api/ea-compatibility")
    assert status == 200 and data == expected




