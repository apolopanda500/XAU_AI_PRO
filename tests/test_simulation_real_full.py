# -*- coding: utf-8 -*-
"""Bateria de simulação real — muitos usuários usando TUDO o que o app expõe.

Ambiente FIXADO aqui (ver cabecalho de `test_simulacao_ciclo_vida_real.py`):
`API_TOKEN` vem do `.env` da maquina e o middleware so impoe 401 com ele
preenchido. Sem token no ambiente (CI Linux) o gateway sobe aberto e o teste
via 200 onde esperava 401, e rota inexistente devolvia 404 em vez de 401
porque o middleware deixava passar antes do roteador.

A lista de rotas NAO e escrita a mao: ela vem do proprio FastAPI app.
Escrita a mao, ela envelhece junto com o codigo e volta a medir uma rota que
nao existe — medido no CI de 22/10/2026: `/api/balance`, `/api/audit/log` e
`/api/universal/orders` estavam no arquivo e nao existem no gateway
(`/api/account/balance`, `/api/audit` e `/api/positions` existem), e
`/api/auto/config` so aceita POST (405 em GET).

O dublô de MetaTrader5 precisa devolver `None` (terminal sem sessao), senao
`backend/asset_registry.py:177` levanta `AttributeError` e o handler devolve
500 — medido: `/api/assets` e `/api/symbols` derrubavam a bateria.
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

USERS = 20
TOKEN = TOKEN_DE_TESTE

#: Caminhos que o middleware nao protege de proposito (registro/login/ping).
PUBLICOS = {"/api/auth/ping"}

#: Documentacao isenta DE PROPOSITO, escrito no proprio middleware
#: (`fastapi_gateway._auth_rate_limit`: "Rotas de documentacao ficam isentas").
#: Entram na lista so para o teste nao acusar uma decisao documentada.
DOCUMENTACAO_ISENTA = ("/api/docs", "/api/redoc", "/api/openapi.json", "/docs")

#: `/api/auth/me` confere o token de SESSAO (canal do Android), nao o token de
#: API do Tauri — com token de API ele da 401 de proposito.
CANAL_DE_SESSAO = "/api/auth/me"


def _rotas_get():
    """Rotas GET reais registradas no app, sem as que exigem parametro de caminho."""
    from backend.fastapi_gateway import app

    rotas = []
    for rota in app.routes:
        metodos = getattr(rota, "methods", None) or set()
        caminho = getattr(rota, "path", "")
        if "GET" not in metodos or "{" in caminho:
            continue
        if caminho in PUBLICOS or caminho.startswith(DOCUMENTACAO_ISENTA):
            continue
        rotas.append(caminho)
    return sorted(rotas)


#: Medido da aplicacao, nao escrito de memoria.
ENDPOINTS_GET = _rotas_get()

#: Leituras que tem de responder para um cliente autenticado.
LEITURAS_PARAMETRIZADAS = [
    "/api/assets", "/api/account/balance", "/api/ai/models", "/api/ai/trained",
    "/api/auto/state", "/api/audit/commands", "/api/audit",
    "/api/trade/positions", "/api/risk/state", "/api/watchdog",
]

#: Leituras universais (o contrato cross-broker do §3).
LEITURAS_UNIVERSAIS = [
    "/api/universal/overview", "/api/universal/positions",
    "/api/universal/trades", "/api/universal/capabilities",
]


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


class TestFullSimulation:
    """Simula muitos usuarios usando todas as funcionalidades."""

    def test_health(self, client):
        assert client.get("/api/health").status_code == 200

    def test_capabilities(self, client):
        assert client.get("/api/capabilities").status_code == 200

    def test_boot(self, client):
        r = client.get("/api/boot")
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_boot_antigos_foram_removidos(self, client):
        """As rotas inventadas nao existem: 404 com token, nunca 200."""
        for ep in ("/api/boot/status", "/api/boot/report", "/api/boot/route"):
            assert client.get(ep).status_code == 404, ep

    @pytest.mark.parametrize("ep", LEITURAS_UNIVERSAIS)
    def test_universal_reads(self, client, ep):
        r = client.get(ep, params={"broker": "mt5", "market": "metals"})
        assert r.status_code in (200, 403, 422, 503), f"{ep}: {r.status_code} {r.text}"
        assert r.status_code != 401

    @pytest.mark.parametrize("ep", LEITURAS_PARAMETRIZADAS)
    def test_leituras_respondem(self, client, ep):
        r = client.get(ep)
        assert r.status_code in (200, 403, 422, 503), f"{ep}: {r.status_code} {r.text}"
        assert r.status_code != 401

    def test_posicoes_e_status(self, client):
        for ep in ("/api/positions", "/api/orders", "/api/symbols", "/api/status"):
            r = client.get(ep)
            assert r.status_code in (200, 403, 422, 503), f"{ep}: {r.status_code}"
            assert r.status_code not in (401, 500), f"{ep}: {r.status_code} {r.text}"

    def test_multi_users_health(self, client):
        codes = [client.get("/api/health").status_code for _ in range(USERS)]
        assert set(codes) == {200}, codes

    def test_multi_users_capabilities(self, client):
        codes = [client.get("/api/capabilities").status_code for _ in range(USERS)]
        assert set(codes) == {200}, codes

    def test_multi_users_universal(self, client):
        codes = [client.get("/api/universal/overview",
                            params={"broker": "mt5", "market": "metals"}).status_code
                 for _ in range(USERS)]
        assert set(codes) <= {200, 403, 422, 503}, codes

    def test_a_lista_de_rotas_medida_nao_e_vazia(self):
        """Prova negativa: se o enumerador falhar, ele devolve [] e o resto passa em vazio."""
        assert len(ENDPOINTS_GET) >= 20, ENDPOINTS_GET
        assert "/api/health" in ENDPOINTS_GET

    def test_sem_token_tudo_fecha(self, anonimo):
        """Fail-closed em TODAS as rotas nao publicas registradas no app."""
        assert len(ENDPOINTS_GET) >= 20, ENDPOINTS_GET
        codigos = [(ep, anonimo.get(ep).status_code) for ep in ENDPOINTS_GET]
        abertos = [pair for pair in codigos if pair[1] != 401]
        assert not abertos, abertos

    def test_com_token_nenhuma_rota_devolve_500_ou_401(self, client):
        rotas = [ep for ep in ENDPOINTS_GET if ep != CANAL_DE_SESSAO]
        codigos = [(ep, client.get(ep).status_code) for ep in rotas]
        quebrados = [pair for pair in codigos if pair[1] in (401, 500)]
        assert not quebrados, quebrados

    def test_canal_de_sessao_nao_aceita_token_de_api(self, client):
        """Dois canais: o token do Tauri nao e sessao de usuario logado."""
        assert CANAL_DE_SESSAO in ENDPOINTS_GET, "rota /api/auth/me nao registrada"
        assert client.get(CANAL_DE_SESSAO).status_code == 401
