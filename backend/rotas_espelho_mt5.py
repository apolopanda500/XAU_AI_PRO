# -*- coding: utf-8 -*-
"""Rotas que o app chama e que so a `mt5_gateway` servia.

PORQUE ESTE ARQUIVO EXISTE (medido 17/11/2026 19:0x)
====================================================
Este projeto tem DUAS implementacoes do mesmo gateway:

    backend/mt5_gateway.py      ThreadingHTTPServer, rotas por `parsed.path ==`
    backend/fastapi_gateway.py  FastAPI, rotas por `@app.get/post`

O que esta no ar e quem o painel consulta e a **FastAPI** — medido por
`Get-NetTCPConnection` + `Win32_Process`:

    pid 1616 -> .venv\\Scripts\\python.exe -m uvicorn backend.fastapi_gateway:app --port 9027
    127.0.0.1:9027  LISTEN  1616

Duas rotas que o painel consome existiam SO na `mt5_gateway`:

    POST /api/auto/sugerir-limites   `OperacaoAutomatica.tsx` (botao "IA sugere limites")
    GET  /api/publico/ohlc           `marketApi.ts` (MARKET_ENDPOINTS.publicOhlc)

Consequencia medida nas capturas do dono (17/11/2026 18:50): "IA sem sugestao:
HTTP 404" na aba Risco e "Grafico indisponivel: Gateway HTTP 404" na aba
Operacao. Nao era prefixo trocado: a rota nao existia no processo que escuta.

O QUE ESTE MODULO NAO FAZ
=========================
Nao calcula risco. `/api/auto/sugerir-limites` delega para
`auto_engine.sugerir_limites`, a MESMA funcao que a `mt5_gateway` chama: a
sugestao continua medida no cenario real (edge e confianca da inferencia +
volatilidade da serie) e continua NUNCA gravando nada. Nao ha numero de fabrica
aqui — sugestao de risco com valor fixo e o operador confiando em magia, e a
regra §3 do AGENTS.md proibe numero presumido em qualquer camada.

As assinaturas de resposta sao as mesmas da `mt5_gateway` (inclusive o
`status_code`), porque o cliente ja foi escrito contra elas: dois lados do
mesmo dado com nomes diferentes foi o defeito que mais custou neste projeto.
"""
from __future__ import annotations

import json
from typing import Any, Final

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

#: Caminhos que este modulo espelha. A lista existe para o teste poder
#: comparar os dois lados por MEDICAO, e nao por leitura de olho.
ROTAS_ESPELHADAS: Final[tuple[str, ...]] = (
    "/api/auto/sugerir-limites",
    "/api/publico/ohlc",
)

router = APIRouter(tags=["espelho-mt5"])


def _corpo_json_invalido() -> JSONResponse:
    """Mesma recusa da `mt5_gateway`, com o mesmo texto e o mesmo status."""
    return JSONResponse({"ok": False, "error": "corpo JSON invalido"}, status_code=400)


@router.post("/api/auto/sugerir-limites")
async def sugerir_limites(request: Request) -> JSONResponse:
    """A IA estuda o cenario e SUGERE limites. Nao grava, nao liga nada.

    Quem grava e o operador, pelo "Aplicar". O corpo aceita:
    `simbolo`, `timeframe`, `broker`, `market` — os quatro nomes que o
    componente envia e que `auto_engine.sugerir_limites` le.
    """
    from backend import auto_engine

    bruto = await request.body()
    try:
        corpo: Any = json.loads(bruto or b"{}")
    except (ValueError, UnicodeDecodeError):
        return _corpo_json_invalido()
    if not isinstance(corpo, dict):
        return _corpo_json_invalido()

    # Sem simbolo/periodo a propria funcao recusa com motivo — e a recusa e a
    # resposta certa: 200 com `ok: false` e `error`, como na `mt5_gateway`.
    resultado = auto_engine.sugerir_limites(
        str(corpo.get("simbolo") or ""),
        str(corpo.get("timeframe") or ""),
        str(corpo.get("broker") or ""),
        str(corpo.get("market") or ""),
    )
    return JSONResponse(resultado, status_code=200)


@router.get("/api/publico/ohlc")
async def ohlc_publico(
    symbol: str = Query(default=""),
    timeframe: str = Query(default="M5"),
    limit: int = Query(default=300),
) -> JSONResponse:
    """OHLC de fonte publica, com a procedencia junto.

    Tres respostas distintas de proposito, como na `mt5_gateway`:
    200 com dado, 400 com `error` quando o pedido e invalido, 503 quando
    "nao consegui perguntar" — que nao e a mesma coisa que "nao tem dado".
    """
    from backend import mercado_publico

    try:
        dados = mercado_publico.ohlc_publico(symbol, timeframe, int(limit))
    except ValueError as ex:
        return JSONResponse({"ok": False, "error": str(ex)}, status_code=400)
    except Exception as ex:  # fonte fora do ar nao e ausencia de dado
        return JSONResponse(
            {"ok": False, "error": str(ex), "fonte": None}, status_code=503
        )
    return JSONResponse(dados, status_code=200)
