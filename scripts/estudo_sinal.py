# -*- coding: utf-8 -*-
"""Existe sinal? Regra simples contra a classe majoritaria (22/10/2026).

POR QUE ESTE SCRIPT EXISTE
==========================
MEDIDO em 22/10/2026: com 16 meses de M5 real do MT5, o RandomForest de 25
features nao bateu a classe majoritaria em nenhuma das 40 combinacoes
simbolo x timeframe (0 de 40 publicaveis). Antes de culpar o modelo, e preciso
medir se existe sinal NESTE dado e NESTE alvo.

Aqui a regra mais simples possivel - "subiu nas ultimas k barras, compra" -
e comparada com o mesmo palpite honesto que a porta usa: a classe
majoritaria da fatia de teste. Nao treina modelo, nao grava nada, nao publica.
Se nem a regra simples bate a majoritaria, o problema e do alvo/mercado, e
nao da floresta; se ela bate, o problema esta na modelagem.

USO
====
    .\\.venv\\Scripts\\python.exe scripts\\estudo_sinal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if str(RAIZ / "Python") not in sys.path:
    sys.path.insert(0, str(RAIZ / "Python"))

from Python.ai import train_v2 as t  # noqa: E402

DATA = RAIZ.parent / "Data"
COLUNAS = [
    "Time", "Symbol", "Open", "High", "Low", "Close", "Volume", "Spread",
    "ATR", "ADX", "RSI", "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",
]
JANELAS = (1, 3, 6, 12, 24, 48)


def carregar(simbolos: tuple[str, ...]) -> pd.DataFrame:
    fontes = [DATA / "dataset_legacy_20260910_1730.csv", DATA / "dataset.csv"]
    fontes += sorted(DATA.glob("dataset_mt5_*.csv"))
    partes = []
    for caminho in fontes:
        if not caminho.exists():
            continue
        # Encoding medido pelo BOM, nao pelo nome: `dataset.csv` tambem e
        # UTF-16 (o DataLogger grava FILE_UNICODE) e falhava como utf-8.
        inicio = caminho.open("rb").read(2)
        codificacao = "utf-16" if inicio in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
        df = pd.read_csv(
            caminho, header=None, names=COLUNAS, encoding=codificacao,
            dtype={"Symbol": str}, on_bad_lines="skip",
        )
        partes.append(df)
    tudo = pd.concat(partes, ignore_index=True)
    tudo = tudo.drop_duplicates(subset=["Time", "Symbol"], keep="last")
    tudo["Time"] = pd.to_datetime(tudo["Time"], errors="coerce")
    tudo = tudo.dropna(subset=["Time"])
    return tudo[tudo["Symbol"].isin(simbolos)].reset_index(drop=True)


def avaliar(base: pd.DataFrame, janela: int) -> dict[str, float]:
    """Regra de momento avaliada na mesma fatia de teste da porta (80%)."""
    d = base.copy()
    passado = d["Close"] / d["Close"].shift(janela) - 1.0
    palpite = pd.Series(0, index=d.index)
    palpite[passado > 0] = 2
    # NEUTRO quando o movimento anterior nao paga o ATR: a regra nao opina.
    palpite[passado.abs() < 0.5 * (d["ATR"] / d["Close"])] = 1
    corte = int(len(d) * 0.8)
    treino = slice(0, max(0, corte - 10))
    teste = slice(corte + 10, None)

    def media(faixa: slice) -> tuple[float, float]:
        real = d["Target"].iloc[faixa].astype(int)
        previsto = palpite.iloc[faixa].astype(int)
        acerto = float((real == previsto).mean())
        majoritaria = float(real.value_counts(normalize=True).max())
        return acerto, majoritaria

    acc_treino, base_treino = media(treino)
    acc_teste, base_teste = media(teste)
    # IMPORTANTE: a janela e escolhida no TREINO, nunca no teste. Escolher a
    # melhor janela olhando o teste seria selection bias - o mesmo defeito que
    # a porta de qualidade existe para pegar.
    return {
        "edge_treino": acc_treino - base_treino,
        "accuracy": acc_teste,
        "baseline": base_teste,
        "edge": acc_teste - base_teste,
        "cobertura": float((palpite.iloc[teste] != 1).mean()),
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    simbolos = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD")
    tudo = carregar(simbolos)
    print(f"linhas: {len(tudo):,}")
    for simbolo in simbolos:
        base_simbolo = tudo[tudo["Symbol"] == simbolo].sort_values("Time")
        for tf in ("M5", "M15", "H1", "H4"):
            base = t.construir_target(
                t.construir_features(t.reamostrar(base_simbolo, tf)),
                t.LOOKAHEAD.get(tf, 1),
            )
            if len(base) < 500:
                continue
            melhores = []
            for janela in JANELAS:
                r = avaliar(base, janela)
                melhores.append((r["edge_treino"], janela, r))
            melhores.sort(reverse=True)
            _, janela, r = melhores[0]
            edge = r["edge"]
            print(
                f"{simbolo:<7}{tf:<4} melhor k={janela:<3} "
                f"acc {r['accuracy']:.4f} vs majoritaria {r['baseline']:.4f} "
                f"edge {edge:+.4f} cobertura {r['cobertura']:.3f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
