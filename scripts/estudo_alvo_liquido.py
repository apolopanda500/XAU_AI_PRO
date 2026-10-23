# -*- coding: utf-8 -*-
"""Alvo liquido de custo: o modelo bate a classe majoritaria quando o rotulo
so conta movimento que paga o spread?

MEDIDO 22/10/2026 (antes deste estudo): 0 de 40 combinacoes publicaveis com o
alvo de direcao BRUTA, e nenhum sinal direcional no dado (autocorrelacao
|r| <= 0,046). Este script repete a medicao com o unico rotulo que importa
para quem opera: o movimento tem de pagar o custo de entrar e sair.

O custo e o spread do MT5 (coluna Spread, em pontos) convertido pelo `point`
do simbolo. Comissao nao esta no dataset, entao a medida e OTIMISTA: o
resultado real e pior, nunca melhor.

USO
    .\\.venv\\Scripts\\python.exe scripts\\estudo_alvo_liquido.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from Python.ai import train_v2 as t  # noqa: E402

DATA = RAIZ.parent / "Data"
COLUNAS = [
    "Time", "Symbol", "Open", "High", "Low", "Close", "Volume", "Spread",
    "ATR", "ADX", "RSI", "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",
]
SIMBOLOS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD")
TIMEFRAMES = ("M5", "M15", "H1", "H4")


def carregar(simbolos: tuple[str, ...]) -> pd.DataFrame:
    caminho = sorted(DATA.glob("dataset_mt5_*.csv"))[-1]
    df = pd.read_csv(caminho, header=None, names=COLUNAS, encoding="utf-8")
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df = df.dropna(subset=["Time"]).drop_duplicates(["Time", "Symbol"], keep="last")
    return df[df["Symbol"].isin(simbolos)].reset_index(drop=True)


def pontos_do_mt5(simbolos: tuple[str, ...]) -> dict[str, float]:
    """`point` real da corretora. Sem ele, Spread em pontos nao e preco."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {}
    if not mt5.initialize():
        print(f"MT5 indisponivel: {mt5.last_error()}")
        return {}
    saida = {}
    for simbolo in simbolos:
        info = mt5.symbol_info(simbolo)
        if info is not None:
            saida[simbolo] = float(info.point)
    mt5.shutdown()
    return saida


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    tudo = carregar(SIMBOLOS)
    pontos = pontos_do_mt5(SIMBOLOS)
    print(f"linhas: {len(tudo):,}   points: {pontos}")
    total = 0
    publicaveis = 0
    for simbolo in SIMBOLOS:
        ponto = pontos.get(simbolo)
        if not ponto:
            print(f"{simbolo}: sem point do MT5, pulando (custo nao medivel)")
            continue
        serie = tudo[tudo["Symbol"] == simbolo].sort_values("Time")
        for tf in TIMEFRAMES:
            r = t.treinar(serie, simbolo, tf, ponto=ponto)
            total += 1
            if r.Treinou is False:
                print(f"{simbolo:<7}{tf:<4} -- {r.motivo}")
                continue
            publicaveis += 1 if r.publicavel else 0
            neutro = ""
            if r.folds:
                neutro = "  folds " + " ".join(f"{f['edge']:+.3f}" for f in r.folds)
            print(
                f"{simbolo:<7}{tf:<4} acc {r.accuracy:.4f} "
                f"maioria {r.palpite:.4f} edge {r.edge:+.4f}{neutro}  "
                f"{'OK' if r.publicavel else 'reprovado'}"
            )
    print(f"\npublicaveis: {publicaveis} de {total}")
    return 0 if publicaveis else 1


if __name__ == "__main__":
    raise SystemExit(main())
