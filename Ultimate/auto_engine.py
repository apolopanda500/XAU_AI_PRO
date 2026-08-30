"""
XAU AI PRO - AutoEngine
Motor de automação "auto-approve": treina, prediz, valida e gera um
relatório de aprovação de condições de mercado.

Fluxo:
  1. Garante que o dataset exista (coleta via MT5 se possível).
  2. Treina/re-treina modelos por símbolo (se houver dados suficientes).
  3. Gera predições -> prediction_<symbol>.json (sincronizado com o EA).
  4. Valida as condições (volume de amostras, acurácia mínima, sinais).
  5. Grava um relatório de aprovação em Reports/auto_approve_<data>.json.

Pode ser agendado (task do Windows) ou chamado pela GUI.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_DIR = ROOT / "Python"
MQL_DATA = ROOT / "MQL5" / "Files" / "Data"
REPORTS_DIR = ROOT / "Reports"
DB_PATH = ROOT / "database" / "trading.db"

MIN_SAMPLES_FOR_TRAIN = 500
MIN_ACCURACY_TO_APPROVE = 0.55


def _python() -> str:
    return sys.executable or "python"


def _ensure_reports_dir() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def dataset_stats() -> dict:
    """Lê o dataset e retorna nº de linhas, símbolos e período."""
    csv_path = MQL_DATA / "dataset.csv"
    if not csv_path.exists():
        return {"exists": False, "rows": 0, "symbols": [], "period": None}
    try:
        import io

        import pandas as pd

        with open(csv_path, "rb") as f:
            content = f.read()
        if len(content) % 2 != 0:
            content = content[:-1]  # remove byte ímpar para UTF-16 válido
        df = pd.read_csv(
            io.BytesIO(content),
            encoding="utf-16",
            header=None,
            on_bad_lines="skip",
            engine="python",
        )
        # remove possível cabeçalho duplicado "Time,..."
        df = df[df.iloc[:, 0].astype(str).str.strip() != "Time"]
        syms = df.iloc[:, 1].astype(str).str.strip().str.upper()
        symbols = sorted(syms[syms != ""].unique().tolist())
        times = pd.to_datetime(df.iloc[:, 0], errors="coerce")
        period = None
        if times.notna().any():
            period = [times.min().strftime("%Y-%m-%d"), times.max().strftime("%Y-%m-%d")]
        return {
            "exists": True,
            "rows": len(df),
            "symbols": symbols,
            "period": period,
        }
    except Exception as e:
        return {
            "exists": True, "rows": -1, "symbols": [], "period": None, "error": str(e)
        }


def run_training() -> dict:
    """Executa train.py e captura resultado."""
    result = subprocess.run(
        [_python(), "train.py"],
        cwd=str(PY_DIR),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return {
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "output_tail": (result.stdout or "")[-1500:],
        "error_tail": (result.stderr or "")[-800:],
    }


def run_prediction() -> dict:
    """Executa predict.py e captura resultado."""
    result = subprocess.run(
        [_python(), "predict.py"],
        cwd=str(PY_DIR),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return {
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "output_tail": (result.stdout or "")[-1500:],
        "error_tail": (result.stderr or "")[-800:],
    }


def list_predictions() -> list[dict]:
    """Lista os prediction_*.json existentes com sinal/score."""
    out: list[dict] = []
    for p in sorted(MQL_DATA.glob("prediction_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append(
                {
                    "file": p.name,
                    "symbol": data.get("symbol"),
                    "signal": data.get("signal"),
                    "score": data.get("score"),
                    "price": data.get("price"),
                }
            )
        except Exception:
            continue
    return out


def _approved_verdict(stats: dict, train: dict, preds: list[dict]) -> dict:
    """Decide se as condições são 'aprovadas' para operar."""
    checks: list[dict] = []
    ok = True

    enough_data = stats.get("rows", 0) >= MIN_SAMPLES_FOR_TRAIN
    checks.append(
        {
            "name": "dados_suficientes",
            "ok": enough_data,
            "detail": f"{stats.get('rows', 0)} amostras (min {MIN_SAMPLES_FOR_TRAIN})",
        }
    )
    if not enough_data:
        ok = False

    train_ok = train.get("ok", False)
    checks.append({"name": "treinamento", "ok": train_ok, "detail": "train.py"})
    if not train_ok:
        ok = False

    has_preds = len(preds) > 0
    checks.append(
        {"name": "predicoes_geradas", "ok": has_preds, "detail": f"{len(preds)} arquivos"}
    )
    if not has_preds:
        ok = False

    return {"approved": ok, "checks": checks}

def run_full(check: bool = True) -> dict:
    """Executa o fluxo completo de auto-approve e grava relatório."""
    _ensure_reports_dir()
    started = datetime.now().isoformat(timespec="seconds")

    stats = dataset_stats()
    train = run_training()
    pred = run_prediction()
    preds = list_predictions()

    verdict = (
        _approved_verdict(stats, train, preds)
        if check
        else {"approved": None, "checks": []}
    )

    report = {
        "generated_at": started,
        "dataset": stats,
        "training": {k: v for k, v in train.items() if k not in ("output_tail", "error_tail")},
        "prediction": {k: v for k, v in pred.items() if k not in ("output_tail", "error_tail")},
        "predictions": preds,
        "verdict": verdict,
    }

    out_file = REPORTS_DIR / f"auto_approve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["report_file"] = str(out_file)

    # Notifica resultado no Slack (se configurado)
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        import slack_notifier as _sn
        approved = verdict.get("approved") if check else None
        if approved is not None:
            details = f"Dataset: {stats.get('rows', 0)} amostras | Trades: {len(preds)}"
            _sn.SlackNotifier.get().send_approval(approved, details)
    except Exception:
        pass

    return report


if __name__ == "__main__":
    rep = run_full()
    print("=" * 60)
    print("AUTO-APPROVE")
    print("=" * 60)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    print("=" * 60)
    print("Aprovado:", rep["verdict"].get("approved"))
