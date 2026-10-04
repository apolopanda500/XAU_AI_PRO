# -*- coding: utf-8 -*-
"""Treina o MULTI de cada classe: um modelo so, que opera M1 ate H4.

O QUE O DONO DEFINIU (2026-10-02)
==================================
> *"modelos MULTI precisam operar todos os horarios; apenas os unitarios
> serao separados por periodos"*

Entao aqui nao existe `MULTI_CRYPTO_H1`. Existe **`MULTI_CRYPTO`**, e o
timeframe entra como feature (`Timeframe_Cod`). Um so artefato por classe.

A EVIDENCIA QUE SUSTENTA O DESENHO
===================================
O log de treino de 28/09 mostra que o edge depende do HORIZONTE, nao do
ativo:

| Ativo | M5 | M15 | H1 | H4 |
|---|---|---|---|---|
| EURUSD | +0,0035 (reprovou) | +0,0864 | +0,1641 | +0,2092 |
| ETHUSD | +0,0295 (reprovou) | +0,0946 | +0,1420 | +0,1303 |
| USDCAD | +0,0139 (reprovou) | +0,0685 | +0,0749 | +0,1933 |

Todo M5 reprovou e todo H4 publicou. Separar por timeframe criaria 4
artefatos por classe para capturar um efeito que cabe em UMA feature. Por
isso aqui o horizonte e entrada, e nao sufixo do nome.

A GOVERNANCA NAO MUDA
=====================
Reaproveita `train_v2.walk_forward` e `train_v2.edge_consistente` sem
alterar: 5 folds cronologicos, `publicable=false` com o motivo gravado
quando nao passa. Modelo reprovado NAO entra — e continua gravado, para
que a tela mostre *por que* nao foi publicado.

O QUE ESTE SCRIPT NAO FAZ
==========================
Nao envia ordem, nao toca dinheiro real e nao chama exchange. Treina,
valida e grava o artefato. A trava de saque segue em `AGENTS.md`.

USO
====
    .\.venv\Scripts\python.exe Python\ai\train_multi.py --classe CRYPTO
    .\.venv\Scripts\python.exe Python\ai\train_multi.py --todas
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from Python.ai import train_v2 as t  # noqa: E402
from Python.ai.features_estacionarias import (  # noqa: E402
    CODIGO_TIMEFRAME,
    FEATURES_ESTACIONARIAS,
    FEATURE_VERSION_ESTACIONARIA,
    construir_features_estacionarias,
    feature_hash_estacionaria,
)
from backend.asset_classes import (  # noqa: E402
    CLASSES_COM_DADO,
    nome_do_modelo_multi,
    simbolos_da_classe,
)
from Python.ai.dataset_io import (  # noqa: E402
    COLUNAS as COLUNAS_REAIS,
    DATASET_LIMPO,
    ler_simbolos,
)

MODELOS_DIR = RAIZ / "frontend" / "src-tauri" / "Python" / "models"

#: Dataset limpo produzido por `scripts/limpar_dataset.py`. A constante
#: vive em `Python.ai.dataset_io` para nao existir dois lugares com o id do
#: terminal — ja houve divergencia entre eles.
DATASET = DATASET_LIMPO

#: Timeframes que o MULTI aprende. O dono pediu de M1 ate H4; o dataset tem
#: so M5 e o reamostrador so AGREGA (`alvo >= base`), entao M1 fica fora do
#: treino. Declarado aqui para o log dizer a verdade em vez de omitir.
TIMEFRAMES_TREINO: tuple[str, ...] = ("M5", "M15", "H1", "H4")

MIN_AMOSTRAS = 800

#: Nucleos para o treino. MEDIDO (2026-10-02): `n_jobs=-1` matava o processo
#: — o joblib abre um processo por nucleo e, com ~466 mil amostras x 22
#: features x 300 arvores x profundidade 12, o working set estourava e o SO
#: encerrava o processo SEM stderr (4 MB e CPU em zero no gerenciador).
#:
#: `_carregar` (3,4 s) e `montar_base` (2,8 s) passavam; so o `fit` morria.
#: O valor vem do mesmo env que `ai_inference.cpu_threads()` le, com teto
#: conservador — uma maquina com muitos nucleos extras e o caso que estoura.
N_JOBS_TREINO = max(1, min(int(os.environ.get("XAU_AI_PRO_N_JOBS", "2")), 8))


COLUNAS_REAIS = (
    "Time", "Symbol", "Open", "High", "Low", "Close", "Volume",
    "Spread", "ATR", "ADX", "RSI",
)


def _largura_do_csv() -> list[str]:
    """Nomeia as colunas pela largura REAL do CSV.

    MEDIDO (2026-10-02): as linhas tem **11 campos**, nao os 15 de
    `train_v2.COLUNAS_DATASET`. Zipar as duas listas dava `KDI_MINUS = None` em
    toda linha, e o filtro `len(partes) < 15` descartava o arquivo inteiro — o
    treino acusava *"sem dados para a classe"* com o arquivo de 85 MB na mesa.

    As 4 colunas KCI nao existem no arquivo, e isso e o esperado: e
    exatamente por isso que `derivar_kci_estacionaria` as calcula da serie.
    """
    return list(COLUNAS_REAIS)


def _carregar(classe: str) -> pd.DataFrame:
    """Le o dataset limpo e devolve so as linhas dos simbolos da classe.

    O parseo mora em `Python.ai.dataset_io.ler_simbolos` de proposito. A
    versao anterior vivia aqui e importava `scripts.limpar_dataset` DENTRO da
    funcao; como `scripts/` nao tem `__init__.py`, o Python tratava a pasta
    como namespace package e o auto-loader varria os 36 arquivos do diretorio.
    O processo ficava em 4 MB com CPU em zero e **sem stderr** — um travamento
    sem rastro. Medido: o mesmo parseo, antes do import aninhado, levava 2,2 s.
    """
    if not DATASET.exists():
        raise FileNotFoundError(
            f"dataset limpo ausente: {DATASET}\n"
            "Rode antes: .\\.venv\\Scripts\\python.exe scripts\\limpar_dataset.py"
        )
    registros = ler_simbolos(DATASET, set(simbolos_da_classe(classe)))
    if not registros:
        return pd.DataFrame()
    df = pd.DataFrame(registros, columns=list(COLUNAS_REAIS))
    # `format=` explicito: sem ele o pandas cai no `dateutil` e emite
    # "Could not infer format, so each element will be parsed individually" —
    # o que e lento E o mesmo parse, elemento a elemento. O dataset tem dois
    # formatos ("2026-01-02 09:05:00" e "2026.09.16 04:55:00") porque os dois
    # arquivos veio de produtor diferentes.
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce", format="mixed")
    df = df.dropna(subset=["Time", "Open", "High", "Low", "Close"])
    return _descartar_timestamps_impossiveis(df)


#: Uma data so e plausivel nesta janela. O dataset e de 2026; a faixa e larga
#: de proposito para nao eliminar dado legitimo de um produtor antigo.
JANELA_TEMPORAL = ("1990-01-01", "2035-12-31")


def _descartar_timestamps_impossiveis(df: pd.DataFrame) -> pd.DataFrame:
    """Remove a data quebrada que envenena todo o reamostramento.

    MEDIDO (2026-10-02): o `dataset_limpo.csv` tem **1 linha em 49.365** com
    `Time = "4 13:05:00"` — um corte do produtor, sem ano. O pandas parseia
    como `0001-01-04 13:05:00` (ano 1, sem reclamar).

    Uma linha so nao estraga o reamostramento inteiro, porque
    `resample()` usa o **span** entre `min` e `max` para criar os bins: de 1
    ate 2026 dao 2.025 anos, e um bin por minuto disso sao as 71.028.348
    linhas que estouraram a RAM no treino do FIAT
    (`ArrayMemoryError: Unable to allocate 542. MiB`).

    A alternativa — filtrar no `min()`/`max()` do resample — esconderia o dado
    ruim mas deixaria a causa. Aqui a linha some do conjunto, que e o que a
    governanca de dados pede.
    """
    if df.empty:
        return df
    inicio, fim = pd.Timestamp(JANELA_TEMPORAL[0]), pd.Timestamp(JANELA_TEMPORAL[1])
    dentro = df["Time"].between(inicio, fim)
    if dentro.all():
        return df
    descartadas = int((~dentro).sum())
    print(
        f"    timestamps fora de {JANELA_TEMPORAL[0]}..{JANELA_TEMPORAL[1]}: "
        f"{descartadas} linha(s) descartada(s)",
        flush=True,
    )
    return df[dentro].reset_index(drop=True)


def montar_base(bronze: pd.DataFrame, classe: str) -> pd.DataFrame:
    """Concatena todos os simbolos e timeframes da classe em uma base so.

    Aqui esta o que faz o MULTI ser MULTI: cada simbolo e reamostrado em cada
    timeframe, as features estacionarias sao calculadas **com o timeframe
    daquela fatia**, e tudo e empilhado. O modelo ve a classe inteira e
    aprende sozinho que H4 se comporta diferente de M5 — porque
    `Timeframe_Cod` esta nas features e o rotulo tambem depende do horizonte.
    """
    blocos: list[pd.DataFrame] = []
    for simbolo, serie in bronze.groupby("Symbol"):
        serie = serie.sort_values("Time").set_index("Time")
        for timeframe in TIMEFRAMES_TREINO:
            if timeframe not in CODIGO_TIMEFRAME:
                continue
            try:
                agregada = t.reamostrar(serie.reset_index(), timeframe)
            except ValueError:
                continue
            if len(agregada) < 200:
                continue
            horizonte = t.LOOKAHEAD.get(timeframe, 2)
            base = construir_features_estacionarias(agregada, timeframe, classe)
            base = t.construir_target(base, horizonte)
            # `replace([inf, -inf], nan)` cria uma COPIA do quadro inteiro.
            # Medido no FIAT: a base dava ~71 milhoes de celulas e o processo
            # morria com `ArrayMemoryError: Unable to allocate 542. MiB`.
            # Substituir apenas nas colunas que entram no treino evita a copia
            # e o `dropna` ja descarta o que sobrou.
            colunas = FEATURES_ESTACIONARIAS + ["Target"]
            valores = base[colunas].to_numpy(dtype="float64", na_value=np.nan)
            base.loc[:, colunas] = base[colunas].mask(np.isinf(valores))
            base = base.dropna(subset=colunas)
            del agregada, valores
            if len(base) < MIN_AMOSTRAS:
                continue
            base = base.sort_values("Time")  # ordem cronologica entre timeframes
            blocos.append(base)
            # O `ArrayMemoryError` nasce ANTES daqui, dentro do
            # `resample().agg("mean")` do pandas. Manter todas as fatiadas
            # vivas ate o `concat` final significa que as duas copias coexistem
            # no fim, e com 10 pares x 4 timeframes isso estoura a RAM.
            # `gc.collect()` devolve ao SO o que o pandas ainda segura da
            # fatiada anterior; sem ele o processo mantem tudo ate o fim.
            gc.collect()
    if not blocos:
        return pd.DataFrame()
    return pd.concat(blocos, ignore_index=True)


def _walk_forward_estacionario(base: pd.DataFrame, n_folds: int = t.N_FOLDS) -> list[dict[str, Any]]:
    """Mesma validacao de `train_v2.walk_forward`, nas colunas estacionarias.

    Deliberadamente duplicada em vez de parametrizar a original: mexer em
    `train_v2` afetaria os 36 modelos ja publicados, e a governanca deles
    depende de `walk_forward` nao mudar. A logica e a mesma — expanding
    window, 5 folds cronologicos, purga de 10 barras.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score

    folds: list[dict[str, Any]] = []
    total = len(base)
    min_treino = min(500, max(200, total // 4))
    if total < min_treino + 200:
        return folds
    passo = (total - min_treino) // n_folds
    for k in range(n_folds):
        fim_treino = min_treino + k * passo
        ini_teste = fim_treino + 10  # purga de lookahead
        fim_teste = min(total, ini_teste + passo)
        if fim_treino < 200 or fim_teste - ini_teste < 50:
            continue
        X_tr = base[FEATURES_ESTACIONARIAS].iloc[:fim_treino]
        y_tr = base["Target"].iloc[:fim_treino].astype(int)
        X_te = base[FEATURES_ESTACIONARIAS].iloc[ini_teste:fim_teste]
        y_te = base["Target"].iloc[ini_teste:fim_teste].astype(int)
        modelo = RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=5,
            class_weight="balanced", random_state=42 + k, n_jobs=N_JOBS_TREINO,
        )
        modelo.fit(X_tr, y_tr)
        acc = float(accuracy_score(y_te, modelo.predict(X_te)))
        palpite = 1.0 / max(int(base["Target"].nunique()), 2)
        folds.append({
            "fold": k + 1,
            "accuracy": acc,
            "baseline": palpite,
            "edge": acc - palpite,
            "train": int(len(X_tr)),
            "test": int(len(X_te)),
        })
    return folds


def _balancear(base: pd.DataFrame, teto: int | None = None) -> pd.DataFrame:
    """Reduz a base preservando a proporcao de classe e de timeframe.

    POR QUE ISTO EXISTE (2026-10-02)
    =================================
    Medido nesta maquina:

    - `RandomForest.fit` nas 466.465 linhas do CRYPTO leva **49,6 s** e passa,
      mas cinco folds sobre a base inteira nao cabem: o processo morria em
      ~30 s, 4 MB de working set e **sem stderr**.
    - No FIAT o excesso chegou a ser explicito:
      `numpy._core._exceptions._ArrayMemoryError: Unable to allocate 542. MiB
      for an array with shape (71040988, 1)` — o `groupby` do balanceamento
      materializava um array de 71 milhoes de elementos.

    Por isso o teto **nao e um numero unico**: ele e calculado a partir do
    tamanho real da base e do que a maquina aguenta, com piso e teto duros.
    Um teto fixo alto quebrava no FIAT e desperdiçava tempo no CRYPTO.

    O corte e **estratificado**: mesma proporcao de `Target` e de
    `Timeframe_Cod` da base original. Cortar sem estratificar daria ao modelo
    uma distribuicao diferente da real — ele aprenderia a hierarquia das
    classes, e o edge medido seria artefato da amostra, nao do dado.

    A ordem cronologica e preservada: `sort_values("Time")` no fim, porque o
    walk-forward treina no passado e testa na fatia seguinte.
    """
    if teto is None:
        # 150 mil foi o que passou no CRYPTO. A base do FIAT e maior, entao
        # o alvo efetivo nunca passa do teto padrao.
        teto = int(os.environ.get("XAU_MULTI_MAX_AMOSTRAS", "150000"))

    if len(base) <= teto:
        return base.sort_values("Time").reset_index(drop=True)

    # `groupby(...).apply` materializa um array do tamanho do grupo; agrupar
    # por indice ja resolve e evita o `ArrayMemoryError`. O `_estrato` vira
    # categoria, e `value_counts` sobre a categoria e o que substitui o
    # calculo de proporcao por grupo.
    base = base.assign(_estrato=(
        base["Target"].astype(int).astype(str) + "|"
        + base["Timeframe_Cod"].astype(int).astype(str)
    ))
    pesos = base["_estrato"].value_counts()
    # Descarte as fatias mais raras de fora do grupo com mais ruido de
    # amostragem: uma classe com 3 linhas nao muda o modelo e consome o teto.
    minimo = max(200, int(teto * 0.004))
    relevantes = pesos[pesos >= minimo].index
    if not len(relevantes):
        relevantes = pesos.index[:1]

    partes: list[pd.DataFrame] = []
    for estrato in relevantes:
        grupo = base[base["_estrato"] == estrato]
        n = max(1, int(round(teto * len(grupo) / len(base))))
        partes.append(grupo.sample(n=min(n, len(grupo)), random_state=42))

    return (
        pd.concat(partes, ignore_index=True)
        .drop(columns=["_estrato"])
        .sort_values("Time")
        .reset_index(drop=True)
    )


def treinar_classe(classe: str) -> dict[str, Any]:
    """Treina, valida e grava `MULTI_<CLASSE>`. Devolve o `.meta.json`."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score

    nome = nome_do_modelo_multi(classe)
    resultado: dict[str, Any] = {
        "symbol": nome,
        "class": classe,
        "model_type": "multi",
        "feature_version": FEATURE_VERSION_ESTACIONARIA,
        "feature_hash": feature_hash_estacionaria(),
        "feature_count": len(FEATURES_ESTACIONARIAS),
        "features": list(FEATURES_ESTACIONARIAS),
        "timeframes": list(TIMEFRAMES_TREINO),
        "algorithm": "RandomForestClassifier",
        "train_date": datetime.now(timezone.utc).isoformat(),
        # Declarados aqui: o MULTI destrava recurso, nunca dinheiro real.
        "live_execution": False,
        "withdrawals_enabled": False,
        "transfers_enabled": False,
    }

    bronze = _carregar(classe)
    if bronze.empty:
        resultado.update(publicable=False, publish_reason="sem dados para a classe")
        return resultado

    base = montar_base(bronze, classe)
    if base.empty or len(base) < MIN_AMOSTRAS:
        resultado.update(
            publicable=False,
            publish_reason=f"amostras insuficientes: {len(base)} < {MIN_AMOSTRAS}",
        )
        return resultado

    X = base[FEATURES_ESTACIONARIAS]
    y = base["Target"].astype(int)

    # O corte estratificado acontece ANTES dos folds, para que treino e
    # validacao usem a mesma distribuicao — cortando depois, o edge medido
    # seria de outra populacao.
    total_bruto = len(base)
    base = _balancear(base)
    X = base[FEATURES_ESTACIONARIAS]
    y = base["Target"].astype(int)

    folds = _walk_forward_estacionario(base)
    estavel, motivo = t.edge_consistente(folds, min_edge=t.PUBLICACAO_MIN_EDGE)

    # Modelo final: treina em TUDO, so DEPOIS de os folds aprovarem.
    # Publicar antes seria publicar sobre dados que ja viram validacao.
    #
    # `n_jobs=-1` era o que matava o processo. Medido: `_carregar` (3,4 s) e
    # `montar_base` (2,8 s) passavam, e o `main` morria em ~30 s com 4 MB e
    # **sem stderr** — o joblib abre um processo por nucleo, e com 466 mil
    # amostras x 22 features x 300 arvores x profundidade 12 o working set
    # estoura e o SO encerra o processo. Por isso `n_jobs` vem de
    # `XAU_AI_PRO_N_JOBS` (o mesmo env que `ai_inference.cpu_threads()` le),
    # com teto conservative, em vez de "todos os nucleos".
    n_jobs = max(1, min(int(os.environ.get("XAU_AI_PRO_N_JOBS", "2")), 8))

    modelo = RandomForestClassifier(
        n_estimators=300, max_depth=12, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=n_jobs,
    )
    modelo.fit(X, y)
    previsto = modelo.predict(X)
    acc = float(accuracy_score(y, previsto))
    f1 = float(f1_score(y, previsto, average="weighted", zero_division=0))
    palpite = 1.0 / max(int(y.nunique()), 2)
    media_folds = float(np.mean([f["edge"] for f in folds])) if folds else 0.0

    resultado["metrics"] = {
        "accuracy": acc,
        "f1_score": f1,
        "baseline": palpite,
        "edge": acc - palpite,
        "edge_media_folds": media_folds,
        "train_samples": int(len(X)),
        # Declarado porque o `.meta.json` e a fonte que a tela le: se o
        # operador ver 150.000 amostras, precisa saber que o dado original
        # tinha mais, e que a reducao foi estratificada (nao aleatoria).
        "train_samples_bruto": int(total_bruto),
        "amostra_estratificada": bool(total_bruto > len(X)),
        "estratos": int(base["Target"].nunique() * base["Timeframe_Cod"].nunique()),
        "classes": int(y.nunique()),
        "symbols": sorted(bronze["Symbol"].unique().tolist()),
        "purged": 10,
        "folds": folds,
        "edge_estavel": estavel,
    }
    resultado["min_edge"] = t.PUBLICACAO_MIN_EDGE

    MODELOS_DIR.mkdir(parents=True, exist_ok=True)
    if estavel:
        import joblib

        caminho_pkl = MODELOS_DIR / f"{nome}.pkl"
        joblib.dump(modelo, caminho_pkl)
        # Grava o SHA-256 do artefato no `.meta.json`. A inferencia confere
        # ANTES do `joblib.load`, que desserializa com pickle e executa codigo.
        # Ver `Python/integridade_modelo.py`.
        from Python.integridade_modelo import registrar as _registrar_hash

        _registrar_hash(caminho_pkl, resultado)
        resultado.update(publicable=True, publish_reason="")
    else:
        resultado.update(publicable=False, publish_reason=motivo)

    (MODELOS_DIR / f"{nome}.meta.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return resultado


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Treina o MULTI de cada classe")
    ap.add_argument("--classe", default="", choices=["", *CLASSES_COM_DADO])
    ap.add_argument("--todas", action="store_true")
    args = ap.parse_args()

    alvos = list(CLASSES_COM_DADO) if args.todas else ([args.classe] if args.classe else list(CLASSES_COM_DADO))

    print(f"dataset: {DATASET}")
    print(f"timeframes: {', '.join(TIMEFRAMES_TREINO)}")
    print("NOTA: o dataset so tem M5 e o reamostrador so AGREGA — M1 fica fora.")
    print()

    for classe in alvos:
        print(f"=== {nome_do_modelo_multi(classe)} ({classe}) ===", flush=True)
        r = treinar_classe(classe)
        m = r.get("metrics", {})
        print(f"  simbolos : {', '.join(m.get('symbols', [])) or '-'}")
        print(f"  amostras : {m.get('train_samples', 0):,}")
        print(f"  acc      : {m.get('accuracy', 0):.4f}  (palpite {m.get('baseline', 0):.4f})")
        print(f"  edge     : {m.get('edge', 0):+.4f}  | media dos folds {m.get('edge_media_folds', 0):+.4f}")
        for f in m.get("folds", []):
            print(f"    fold {f['fold']}: edge {f['edge']:+.4f} (treino {f['train']:,} / teste {f['test']:,})")
        if r["publicable"]:
            print("  PUBLICADO")
        else:
            print(f"  REPROVADO: {r['publish_reason']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
