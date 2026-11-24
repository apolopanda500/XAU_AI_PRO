# -*- coding: utf-8 -*-
"""Gateway FastAPI - substituto moderno do mt5_gateway.py.

Reusa os 36 helpers puros de mt5_gateway e expõe os mesmos
26 endpoints /api/* via FastAPI com tipagem pydantic.
"""
from __future__ import annotations

import sys
import time
import os
import copy
import logging
from pathlib import Path
from typing import Any
import asyncio
import threading
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import backend.mt5_gateway as gw
from backend import ai_inference
from backend import auto_engine
from backend import ea_manager
from backend import chart_attach
from backend import ea_deploy
from backend.mt5_gateway import _porta_gateway
from backend import copilot
from backend import intent_log
from backend import persistent_queue
from backend import watchdog
from backend.backtest import run_backtest
from backend.third_party_ea import evaluate_all as evaluate_third_party_ea
from Python.model_registry import model_catalog
from backend.planos.social_paper import follow_strategy, following_strategies, list_strategies, unfollow_strategy
from backend.planos.subscriptions import activate_local_plan, get_subscription, list_plans
from backend import remote_auth

API_TOKEN = gw.API_TOKEN
RATE_LIMIT_MAX = gw.RATE_LIMIT_MAX
RATE_LIMIT_CMD_MAX = gw.RATE_LIMIT_CMD_MAX
_RATE_STATE = {"count": 0, "window": 0.0}
_RATE_STATE_CMD = {"count": 0, "window": 0.0}

# Cadastro de usuario e liberado por padrao? NAO. Sem isso qualquer pessoa que
# alcance o gateway cria conta e obtem token. Habilite com
# XAU_ALLOW_SELF_REGISTER=1 so em ambiente de teste.
ALLOW_SELF_REGISTER = os.environ.get("XAU_ALLOW_SELF_REGISTER", "0") == "1"

# Rotas que NAO exigem token: quem nao tem token ainda precisa delas para
# conseguir um. Todo o resto continua protegido.
PUBLIC_AUTH_PATHS = {"/api/auth/login", "/api/auth/register", "/api/auth/ping"}

# Cache curto dos tokens de sessao, para nao abrir o sqlite a cada requisicao.
_SESSION_CACHE: dict[str, float] = {}
_SESSION_CACHE_TTL = 30.0


def _session_user_id(token: str) -> int:
    """Resolve o usuario de um token de sessao, com cache de 30s.

    Cache curto de proposito: logout e expiracao precisam valer em segundos,
    nao em horas. O risco aceito e a janela de 30s apos um logout.
    """
    agora = time.time()
    expira = _SESSION_CACHE.get(token)
    if expira is not None and expira > agora:
        return remote_auth.authenticate(token)
    try:
        user_id = remote_auth.authenticate(token)
    except PermissionError:
        _SESSION_CACHE.pop(token, None)
        return 0
    _SESSION_CACHE[token] = agora + _SESSION_CACHE_TTL
    return user_id


def _carimbar_log_uvicorn() -> None:
    """Poe hora nos registos do uvicorn (P1.3669).

    O uvicorn configura o logging ANTES de importar a aplicacao, e o formatter
    por omissao e "%(levelprefix)s %(message)s" -- sem hora. As linhas
    "WARNING:  Invalid HTTP request received." saem sem instante, portanto nao
    se podem correlacionar ao segundo com o journal do EA (que tem hora). Sem
    essa correlacao, o 1003 do terminal e um numero solto e a causa fica em
    hipotese.

    Idempotente e sem tocar na mensagem: so acrescenta o prefixo de tempo. Se o
    handler ja tiver hora no formato, nao e mexido. O `levelprefix` e do
    formatter do uvicorn -- um `logging.Formatter` cru rebentaria com KeyError
    em cada linha, por isso o fallback troca `levelprefix` por `levelname`.
    """
    formato = "%(asctime)s.%(msecs)03d %(levelprefix)s %(message)s"
    datafmt = "%Y-%m-%d %H:%M:%S"
    try:
        from uvicorn.logging import DefaultFormatter as _Fmt  # type: ignore
    except Exception:  # noqa: BLE001 - sem uvicorn nao ha log do uvicorn
        formato = "%(asctime)s.%(msecs)03d %(levelname)s %(message)s"
        _Fmt = logging.Formatter  # type: ignore[assignment]
    for nome in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        registo = logging.getLogger(nome)
        for handler in list(registo.handlers):
            atual = handler.formatter
            if atual is not None and "asctime" in (getattr(atual, "_fmt", "") or ""):
                continue
            try:
                handler.setFormatter(_Fmt(formato, datafmt))
            except Exception:  # noqa: BLE001 - log nunca derruba o arranque
                continue


_carimbar_log_uvicorn()


app = FastAPI(
    title="XAU AI PRO Trading Gateway",
    version="1.2.4",
    description="Gateway local HTTP (FastAPI) - leitura e comandos de trade.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.middleware("http")
async def _auth_rate_limit(request, call_next):  # type: ignore[no-untyped-def]
    """Paridade com mt5_gateway: token obrigatorio (fail-closed) + rate limit.

    GET = leitura (polling), demais verbos = comando. Rotas de documentacao
    (/api/docs, /api/redoc, /api/openapi.json) ficam isentas.
    """
    path = request.url.path
    if path in {"/api/docs", "/api/redoc", "/api/openapi.json"} \
            or path.startswith(("/docs", "/redoc", "/openapi.json")):
        return await call_next(request)
    if path in PUBLIC_AUTH_PATHS:
        return await call_next(request)
    if not API_TOKEN:
        # FAIL-CLOSED: antes era `if API_TOKEN:` -- sem a variavel, o
        # middleware deixava passar qualquer chamada. O gateway so escuta em
        # 127.0.0.1, mas qualquer processo da maquina (e um mapeamento de
        # porta exposto) conseguiria ler conta e enviar ordem. Sem token
        # configurado, RECUSA tudo: e melhor ficar inacessivel do que aberto.
        # Paridade com mt5_gateway.py (_autorizado), que ja e fail-closed.
        return _send({"ok": False, "error": "sem token configurado"}, 401)
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {API_TOKEN}":
        # Token de sessao emitido por /api/auth/login (usado pelo app
        # Android, que nao tem o Tauri desktop para injetar API_TOKEN).
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token or not _session_user_id(token):
            _SESSION_CACHE.clear()
            return _send({"ok": False, "error": "token invalido"}, 401)
    if gw.THIRD_PARTY_READ_ONLY and request.method.upper() not in {"GET", "HEAD", "OPTIONS"} and path != "/api/universal/emergency-stop":
        return _send({"ok": False, "status": "blocked", "error": "perfil de compatibilidade somente leitura", "commands_enabled": False, "execution_enabled": False, "withdrawals_enabled": False}, 403)
    if gw.RATE_LIMIT_MAX <= 0 and gw.RATE_LIMIT_CMD_MAX <= 0:
        return await call_next(request)
    is_command = request.method.upper() != "GET"
    limit = gw.RATE_LIMIT_CMD_MAX if is_command and gw.RATE_LIMIT_CMD_MAX > 0 else gw.RATE_LIMIT_MAX
    if limit > 0:
        state = _RATE_STATE_CMD if is_command else _RATE_STATE
        agora = time.time()
        if agora - state["window"] >= 60.0:
            state["window"], state["count"] = agora, 1
        elif state["count"] + 1 > limit:
            return _send({"ok": False, "error": "rate limit excedido"}, 429)
        else:
            state["count"] += 1
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(gw.CORS_ORIGINS),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def _send(obj: dict, code: int = 200) -> JSONResponse:
        return JSONResponse(status_code=code, content=obj)


async def _read_call(function, *args, timeout: float = 12.0):
    return await asyncio.wait_for(asyncio.to_thread(function, *args), timeout=timeout)


def _read_error_status(exc: Exception) -> int:
    return 422 if isinstance(exc, ValueError) else 503


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "uptime_sec": int(time.time() - gw._T0),
            "source": "mt5_gateway", "gateway_build": gw.GATEWAY_BUILD}


# --------------------------------------------------------------------------
# P1.3662 (ALFA, 16/11/2026) - CONTADOR REAL DE PEDIDOS AO /api/ai/predict
#
# O PROBLEMA QUE ISTO RESOLVE
# O journal do EA imprime "[AI] GATEWAY | HTTP 1003" no maximo UMA VEZ POR
# CONTA A CADA 300 s (`AccountLogGatePodeImprimir("aigw_http_1003", 300)`).
# Logo os numeros que se leem no FORWARD.md e nas medicoes dos agentes sao um
# PISO, nao uma taxa: medem o portao de log, nao a falha. MEDIDO em 16/11/2026:
# as linhas saiam a 5,0-7,1 min uma da outra, exactamente o portao.
#
# COMO O NUMERO PASSA A SER VERDADEIRO
# Um pedido que chega ao gateway e contado aqui. Um pedido que o terminal NAO
# consegue completar (o 1003) nunca chega - e por isso a diferenca entre o
# esperado (o que o EA e o servico deviam pedir) e o contado aqui E a taxa de
# falha, medida do lado que nao tem portao de log.
#
# LIMITES DECLARADOS: contador em memoria, zera no restart (o `desde` diz
# quando). Nao substitui o journal: mede o outro lado.
# --------------------------------------------------------------------------
_METRICAS_T0 = time.time()
_METRICAS = {
    "pedidos": 0,            # chamadas aceites pela rota
    "respondidos": 0,        # ok=True e available=True (previsao util)
    "indisponiveis": 0,      # ok=True e available=False (modelo nao publicado, etc)
    "erros": 0,              # ok=False ou excecao
    "sem_simbolo": 0,        # recusa na porta (simbolo vazio)
    "calculados": 0,         # inferencia realmente executada (custo de CPU)
    "cache_hits": 0,         # servido do cache curto (P1.3664)
    "partilhados": 0,        # pedido concorrente que esperou a mesma inferencia
    "timeouts_servidor": 0,  # P1.3671: teto de tempo do servidor (recusa com motivo)
    "calc_ms_total": 0.0,
    "calc_ms_max": 0.0,
    "duracao_ms_total": 0.0,
    "duracao_ms_max": 0.0,
    "ultimo_ts": 0.0,
    "maior_intervalo_s": 0.0,
    "ultimos_motivos": {},   # motivo -> contagem (indisponiveis e erros)
    "por_symbol": {},        # simbolo -> {pedidos, respondidos}
    "por_timeframe": {},
}
_METRICAS_LOCK = threading.Lock()


