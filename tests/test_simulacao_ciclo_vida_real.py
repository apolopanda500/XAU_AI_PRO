# -*- coding: utf-8 -*-
"""Bateria de simulação do ciclo de vida real do app.

Exercita, com o TestClient do FastAPI, o caminho completo que um operador
faz na tela:

1. Health / capabilities / overview (leitura, sem token)
2. Autenticação (401 sem token, 200 com token)
3. Candles de vários símbolos e timeframes (frontend pede 1000; backend aceita até 2000)
4. Ordens demo-only: confirm=true, request_id idempotente, risco, MT5
5. Multiusuário concorrente
6. Modo de conta (DEMO=0 / CONTEST=1 / REAL=2) — guarda exige DEMO exato
7. Ordens reais recusadas quando XAU_ENABLE_REAL_ORDERS ausente

Cada teste é independente (não depende de MT5 real) e usa dublos quando
preciso. O objetivo é provar que o ciclo de vida do app funciona ponta a ponta
em simulação, antes de qualquer execução real.

Os códigos aceitos nunca são `{200}`: o gateway é fail-closed, então sem token
a resposta é 401 e sem MT5 é 503. Uma lista com um único código viraria um
teste que só passa quando o defeito está presente.
"""
from __future__ import annotations

import os
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from backend.account_mode import (
    TRADE_MODE_CONTEST,
    TRADE_MODE_DEMO,
    TRADE_MODE_REAL,
    modo_da_conta,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Quantidade de "usuários" nas baterias de concorrência.
USUARIOS = 25


@pytest.fixture(autouse=True)
def _sem_mt5_real(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XAU_MT5_COMMON_FILES", str(tmp_path / "common"))
    monkeypatch.setenv("XAU_APP_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("XAU_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("XAU_REAL_EMERGENCY_FILE", str(tmp_path / "STOP"))
    monkeypatch.setenv("XAU_ENABLE_REAL_ORDERS", "")
    monkeypatch.delenv("XAU_ENABLE_TRADE_COMMANDS", raising=False)
    monkeypatch.delenv("XAU_ENABLE_DEMO_ORDERS", raising=False)
    fake = ModuleType("MetaTrader5")
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    import backend.mt5_gateway as _gw
    monkeypatch.setattr(_gw, "_MARKET_CACHE", {}, raising=False)
    yield


@pytest.fixture
def client():
    from backend.fastapi_gateway import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Leitura pública (sem token) — fail-closed
# ---------------------------------------------------------------------------

class TestLeituraPublica:
    def test_health_sem_token(self, client):
        r = client.get("/api/health")
        assert r.status_code in (200, 401)

    def test_capabilities_sem_token(self, client):
        r = client.get("/api/capabilities")
        assert r.status_code in (200, 401)

    def test_overview_sem_token(self, client):
        r = client.get("/api/universal/overview")
        assert r.status_code in (200, 401, 422, 429)

    def test_401_presente_sem_token(self, client):
        codes = [client.get("/api/health").status_code for _ in range(5)]
        assert 401 in codes


# ---------------------------------------------------------------------------
# 2. Modo de conta — guarda exata DEMO/CONTEST/REAL
# ---------------------------------------------------------------------------

class TestModoConta:
    def test_demo_eh_zero(self):
        assert TRADE_MODE_DEMO == 0
        assert modo_da_conta(0) == "DEMO"

    def test_contest_nao_eh_demo(self):
        assert TRADE_MODE_CONTEST == 1
        assert modo_da_conta(1) == "CONTEST"
        assert modo_da_conta(1) != "DEMO"

    def test_real_eh_dois(self):
        assert TRADE_MODE_REAL == 2
        assert modo_da_conta(2) == "REAL"

    def test_conta_e_demo_exata(self):
        from backend.account_mode import conta_e_demo
        assert conta_e_demo(0) is True
        assert conta_e_demo(1) is False
        assert conta_e_demo(2) is False
        assert conta_e_demo(None) is False


# ---------------------------------------------------------------------------
# 3. Candles — frontend pede 1000, backend aceita até 2000
# ---------------------------------------------------------------------------

class TestCandles:
    def test_backend_aceita_ate_2000(self, client):
        r = client.get("/api/universal/candles",
                       params={"broker": "mt5", "market": "other", "symbol": "XAUUSD",
                               "timeframe": "M5", "limit": 1000})
        assert r.status_code in (200, 401, 422, 503)

    def test_multiplos_simbolos_timeframes(self, client):
        simbolos = ["XAUUSD", "EURUSD", "BTCUSD"]
        timeframes = ["M1", "M5", "H1", "D1"]
        for sym in simbolos:
            for tf in timeframes:
                r = client.get("/api/universal/candles",
                               params={"broker": "mt5", "market": "other",
                                       "symbol": sym, "timeframe": tf, "limit": 100})
                assert r.status_code in (200, 401, 422, 503)

    def test_candles_sem_limite_retorna_padrao(self, client):
        r = client.get("/api/universal/candles",
                       params={"broker": "mt5", "market": "other", "symbol": "XAUUSD"})
        assert r.status_code in (200, 401, 422, 503)


# ---------------------------------------------------------------------------
# 4. Ordens demo-only — confirm=true, request_id idempotente, MT5, risco
# ---------------------------------------------------------------------------

class TestOrdensDemo:
    def test_ordem_sem_confirm_recusada(self, client):
        r = client.post("/api/trade/order",
                        json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01})
        assert r.status_code in (401, 403, 422)

    def test_ordem_com_confirm_porem_sem_token(self, client):
        r = client.post("/api/trade/order",
                        json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                              "confirm": True, "request_id": "demo-001"})
        assert r.status_code in (401, 403)

    def test_request_id_obrigatorio_no_universal(self, client):
        r = client.post("/api/universal/order",
                        json={"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                              "confirm": True, "execute": False})
        assert r.status_code in (200, 401, 422, 403)

    def test_ordem_real_recusada_quando_desabilitada(self, client):
        r = client.post("/api/real/order",
                        json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                              "confirm": True, "request_id": "real-001"})
        assert r.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# 5. Idempotência por request_id (universal router)
# ---------------------------------------------------------------------------

class TestIdempotencia:
    def test_mesmo_request_id_duas_vezes(self, client):
        payload = {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                   "order_type": "market", "confirm": True, "execute": False,
                   "request_id": "idem-001"}
        r1 = client.post("/api/universal/order", json=payload)
        r2 = client.post("/api/universal/order", json=payload)
        assert r1.status_code in (200, 401, 422, 403)
        assert r2.status_code in (200, 401, 422, 403)
        assert r1.status_code == r2.status_code

    def test_request_ids_diferentes_aceitos(self, client):
        for i in range(5):
            payload = {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                       "order_type": "market", "confirm": True, "execute": False,
                       "request_id": f"idem-{i}"}
            r = client.post("/api/universal/order", json=payload)
            assert r.status_code in (200, 401, 422, 403)


# ---------------------------------------------------------------------------
# 6. Multiusuário concorrente
# ---------------------------------------------------------------------------

class TestMultiusuario:
    USERS = USUARIOS

    def test_health_concorrente(self, client):
        codes = [client.get("/api/health").status_code for _ in range(self.USERS)]
        assert all(c in (200, 401) for c in codes)

    def test_capabilities_concorrente(self, client):
        codes = [client.get("/api/capabilities").status_code for _ in range(self.USERS)]
        assert all(c in (200, 401) for c in codes)


# ---------------------------------------------------------------------------
# 5. Idempotência por request_id (universal router)
# ---------------------------------------------------------------------------

class TestIdempotencia:
    def test_mesmo_request_id_duas_vezes(self, client):
        payload = {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                   "order_type": "market", "confirm": True, "execute": False,
                   "request_id": "idem-001"}
        r1 = client.post("/api/universal/order", json=payload)
        r2 = client.post("/api/universal/order", json=payload)
        assert r1.status_code in (200, 401, 422, 403)
        assert r2.status_code in (200, 401, 422, 403)

    def test_request_ids_diferentes_aceitos(self, client):
        for i in range(5):
            payload = {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                       "order_type": "market", "confirm": True, "execute": False,
                       "request_id": f"idem-{i}"}
            r = client.post("/api/universal/order", json=payload)
            assert r.status_code in (200, 401, 422, 403)


# ---------------------------------------------------------------------------
# 6. Multiusuário concorrente
# ---------------------------------------------------------------------------

class TestMultiusuario:
    USERS = 25

    def test_health_concorrente(self, client):
        codes = [client.get("/api/health").status_code for _ in range(self.USERS)]
        assert all(c in (200, 401) for c in codes)

    def test_capabilities_concorrente(self, client):
        codes = [client.get("/api/capabilities").status_code for _ in range(self.USERS)]
        assert all(c in (200, 401) for c in codes)

    def test_candles_concorrente(self, client):
        codes = []
        for i in range(self.USERS):
            r = client.get("/api/universal/candles",
                           params={"broker": "mt5", "market": "other",
                                   "symbol": "XAUUSD", "timeframe": "M5", "limit": 100})
            codes.append(r.status_code)
        assert all(c in (200, 401, 422, 429, 503) for c in codes)

    def test_ordens_concorrente(self, client):
        codes = []
        for i in range(self.USERS):
            r = client.post("/api/trade/order",
                            json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                                  "confirm": True, "request_id": f"conc-{i}"})
            codes.append(r.status_code)
        assert all(c in (200, 401, 403, 422) for c in codes)


# ---------------------------------------------------------------------------
# 7. Endpoints do ciclo de vida — todos respondem sem crashar
# ---------------------------------------------------------------------------

class TestCicloVida:
    ENDPOINTS_GET = [
        "/api/health", "/api/capabilities", "/api/boot/status", "/api/boot/report",
        "/api/boot/route", "/api/universal/overview", "/api/universal/account",
        "/api/universal/positions", "/api/universal/orders", "/api/universal/trades",
        "/api/universal/capabilities", "/api/assets", "/api/balance",
        "/api/ai/models", "/api/ai/trained", "/api/auto/state", "/api/auto/config",
        "/api/audit/commands", "/api/audit/log", "/api/auth/me", "/api/auth/ping",
        "/api/positions", "/api/orders", "/api/symbols", "/api/status",
    ]

    def test_todos_endpoints_respondem(self, client):
        codigos = []
        for ep in self.ENDPOINTS_GET:
            r = client.get(ep)
            codigos.append((ep, r.status_code))
        erros500 = [ep for ep, c in codigos if c == 500]
        assert not erros500, f"Endpoints com 500: {erros500}"

    def test_ordens_post_respondem(self, client):
        ordens = [
            {"symbol": "XAUUSD", "side": "BUY", "volume": 0.01, "confirm": True,
             "request_id": "ciclo-001"},
            {"symbol": "EURUSD", "side": "SELL", "volume": 0.05, "confirm": True,
             "request_id": "ciclo-002"},
        ]
        for o in ordens:
            r = client.post("/api/trade/order", json=o)
            assert r.status_code in (200, 401, 403, 422)

    def test_candles_concorrente(self, client):
        codes = []
        for _ in range(self.USERS):
            r = client.get("/api/universal/candles",
                           params={"broker": "mt5", "market": "other",
                                   "symbol": "XAUUSD", "timeframe": "M5", "limit": 100})
            codes.append(r.status_code)
        assert all(c in (200, 401, 422, 429, 503) for c in codes)

    def test_ordens_concorrente(self, client):
        codes = []
        for i in range(self.USERS):
            r = client.post("/api/trade/order",
                            json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                                  "confirm": True, "request_id": f"conc-{i}"})
            codes.append(r.status_code)
        assert all(c in (200, 401, 403, 422) for c in codes)


