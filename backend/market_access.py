# -*- coding: utf-8 -*-
"""Acesso de leitura e envio por (corretora, mercado, ativo) — sem caminho fixo.

POR QUE ESTE MODULO EXISTE
==========================
O motor automatico aceitava `broker` e `market`, validava os dois contra o
catalogo, mostrava os dois na tela — e ignorava os dois no `_loop`, que
importava `mt5_gateway` direto. O operador escolhia Binance, a tela confirmava
Binance, e a ordem ia para o MetaTrader.

Este modulo e o ponto unico onde o motor resolve "qual caminho usar para este
par". Ele NAO decide nada: apenas traduz (broker, market) em chamada concreta
e devolve o motivo da falha quando nao ha caminho.

SEM ATIVO E SEM CORRETORA FIXOS
===============================
Nada aqui tem default. `acesso(broker, market)` sem informacao recusa, e
`candles` sem simbolo recusa. A regra do dono: nenhum simbolo pode ser
presumido, nenhuma corretora pode ser caminho exclusivo.

O QUE ESTE MODULO NAO FAZ
==========================
Nao envia ordem, nao calcula risco, nao decide sinal. O `UniversalRouter`
continua sendo o unico caminho de ENVIO, com `intent_log` e gate por corretora.
Aqui e so leitura, e so traducao de argumentos.
"""
from __future__ import annotations

from typing import Any

from backend.broker_registry import get_broker


class SemCaminhoError(RuntimeError):
    """Nao existe caminho de leitura para este par (corretora, mercado).

    Levanta em vez de devolver vazio: uma lista de candles vazia e
    indistinguivel de "mercado fechado", e o motor trataria as duas como
    "sem dado" sem dizer qual das duas foi.
    """


def acesso(broker: str, market: str) -> dict[str, Any]:
    """Valida o par e devolve o escopo normalizado. Recusa com motivo.

    Reusa `normalize_read_scope` do `broker_registry`, que ja normaliza mercado
    e valida a combinacao. Duplicar essa normalizacao aqui criaria um segundo
    lugar onde "forex" e "metals" significam coisas diferentes.
    """
    from backend.broker_registry import normalize_read_scope

    broker_norm = str(broker or "").strip().lower()
    if not broker_norm:
        raise SemCaminhoError("escolha a corretora antes de operar: nenhuma e padrao")
    scope = normalize_read_scope(broker_norm, market)
    definicao = get_broker(scope["broker"])
    if definicao is None:
        raise SemCaminhoError(f"corretora desconhecida: {scope['broker']}")
    if not definicao.public_data:
        raise SemCaminhoError(f"{definicao.label} nao oferece leitura publica")
    return {"broker": scope["broker"], "market": scope["market"], "label": definicao.label}


def candles(broker: str, market: str, symbol: str, timeframe: str, limit: int = 600) -> list[dict[str, Any]]:
    """Candles da corretora escolhida, ja no formato do treino.

    Para MT5, a funcao abaixo delega ao mesmo `_mt5_candles` de sempre: o
    terminal tem o seu proprio serie, e nao ha motivo para tratar MT5
    diferente de qualquer outra corretora **na leitura**.
    """
    escopo = acesso(broker, market)
    simbolo = str(symbol or "").strip().upper()
    if not simbolo:
        raise SemCaminhoError("escolha o ativo: simbolo vazio nao tem serie")
    from backend.mt5_gateway import _universal_candles

    resposta = _universal_candles(escopo["broker"], escopo["market"], simbolo, timeframe, limit)
    linhas = resposta.get("candles") if isinstance(resposta, dict) else None
    if not linhas:
        motivo = ""
        if isinstance(resposta, dict):
            motivo = str(resposta.get("error") or resposta.get("reason") or "")
        raise SemCaminhoError(
            f"{escopo['label']} nao devolveu candles para {simbolo} {timeframe}"
            + (f" ({motivo})" if motivo else "")
        )
    from backend.mt5_gateway import candles_mt5_para_dataframe

    return candles_mt5_para_dataframe(linhas)


def estado_de_risco(broker: str, market: str) -> dict[str, Any]:
    """Metricas de risco do DIA, da corretora escolhida.

    O `ciclo_unico` exige as chaves `ok`, `open_positions` e `daily_trades`.
    Qualquer ausencia vira `ok: False` com motivo — nunca um dicionario
    parcialmente preenchido, porque o motor leria `0` como "zero posicoes" e
    abriria a primeira ordem do dia believing estar em conta vazia.
    """
    escopo = acesso(broker, market)
    broker_norm, market_norm = escopo["broker"], escopo["market"]

    if broker_norm == "mt5":
        from backend.mt5_gateway import _mt5, _risk_state

        return _risk_state(_mt5())

    from backend.mt5_gateway import _universal_account, _universal_positions

    try:
        conta = _universal_account(broker_norm, market_norm)
        posicoes = _universal_positions(broker_norm, market_norm)
    except Exception as exc:
        return {"ok": False, "error": f"{escopo['label']} nao respondeu: {exc}"}

    if not conta.get("ok"):
        return {"ok": False, "error": conta.get("error") or "conta indisponivel"}
    lista = posicoes.get("positions") if isinstance(posicoes, dict) else None
    if lista is None:
        return {"ok": False, "error": "posicoes indisponiveis: sem dado, nao approve"}
    return {
        "ok": True,
        "open_positions": len(lista),
        "daily_trades": int(conta.get("daily_trades", 0) or 0),
        # Exchanges nao expõem estes dois de forma homogenia. `None` e honesto;
        # o risk_gate trata dado ausente como falha fechada.
        "daily_loss_pct": conta.get("daily_loss_pct"),
        "exposure_pct": conta.get("exposure_pct"),
        "drawdown_pct": conta.get("drawdown_pct"),
        "source": f"{broker_norm}_universal",
    }
