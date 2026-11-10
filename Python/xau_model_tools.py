# -*- coding: utf-8 -*-
"""XAU_AI_PRO - ferramentas de modelo e de JSON de predicao.

Comandos:
    probe     - mostra o inventario do dataset e dos JSON de predicao
    train     - treina XAUUSD em M5/M15/H1/H4 e grava modelo + .meta.json
    validate  - valida TODOS os prediction_*.json da pasta Data
    publish   - regenera prediction_XAUUSD*.json a partir do modelo treinado

Regras de honestidade:
  * o modelo so e marcado `publicable` quando o edge medido no walk-forward
    alcanca `MIN_EDGE` e aparece em pelo menos 4 dos 5 folds;
  * modelo nao publicavel NAO vira sinal de compra/venda: o JSON sai NEUTRAL
    com o motivo escrito em `publish_reason`.

Uso:
    python xau_model_tools.py validate
    python xau_model_tools.py train
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

# ============================================================
# CAMINHOS
# ============================================================

HERE = Path(__file__).resolve().parent
FILES_DIR = HERE.parent.parent                 # ...\MQL5\Files
DATA_DIR = FILES_DIR / "Data"
MODELS_DIR = HERE / "models"
REPORT_PATH = DATA_DIR / "json_validation_report.json"

DATASET_PRIMARY = DATA_DIR / "dataset_mt5_20261101.csv"
DATASET_FALLBACK = DATA_DIR / "dataset.csv"

SYMBOL = "XAUUSD"
TIMEFRAMES = ("M5", "M15", "H1", "H4")
MIN_EDGE = 0.02
# A acuracia contra a classe maioritaria pune o modelo que reconhece a classe
# minoritaria: no ouro o periodo tem deriva de alta, entao "apostar sempre na
# alta" acerta 52-58% sem nenhum sinal. O gate passa a medir DISCRIMINACAO
# (balanced accuracy, que e a media dos dois recalls) e AUC. A acuracia bruta
# continua medida e publicada como referencia, mas nao decide sozinha.
MIN_EDGE_BAL = 0.02
MIN_AUC = 0.52
LOOKAHEAD = {"M5": 12, "M15": 8, "H1": 6, "H4": 4}
CLASS_THRESHOLD = 0.5        # em unidades de ATR

VALID_SIGNALS = {"BUY", "SELL", "NEUTRAL", "STRONG_BUY", "STRONG_SELL"}


# ============================================================
# LEITURA DO DATASET
# ============================================================

def _decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig", errors="replace")
    if raw.count(b"\x00") > max(16, len(raw) // 4):
        return raw.decode("utf-16-le", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def load_bars(path: Path, symbol: str = SYMBOL, limit: int | None = None) -> pd.DataFrame:
    """Le o CSV do MT5 e devolve OHLCV do simbolo pedido, ordenado por tempo."""
    raw = path.read_bytes()
    text = _decode(raw).replace("\r\n", "\n").replace("\r", "\n")

    times: list[datetime] = []
    o: list[float] = []
    h: list[float] = []
    l: list[float] = []  # noqa: E741
    c: list[float] = []
    v: list[float] = []
    sp: list[float] = []

    target = symbol.upper()
    bad = 0

    for line in text.split("\n"):
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 7:
            continue
        if parts[1].strip().upper() != target:
            continue
        stamp = parts[0].strip()
        # linhas corrompidas tipo "20262026.11.03 04:00:00"
        if len(stamp) < 19:
            bad += 1
            continue
        stamp = stamp[-19:]
        try:
            dt = datetime.strptime(stamp, "%Y.%m.%d %H:%M:%S")
            oo = float(parts[2])
            hh = float(parts[3])
            ll = float(parts[4])
            cc = float(parts[5])
        except ValueError:
            bad += 1
            continue
        if not (oo > 0 and hh > 0 and ll > 0 and cc > 0):
            bad += 1
            continue
        times.append(dt)
        o.append(oo)
        h.append(hh)
        l.append(ll)
        c.append(cc)
        try:
            v.append(float(parts[6]))
        except ValueError:
            v.append(0.0)
        try:
            sp.append(float(parts[7]))
        except (ValueError, IndexError):
            sp.append(0.0)

    df = pd.DataFrame(
        {"time": times, "open": o, "high": h, "low": l, "close": c, "tickvol": v, "spread": sp}
    )
    df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    if limit is not None and len(df) > limit:
        df = df.tail(limit).reset_index(drop=True)
    df.attrs["bad_rows"] = bad
    return df


def resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe == "M5":
        return df.copy()
    rule = {"M15": "15min", "H1": "1h", "H4": "4h"}[timeframe]
    idx = pd.DatetimeIndex(df["time"])
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "tickvol" in df.columns:
        agg["tickvol"] = "sum"
    if "spread" in df.columns:
        agg["spread"] = "mean"
    out = df.set_index(idx).resample(rule, label="left", closed="left").agg(agg)
    for extra in ("tickvol", "spread"):
        if extra not in out.columns:
            out[extra] = 0.0
    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index().rename(columns={"index": "time"})
    return out.reset_index(drop=True)


# ============================================================
# INDICADORES (implementados aqui para nao depender de pacote)
# ============================================================

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    au = up.ewm(alpha=1.0 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1.0 / n, adjust=False).mean()
    rs = au / ad.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1
    ).max(axis=1)
    atr_n = tr.ewm(alpha=1.0 / n, adjust=False).mean().replace(0.0, np.nan)
    pdi = 100.0 * pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / n, adjust=False).mean() / atr_n
    mdi = 100.0 * pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / n, adjust=False).mean() / atr_n
    dx = (abs(pdi - mdi) / (pdi + mdi).replace(0.0, np.nan)) * 100.0
    return dx.ewm(alpha=1.0 / n, adjust=False).mean().fillna(0.0)


FEATURES = [
    "ret1", "ret3", "ret5", "ret10", "ret20",
    "ema20_rel", "ema50_rel", "ema200_rel", "ema20_slope", "ema50_slope",
    "rsi14", "rsi_slope",
    "atr_pct", "atr_z",
    "adx14", "pdi_minus_mdi",
    "bbw", "close_z20",
    "stoch14",
    "body_ratio", "upper_wick", "lower_wick", "range_pct",
    "vol_z", "vol_ratio",
    "ret5_std", "gap_pct",
    "hour_sin", "hour_cos", "dow",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    cl = d["close"]

    d["ret1"] = cl.pct_change()
    for n in (3, 5, 10, 20):
        d[f"ret{n}"] = cl.pct_change(n)

    for n in (20, 50, 200):
        d[f"ema{n}_rel"] = cl / ema(cl, n) - 1.0
    d["ema20_slope"] = ema(cl, 20).pct_change(3)
    d["ema50_slope"] = ema(cl, 50).pct_change(3)

    r = rsi(cl, 14)
    d["rsi14"] = r
    d["rsi_slope"] = r.diff(2)

    a = atr(d, 14)
    d["atr_pct"] = a / cl
    d["atr_z"] = (d["atr_pct"] - d["atr_pct"].rolling(50).mean()) / (
        d["atr_pct"].rolling(50).std().replace(0.0, np.nan)
    )

    d["adx14"] = adx(d, 14)
    up = d["high"].diff()
    dn = -d["low"].diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a_n = a.replace(0.0, np.nan)
    pdi = 100.0 * pd.Series(plus_dm, index=d.index).ewm(alpha=1 / 14, adjust=False).mean() / a_n
    mdi = 100.0 * pd.Series(minus_dm, index=d.index).ewm(alpha=1 / 14, adjust=False).mean() / a_n
    d["pdi_minus_mdi"] = (pdi - mdi).fillna(0.0)

    m20 = cl.rolling(20).mean()
    s20 = cl.rolling(20).std()
    d["bbw"] = (4.0 * s20 / m20).fillna(0.0)
    d["close_z20"] = ((cl - m20) / s20.replace(0.0, np.nan)).fillna(0.0)

    ll = d["low"].rolling(14).min()
    hh = d["high"].rolling(14).max()
    d["stoch14"] = (100.0 * (cl - ll) / (hh - ll).replace(0.0, np.nan)).fillna(50.0)

    rng = (d["high"] - d["low"]).replace(0.0, np.nan)
    d["body_ratio"] = ((cl - d["open"]) / rng).fillna(0.0)
    d["upper_wick"] = ((d["high"] - cl.combine(d["open"], max)) / rng).fillna(0.0)
    d["lower_wick"] = ((cl.combine(d["open"], min) - d["low"]) / rng).fillna(0.0)
    d["range_pct"] = (d["high"] - d["low"]) / cl

    vm = d["tickvol"].rolling(20).mean()
    vs = d["tickvol"].rolling(20).std()
    d["vol_z"] = ((d["tickvol"] - vm) / vs.replace(0.0, np.nan)).fillna(0.0)
    d["vol_ratio"] = (d["tickvol"] / vm.replace(0.0, np.nan)).fillna(1.0)

    d["ret5_std"] = d["ret1"].rolling(20).std()
    d["gap_pct"] = (d["open"] - cl.shift(1)) / cl.shift(1)

    hours = pd.DatetimeIndex(d["time"]).hour + pd.DatetimeIndex(d["time"]).minute / 60.0
    d["hour_sin"] = np.sin(2 * math.pi * hours / 24.0)
    d["hour_cos"] = np.cos(2 * math.pi * hours / 24.0)
    # v3.1: day_of_week (dayofweek esta deprecado no pandas 4 e gera warning)
    d["dow"] = pd.DatetimeIndex(d["time"]).day_of_week.astype(float)

    return d


def build_target(df: pd.DataFrame, lookahead: int) -> pd.Series:
    """Alvo BINARIO de direcao, com zona morta em ATR.

    A v3 usava 3 classes (sobe/neutro/desce) e a classe NEUTRO ficava com 39-42%
    das amostras. O RandomForest ficou ABAIXO do palpite majoritario em todos os
    timeframes (edge -0.03 a -0.06): prever "nao vai a lado nenhum" nao e sinal
    operacional, o EA compra ou vende. Aqui o alvo e apenas o LADO do movimento
    que superou CLASS_THRESHOLD ATR; o que fica dentro da zona morta e descartado
    em vez de virar uma terceira classe dominante.
    """
    fwd = df["close"].shift(-lookahead) / df["close"] - 1.0
    vol = df["atr_pct"].rolling(50).mean().shift(1)
    norm = fwd / vol.replace(0.0, np.nan)
    target = np.where(
        norm >= CLASS_THRESHOLD, 1.0,
        np.where(norm <= -CLASS_THRESHOLD, 0.0, np.nan),
    )
    out = pd.Series(target, index=df.index, dtype="float64")
    out[fwd.isna() | vol.isna() | norm.isna()] = np.nan
    return out


# ============================================================
# MODELOS CANDIDATOS
# ============================================================

MODEL_CANDIDATES = ("rf", "hgb")

MODEL_LABEL = {
    "rf": "RandomForestClassifier",
    "hgb": "HistGradientBoostingClassifier",
}


def make_model(kind: str, extra: dict[str, Any] | None = None):
    """Fabrica o modelo candidato. O EA le o nome em `algorithm`/`model`.

    "hgb" (gradient boosting) costuma bater o RandomForest em serie financeira
    com muitos atributos correlacionados, porque faz regularizacao por passo em
    vez de sortear arvores independentes. Os dois sao medidos no MESMO
    walk-forward e so o melhor segue para a publicacao.
    """
    extra = extra or {}
    if kind == "hgb":
        from sklearn.ensemble import HistGradientBoostingClassifier

        params = {
            "max_iter": 300,
            "learning_rate": 0.05,
            "max_leaf_nodes": 15,
            "min_samples_leaf": 120,
            "l2_regularization": 1.0,
            "early_stopping": True,
            "validation_fraction": 0.15,
            "n_iter_no_change": 30,
            "random_state": 42,
        }
        params.update(extra)
        return HistGradientBoostingClassifier(**params)

    params = {
        "n_estimators": 500,
        "max_depth": 6,
        "min_samples_leaf": 120,
        "max_features": "sqrt",
        "class_weight": "balanced_subsample",
        "random_state": 42,
        "n_jobs": -1,
    }
    params.update(extra)
    return RandomForestClassifier(**params)


# ============================================================
# TREINO COM WALK-FORWARD PURGADO
# ============================================================

@dataclass
class FoldResult:
    fold: int
    accuracy: float
    baseline: float
    edge: float
    f1: float
    trade_accuracy: float
    trade_share: float
    # v4: discriminacao, nao acerto bruto. auc=0.5 e bal_acc=0.5 significam
    # "moeda ao ar"; acc_edge e a diferenca contra a classe maioritaria, so
    # informativa.
    auc: float = 0.5
    bal_acc: float = 0.5
    acc_edge: float = 0.0


def walk_forward(
    X: np.ndarray,
    y: np.ndarray,
    n_folds: int = 5,
    purge: int = 12,
    params: dict[str, Any] | None = None,
    kind: str = "rf",
) -> tuple[list[FoldResult], Any | None]:
    n = len(X)
    start = int(n * 0.4)
    if n - start < n_folds * 50:
        return [], None

    block = (n - start) // n_folds
    folds: list[FoldResult] = []
    last_model: Any | None = None

    base_params = dict(params) if params else {}

    for k in range(n_folds):
        test_lo = start + k * block
        test_hi = n if k == n_folds - 1 else test_lo + block
        train_hi = test_lo - purge
        if train_hi < 300:
            continue

        X_tr, y_tr = X[:train_hi], y[:train_hi]
        X_te, y_te = X[test_lo:test_hi], y[test_lo:test_hi]
        model = make_model(kind, base_params)
        model.fit(X_tr, y_tr)

        from sklearn.metrics import balanced_accuracy_score, roc_auc_score

        pred = model.predict(X_te)
        acc = float(accuracy_score(y_te, pred))
        bal_acc = float(balanced_accuracy_score(y_te, pred))
        f1 = float(f1_score(y_te, pred, average="weighted"))

        values, counts = np.unique(y_te, return_counts=True)
        baseline = float(counts.max() / counts.sum())

        proba_te = model.predict_proba(X_te)
        classes_te = list(model.classes_)
        up_idx = classes_te.index(1) if 1 in classes_te else -1
        try:
            auc = float(roc_auc_score(y_te, proba_te[:, up_idx])) if up_idx >= 0 and len(values) > 1 else 0.5
        except ValueError:
            auc = 0.5

        # "trade" = barra em que o modelo tem conviccao. O alvo agora e binario
        # (0/1), por isso nao existe classe NEUTRO para filtrar; mede-se o acerto
        # no subconjunto em que o EA realmente agiria.
        conf = model.predict_proba(X_te).max(axis=1)
        mask = conf >= 0.55
        trade_share = float(mask.mean()) if len(mask) else 0.0
        trade_acc = float(accuracy_score(y_te[mask], pred[mask])) if mask.sum() >= 20 else float("nan")

        folds.append(
            FoldResult(
                fold=k + 1,
                accuracy=acc,
                baseline=baseline,
                edge=bal_acc - 0.5,
                f1=f1,
                trade_accuracy=trade_acc,
                trade_share=trade_share,
                auc=auc,
                bal_acc=bal_acc,
                acc_edge=acc - baseline,
            )
        )
        last_model = model

    return folds, last_model


def train_timeframe(df_tf: pd.DataFrame, timeframe: str) -> dict[str, Any]:
    lookahead = LOOKAHEAD[timeframe]
    feats = build_features(df_tf)
    feats["target"] = build_target(feats, lookahead)
    data = feats.dropna(subset=FEATURES + ["target"]).reset_index(drop=True)

    if len(data) < 600:
        return {"timeframe": timeframe, "status": "error", "error": f"amostras insuficientes ({len(data)})"}

    X = data[FEATURES].to_numpy(dtype=np.float64)
    y = data["target"].to_numpy(dtype=int)

    purge = lookahead + 3
    trials: dict[str, list[FoldResult]] = {}
    for kind in MODEL_CANDIDATES:
        got, _ = walk_forward(X, y, n_folds=5, purge=purge, kind=kind)
        if got and len(got) >= 5:
            trials[kind] = got
    if not trials:
        return {"timeframe": timeframe, "status": "error", "error": "walk-forward sem folds validos"}

    def _edge_of(fs: list[FoldResult]) -> float:
        return float(np.mean([f.edge for f in fs]))

    # Selecao e medicao em folds DIFERENTES: o candidato e escolhido pelas 2
    # primeiras folds e o edge publicado/medido vem das 3 ultimas. Escolher e
    # medir nas mesmas folds e o "teste verde que esconde defeito" deste projeto.
    sel_kind = max(trials, key=lambda k: _edge_of(trials[k][:2]))
    folds = trials[sel_kind]
    holdout = folds[2:] if len(folds) > 2 else folds
    edge_all = _edge_of(folds)
    edge = _edge_of(holdout)                  # balanced accuracy - 0.5
    acc = float(np.mean([f.accuracy for f in folds]))
    baseline = float(np.mean([f.baseline for f in folds]))
    acc_edge = acc - baseline
    bal_acc = float(np.mean([f.bal_acc for f in folds]))
    auc = float(np.mean([f.auc for f in folds]))
    auc_holdout = float(np.mean([f.auc for f in holdout]))
    edges = [f.edge for f in folds]
    positive = sum(1 for e in edges if e > 0)
    stable = positive >= 4
    trade_acc = float(np.nanmean([f.trade_accuracy for f in folds]))
    min_edge_obs = min(f.edge for f in holdout)

    publicable = bool(edge >= MIN_EDGE_BAL and auc_holdout >= MIN_AUC and stable and edge_all > 0.0)

    if publicable:
        reason = (f"balanced edge {edge:+.4f} nas folds de medicao >= {MIN_EDGE_BAL:.4f}, "
                  f"AUC {auc_holdout:.4f} >= {MIN_AUC:.4f} e {positive}/5 folds positivos")
    else:
        motivo = []
        if edge < MIN_EDGE_BAL:
            motivo.append(f"balanced edge {edge:+.4f} abaixo do minimo {MIN_EDGE_BAL:.4f}")
        if auc_holdout < MIN_AUC:
            motivo.append(f"AUC {auc_holdout:.4f} abaixo do minimo {MIN_AUC:.4f}")
        if not stable:
            motivo.append(f"apenas {positive}/5 folds positivos (minimo 4)")
        if edge_all <= 0.0:
            motivo.append(f"balanced edge medio global {edge_all:+.4f} <= 0")
        reason = "; ".join(motivo)

    # modelo final treinado em toda a serie (mesmos hiperparametros)
    final = make_model(sel_kind)
    train_hi = len(X) - purge
    final.fit(X[:train_hi], y[:train_hi])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"{SYMBOL}_{timeframe}.pkl"
    dump(final, model_path)

    # previsao da ultima barra fechada
    last_row = data.iloc[[-1]]
    # Alvo binario: 0 = desce, 1 = sobe. Aqui o indice 1 NAO e "neutro"
    # (isso era a v3 de 3 classes); trocar os dois converteria compra em neutro
    # em silencio, que e o tipo de defeito que so aparece a operar.
    proba = final.predict_proba(last_row[FEATURES].to_numpy(dtype=np.float64))[0]
    classes = list(final.classes_)
    p_sell = float(proba[classes.index(0)]) if 0 in classes else 0.0
    p_buy = float(proba[classes.index(1)]) if 1 in classes else 0.0
    p_neutral = 0.0

    meta = {
        "symbol": SYMBOL,
        "timeframe": timeframe,
        "feature_version": "XAU-30F-v4",
        "feature_hash": str(abs(hash(tuple(FEATURES))) % (10**16)),
        "feature_count": len(FEATURES),
        "algorithm": MODEL_LABEL[sel_kind],
        "model_kind": sel_kind,
        "label": f"direcao binaria do retorno em {lookahead} barras acima de {CLASS_THRESHOLD} ATR",
        "metrics": {
            "accuracy": acc,
            "baseline": baseline,
            "edge": edge,
            "edge_balanced": edge,
            "balanced_accuracy": bal_acc,
            "auc": auc,
            "auc_holdout": auc_holdout,
            "acc_edge": acc_edge,
            "f1_score": float(np.mean([f.f1 for f in folds])),
            "trade_accuracy": trade_acc,
            "trade_share": float(np.mean([f.trade_share for f in folds])),
            "min_edge_fold": min_edge_obs,
            "edge_all_folds": edge_all,
            "selection_kind": sel_kind,
            "holdout_folds": [f.fold for f in holdout],
            "folds": [
                {
                    "fold": f.fold,
                    "accuracy": round(f.accuracy, 4),
                    "baseline": round(f.baseline, 4),
                    "edge": round(f.edge, 4),
                    "auc": round(f.auc, 4),
                    "bal_acc": round(f.bal_acc, 4),
                    "acc_edge": round(f.acc_edge, 4),
                    "f1": round(f.f1, 4),
                    "trade_accuracy": None if math.isnan(f.trade_accuracy) else round(f.trade_accuracy, 4),
                }
                for f in folds
            ],
            "positive_folds": positive,
            "folds_total": len(folds),
        },
        "edge_estavel": stable,
        "publicable": publicable,
        "publish_reason": reason,
        "min_edge": MIN_EDGE,
        "train_samples": int(train_hi),
        "test_samples": int(len(X) - train_hi),
        "purged": lookahead + 3,
        "train_date": datetime.now(timezone.utc).isoformat(),
        "dataset": DATASET_PRIMARY.name,
        "bars": int(len(df_tf)),
        "price": float(last_row["close"].iloc[0]),
        "atr": float(last_row["atr_pct"].iloc[0] * last_row["close"].iloc[0]),
        "proba": {"sell": round(p_sell, 4), "neutral": round(p_neutral, 4), "buy": round(p_buy, 4)},
        "last_bar": str(last_row["time"].iloc[0]),
    }
    meta_path = model_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"timeframe": timeframe, "status": "ok", "edge": edge, "accuracy": acc,
            "baseline": baseline, "bal_acc": bal_acc, "auc": auc,
            "stable": stable, "publicable": publicable,
            "reason": reason, "kind": sel_kind, "edge_all": edge_all,
            "positive": positive}


# ============================================================
# JSON DE PREDICAO (contrato lido pelo EA)
# ============================================================

def build_prediction(tf: str, meta: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    price = float(meta["price"])
    atr = float(meta["atr"]) or max(price * 0.001, 0.01)
    proba = meta["proba"]
    conf = max(proba["buy"], proba["sell"], proba["neutral"]) * 100.0

    if meta["publicable"]:
        signal = "BUY" if proba["buy"] > max(proba["sell"], proba["neutral"]) else (
            "SELL" if proba["sell"] > max(proba["buy"], proba["neutral"]) else "NEUTRAL"
        )
    else:
        signal = "NEUTRAL"   # modelo sem edge nao autoriza direcao

    score = 50.0 + (proba["buy"] - proba["sell"]) * 50.0
    if not meta["publicable"]:
        score = 50.0 + (proba["buy"] - proba["sell"]) * 10.0   # encolhe sem edge

    buy = round(proba["buy"] * 100.0, 2)
    sell = round(proba["sell"] * 100.0, 2)

    sl = round(price - atr * 1.5, 2)
    tp = round(price + atr * 3.0, 2)

    return {
        "symbol": SYMBOL,
        "category": "Metals",
        "signal": signal,
        "confidence": round(conf, 2),
        "score": round(score, 2),
        "buy": buy,
        "sell": sell,
        "risk": "LOW" if conf >= 85 else "MEDIUM" if conf >= 70 else "HIGH" if conf >= 55 else "VERY_HIGH",
        "model": "random_forest_xau_v3",
        "model_version": f"xau-{tf}-v3",
        "model_id": f"RF_{SYMBOL}_{tf}",
        "feature_hash": meta["feature_hash"],
        "feature_count": meta["feature_count"],
        "inference_ms": 0,
        "algorithm": meta["algorithm"],
        "train_date": meta["train_date"][:10],
        "dataset_version": meta["dataset"],
        "metrics": json.dumps(
            {
                "accuracy": round(meta["metrics"]["accuracy"], 4),
                "baseline": round(meta["metrics"]["baseline"], 4),
                "edge": round(meta["metrics"]["edge"], 4),
                "positive_folds": meta["metrics"]["positive_folds"],
                "publicable": meta["publicable"],
                "reason": meta["publish_reason"],
            },
            ensure_ascii=False,
        ),
        "timeframe": tf,
        "timeframes_used": [tf],
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "price": price,
        "atr": round(atr, 4),
        "spread": int(prior.get("spread", 0)) if prior else 0,
        "volume": int(prior.get("volume", 0)) if prior else 0,
        "sl": sl,
        "tp": tp,
        "publicable": meta["publicable"],
        "publish_reason": meta["publish_reason"],
    }


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


# ============================================================
# VALIDACAO DOS JSON
# ============================================================

ALIASES = {"GOLD": SYMBOL, "XAU": SYMBOL}


def normalize(name: str) -> str:
    """Normaliza o nome do simbolo do broker.

    O sufixo so e removido no FIM do nome (v1.2.95 P1.83b): procurar "M" ou "C"
    em qualquer posicao transformava USDCAD em USD, e o EA recebia recusa com
    motivo errado. Os aliases so valem para o nome INTEIRO ja sem sufixo.
    """
    up = name.upper().strip()
    for suf in ("#", ".PRO", "_I", "C", "M"):
        if up.endswith(suf) and len(up) > len(suf) + 3:
            up = up[: -len(suf)]
            break
    return ALIASES.get(up, up)


def validate_all() -> dict[str, Any]:
    files = sorted(DATA_DIR.glob("prediction*.json"))
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    ok = 0
    now = datetime.now(timezone.utc)

    for path in files:
        rel = path.name
        data = read_json(path)
        if data is None:
            errors.append({"file": rel, "error": "JSON invalido (parse falhou)"})
            continue

        problems: list[str] = []

        sym = str(data.get("symbol", "")).strip()
        if not sym:
            problems.append("sem chave 'symbol'")
        else:
            stem = rel[len("prediction_"):-len(".json")] if rel.startswith("prediction_") else ""
            if rel == "prediction.json":
                pass
            else:
                for tf in ("_H1", "_M15", "_M5", "_H4"):
                    if stem.upper().endswith(tf):
                        stem = stem[: -len(tf)]
                        break
                if stem and normalize(stem) != normalize(sym):
                    problems.append(f"simbolo do ficheiro ({stem}) != 'symbol' ({sym})")

        sig = str(data.get("signal", "")).upper()
        if not sig:
            problems.append("sem chave 'signal'")
        elif sig not in VALID_SIGNALS:
            problems.append(f"signal invalido: {sig}")

        conf = data.get("confidence", data.get("score"))
        if conf is None:
            problems.append("sem 'confidence' nem 'score'")
        else:
            try:
                cf = float(conf)
                if not (0.0 <= cf <= 100.0):
                    problems.append(f"confidence fora de 0..100: {cf}")
            except (TypeError, ValueError):
                problems.append(f"confidence nao numerico: {conf!r}")

        for key in ("buy", "sell"):
            if key in data:
                try:
                    val = float(data[key])
                    if not (0.0 <= val <= 100.0):
                        problems.append(f"{key} fora de 0..100: {val}")
                except (TypeError, ValueError):
                    problems.append(f"{key} nao numerico")

        price = data.get("price")
        if price is None:
            problems.append("sem 'price'")
        else:
            try:
                if float(price) <= 0:
                    problems.append("price <= 0")
            except (TypeError, ValueError):
                problems.append("price nao numerico")

        ts = data.get("timestamp_utc") or data.get("time")
        if not ts:
            warnings.append({"file": rel, "warning": "sem timestamp_utc (EA nao consegue medir idade)"})
        else:
            parsed = None
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    parsed = datetime.strptime(str(ts)[:26], fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            if parsed is None:
                warnings.append({"file": rel, "warning": f"timestamp nao reconhecido: {ts}"})
            elif (now - parsed).total_seconds() > 86400:
                warnings.append({"file": rel, "warning": f"predicao com mais de 24h ({ts})"})

        if problems:
            errors.append({"file": rel, "error": "; ".join(problems)})
        else:
            ok += 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_dir": str(DATA_DIR),
        "files_total": len(files),
        "files_ok": ok,
        "errors": errors,
        "warnings": warnings,
        "exit_code": 0 if not errors else 1,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


# ============================================================
# COMANDOS
# ============================================================

def _bars_by_symbol(path: Path) -> dict[str, pd.DataFrame]:
    """Le o CSV uma vez e devolve {simbolo: DataFrame(time,open,high,low,close)}.

    O dataset tem linhas de largura 4/26/29 e timestamps corrompidos
    ("20262026.11.03 04:00:00"); a linha inteira e descartada em vez de
    remendar o preco, porque um preco remendado vira sinal errado.
    """
    text = _decode(path.read_bytes())
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines:
        return {}
    head = [c.strip().lower() for c in lines[0].split(",")]
    header = True
    try:
        i_t = head.index("time")
        i_s = head.index("symbol")
        i_o = head.index("open")
        i_h = head.index("high")
        i_l = head.index("low")
        i_c = head.index("close")
    except ValueError:
        # Os datasets do MT5 nao tem cabecalho: colunas posicionais
        # 0=time 1=symbol 2=open 3=high 4=low 5=close 6=tickvol 7=spread.
        header = False
        i_t, i_s, i_o, i_h, i_l, i_c = 0, 1, 2, 3, 4, 5
    need = max(i_t, i_s, i_o, i_h, i_l, i_c)
    rows: dict[str, list[tuple[Any, float, float, float, float]]] = {}
    for ln in (lines[1:] if header else lines):
        if not ln.strip():
            continue
        p = ln.split(",")
        if len(p) <= need:
            continue
        try:
            ts = pd.to_datetime(p[i_t].strip()[-19:], format="%Y.%m.%d %H:%M:%S")
            o = float(p[i_o]); h = float(p[i_h]); l = float(p[i_l]); c = float(p[i_c])
        except (ValueError, TypeError):
            continue
        if not (o > 0 and h > 0 and l > 0 and c > 0):
            continue
        rows.setdefault(p[i_s].strip().upper(), []).append((ts, o, h, l, c))
    out: dict[str, pd.DataFrame] = {}
    for sym, rs in rows.items():
        df = pd.DataFrame(rs, columns=["time", "open", "high", "low", "close"])
        out[sym] = df.sort_values("time").reset_index(drop=True)
    return out


def fallback_payload(sym: str, df: pd.DataFrame, tf: str) -> dict[str, Any]:
    """Payload de FALLBACK (sem modelo treinado) para um simbolo/timeframe.

    Nao inventa edge: o sinal sai NEUTRAL e a confianca fica presa entre 50 e 56.
    O momentum so alimenta `buy`/`sell` para o operador ver a direcao do preco,
    e o campo `model` diz explicitamente que isto NAO e o modelo treinado.
    """
    close = df["close"]
    price = float(close.iloc[-1])
    a = atr(df, 14)
    atr_v = float(a.iloc[-1]) if len(a) and not math.isnan(float(a.iloc[-1])) else price * 0.001
    ret5 = price / float(close.iloc[-6]) - 1.0 if len(close) > 6 else 0.0
    ret20 = price / float(close.iloc[-21]) - 1.0 if len(close) > 21 else 0.0
    mom = ret20 * 0.6 + ret5 * 0.4
    bias = max(-0.06, min(0.06, mom * 8.0))
    buy = round((0.5 + bias) * 100.0, 2)
    sell = round(100.0 - buy, 2)
    conf = round(min(56.0, 50.0 + abs(bias) * 100.0), 2)
    last_time = df["time"].iloc[-1]
    return {
        "symbol": sym,
        "category": "Metals" if sym == SYMBOL else "FX",
        "signal": "NEUTRAL",
        "confidence": conf,
        "score": conf,
        "buy": buy,
        "sell": sell,
        "risk": "HIGH",
        "model": "dataset_momentum_fallback_v1",
        "model_version": "fallback-1.1",
        "model_id": f"fallback_{sym}_{tf}",
        "feature_hash": "momentum20+momentum5+atr14+sigma30",
        "inference_ms": 0,
        "algorithm": "deterministic_momentum",
        "train_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "dataset_version": DATASET_PRIMARY.name if DATASET_PRIMARY.exists() else DATASET_FALLBACK.name,
        "metrics": json.dumps(
            {"note": "fallback local; nao e o modelo treinado", "edge": 0.0},
            ensure_ascii=False,
        ),
        "timeframe": tf,
        "timeframes_used": [tf],
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "price": round(price, 5),
        "atr": round(atr_v, 5),
        "spread": 0,
        "volume": 0,
        "sl": round(price - atr_v * 1.5, 5),
        "tp": round(price + atr_v * 3.0, 5),
        "publicable": False,
        "publish_reason": "fallback deterministico; sem modelo treinado para este simbolo",
        "_derived": {
            "bars": int(len(df)),
            "last_bar": str(last_time),
            "ret5_pct": round(ret5 * 100.0, 4),
            "ret20_pct": round(ret20 * 100.0, 4),
        },
    }


def cmd_regen() -> None:
    """Regenera todo prediction_<SIM>.json que tenha dado real no dataset."""
    src = DATASET_PRIMARY if DATASET_PRIMARY.exists() else DATASET_FALLBACK
    by_sym = _bars_by_symbol(src)
    if not by_sym:
        raise SystemExit(f"[regen] nenhum simbolo lido de {src}")
    canon = {normalize(s): s for s in by_sym}
    print(f"[regen] dataset={src.name} simbolos={len(by_sym)}")

    written, skipped = [], []
    for path in sorted(DATA_DIR.glob("prediction*.json")):
        if path.name == "prediction.json":
            skipped.append((path.name, "contrato legado, sem simbolo no nome"))
            continue
        stem = path.name[len("prediction_"): -len(".json")]
        base, tf = stem, "M5"
        for cand in ("_M15", "_M5", "_H1", "_H4"):
            if base.upper().endswith(cand):
                base, tf = base[: -len(cand)], cand[1:]
                break
        dsym = canon.get(normalize(base))
        if not dsym:
            skipped.append((path.name, "simbolo ausente no dataset"))
            continue
        df = by_sym[dsym]
        if tf != "M5":
            df = resample(df, tf)
        if len(df) < 30:
            skipped.append((path.name, f"barras insuficientes ({len(df)})"))
            continue
        payload = fallback_payload(dsym, df, tf)
        path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
        written.append(path.name)

    for name in written:
        print(f"[regen] escrito {name}")
    for name, why in skipped:
        print(f"[regen] PULADO {name}: {why}")
    print(f"[regen] total escrito={len(written)} pulado={len(skipped)}")


def cmd_probe() -> None:
    src = DATASET_PRIMARY if DATASET_PRIMARY.exists() else DATASET_FALLBACK
    df = load_bars(src)
    print(f"[probe] dataset={src.name} bars={len(df)} bad={df.attrs.get('bad_rows')}")
    if len(df):
        print(f"[probe] range {df['time'].iloc[0]} -> {df['time'].iloc[-1]}")
        print(f"[probe] close {df['close'].iloc[-1]}")
    for tf in TIMEFRAMES:
        d = resample(df, tf)
        print(f"[probe] {tf}: {len(d)} barras")
    print(f"[probe] JSON de predicao em {DATA_DIR}: {len(list(DATA_DIR.glob('prediction*.json')))}")


def cmd_train() -> None:
    src = DATASET_PRIMARY if DATASET_PRIMARY.exists() else DATASET_FALLBACK
    df = load_bars(src)
    if len(df) < 1000:
        raise SystemExit(f"dataset insuficiente: {len(df)} barras de {SYMBOL} em {src}")

    print(f"[train] {SYMBOL} | {len(df)} barras M5 | {df['time'].iloc[0]} -> {df['time'].iloc[-1]}")
    for tf in TIMEFRAMES:
        tf_df = resample(df, tf)
        res = train_timeframe(tf_df, tf)
        if res.get("status") == "ok":
            print(
                f"[train] {tf}: acc={res['accuracy']:.4f} base={res['baseline']:.4f} "
                f"bal_acc={res['bal_acc']:.4f} auc={res['auc']:.4f} "
                f"edge={res['edge']:+.4f} ({res['kind']}) estavel={res['stable']} "
                f"publicavel={res['publicable']} | {res['reason']}"
            )
        else:
            print(f"[train] {tf}: ERRO {res.get('error')}")


def cmd_publish() -> None:
    prior = read_json(DATA_DIR / f"prediction_{SYMBOL}.json") or {}
    metas: dict[str, dict[str, Any]] = {}
    for tf in TIMEFRAMES:
        meta_path = MODELS_DIR / f"{SYMBOL}_{tf}.meta.json"
        if not meta_path.exists():
            print(f"[publish] {tf}: meta em falta ({meta_path.name})")
            continue
        meta = read_json(meta_path)
        if not meta:
            print(f"[publish] {tf}: meta ilegivel")
            continue
        metas[tf] = meta

    if not metas:
        raise SystemExit("[publish] nenhum modelo treinado; rode 'train' primeiro")

    written = []
    per_tf: dict[str, dict[str, Any]] = {}
    for tf, meta in metas.items():
        payload = build_prediction(tf, meta, prior)
        out = DATA_DIR / f"prediction_{SYMBOL}_{tf}.json"
        out.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
        per_symbol = DATA_DIR / f"prediction_{SYMBOL}.json"
        written.append(out.name)
        per_tf[tf] = payload

    # consolidado: usa o timeframe publicavel de maior edge; senao o H1
    publicable = {tf: p for tf, p in per_tf.items() if metas[tf]["publicable"]}
    if publicable:
        best_tf = max(publicable, key=lambda t: metas[t]["metrics"]["edge"])
        signal = publicable[best_tf]["signal"]
        reason = f"publicado por {best_tf}: {metas[best_tf]['publish_reason']}"
        chosen = dict(publicable[best_tf])
    else:
        best_tf = "H1" if "H1" in per_tf else sorted(per_tf)[0]
        chosen = dict(per_tf[best_tf])
        signal = "NEUTRAL"
        reason = "; ".join(f"{tf}: {metas[tf]['publish_reason']}" for tf in metas)

    chosen.update(
        {
            "signal": signal,
            "model": "random_forest_xau_v3",
            "model_version": f"xau-multi-v3 ({'+'.join(sorted(per_tf))})",
            "model_id": f"RF_{SYMBOL}_ENSEMBLE",
            "timeframes_used": sorted(per_tf),
            "timeframe": best_tf,
            "publicable": bool(publicable),
            "publish_reason": reason,
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        }
    )
    out = DATA_DIR / f"prediction_{SYMBOL}.json"
    out.write_text(json.dumps(chosen, indent=4, ensure_ascii=False), encoding="utf-8")
    written.append(out.name)

    for name in written:
        print(f"[publish] escrito {name}")
    print(f"[publish] sinal consolidado={signal} | {reason}")


def cmd_validate() -> None:
    report = validate_all()
    print(f"[validate] ficheiros={report['files_total']} ok={report['files_ok']} "
          f"erros={len(report['errors'])} avisos={len(report['warnings'])}")
    for item in report["errors"]:
        print(f"  ERRO  {item['file']}: {item['error']}")
    for item in report["warnings"][:20]:
        print(f"  AVISO {item['file']}: {item['warning']}")
    print(f"[validate] relatorio: {REPORT_PATH}")
    if report["errors"]:
        sys.exit(1)


def cmd_stamp() -> None:
    """Carimba timestamp_utc nos JSON antigos que nao o tem.

    O EA mede a idade da predicao por timestamp_utc; sem ele nao consegue
    decidir se o dado esta velho. Carimbar com a data de modificacao do
    ficheiro e o mais honesto que se pode fazer sem dado de mercado: o EA
    passa a ver a idade REAL do ficheiro e a recusa-lo, em vez de aceitar em
    silencio um JSON de origem desconhecida.
    """
    stamped, skipped = 0, 0
    for path in sorted(DATA_DIR.glob("prediction_*.json")):
        payload = read_json(path)
        if payload is None:
            continue
        if payload.get("timestamp_utc"):
            skipped += 1
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        payload["timestamp_utc"] = mtime.isoformat()
        payload["timestamp_source"] = "file_mtime"
        payload["publicable"] = False
        payload.setdefault("publish_reason", "sem timestamp original; idade medida pela data do ficheiro")
        path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
        stamped += 1
        print(f"[stamp] {path.name}: timestamp_utc={payload['timestamp_utc']} (mtime)")
    print(f"[stamp] carimbados={stamped} ja_tinham={skipped}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "probe":
        cmd_probe()
    elif cmd == "regen":
        cmd_regen()
    elif cmd == "train":
        cmd_train()
    elif cmd == "publish":
        cmd_publish()
    elif cmd == "validate":
        cmd_validate()
    elif cmd == "stamp":
        cmd_stamp()
    else:
        raise SystemExit(f"comando desconhecido: {cmd}")