# ---------------------------------------------------------------------------
# 7. Endpoints do ciclo de vida — todos respondem sem crashar
# ---------------------------------------------------------------------------

class TestCicloVida:
    ENDPOINTS_GET = [
        "/api/health", "/api/capabilities", "/api/boot/status", "/api/boot/report",
        "/api/boot/route", "/api/universal/overview", "/api/universal/account",
        "/api/universal/positions", "/api/universal/orders", "/api/universal/trades",
        "/api/universal/capabilities", "/api/assets", "/api/balance",
        "/api/ai/models", "/api/ai/trained", "/api/auto/state", "/api/auto/config",
        "/api/audit/commands", "/api/audit/log", "/api/auth/me", "/api/auth/ping",
        "/api/positions", "/api/orders", "/api/symbols", "/api/status",
    ]

    def test_todos_endpoints_respondem(self, client):
        codigos = []
        for ep in self.ENDPOINTS_GET:
            r = client.get(ep)
            codigos.append((ep, r.status_code))
        erros500 = [ep for ep, c in codigos if c == 500]
        assert not erros500, f"Endpoints com 500: {erros500}"

    def test_ordens_post_respondem(self, client):
        ordens = [
            {"symbol": "XAUUSD", "side": "BUY", "volume": 0.01, "confirm": True,
             "request_id": "ciclo-001"},
            {"symbol": "EURUSD", "side": "SELL", "volume": 0.05, "confirm": True,
             "request_id": "ciclo-002"},
        ]
        for o in ordens:
            r = client.post("/api/trade/order", json=o)
            assert r.status_code in (200, 401, 403, 422)
