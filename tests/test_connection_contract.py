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
def test_trocar_credencial_nao_exige_excluir_e_recriar(gateway):
    """Trocar a chave reescreve o MESMO id. Nao existe PUT sem isso.

    O caminho que existia antes — excluir e cadastrar de novo com o mesmo
    nome — deixa a conta sem credencial no meio, e sem volta se o cadastro
    novo falhar. Aqui o `id` e o mesmo e a credencial e sobrescrita no lugar.
    """
    payload = {
        "id": "mexc:crypto-spot:demo",
        "broker": "mexc",
        "market": "crypto-spot",
        "api_key": "CHAVE_ANTIGA",
        "api_secret": "SECRET_ANTIGO",
    }
    status, data = _request(gateway, "POST", "/api/connections", payload)
    assert status == 201, data

    status, data = _request(
        gateway, "PUT", "/api/connections/mexc%3Acrypto-spot%3Ademo",
        {"api_key": "CHAVE_NOVA", "api_secret": "SECRET_NOVO"},
    )
    assert status == 200, data
    assert data["ok"] is True
    assert data["updated"] is True
    assert data["connection"]["id"] == payload["id"]
    # A listagem nunca devolve credencial — nem na edicao. O que se checa e o
    # VALOR vazando, nao o nome do campo: `credential_source: "api_key"` contem
    # a substring "api_key" e é informação legítima da tela.
    assert "api_key" not in data["connection"]
    assert "api_secret" not in data["connection"]
    vazamento = json.dumps(data)
    assert "CHAVE_NOVA" not in vazamento
    assert "SECRET_NOVO" not in vazamento

    from backend.connection_store import load_connection_credentials_full

    key, secret, _ = load_connection_credentials_full("mexc:crypto-spot:demo")
    assert key == "CHAVE_NOVA"
    assert secret == "SECRET_NOVO"


@_REQUERE_DPAPI
def test_campo_em_branco_na_update_mantem_a_credencial(gateway):
    """Rotacionar so a chave nao pode apagar o secret.

    Este e o contrato que permite trocar a chave SEM ler a atual de volta: o
    que falta no payload vem do DPAPI. Um PUT so com `api_key` trocaria a
    chave e gravaria `api_secret: ""` — apagando a credencial valida.
    """
    payload = {
        "id": "mexc:crypto-spot:rotacao",
        "broker": "mexc",
        "market": "crypto-spot",
        "api_key": "KEY_1",
        "api_secret": "SECRET_1",
    }
    assert _request(gateway, "POST", "/api/connections", payload)[0] == 201

    status, data = _request(
        gateway, "PUT", "/api/connections/mexc%3Acrypto-spot%3Arotacao",
        {"api_key": "KEY_2"},
    )
    assert status == 200, data

    from backend.connection_store import load_connection_credentials_full

    key, secret, _ = load_connection_credentials_full("mexc:crypto-spot:rotacao")
    assert key == "KEY_2", "a chave nova tem de estar gravada"
    assert secret == "SECRET_1", "o secret em branco nao pode apagar o gravado"


@_REQUERE_DPAPI
def test_update_sem_nada_a_gravar_e_recusado(gateway):
    """Um PUT sem credencial nova nao pode responder 200.

    Responder "atualizado" sem ter atualizado nada faz o operador acreditar
    que a chave mudou quando ela continua a antiga.
    """
    payload = {
        "id": "mexc:crypto-spot:vazia",
        "broker": "mexc",
        "market": "crypto-spot",
        "api_key": "KEY",
        "api_secret": "SECRET",
    }
    assert _request(gateway, "POST", "/api/connections", payload)[0] == 201

    status, data = _request(
        gateway, "PUT", "/api/connections/mexc%3Acrypto-spot%3Avazia", {},
    )
    assert status == 422, data
    assert data["ok"] is False

    from backend.connection_store import load_connection_credentials_full

    key, secret, _ = load_connection_credentials_full("mexc:crypto-spot:vazia")
    assert (key, secret) == ("KEY", "SECRET"), "recusa nao pode ter apagado nada"


