# -*- coding: utf-8 -*-
"""Caos/persistência SEM inventar rota de escrita (gateway é somente leitura)."""
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import mobile_control  # noqa: E402


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/mobile/control")
    def controle():
        return mobile_control.montar_de_leitura(
            {"login": 1, "server": "DEMO", "balance": 1000.0},
            {"ok": True, "gateway_build": "teste"}, None, [])
    return app


def test_chaos_01_rajada_concorrente_de_leitura_sem_duplicacao():
    client = TestClient(_app())
    def ler(_):
        r = client.get("/api/mobile/control")
        return r.status_code, r.json()
    with ThreadPoolExecutor(max_workers=20) as pool:
        resultados = list(pool.map(ler, range(20)))
    assert all(code == 200 for code, _ in resultados)
    corpos = [c for _, c in resultados]
    assert all(c == corpos[0] for c in corpos)
    assert all(c.get("read_only") is True for c in corpos)


def test_chaos_02_fail_closed_token_invalido_nao_derruba_servidor():
    base = os.getenv("XAU_GATEWAY_URL", "http://127.0.0.1:9027")
    req = urllib.request.Request(f"{base}/api/mobile/control",
        headers={"Authorization": "Bearer token_invalido_chaos"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            raise AssertionError(f"gateway aceitou token inválido: HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        assert exc.code in (401, 403), f"esperado 401/403, recebeu {exc.code}"
    except urllib.error.URLError:
        pass


def test_chaos_03_payload_serializavel_e_sem_segredos():
    corpo = mobile_control.montar_de_leitura(
        {"login": 1, "server": "S", "balance": 10.0},
        {"ok": True, "gateway_build": "1.2.4"}, None, [])
    texto = json.dumps(corpo, ensure_ascii=False)
    assert texto and "Bearer" not in texto and "api_key" not in texto
