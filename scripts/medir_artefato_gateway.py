# -*- coding: utf-8 -*-
"""Mede o ARTEFATO congelado do gateway (`dist/mt5-gateway/mt5-gateway.exe`).

A regra do ciclo é **medir o artefato, não o código** (AGENTS.md): o instalador
entrega o `.exe` do PyInstaller, e é ele que o app executa na ponte. Um teste
que só sobe `backend/mt5_gateway.py` pelo fonte prova que o fonte está certo
mesmo quando o pacote sai sem `Docs/version.json`, sem modelos ou com o entry
point trocado — o `.spec` já teve esse defeito.

O que este script mede, e por quê:
  * **sem token → 401** — o `_autorizado()` do gateway local é fail-closed por
    decisão (linha 3131): sem `XAU_GATEWAY_TOKEN` ele recusa tudo, e é essa
    trava que protege uma porta aberta só para 127.0.0.1.
  * **`gateway_build` do `/api/health`** — identidade lida de
    `Docs/version.json` **dentro do pacote**; divergiu, e o frontend recusa o
    bootstrap por tela branca.
  * **`withdrawals_enabled`/`transfers_enabled`** — a proibição permanente
    (§2) conferida no binário, não no fonte.
  * **ordem `execute=false`** — tem de validar e parar em `stage=validated`.

Nunca imprime token nem credencial: só código HTTP e campos públicos.

Uso:
  .venv\\Scripts\\python.exe scripts\\medir_artefato_gateway.py
  .venv\\Scripts\\python.exe scripts\\medir_artefato_gateway.py --porta 9199
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_PADRAO = os.path.join(RAIZ, "dist", "mt5-gateway", "mt5-gateway.exe")

#: Rotas medidas sem credencial: a prova do fail-closed.
ROTAS_SEM_TOKEN = ("/api/health", "/api/capabilities", "/api/positions",
                   "/api/universal/overview", "/api/status")

#: Rotas medidas com credencial.
ROTAS_COM_TOKEN = ("/api/health", "/api/capabilities", "/api/status",
                   "/api/universal/overview", "/api/boot")


def porta_livre() -> int:
    """Uma porta efemera, para nao colidir com o app que esta no ar."""
    with socket.socket() as soquete:
        soquete.bind(("127.0.0.1", 0))
        return soquete.getsockname()[1]


def _chamada(base: str, caminho: str, token: str | None,
             metodo: str = "GET", corpo: dict | None = None) -> tuple[Any, dict]:
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    cabecalhos = {"Content-Type": "application/json"} if dados else {}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    requisicao = urllib.request.Request(
        f"{base}{caminho}", data=dados, method=metodo, headers=cabecalhos)
    try:
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            texto = resposta.read().decode("utf-8", "replace")
            return resposta.status, _json_ou_vazio(texto)
    except urllib.error.HTTPError as exc:
        texto = exc.read().decode("utf-8", "replace")
        return exc.code, _json_ou_vazio(texto)
    except Exception as exc:  # noqa: BLE001 - medição, nunca exceção solta
        return f"ERRO:{type(exc).__name__}", {"erro": str(exc)[:200]}


def _json_ou_vazio(texto: str) -> dict:
    try:
        corpo = json.loads(texto)
    except Exception:
        return {"_texto": texto[:200]}
    return corpo if isinstance(corpo, dict) else {"_texto": str(corpo)[:200]}


def medir_artefato(exe: str = EXE_PADRAO, porta: int | None = None,
                   token: str = "bateria-artefato", tempo_limite: float = 60.0) -> dict:
    """Sobe o `.exe`, mede e encerra. Devolve só medições, nunca credencial."""
    if not os.path.exists(exe):
        return {"disponivel": False, "motivo": f"bundle nao construido: {exe}"}

    porta = porta or porta_livre()
    base = f"http://127.0.0.1:{porta}"
    env = dict(os.environ)
    env.update({
        "XAU_GATEWAY_PORT": str(porta),
        "XAU_GATEWAY_TOKEN": token,
        "XAU_RATE_LIMIT": "0",
        "XAU_RATE_LIMIT_CMD": "0",
    })

    processo = subprocess.Popen([exe], env=env, cwd=RAIZ,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        inicio = time.time()
        while time.time() - inicio < tempo_limite:
            codigo, _ = _chamada(base, "/api/health", None)
            if codigo != "ERRO:URLError":
                break
            time.sleep(0.4)
        else:
            return {"disponivel": True, "respondeu": False, "porta": porta}

        sem_token = {rota: _chamada(base, rota, None)[0] for rota in ROTAS_SEM_TOKEN}
        com_token = {rota: _chamada(base, rota, token)[0] for rota in ROTAS_COM_TOKEN}
        _, health = _chamada(base, "/api/health", token)
        _, capabilities = _chamada(base, "/api/capabilities", token)
        codigo_ordem, corpo_ordem = _chamada(
            base, "/api/universal/order", token, metodo="POST",
            corpo={"broker": "mt5", "market": "metals", "account_id": "simulacao",
                   "symbol": "XAUUSD", "side": "buy", "quantity": 0.01,
                   "order_type": "market", "confirm": True, "execute": False,
                   "request_id": f"artefato-{porta}"})
        codigo_token_errado, _ = _chamada(base, "/api/health", f"{token}-errado")
        return {
            "disponivel": True, "respondeu": True, "porta": porta,
            "sem_token": sem_token,
            "com_token": com_token,
            "gateway_build": health.get("gateway_build"),
            "withdrawals_enabled": capabilities.get("withdrawals_enabled"),
            "transfers_enabled": capabilities.get("transfers_enabled"),
            "codigo_ordem": codigo_ordem,
            "ordem": {k: corpo_ordem.get(k) for k in ("ok", "accepted", "stage")
                      if k in corpo_ordem},
            "token_errado": codigo_token_errado,
        }
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=20)
        except Exception:
            processo.kill()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--exe", default=EXE_PADRAO)
    parser.add_argument("--porta", type=int, default=None)
    parser.add_argument("--token", default="bateria-artefato")
    args = parser.parse_args(argv)

    medição = medir_artefato(args.exe, args.porta, args.token)
    if not medição.get("disponivel"):
        print(f"[AVISO] {medição.get('motivo')}")
        return 2
    if not medição.get("respondeu"):
        print("[FALHA] o binario subiu mas nao respondeu dentro do tempo")
        return 1

    print(f"binario medido: {args.exe}")
    print(f"porta isolada : {medição['porta']}")
    print(f"gateway_build : {medição.get('gateway_build')}")
    print(f"withdrawals_enabled = {medição.get('withdrawals_enabled')}"
          f"  transfers_enabled = {medição.get('transfers_enabled')}")
    print("sem token :")
    for rota, codigo in medição["sem_token"].items():
        print(f"  {rota:34} -> {codigo}")
    print("com token :")
    for rota, codigo in medição["com_token"].items():
        print(f"  {rota:34} -> {codigo}")
    print(f"token errado -> {medição.get('token_errado')}")
    print(f"ordem execute=false -> {medição.get('codigo_ordem')} {medição.get('ordem')}")

    falhas = []
    if any(codigo != 401 for codigo in medição["sem_token"].values()):
        falhas.append("fail-closed quebrado: alguma rota respondeu sem token")
    if medição.get("token_errado") != 401:
        falhas.append("token errado nao foi recusado com 401")
    if medição.get("withdrawals_enabled") is not False:
        falhas.append("withdrawals_enabled nao e False no artefato")
    if medição.get("transfers_enabled") is not False:
        falhas.append("transfers_enabled nao e False no artefato")
    if medição.get("ordem", {}).get("stage") != "validated":
        falhas.append("ordem dry-run nao parou em stage=validated")

    if falhas:
        print("\nFALHAS:")
        for falha in falhas:
            print(f"  - {falha}")
        return 1
    print("\nOK: artefato fail-closed, sem saque/transferencia e dry-run valida.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
