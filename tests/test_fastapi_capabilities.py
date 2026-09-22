"""Contrato auditável das capabilities do gateway FastAPI."""
from __future__ import annotations

import asyncio

from backend import fastapi_gateway


def test_capabilities_declara_travas_reais_e_saques_bloqueados() -> None:
    data = asyncio.run(fastapi_gateway.capabilities())

    assert data["ok"] is True
    assert data["source"] == "fastapi_gateway"
    assert data["real_orders_enabled"] is False
    assert data["withdrawals_enabled"] is False