# -*- coding: utf-8 -*-
"""Bateria de simulacao REAL do app XAU AI PRO.

Roda contra o gateway que estiver no ar (porta lida de XAU_GATEWAY_PORT ou
9001) e exercita o motor automatico de ponta a ponta em DEMO:

  1. /api/health (gateway vivo)
  2. /api/auto/sugerir-limites (IA estuda a serie)
  3. /api/auto/config (aplica os limites sugeridos)
  4. /api/auto/start (liga o motor)
  5. /api/auto/tick N vezes (ciclos reais: inferencia + risk_gate + intent_log)
  6. /api/auto/status (confirma ligado e contadores)
  7. /api/auto/stop (desliga)

Uso:
    python scripts/simulacao_real.py [--simbolo EURUSD] [--tf H1] [--ticks 3]

Nao liga ordem real: depende dos gates XAU_ENABLE_DEMO_ORDERS / XAU_ENABLE_REAL_ORDERS
estarem desligados por padrao (default do gateway). So exercita o ciclo.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request


def _porta() -> int:
    return int(os.getenv("XAU_GATEWAY_PORT", "9001") or "9001")


def _token() -> str:
    # O token de sessao (Tauri) prevalece; aqui lemos do env para CI/manual.
    return os.getenv("XAU_GATEWAY_TOKEN", "").strip()


def _req(metodo: str, caminho: str, corpo=None, timeout: int = 30):
    url = f"http://127.0.0.1:{_porta()}{caminho}"
    dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(url, data=dados, method=metodo)
    req.add_header("Content-Type", "application/json")
    tok = _token()
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--simbolo", default="EURUSD")
    ap.add_argument("--tf", default="H1")
    ap.add_argument("--broker", default="mt5")
    ap.add_argument("--market", default="forex")
    ap.add_argument("--ticks", type=int, default=3)
    args = ap.parse_args()

    falhas = 0
    def passo(nome, ok, detalhe=""):
        nonlocal falhas
        marca = "OK " if ok else "FAIL"
        print(f"[{marca}] {nome}{(' - ' + detalhe) if detalhe else ''}")
        if not ok:
            falhas += 1

    # 1. health
    st, d = _req("GET", "/api/health")
    passo("health", st == 200 and bool(d.get("ok", True)), f"status={st}")

    # 2. sugerir limites (IA)
    st, d = _req("POST", "/api/auto/sugerir-limites", {
        "simbolo": args.simbolo, "timeframe": args.tf,
        "broker": args.broker, "market": args.market,
    })
    ok = st == 200 and d.get("ok") is True
    limites = d.get("limites") if ok else None
    passo("sugerir-limites", ok, f"status={st} conf={limites.get('confianca_minima') if limites else None}")

    # 3. aplicar limites
    if ok:
        st, d = _req("POST", "/api/auto/config", {
            "simbolo": args.simbolo, "timeframe": args.tf,
            "broker": args.broker, "market": args.market,
            "limites": limites,
        })
        passo("config", st == 200 and d.get("ok") is True, f"status={st}")

    # 4. ligar motor
    st, d = _req("POST", "/api/auto/start", {
        "simbolo": args.simbolo, "timeframe": args.tf,
        "broker": args.broker, "market": args.market,
    })
    passo("start", st == 200, f"status={st} {d.get('error','')}")

    # 5. ticks
    for i in range(args.ticks):
        st, d = _req("POST", "/api/auto/tick", {
            "simbolo": args.simbolo, "timeframe": args.tf,
            "broker": args.broker, "market": args.market,
        })
        passo(f"tick {i+1}", st == 200, f"status={st} {str(d)[:80]}")
        time.sleep(0.5)

    # 6. status
    st, d = _req("GET", "/api/auto/status")
    passo("status", st == 200, f"status={st} ligado={d.get('ligado') if isinstance(d,dict) else '?'}")

    # 7. desligar
    st, d = _req("POST", "/api/auto/stop", {})
    passo("stop", st in (200, 204), f"status={st}")

    print(f"\nRESULTADO: {falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