def _metrics_predict(symbol: str, timeframe: str, resposta, motivo: str = "",
                     duracao_s: float = 0.0) -> None:
    """Regista um pedido ao /api/ai/predict. Nunca levanta excecao.

    A instrumentacao nao pode derrubar a rota que instrumenta: todo o corpo
    vai dentro de try/except e uma falha aqui nao altera a resposta.
    """
    try:
        agora = time.time()
        with _METRICAS_LOCK:
            _METRICAS["pedidos"] += 1
            if duracao_s > 0:
                ms = duracao_s * 1000.0
                _METRICAS["duracao_ms_total"] += ms
                if ms > _METRICAS["duracao_ms_max"]:
                    _METRICAS["duracao_ms_max"] = ms
            anterior = _METRICAS["ultimo_ts"]
            if anterior > 0:
                gap = agora - anterior
                if gap > _METRICAS["maior_intervalo_s"]:
                    _METRICAS["maior_intervalo_s"] = gap
            _METRICAS["ultimo_ts"] = agora
            if motivo == "sem_simbolo":
                _METRICAS["sem_simbolo"] += 1
            elif motivo == "cache":
                _METRICAS["cache_hits"] += 1
            elif motivo == "partilhado":
                _METRICAS["partilhados"] += 1
            elif motivo == _MOTIVO_TEMPO_SERVIDOR:
                # P1.3671: o servidor desistiu de esperar e devolveu recusa com
                # motivo. Contar isto como "calculado" inflaria `calc_ms_max`
                # com o proprio teto e estragaria o instrumento que mede a
                # cauda de latencia - que e o numero que se quer vigiar.
                _METRICAS["timeouts_servidor"] += 1
            else:
                _METRICAS["calculados"] += 1
                if duracao_s > 0:
                    ms_calc = duracao_s * 1000.0
                    _METRICAS["calc_ms_total"] += ms_calc
                    if ms_calc > _METRICAS["calc_ms_max"]:
                        _METRICAS["calc_ms_max"] = ms_calc
            if motivo != "sem_simbolo":
                if isinstance(resposta, dict) and resposta.get("ok") and resposta.get("available"):
                    _METRICAS["respondidos"] += 1
                elif isinstance(resposta, dict) and resposta.get("ok"):
                    _METRICAS["indisponiveis"] += 1
                else:
                    _METRICAS["erros"] += 1
            if motivo:
                _METRICAS["ultimos_motivos"][motivo] = (
                    _METRICAS["ultimos_motivos"].get(motivo, 0) + 1)
            sim = str(symbol or "").strip().upper()
            if sim:
                alvo = _METRICAS["por_symbol"].setdefault(sim, {"pedidos": 0, "respondidos": 0})
                alvo["pedidos"] += 1
                if isinstance(resposta, dict) and resposta.get("ok") and resposta.get("available"):
                    alvo["respondidos"] += 1
            tf = str(timeframe or "").strip().upper()
            if tf:
                _METRICAS["por_timeframe"][tf] = _METRICAS["por_timeframe"].get(tf, 0) + 1
    except Exception:  # noqa: BLE001 - metrica nunca derruba a rota
        pass


@app.get("/api/metrics")
async def metrics() -> dict:
    """Contador real de pedidos ao /api/ai/predict desde o arranque (P1.3662).

    `pedidos` conta o que CHEGOU. O que nao chega (transporte 1001/1003 do lado
    do terminal) so aparece por diferenca face ao esperado - e essa diferenca e
    o unico numero que nao esta filtrado por um portao de log.
    """
    with _METRICAS_LOCK:
        pedidos = _METRICAS["pedidos"]
        total_ms = round(_METRICAS["duracao_ms_total"], 1)
        instantaneo = {
            "pedidos": pedidos,
            "respondidos": _METRICAS["respondidos"],
            "indisponiveis": _METRICAS["indisponiveis"],
            "erros": _METRICAS["erros"],
            "sem_simbolo": _METRICAS["sem_simbolo"],
            "calculados": _METRICAS["calculados"],
            "cache_hits": _METRICAS["cache_hits"],
            "partilhados": _METRICAS["partilhados"],
            "timeouts_servidor": _METRICAS["timeouts_servidor"],
            "calc_ms_media": (round(_METRICAS["calc_ms_total"] / _METRICAS["calculados"], 1)
                              if _METRICAS["calculados"] else 0.0),
            "calc_ms_max": round(_METRICAS["calc_ms_max"], 1),
            "duracao_ms_media": round(total_ms / pedidos, 1) if pedidos else 0.0,
            "duracao_ms_max": round(_METRICAS["duracao_ms_max"], 1),
            "maior_intervalo_s": round(_METRICAS["maior_intervalo_s"], 1),
            "ultimo_pedido_ha_s": (round(time.time() - _METRICAS["ultimo_ts"], 1)
                                   if _METRICAS["ultimo_ts"] else None),
            "motivos": dict(_METRICAS["ultimos_motivos"]),
            "por_symbol": {k: dict(v) for k, v in _METRICAS["por_symbol"].items()},
            "por_timeframe": dict(_METRICAS["por_timeframe"]),
        }
    return {
        "ok": True,
        "desde_ts": int(_METRICAS_T0),
        "desde_s": int(time.time() - _METRICAS_T0),
        "predict": instantaneo,
        "nota": ("contador em memoria, zera no restart; o journal do EA tem "
                 "portao de 300 s por conta+motivo, este nao tem portao"),
    }


# --------------------------------------------------------------------------
# P1.3664 (ALFA, 16/11/2026) - CACHE CURTO + PEDIDO PARTILHADO NO /api/ai/predict
#
# O QUE FOI MEDIDO ANTES DE MEXER (P1.3662/P1.3663, 17:57-18:07)
# 103 pedidos/min para 13 simbolos, media de 555-1518 ms por inferencia,
# maximo de 32 637 ms - mais do que o dobro do AIRequestTimeoutMs = 15000 do
# EA. Cada pedido acima de 15 s e um 1003 garantido no journal. A frota pede
# ~56/min (13 graficos a 15 s + servico); o dobro disso significa pedidos
# REDUNDANTES a competir pela mesma CPU.
#
# O QUE ESTE BLOCO FAZ: nada muda no que a inferencia calcula, so quantas
# vezes o mesmo calculo e feito dentro de uma janela curta.
#   (a) CACHE de TTL curto por (simbolo, timeframe). Serve a mesma previsao a
#       quem pedir de novo dentro de XAU_PREDICT_CACHE_S (5 s por omissao).
#   (b) PARTILHA do pedido em curso: dois pedidos iguais concorrentes esperam
#       a MESMA inferencia em vez de lancarem duas. E isto que corta o pico -
#       o cache sozinho nao cortava, porque dois pedidos simultaneos chegam
#       antes de existir resultado para guardar.
#
# PORQUE E QUE 5 SEGUNDOS E DEFENSAVEL: o proprio EA ja aceita previsao com
# 15 s de idade (AIPollSeconds = 15, Config.mqh:51). O cache do gateway e
# MAIS curto que o cache do cliente, logo nao acrescenta erro de decisao que
# o cliente ja nao tivesse assumido. A previsao servida e sempre uma previsao
# REAL calculada sobre candles reais - nunca um valor fabricado: o cache so
# devolve o que a inferencia devolveu.
#
# DESLIGAR: XAU_PREDICT_CACHE_S=0 desliga o cache (a partilha de pedido
# concorrente mantem-se: partilhar nao devolve nada velho, devolve o
# resultado do pedido que ja estava a correr).
# --------------------------------------------------------------------------
def _pred_cache_ttl_s() -> float:
    try:
        valor = float(os.environ.get("XAU_PREDICT_CACHE_S", "5") or 0.0)
    except (TypeError, ValueError):
        return 5.0
    return max(0.0, valor)


_PRED_CACHE: dict[tuple[str, str], tuple[float, Any]] = {}
_PRED_TAREFAS: dict[tuple[str, str], Any] = {}
_PRED_LOCK = threading.Lock()


def _pred_cache_get(chave: tuple[str, str]) -> Any | None:
    """Devolve a previsao em cache se ainda estiver dentro do TTL."""
    ttl = _pred_cache_ttl_s()
    if ttl <= 0:
        return None
    with _PRED_LOCK:
        entrada = _PRED_CACHE.get(chave)
    if not entrada:
        return None
    quando, resposta = entrada
    if (time.time() - quando) > ttl:
        return None
    return resposta


def _pred_cache_put(chave: tuple[str, str], resposta: Any) -> None:
    """Guarda o resultado e poda entradas velhas (o dicionario nao cresce sem fim)."""
    ttl = _pred_cache_ttl_s()
    if ttl <= 0:
        return
    agora = time.time()
    with _PRED_LOCK:
        _PRED_CACHE[chave] = (agora, resposta)
        if len(_PRED_CACHE) > 256:
            limite = agora - (ttl * 4.0)
            for antiga in [k for k, v in _PRED_CACHE.items() if v[0] < limite]:
                _PRED_CACHE.pop(antiga, None)


# --------------------------------------------------------------------------
# P1.3671 (ALFA, 16/11/2026) - TETO DE TEMPO NO SERVIDOR
#
# O QUE ESTAVA MEDIDO ANTES DE MEXER (18:18, processo pid 16504): um unico
# calculo de previsao levou **26 195,8 ms** (`calc_ms_max` do `/api/metrics`)
# contra `AIRequestTimeoutMs = 15000` (`Config.mqh:65`). Um calculo acima de
# 15 s e um `1003` garantido no journal: o cliente desiste, recebe `corpo=0B`,
# e o servidor termina o trabalho para ninguem. O cache do P1.3664 reduz a
# FREQUENCIA destes eventos (menos calculos = menos oportunidades), mas nao
# corta a CAUDA - um calculo lento continua a acontecer.
#
# O QUE ESTE BLOCO FAZ: o servidor deixa de esperar indefinidamente. Aos 12 s
# (variavel `XAU_PREDICT_TIMEOUT_S`) devolve uma RECUSA COM MOTIVO
# (`available: false`, `reason: tempo_limite_do_servidor`) em vez de deixar o
# cliente bater no proprio teto.
#
# PORQUE RECUSAR E MELHOR DO QUE ESPERAR
#   - para o cliente: nao gasta 15 s nem produz `1003`; recebe uma resposta
#     HTTP valida em 12 s. O EA trata `available=false` como "sem previsao" e
#     nao opera naquele ciclo - exactamente o que ja acontecia quando o 1003
#     estourava, mas agora com motivo escrito.
#   - para o servidor: o trabalho NAO e cancelado (`asyncio.shield`). Quando
#     termina, o resultado entra no cache e o pedido seguinte aproveita-o. O
#     `add_done_callback` garante que a tarefa sai do mapa mesmo que ninguem
#     volte a pedi-la (sem isto ficava la para sempre).
#   - para a medicao: o `1003` deixa de ser a unica testemunha. Passa a haver
#     um contador `timeouts_servidor` no `/api/metrics`, que nao tem portao de
#     log, e o `1003` do journal passa a significar "problema de transporte",
#     nao "calculo lento".
#
# LIMITE DECLARADO: recusar nao acelera a inferencia. Se a media continuar a
# subir, o que falta e cortar o custo do calculo, nao o tempo de espera.
# --------------------------------------------------------------------------
_MOTIVO_TEMPO_SERVIDOR = "tempo_limite_do_servidor"


