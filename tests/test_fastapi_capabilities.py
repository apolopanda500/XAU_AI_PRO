"""Contrato auditável das capabilities do gateway FastAPI."""
from __future__ import annotations

import asyncio
import json

import pytest

from backend import fastapi_gateway


def test_capabilities_declara_travas_reais_e_saques_bloqueados() -> None:
    data = asyncio.run(fastapi_gateway.capabilities())

    assert data["ok"] is True
    assert data["source"] == "fastapi_gateway"
    assert data["real_orders_enabled"] is False
    assert data["withdrawals_enabled"] is False
    assert data["matrix"]
    assert all(row["execution"] == [] for row in data["matrix"])
    assert all(row["withdrawals"] is False and row["transfers"] is False for row in data["matrix"])
    assert data["third_party_ea"]["commands"] is False


@pytest.mark.parametrize("handler", [fastapi_gateway.universal_order,
                                     fastapi_gateway.universal_close,
                                     fastapi_gateway.universal_modify,
                                     fastapi_gateway.universal_cancel])
def test_fastapi_universal_nao_encaminha_execucao(handler, monkeypatch) -> None:
    from backend.universal_router import UniversalRouter

    def proibido(*args, **kwargs):
        raise AssertionError("roteador não deve receber execução")

    monkeypatch.setattr(UniversalRouter, "execute", proibido)
    response = asyncio.run(handler({"execute": True, "authorize_execution": True,
                                    "confirm_live": True, "request_id": "teste"}))
    data = json.loads(response.body)
    assert response.status_code == 403
    assert data["status"] == "blocked" and data["execution_enabled"] is False


def test_fastapi_real_bloqueado_independente_do_ambiente(monkeypatch) -> None:
    monkeypatch.setenv("XAU_ENABLE_REAL_ORDERS", "1")
    monkeypatch.setattr(fastapi_gateway.gw, "_mt5", lambda: (_ for _ in ()).throw(
        AssertionError("MT5 não pode ser chamado")))
    response = asyncio.run(fastapi_gateway.real_order({"confirm_real": True}))
    assert response.status_code == 403