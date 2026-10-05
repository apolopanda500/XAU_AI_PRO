"""Contrato auditável das capabilities do gateway FastAPI."""
from __future__ import annotations

import asyncio
import json

import pytest

from backend import fastapi_gateway


def test_capabilities_declara_execucao_real_e_saques_bloqueados() -> None:
    data = asyncio.run(fastapi_gateway.capabilities())

    assert data["ok"] is True
    assert data["source"] == "fastapi_gateway"
    assert data["real_orders_enabled"] is True
    assert data["live_execution_enabled"] is True
    assert data["withdrawals_enabled"] is False
    assert data["transfers_enabled"] is False
    assert data["matrix"]
    assert all(row["execution"] for row in data["matrix"])
    assert all(row["withdrawals"] is False and row["transfers"] is False for row in data["matrix"])
    assert "trade/order" in data["trade_commands"]
    assert "start" in data["ea_commands"]
    assert data["third_party_ea"]["commands"] is False


def test_fastapi_universal_encaminha_execucao(monkeypatch):
    """execute=true roteia de verdade, em vez de devolver 403 'somente previa'."""
    from fastapi.testclient import TestClient

    import backend.fastapi_gateway as fgw

    vistos = []

    def _executor(payload, action):
        vistos.append(action)
        return {"ok": True, "status": "executed", "action": action}

    monkeypatch.setattr(fgw.gw, "_universal_execute", _executor)
    # Fail-closed com `.env` (05/10/2026): autentica para mirar o 200 da rota.
    monkeypatch.setattr(fgw, "API_TOKEN", "token-de-teste")
    cliente = TestClient(fgw.app)
    for acao, rota in (("order", "/api/universal/order"),
                       ("close", "/api/universal/close"),
                       ("modify", "/api/universal/modify"),
                       ("cancel", "/api/universal/cancel")):
        resposta = cliente.post(rota, json={"execute": True, "broker": "mt5",
                                            "market": "forex", "symbol": "XAUUSD",
                                            "account_id": "mt5:active"},
                                headers={"Authorization": "Bearer token-de-teste"})
        assert resposta.status_code == 200, (rota, resposta.text)
        assert resposta.json()["ok"] is True
        assert vistos, "o executor nao foi chamado"
        assert resposta.json().get("status") != "blocked"


def test_fastapi_real_bloqueado_independente_do_ambiente(monkeypatch) -> None:
    monkeypatch.setenv("XAU_ENABLE_REAL_ORDERS", "1")
    monkeypatch.setattr(fastapi_gateway.gw, "_mt5", lambda: (_ for _ in ()).throw(
        AssertionError("MT5 não pode ser chamado")))
    response = asyncio.run(fastapi_gateway.real_order({"confirm_real": True}))
    assert response.status_code == 403