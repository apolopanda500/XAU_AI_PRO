"""Autenticacao por usuario no gateway: rotas /api/auth/* e o middleware.

Estes testes exercitam o middleware de verdade (via TestClient), porque o que
importa aqui nao e so o handler: e que /api/auth/login e alcancavel sem token,
que as demais rotas continuam protegidas e que um token de sessao substitui o
API_TOKEN estatico no app Android.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import fastapi_gateway as gw
from backend import remote_auth

SENHA = "senha-de-teste-bem-longa"


@pytest.fixture(autouse=True)
def _ambiente(tmp_path, monkeypatch):
    """API_TOKEN ativo e banco de auth isolado, como em producao mobile."""
    monkeypatch.setattr(remote_auth, "DB_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(remote_auth, "SESSION_TTL", 3600)
    monkeypatch.setattr(gw, "API_TOKEN", "token-estatico-do-desktop")
    monkeypatch.setattr(gw.gw, "API_TOKEN", "token-estatico-do-desktop")
    monkeypatch.setattr(gw.gw, "RATE_LIMIT_MAX", 0)
    monkeypatch.setattr(gw.gw, "RATE_LIMIT_CMD_MAX", 0)
    monkeypatch.setattr(gw, "ALLOW_SELF_REGISTER", False)
    gw._SESSION_CACHE.clear()
    yield
    gw._SESSION_CACHE.clear()


@pytest.fixture()
def client():
    return TestClient(gw.app)


def _login(client: TestClient, email: str = "trader@exemplo.com", password: str = SENHA) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


# --------------------------------------------------------------------------
# as rotas de auth nao exigem token previo
# --------------------------------------------------------------------------

def test_login_e_alcancavel_sem_token(client):
    remote_auth.register("trader@exemplo.com", SENHA)
    r = client.post("/api/auth/login", json={"email": "trader@exemplo.com", "password": SENHA})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["token"]
    assert body["expires_in"] == 3600


def test_register_e_alcancavel_sem_token_mas_responde_403_por_padrao(client):
    r = client.post("/api/auth/register", json={"email": "novo@exemplo.com", "password": SENHA})
    assert r.status_code == 403
    assert "desativado" in r.json()["error"]


def test_ping_nao_exige_token_e_nao_vaza_nada(client):
    r = client.get("/api/auth/ping")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["self_register"] is False
    assert "token" not in body


def test_registro_ligado_por_variavel_de_ambiente(client, monkeypatch):
    monkeypatch.setattr(gw, "ALLOW_SELF_REGISTER", True)
    r = client.post("/api/auth/register", json={"email": "novo@exemplo.com", "password": SENHA})
    assert r.status_code == 200
    assert r.json()["user_id"] > 0
    # e o usuario registrado ja consegue fazer login
    assert _login(client, "novo@exemplo.com")


# --------------------------------------------------------------------------
# falha de login
# --------------------------------------------------------------------------

def test_login_com_senha_errada_responde_401(client):
    remote_auth.register("trader@exemplo.com", SENHA)
    r = client.post("/api/auth/login", json={"email": "trader@exemplo.com", "password": "errada-longa-aqui"})
    assert r.status_code == 401
    assert "token" not in r.json()


def test_login_nao_distingue_usuario_inexistente_de_senha_errada(client):
    remote_auth.register("trader@exemplo.com", SENHA)
    inexistente = client.post("/api/auth/login", json={"email": "ninguem@exemplo.com", "password": SENHA})
    senha_errada = client.post("/api/auth/login", json={"email": "trader@exemplo.com", "password": "errada-longa-aqui"})
    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json()["error"] == senha_errada.json()["error"]


# --------------------------------------------------------------------------
# o token de sessao substitui o API_TOKEN estatico (fluxo do Android)
# --------------------------------------------------------------------------

def test_token_de_sessao_abre_rota_protegida(client):
    remote_auth.register("trader@exemplo.com", SENHA)
    token = _login(client)
    r = client.get("/api/health", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_rota_protegida_sem_nenhum_token_responde_401(client):
    r = client.get("/api/health")
    assert r.status_code == 401


def test_rota_protegida_com_token_inventado_responde_401(client):
    r = client.get("/api/health", headers={"Authorization": "Bearer token-falsificado"})
    assert r.status_code == 401


def test_token_estatico_do_desktop_continua_valendo(client):
    r = client.get("/api/health", headers={"Authorization": "Bearer token-estatico-do-desktop"})
    assert r.status_code == 200


def test_header_sem_prefixo_bearer_e_recusado(client):
    remote_auth.register("trader@exemplo.com", SENHA)
    token = _login(client)
    r = client.get("/api/health", headers={"Authorization": token})
    assert r.status_code == 401


def test_me_confere_o_token(client):
    remote_auth.register("trader@exemplo.com", SENHA)
    token = _login(client)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["user_id"] > 0


def test_me_sem_token_responde_401(client):
    assert client.get("/api/auth/me").status_code == 401


# --------------------------------------------------------------------------
# logout
# --------------------------------------------------------------------------

def test_logout_invalida_o_token_no_gateway(client):
    remote_auth.register("trader@exemplo.com", SENHA)
    token = _login(client)
    r = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # imediatamente apos o logout a rota protegida tem de recusar
    assert client.get("/api/health", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_derruba_o_cache_do_token(client):
    """O cache de 30s nao pode ressuscitar um token apos o logout."""
    remote_auth.register("trader@exemplo.com", SENHA)
    token = _login(client)
    client.get("/api/health", headers={"Authorization": f"Bearer {token}"})  # popula o cache
    assert token in gw._SESSION_CACHE
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert token not in gw._SESSION_CACHE
    assert client.get("/api/health", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_sem_token_responde_401(client):
    assert client.post("/api/auth/logout").status_code == 401


# --------------------------------------------------------------------------
# sessao expirada
# --------------------------------------------------------------------------

def test_token_expirado_nao_abre_rota_protegida(client, monkeypatch):
    remote_auth.register("trader@exemplo.com", SENHA)
    token = _login(client)
    # rebaixa o TTL para 0 e recria a sessao ja expirada
    import sqlite3
    import time as _time
    with sqlite3.connect(remote_auth.DB_PATH) as db:
        db.execute("UPDATE sessions SET expires_at = ?", (int(_time.time()) - 1,))
    assert client.get("/api/health", headers={"Authorization": f"Bearer {token}"}).status_code == 401