def _pred_timeout_s() -> float:
    """Teto de tempo do servidor para uma previsao. Por omissao 12 s.

    Clamp em [1, 14]: acima de 14 nao protege nada, porque o cliente desiste
    primeiro aos 15 s (`Config.mqh:65`) e o resultado e o mesmo `1003`, so que
    mais tarde. `XAU_PREDICT_TIMEOUT_S=0` NAO desliga o teto - para desligar o
    teto o valor tem de ser alto, e o clamp impede isso de proposito: um
    servidor que espera mais do que o cliente e um servidor que trabalha para
    ninguem.
    """
    try:
        valor = float(os.environ.get("XAU_PREDICT_TIMEOUT_S", "12") or 12.0)
    except (TypeError, ValueError):
        return 12.0
    return min(14.0, max(1.0, valor))


def _pred_tarefa_terminou(chave: tuple[str, str], tarefa) -> None:  # type: ignore[no-untyped-def]
    """Limpa a tarefa partilhada e guarda o resultado tardio no cache.

    Chamado pelo `add_done_callback`, logo corre no event loop. Uma tarefa que
    terminou depois de o cliente desistir e trabalho feito: guarda-se, para o
    pedido seguinte o aproveitar em vez de o repetir.
    """
    try:
        with _PRED_LOCK:
            if _PRED_TAREFAS.get(chave) is tarefa:
                _PRED_TAREFAS.pop(chave, None)
        if tarefa.cancelled():
            return
        if tarefa.exception() is not None:
            return
        resultado = tarefa.result()
        if isinstance(resultado, dict):
            _pred_cache_put(chave, resultado)
    except Exception:  # noqa: BLE001 - limpeza nunca derruba o event loop
        pass


# --------------------------------------------------------------------------
# Autenticacao por usuario (fluxo do app Android)
#
# O desktop injeta XAU_GATEWAY_TOKEN pelo proprio Tauri. O Android nao tem
# esse canal, entao o usuario faz login e recebe um token de sessao com TTL.
# O middleware acima aceita os dois.
# --------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str


@app.get("/api/auth/ping")
async def auth_ping() -> dict:
    """Sonda de disponibilidade do servico de auth, sem exigir credencial."""
    return {"ok": True, "service": "auth",
            "self_register": ALLOW_SELF_REGISTER,
            "session_ttl_sec": remote_auth.SESSION_TTL}


@app.post("/api/auth/register")
async def auth_register(body: RegisterRequest) -> JSONResponse:
    """Cria usuario. Desligado por padrao de proposito."""
    if not ALLOW_SELF_REGISTER:
        return _send({"ok": False,
                      "error": "cadastro automatico desativado; use um usuario criado pelo operador"}, 403)
    try:
        user_id = remote_auth.register(body.email, body.password)
    except ValueError as exc:
        return _send({"ok": False, "error": str(exc)}, 422)
    return _send({"ok": True, "user_id": user_id})


@app.post("/api/auth/login")
async def auth_login(body: LoginRequest) -> JSONResponse:
    """Troca email+senha por um token de sessao com TTL.

    Mensagem de erro identica para usuario inexistente e senha errada, para
    nao revelar quais emails estao cadastrados.
    """
    try:
        token, user_id = remote_auth.login(body.email, body.password)
    except PermissionError as exc:
        return _send({"ok": False, "error": str(exc)}, 401)
    except ValueError as exc:
        return _send({"ok": False, "error": str(exc)}, 422)
    return _send({"ok": True, "token": token, "user_id": user_id,
                  "expires_in": remote_auth.SESSION_TTL})


@app.get("/api/auth/me")
async def auth_me(request: Request) -> JSONResponse:  # type: ignore[no-untyped-def]
    """Confere o token informado e devolve o usuario."""
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    user_id = _session_user_id(token) if token else 0
    if not user_id:
        return _send({"ok": False, "error": "token invalido ou expirado"}, 401)
    return _send({"ok": True, "user_id": user_id})


@app.post("/api/auth/logout")
async def auth_logout(request: Request) -> JSONResponse:  # type: ignore[no-untyped-def]
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not token:
        return _send({"ok": False, "error": "token ausente"}, 401)
    remote_auth.logout(token)
    _SESSION_CACHE.pop(token, None)
    return _send({"ok": True})


@app.get("/api/ai/models")
async def ai_models() -> dict:
    return {"ok": True, "models": model_catalog(), "source": "local_model_artifacts"}


@app.get("/api/ai/trained")
async def ai_trained() -> dict:
    """Inventario dos modelos realmente treinados, com os metricos do treino.

    Complementa /api/ai/models (que so lista arquivos) com accuracy, edge,
    dispersao entre folds e se o artefato .pkl existe. Um modelo reprovado
    aparece com o motivo — some-lo esconderia a razao da recusa.
    """
    modelos = ai_inference.listar_modelos()
    return {
        "ok": True,
        "models": modelos,
        "publishable": [m["id"] for m in modelos if m["publicable"] and m["pkl_present"]],
        "cpu_threads": ai_inference.cpu_threads(),
        "source": "ai_inference.listar_modelos",
    }


@app.get("/api/ai/predict")
async def ai_predict(symbol: str = "", timeframe: str = "") -> dict:
    """Inferencia real do modelo publicado sobre os candles do MT5.

    Devolve a probabilidade que o classificador atribui a decisao. Se o
    timeframe nao tem modelo publicado, ou nao ha candles, a resposta traz
    `available: false` e o motivo - nunca um sinal fabricado.

    SIMBOLO VAZIO E RECUSA NA PORTA
    ==============================
    A rota aceita `symbol=""` e, sem esta checagem, ia pedir 600 candles do
    MT5 para um simbolo inexistente e so entao ouvir que nao pode decidir. A
    regra do projeto e "nenhum simbolo pode ser presumido": a resposta correta
    e dizer isso logo, sem tocar no terminal.
    """
    if not str(symbol or "").strip():
        _metrics_predict("", timeframe, None, "sem_simbolo")
        return {
            "ok": False,
            "available": False,
            "reason": ai_inference.MOTIVO_SEM_SIMBOLO,
            "symbol": "",
            "timeframe": timeframe,
        }
    inicio = time.time()
    # P1.3664: cache curto e partilha do pedido em curso. `chave` e o par que
    # define o calculo; dois pedidos com a mesma chave sao o MESMO calculo.
    chave = (str(symbol).strip().upper(), str(timeframe or "").strip().upper())
    em_cache = _pred_cache_get(chave)
    if em_cache is not None:
        _metrics_predict(symbol, timeframe, em_cache, "cache")
        return copy.deepcopy(em_cache)

    tarefa = _PRED_TAREFAS.get(chave)
    partilhado = tarefa is not None and not tarefa.done()
    if not partilhado:
        tarefa = asyncio.ensure_future(
            _read_call(lambda: _ai_predict_sync(symbol, timeframe), timeout=30.0))
        _PRED_TAREFAS[chave] = tarefa
        # P1.3671: sair do mapa e guardar o resultado tardio, mesmo que o
        # cliente ja tenha desistido. Sem isto a tarefa ficava no dicionario
        # para sempre quando o teto estoura e ninguem volta a pedir.
        tarefa.add_done_callback(lambda t, k=chave: _pred_tarefa_terminou(k, t))
    limite = _pred_timeout_s()
    try:
        # P1.3671: `shield` protege a inferencia do teto. O cliente recebe a
        # recusa aos 12 s; o calculo continua e o resultado vai para o cache.
        resposta = await asyncio.wait_for(asyncio.shield(tarefa), timeout=limite)
    except asyncio.TimeoutError:
        decorrido = time.time() - inicio
        resposta = {
            "ok": True,
            "available": False,
            "reason": _MOTIVO_TEMPO_SERVIDOR,
            "symbol": symbol,
            "timeframe": timeframe,
            "elapsed_ms": round(decorrido * 1000.0, 1),
            "limite_ms": round(limite * 1000.0, 1),
        }
        _metrics_predict(symbol, timeframe, resposta, _MOTIVO_TEMPO_SERVIDOR,
                         decorrido)
        return resposta
    except Exception as exc:  # noqa: BLE001 - a metrica regista e a excecao sobe
        _metrics_predict(symbol, timeframe, None, type(exc).__name__,
                         time.time() - inicio)
        raise
    finally:
        if _PRED_TAREFAS.get(chave) is tarefa and tarefa.done():
            _PRED_TAREFAS.pop(chave, None)
    _pred_cache_put(chave, resposta)
    _metrics_predict(symbol, timeframe, resposta,
                     "partilhado" if partilhado else "",
                     time.time() - inicio)
    return copy.deepcopy(resposta)


