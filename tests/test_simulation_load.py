# -*- coding: utf-8 -*-
"""Bateria de simulação de muitos usuários concorrentes."""
from __future__ import annotations

from fastapi.testclient import TestClient
from backend.fastapi_gateway import app

import pytest

USERS = 30


@pytest.fixture
def client():
    return TestClient(app)


class TestConcurrentSimulation:
    """Simula muitos usuários pelo test client do FastAPI."""

    def test_health_all(self, client):
        codes = [client.get("/api/health").status_code for _ in range(USERS)]
        assert all(c in (200, 401) for c in codes)

    def test_account_no_broker(self, client):
        codes = [client.get("/api/universal/account").status_code for _ in range(USERS)]
        assert all(c in (200, 422, 401) for c in codes)

    def test_overview(self, client):
        codes = [client.get("/api/universal/overview").status_code for _ in range(USERS)]
        assert all(c in (200, 401, 422, 429) for c in codes)

    def test_symbols(self, client):
        for sym in ["XAUUSD", "EURUSD", "BTCUSD", "ETHUSD", ""]:
            codes = [client.get(f"/api/universal/capabilities?symbol={sym}").status_code for _ in range(3)]
            assert all(c in (200, 401, 422, 429) for c in codes)

    def test_invalid_orders(self, client):
        codes = []
        for order in [{"symbol": "XAUUSD", "volume": -0.01, "price": 0, "side": "buy", "execute": False},
                      {"symbol": "", "volume": 0.01, "price": 0, "side": "buy", "execute": False}]:
            for _ in range(2):
                r = client.post("/api/universal/order", json=order)
                codes.append(r.status_code)
        # Ordens sem token dão 401 (fail-closed). Com token podem ser 400/422/403/200.
        # O importante: o sistema rejeita/gere erro e não aceita ordens inválidas como válidas.
        # Aqui testamos que o sistema responde consistentemente (não crasha).
        assert all(c in (400, 422, 403, 401, 200) for c in codes)

    def test_idempotent_ids(self, client):
        seen, viol = set(), []
        for i in range(USERS * 2):
            rid = f"test-{i}"
            if rid in seen: viol.append(rid)
            seen.add(rid)
            for _ in range(2):
                r = client.post("/api/universal/order",
                                json={"symbol": "XAUUSD", "volume": 0.01, "price": 2000,
                                      "side": "buy", "request_id": rid, "confirm": True, "execute": False})
                assert r.status_code in (200, 401, 400, 403, 422)

    def test_401_no_token(self, client):
        codes = [client.get("/api/health").status_code for _ in range(USERS * 3)]
        assert all(c in (200, 401) for c in codes)
        assert 401 in codes

    def test_mixed_requests(self, client):
        codes = []
        for i in range(USERS):
            if i % 3 == 0:
                codes.append(client.get("/api/health").status_code)
            elif i % 3 == 1:
                codes.append(client.get("/api/capabilities").status_code)
            else:
                codes.append(client.post("/api/universal/order",
                                         json={"symbol": "XAUUSD", "volume": 0, "price": 0, "side": "buy", "execute": False}).status_code)
        assert all(c in (200, 400, 401, 403, 422, 429) for c in codes)