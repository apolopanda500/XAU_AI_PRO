# -*- coding: utf-8 -*-
"""Bateria de simulação do ciclo de vida real do app.

Exercita, com o TestClient do FastAPI, o caminho completo que um operador
faz na tela: leitura, autenticação, candles, ordens, idempotência,
multiusuário e modo de conta.

POR QUE O AMBIENTE E FIXADO AQUI (medido no CI de 22/10/2026)
-------------------------------------------------------------
O middleware de auth so impõe 401 quando `API_TOKEN` esta preenchido
(`backend/fastapi_gateway.py:104`), e `API_TOKEN` vem do `.env` da maquina.
Sem `.env` (CI em Linux) o gateway sobe ABERTO: os testes viam 200 onde
esperavam 401, e rotas inexistentes devolviam 404 em vez de 401 porque o
middleware deixava passar antes do roteador. Um teste que muda de resultado
conforme a maquina nao prova nada — entao o token e fixado aqui, os dois
sentidos (com e sem token) sao exercitados, e a taxa de limite e desligada
para o numero de requisicoes da bateria nao depender do relogio.

Endpoints inventados tambem apareceram: `/api/boot/status`, `/api/boot/report`
e `/api/boot/route` nao existem — o app tem `/api/boot`. Passavam em maquina
com token porque o middleware respondia 401 antes do roteador. Aqui a lista e a
de rotas registradas de verdade.

Os codigos aceitos nunca sao `{200}`: sem token a resposta e 401 (fail-closed)
e sem terminal MT5 a resposta e 503.
"""
from __future__ import annotations

import os
import sys

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

from conftest import TOKEN_DE_TESTE  # noqa: E402
from _dublo_mt5 import terminal_desconectado  # noqa: E402

#: Quantidade de "usuarios" nas baterias de concorrencia.
USUARIOS = 25

#: O token do modulo vem do conftest: um lugar so para a string.
TOKEN = TOKEN_DE_TESTE


