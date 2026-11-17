# -*- coding: utf-8 -*-
"""Rota `/api/auto/sugerir-limites` no gateway FastAPI.

POR QUE EXISTE
==============
A aba de Risco da Trading Desk chamava `/api/auto/sugerir-limites`, que só
existia no gateway legado (`backend/mt5_gateway.py`, servidor HTTP clássico) e
não no FastAPI (`backend/fastapi_gateway.py`). Enquanto isso:

    "IA sem sugestão: HTTP 404"

A correção é a mesma função que o servidor legado já usava
(`auto_engine.sugerir_limites`), exposta pela rota nova. Os testes aqui provam
o contrato que a tela consome e que a nova rota é de leitura (não grava, não
liga motor, não executa ordem).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import fastapi_gateway as gw
from backend import remote_auth

TOKEN = "token-estatico-do-desktop"
SENHA = "senha-de-teste-bem-longa"


@pytest.fixture(autouse=True)
def _ambiente(tmp_path, monkeypatch):
    """API_TOKEN ativo e banco de auth isolado, como em produção."""
    monkeypatch.setattr(remote_auth, "DB_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(remote_auth, "SESSION_TTL", 3600)
    monkeypatch.setattr(gw, "API_TOKEN", TOKEN)
    monkeypatch.setattr(gw.gw, "API_TOKEN", TOKEN)
    monkeypatch.setattr(gw.gw, "RATE_LIMIT_MAX", 0)
    monkeypatch.setattr(gw.gw, "RATE_LIMIT_CMD_MAX", 0)
    monkeypatch.setattr(gw, "ALLOW_SELF_REGISTER", False)
    gw._SESSION_CACHE.clear()
    yield
    gw._SESSION_CACHE.clear()


@pytest.fixture()
def client():
    return TestClient(gw.app)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_sugerir_limites_exige_token(client):
    r = client.post("/api/auto/sugerir-limites", json={"simbolo": "EURUSD"})
    assert r.status_code == 401


def test_sugerir_limites_responde_200_com_o_contrato_do_legado(client, monkeypatch):
    parcial = {
        "ok": True,
        "limites": {"min_edge": 4.2, "min_confianca": 58.0},
        "base": {"acerteza": "medida"},
        "serie": {"velas": 300, "atr_pct": 0.41, "edge": 0.052, "confianca": 61.2},
    }
    chamadas = {}

    def _fake(simbolo, timeframe, broker, market):
        chamadas.update(simbolo=simbolo, timeframe=timeframe, broker=broker, market=market)
        return parcial

    monkeypatch.setattr(gw.auto_engine, "sugerir_limites", _fake)

    r = client.post(
        "/api/auto/sugerir-limites",
        json={"simbolo": "EURUSD", "timeframe": "H1", "broker": "mt5", "market": "forex"},
        headers=_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["limites"]["min_edge"] == 4.2
    assert body["serie"]["velas"] == 300
    assert chamadas == {"simbolo": "EURUSD", "timeframe": "H1", "broker": "mt5", "market": "forex"}


def test_sugerir_limites_recusa_corpo_invalido(client):
    r = client.post(
        "/api/auto/sugerir-limites",
        content=b"isto-nao-e-json",
        headers={**_headers(), "Content-Type": "application/json"},
    )
    assert r.status_code == 400
    assert r.json()["ok"] is False


def test_sugerir_limites_sem_corpo_devolve_400(client):
    r = client.post("/api/auto/sugerir-limites", headers=_headers())
    assert r.status_code == 400