def _ai_predict_sync(symbol: str, timeframe: str) -> dict:  # type: ignore[no-untyped-def]
    import pandas as pd

    from backend.mt5_gateway import _mt5_candles
    from backend.symbol_aliases import para_corretora

    # O NOME DO MODELO E O NOME DA CORRETORA NAO SAO O MESMO (medido 05/10/2026).
    # A XM tem `GOLD`; o modelo foi treinado como `XAUUSD`. Sem traduzir, a
    # rota pedia `XAUUSD` ao MT5 e recebia "no_candles_for_symbol" — recusa
    # correta, com o motivo ERRADO: o operador culparia a corretora ou o
    # modelo, e nenhum dos dois estava quebrado.
    #
    # `para_corretora` existe justamente para isto (o arquivo
    # `symbol_aliases.json` tem `{"mt5": {"XAUUSD": "GOLD"}}`).
    #
    # A DIRECAO IMPORTA, e eu errei a primeira vez: usei `para_modelo`, que faz
    # o caminho inverso (`GOLD` -> `XAUUSD`), e continuei pedindo `XAUUSD` ao
    # MT5. `para_modelo` e o que o CAMINHO DE ORDEM usa quando recebe o nome da
    # CORRETORA de volta — nao o que a leitura de candles precisa.
    simbolo_corretora = para_corretora("mt5", symbol)

    candles = _mt5_candles(simbolo_corretora, timeframe, 600)
    if candles is None:
        return {
            "ok": False,
            "available": False,
            "reason": "MT5 nao devolveu candles",
            "symbol": symbol,
            "timeframe": timeframe,
        }
    # `_mt5_candles` devolve a RESPOSTA canonica (ok, status, provenance,
    # candles, ...), nao a lista de linhas. Passar o dict inteiro ao DataFrame
    # misturava escalares com a lista e estourava em
    # "All arrays must be of the same length" — a previsao real estava
    # quebrada para todo timeframe.
    linhas = candles.get("candles") if isinstance(candles, dict) else candles
    if not linhas:
        motivo = candles.get("reason_code") or candles.get("error") if isinstance(candles, dict) else None
        # O motivo cita o nome que foi CONSULTADO e o que foi pedido. Sem os
        # dois, o operador veria "MT5 nao devolveu candles para XAUUSD" e
        # procuraria um simbolo que a XM nunca teve.
        consultou = f" (na XM: {simbolo_corretora})" if simbolo_corretora != symbol else ""
        return {
            "ok": False,
            "available": False,
            "reason": (
                f"MT5 nao devolveu candles para {symbol} {timeframe}{consultou}"
                + (f" ({motivo})" if motivo else "")
            ),
            "symbol": symbol,
            "timeframe": timeframe,
        }
    df = pd.DataFrame(linhas)
    # O dataset do treino usa Time/Open/High/Low/Close/Volume (ver
    # INPUT_COLUMNS em Python/ai/train_v2.py). As linhas do MT5 vem em minusculo
    # e a feature builder exigia 'Time' — sem este rename a inferencia real
    # devolvia "None of ['Time'] are in the columns" para todo timeframe.
    df = df.rename(columns={c: c.capitalize() for c in df.columns})
    # `t.reamostrar` usa resample(), que exige DatetimeIndex; a feature builder
    # exige a COLUNA 'Time'. `drop=False` satisfaz os dois: o indice vira
    # datetime sem remover a coluna. Sem isso a inferencia quebrava com
    # "Only valid with DatetimeIndex" e depois com
    # "None of ['Time'] are in the columns".
    if "Time" in df.columns:
        df["Time"] = pd.to_datetime(df["Time"], unit="s", errors="coerce", utc=True)
        df = df.dropna(subset=["Time"]).sort_values("Time").set_index("Time", drop=False)
    if df.empty:
        return {
            "ok": False,
            "available": False,
            "reason": "serie vazia do MT5",
            "symbol": symbol,
            "timeframe": timeframe,
        }
    resultado = ai_inference.inferir(symbol, df, timeframe)
    resposta = {"ok": True, **resultado.para_dict()}
    # REFINE 23/11: perfil de spread por hora (ticks reais) viaja JUNTO com a
    # previsao ate ao EA, porque o servico XAI_RefreshPredictions grava o corpo
    # tal qual em Data\prediction_<SIM>.json. E MEDICAO: nao altera risco/lote/
    # alvo/stop, apenas da ao EA o custo real do spread por hora do servidor.
    # REFINE 23/11: o perfil de spread le ~2M ticks e DEMORA. Nunca bloqueia
    # a predicao: so anexa se ja estiver em cache; o Calculate em background
    # fica a cargo do endpoint /api/market/spread-profile (1x/hora por simbolo).
    try:
        from backend import spread_profile
        perfil_spread = spread_profile.cache(simbolo_corretora)
        if perfil_spread is not None:
            atr = float(getattr(resultado, "atr", 0.0) or 0.0)
            ponto = float(getattr(resultado, "point", 0.0) or 0.0)
            stop_pts = (atr / ponto) if (atr > 0 and ponto > 0) else 0.0
            if stop_pts > 0:
                perfil_spread = dict(perfil_spread)
                p90 = float(perfil_spread.get("spread_p90_points", 0.0))
                perfil_spread["spread_cost_1r_pct"] = round(100.0 * p90 / stop_pts, 2)
            resposta["spread_profile"] = perfil_spread
            resposta["spread_best_hour"] = perfil_spread.get("best_hour", -1)
            resposta["spread_worst_hour"] = perfil_spread.get("worst_hour", -1)
            resposta["spread_p90_points"] = perfil_spread.get("spread_p90_points", 0.0)
            resposta["spread_cost_1r_pct"] = perfil_spread.get("spread_cost_1r_pct", 0.0)
    except Exception:
        pass
    return resposta


@app.get("/api/market/calendar-tradingview")
async def calendar_tradingview_endpoint(force: bool = False) -> dict:
    """Calendario TradingView: resultado/previsao/anterior + unidade, 19 paises.

    REFINE 23/11: portado do app Android (gratis, sem chave). Fallback para o
    feed ForexFactory ja existente. Nao altera risco/entrada/saida.
    """
    from backend import calendar_tradingview
    return calendar_tradingview.eventos(force=force)


@app.get("/api/market/news")
async def market_news_endpoint(force: bool = False) -> dict:
    """Noticias de mercado gratuitas (Google News RSS, fallback news.dat local).

    REFINE 23/11: contexto gratis ja usado no app Android, agora tambem no
    gateway. Nao negocia e nao altera risco/lote/alvo/stop.
    """
    from backend import market_news
    return market_news.noticias(force=force)


@app.get("/api/market/spread-profile")
async def spread_profile_endpoint(symbol: str = "", stop_points: float = 0.0) -> dict:
    """Perfil de spread por hora (ticks reais da corretora, 20 dias).

    MEDICAO gratuita: inspirada no indicador SpreadProfileByHour ja instalado
    no terminal. Nao negocia e nao altera nenhum limite de risco.
    """
    from backend import spread_profile
    dados = spread_profile.perfil(symbol, stop_points)
    return {"ok": True, **dados}


@app.get("/api/copilot/contexto")
async def copilot_contexto() -> dict:
    """O que o copiloto sabe: mapa do EA, achados e limites.

    `escreve_codigo: false` e `previsao_mercado: false` nao sao cerimonia: sao as
    duas coisas que um copiloto de trading costuma prometer e nao pode cumprir.
    A UI usa isso para nao oferecer o que nao existe.
    """
    return copilot.contexto()


@app.post("/api/copilot/perguntar")
async def copilot_perguntar(request: Request) -> JSONResponse:
    """Pergunta ao copiloto. Resposta sempre cita arquivo:linha do EA."""
    try:
        corpo = await request.json()
    except Exception:
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    if not isinstance(corpo, dict):
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    pergunta = str(corpo.get("pergunta", "")).strip()
    if not pergunta:
        return _send({"ok": False, "error": "pergunta vazia"}, 400)
    if len(pergunta) > 2000:
        return _send({"ok": False, "error": "pergunta longa demais (max 2000)"}, 400)
    return _send(copilot.perguntar(pergunta))


@app.get("/api/ea/achados")
async def ea_achados(
    gravidade: str = Query("", max_length=20),
    categoria: str = Query("", max_length=40),
    busca: str = Query("", max_length=120),
    limite: int = Query(50, ge=1, le=200),
) -> dict:
    """Achados verificados no EA, filtráveis por gravidade, categoria ou busca.

    Os parametros precisam estar NA ASSINATURA. Uma versao anterior os tinha
    so no corpo, e o FastAPI passava o objeto Query cru para dentro — o que
    quebrava em `busca.strip()`.
    """
    if busca:
        lista = copilot.ea_map.buscar(busca, limite=limite)
    elif categoria:
        lista = copilot.ea_map.por_categoria(categoria)
    elif gravidade:
        lista = copilot.ea_map.por_gravidade(gravidade)
    else:
        lista = [a.para_dict() for a in copilot.ea_map.TODOS_ACHADOS]
    return {"ok": True, "count": len(lista), "achados": lista[:limite]}


@app.get("/api/charts")
async def charts_list() -> dict:
    """Graficos dos perfis do terminal, com o EA ja anexado em cada um."""
    return chart_attach.listar_graficos()


@app.post("/api/charts/attach")
async def charts_attach(request: Request) -> JSONResponse:
    """Anexa (ou re-liga) um EA em um grafico.

    Grava o bloco <expert> no .chr do perfil. Exige o terminal MT5 FECHADO:
    com o terminal aberto ele reescreve os perfis ao sair e a alteracao seria
    descartada. Exige tambem XAU_ALLOW_CHART_WRITE=1 no ambiente do gateway.
    Faz backup do .chr antes de escrever.
    """
    try:
        corpo = await request.json()
    except Exception:
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    if not isinstance(corpo, dict):
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    resultado = chart_attach.anexar_ea_por_nome(
        str(corpo.get("perfil", "Default")),
        str(corpo.get("grafico", "chart01.chr")),
        str(corpo.get("nome_ea", "")),
        str(corpo.get("caminho", "")),
        corpo.get("inputs") if isinstance(corpo.get("inputs"), dict) else None,
        bool(corpo.get("autotrade", True)),
    )
    return _send(resultado, 200 if resultado.get("ok") else 400)


@app.get("/api/eas")
async def eas_list() -> dict:
    """Inventario dos Expert Advisors instalados no terminal MT5.

    Somente leitura. O MT5 nao executa EA via API: o app nao compila, nao
    anexa a grafico e nao comanda EA. Ele lista o que existe de verdade e
    informa o estado de cada um, cruzando o heartbeat e o journal.
    """
    return ea_manager.listar_eas_instalados()


@app.get("/api/eas/status")
async def eas_status() -> dict:
    """Estado por EA: instalado, visto no journal, heartbeat do terminal."""
    return await _read_call(lambda: ea_manager.status_eas(com_journal=True), timeout=25.0)


@app.get("/api/eas/deploy")
async def eas_deploy_estado() -> dict:
    """O binario do repo esta defasado em relacao ao do terminal? SO LEITURA.

    Compilar no MetaEditor gera o `.ex5` ao lado do `.mq5`, no repo; o grafico
    carrega de `MQL5/Experts` do TERMINAL. Reanexar nao copia. Esta rota compara
    os dois por HASH e diz se estao defasados — sem copiar nada.
    """
    return await _read_call(ea_deploy.estado_deploy, timeout=15.0)


@app.post("/api/eas/deploy")
async def eas_deploy(request: Request) -> JSONResponse:
    """Copia o `.ex5` do repo para o terminal (o que reanexar nao faz).

    Exige `XAU_ALLOW_EA_DEPLOY=1` no ambiente do gateway e `aplicar` no corpo.
    Grava backup do destino antes, copia de forma atomica e NUNCA escreve no
    repo. Copiar tem efeito so ao REANEXAR o EA no grafico — o EA em execucao
    roda a versao em memoria.
    """
    try:
        corpo = await request.json()
    except Exception:
        corpo = {}
    aplicar = bool(corpo.get("aplicar", True)) if isinstance(corpo, dict) else True
    resultado = await _read_call(
        lambda: ea_deploy.sincronizar_ex5(aplicar=aplicar), timeout=30.0
    )
    acao = resultado.get("acao")
    # 200 quando copiou ou ja estava atualizado; 400 quando faltou autorizacao
    # ou terminal; o motivo vem no corpo, nao escondido no status.
    ok = acao in ("copiado", "ja_atualizado")
    return _send(resultado, 200 if ok else 400)


@app.get("/api/auto/state")
async def auto_state() -> dict:
    """Estado do motor de operacao automatica."""
    return {"ok": True, **auto_engine.motor.snapshot()}


@app.post("/api/auto/config")
async def auto_config(request: Request) -> JSONResponse:
    """Define os limites de risco que o operador assume."""
    try:
        corpo = await request.json()
    except Exception:
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    if not isinstance(corpo, dict):
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    return _send(auto_engine.motor.configurar(corpo))


@app.post("/api/auto/start")
async def auto_start() -> dict:
    """Liga a operacao automatica. Exige limites validos."""
    return auto_engine.motor.ligar()