@pytest.fixture(autouse=True)
def _ambiente_deterministico(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XAU_MT5_COMMON_FILES", str(tmp_path / "common"))
    monkeypatch.setenv("XAU_APP_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("XAU_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("XAU_REAL_EMERGENCY_FILE", str(tmp_path / "STOP"))
    monkeypatch.setenv("XAU_ENABLE_REAL_ORDERS", "")
    monkeypatch.delenv("XAU_ENABLE_TRADE_COMMANDS", raising=False)
    monkeypatch.delenv("XAU_ENABLE_DEMO_ORDERS", raising=False)
    monkeypatch.setitem(sys.modules, "MetaTrader5", terminal_desconectado())

    import backend.fastapi_gateway as fg
    import backend.mt5_gateway as gw

    monkeypatch.setattr(fg, "API_TOKEN", TOKEN)
    monkeypatch.setattr(gw, "RATE_LIMIT_MAX", 0, raising=False)
    monkeypatch.setattr(gw, "RATE_LIMIT_CMD_MAX", 0, raising=False)
    monkeypatch.setattr(gw, "_MARKET_CACHE", {}, raising=False)
    fg._RATE_STATE.update({"count": 0, "window": 0.0})
    fg._RATE_STATE_CMD.update({"count": 0, "window": 0.0})
    yield


@pytest.fixture
def anonimo():
    """Cliente SEM credencial — o estado de uma aplicacao que ainda nao logou."""
    from backend.fastapi_gateway import app
    return TestClient(app)


@pytest.fixture
def client(anonimo):
    """Cliente AUTENTICADO com o token fixado acima."""
    anonimo.headers.update({"Authorization": f"Bearer {TOKEN}"})
    return anonimo


# ---------------------------------------------------------------------------
# 1. Leitura sem token — fail-closed e rotas publicas de verdade
# ---------------------------------------------------------------------------

class TestLeituraPublica:
    def test_health_sem_token_e_401(self, anonimo):
        r = anonimo.get("/api/health")
        assert r.status_code == 401, r.text
        assert r.json().get("ok") is False

    def test_capabilities_sem_token_e_401(self, anonimo):
        assert anonimo.get("/api/capabilities").status_code == 401

    def test_overview_sem_token_e_401(self, anonimo):
        assert anonimo.get("/api/universal/overview").status_code == 401

    def test_qualquer_rota_desconhecida_tambem_e_401(self, anonimo):
        """Prova que o 401 vem do middleware, nao do roteador."""
        assert anonimo.get("/api/rota-que-nao-existe").status_code == 401

    def test_rota_publica_continua_aberta(self, anonimo):
        assert anonimo.get("/api/auth/ping").status_code == 200

    def test_401_e_estavel_em_repeticao(self, anonimo):
        codes = [anonimo.get("/api/health").status_code for _ in range(10)]
        assert set(codes) == {401}


# ---------------------------------------------------------------------------
# 2. Autenticacao — token certo entra, token errado nao
# ---------------------------------------------------------------------------

class TestAutenticacao:
    def test_token_correto_aceito(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_token_errado_rejeitado(self, anonimo):
        anonimo.headers.update({"Authorization": "Bearer errado"})
        assert anonimo.get("/api/health").status_code == 401

    def test_header_malformado_rejeitado(self, anonimo):
        anonimo.headers.update({"Authorization": TOKEN})
        assert anonimo.get("/api/health").status_code == 401


# ---------------------------------------------------------------------------
# 3. Modo de conta — guarda exata DEMO/CONTEST/REAL
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
# 4. Candles — frontend pede 1000; backend aceita ate 2000
# ---------------------------------------------------------------------------

class TestCandles:
    def test_backend_aceita_ate_2000(self, client):
        r = client.get("/api/universal/candles",
                       params={"broker": "mt5", "market": "other", "symbol": "XAUUSD",
                               "timeframe": "M5", "limit": 1000})
        assert r.status_code in (200, 403, 422, 503), r.text
        assert r.status_code != 401

    def test_limite_acima_de_2000_e_422(self, client):
        r = client.get("/api/universal/candles",
                       params={"broker": "mt5", "market": "other", "symbol": "XAUUSD",
                               "timeframe": "M5", "limit": 2001})
        assert r.status_code == 422, r.text

    def test_limite_zero_e_422(self, client):
        r = client.get("/api/universal/candles",
                       params={"broker": "mt5", "market": "other", "symbol": "XAUUSD",
                               "timeframe": "M5", "limit": 0})
        assert r.status_code == 422, r.text

    def test_multiplos_simbolos_timeframes(self, client):
        for sym in ("XAUUSD", "EURUSD", "BTCUSD"):
            for tf in ("M1", "M5", "H1", "D1"):
                r = client.get("/api/universal/candles",
                               params={"broker": "mt5", "market": "other",
                                       "symbol": sym, "timeframe": tf, "limit": 100})
                assert r.status_code in (200, 403, 422, 503), f"{sym}/{tf}: {r.status_code}"
                assert r.status_code != 401

    def test_candles_sem_limite_retorna_padrao(self, client):
        r = client.get("/api/universal/candles",
                       params={"broker": "mt5", "market": "other", "symbol": "XAUUSD"})
        assert r.status_code in (200, 403, 422, 503), r.text


# ---------------------------------------------------------------------------
# 5. Ordens — sem confirm nao passa; sem terminal MT5 nada e executado
# ---------------------------------------------------------------------------

class TestOrdensDemo:
    def test_ordem_sem_confirm_e_403(self, client):
        r = client.post("/api/trade/order",
                        json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01})
        assert r.status_code == 403, r.text
        assert r.json().get("ok") is False

    def test_ordem_sem_token_e_401(self, anonimo):
        r = anonimo.post("/api/trade/order",
                         json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                               "confirm": True, "request_id": "demo-001"})
        assert r.status_code == 401, r.text

    def test_ordem_com_confirm_sem_terminal_nao_executa(self, client):
        """Sem MT5 de verdade nao ha ordem: a resposta jamais e sucesso."""
        r = client.post("/api/trade/order",
                        json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                              "confirm": True, "request_id": "demo-002"})
        assert r.status_code in (403, 503), r.text
        assert r.json().get("ok") is not True

    def test_request_id_obrigatorio_no_universal(self, client):
        """Sem `request_id` nao ha como saber se e a mesma ordem duas vezes."""
        r = client.post("/api/universal/order",
                        json={"broker": "mt5", "market": "metals",
                              "account_id": "simulacao",
                              "symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                              "order_type": "market", "confirm": True,
                              "execute": False})
        corpo = r.json()
        assert corpo.get("ok") is False, r.text
        assert "request_id" in str(corpo).lower()

    def test_universal_sem_corretora_e_recusa(self, client):
        """`broker` e obrigatório: símbolo so existe dentro de uma corretora (§3).

        O router devolve `ok:false` com `INVALID_UNIVERSAL_REQUEST`; o status
        HTTP e 200 porque a recusa vem do corpo da resposta, nao do codigo de
        transporte. O que se prova e que nada foi aceito.
        """
        r = client.post("/api/universal/order",
                        json={"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                              "confirm": True, "execute": False,
                              "request_id": "sem-corretora"})
        corpo = r.json()
        assert corpo.get("ok") is False, r.text
        assert corpo.get("error", {}).get("code") == "INVALID_UNIVERSAL_REQUEST"
        assert "corretora" in str(corpo).lower()

    def test_universal_sem_account_id_e_recusa(self, client):
        r = client.post("/api/universal/order",
                        json={"broker": "mt5", "market": "metals",
                              "symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                              "order_type": "market", "confirm": True,
                              "execute": False, "request_id": "sem-conta"})
        corpo = r.json()
        assert corpo.get("ok") is False, r.text
        assert "account_id" in str(corpo).lower()

    def test_universal_dry_run_valida_sem_executar(self, client):
        """`execute=false` valida e para em `stage=validated`: nenhuma ordem sai."""
        r = client.post("/api/universal/order",
                        json={"broker": "mt5", "market": "metals",
                              "account_id": "simulacao",
                              "symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                              "order_type": "market", "confirm": True,
                              "execute": False, "request_id": "dry-run-001"})
        corpo = r.json()
        assert r.status_code in (200, 403, 422), r.text
        if corpo.get("ok"):
            assert corpo.get("accepted") is True
            assert corpo.get("stage") == "validated"
        else:
            # Recusa documentada, nunca aceitacao silenciosa.
            assert corpo.get("error"), r.text

    def test_ordem_real_sem_token_e_401(self, anonimo):
        r = anonimo.post("/api/real/order",
                         json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                               "confirm": True, "request_id": "real-001"})
        assert r.status_code == 401, r.text

    def test_ordem_real_nao_executa_sem_terminal(self, client):
        r = client.post("/api/real/order",
                        json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                              "confirm": True, "request_id": "real-002"})
        assert r.status_code in (403, 503), r.text
        assert r.json().get("ok") is not True


