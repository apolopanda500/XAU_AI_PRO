# -*- coding: utf-8 -*-
"""ETAPA 18.8 - EventStream da IA.

Cada evento importante da IA entra no forward_test_events.csv (append-only).
Usa o mesmo formato 10 colunas do EventEmitter do EA.

Eventos IA:
  AI_PREDICTION, AI_ERROR, AI_STALE, AI_UNAVAILABLE, AI_MODEL_READY,
  AI_MODEL_CHANGED, AI_FEATURE_ERROR

IMPORTANTE: este modulo apenas ANEXA ao CSV compartilhado (FILE_SHARE),
nao reescreve nem apaga. Se o arquivo nao existir, tenta em fallbacks.
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from app.utils.paths import get_mql_data_path

TERMINAL_DATA = get_mql_data_path() / "forward_test_events.csv"
LOCAL_DATA = Path(__file__).resolve().parent.parent / "MQL5" / "Files" / "Data" / "forward_test_events.csv"

HEADER = ["Time", "Event", "Symbol", "TF", "Ticket", "Severity",
          "Module", "Message", "Value", "Status"]


def events_file() -> Path:
    if TERMINAL_DATA.exists():
        return TERMINAL_DATA
    return LOCAL_DATA


def _now_mt5() -> str:
    """Timestamp no formato MT5: YYYY.MM.DD HH:MM:SS (hora local)."""
    return datetime.now().strftime("%Y.%m.%d %H:%M:%S")


def emit(event: str, symbol: str = "", timeframe: str = "", ticket: str = "0",
         severity: str = "INFO", module: str = "AI", message: str = "",
         value: str = "", status: str = "") -> bool:
    """Anexa 1 evento ao forward_test_events.csv (UTF-16, ',', append)."""
    row = [_now_mt5(), event, symbol, timeframe, ticket, severity,
           module, message, value, status]
    try:
        new_file = not events_file().exists()
        with open(events_file(), "a", encoding="utf-16", newline="") as f:
            w = csv.writer(f, delimiter=",")
            if new_file:
                w.writerow(HEADER)
            w.writerow(row)
        return True
    except Exception:  # noqa: BLE001
        return False


# helpers semanticos (18.8)
def ai_prediction(symbol, tf, signal, confidence, value=""):
    return emit("AI_PREDICTION", symbol, tf, severity="INFO", message=f"{signal} {confidence:.0%}",
                value=value, status="READY")

def ai_error(symbol, tf, reason):
    return emit("AI_ERROR", symbol, tf, severity="ERROR", message=reason, status="ERROR")

def ai_stale(symbol, tf, age_sec):
    return emit("AI_STALE", symbol, tf, severity="WARN", message=f"age={age_sec}s", status="STALE")

def ai_unavailable(symbol, tf, reason):
    return emit("AI_UNAVAILABLE", symbol, tf, severity="WARN", message=reason, status="UNAVAILABLE")

def ai_model_ready(symbol, tf, model):
    return emit("AI_MODEL_READY", symbol, tf, severity="INFO", message=model, status="READY")

def ai_model_changed(symbol, tf, old, new):
    return emit("AI_MODEL_CHANGED", symbol, tf, severity="INFO", message=f"{old}->{new}", status="READY")

def ai_feature_error(symbol, tf, reason):
    return emit("AI_FEATURE_ERROR", symbol, tf, severity="ERROR", message=reason, status="FEATURE_ERROR")


if __name__ == "__main__":
    print("IA EventStream ->", events_file())
    ok = ai_model_ready("XAUUSD", "M5", "XAUUSD_M5")
    ok2 = ai_stale("XAUUSD", "M5", 666348)
    print("emit ready:", ok, "| emit stale:", ok2)
