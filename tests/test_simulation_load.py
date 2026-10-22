# -*- coding: utf-8 -*-
"""Bateria de carga — muitos usuarios concorrentes no mesmo gateway.

Ambiente FIXADO aqui (ver o cabecalho de `test_simulacao_ciclo_vida_real.py`):
o middleware so impoe 401 quando `API_TOKEN` esta preenchido, e ele vem do
`.env` da maquina. No CI (Linux, sem `.env`) o gateway sobe aberto e o teste
`test_401_no_token` via 200 em vez de 401 — o numero mudava conforme a maquina.
Aqui o token e fixado, a taxa de limite e desligada (a bateria faz centenas de
requisicoes em segundos) e os dois sentidos sao exercitados: anonimo da 401,
autenticado nunca da 401.
"""
from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from conftest import TOKEN_DE_TESTE  # noqa: E402
from _dublo_mt5 import terminal_desconectado  # noqa: E402

USERS = 30
TOKEN = TOKEN_DE_TESTE


@pytest.fixture(autouse=True)
def _ambiente_deterministico(monkeypatch, tmp_path):
    monkeypatch.setenv("XAU_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("XAU_REAL_EMERGENCY_FILE", str(tmp_path / "STOP"))
    monkeypatch.setitem(sys.modules, "MetaTrader5", terminal_desconectado())

    import backend.fastapi_gateway as fg
    import backend.mt5_gateway as gw

    monkeypatch.setattr(fg, "API_TOKEN", TOKEN)
    monkeypatch.setattr(gw, "RATE_LIMIT_MAX", 0, raising=False)
    monkeypatch.setattr(gw, "RATE_LIMIT_CMD_MAX", 0, raising=False)
    fg._RATE_STATE.update({"count": 0, "window": 0.0})
    fg._RATE_STATE_CMD.update({"count": 0, "window": 0.0})
    yield


@pytest.fixture
def anonimo():
    from backend.fastapi_gateway import app
    return TestClient(app)


@pytest.fixture
def client(anonimo):
    anonimo.headers.update({"Authorization": f"Bearer {TOKEN}"})
    return anonimo


class TestConcurrentSimulation:
    """Simula muitos usuarios pelo test client do FastAPI."""

    def test_health_autenticado_200(self, client):
        codes = [client.get("/api/health").status_code for _ in range(USERS)]
        assert set(codes) == {200}, codes

    def test_account_sem_corretora(self, client):
        codes = [client.get("/api/universal/account").status_code for _ in range(USERS)]
        assert set(codes) <= {422, 503}, codes

    def test_overview_autenticado(self, client):
        codes = [client.get("/api/universal/overview").status_code for _ in range(USERS)]
        assert set(codes) <= {200, 422, 503}, codes

    def test_symbols(self, client):
        for sym in ("XAUUSD", "EURUSD", "BTCUSD", "ETHUSD", ""):
            codes = [client.get(f"/api/universal/capabilities?symbol={sym}").status_code
                     for _ in range(3)]
            assert set(codes) <= {200, 403, 422, 503}, f"{sym}: {codes}"

    def test_invalid_orders_never_accepted(self, client):
        """Ordem invalida nao e aceita em lugar nenhum; o corpo diz por que.

        O preview de `/api/universal/order` devolve **200 com `ok:false`**
        (medido: `_universal_execution_preview` devolve `error_response(...)` e
        `_send` usa `code=200` por padrao). Por isso a prova e do CORPO, nao do
        codigo de transporte: um 200 com `accepted:true` seria aceitacao.
        """
        pedidos = [
            {"symbol": "XAUUSD", "quantity": -0.01, "side": "buy",
             "broker": "mt5", "market": "metals", "account_id": "carga",
             "order_type": "market", "execute": False, "confirm": True,
             "request_id": "carga-neg"},
            {"symbol": "", "quantity": 0.01, "side": "buy",
             "broker": "mt5", "market": "metals", "account_id": "carga",
             "order_type": "market", "execute": False, "confirm": True,
             "request_id": "carga-vazio"},
        ]
        for pedido in pedidos:
            for _ in range(2):
                r = client.post("/api/universal/order", json=pedido)
                corpo = r.json()
                assert corpo.get("ok") is False, r.text
                assert corpo.get("accepted") is not True, r.text
                assert corpo.get("error", {}).get("code") in {
                    "INVALID_UNIVERSAL_REQUEST", "RISK_REJECTED", "REJECTED",
                } or corpo.get("error"), r.text

    def test_idempotent_ids(self, client):
        """O mesmo `request_id` duas vezes devolve o MESMO resultado.

        Aqui `execute=false`, entao o que se prova e a estabilidade da
        validacao: a segunda chamada nao muda de ideia nem inventa uma segunda
        ordem. Um corpo diferente na repeticao seria recusa com motivo errado
        (§5) — o operador veria uma ordem ida e outra nao.
        """
        seen, viol = set(), []
        for i in range(USERS * 2):
            rid = f"test-{i}"
            if rid in seen:
                viol.append(rid)
            seen.add(rid)
            payload = {"symbol": "XAUUSD", "volume": 0.01, "price": 2000,
                       "side": "buy", "broker": "mt5", "market": "metals",
                       "account_id": "carga", "request_id": rid,
                       "confirm": True, "execute": False}
            primeira = client.post("/api/universal/order", json=payload)
            segunda = client.post("/api/universal/order", json=payload)
            corpo1, corpo2 = primeira.json(), segunda.json()
            # Nunca executado: o preview so valida (stage) ou recusa (error).
            assert corpo1.get("stage") in (None, "validated"), corpo1
            assert corpo1.get("execution") is None, corpo1
            assert corpo1 == corpo2, (rid, corpo1, corpo2)
        assert not viol, viol

    def test_401_no_token(self, anonimo):
        """Fail-closed: sem credencial nenhuma rota responde conteudo."""
        codes = [anonimo.get("/api/health").status_code for _ in range(USERS * 3)]
        assert set(codes) == {401}, codes

    def test_401_permanece_em_todas_as_rotas(self, anonimo):
        rotas = ("/api/health", "/api/capabilities", "/api/universal/overview",
                 "/api/ai/models", "/api/auto/state")
        codes = [anonimo.get(rota).status_code for rota in rotas]
        assert set(codes) == {401}, codes

    def test_mixed_requests(self, client):
        codes = []
        for i in range(USERS):
            if i % 3 == 0:
                codes.append(client.get("/api/health").status_code)
            elif i % 3 == 1:
                codes.append(client.get("/api/capabilities").status_code)
            else:
                codes.append(client.post(
                    "/api/universal/order",
                    json={"symbol": "XAUUSD", "volume": 0, "price": 0, "side": "buy",
                          "broker": "mt5", "market": "metals", "execute": False,
                          "request_id": f"misto-{i}"}).status_code)
        assert set(codes) <= {200, 400, 403, 422}, codes
        assert 401 not in codes
