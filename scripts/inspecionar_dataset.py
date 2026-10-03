# -*- coding: utf-8 -*-
"""Le o cabecalho do dataset do MT5 e mostra as colunas reais.

Os datasets do terminal usam nomes proprios do MetaTrader: `Symbol` pode vir
como `symbol`, e o separador pode ser `;`. Descobrir a coluna real e o encoding
e o que evita `KeyError: 'Symbol'` e `UnicodeDecodeError` na hora de provar o
backtester com dado real.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\inspecionar_dataset.py
"""
from __future__ import annotations

from pathlib import Path

DATA = Path(
    r"C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal"
    r"\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\Data"
)


def main() -> int:
    import pandas as pd

    for origem in sorted(DATA.glob("dataset*.csv")):
        print(f"\n=== {origem.name} ({origem.stat().st_size / 1e6:.1f} MB) ===")
        achou = False
        for encoding in ("utf-16", "utf-8-sig", "utf-8", "latin-1"):
            for sep in (",", ";"):
                try:
                    df = pd.read_csv(origem, nrows=3, encoding=encoding, sep=sep)
                except (UnicodeDecodeError, UnicodeError, ValueError):
                    continue
                print(f"  encoding={encoding} sep={sep!r}")
                print(f"  colunas: {list(df.columns)}")
                if len(df.columns) > 1:
                    print(f"  1a linha: {df.iloc[0].to_dict()}")
                achou = True
                break
            if achou:
                break
        if not achou:
            print("  nao consegui ler em nenhum encoding/conjunto de separadores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())