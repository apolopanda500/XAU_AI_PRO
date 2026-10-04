# -*- coding: utf-8 -*-
"""Sincroniza ativos: modelos x corretoras. Somente leitura, nunca opera.

Compara o catalogo de modelos (`backend/ai_inference.listar_modelos`) com o
catalogo real de cada corretora (gateway `/api/universal/assets`) e diz, por
ativo, ONDE ele opera e em que par:

- MT5/XM: par exato do terminal (`EURUSD`); sem presumir sufixo
- MEXC & Cia: par em USDT via `exchange_symbols` (`BTCUSD` -> `BTCUSDT`)
- Divergencia (ex.: `XAUUSD` sem par na XM real) e reportada, nao inventada

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\sincronizar_ativos.py
    .\\.venv\\Scripts\\python.exe scripts\\sincronizar_ativos.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def _token() -> str:
    env = RAIZ / ".env"
    if not env.exists():
        return ""
    for linha in env.read_text(encoding="utf-8", errors="replace").splitlines():
        if linha.startswith("XAU_GATEWAY_TOKEN="):
            return linha.split("=", 1)[1].strip()
    return ""


def _get(path: str, token: str) -> dict | None:
    req = urllib.request.Request(
        "http://127.0.0.1:9001" + path, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def catalogo_corretora(broker: str, market: str, token: str) -> set[str] | None:
    dados = _get(f"/api/universal/assets?broker={broker}&market={market}", token)
    if not dados or not isinstance(dados.get("assets"), list):
        return None
    return {str(a.get("symbol", "")).upper() for a in dados["assets"] if a.get("symbol")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza ativos: modelos x corretoras")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from backend import ai_inference as ai
    from backend.exchange_symbols import ParInvalido, normalizar_par

    modelos = ai.listar_modelos()
    por_simbolo: dict[str, list[str]] = {}
    for m in modelos:
        por_simbolo.setdefault(str(m.get("symbol", "")), []).append(str(m.get("id", "")))

    token = _token()
    mt5 = catalogo_corretora("mt5", "metals", token) if token else None
    mexc = catalogo_corretora("mexc", "crypto-spot", token) if token else None

    linhas = []
    for simbolo in sorted(por_simbolo):
        capazes = ai.timeframes_capazes(simbolo)
        try:
            par_mexc = normalizar_par(simbolo, contexto="MEXC spot")
            na_mexc = (mexc is None) or (par_mexc in mexc)
        except ParInvalido as exc:
            par_mexc, na_mexc = f"RECUSA: {exc}", False
        no_mt5 = (mt5 is None) or (simbolo in mt5)
        linhas.append({
            "simbolo": simbolo,
            "modelos": len(por_simbolo[simbolo]),
            "capazes": capazes,
            "mt5": simbolo if no_mt5 else "AUSENTE no catalogo MT5",
            "mexc": par_mexc if na_mexc else f"{par_mexc} AUSENTE" if not str(par_mexc).startswith("RECUSA") else par_mexc,
        })

    if args.json:
        print(json.dumps({"ok": True, "ativos": linhas,
                          "gateway": bool(mt5 or mexc)}, ensure_ascii=False, indent=1))
        return 0
    print(f"{'ATIVO':<10}{'MODELOS':<9}{'CAPAZES':<16}{'MT5/XM':<28}{'MEXC'}")
    for ln in linhas:
        print(f"{ln['simbolo']:<10}{ln['modelos']:<9}{','.join(ln['capazes']):<16}"
              f"{ln['mt5']:<28}{ln['mexc']}")
    if mt5 is None and mexc is None:
        print("\ngateway offline: colunas MT5/MEXC nao conferidas (modelos e capazes OK)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
