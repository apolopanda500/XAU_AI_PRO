"""
XAU_AI_PRO - Multi-Asset Pipeline
v1.2.0 Multi-Asset Engine

Responsabilidades:
- Carregar e organizar dataset por sÃ­mbolo
- Limpar e validar dados
- Gerar features especÃ­ficas por ativo
- Treinar modelo independente por sÃ­mbolo
- Gerar previsÃµes com classificaÃ§Ã£o de mercado
- Integrar EntryFilter, RiskManager e DecisionEngine
- Executar backtest por sÃ­mbolo
- Gerar JSONs profissionais por ativo
- Suporte a mÃºltiplos timeframes
- Processamento paralelo por ativo
"""

from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime, timezone
import logging
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import dump, load  # type: ignore[import]
from sklearn.ensemble import RandomForestClassifier  # type: ignore[import]
from sklearn.metrics import accuracy_score, f1_score  # type: ignore[import]

# ============================================================
# MT5 BRIDGE - Caminho dinamico do terminal
# ============================================================
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from mt5_bridge import (
        mt5_files_path,
        get_mt5_data_path,
        normalize_symbol,
        is_prediction_stale,
        save_prediction_json,
        get_mt5_files_path,
    )
except ImportError:
    # Fallback para compatibilidade
    HOME_MT5 = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
    _terminal = None
    if HOME_MT5.exists():
        for item in HOME_MT5.iterdir():
            if item.is_dir() and (item / "MQL5" / "Files").exists():
                _terminal = item
                break
    mt5_files_path = (_terminal / "MQL5" / "Files") if _terminal else Path.cwd()
    OUTPUT_DIR = get_mt5_data_path()
    
    def normalize_symbol(symbol):
        return symbol.strip().upper().replace("#", "").replace("c", "").replace("m", "").replace(".", "")
    
    def is_prediction_stale(ts, max_age=300):
        return False
    
    def save_prediction_json(result, output_dir=None):
        if output_dir is None:
            output_dir = OUTPUT_DIR
        import json
        output_dir.mkdir(parents=True, exist_ok=True)
        symbol = result.get("symbol", "UNKNOWN")
        primary_path = output_dir / f"prediction_{symbol}.json"
        primary_path.write_text(json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8")
        return str(primary_path)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MODELS_DIR = BASE_DIR / "models"
OUTPUT_DIR = get_mt5_data_path()
DATASETS_DIR = BASE_DIR / "datasets"

for directory in [MODELS_DIR, OUTPUT_DIR, DATASETS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================
# VERSION
# ============================================================

APP_NAME = "XAU_AI_PRO Multi-Asset Pipeline"
APP_VERSION = "1.2.0"

# ============================================================
# RETRAIN CONFIG
# ============================================================

RETRAIN_MIN_NEW_CANDLES = 1000
RETRAIN_DB_PATH = PROJECT_ROOT / "database" / "trading.db"

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("XAU_AI_PRO.PIPELINE")

# ============================================================
# CONFIGURAÃ‡Ã•ES POR CATEGORIA
# ============================================================

CATEGORY_CONFIG: dict[str, dict[str, Any]] = {
    "Metals": {
        "n_estimators": 300,
        "max_depth": 10,
        "min_samples_leaf": 5,
        "lookback": 1,
        "timeframes": ["M5", "H1", "H4"],
        "target_mode": "atr",  # "atr" = normalizado por volatilidade | "fixed" = limiares fixos
        "atr_directional_th": 0.4,  # multiplos de ATR p/ BUY/SELL
        "atr_strong_th": 1.0,  # multiplos de ATR p/ STRONG_BUY/STRONG_SELL
        "atr_window": 14,  # janela do ATR medio
        "atr_floor_quantile": 0.02,  # piso anti-spike (2o percentil)
        "atr_clip": 6.0,  # clip de extremos em multiplos de ATR
        "n_classes": 3,  # 3 = SELL/NEUTRAL/BUY | 5 = com STRONG_*
        "calibrate": True,  # calibra probabilidades (isotonic)
        "calibration_cv": 3,
    },
    "Crypto": {
        "n_estimators": 400,
        "max_depth": 12,
        "min_samples_leaf": 4,
        "lookback": 3,
        "timeframes": ["M5", "M15", "H1", "H4"],
        "target_mode": "atr",
        "atr_directional_th": 0.4,
        "atr_strong_th": 1.0,
        "atr_window": 14,
        "atr_floor_quantile": 0.02,
        "atr_clip": 6.0,
        "n_classes": 3,
        "calibrate": True,
        "calibration_cv": 3,
    },
    "Forex": {
        "n_estimators": 200,
        "max_depth": 8,
        "min_samples_leaf": 6,
        "lookback": 1,
        "timeframes": ["M5", "M15", "H1"],
        "target_mode": "atr",
        "atr_directional_th": 0.4,
        "atr_strong_th": 1.0,
        "atr_window": 14,
        "atr_floor_quantile": 0.02,
        "atr_clip": 6.0,
        "n_classes": 3,
        "calibrate": True,
        "calibration_cv": 3,
    },
    "Indices": {
        "n_estimators": 300,
        "max_depth": 10,
        "min_samples_leaf": 5,
        "lookback": 2,
        "timeframes": ["M5", "M15", "H1", "H4"],
        "target_mode": "atr",
        "atr_directional_th": 0.4,
        "atr_strong_th": 1.0,
        "atr_window": 14,
        "atr_floor_quantile": 0.02,
        "atr_clip": 6.0,
        "n_classes": 3,
        "calibrate": True,
        "calibration_cv": 3,
    },
    "Energy": {
        "n_estimators": 300,
        "max_depth": 10,
        "min_samples_leaf": 5,
        "lookback": 1,
        "timeframes": ["M5", "H1", "H4"],
        "target_mode": "atr",
        "atr_directional_th": 0.4,
        "atr_strong_th": 1.0,
        "atr_window": 14,
        "atr_floor_quantile": 0.02,
        "atr_clip": 6.0,
        "n_classes": 3,
        "calibrate": True,
        "calibration_cv": 3,
    },
    "Unknown": {
        "n_estimators": 300,
        "max_depth": 10,
        "min_samples_leaf": 5,
        "lookback": 1,
        "timeframes": ["M5", "H1"],
        "target_mode": "atr",
        "atr_directional_th": 0.4,
        "atr_strong_th": 1.0,
        "atr_window": 14,
        "atr_floor_quantile": 0.02,
        "atr_clip": 6.0,
        "n_classes": 3,
        "calibrate": True,
        "calibration_cv": 3,
    },
}

SYMBOL_CATEGORY_MAP: dict[str, str] = {
    "XAUUSD": "Metals",
    "XAGUSD": "Metals",
    "BTCUSD": "Crypto",
    "ETHUSD": "Crypto",
    "EURUSD": "Forex",
    "GBPUSD": "Forex",
    "USDJPY": "Forex",
    "US30": "Indices",
    "NAS100": "Indices",
}


def _detect_category(symbol: str) -> str:
    """Detecta a categoria do ativo pelo nome do sÃ­mbolo."""
    upper = symbol.upper()

    if upper in SYMBOL_CATEGORY_MAP:
        return SYMBOL_CATEGORY_MAP[upper]

    if upper.startswith(("XAU", "XAG", "GOLD", "SILVER")):
        return "Metals"

    if upper.startswith(("BTC", "ETH", "BNB", "SOL", "ADA", "DOGE")):
        return "Crypto"

    if any(
        index in upper for index in ["NAS", "US30", "SPX", "DOW", "FTSE", "DAX", "CAC"]
    ):
        return "Indices"

    if any(energy in upper for energy in ["OIL", "WTI", "BRENT", "NGAS"]):
        return "Energy"

    if any(
        quote in upper
        for quote in ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
    ):
        return "Forex"

    return "Unknown"


# ============================================================
# FEATURES
# ============================================================

from ai.feature_engineering import (
    FEATURES,
    build_features,
)

# ============================================================
# BACKTEST / DECISION / RISK / ENTRY
# ============================================================
from backtest.backtest_engine import (
    BacktestConfig,
    BacktestEngine,
)

# ============================================================
# DATA
# ============================================================
from data.data_engine import DataEngine
from data.data_pipeline import DataPipeline
from decision.decision_engine import (
    DecisionConfig,
    DecisionEngine,
)
from entry.entry_filter import (
    EntryConfig,
    EntryFilter,
)
from risk.risk_manager import (
    RiskConfig,
    RiskManager,
)

# ============================================================
# CLASSIFIER
# ============================================================

# MODEL MANAGER
# ============================================================


def get_model_path(symbol: str, timeframe: str = "M5") -> Path:
    return MODELS_DIR / f"{symbol}_{timeframe}.pkl"


def save_model(symbol: str, timeframe: str, model: Any) -> Path:
    path = get_model_path(symbol, timeframe)
    path.parent.mkdir(parents=True, exist_ok=True)
    dump(model, path)
    logger.info("Modelo salvo: %s", path)
    return path


def load_model(symbol: str, timeframe: str = "M5") -> Any:
    path = get_model_path(symbol, timeframe)
    if not path.exists():
        raise FileNotFoundError(f"Modelo nÃ£o encontrado: {path}")
    model = load(path)
    logger.info("Modelo carregado: %s", path)
    return model


def load_model_meta(symbol: str, timeframe: str = "M5") -> dict[str, Any]:
    """ETAPA 15.3: metadados de governanca do modelo (.meta.json)."""
    path = get_model_path(symbol, timeframe).with_suffix(".meta.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def model_exists(symbol: str, timeframe: str = "M5") -> bool:
    return get_model_path(symbol, timeframe).exists()


# ============================================================
# TRAIN / PREDICT POR SÃMBOLO
# ============================================================


def train_symbol_model(
    symbol: str,
    df: pd.DataFrame,
    timeframe: str = "M5",
    category: str = "Unknown",
    sample_weights: pd.Series | None = None,
) -> dict[str, Any]:
    config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["Unknown"])

    df = _build_multiclass_target(df, lookahead=config["lookback"], category=category)

    if len(df) < 500:
        raise ValueError(f"Amostras insuficientes: {len(df)}")

    X = df[FEATURES]
    y = df["Target"]

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = RandomForestClassifier(
        n_estimators=config["n_estimators"],
        max_depth=config["max_depth"],
        min_samples_leaf=config["min_samples_leaf"],
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    logger.info("Treinando %s | %s | amostras=%d", symbol, timeframe, len(X_train))
    if sample_weights is not None:
        model.fit(X_train, y_train, sample_weight=sample_weights.iloc[:split_idx])
    else:
        model.fit(X_train, y_train)

    # Calibracao de probabilidades (isotonic) - melhora a confianca dos sinais
    if config.get("calibrate", False):
        from sklearn.calibration import CalibratedClassifierCV

        model = CalibratedClassifierCV(
            model,
            method="isotonic",
            cv=config.get("calibration_cv", 3),
        )
        if sample_weights is not None:
            model.fit(X_train, y_train, sample_weight=sample_weights.iloc[:split_idx])
        else:
            model.fit(X_train, y_train)
        logger.info("Modelo %s [%s] | calibracao isotonica aplicada", symbol, timeframe)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")

    metrics = {
        "accuracy": float(accuracy),
        "f1_score": float(f1),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }

    save_model(symbol, timeframe, model)

    # ============================================================
    # ETAPA 15.3: METADADOS DE GOVERNANCA (ModelGovernance.mqh)
    # Publica algorithm/train_date/dataset_version/metrics que o
    # AIConnector le via GetAIMetaString -> ModelGovernanceRefresh.
    # ============================================================
    try:
        ds_sig = (
            f"{len(df)}|"
            f"{float(df['Close'].iloc[-1]):.5f}|"
            f"{timeframe}|"
            f"{len(FEATURES)}"
        )
        meta = {
            "algorithm": type(model).__name__,
            "train_date": datetime.now(timezone.utc).isoformat(),
            "dataset_version": hashlib.sha256(ds_sig.encode("utf-8")).hexdigest()[:16],
            "metrics": metrics,
            "feature_count": len(FEATURES),
            "symbol": symbol,
            "timeframe": timeframe,
            "model_version": APP_VERSION,
        }
        meta_path = get_model_path(symbol, timeframe).with_suffix(".meta.json")
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        logger.info("Meta de governanca salva: %s", meta_path)
    except Exception as exc:
        logger.warning("Falha ao salvar meta de governanca %s: %s", symbol, exc)

    logger.info(
        "Modelo %s [%s] | acc=%.2f%% | f1=%.2f",
        symbol,
        timeframe,
        accuracy * 100,
        f1,
    )

    return metrics


def predict_symbol(
    symbol: str, df: pd.DataFrame, timeframe: str = "M5"
) -> dict[str, Any]:
    if not model_exists(symbol, timeframe):
        raise FileNotFoundError(f"Modelo nÃ£o encontrado: {symbol}_{timeframe}.pkl")

    model = load_model(symbol, timeframe)

    last_row = df.iloc[-1:]
    X = last_row[FEATURES]

    prediction = int(model.predict(X)[0])
    probabilities = model.predict_proba(X)[0]

    confidence = float(max(probabilities)) * 100
    prob_buy = (
        float(probabilities[-1]) if len(probabilities) > 1 else float(probabilities[0])
    )
    prob_sell = float(probabilities[0])

    return {
        "prediction": prediction,
        "confidence": round(confidence, 2),
        "prob_buy": round(prob_buy * 100, 2),
        "prob_sell": round(prob_sell * 100, 2),
        # ETAPA 15.3: metadados de governanca para o JSON final
        "meta": load_model_meta(symbol, timeframe),
    }


# ============================================================
# TARGET BUILDER
# ============================================================


def _build_multiclass_target(
    df: pd.DataFrame,
    lookahead: int = 1,
    category: str = "Unknown",
) -> pd.DataFrame:
    """Constroi target multiclasse (0-4).

    Modo "atr" (padrao): normaliza o retorno combinado pela volatilidade
    (ATR relativo ao preco), gerando classes balanceadas comparaveis entre
    simbolos de categorias diferentes (Forex, Ouro, Crypto).

    Modo "fixed": usa limiares fixos de retorno (legado, desbalanceado).
    """
    future_return = df["Close"].shift(-lookahead) / df["Close"] - 1
    future_return_5 = df["Close"].shift(-5) / df["Close"] - 1
    future_return_10 = df["Close"].shift(-10) / df["Close"] - 1

    combined = (future_return + future_return_5 * 0.5 + future_return_10 * 0.3) / 1.8

    cfg = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["Unknown"])
    mode = cfg.get("target_mode", "atr")

    if mode == "atr":
        # ATR relativo ao preco (fracao), com piso para evitar spikes quando ATR~0
        atr_rel = (df["ATR"] / df["Close"]).rolling(cfg["atr_window"]).mean().shift(1)
        floor = atr_rel.quantile(cfg["atr_floor_quantile"])
        atr_rel = atr_rel.clip(lower=floor)
        norm = (combined / atr_rel).clip(-cfg["atr_clip"], cfg["atr_clip"])

        d_th = cfg["atr_directional_th"]
        s_th = cfg["atr_strong_th"]
        conditions = [
            norm >= s_th,
            norm >= d_th,
            norm >= -d_th,
            norm >= -s_th,
        ]
    else:
        conditions = [
            combined >= 0.015,
            combined >= 0.005,
            combined >= -0.005,
            combined >= -0.015,
        ]

    choices = [4, 3, 2, 1]
    df["Target"] = pd.Series(
        np.select(conditions, choices, default=0),
        index=df.index,
    )

    # Reduz de 5 para 3 classes quando configurado (0=SELL, 1=NEUTRAL, 2=BUY)
    if cfg.get("n_classes", 5) == 3:
        df["Target"] = df["Target"].map({0: 0, 1: 0, 2: 1, 3: 2, 4: 2})

    df = df.dropna(subset=["Target"])
    return df


# ============================================================
# JSON BUILDER
# ============================================================


def build_prediction_json(
    symbol: str,
    prediction: int,
    confidence: float,
    prob_buy: float,
    prob_sell: float,
    df: pd.DataFrame,
    model_type: str = "random_forest",
    timeframe: str = "M5",
    category: str = "Unknown",
    inference_ms: float = 0.0,
    meta: dict[str, Any] | None = None,  # ETAPA 15.3: governanca
) -> dict[str, Any]:
    """ConstrÃ³i JSON de predicao."""
    last_row = df.iloc[-1]
    n_classes = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["Unknown"]).get(
        "n_classes", 5
    )
    if n_classes == 3:
        # 0=SELL, 1=NEUTRAL, 2=BUY
        signal = {0: "SELL", 1: "NEUTRAL", 2: "BUY"}.get(prediction, "NEUTRAL")
    else:
        signal = {0: "STRONG_SELL", 1: "SELL", 2: "NEUTRAL", 3: "BUY", 4: "STRONG_BUY"}.get(
            prediction, "NEUTRAL"
        )
    risk = (
        "LOW"
        if confidence >= 85
        else (
            "MEDIUM"
            if confidence >= 70
            else "HIGH" if confidence >= 55 else "VERY_HIGH"
        )
    )

    close_price = float(last_row["Close"])
    atr = float(last_row.get("ATR", 0.0))

    point = 0.01
    if atr > 0:
        sl = round(close_price - (atr * 1.5) / point, 2)
        tp = round(close_price + (atr * 3.0) / point, 2)
    else:
        sl = round(close_price * 0.99, 2)
        tp = round(close_price * 1.02, 2)

    model_id = f"{model_type}_{symbol}_{timeframe}"
    feature_hash = hashlib.sha256(
        f"{model_id}|{close_price}|{atr}|{confidence}".encode("utf-8")
    ).hexdigest()[:16]

    # ETAPA 15.3: metadados de governanca vindos do .meta.json do treino
    m = meta or {}

    result: dict[str, Any] = {
        "symbol": symbol,
        "category": category,
        "signal": signal,
        "confidence": confidence,
        "score": round(confidence, 1),
        "buy": prob_buy,
        "sell": prob_sell,
        "prob_buy": prob_buy,
        "prob_sell": prob_sell,
        "risk": risk,
        "model": model_type,
        "model_version": str(m.get("model_version", APP_VERSION)),
        "model_id": model_id,
        "feature_hash": feature_hash,
        # ETAPA 15.3: campos consumidos pelo ModelGovernance.mqh
        "algorithm": str(m.get("algorithm", "")),
        "train_date": str(m.get("train_date", "")),
        "dataset_version": str(m.get("dataset_version", "")),
        "feature_count": int(m.get("feature_count", len(FEATURES))),
        "metrics": json.dumps(m.get("metrics", {}), ensure_ascii=False),
        "inference_ms": inference_ms,
        "timestamp": pd.Timestamp.now().isoformat(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "price": round(close_price, 2),
        "atr": round(atr, 2),
        "spread": round(float(last_row.get("Spread", 0)), 2),
        "volume": int(last_row.get("Volume", 0)),
        "sl": sl,
        "tp": tp,
    }

    return result


def save_prediction_json(result: dict[str, Any], timeframe: str | None = None) -> Path:
    symbol = result["symbol"]
    if timeframe:
        output_path = OUTPUT_DIR / f"prediction_{symbol}_{timeframe}.json"
    else:
        output_path = OUTPUT_DIR / f"prediction_{symbol}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    logger.info("JSON salvo: %s", output_path)
    return output_path


# ============================================================
# PIPELINE CLASS
# ============================================================


class Pipeline:
    """
    Pipeline multi-ativo completo.
    """

    def __init__(
        self,
        dataset_path: str | Path | None = None,
        max_workers: int = 4,
    ) -> None:
        self.dataset_path = (
            Path(dataset_path).expanduser()
            if dataset_path is not None
            else (PROJECT_ROOT / "MQL5" / "Files" / "Data" / "dataset.csv")
        )

        self.entry_filter = EntryFilter(EntryConfig())
        self.risk_manager = RiskManager(RiskConfig())
        self.decision_engine = DecisionEngine(DecisionConfig())
        self.backtest_engine = BacktestEngine(BacktestConfig())

        self.df: pd.DataFrame | None = None
        self.feature_df: pd.DataFrame | None = None
        self.symbols: list[str] = []
        self.max_workers = max_workers
        self._last_timeframe_predictions: dict[str, dict[str, Any]] = {}
        self._last_timeframe_predictions: dict[str, dict[str, Any]] = {}

    # ========================================================
    # 1. CARREGAR
    # ========================================================

    def load_dataset(self) -> pd.DataFrame:
        """
        Carrega e organiza o dataset por sÃ­mbolo.
        """

        logger.info("Carregando dataset: %s", self.dataset_path)

        engine = DataEngine(dataset_path=self.dataset_path)
        df = engine.load()

        if df.empty:
            raise ValueError("Dataset vazio.")

        self.df = df
        self.symbols = sorted(
            df["Symbol"].astype(str).str.strip().str.upper().unique().tolist()
        )

        logger.info(
            "Dataset carregado | %d registros | %d sÃ­mbolos",
            len(df),
            len(self.symbols),
        )

        return df

    # ========================================================
    # 2. LIMPAR
    # ========================================================

    def clean_data(self) -> pd.DataFrame:
        """
        Limpa e valida os dados.
        """

        if self.df is None:
            raise ValueError("Dataset nÃ£o carregado.")

        pipeline = DataPipeline(self.df)
        df = pipeline.clean().get()

        if df.empty:
            raise ValueError("Dataset vazio apÃ³s limpeza.")

        self.df = df
        logger.info("Dados limpos | %d registros", len(df))
        return df

    # ========================================================
    # 3. FEATURES
    # ========================================================

    def generate_features(self) -> pd.DataFrame:
        """
        Gera features para todos os sÃ­mbolos.
        """

        if self.df is None:
            raise ValueError("Dataset nÃ£o carregado.")

        feature_df = build_features(
            self.df,
            dropna=True,
        )

        if feature_df.empty:
            raise ValueError("Nenhuma feature vÃ¡lida.")

        self.feature_df = feature_df

        logger.info(
            "Features geradas | %d registros | %d features",
            len(feature_df),
            len(FEATURES),
        )

        return feature_df

    # ========================================================
    # 4. ORGANIZAR POR SÃMBOLO
    # ========================================================

    def organize_by_symbol(self) -> dict[str, pd.DataFrame]:
        """
        Organiza datasets por sÃ­mbolo.
        """

        if self.feature_df is None:
            raise ValueError("Features nÃ£o geradas.")

        datasets: dict[str, pd.DataFrame] = {}

        for symbol, group in self.feature_df.groupby(
            "Symbol",
            sort=False,
        ):
            datasets[str(symbol)] = group.sort_values("Time").reset_index(drop=True)

        logger.info(
            "Datasets organizados | %d sÃ­mbolos",
            len(datasets),
        )

        return datasets

    # ========================================================
    # 5. TREINAR MODELOS
    # ========================================================

    def train_all_models(self, timeframes: list[str] | None = None) -> dict[str, Any]:
        """Treina modelo para cada sÃ­mbolo em todos os timeframes aplicÃ¡veis."""
        datasets = self.organize_by_symbol()
        summary: dict[str, Any] = {}
        jobs: list[tuple[str, pd.DataFrame, str, str]] = []

        for symbol in self.symbols:
            if symbol not in datasets:
                continue

            df = datasets[symbol]
            category = _detect_category(symbol)
            category_config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["Unknown"])
            available_timeframes = category_config["timeframes"]
            selected_timeframes = (
                list(timeframes) if timeframes else list(available_timeframes)
            )

            for tf in selected_timeframes:
                jobs.append((symbol, df, tf, category))

        if jobs:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_job = {
                    executor.submit(self._train_one, symbol, df, tf, category): (
                        symbol,
                        tf,
                    )
                    for symbol, df, tf, category in jobs
                }
                for future in as_completed(future_to_job):
                    symbol, tf = future_to_job[future]
                    try:
                        result = future.result()
                        summary[f"{symbol}_{tf}"] = result
                    except Exception as exc:
                        logger.exception(
                            "Falha ao treinar %s [%s]: %s", symbol, tf, exc
                        )
                        summary[f"{symbol}_{tf}"] = {
                            "status": "error",
                            "error": str(exc),
                            "category": category,
                            "timeframe": tf,
                            "symbol": symbol,
                        }

        return summary

    def _train_one(
        self,
        symbol: str,
        df: pd.DataFrame,
        timeframe: str,
        category: str,
    ) -> dict[str, Any]:
        """Executa treino de um sÃ­mbolo/timeframe."""
        sample_weights = build_feedback_sample_weights(
            df,
            symbol,
            timeframe,
            db_path=RETRAIN_DB_PATH,
        )
        metrics = train_symbol_model(
            symbol,
            df,
            timeframe=timeframe,
            category=category,
            sample_weights=sample_weights,
        )
        return {
            "status": "success",
            "metrics": metrics,
            "category": category,
            "timeframe": timeframe,
            "symbol": symbol,
        }

    # ========================================================
    # 6. PREDIZER TODOS
    # ========================================================

    def predict_all(self, timeframes: list[str] | None = None) -> dict[str, Any]:
        """Prediz todos os sÃ­mbolos em todos os timeframes aplicÃ¡veis."""
        datasets = self.organize_by_symbol()
        predictions: dict[str, Any] = {}
        timeframe_predictions: dict[str, dict[str, Any]] = {}
        jobs: list[tuple[str, pd.DataFrame, str, str]] = []

        for symbol in self.symbols:
            if symbol not in datasets:
                continue

            df = datasets[symbol]
            category = _detect_category(symbol)
            category_config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["Unknown"])
            available_timeframes = category_config["timeframes"]
            selected_timeframes = (
                list(timeframes) if timeframes else list(available_timeframes)
            )

            for tf in selected_timeframes:
                jobs.append((symbol, df, tf, category))

        if jobs:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_job = {
                    executor.submit(self._predict_one, symbol, df, tf, category): (
                        symbol,
                        tf,
                    )
                    for symbol, df, tf, category in jobs
                }
                for future in as_completed(future_to_job):
                    symbol, tf = future_to_job[future]
                    try:
                        result = future.result()
                        if result.get("status") == "error":
                            timeframe_predictions[f"{symbol}_{tf}"] = result
                            continue
                        timeframe_predictions[f"{symbol}_{tf}"] = result
                    except Exception as exc:
                        logger.exception(
                            "Falha ao predizer %s [%s]: %s", symbol, tf, exc
                        )
                        timeframe_predictions[f"{symbol}_{tf}"] = {
                            "status": "error",
                            "error": str(exc),
                            "symbol": symbol,
                            "timeframe": tf,
                        }

        from collections import defaultdict

        by_symbol: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for key, result in timeframe_predictions.items():
            if result.get("status") == "error":
                continue
            sym = result.get("symbol")
            tf = result.get("timeframe")
            if sym and tf:
                by_symbol[sym][tf] = result

        for symbol in self.symbols:
            symbol_predictions = by_symbol.get(symbol, {})
            consolidated = self.ensemble_timeframes(symbol, symbol_predictions)
            if consolidated is not None:
                save_prediction_json(consolidated)
                predictions[symbol] = consolidated
            else:
                # ETAPA 15.3: modelo/ensaio indisponivel -> grava UNAVAILABLE
                # para AIConnector bloquear (nunca vira sinal de trade).
                pred_unavail = {
                    "symbol": symbol,
                    "signal": "UNAVAILABLE",
                    "price": 0.0,
                    "buy": 0.0,
                    "sell": 0.0,
                    "score": 0.0,
                    "confidence": 0.0,
                    "model_version": "1.2.0",
                    "model_id": "unavailable",
                    "feature_hash": "",
                    "inference_ms": 0.0,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Nenhuma predicao valida para ensemble.",
                }
                save_prediction_json(pred_unavail)
                predictions[symbol] = pred_unavail

        self._last_timeframe_predictions = timeframe_predictions
        return predictions

    def _predict_one(
        self, symbol: str, df: pd.DataFrame, timeframe: str, category: str
    ) -> dict[str, Any]:
        """Executa predicao de um simbolo/timeframe."""
        _t0 = time.perf_counter()
        pred = predict_symbol(symbol, df, timeframe=timeframe)
        inference_ms = round((time.perf_counter() - _t0) * 1000.0, 2)
        result = build_prediction_json(
            symbol=symbol,
            prediction=pred["prediction"],
            confidence=pred["confidence"],
            prob_buy=pred["prob_buy"],
            prob_sell=pred["prob_sell"],
            df=df,
            category=category,
            timeframe=timeframe,
            inference_ms=inference_ms,
            meta=pred.get("meta"),  # ETAPA 15.3: governanca
        )
        return result

    # ========================================================
    # ENSEMBLE POR TIME-FRAMES
    # ========================================================

    @staticmethod
    def ensemble_timeframes(
        symbol: str,
        timeframe_predictions: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Combina prediÃ§Ãµes de mÃºltiplos timeframes em um sinal consolidado."""
        valid_results: list[dict[str, Any]] = [
            result
            for result in timeframe_predictions.values()
            if isinstance(result, dict) and result.get("status") != "error"
        ]

        if not valid_results:
            return None

        buy_like = sum(
            1 for r in valid_results if r.get("signal") in {"BUY", "STRONG_BUY"}
        )
        sell_like = sum(
            1 for r in valid_results if r.get("signal") in {"SELL", "STRONG_SELL"}
        )

        if buy_like > sell_like:
            signal = "BUY" if buy_like > len(valid_results) / 2 else "NEUTRAL"
        elif sell_like > buy_like:
            signal = "SELL" if sell_like > len(valid_results) / 2 else "NEUTRAL"
        else:
            signal = "NEUTRAL"

        confidence = float(sum(r.get("confidence", 0.0) for r in valid_results)) / len(
            valid_results
        )
        score = float(sum(r.get("score", 0.0) for r in valid_results)) / len(
            valid_results
        )
        prob_buy = float(sum(r.get("prob_buy", 0.0) for r in valid_results)) / len(
            valid_results
        )
        prob_sell = float(sum(r.get("prob_sell", 0.0) for r in valid_results)) / len(
            valid_results
        )
        atr = float(sum(r.get("atr", 0.0) for r in valid_results)) / len(valid_results)
        spread = float(sum(r.get("spread", 0.0) for r in valid_results)) / len(
            valid_results
        )
        volume = int(
            sum(r.get("volume", 0) for r in valid_results) / len(valid_results)
        )
        price = float(valid_results[-1].get("price", 0.0))

        category = valid_results[-1].get("category", "Unknown")
        timeframe = valid_results[-1].get("timeframe", "M5")
        timeframes = sorted({r.get("timeframe", "M5") for r in valid_results})

        risk = (
            "LOW"
            if confidence >= 85
            else (
                "MEDIUM"
                if confidence >= 70
                else "HIGH" if confidence >= 55 else "VERY_HIGH"
            )
        )

        point = 0.01
        if atr > 0:
            sl = round(price - (atr * 1.5) / point, 2)
            tp = round(price + (atr * 3.0) / point, 2)
        else:
            sl = round(price * 0.99, 2)
            tp = round(price * 1.02, 2)

        return {
            "symbol": symbol,
            "category": category,
            "signal": signal,
            "confidence": round(confidence, 2),
            "score": round(score, 1),
            "buy": round(prob_buy, 2),
            "sell": round(prob_sell, 2),
            "prob_buy": round(prob_buy, 2),
            "prob_sell": round(prob_sell, 2),
            "risk": risk,
            "model": "ensemble_timeframes",
            "timeframe": timeframe,
            "timeframes_used": timeframes,
            "timestamp": pd.Timestamp.now().isoformat(),
            "price": round(price, 2),
            "atr": round(atr, 2),
            "spread": round(spread, 2),
            "volume": volume,
            "sl": sl,
            "tp": tp,
        }

    # ========================================================
    # 7. BACKTEST
    # ========================================================

    def run_backtest(self, symbol: str) -> Any:
        """Executa backtest."""
        if self.df is None:
            raise ValueError("Dataset nÃ£o carregado.")

        result = self.backtest_engine.run(df=self.df, symbol=symbol)

        logger.info(
            "Backtest %s | PF=%.2f | Expectancy=%.2f | WinRate=%.2f%% | SQN=%.2f",
            symbol,
            result.profit_factor,
            result.expectancy,
            result.win_rate * 100.0,
            result.sqn,
        )

        return result

    # ========================================================
    # AUTO-RETRAIN
    # ========================================================

    def maybe_retrain_all(self, timeframes: list[str] | None = None) -> dict[str, Any]:
        """Verifica todos os sÃ­mbolos e retreina se houver candles novos suficientes."""
        if self.df is None:
            return {}

        datasets = self.organize_by_symbol()
        summary: dict[str, Any] = {}
        jobs: list[tuple[str, pd.DataFrame, str, str]] = []

        for symbol in self.symbols:
            if symbol not in datasets:
                continue

            df = datasets[symbol]
            category = _detect_category(symbol)
            category_config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["Unknown"])
            available_timeframes = category_config["timeframes"]
            selected_timeframes = (
                list(timeframes) if timeframes else list(available_timeframes)
            )

            for tf in selected_timeframes:
                jobs.append((symbol, df, tf, category))

        if jobs:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_job = {
                    executor.submit(
                        maybe_retrain_symbol, symbol, df, tf, category, RETRAIN_DB_PATH
                    ): (symbol, tf)
                    for symbol, df, tf, category in jobs
                }
                for future in as_completed(future_to_job):
                    symbol, tf = future_to_job[future]
                    try:
                        result = future.result()
                        if result is not None:
                            summary[f"{symbol}_{tf}"] = result
                    except Exception as exc:
                        logger.exception(
                            "Falha no retreino automÃ¡tico para %s [%s]: %s",
                            symbol,
                            tf,
                            exc,
                        )

        return summary

    # ========================================================
    # 8. RUN COMPLETO
    # ========================================================

    def run(self) -> dict[str, Any]:
        """Executa pipeline completo."""
        print()
        print("=" * 70)
        print(f" {APP_NAME}")
        print(f" VERSION {APP_VERSION}")
        print("=" * 70)
        print()

        self.load_dataset()
        self.clean_data()
        self.generate_features()

        print()
        print("=" * 70)
        print(" TREINAMENTO")
        print("=" * 70)
        train_summary = self.train_all_models()

        print()
        print("=" * 70)
        print(" RETREINO AUTOMÃTICO")
        print("=" * 70)
        retrain_summary = self.maybe_retrain_all()

        print()
        print("=" * 70)
        print(" PREDIÃ‡ÃƒO")
        print("=" * 70)
        predictions = self.predict_all()

        print()
        print("=" * 70)
        print(" BACKTEST")
        print("=" * 70)
        backtests: dict[str, Any] = {}

        for symbol in self.symbols:
            try:
                result = self.run_backtest(symbol)
                backtests[symbol] = result.to_dict()
            except Exception as exc:
                logger.warning("%s | backtest falhou: %s", symbol, exc)
                backtests[symbol] = {"error": str(exc)}

        print()
        print("=" * 70)
        print(" PIPELINE CONCLUÃDO")
        print("=" * 70)
        print()
        print("SÃ­mbolos processados:", len(self.symbols))
        print(
            "Modelos treinados:",
            sum(1 for v in train_summary.values() if v.get("status") == "success"),
        )
        print("PrediÃ§Ãµes geradas:", len(predictions))
        print()

        for symbol, pred in predictions.items():
            if isinstance(pred, dict) and "signal" in pred:
                timeframes_used = pred.get(
                    "timeframes_used", [pred.get("timeframe", "M5")]
                )
                print(
                    f"{symbol} | {pred['signal']} | {pred['confidence']:.1f}% | "
                    f"{pred.get('category', 'Unknown')} | "
                    f"TFs={timeframes_used}"
                )

        print()
        for symbol, result in backtests.items():
            if isinstance(result, dict) and "profit_factor" in result:
                print(
                    f"{symbol} | PF={result['profit_factor']:.2f} | "
                    f"Expectancy={result['expectancy']:.2f} | "
                    f"WinRate={result['win_rate'] * 100:.2f}% | SQN={result['sqn']:.2f}"
                )

        print()
        print("=" * 70)

        return {
            "symbols": self.symbols,
            "train_summary": train_summary,
            "predictions": predictions,
            "backtests": backtests,
        }


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    """Entry point."""
    pipeline = Pipeline()

    try:
        pipeline.run()
    except Exception as exc:
        logger.exception("Erro no pipeline: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()


# ============================================================
# AUTO-RETRAIN
# ============================================================


def _ensure_retrain_table(db_path: Path) -> None:
    """Cria tabela de retreino se nÃ£o existir."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retrain_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            category TEXT,
            dataset_rows INTEGER NOT NULL,
            status TEXT NOT NULL,
            accuracy REAL,
            f1_score REAL,
            trained_at TEXT NOT NULL
        )
        """)
    conn.commit()
    conn.close()


def _get_last_retrain_row_count(
    db_path: Path, symbol: str, timeframe: str
) -> int | None:
    """Retorna a contagem de linhas do dataset no Ãºltimo retreino."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dataset_rows
        FROM retrain_log
        WHERE symbol = ? AND timeframe = ?
        ORDER BY trained_at DESC
        LIMIT 1
        """,
        (symbol, timeframe),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def _record_retrain(
    db_path: Path,
    symbol: str,
    timeframe: str,
    category: str,
    dataset_rows: int,
    status: str,
    accuracy: float | None = None,
    f1_score: float | None = None,
) -> None:
    """Registra um retreino no banco."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO retrain_log (symbol, timeframe, category, dataset_rows, status, accuracy, f1_score, trained_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            timeframe,
            category,
            dataset_rows,
            status,
            accuracy,
            f1_score,
            pd.Timestamp.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ============================================================
