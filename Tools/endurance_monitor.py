# -*- coding: utf-8 -*-
"""ETAPA 15.9 - Endurance Monitor: coletor de metricas continuo.

Uso:
    python Tools/endurance_monitor.py              # roda indefinidamente
    python Tools/endurance_monitor.py --once       # amostra unica (teste)

Coleta (JSONL append-only, 1 linha por ciclo):
    - Heartbeat EA (system_status.json idade)
    - Dataset growth (bytes, delta desde ultima amostra)
    - Predicoes recentes (qtde arquivos < 600s)
    - Processos terminal64.exe / python.exe (memoria MB via psutil se disponivel)
    - Timestamps UTC

Saida: Logs/endurance_metrics.jsonl
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from app.utils.paths import get_mql_data_path

DATA_DIR = get_mql_data_path()
OUT = BASE / "Logs" / "endurance_metrics.jsonl"
INTERVAL = 300  # 5 minutos


def try_psutil():
    try:
        import psutil  # noqa
        return psutil
    except ImportError:
        return None


def proc_mem_mb(psutil, name):
    if psutil is None:
        return None
    total = 0.0
    found = False
    for p in psutil.process_iter(["name"]):
        try:
            if name.lower() in (p.info["name"] or "").lower():
                total += p.memory_info().rss / (1024 * 1024)
                found = True
        except Exception:
            continue
    return round(total, 1) if found else None


def collect(last_dataset_bytes):
    now = datetime.now(timezone.utc)
    sample = {"ts_utc": now.isoformat()}

    # 1. Heartbeat do EA
    ss = DATA_DIR / "system_status.json"
    if ss.exists():
        age = time.time() - ss.stat().st_mtime
        sample["status_age_sec"] = int(age)
        sample["ea_heartbeat_ok"] = age <= 120
    else:
        sample["status_age_sec"] = -1
        sample["ea_heartbeat_ok"] = False

    # 2. Crescimento do dataset
    ds = DATA_DIR / "dataset.csv"
    if ds.exists():
        b = ds.stat().st_size
        sample["dataset_bytes"] = b
        sample["dataset_delta_bytes"] = (
            b - last_dataset_bytes if last_dataset_bytes else 0
        )
        last_dataset_bytes = b

    # 3. Predicoes frescas (< 600s)
    fresh = 0
    pred_dir = DATA_DIR.parent
    if pred_dir.exists():
        for f in pred_dir.glob("prediction_*.json"):
            try:
                if time.time() - f.stat().st_mtime < 600:
                    fresh += 1
            except OSError:
                continue
    sample["predictions_fresh"] = fresh

    # 4. Recursos dos processos
    psutil = try_psutil()
    sample["terminal_mem_mb"] = proc_mem_mb(psutil, "terminal64.exe")
    sample["python_mem_mb"] = proc_mem_mb(psutil, "python.exe")

    return sample, last_dataset_bytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"[ENDURANCE] Coletor iniciado -> {OUT}")
    print("[ENDURANCE] Intervalo:", INTERVAL, "s | Ctrl+C para parar")

    last_ds = 0
    while True:
        try:
            sample, last_ds = collect(last_ds)
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample) + "\n")
            print(json.dumps(sample))
        except KeyboardInterrupt:
            print("\n[ENDURANCE] Coleta interrompida pelo operador.")
            break
        except Exception as e:
            print("[ENDURANCE][ERRO]", e)

        if args.once:
            break
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
