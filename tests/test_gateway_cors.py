"""CORS do gateway local (pré-requisito Android: origens e preflight corretos)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def gw(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XAU_MT5_COMMON_FILES", str(tmp_path / "common"))
    monkeypatch.setenv("XAU_APP_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("XAU_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("XAU_REAL_EMERGENCY_FILE", str(tmp_path / "STOP"))
    fake = ModuleType("MetaTrader5")
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    import backend.mt5_gateway as gw_mod

    return importlib.reload(gw_mod)


def test_preflight_options_204(gw):
    from backend.mt5_gateway import Handler

    handler = Handler.__new__(Handler)
    status: list[int] = []
    handler.send_response = lambda code, *a, **k: status.append(code)  # type: ignore[method-assign]
    handler.end_headers = lambda: None  # type: ignore[method-assign]
    sent: dict[str, str] = {}
    handler.send_header = lambda name, value: sent.__setitem__(name, value)  # type: ignore[method-assign]
    handler.headers = {}  # type: ignore[attr-defined]

    Handler.do_OPTIONS(handler)  # type: ignore[arg-type]

    assert status == [204]
    assert sent.get("Access-Control-Allow-Origin") == "*"
    assert sent.get("Access-Control-Allow-Methods") == "GET, POST, PUT, DELETE, OPTIONS"
    assert sent.get("Access-Control-Allow-Headers") == "Content-Type, Authorization"


def test_respostas_incluem_allow_origin(gw):
    """Toda resposta JSON do gateway deve carregar Access-Control-Allow-Origin."""
    from backend.mt5_gateway import Handler

    src = Path(gw.__file__).read_text(encoding="utf-8", errors="ignore")
    assert '"Access-Control-Allow-Origin"' in src, "gateway sem header CORS"


def test_fastapi_health_exige_token_quando_configurado(monkeypatch):
    import asyncio
    import httpx
    from backend import fastapi_gateway

    async def exercise():
        transport = httpx.ASGITransport(app=fastapi_gateway.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/api/health")).status_code == 401
            response = await client.get(
                "/api/health",
                headers={"Authorization": "Bearer segredo-local"},
            )
            assert response.status_code == 200
            assert response.json()["gateway_build"].startswith("xau-ai-pro-")

    monkeypatch.setattr(fastapi_gateway, "API_TOKEN", "segredo-local")
    asyncio.run(exercise())
