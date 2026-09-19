"""Contrato HTTP de conexões: cadastro e validação somente leitura.

Usa servidor efêmero em 127.0.0.1:0, credenciais sintéticas e clientes stub.
Nenhuma credencial real é lida; nenhum arquivo do usuário é alterado.
"""
from __future__ import annotations

import http.client
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)


@pytest.fixture()
def gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    original = Path.read_text

    def safe_read(self, *args, **kwargs):
        if self.name.startswith(".env"):
            return ""
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", safe_read)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import backend.mt5_gateway as gw

    server = ThreadingHTTPServer(("127.0.0.1", 0), gw.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _request(base: str, method: str, path: str, payload: dict | None = None):
    host, port = base.split(":")
    conn = http.client.HTTPConnection(host, int(port), timeout=10)
    body = json.dumps(payload) if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = json.loads(response.read() or b"{}")
    conn.close()
    return response.status, data


def test_save_rejeita_api_key_para_mt5(gateway):
    payload = {"id": "mt5:forex:x", "broker": "mt5", "market": "forex", "api_key": "k", "api_secret": "s"}
    status, data = _request(gateway, "POST", "/api/connections", payload)
    assert status == 422 and data["ok"] is False and "terminal" in data["error"]


def test_salva_e_testa_leitura_com_stub(gateway):
    payload = {"id": "mexc:crypto-spot:demo", "broker": "mexc", "market": "crypto-spot", "api_key": "KEY", "api_secret": "SECRET"}

    status, data = _request(gateway, "POST", "/api/connections", payload)
    assert status == 201 and data["ok"] is True and data["validated"] is False
    assert data["connection"]["id"] == payload["id"]
    assert "api_key" not in data["connection"] and "api_secret" not in data["connection"]

    class StubClient:
        def __init__(self, market: str = "spot") -> None:
            self.api_key = ""
            self.api_secret = ""

        def account(self):
            return {"ok": True}

    import backend.connection_service as service

    with patch.object(service, "MexcClient", StubClient):
        status, data = _request(gateway, "POST", "/api/connections/mexc:crypto-spot:demo/test", {})
    assert status == 200 and data["validated"] is True and data["read_only"] is True

    status, data = _request(gateway, "POST", "/api/connections/inexistente/test", {})
    assert status == 404 and data["ok"] is False and data["credentials_exposed"] is False

    with patch.object(service, "MexcClient", StubClient):
        status, data = _request(gateway, "POST", "/api/connections/mexc:crypto-spot:demo/deactivate", {})
    assert status == 200 and data["active"] is False

    status, data = _request(gateway, "GET", "/api/connections")
    assert status == 200
    assert all("api_key" not in item and "api_secret" not in item for item in data["connections"])


def test_falha_de_validacao_retorna_502_sem_segredos(gateway):
    payload = {"id": "binance:crypto-spot:demo", "broker": "binance", "market": "crypto-spot", "api_key": "KEY", "api_secret": "SECRET"}

    status, _ = _request(gateway, "POST", "/api/connections", payload)
    assert status == 201

    class BrokenClient:
        def __init__(self, market: str = "spot") -> None:
            self.api_key = ""
            self.secret = ""

        def account(self):
            raise RuntimeError("binance indisponível (stub)")

    import backend.connection_service as service

    with patch.object(service, "BinanceClient", BrokenClient):
        status, data = _request(gateway, "POST", "/api/connections/binance:crypto-spot:demo/test", {})
    assert status == 502 and data["validated"] is False
    assert "KEY" not in json.dumps(data) and "SECRET" not in json.dumps(data)