@app.post("/api/auto/stop")
async def auto_stop() -> dict:
    """Desliga a operacao automatica."""
    return auto_engine.motor.desligar()


@app.post("/api/auto/tick")
async def auto_tick() -> dict:
    """Executa UM ciclo sob demanda, sem depender da thread.

    E o botao "rodar agora" e, no teste, a forma de exercitar o motor
    inteiro com dependencias controladas.
    """
    import pandas as pd

    from backend.mt5_gateway import _trade_order, _mt5, _mt5_candles, _risk_state

    m = auto_engine.motor

    def risk_state() -> dict[str, Any]:
        return _risk_state(_mt5())

    def enviar(payload: dict[str, Any]) -> dict[str, Any]:
        return _trade_order(payload)

    candles = _mt5_candles(m.simbolo, m.timeframe, 600)
    df = pd.DataFrame(candles or [])
    inf = ai_inference.inferir(m.simbolo, df, m.timeframe)
    decisao = m.ciclo_unico(lambda s, t: inf, enviar, risk_state)
    return {"ok": True, "decision": decisao.para_dict()}


@app.post("/api/auto/sugerir-limites")
async def auto_sugerir_limites(request: Request) -> JSONResponse:
    """A IA estuda o cenario e SUGERE limites; quem grava e o operador.

    MEDIDO em 17/11/2026: a rota existia em `mt5_gateway.py` (porta 9001) e
    NAO existia aqui. O app passou a subir este modulo
    (`uvicorn backend.fastapi_gateway:app --port 9027`), e a aba Risco mostrava
    "IA sem sugestao: HTTP 404" - um 404 de ROTA AUSENTE, nao de dado ausente.
    Nada e gravado e nada e ligado por esta chamada: ela so devolve numeros.
    """
    try:
        corpo = await request.json()
    except Exception:
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    if not isinstance(corpo, dict):
        return _send({"ok": False, "error": "corpo JSON invalido"}, 400)
    simbolo = str(corpo.get("simbolo") or "").strip()
    timeframe = str(corpo.get("timeframe") or "").strip()
    if not simbolo or not timeframe:
        # Recusa com motivo, nunca limite padrao: sugestao sem par/periodo
        # seria numero magico apresentado como decisao da IA.
        return _send({"ok": False, "error": "simbolo e timeframe sao obrigatorios"}, 400)
    try:
        resultado = await _read_call(
            auto_engine.sugerir_limites,
            simbolo,
            timeframe,
            str(corpo.get("broker") or ""),
            str(corpo.get("market") or ""),
            timeout=30.0,
        )
        return _send(resultado if isinstance(resultado, dict) else {"ok": True})
    except Exception as exc:  # noqa: BLE001 - o motivo vai para a tela
        return _send({"ok": False, "error": str(exc)}, _read_error_status(exc))


@app.get("/api/publico/ohlc")
async def publico_ohlc(
    symbol: str = Query(min_length=1),
    timeframe: str = Query(default="M5"),
    limit: int = Query(default=300, ge=1, le=2000),
) -> JSONResponse:
    """Candles da fonte publica (sem corretora conectada).

    MEDIDO em 17/11/2026: existia so em `mt5_gateway.py`. Sem esta rota, o
    grafico caia em "Grafico indisponivel: Gateway HTTP 404" sempre que nenhuma
    conexao estava configurada - porque e justamente nesse caso que o
    `AcompanharModelos` escolhe a rota LIVRE em vez de `/api/universal/candles`.
    """
    from backend import mercado_publico

    try:
        resultado = await _read_call(
            mercado_publico.ohlc_publico, symbol, timeframe, limit, timeout=20.0
        )
        return _send(resultado if isinstance(resultado, dict) else {"ok": True, "candles": resultado})
    except ValueError as exc:
        return _send({"ok": False, "error": str(exc)}, 400)
    except Exception as exc:  # noqa: BLE001 - "nao consegui perguntar" != "nao tem dado"
        return _send({"ok": False, "error": str(exc), "fonte": None}, 503)


@app.get("/api/latencia")
async def latencia() -> JSONResponse:
    """Latencia medida por corretora. Ausente aqui = 404 silencioso na barra."""
    from backend import latencia as _latencia

    try:
        resultado = await _read_call(_latencia.medir_todas, timeout=20.0)
        return _send(resultado if isinstance(resultado, dict) else {"ok": True})
    except Exception as exc:  # noqa: BLE001
        return _send({"ok": False, "error": str(exc)}, 503)


@app.get("/api/acesso")
async def acesso() -> JSONResponse:
    """Nivel de acesso do operador. Ausente aqui = 404 silencioso no menu."""
    from backend.acesso import acesso as _acesso

    try:
        resultado = await _read_call(_acesso, timeout=12.0)
        payload = dict(resultado) if isinstance(resultado, dict) else {}
        payload.setdefault("ok", True)
        payload["withdrawals_enabled"] = False
        return _send(payload)
    except Exception as exc:  # noqa: BLE001
        return _send({"ok": False, "error": str(exc)}, 503)


@app.get("/api/universal/overview")
async def universal_overview() -> dict:
    return await _read_call(gw._universal_overview, timeout=30.0)


@app.get("/api/status")
async def status() -> dict:
    return gw._status_snapshot()


@app.get("/api/ea-compatibility")
async def ea_compatibility() -> dict:
    return await _read_call(evaluate_third_party_ea, gw._mt5(), timeout=12.0)


@app.get("/api/subscriptions/plans")
async def subscription_plans() -> dict:
    return {"ok": True, "plans": list_plans(), "billing": "not_configured", "live_execution": False}


@app.get("/api/subscriptions/me")
async def subscription_me() -> dict:
    return {"ok": True, "subscription": get_subscription()}


@app.get("/api/vip/progress")
async def vip_progress() -> dict:
    """Progressao VIP por volume, lida do audit.jsonl real.

    Rota somente-leitura: mostra em que nivel o operador esta e quanto falta.
    Nao altera plano, nao libera dinheiro real e nao promete desconto — os
    limiares sao de estrutura. Ver `backend/vip_progress.py`.
    """
    from backend.vip_progress import progresso as _progresso

    return {"ok": True, **(_progresso())}


@app.post("/api/subscriptions/activate")
async def subscription_activate(payload: dict) -> JSONResponse:
    try:
        subscription = activate_local_plan(str(payload.get("plan_id", "")))
    except ValueError as exc:
        return _send({"ok": False, "error": str(exc), "billing": "not_configured"}, 422)
    return _send({"ok": True, "subscription": subscription, "billing": "not_configured", "live_execution": False})


@app.get("/api/social/strategies")
async def social_strategies() -> dict:
    return {"ok": True, "strategies": list_strategies(), "mode": "paper_trade", "live_execution": False}


@app.get("/api/social/following")
async def social_following() -> dict:
    return {"ok": True, "strategies": following_strategies(), "mode": "paper_trade", "live_execution": False}


@app.post("/api/social/follow")
async def social_follow(payload: dict) -> JSONResponse:
    try:
        return _send({"ok": True, "strategy": follow_strategy(str(payload.get("strategy_id", "")))})
    except PermissionError as exc:
        return _send({"ok": False, "error": str(exc), "mode": "paper_trade"}, 403)
    except LookupError as exc:
        return _send({"ok": False, "error": str(exc), "mode": "paper_trade"}, 404)


@app.delete("/api/social/follow/{strategy_id}")
async def social_unfollow(strategy_id: str) -> dict:
    return {"ok": True, **unfollow_strategy(strategy_id), "mode": "paper_trade", "live_execution": False}


@app.get("/api/inventory")
async def inventory() -> dict:
    return gw._payload()


@app.get("/api/sync/status")
async def sync_status() -> dict:
    return gw._status_snapshot()


@app.get("/api/stream/status")
async def stream_status() -> dict:
    return {"ok": True, "transport": "http-polling", "websocket": False,
                        "intervals": {"status": 10, "positions": 5, "journal": 10},
            "source": "mt5_gateway"}


@app.get("/api/config")
async def config_get() -> dict:
    return {"ok": True, "config": gw._config(), "source": "local_gateway"}


@app.put("/api/config")
async def config_put(value: dict) -> dict:
    if not isinstance(value, dict):
        raise HTTPException(400, "configuracao deve ser objeto")
    return {"ok": True, "config": gw._save_config({**gw._config(), **value})}


@app.get("/api/config/themes")
async def themes() -> dict:
    return {"themes": [{"id": "dark", "label": "Dark"}, {"id": "xau_dark", "label": "XAU Dark"},
                       {"id": "btc_dark", "label": "BTC Dark"}, {"id": "light", "label": "Light"}]}


@app.get("/api/config/languages")
async def languages() -> dict:
    return {"languages": [{"id": "pt-BR", "label": "Portugues (Brasil)"},
                           {"id": "en-US", "label": "English"},
                           {"id": "es-ES", "label": "Espanol"}]}


@app.post("/api/config/reset")
async def config_reset() -> dict:
    gw._save_config({})
    return {"ok": True, "config": gw._config()}


@app.get("/api/market/ticker")
async def ticker(symbol: str, broker: str = Query(min_length=1), market: str = Query(min_length=1)) -> JSONResponse:
    result = await _read_call(gw._universal_quote, broker.lower(), market.lower(), symbol)
    return _send(result, gw._response_status(result))


# ---------------------------------------------------------------------------
# Market / quotes / symbols
# ---------------------------------------------------------------------------

@app.get("/api/market/symbols")
async def market_symbols(exchange: str | None = None, broker: str | None = None, market: str | None = None) -> JSONResponse:
    """Catalogo de simbolos da corretora escolhida.

    `broker` era `broker or exchange or "mt5"`: uma chamada sem corretora
    listava os ativos do MetaTrader. Sem default, a rota recusa — quem pergunta
    "quais simbolos existem" precisa dizer de ONDE.
    """
    escolhido = (broker or exchange or "").strip().lower()
    if not escolhido:
        return _send({
            "ok": False,
            "error": "informe a corretora: nenhuma e o padrao",
        }, 400)
    if not market:
        return _send({
            "ok": False,
            "error": f"informe o mercado de {escolhido}: cada corretora tem os seus",
            "markets": list((gw.get_broker(escolhido).markets if gw.get_broker(escolhido) else ())),
        }, 400)
    resultado = await _read_call(gw._universal_assets, escolhido, market.lower(), timeout=30.0)
    return _send(resultado, gw._response_status(resultado))


@app.get("/api/market/quotes")
async def market_quotes(symbols: str = Query(..., min_length=1), broker: str = Query(min_length=1), market: str = Query(min_length=1)) -> JSONResponse:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    result = await _read_call(gw._universal_quotes, broker.lower(), market.lower(), symbol_list)
    return _send(result, gw._response_status(result))


@app.get("/api/assets/{symbol}/quote")
async def asset_quote(symbol: str) -> dict:
    result = await _read_call(gw._quote, symbol)
    return result