# FEEDBACK / LEARNING
# ============================================================


def _ensure_feedback_tables(db_path: Path) -> None:
    """Cria tabelas de feedback se nÃ£o existirem."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS prediction_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            prediction_timestamp TEXT NOT NULL,
            signal TEXT,
            confidence REAL,
            result TEXT NOT NULL,
            pnl REAL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feedback_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            last_updated TEXT NOT NULL
        );
        """)
    conn.commit()
    conn.close()


def _upsert_feedback_stats(
    db_path: Path, symbol: str, timeframe: str, win: bool
) -> None:
    """Atualiza estatÃ­sticas de acerto por sÃ­mbolo/timeframe."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO feedback_stats (symbol, timeframe, wins, losses, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(symbol, timeframe) DO UPDATE SET
            wins = wins + ?,
            losses = losses + ?,
            last_updated = ?
        """,
        (
            symbol,
            timeframe,
            1 if win else 0,
            0 if win else 1,
            pd.Timestamp.now().isoformat(),
            1 if win else 0,
            0 if win else 1,
            pd.Timestamp.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def save_prediction_feedback(
    db_path: Path,
    symbol: str,
    timeframe: str,
    prediction_timestamp: str,
    signal: str,
    confidence: float,
    result: str,
    pnl: float | None = None,
) -> None:
    """Salva feedback de uma prediÃ§Ã£o."""
    _ensure_feedback_tables(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO prediction_feedback (symbol, timeframe, prediction_timestamp, signal, confidence, result, pnl, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            timeframe,
            prediction_timestamp,
            signal,
            confidence,
            result,
            pnl,
            pd.Timestamp.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    if result in {"win", "loss"}:
        _upsert_feedback_stats(db_path, symbol, timeframe, win=result == "win")


def load_feedback_weights(
    db_path: Path,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    """Carrega pesos baseados no histÃ³rico de acerto."""
    _ensure_feedback_tables(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT wins, losses
        FROM feedback_stats
        WHERE symbol = ? AND timeframe = ?
        """,
        (symbol, timeframe),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"weight": 1.0, "wins": 0, "losses": 0}

    wins, losses = row
    total = wins + losses
    if total == 0:
        return {"weight": 1.0, "wins": wins, "losses": losses}

    win_rate = wins / total
    weight = float(max(0.5, min(1.5, win_rate)))
    return {"weight": round(weight, 4), "wins": wins, "losses": losses}


def build_feedback_sample_weights(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    db_path: Path = RETRAIN_DB_PATH,
) -> pd.Series:
    """Gera pesos para amostras baseados em feedback histÃ³rico."""
    if df.empty or "Time" not in df.columns:
        return pd.Series([1.0] * len(df), index=df.index)

    _ensure_feedback_tables(db_path)

    conn = sqlite3.connect(db_path)
    feedback = pd.read_sql_query(
        """
        SELECT prediction_timestamp, result, pnl
        FROM prediction_feedback
        WHERE symbol = ? AND timeframe = ?
        ORDER BY prediction_timestamp DESC
        """,
        conn,
        params=(symbol, timeframe),
    )
    conn.close()

    if feedback.empty:
        return pd.Series([1.0] * len(df), index=df.index)

    feedback["prediction_timestamp"] = pd.to_datetime(
        feedback["prediction_timestamp"], errors="coerce"
    )
    df = df.copy()
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df = df.sort_values("Time")

    merged = pd.merge(
        df.reset_index().rename(columns={"index": "row_index"}),
        feedback,
        left_on="Time",
        right_on="prediction_timestamp",
        how="left",
    ).set_index("row_index")

    weights = []
    for idx in df.index:
        row = merged.loc[idx] if idx in merged.index else None
        if row is not None and pd.notna(row.get("prediction_timestamp")):
            result_value = row.get("result")
            if result_value == "win":
                weights.append(1.3)
            elif result_value == "loss":
                weights.append(0.7)
            else:
                weights.append(1.0)
        else:
            weights.append(1.0)

    return pd.Series(weights, index=df.index)


def maybe_retrain_symbol(
    symbol: str,
    df: pd.DataFrame,
    timeframe: str = "M5",
    category: str = "Unknown",
    db_path: Path = RETRAIN_DB_PATH,
) -> dict[str, Any] | None:
    """Retreina automaticamente se houver candles novos suficientes."""
    _ensure_retrain_table(db_path)

    current_rows = len(df)
    last_rows = _get_last_retrain_row_count(db_path, symbol, timeframe)

    if last_rows is not None and current_rows - last_rows < RETRAIN_MIN_NEW_CANDLES:
        return None

    logger.info(
        "Retreino automÃ¡tico iniciado para %s [%s] | rows=%d | delta=%d",
        symbol,
        timeframe,
        current_rows,
        current_rows - last_rows if last_rows is not None else current_rows,
    )

    try:
        sample_weights = build_feedback_sample_weights(
            df,
            symbol,
            timeframe,
            db_path=db_path,
        )
        metrics = train_symbol_model(
            symbol,
            df,
            timeframe=timeframe,
            category=category,
            sample_weights=sample_weights,
        )
        _record_retrain(
            db_path=db_path,
            symbol=symbol,
            timeframe=timeframe,
            category=category,
            dataset_rows=current_rows,
            status="success",
            accuracy=metrics.get("accuracy"),
            f1_score=metrics.get("f1_score"),
        )
        logger.info(
            "Retreino automÃ¡tico concluÃ­do para %s [%s] | acc=%.2f%% | f1=%.2f",
            symbol,
            timeframe,
            metrics.get("accuracy", 0.0) * 100,
            metrics.get("f1_score", 0.0),
        )
        return {"status": "success", "metrics": metrics}
    except Exception as exc:
        _record_retrain(
            db_path=db_path,
            symbol=symbol,
            timeframe=timeframe,
            category=category,
            dataset_rows=current_rows,
            status="error",
        )
        logger.exception("Falha no retreino automÃ¡tico para %s: %s", symbol, exc)
        return {"status": "error", "error": str(exc)}