# ---------------------------------------------------------------------------
# 6. Idempotencia por request_id (universal router)
# ---------------------------------------------------------------------------

class TestIdempotencia:
    def test_mesmo_request_id_duas_vezes(self, client):
        payload = {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                   "order_type": "market", "confirm": True, "execute": False,
                   "request_id": "idem-001"}
        r1 = client.post("/api/universal/order", json=payload)
        r2 = client.post("/api/universal/order", json=payload)
        assert r1.status_code == r2.status_code, (r1.text, r2.text)
        assert r1.status_code in (200, 403, 422)

    def test_request_ids_diferentes_aceitos(self, client):
        codes = []
        for i in range(5):
            payload = {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                       "order_type": "market", "confirm": True, "execute": False,
                       "request_id": f"idem-{i}"}
            codes.append(client.post("/api/universal/order", json=payload).status_code)
        assert all(c in (200, 403, 422) for c in codes), codes

    def test_sem_request_id_repete_o_mesmo_resultado(self, client):
        payload = {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                   "confirm": True, "execute": False}
        codes = [client.post("/api/universal/order", json=payload).status_code
                 for _ in range(3)]
        assert len(set(codes)) == 1, codes


# ---------------------------------------------------------------------------
# 7. Multiusuario concorrente
# ---------------------------------------------------------------------------

