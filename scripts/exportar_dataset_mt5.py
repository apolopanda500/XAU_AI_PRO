# -*- coding: utf-8 -*-
"""Exporta candles M5 reais do MT5 para o formato do dataset de treino.

POR QUE ESTE SCRIPT EXISTE
==========================
Medido em 22/10/2026: o `dataset_legacy_20260910_1730.csv` termina em
15/08/2026 e o `dataset.csv` tem algumas centenas de linhas por simbolo. O
treino, portanto, valida com dado de agosto. O terminal, porem, entrega M5
de 08/12/2025 ate hoje (`copy_rates_from_pos`, 60.000 barras, medido).

Este script pega esse M5 do proprio terminal e grava no MESMO layout de 15
colunas que o `DataEngineXAU` le. As colunas ATR, ADX, RSI e as quatro KCI
vem zeradas de proposito: `train_v2` deriva ATR/ADX/RSI de Wilder e as KCI da
propria serie OHLC quando a fonte as traz zeradas, e derivar duas vezes
produziria numero diferente do que a inferencia ao vivo calcula.

O QUE ELE NAO FAZ
=================
Nao treina, nao publica modelo, nao envia ordem e nao toca dinheiro. So le
cotacao do terminal e escreve um CSV ao lado dos outros datasets.

USO
====
    .\\.venv\\Scripts\\python.exe scripts\\exportar_dataset_mt5.py
    .\\.venv\\Scripts\\python.exe scripts\\exportar_dataset_mt5.py --barras 200000
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ.parent / "Data"

SIMBOLOS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD")

COLUNAS = 15  # Time, Symbol, O/H/L/C, Volume, Spread, ATR, ADX, RSI, 4x KCI
PAGINA = 50_000  # limite pratico do copy_rates_from_pos (medido)


def linhas_de(barra, simbolo: str) -> list[object]:
    """Uma barra do MT5 no layout do dataset. Indicadores zerados: sao derivados."""
    return [
        datetime.fromtimestamp(int(barra[0]), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        simbolo,
        float(barra[1]),
        float(barra[2]),
        float(barra[3]),
        float(barra[4]),
        float(barra[5]),
        float(barra[6]),
        0.0,  # ATR
        0.0,  # ADX
        0.0,  # RSI
        0.0,  # KCI_VD
        0.0,  # KCI_MAIN
        0.0,  # KDI_PLUS
        0.0,  # KDI_MINUS
    ]


def escrever(destino: Path, registros: list[list[object]]) -> int:
    """Grava sem cabecalho e sem duplicar (Time, Symbol), mantendo o mais novo."""
    vistos: dict[tuple[str, str], list[object]] = {}
    for linha in registros:
        vistos[(str(linha[0]), str(linha[1]))] = linha
    ordenados = sorted(vistos.values(), key=lambda l: (l[1], l[0]))
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    with temporario.open("w", encoding="utf-8", newline="\n") as f:
        for linha in ordenados:
            if len(linha) != COLUNAS:  # pragma: no cover - guarda de layout
                raise ValueError(f"linha com {len(linha)} colunas: {linha!r}")
            f.write(",".join(str(v) for v in linha) + "\n")
    temporario.replace(destino)
    return len(ordenados)


def exportar(simbolos: tuple[str, ...], barras: int, destino: Path) -> int:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        print(f"MT5 nao inicializou: {mt5.last_error()}")
        return 1
    try:
        conta = mt5.account_info()
        print(f"conta {getattr(conta, 'login', '?')} @ {getattr(conta, 'server', '?')}")
        registros: list[list[object]] = []
        for simbolo in simbolos:
            if mt5.symbol_info(simbolo) is None:
                print(f"  ! {simbolo}: ausente na corretora")
                continue
            mt5.symbol_select(simbolo, True)
            # MEDIDO 22/10/2026: `copy_rates_from_pos` recusa mais de ~60.000
            # barras com "Invalid params". A pagina e o que permite pedir
            # historico mais antigo sem depender de um limite invisivel.
            paginas: list[object] = []
            posicao = 0
            while posicao < barras:
                quanto = min(PAGINA, barras - posicao)
                taxa = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, posicao, quanto)
                if taxa is None or len(taxa) == 0:
                    break
                paginas.append(taxa)
                if len(taxa) < quanto:
                    break
                posicao += len(taxa)
            if not paginas:
                print(f"  ! {simbolo}: sem historico ({mt5.last_error()})")
                continue
            total = sum(len(t) for t in paginas)
            primeira = paginas[-1][0][0]
            ultima = paginas[0][-1][0]
            inicio = datetime.fromtimestamp(int(primeira), tz=timezone.utc)
            fim = datetime.fromtimestamp(int(ultima), tz=timezone.utc)
            for taxa in paginas:
                registros.extend(linhas_de(t, simbolo) for t in taxa)
            print(f"  + {simbolo}: {total:,} barras  {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}")
    finally:
        mt5.shutdown()
    if not registros:
        print("nada exportado")
        return 1
    total = escrever(destino, registros)
    print(f"gravado {destino.name}: {total:,} linhas unicas")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--barras", type=int, default=100000)
    parser.add_argument("--simbolos", default=",".join(SIMBOLOS))
    parser.add_argument("--destino", default="")
    args = parser.parse_args()
    simbolos = tuple(s.strip().upper() for s in args.simbolos.split(",") if s.strip())
    destino = (
        Path(args.destino)
        if args.destino
        else DATA / f"dataset_mt5_{datetime.now():%Y%m%d}.csv"
    )
    return exportar(simbolos, args.barras, destino)


if __name__ == "__main__":
    raise SystemExit(main())
