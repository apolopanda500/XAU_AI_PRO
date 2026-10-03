"""Contrato HTTP de conexÃµes: cadastro e validaÃ§Ã£o somente leitura.

Usa servidor efÃªmero em 127.0.0.1:0, credenciais sintÃ©ticas e clientes stub.
Nenhuma credencial real Ã© lida; nenhum arquivo do usuÃ¡rio Ã© alterado.
"""
from __future__ import annotations

import http.client
import json
import sys
import threading

from conftest import TOKEN_DE_TESTE
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)

# Salvar credencial usa DPAPI do Windows: `connection_store._protect()` chama
# `ctypes.windll.crypt32.CryptProtectData`. Em runner Linux a API nao existe,
# a excecao vira 503 e o teste falha assertando 201 â€” sem que exista
# qualquer defeito no contrato HTTP.
#
# DPAPI e a garantia de que a credencial nao sai do Windows do operador
# (decisao C5 de `Docs/DECISOES_PRODUTO_20260925.md`). Nao ha equivalente
# para Linux, e nao deve haver: o produto e desktop Windows.
_REQUERE_DPAPI = pytest.mark.skipif(
    sys.platform != "win32",
    reason="cadastro de credencial usa DPAPI (ctypes.windll.crypt32), API do Windows",
)


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
    # Gateway fail-closed: sem token ele recusa tudo. Definido antes do import
    # para que `API_TOKEN` ja valha; a validacao continua real.
    monkeypatch.setenv("XAU_GATEWAY_TOKEN", TOKEN_DE_TESTE)
    monkeypatch.setenv("XAU_RATE_LIMIT", "0")
    monkeypatch.setenv("XAU_RATE_LIMIT_CMD", "0")
    import backend.mt5_gateway as gw
    import importlib

    gw = importlib.reload(gw)

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
    headers["Authorization"] = f"Bearer {TOKEN_DE_TESTE}"
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = json.loads(response.read() or b"{}")
    conn.close()
    return response.status, data


def test_mt5_entra_no_mesmo_fluxo_de_conexao(gateway):
    """MT5 e uma conexao como as outras - a credencial vem da sessao.

    Antes este teste afirmava o CONTRARIO: 422 "nao cadastre API key para
    MT5". A regra do dono e o oposto de excecao: nenhuma corretora pode ser
    caminho exclusivo, e MT5 nao e caso especial, e uma fonte de credencial
    diferente.

    O que muda e o que a tela recebe: `credential_source: "session"` diz que
    nao ha API key para pedir, em vez de a corretora sumir do fluxo.
    """
    payload = {"id": "mt5:forex:terminal", "broker": "mt5", "market": "forex"}
    status, data = _request(gateway, "POST", "/api/connections", payload)
    assert status == 201, data
    assert data["ok"] is True
    assert data["credential_source"] == "session"

    status, data = _request(gateway, "GET", "/api/connections")
    assert status == 200
    linha = next(c for c in data["connections"] if c["id"] == payload["id"])
    assert linha["broker"] == "mt5"
    assert linha["credential_source"] == "session"
    assert linha["configured"] is False
    # Sem API key gravada: gravar string vazia no DPAPI seria mentira.
    assert "api_key" not in linha and "api_secret" not in linha


def test_corretora_desconhecida_e_recusada(gateway):
    status, data = _request(
        gateway, "POST", "/api/connections",
        {"id": "x:forex:y", "broker": "nao-existe", "market": "forex"},
    )
    assert status == 422 and data["ok"] is False
    assert "desconhecida" in data["error"].lower()


def test_mercado_incompativel_com_a_corretora_e_recusado(gateway):
    """Binance so faz cripto. A recusa vem do catalogo, nao de uma lista local."""
    status, data = _request(
        gateway, "POST", "/api/connections",
        {"id": "binance:forex:x", "broker": "binance", "market": "forex",
         "api_key": "k", "api_secret": "s"},
    )
    assert status == 422 and data["ok"] is False
    assert "forex" in data["error"]


@_REQUERE_DPAPI
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

    # O patch mira o REGISTRO `CLIENTES`, nao o nome importado: e o registro
    # que decide qual construtor entra em uso. Apontar para `MexcClient`
    # ainda passaria no teste antigo e pararia de valer aqui.
    with patch.dict(service.CLIENTES, {"mexc": StubClient}):
        status, data = _request(gateway, "POST", "/api/connections/mexc:crypto-spot:demo/test", {})
    assert status == 200 and data["validated"] is True and data["read_only"] is True

    status, data = _request(gateway, "POST", "/api/connections/inexistente/test", {})
    assert status == 404 and data["ok"] is False and data["credentials_exposed"] is False

    with patch.dict(service.CLIENTES, {"mexc": StubClient}):
        status, data = _request(gateway, "POST", "/api/connections/mexc:crypto-spot:demo/deactivate", {})
    assert status == 200 and data["active"] is False

    status, data = _request(gateway, "GET", "/api/connections")
    assert status == 200
    assert all("api_key" not in item and "api_secret" not in item for item in data["connections"])


def test_leitura_de_conexoes_nao_cria_diretorio(gateway, tmp_path, monkeypatch):
    missing = tmp_path / "missing-appdata"
    monkeypatch.setenv("APPDATA", str(missing))
    status, data = _request(gateway, "GET", "/api/connections")
    assert status == 200
    assert data["connections"] == []
    assert not missing.exists()


@_REQUERE_DPAPI
def test_falha_de_validacao_retorna_502_sem_segredos(gateway):
    payload = {"id": "binance:crypto-spot:demo", "broker": "binance", "market": "crypto-spot", "api_key": "KEY", "api_secret": "SECRET"}

    status, _ = _request(gateway, "POST", "/api/connections", payload)
    assert status == 201

    class BrokenClient:
        def __init__(self, market: str = "spot") -> None:
            self.api_key = ""
            self.secret = ""

        def account(self):
            raise RuntimeError("binance indisponÃ­vel (stub)")

    import backend.connection_service as service

    with patch.object(service, "BinanceClient", BrokenClient):
        status, data = _request(gateway, "POST", "/api/connections/binance:crypto-spot:demo/test", {})
    assert status == 502 and data["validated"] is False
    assert "KEY" not in json.dumps(data) and "SECRET" not in json.dumps(data)
