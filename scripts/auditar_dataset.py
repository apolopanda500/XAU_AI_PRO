"""Auditoria de qualidade do dataset legado antes de retreinar.

Motivo: o arquivo tem 670.897 linhas, mas as primeiras linhas têm 11 campos e
as finais 15 — o produtor mudou de schema no meio do arquivo. Alem disso, os
indicadores do comeco do arquivo parecem nao inicializados (ADX=0, RSI=50).
Treinar com isso produz modelo que aprende lixo.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COLUNAS = [
    "Time", "Symbol", "Open", "High", "Low", "Close", "Volume",
    "Spread", "ATR", "ADX", "RSI", "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",
]

ORIGEM = Path(
    r"C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal"
    r"\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\Data\dataset_legacy_20260910_1730.csv"
)


def main() -> int:
    bruto = ORIGEM.read_bytes()
    # Descobre a codificacao como o consumidor real faz.
    if bruto[:2] in (b"\xff\xfe", b"\xfe\xff"):
        enc = "utf-16"
    elif bruto[:3] == b"\xef\xbb\xbf":
        enc = "utf-8-sig"
    else:
        enc = "cp1252"
    print(f"arquivo : {ORIGEM.name}")
    print(f"tamanho : {len(bruto) / 1024 / 1024:.1f} MB")
    print(f"encoding: {enc}")

    # Conta os campos de cada linha sem carregar tudo em memoria.
    texto = bruto.decode(enc, errors="replace")
    linhas = texto.splitlines()
    print(f"linhas  : {len(linhas):,}")

    contagem: dict[int, int] = {}
    for linha in linhas:
        n = linha.count(",") + 1
        contagem[n] = contagem.get(n, 0) + 1
    print("\ncampos por linha (schema mudou no meio do arquivo?):")
    for n in sorted(contagem):
        marca = "  <-- schema antigo, sem as 4 colunas KCI" if n == 11 else ""
        print(f"  {n:>3} campos: {contagem[n]:>9,}{marca}")

    df = pd.read_csv(
        io.StringIO(texto), names=COLUNAS, header=None,
        skip_blank_lines=True, engine="python", on_bad_lines="skip",
    )
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    for c in COLUNAS[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    print(f"\nperiodo : {df['Time'].min()}  ->  {df['Time'].max()}")
    print(f"simbolos: {df['Symbol'].nunique()}")
    print("\nlinhas por simbolo:")
    print(df["Symbol"].value_counts().to_string())

    print("\nindicadores nao inicializados (valores default do MQ):")
    adx_zero = int((df["ADX"] == 0.0).sum())
    rsi_meio = int((df["RSI"] == 50.0).sum())
    print(f"  ADX == 0.0        : {adx_zero:>9,}  ({adx_zero / len(df):.1%})")
    print(f"  RSI == 50.0       : {rsi_meio:>9,}  ({rsi_meio / len(df):.1%})")
    sujo = int(((df["ADX"] == 0.0) | (df["RSI"] == 50.0)).sum())
    print(f"  algum dos dois    : {sujo:>9,}  ({sujo / len(df):.1%})  <-- inservivel")

    print("\nfeatures mortas (constantes) no arquivo:")
    for c in COLUNAS[2:]:
        v = df[c].dropna()
        if len(v) == 0:
            print(f"  {c:<10} toda nula")
        elif v.std() == 0 or v.nunique() == 1:
            print(f"  {c:<10} constante = {v.iloc[0]}")

    print("\nresolucao do timeframe (delta mediano entre candles do XAUUSD):")
    xau = df[df["Symbol"].astype(str).str.upper() == "XAUUSD"].dropna(subset=["Time"])
    xau = xau.sort_values("Time")
    if len(xau) > 10:
        delta = xau["Time"].diff().dt.total_seconds().median() / 60
        print(f"  {delta:.0f} minutos  -> dataset e {['M1','M5','M15','M30','H1','H4'][0] if delta==1 else 'M5' if delta==5 else '?'}")
        print(f"  linhas XAUUSD: {len(xau):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
