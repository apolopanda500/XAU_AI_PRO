"""Trava das rotas universal e do motivo de recusa.

Duas regressoes medidas em 20/10/2026, ambas apontadas pelo CodeQL:

1. `backend/fastapi_gateway.py` tinha TRES rotas universal definidas duas vezes.
   A primeira definicao vencia no roteamento; a segunda ficava morta, usava
   nomes que nao existem (`connection_store`) e ainda respondia por um
   `except Exception: pass`. Rota morta nao e inofensiva: ela e a que um dia
   alguem "conserta" sem perceber que nao esta no ar.
2. `MotorAuto.ligar()` devolvia `{exc}` no motivo. O texto da excecao e dado
   interno e o CodeQL classifica como `py/stack-trace-exposure`.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend import broker_registry
from backend import fastapi_gateway as fgw
from backend.auto_engine import LimitesAuto, MotorAuto

TOKEN = "token-de-teste"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _motor(broker: str = "mexc", market: str = "forex") -> MotorAuto:
    m = MotorAuto()
    m.simbolo = "XAUUSD"
    m.timeframe = "M5"
    m.broker = broker
    m.market = market
    m.limites = LimitesAuto(
        banca=20.0, risco_por_trade_pct=1.0, confianca_minima=55.0,
        edge_minimo=0.05, max_posicoes=2, max_operacoes_dia=20,
        perda_diaria_max_pct=2.0, sl_atr=1.5, tp_atr=3.0,
        intervalo_minutos=15,
    )
    return m


def test_ligar_nao_ecoa_o_texto_da_excecao(monkeypatch):
    """O motivo nomeia o par e os mercados aceitos, nunca a excecao crua."""
    def explodir(broker, market, symbol=""):
        raise ValueError("SEGREDO-INTERNO-123: caminho /home/operador/.env")

    monkeypatch.setattr(broker_registry, "normalize_read_scope", explodir)
    r = _motor().ligar()

    assert r["ok"] is False
    assert "SEGREDO-INTERNO-123" not in json.dumps(r)
    assert "/home/operador" not in json.dumps(r)
    # O motivo continua util: nomeia o par e o que a corretora aceita.
    assert "mexc" in r["error"]
    assert "crypto-spot" in r["error"]


def test_motivo_de_corretora_desconhecida_nao_ecoa_a_excecao(monkeypatch):
    def explodir(broker, market, symbol=""):
        raise ValueError("TOKEN=nao-pode-vazar")

    monkeypatch.setattr(broker_registry, "normalize_read_scope", explodir)
    r = _motor(broker="corretora-inexistente", market="forex").ligar()

    assert r["ok"] is False
    assert "TOKEN=" not in json.dumps(r)
    assert "corretora-inexistente" in r["error"]


def test_gateway_nao_registra_a_mesma_rota_duas_vezes():
    rotas: dict[tuple[str, tuple[str, ...]], list[int]] = {}
    for rota in fgw.app.routes:
        caminho = getattr(rota, "path", "")
        if not caminho.startswith("/api/"):
            continue
        metodos = tuple(sorted(getattr(rota, "methods", ()) or ()))
        rotas.setdefault((caminho, metodos), []).append(
            rota.endpoint.__code__.co_firstlineno
        )

    repetidas = {chave: linhas for chave, linhas in rotas.items() if len(linhas) > 1}
    assert not repetidas, f"rota registrada mais de uma vez: {repetidas}"


def test_overview_universal_responde_pelo_caminho_real(monkeypatch):
    """A rota viva e a que delega ao `mt5_gateway`, nao a copia morta."""
    monkeypatch.setattr(fgw, "API_TOKEN", TOKEN)
    monkeypatch.setattr(
        fgw.gw,
        "_universal_overview",
        lambda: {"conexoes": [], "moedas": [], "simbolos": [], "mt5_required": False},
    )

    resposta = TestClient(fgw.app).get("/api/universal/overview", headers=AUTH)

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["mt5_required"] is False
    assert {"conexoes", "moedas", "simbolos"} <= set(resposta.json())


def test_conta_universal_exige_par_corretora_mercado(monkeypatch):
    """Sem `broker` e `market` a rota recusa na validacao, nao com 500."""
    monkeypatch.setattr(fgw, "API_TOKEN", TOKEN)
    cliente = TestClient(fgw.app)

    resposta = cliente.get("/api/universal/account", headers=AUTH)

    assert resposta.status_code == 422
    assert "broker" in resposta.text