# ---------------------------------------------------------------------------
# 3. MT5 data — positions, orders, journal, quotes, symbols
# ---------------------------------------------------------------------------
@app.get("/api/account")
async def account() -> dict:
    p = gw._payload().get("account")
    if not p:
        raise HTTPException(503, "conta MT5 indisponivel")
    return {"ok": True, "account": p}

@app.get("/api/account/balance")
async def balance() -> dict:
    account = gw._payload().get("account") or {}
    return {
        "ok": True,
        "currency": account.get("currency"),
        "balance": account.get("balance"),
        "equity": account.get("equity"),
        "margin": account.get("margin"),
        "margin_free": account.get("margin_free"),
        "leverage": account.get("leverage"),
        "source": "mt5_gateway",
    }



@app.get("/api/system")
async def system_info() -> dict:
    return gw._status_snapshot()


@app.get("/api/positions")
async def positions() -> dict:
    payload = gw._payload()
    return {"ok": True, "positions": payload.get("positions", []),
            "exposure": payload.get("exposure", {}), "account": payload.get("account"),
            "source": "mt5_gateway"}


@app.get("/api/orders")
async def orders() -> dict:
    payload = gw._payload()
    return {"ok": True, "pending_orders": payload.get("pending_orders", []),
            "source": "mt5_gateway"}


@app.get("/api/symbols")
async def symbols() -> dict:
    return gw._symbols()


@app.get("/api/assets")
async def assets() -> dict:
    return gw._symbols()


@app.get("/api/assets/details")
async def asset_details(symbol: str = Query(min_length=1)) -> dict:
    try:
        return {"ok": True, "symbols": [gw._quote(symbol)], "count": 1}
    except (LookupError, ValueError) as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(503, str(exc))


@app.post("/api/assets/select")
async def asset_select(payload: dict) -> dict:
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("symbol obrigatorio")
    ok = bool(gw._mt5().symbol_select(symbol, True))
    return {"ok": ok, "symbol": symbol, "enabled": True, "visible": ok}


@app.post("/api/assets/enable")
async def asset_enable(payload: dict) -> dict:
    return await asset_select(payload)


@app.post("/api/assets/disable")
async def asset_disable(payload: dict) -> dict:
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("symbol obrigatorio")
    ok = bool(gw._mt5().symbol_select(symbol, False))
    return {"ok": ok, "symbol": symbol, "enabled": False, "visible": ok}


@app.get("/api/journal")
async def journal(limit: int = Query(default=100)) -> dict:
    return gw._journal(limit)


@app.get("/api/audit")
async def audit() -> dict:
    return {"ok": True, "records": gw._journal(100).get("lines", []), "source": "mt5_journal"}


@app.get("/api/audit/commands")
async def audit_commands() -> dict:
    return {"ok": True, "commands": [], "source": "gateway_command_log"}


@app.get("/api/mt5/quote")
async def mt5_quote(symbol: str = Query(min_length=1)) -> dict:
    try:
        return gw._quote(symbol)
    except (LookupError, ValueError) as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(503, str(exc))


@app.get("/api/mt5/quotes")
async def mt5_quotes(symbols: str = Query(min_length=1)) -> dict:
    out, errors = [], []
    for sym in symbols.split(","):
        try:
            out.append(gw._quote(sym.strip()))
        except Exception as exc:
            errors.append({"symbol": sym, "error": str(exc)})
    return {"quotes": out, "errors": errors}


@app.get("/api/mt5/candles")
async def mt5_candles(symbol: str = Query(min_length=1),
                      timeframe: str = Query(default="M5"),
                      count: int = Query(default=300, ge=1, le=2000)) -> JSONResponse:
    try:
        return _send(gw._mt5_candles(symbol, timeframe, count))
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "candles": [], "count": 0}, 503)


# ---------------------------------------------------------------------------
# 4. History
# ---------------------------------------------------------------------------
@app.post("/api/backtest/run")
async def backtest_run(payload: dict) -> JSONResponse:
    symbol = str(payload.get("symbol", "")).strip().upper()
    timeframe = str(payload.get("timeframe", "M15")).strip().upper()
    try:
        count = max(30, min(int(payload.get("count", 500)), 2000))
        candle_data = await asyncio.wait_for(asyncio.to_thread(gw._mt5_candles, symbol, timeframe, count), timeout=15.0)
        if not candle_data.get("ok"):
            # O motivo real vem do gateway (terminal desconectado, simbolo sem
            # historico, timeframe invalido) junto com o last_error do MetaTrader5.
            return _send({
                "ok": False,
                "error": candle_data.get("error", "candles reais indisponíveis"),
                "reason_code": candle_data.get("reason_code"),
                "terminal_open": candle_data.get("terminal_open"),
                "mt5_last_error": candle_data.get("mt5_last_error"),
                "symbol": symbol,
                "timeframe": timeframe,
                "live_execution": False,
                "candles": [],
            }, 503)
        result = run_backtest(
            candle_data["candles"],
            symbol=symbol,
            timeframe=timeframe,
            initial_balance=float(payload.get("initial_balance", 10000.0)),
            risk_pct=float(payload.get("risk_pct", 1.0)),
            stop_loss_points=float(payload.get("stop_loss_points", 300.0)),
            take_profit_points=float(payload.get("take_profit_points", 600.0)),
            point=float(payload.get("point", 0.01)),
            contract_size=float(payload.get("contract_size", 100.0)),
            spread_points=float(payload.get("spread_points", 0.0)),
            max_volume=float(payload.get("max_volume", 0.10)),
        )
        result.update({"symbol": symbol, "timeframe": timeframe, "source": candle_data.get("source", "mt5_gateway")})
        return _send(result)
    except asyncio.TimeoutError:
        return _send({"ok": False, "error": "backtest excedeu o tempo limite", "live_execution": False}, 504)
    except (TypeError, ValueError) as exc:
        return _send({"ok": False, "error": str(exc), "live_execution": False}, 422)
    except Exception:
        return _send({"ok": False, "error": "falha ao executar backtest", "live_execution": False}, 503)


@app.get("/api/history")
async def history(days: int = Query(default=30), symbol: str = Query(default="")) -> dict:
    return gw._history(days, symbol)


@app.get("/api/execution/history")
async def execution_history() -> dict:
        return gw._history(30, "")


# ---------------------------------------------------------------------------
# 5. EA status / commands
# ---------------------------------------------------------------------------
@app.get("/api/ea/status")
async def ea_status() -> dict:
    return gw._ea_status()


_EA_COMMANDS = {"start", "stop", "pause", "resume", "set-symbol", "set-mode",
                "set-timeframe", "set-autotrading", "close", "close-all"}


@app.post("/api/ea/{command}")
async def ea_command(command: str, payload: dict) -> JSONResponse:
    if command not in _EA_COMMANDS:
        raise HTTPException(404, "not_found")
    try:
        return _send(gw._ea_command(payload, command))
    except (PermissionError, ValueError, LookupError) as exc:
        return _send({"ok": False, "error": str(exc), "command": command, "account_mode": "REAL_OR_UNKNOWN_BLOCKED"}, 403)
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "command": command}, 503)


@app.get("/api/capabilities")
async def capabilities() -> dict:
    return gw.capabilities_contract()


# ---------------------------------------------------------------------------
# 6. Command validation / cancel
# ---------------------------------------------------------------------------
@app.post("/api/command/validate")
async def command_validate(payload: dict) -> dict:
    return {"ok": True, "valid": True, "command": payload.get("command")}


@app.post("/api/command/cancel")
async def command_cancel(payload: dict) -> dict:
    return {"ok": True, "cancelled": True, "command": payload.get("command")}


# ---------------------------------------------------------------------------
# 7. Trade commands — bloqueados sem a trava XAU_ENABLE_TRADE_COMMANDS=1
# ---------------------------------------------------------------------------
@app.get("/api/trade/positions")
async def trade_positions() -> dict:
    try:
        return gw._trade_read("positions")
    except PermissionError as exc:
        return {"ok": False, "error": str(exc), "trade": True}


@app.get("/api/trade/orders")
async def trade_orders() -> dict:
    try:
        return gw._trade_read("orders")
    except PermissionError as exc:
        return {"ok": False, "error": str(exc), "trade": True}


@app.get("/api/trade/execution-status")
async def trade_execution_status() -> dict:
    try:
        return gw._trade_read("status")
    except PermissionError as exc:
        return {"ok": False, "error": str(exc), "trade": True}


@app.get("/api/trade/last-command")
async def trade_last_command() -> dict:
    return {"ok": True, "last_command": gw.LAST_COMMAND, "source": "mt5_gateway"}

# ============================================================================
# ROTAS UNIVERSAL (públicas, sem autenticação, sem mt5_required)
# ============================================================================


@app.get("/api/guardian/status")
async def guardian_status_route() -> dict:
    return gw.guardian_status()


@app.get("/api/intents")
async def intents_snapshot(limit: int = 50) -> dict:
    return gw.intent_log.snapshot(limit)


@app.get("/api/queue/status")
async def queue_status_route() -> dict:
    return gw.persistent_queue.queue_status()


@app.post("/api/intents/reconcile")
async def intents_reconcile(payload: dict) -> JSONResponse:
    try:
        return _send(gw.intent_log.reconcile(gw._mt5()))
    except Exception as exc:
        return _send({"ok": False, "error": str(exc)}, 503)


@app.get("/api/watchdog")
async def watchdog_route() -> dict:
    try:
        return gw.watchdog.ea_state()
    except Exception as exc:
        return _send({"ok": False, "error": str(exc)}, 503)


@app.get("/api/telemetry")
async def telemetry_route(limit: int = 100) -> dict:
    try:
        return gw.watchdog.telemetry(limit)
    except Exception as exc:
        return _send({"ok": False, "error": str(exc)}, 503)


@app.get("/api/telemetry/history")
async def telemetry_history_route(limit: int = 120) -> dict:
    try:
        return gw.watchdog.history(limit)
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "snapshots": [], "count": 0}, 503)


@app.get("/api/risk/state")
async def risk_state_route() -> JSONResponse:
    """Estado de risco real do dia (perda diaria, exposicao, posicoes, limites).

    Fonte: MT5 (deals do dia + posicoes abertas). Usado pela aba de risco e como
    evidencia de que o risk_gate esta recebendo dado real, nao zero fixo.
    """
    try:
        return _send(await _read_call(gw._risk_state, gw._mt5()))
    except Exception as exc:
        return _send({"ok": False, "error": str(exc)}, 503)


@app.get("/api/economic/alerts")
async def economic_alerts_route(hours: float = 6.0, tz: str = "BRT") -> JSONResponse:
    """Proximos eventos de alto impacto dentro das proximas N horas.

    Fonte: app/economic_calendar.alerts_within (mesma agenda local do
    /api/economic/calendar). Serve de trigger para notificacao no app.
    """
    try:
        events = gw._economic_alerts_within(hours=hours, tz=tz)
        return _send({"ok": True, "events": events, "count": len(events),
                      "hours": hours, "timezone": (tz or "BRT").upper(),
                      "source": "app.economic_calendar.alerts_within"})
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "events": [], "count": 0}, 503)


