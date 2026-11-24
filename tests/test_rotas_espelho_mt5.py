# -*- coding: utf-8 -*-
"""As duas rotas que davam 404 no painel existem nos DOIS gateways.

O QUE ACONTECEU (medido 17/11/2026 19:0x)
=========================================
Captura do dono, 18:50:

    aba Operacao -> "Grafico indisponivel: Gateway HTTP 404"
    aba Risco    -> "IA sem sugestao: HTTP 404"

Causa medida, nao presumida: o processo que escuta (pid 1616, porta 9027) e

    python -m uvicorn backend.fastapi_gateway:app

e `fastapi_gateway.py` **nao tinha** `POST /api/auto/sugerir-limites` nem
`GET /api/publico/ohlc`. As duas viviam so em `backend/mt5_gateway.py`
(`parsed.path == "/api/auto/sugerir-limites"` e `== "/api/publico/ohlc"`).

O teste antigo (`test_rotas_gateway_local.py`) olhava so a `mt5_gateway` —
logo passava verde enquanto o app instalado recebia 404. Este arquivo fecha a
outra metade.

A REGRA
=======
Toda rota espelhada tem de (1) existir no fonte da `mt5_gateway`, (2) existir
no fonte da `fastapi_gateway` (pelo router) e (3) responder pelo contrato que o
cliente ja le. Sem a (2), o build passa e a tela mostra 404 em silencio.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
MT5_GATEWAY = RAIZ / "backend" / "mt5_gateway.py"
FASTAPI_GATEWAY = RAIZ / "backend" / "fastapi_gateway.py"

from backend.rotas_espelho_mt5 import ROTAS_ESPELHADAS, router


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _servidas_pela_mt5() -> set[str]:
    texto = MT5_GATEWAY.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r'parsed\.path\s*==\s*"([^"]+)"', texto))


def test_lista_nao_esta_vazia():
    assert len(ROTAS_ESPELHADAS) >= 2


@pytest.mark.parametrize("rota", ROTAS_ESPELHADAS)
def test_rota_existe_na_mt5_gateway(rota: str):
    """Sem isto, alguem remove da `mt5_gateway` e o teste fica exigindo o nada."""
    assert rota in _servidas_pela_mt5(), (
        f"{rota} esta em ROTAS_ESPELHADAS mas nao e servida por "
        f"backend/mt5_gateway.py — a lista virou documento morto"
    )


def test_rotas_estao_no_fastapi_gateway():
    """A metade que faltava: quem escuta hoje e a FastAPI.

    Le o FONTE de `fastapi_gateway.py` e exige o `include_router` do modulo.
    Um `from ... import router` sem include tambem daria 404, por isso a
    exigencia e o `include_router`.
    """
    texto = FASTAPI_GATEWAY.read_text(encoding="utf-8", errors="replace")
    assert "rotas_espelho_mt5" in texto, (
        "backend/fastapi_gateway.py nao importa rotas_espelho_mt5 — as duas "
        "rotas continuam 404 no processo que escuta (medido: 9027)"
    )
    assert re.search(r"include_router\(\s*rotas_espelho_mt5", texto) or re.search(
        r"include_router\(\s*rotas_espelho\.router", texto
    ), "include_router do rotas_espelho_mt5 ausente em fastapi_gateway.py"


def test_sugerir_limites_nao_inventa_numero(monkeypatch):
    """Delega para `auto_engine.sugerir_limites` — a mesma funcao da mt5.

    Se este modulo passasse a devolver numeros fixos, a aba Risco mostraria
    sugestao que ninguem mediu. O duble prova que a chamada ACONTECE e que a
    resposta e a da funcao, campo por campo.
    """
    chamadas: list[tuple] = []

    def _falsa(simbolo, timeframe, broker, market):
        chamadas.append((simbolo, timeframe, broker, market))
        return {"ok": True, "simbolo": simbolo, "limites": {"confianca_minima": 77}}

    monkeypatch.setattr("backend.auto_engine.sugerir_limites", _falsa)

    cliente = TestClient(_app())
    r = cliente.post(
        "/api/auto/sugerir-limites",
        data=json.dumps(
            {"simbolo": "EURUSD", "timeframe": "H1", "broker": "mt5", "market": "forex"}
        ),
        headers={"Content-Type": "application/json"},
    )

    assert r.status_code == 200
    assert chamadas == [("EURUSD", "H1", "mt5", "forex")]
    assert r.json()["limites"]["confianca_minima"] == 77


def test_sugerir_limites_recusa_sem_simbolo(monkeypatch):
    """A recusa vem de `auto_engine`, com motivo — nao um 404 e nao um numero."""

    def _falsa(simbolo, timeframe, broker, market):
        assert simbolo == ""
        return {"ok": False, "error": "simbolo vazio: escolha o ativo na tela"}

    monkeypatch.setattr("backend.auto_engine.sugerir_limites", _falsa)
    cliente = TestClient(_app())
    r = cliente.post(
        "/api/auto/sugerir-limites",
        data=json.dumps({"timeframe": "H1"}),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert "simbolo" in r.json()["error"]


def test_corpo_invalido_recusa_com_motivo():
    cliente = TestClient(_app())
    r = cliente.post(
        "/api/auto/sugerir-limites", data="{", headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 400
    assert r.json()["error"] == "corpo JSON invalido"


def test_ohlc_publico_devolve_o_que_a_fonte_devolveu(monkeypatch):
    def _falsa(symbol, timeframe="M5", limit=300):
        return {
            "ok": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": [{"time": 1, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}],
            "fonte": "duble",
        }

    monkeypatch.setattr("backend.mercado_publico.ohlc_publico", _falsa)
    cliente = TestClient(_app())
    r = cliente.get("/api/publico/ohlc?symbol=EURUSD&timeframe=M15&limit=2")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["symbol"] == "EURUSD" and len(corpo["candles"]) == 1


def test_ohlc_publico_separa_400_de_503(monkeypatch):
    """PROVA NEGATIVA: pedido invalido e fonte fora do ar nao podem virar o
    mesmo status — a tela decide coisas opostas com esses dois casos."""

    def _invalido(symbol, timeframe="M5", limit=300):
        raise ValueError("periodo invalido: XX")

    def _fora(symbol, timeframe="M5", limit=300):
        raise RuntimeError("fonte fora do ar")

    cliente = TestClient(_app())

    monkeypatch.setattr("backend.mercado_publico.ohlc_publico", _invalido)
    ruim = cliente.get("/api/publico/ohlc?symbol=EURUSD")
    assert ruim.status_code == 400
    assert "periodo invalido" in ruim.json()["error"]

    monkeypatch.setattr("backend.mercado_publico.ohlc_publico", _fora)
    caido = cliente.get("/api/publico/ohlc?symbol=EURUSD")
    assert caido.status_code == 503
    assert caido.json()["fonte"] is None