@_REQUERE_DPAPI
def test_update_da_mesma_conexao_da_broker_e_mercado(gateway):
    """O `id` do path manda: um corpo divergente nao cria conexao paralela.

    Sem isto, um `id` digitado errado na tela criaria uma conexao nova e a
    antiga continuaria ativa com a chave velha — o operador acharia que
    trocou a chave e estaria usando a antiga.
    """
    payload = {
        "id": "mexc:crypto-spot:alvo",
        "broker": "mexc",
        "market": "crypto-spot",
        "api_key": "KEY",
        "api_secret": "SECRET",
    }
    assert _request(gateway, "POST", "/api/connections", payload)[0] == 201

    status, data = _request(
        gateway, "PUT", "/api/connections/mexc%3Acrypto-spot%3Aalvo",
        {"id": "mexc:crypto-spot:OUTRO", "api_key": "KEY_NOVA", "api_secret": "SECRET_NOVO"},
    )
    assert status == 200, data
    assert data["connection"]["id"] == "mexc:crypto-spot:alvo", "o path manda sobre o corpo"

    conexoes = _request(gateway, "GET", "/api/connections")[1]["connections"]
    ids = {c["id"] for c in conexoes}
    assert "mexc:crypto-spot:alvo" in ids
    assert "mexc:crypto-spot:OUTRO" not in ids, "o corpo nao pode criar conexao nova"


@_REQUERE_DPAPI
def test_update_em_conexao_inexistente_recusa(gateway):
    """PUT em conexao que nao existe tem de recusar, nao criar.

    O id vem do path. Se o body trouxesse um id completo, o PUT viraria um
    POST disfarçado e criaria a conexao que o operador pediu para editar.
    """
    status, data = _request(
        gateway, "PUT", "/api/connections/mexc%3Acrypto-spot%3Anaofala",
        {"broker": "mexc", "market": "crypto-spot", "api_key": "K", "api_secret": "S"},
    )
    assert status == 404, data
    assert data["ok"] is False

    conexoes = _request(gateway, "GET", "/api/connections")[1]["connections"]
    assert all(c["id"] != "mexc:crypto-spot:naofala" for c in conexoes)


@_REQUERE_DPAPI
def test_update_de_conexao_por_sessao_nao_grava_segredo(gateway):
    """MT5 usa sessao do terminal. Gravar segredo vazio seria mentira no DPAPI."""
    assert _request(
        gateway, "POST", "/api/connections",
        {"id": "mt5:forex:terminal", "broker": "mt5", "market": "forex"},
    )[0] == 201

    # Corretora de sessao nao tem credencial para trocar. Mesmo assim o PUT
    # responde 200: grava-se o registro sem segredo, que e o unico resultado
    # honesto. Gravar `api_key: "TENTATIVA"` seria o oposto.
    status, data = _request(
        gateway, "PUT", "/api/connections/mt5%3Aforex%3Aterminal",
        {"api_key": "TENTATIVA", "api_secret": "TENTATIVA"},
    )
    assert status == 200, data
    assert data["credential_source"] == "session"

    conexoes = _request(gateway, "GET", "/api/connections")[1]["connections"]
    linha = next(c for c in conexoes if c["id"] == "mt5:forex:terminal")
    assert linha["market"] == "forex", "corretora de sessao nao muda de mercado no PUT"
    assert linha["configured"] is False
    assert "api_key" not in linha

    from backend.connection_store import load_connection_credentials_full

    assert load_connection_credentials_full("mt5:forex:terminal") == ("", "", "")


@_REQUERE_DPAPI
def test_update_nao_muda_o_mercado_da_conexao(gateway):
    """Trocar chave nao pode trocar o mercado junto.

    A conexao e identificada por `broker:market:nome`. Mudar o mercado no PUT
    apontaria o mesmo id para um registro que nunca foi cadastrado nesse
    mercado — e o `resolve_connection` casaria por broker+mercado e deixaria
    de achar a conta.
    """
    assert _request(
        gateway, "POST", "/api/connections",
        {"id": "mexc:crypto-spot:fixa", "broker": "mexc", "market": "crypto-spot",
         "api_key": "K", "api_secret": "S"},
    )[0] == 201

    status, data = _request(
        gateway, "PUT", "/api/connections/mexc%3Acrypto-spot%3Afixa",
        {"market": "crypto-futures", "api_key": "K2", "api_secret": "S2"},
    )
    assert status == 422, data
    assert data["ok"] is False

    from backend.connection_store import load_connection_credentials_full

    # Recusa nao pode ter gravado nada.
    assert load_connection_credentials_full("mexc:crypto-spot:fixa") == ("K", "S", "")


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