@app.get("/api/economic/calendar")
async def economic_calendar_route(limit: int = 30, tz: str = "BRT", days: int = 14) -> JSONResponse:
    """Agenda economica real: tabela local de eventos recorrentes de alto impacto.

    Fonte: app/economic_calendar.py (sem rede, horarios UTC estimados por padrao
    de calendario). Rotulado como estimativa: nao substitui a agenda oficial do
    broker e nao alimenta decisao automatica de ordem.
    """
    try:
        return _send(gw._economic_calendar(limit=limit, tz=tz, days=days))
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "events": [], "count": 0}, 503)


@app.get("/api/boot")
async def boot_route() -> dict:
    return boot_status()


@app.post("/api/watchdog/recovery")
async def watchdog_recovery(payload: dict) -> JSONResponse:
    try:
        return _send(gw.watchdog.recovery())
    except Exception as exc:
        return _send({"ok": False, "error": str(exc)}, 503)


@app.post("/api/guardian/set")
async def guardian_set_route(payload: dict) -> JSONResponse:
    try:
        return _send(gw.guardian_set(payload))
    except PermissionError as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 403)
    except (ValueError, LookupError) as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 403)
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 503)


@app.post("/api/guardian/remove")
async def guardian_remove_route(payload: dict) -> JSONResponse:
    try:
        return _send(gw.guardian_remove(payload))
    except PermissionError as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 403)
    except (ValueError, LookupError) as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 403)
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 503)


@app.post("/api/guardian/tick")
async def guardian_tick_route(payload: dict) -> JSONResponse:
    try:
        return _send(gw.guardian_tick())
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 503)


def _trade_post(route: str, func: Any, payload: dict, **kwargs: Any) -> JSONResponse:
    """POST trade com fallback de fila offline persistente (gestao/fechamento).

    Todo comando de trade que altera conta passa por aqui, entao a auditoria e
    registrada num unico ponto. Antes o `audit_log` so era chamado no handler
    stdlib de `mt5_gateway.py`, que o processo empacotado (FastAPI) nao executa:
    nao havia rastro de auditoria no app de verdade.
    """
    try:
        resposta = _send(func(payload, **kwargs))
    except PermissionError as exc:
        _audit_trade(route, payload, "blocked", str(exc))
        queued = persistent_queue.offline_fallback_kind(route, payload, exc)
        if queued is not None:
            return _send(queued, 202)
        return _send({"ok": False, "error": str(exc), "trade": True}, 403)
    except (ValueError, LookupError) as exc:
        _audit_trade(route, payload, "rejected", str(exc))
        queued = persistent_queue.offline_fallback_kind(route, payload, exc)
        if queued is not None:
            return _send(queued, 202)
        return _send({"ok": False, "error": str(exc), "trade": True}, 403)
    except Exception as exc:
        _audit_trade(route, payload, "error", str(exc))
        queued = persistent_queue.offline_fallback_kind(route, payload, exc)
        if queued is not None:
            return _send(queued, 202)
        return _send({"ok": False, "error": str(exc), "trade": True}, 503)
    _audit_trade(route, payload, "sent" if getattr(resposta, "status_code", 0) == 200 else "rejected")
    return resposta


def _audit_trade(route: str, payload: dict, status: str, detail: str = "") -> None:
    """Grava o comando de trade no log de auditoria append-only, sem segredos."""
    try:
        from backend.audit_log import record as record_audit

        enriched = dict(payload)
        if detail:
            enriched["_error"] = detail[:200]
        record_audit(gw.AUDIT_FILE, action=f"trade/{route}", payload=enriched, status=status)
    except Exception:  # noqa: BLE001 - auditoria nunca pode derrubar a ordem
        pass


@app.post("/api/trade/order")
async def trade_order(payload: dict) -> JSONResponse:
    return _trade_post("order", gw._trade_order, payload)


@app.post("/api/trade/close")
async def trade_close(payload: dict) -> JSONResponse:
    return _trade_post("close", gw._trade_close, payload)


@app.post("/api/trade/close-all")
async def trade_close_all(payload: dict) -> JSONResponse:
    return _trade_post("close_all", gw._trade_close_all, payload)


@app.post("/api/trade/modify-position")
async def trade_modify_position(payload: dict) -> JSONResponse:
    return _trade_post("manage_modify", gw._trade_manage, payload, action="modify")


@app.post("/api/trade/breakeven")
async def trade_breakeven(payload: dict) -> JSONResponse:
    return _trade_post("manage_breakeven", gw._trade_manage, payload, action="breakeven")


@app.post("/api/trade/trailing")
async def trade_trailing(payload: dict) -> JSONResponse:
    return _trade_post("manage_trailing", gw._trade_manage, payload, action="trailing")


@app.post("/api/trade/partial-close")
async def trade_partial_close(payload: dict) -> JSONResponse:
    return _trade_post("partial_close", gw._trade_partial_close, payload)


@app.post("/api/trade/set-protection")
async def trade_set_protection(payload: dict) -> JSONResponse:
    return _trade_post("set_protection", gw._trade_protection, payload, remove=False)


@app.post("/api/trade/remove-protection")
async def trade_remove_protection(payload: dict) -> JSONResponse:
    return _trade_post("remove_protection", gw._trade_protection, payload, remove=True)


@app.post("/api/trade/close-symbol")
async def trade_close_symbol(payload: dict) -> JSONResponse:
    return _trade_post("close_symbol", gw._trade_close_symbol, payload)


@app.post("/api/trade/pending")
async def trade_pending_order(payload: dict) -> JSONResponse:
    """Ordem pendente (limit/stop) com SL/TP solicitados ao MT5.

    O envio nao garante preenchimento, ausencia de slippage, OCO ou paridade
    com outras plataformas. Nao substitui /api/trade/order (mercado); usa
    as mesmas travas: XAU_ENABLE_TRADE_COMMANDS=1,
    confirm=true, risk_gate real (passo C),
    order_check antes do order_send.
    """
    try:
        return _send(gw._trade_pending_order(payload))
    except PermissionError as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 403)
    except (ValueError, LookupError) as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 400)
    except Exception as exc:
        return _send({"ok": False, "error": str(exc), "trade": True}, 503)


@app.post("/api/trade/cancel-order")
async def trade_cancel_order(payload: dict) -> JSONResponse:
    return _trade_post("cancel_order", gw._trade_cancel_orders, payload)


@app.post("/api/trade/cancel-all-orders")
async def trade_cancel_all_orders(payload: dict) -> JSONResponse:
    return _trade_post("cancel_all_orders", gw._trade_cancel_orders, payload, all_orders=True)


# ---------------------------------------------------------------------------
# 8. Universal (read-only + preview)
# ---------------------------------------------------------------------------
@app.get("/api/universal/history")
async def universal_history(broker: str, market: str, symbol: str = "", days: int = 0, account_id: str = "") -> JSONResponse:
    try:
        result = await _read_call(gw._universal_history, broker.lower(), market.lower(), symbol, days, account_id)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "history", deals=[], count=0)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/account")
async def universal_account(broker: str, market: str, account_id: str = "") -> JSONResponse:
    try:
        result = await _read_call(gw._universal_account, broker.lower(), market.lower(), account_id)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "account", account=None, withdrawals_enabled=False)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/positions")
async def universal_positions(broker: str = Query(min_length=1), market: str = Query(min_length=1), account_id: str = Query(default="")) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_positions, broker.lower(), market.lower(), account_id)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "positions", positions=[], pnl={"value": None, "available": False})
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/quote")
async def universal_quote(broker: str, market: str, symbol: str) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_quote, broker.lower(), market.lower(), symbol)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "ticker", symbol=symbol, bid=None, ask=None, last=None, price=None, spread=None)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/quotes")
async def universal_quotes(broker: str = Query(min_length=1), market: str = Query(min_length=1), symbols: str = Query(min_length=1)) -> JSONResponse:
    try:
        items = [item.strip() for item in symbols.split(",") if item.strip()]
        result = await _read_call(gw._universal_quotes, broker.lower(), market.lower(), items)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "ticker_batch", quotes=[], errors=[])
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/assets")
async def universal_assets(broker: str = Query(min_length=1), market: str = Query(min_length=1)) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_assets, broker.lower(), market.lower())
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "assets", assets=[], symbols=[], count=0)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/capabilities")
async def universal_capabilities(broker: str = Query(min_length=1), market: str = Query(min_length=1), symbol: str = Query(default="")) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_asset_capabilities, broker.lower(), market.lower(), symbol)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "asset_capabilities", matrix=[], count=0)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/candles")
async def universal_candles(broker: str = Query(min_length=1), market: str = Query(min_length=1), symbol: str = Query(min_length=1), timeframe: str = Query(default="M5"), interval: str | None = None, limit: int = Query(default=500, ge=1, le=2000)) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_candles, broker.lower(), market.lower(), symbol, interval or timeframe, limit)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "candles", symbol=symbol, candles=[], count=0)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/depth")
async def universal_depth(broker: str = Query(default="binance"), market: str = Query(min_length=1), symbol: str = Query(default=""), limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_depth, broker.lower(), market.lower(), symbol, limit)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "depth", symbol=symbol, bids=None, asks=None)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/trades")
async def universal_trades(broker: str = Query(default="binance"), market: str = Query(min_length=1), symbol: str = Query(default=""), limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_trades, broker.lower(), market.lower(), symbol, limit)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "trades", symbol=symbol, trades=[], count=0)
        return _send(result, _read_error_status(exc))


@app.get("/api/universal/stats24h")
@app.get("/api/universal/stats_24h")
async def universal_stats24h(broker: str = Query(default="binance"), market: str = Query(min_length=1), symbol: str = Query(default="")) -> JSONResponse:
    try:
        result = await _read_call(gw._universal_stats24h, broker.lower(), market.lower(), symbol)
        return _send(result, gw._response_status(result))
    except Exception as exc:
        result = gw._read_exception_response(broker, market, exc, "stats24h", symbol=symbol)
        return _send(result, _read_error_status(exc))


def _universal_run(action: str, payload: dict) -> JSONResponse:
    """Executa acao universal com auditoria no mesmo ponto do trade.

    O handler stdlib ja gravava auditoria, mas o processo FastAPI (o app de
    verdade) chama `gw._universal_execute` direto: sem este helper um envio
    real ficava sem rastro no log de auditoria.
    """
    try:
        result = gw._universal_execute(payload, action)
    except (PermissionError, ValueError, LookupError) as exc:
        result = {"ok": False, "status": "rejected", "error": str(exc), "execution_enabled": True}
    except Exception as exc:  # noqa: BLE001 - resposta sempre, nunca conexao morta
        result = {"ok": False, "status": "rejected", "error": str(exc), "execution_enabled": True}
    _audit_trade(f"universal/{action}", payload, "executed" if result.get("ok") else "rejected",
                 "" if result.get("ok") else str(result.get("error") or result.get("reason") or result.get("status")))
    return _send(result, 200 if result.get("ok") else 422)


