"""Testes do servidor MCP de trading (roteamento puro, sem rede real)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import backend.trading_mcp as mcp  # noqa: E402


@pytest.fixture()
def http_stub(monkeypatch):
    chamadas: list[tuple[str, object]] = []

    def fake_http(path, payload=None, timeout=10.0):
        chamadas.append((path, payload))
        return {"http": 200, "ok": True, "path": path, "payload": payload}

    monkeypatch.setattr(mcp, "_http", fake_http)
    return chamadas


def test_tools_list_11_ferramentas():
    resposta = mcp.processar({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert len(resposta["result"]["tools"]) == 11


def test_initialize_handshake():
    resposta = mcp.processar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resposta["result"]["serverInfo"]["name"] == "xau-ai-pro-trading"


def test_notificacao_sem_resposta():
    assert mcp.processar({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_health_chama_gateway(http_stub):
    resultado = mcp.tool_call("health", {})
    assert resultado["path"] == "/api/health"


def test_place_order_nasce_dry_run(http_stub):
    mcp.tool_call("place_order", {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01})
    path, payload = http_stub[-1]
    assert path == "/api/universal/order"
    assert payload["execute"] is False  # freio 1: toda ordem nasce dry-run


def test_place_order_bloqueado_sem_env(http_stub):
    resultado = mcp.tool_call("place_order", {"symbol": "XAUUSD", "execute": True})
    assert resultado.get("bloqueado") is True  # freio 2: exige XAU_MCP_TRADING=1
    assert not http_stub  # nenhuma ordem saiu do MCP


def test_place_order_executa_com_env(http_stub, monkeypatch):
    monkeypatch.setattr(mcp, "TRADING_HABILITADO", True)
    mcp.tool_call("place_order", {"symbol": "XAUUSD", "execute": True})
    _, payload = http_stub[-1]
    assert payload["execute"] is True


def test_request_id_unico_por_chamada(http_stub):
    mcp.tool_call("place_order", {"symbol": "XAUUSD"})
    mcp.tool_call("place_order", {"symbol": "XAUUSD"})
    ids = {http_stub[-2][1]["request_id"], http_stub[-1][1]["request_id"]}
    assert len(ids) == 2  # dedupe do gateway não pode engolir a segunda ordem


def test_close_position_respeita_travas(http_stub, monkeypatch):
    mcp.tool_call("close_position", {"ticket": 1, "symbol": "XAUUSD"})
    _, payload = http_stub[-1]
    assert payload["execute"] is False  # dry-run por padrão
    resultado = mcp.tool_call("close_position", {"ticket": 1, "symbol": "XAUUSD", "execute": True})
    assert resultado.get("bloqueado") is True  # sem env, bloqueia
    monkeypatch.setattr(mcp, "TRADING_HABILITADO", True)
    mcp.tool_call("close_position", {"ticket": 1, "symbol": "XAUUSD", "execute": True})
    _, payload = http_stub[-1]
    assert payload["execute"] is True


def test_ferramenta_desconhecida(http_stub):
    assert "desconhecida" in mcp.tool_call("nao_existe", {})["error"]


def test_metodo_desconhecido_erro_rpc():
    resposta = mcp.processar({"jsonrpc": "2.0", "id": 9, "method": "metodo/que/nao/existe"})
    assert resposta["error"]["code"] == -32601