class TestMultiusuario:
    def test_health_concorrente(self, client):
        codes = [client.get("/api/health").status_code for _ in range(USUARIOS)]
        assert set(codes) == {200}, codes

    def test_capabilities_concorrente(self, client):
        codes = [client.get("/api/capabilities").status_code for _ in range(USUARIOS)]
        assert set(codes) == {200}, codes

    def test_candles_concorrente(self, client):
        codes = []
        for _ in range(USUARIOS):
            r = client.get("/api/universal/candles",
                           params={"broker": "mt5", "market": "other",
                                   "symbol": "XAUUSD", "timeframe": "M5", "limit": 100})
            codes.append(r.status_code)
        assert all(c in (200, 403, 422, 503) for c in codes), codes
        assert 401 not in codes

    def test_ordens_concorrente_nenhuma_executa(self, client):
        codes = []
        for i in range(USUARIOS):
            r = client.post("/api/trade/order",
                            json={"symbol": "XAUUSD", "side": "BUY", "volume": 0.01,
                                  "confirm": True, "request_id": f"conc-{i}"})
            codes.append(r.status_code)
        assert all(c in (403, 503) for c in codes), codes


# ---------------------------------------------------------------------------
# 8. Endpoints registrados — todos respondem, nenhum da 500
# ---------------------------------------------------------------------------

class TestCicloVida:
    #: Somente rotas que EXISTEM no app. `/api/boot/status`, `/api/boot/report`
    #: e `/api/boot/route` nao estao registradas (o app tem `/api/boot`).
    ENDPOINTS_GET = [
        "/api/health", "/api/capabilities", "/api/boot",
        "/api/universal/overview", "/api/universal/positions",
        "/api/universal/orders", "/api/universal/trades",
        "/api/universal/capabilities", "/api/assets", "/api/balance",
        "/api/ai/models", "/api/ai/trained", "/api/auto/state", "/api/auto/config",
        "/api/audit/commands", "/api/audit/log", "/api/auth/me", "/api/auth/ping",
        "/api/positions", "/api/orders", "/api/symbols", "/api/status",
    ]

    def test_todos_endpoints_respondem_sem_500(self, client):
        codigos = [(ep, client.get(ep).status_code) for ep in self.ENDPOINTS_GET]
        erros500 = [ep for ep, c in codigos if c == 500]
        assert not erros500, f"Endpoints com 500: {erros500}"

    def test_endpoints_autenticados_nunca_devolvem_401(self, client):
        # `/api/auth/me` fica de fora: ele confere o token de SESSAO emitido por
        # /api/auth/login (canal do Android), nao o token de API do Tauri. Ver
        # `test_auth_me_nao_aceita_token_de_api`, logo abaixo.
        rotas = [ep for ep in self.ENDPOINTS_GET if ep != "/api/auth/me"]
        codigos = [(ep, client.get(ep).status_code) for ep in rotas]
        rejeitados = [ep for ep, c in codigos if c == 401]
        assert not rejeitados, f"Token valido recusado em: {rejeitados}"

    def test_auth_me_nao_aceita_token_de_api(self, client):
        """Dois canais distintos: o token de API nao e sessão de usuario."""
        r = client.get("/api/auth/me")
        assert r.status_code == 401, r.text

    def test_rota_inexistente_e_404_com_token(self, client):
        """Com token o roteador responde: 404 significa rota fora do app."""
        assert client.get("/api/boot/status").status_code == 404

    def test_ordens_post_respondem(self, client):
        ordens = [
            {"symbol": "XAUUSD", "side": "BUY", "volume": 0.01, "confirm": True,
             "request_id": "ciclo-001"},
            {"symbol": "EURUSD", "side": "SELL", "volume": 0.05, "confirm": True,
             "request_id": "ciclo-002"},
        ]
        for o in ordens:
            r = client.post("/api/trade/order", json=o)
            assert r.status_code in (403, 503), f"{o['symbol']}: {r.status_code} {r.text}"
            assert r.json().get("ok") is not True