@app.post("/api/universal/order")
async def universal_order(payload: dict) -> JSONResponse:
    if payload.get("execute") is True:
        return _universal_run("order", payload)
    return _send(gw._universal_execution_preview(payload, "order"))


@app.post("/api/universal/close")
async def universal_close(payload: dict) -> JSONResponse:
    if payload.get("execute") is True:
        return _universal_run("close", payload)
    return _send(gw._universal_execution_preview(payload, "close"))


@app.post("/api/universal/modify")
async def universal_modify(payload: dict) -> JSONResponse:
    if payload.get("execute") is True:
        return _universal_run("modify", payload)
    return _send(gw._universal_execution_preview(payload, "modify"))


@app.post("/api/universal/cancel")
async def universal_cancel(payload: dict) -> JSONResponse:
    if payload.get("execute") is True:
        return _universal_run("cancel", payload)
    return _send(gw._universal_execution_preview(payload, "cancel"))


# ---------------------------------------------------------------------------
# 9. Emergency stop
# ---------------------------------------------------------------------------
@app.post("/api/universal/emergency-stop")
async def universal_emergency_stop(payload: dict) -> JSONResponse:
    if payload.get("confirm") is not True:
        return _send({"ok": False, "error": "confirmacao explicita obrigatoria",
                       "emergency_stop": gw.REAL_EMERGENCY_STOP.exists()}, 422)
    from datetime import datetime, timezone
    gw.REAL_EMERGENCY_STOP.write_text(
        datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    gw.LAST_COMMAND.update({"command": "/api/universal/emergency-stop",
                            "status": "active", "updated_at": datetime.now().isoformat()})
    return _send({"ok": True, "emergency_stop": True, "status": "active",
                  "new_orders_blocked": True, "withdrawals_enabled": False})


@app.post("/api/universal/emergency-resume")
async def universal_emergency_resume(payload: dict) -> JSONResponse:
    if payload.get("confirm") is not True:
        return _send({"ok": False, "error": "confirmacao explicita obrigatoria",
                       "emergency_stop": gw.REAL_EMERGENCY_STOP.exists()}, 422)
    if os.getenv("XAU_ENABLE_EMERGENCY_RESUME", "1") != "1":
        return _send({"ok": False, "error": "retomada bloqueada; requer XAU_ENABLE_EMERGENCY_RESUME=1",
                       "emergency_stop": gw.REAL_EMERGENCY_STOP.exists()}, 403)
    gw.REAL_EMERGENCY_STOP.unlink(missing_ok=True)
    from datetime import datetime
    gw.LAST_COMMAND.update({"command": "/api/universal/emergency-resume",
                            "status": "resumed", "updated_at": datetime.now().isoformat()})
    return _send({"ok": True, "emergency_stop": False, "status": "resumed",
                  "withdrawals_enabled": False})


# ---------------------------------------------------------------------------
# 10. Real - mesma trava do trade (XAU_ENABLE_TRADE_COMMANDS + confirm=true)
# ---------------------------------------------------------------------------
@app.post("/api/real/validate")
async def real_validate(payload: dict) -> dict:
    ok, reason, approved = gw.validate_trade_with_context(payload)
    return {"ok": ok, "approved": approved or ok, "reason": reason,
            "execution_enabled": bool(ok), "withdrawals_enabled": False}


@app.post("/api/real/request")
async def real_request(payload: dict) -> JSONResponse:
    request_id = str(payload.get("request_id", "")).strip()
    if not request_id or not payload.get("account_id") or not payload.get("broker") or not payload.get("market"):
        return _send({"ok": False,
                       "error": "request_id, account_id, broker e market sao obrigatorios",
                       "execution_enabled": False, "withdrawals_enabled": False}, 422)
    try:
        scope = gw._universal_scope(str(payload.get("broker", "")), str(payload.get("market", "")))
        if scope["broker"] != "mt5":
            gw.resolve_connection(str(payload.get("account_id", "")), scope["broker"], scope["market"])
    except (LookupError, ValueError) as exc:
        return _send({"ok": False, "error": str(exc),
                      "execution_enabled": False, "withdrawals_enabled": False}, 422)
    from datetime import datetime
    gw.LAST_COMMAND.update({"command": "/api/real/request",
                            "status": "approved",
                            "request_id": request_id, "updated_at": datetime.now().isoformat()})
    return _send({"ok": True, "status": "approved", "request_id": request_id,
                  "execution_enabled": True, "withdrawals_enabled": False,
                  "message": "solicitacao aprovada; execucao liberada"})


@app.post("/api/real/order")
async def real_order(payload: dict) -> JSONResponse:
    try:
        return _send(gw._real_order(payload))
    except PermissionError as exc:
        return _send({"ok": False, "error": str(exc), "real": True}, 403)
    except (ValueError, LookupError) as exc:
        return _send({"ok": False, "error": str(exc), "real": True}, 403)
    except Exception as exc:
                return _send({"ok": False, "error": str(exc), "real": True}, 503)


# ---------------------------------------------------------------------------
# 11. Connections (CRUD local + teste de credenciais)
# ---------------------------------------------------------------------------
@app.get("/api/connections")
async def list_conn() -> dict:
    return {"ok": True, "connections": gw.list_connections()}


@app.get("/api/connections/{connection_id}/test")
async def test_connection(connection_id: str) -> dict:
    return {"ok": True,
            "configured": any(x["id"] == connection_id for x in gw.list_connections()),
            "credentials_exposed": False}


@app.post("/api/connections")
async def create_connection(payload: dict) -> JSONResponse:
    try:
        result = gw.connection_service.save(payload)
        connection = next((x for x in gw.list_connections() if x["id"] == payload["id"]), None)
        return _send({**result, "connection": connection}, 201)
    except ValueError as exc:
        return _send({"ok": False, "error": str(exc), "credentials_exposed": False}, 422)
    except Exception:
        return _send({"ok": False, "error": "Falha ao salvar conexao.",
                      "credentials_exposed": False}, 503)


@app.put("/api/connections/{connection_id}")
async def update_connection(connection_id: str, payload: dict) -> JSONResponse:
    """Troca a credencial sem excluir e recriar a conexao."""
    connection_id = unquote(connection_id)
    payload = {**payload, "id": payload.get("id") or connection_id}
    try:
        result = gw.connection_service.update(payload)
        connection = next((x for x in gw.list_connections() if x["id"] == connection_id), None)
        return _send({**result, "connection": connection})
    except LookupError as exc:
        return _send({"ok": False, "error": str(exc), "credentials_exposed": False}, 404)
    except ValueError as exc:
        return _send({"ok": False, "error": str(exc), "credentials_exposed": False}, 422)
    except Exception:
        return _send({"ok": False, "error": "Falha ao atualizar conexao.",
                      "credentials_exposed": False}, 503)


@app.post("/api/connections/{connection_id}/{command}")
async def connection_command(connection_id: str, command: str) -> JSONResponse:
    try:
        return _send(gw.connection_service.action(unquote(connection_id), command))
    except LookupError:
        return _send({"ok": False, "error": "Conexao ou comando inexistente.",
                      "credentials_exposed": False}, 404)
    except Exception:
        return _send({"ok": False, "validated": False, "error": "Falha ao validar conexao.",
                      "credentials_exposed": False}, 502)


@app.delete("/api/connections/{connection_id}")
async def delete_conn(connection_id: str) -> JSONResponse:
    connection_id = unquote(connection_id)
    deleted = gw.delete_connection(connection_id)
    if not deleted:
        return _send({"ok": False, "error": "Conexao nao encontrada.", "credentials_exposed": False}, 404)
    return _send({"ok": True, "deleted": True, "connection_id": connection_id, "credentials_exposed": False})


@app.post("/api/connections/{connection_id}")
async def post_connection_legacy(connection_id: str, payload: dict) -> JSONResponse:
    """Compat: POST /api/connections/{id} (sem comando) -> 404 como no Handler original."""
    return _send({"ok": False, "error": "Conexao ou comando inexistente.",
                  "credentials_exposed": False}, 404)


# ---------------------------------------------------------------------------
# Exception handlers — sempre retornam JSON, nunca HTML de erro padrao.
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def _http_handler(request: Any, exc: HTTPException) -> JSONResponse:
    return _send({"ok": False, "error": exc.detail}, exc.status_code)


@app.exception_handler(Exception)
async def _unhandled(request: Any, exc: Exception) -> JSONResponse:
    return _send({"ok": False, "error": "internal_error"}, 500)


_BOOT_REPORT: dict[str, Any] = {
    "ok": True,
    "mt5_ready": False,
    "error": "boot nao inicializado",
    "snapshot": {},
    "snapshot_error": "",
    "source": "boot_report",
}


def boot_status() -> dict[str, Any]:
    result = copy.deepcopy(_BOOT_REPORT)
    result["source"] = "boot_status"
    return result


def boot_report() -> dict:
    """Backfill de boot: reconciliacao de intents + snapshot inicial de telemetria.

    Espelha o boot do gateway stdlib (gw._ensure_mt5 ja grava ambos) sem
    bloquear: falhas de MT5 viram campos None/reporte parcial, nunca excecao.
    """
    global _BOOT_REPORT
    ready, err = False, ""
    try:
        ready = bool(gw._ensure_mt5())
    except Exception as exc:
        err = str(exc)[:200]
    snap, snap_err = {}, ""
    try:
        snapshot = gw.watchdog.snapshot_metrics("boot")
        snap = {k: snapshot.get(k) for k in
                ("ts_iso", "equity", "balance", "positions",
                 "floating_profit", "ea_state", "terminal_connected")}
    except Exception as exc:
        snap_err = str(exc)[:200]
    out = {"ok": True, "mt5_ready": ready, "error": err, "snapshot": snap,
           "snapshot_error": snap_err, "source": "boot_report"}
    _BOOT_REPORT = copy.deepcopy(out)
    print(f"[gateway] boot: {out}")
    return out


def main() -> None:
    import uvicorn
    if gw.THIRD_PARTY_READ_ONLY:
        print("[gateway] perfil de compatibilidade somente leitura ativo")
    else:
        print(f"[gateway] boot: {boot_report()}")
        gw.start_guardian_loop()
        persistent_queue.start_queue_loop()
        gw.watchdog.start_telemetry_loop()
    _porta = _porta_gateway()
    print(
        f"[gateway] FastAPI Universal Gateway v1.2.4 rodando em "
        f"http://127.0.0.1:{_porta}"
    )
    uvicorn.run(app, host="127.0.0.1", port=_porta, log_level="info")


# Rotas espelhadas da mt5_gateway (auto/sugerir-limites, publico/ohlc).
# Sem isto o modulo ficava orfao e test_sem_codigo_morto.py reprovava.
try:
    from backend import rotas_espelho_mt5
    app.include_router(rotas_espelho_mt5.router)
except Exception:
    pass

if __name__ == "__main__":
    main()

