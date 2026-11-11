# -*- coding: utf-8 -*-
"""Retreina a IA com o pipeline corrigido e so publica o que passa na porta.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\treinar_ia.py --symbol XAUUSD
    .\\.venv\\Scripts\\python.exe scripts\\treinar_ia.py --todos --dry-run

Diferencas em relacao ao `Python/pipeline.py` antigo:
  - o timeframe e reamostrado em codigo (o dataset so tem M5)
  - o alvo nao vaza futuro (piso de ATR expansivo)
  - ha purga de lookahead na fronteira do split
  - as 4 features KCI, zeradas no dataset, sao derivadas da serie
  - nada e publicado sem advantage minima sobre o palpite
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
for caminho in (RAIZ, RAIZ / "Python"):
    if str(caminho) not in sys.path:
        sys.path.insert(0, str(caminho))

from Python.ai import train_v2 as t  # noqa: E402
from data.data_engine_xau import DataEngineXAU  # noqa: E402

DATA = Path(
    r"C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal"
    r"\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\Data"
)
MODELOS = RAIZ / "Python" / "models"
VERSAO_APP = "1.2.0"

# Timeframes faz sentido treinar a partir de uma base M5.
TIMEFRAMES = ["M5", "M15", "H1", "H4"]


def carregar(caminhos: list[Path]) -> pd.DataFrame:
    """Une varios datasets, dedup por (Time, Symbol) mantendo o mais recente."""
    partes = []
    for caminho in caminhos:
        if not caminho.exists():
            print(f"  ! ignorado (nao existe): {caminho.name}")
            continue
        engine = DataEngineXAU(caminho)
        df = engine.load()
        if df is None or df.empty:
            continue
        df = df.assign(_origem=caminho.name)
        partes.append(df)
        print(f"  + {caminho.name}: {len(df):,} linhas")
    if not partes:
        raise SystemExit("Nenhum dataset carregavel.")
    tudo = pd.concat(partes, ignore_index=True)
    antes = len(tudo)
    tudo = tudo.drop_duplicates(subset=["Time", "Symbol"], keep="last").reset_index(drop=True)
    print(f"  = {len(tudo):,} linhas unicas (dedup removeu {antes - len(tudo):,})")
    return tudo


# Banda de plausibilidade da barra contra o preco do PROPRIO simbolo.
# MEDIDO 11/11/2026 no journal dos 15 graficos: USDBRL trazia 7 barras de 810
# com valores 89657.89780..89658.77740 contra um par que vale 5.62, e USDCOP
# trazia 2270000.00000 e 1.39000 dentro de uma serie de 3312.72. O EA ja
# descarta essas barras (banda de 25% em Indicators/VolatilityFilter e em
# Core/SignalCore, P1.3596/P1.3598). O pipeline Python TEM de fazer o mesmo:
# treinar sobre barras que o EA nunca produz deixa o feature_hash a descrever
# um mundo que nao existe em producao.
SANE_TOL_PCT = 0.25
SANE_JANELA = 500


def sanear_barras(base: pd.DataFrame, simbolo: str) -> pd.DataFrame:
    """Descarta barras fora da banda de 25% em volta do preco do simbolo.

    A referencia e a mediana CORRENTE dos fechos (janela de 500 barras, sempre
    deslocada para tras): uma serie de 16 meses tem tendencia legitima e um
    preco unico de referencia cortaria historico real junto com as barras
    corrompidas. Sem o deslocamento a barra julgaria a si propria.
    """
    if base.empty:
        return base
    fecho = pd.to_numeric(base["Close"], errors="coerce")
    referencia = fecho.rolling(SANE_JANELA, min_periods=20).median().shift(1).bfill().ffill()
    referencia = referencia.where(referencia > 0.0, fecho.abs())
    piso = referencia * (1.0 - SANE_TOL_PCT)
    teto = referencia * (1.0 + SANE_TOL_PCT)

    alto = pd.to_numeric(base["High"], errors="coerce")
    baixo = pd.to_numeric(base["Low"], errors="coerce")
    sanas = (
        (fecho > 0.0) & (alto > 0.0) & (baixo > 0.0) & (alto >= baixo)
        & (fecho >= piso) & (fecho <= teto)
        & (alto >= piso) & (alto <= teto)
        & (baixo >= piso) & (baixo <= teto)
    ).fillna(False)

    descartadas = int((~sanas).sum())
    if descartadas:
        exemplo = base.loc[~sanas].head(3)
        valores = ", ".join("%.5f" % float(v) for v in exemplo["Close"].tolist())
        print(
            f"  [SANE] {simbolo} | descartadas={descartadas} de {len(base)}"
            f" | exemplos de fecho={valores}"
        )
    return base.loc[sanas].reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retreino da IA com porta de qualidade")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--todos", action="store_true", help="treina todos os simbolos do dataset")
    parser.add_argument(
        "--simbolos",
        default="",
        help="lista explicita separada por virgula (ex.: EURUSD,GBPUSD). "
        "Treina so esses, sem carregar simbolo de layout misto do dataset antigo.",
    )
    parser.add_argument(
        "--fontes",
        default="",
        help="CSVs explicitos separados por virgula. Vazio usa os datasets "
        "padrao (legacy, dataset.csv e dataset_mt5_*.csv). Serve para treinar "
        "sobre um export fresco, sem misturar dataset antigo.",
    )
    parser.add_argument("--timeframes", default=",".join(TIMEFRAMES))
    parser.add_argument("--min-edge", type=float, default=t.PUBLICACAO_MIN_EDGE)
    parser.add_argument("--min-amostras", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true", help="nao grava modelo nem prediction")
    parser.add_argument("--escrever-prediction", action="store_true")
    parser.add_argument(
        "--prediction-tf",
        default="M5",
        help="timeframe da prediction.json. Padrao M5, que e o timeframe em que "
        "o produto roda. Se nao houver modelo publicado nele, o arquivo sai "
        "com available=false e signal NEUTRAL — a IA fica inerte e o motivo "
        "fica escrito, em vez de servir sinal de outro timeframe.",
    )
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("datasets:")
    fontes = [DATA / "dataset_legacy_20260910_1730.csv", DATA / "dataset.csv"]
    fontes += sorted(DATA.glob("dataset_mt5_*.csv"))
    df = carregar(fontes)

    simbolos = (
        sorted(df["Symbol"].dropna().unique())
        if args.todos
        else [args.symbol]
    )
    timeframes = [x.strip() for x in args.timeframes.split(",") if x.strip()]

    MODELOS.mkdir(parents=True, exist_ok=True)
    resumo: list[dict] = []
    publicados = 0
    # Guarda o melhor resultado por timeframe, para a prediction sair do modelo
    # com melhor evidence — e nao do primeiro da lista.
    resultados_treino: list[tuple[str, object]] = []

    for simbolo in simbolos:
        base = df[df["Symbol"].astype(str).str.upper() == simbolo.upper()]
        base = base.sort_values("Time").reset_index(drop=True)
        # As barras de outra escala sao descartadas ANTES do treino, com a
        # mesma banda de 25% que o EA aplica ao vivo.
        base = sanear_barras(base, simbolo)
        if base.empty:
            print(f"\n{simbolo}: sem barras sanas no dataset")
            continue
        if base.empty:
            # serie vazia ja recusada acima, depois do saneamento
            continue
        print(f"\n=== {simbolo} ({len(base):,} candles M5) ===")
        print(f"{'tf':<5}{'acc':>8}{'f1':>8}{'edge':>9}{'treino':>9}{'teste':>8}  disposicao")
        for tf in timeframes:
            r = t.treinar(base, simbolo, tf, min_amostras=args.min_amostras, min_edge=args.min_edge)
            if not r.Treinou:
                print(f"{tf:<5}{'-':>8}{'-':>8}{'-':>9}{'-':>9}{'-':>8}  REPROVADO: {r.motivo}")
                resumo.append({"symbol": simbolo, "timeframe": tf, "publicavel": False, "motivo": r.motivo})
                continue
            situacao = "PUBLICADO" if r.publicavel else f"reprovado ({r.motivo})"
            print(
                f"{tf:<5}{r.accuracy:>8.4f}{r.f1:>8.4f}{r.edge:>+9.4f}"
                f"{r.treino:>9}{r.teste:>8}  {situacao}"
            )
            if r.folds:
                marcas = " ".join("%+.3f" % f["edge"] for f in r.folds)
                print(f"      folds: {marcas}   estavel={r.estavel}")
            resumo.append(
                {"symbol": simbolo, "timeframe": tf, "publicavel": r.publicavel,
                 "accuracy": r.accuracy, "f1": r.f1, "edge": r.edge, "motivo": r.motivo}
            )
            if r.publicavel:
                publicados += 1
            if args.dry_run:
                continue
            # Grava sempre, mas o `publicable` fica nos metadados: um revisor
            # humano ve a razao da reprovacao em vez de um arquivo ausente.
            joblib.dump(r.modelo, MODELOS / f"{simbolo}_{tf}.pkl")
            (MODELOS / f"{simbolo}_{tf}.meta.json").write_text(
                json.dumps(r.meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            resultados_treino.append((simbolo, r))

    if args.escrever_prediction and resultados_treino:
        for simbolo, r in resultados_treino:
            if r.timeframe != args.prediction_tf:
                continue
            base = df[df["Symbol"].astype(str).str.upper() == simbolo.upper()]
            base = base.sort_values("Time").reset_index(drop=True)
            pred = t.montar_prediction(r, base, VERSAO_APP)
            destino = DATA / "prediction.json"
            destino.write_text(json.dumps(pred, indent=2, ensure_ascii=False), encoding="utf-8")
            estado = "SINAL" if pred["available"] else "INERTE (available=false)"
            print(f"\nprediction.json <- {simbolo} {r.timeframe}: {estado}")
            print(f"  signal={pred['signal']} confianca={pred['confidence']} motivo={pred['reason']}")

    total = len(resumo)
    print("\n" + "=" * 66)
    print(f"publicados: {publicados} de {total} combinacoes")
    if not publicados:
        print("Nenhum modelo passou na porta de qualidade.")
        print("Isso e o resultado correto: melhor sem sinal do que com sinal ruim.")
        return 0
    print("Modelos reprovados ficam gravados com publicable=false e o motivo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
