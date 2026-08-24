# -*- coding: utf-8 -*-
"""Auto-retrain do XAU_AI_PRO.

Carrega o dataset atual, verifica se cada simbolo acumulou candles novos
suficientes (RETRAIN_MIN_NEW_CANDLES) desde o ultimo treino registrado no
banco (database/trading.db) e retreina somente os que precisam.

Uso:
    python auto_retrain.py                # retreina M5 (padrao)
    python auto_retrain.py M5 H1 H4       # timeframes especificos
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("auto_retrain")

try:
    from sentry_config import capture_training_error
except ImportError:  # pragma: no cover
    def capture_training_error(exc):  # type: ignore
        logger.error("Sentry nao disponivel: %s", exc)


def main() -> int:
    from pipeline import Pipeline

    timeframes = sys.argv[1:] or ["M5"]
    started = time.time()

    pipeline = Pipeline()
    pipeline.load_dataset()
    pipeline.clean_data()
    pipeline.generate_features()

    print(f"\n=== AUTO-RETRAIN | timeframes={timeframes} | simbolos={len(pipeline.symbols)} ===")
    summary = pipeline.maybe_retrain_all(timeframes=timeframes)

    if not summary:
        print("\nNenhum simbolo precisou de retreino (sem candles novos suficientes).")
    else:
        print(f"\nRetreinos executados: {len(summary)}")
        for key, result in sorted(summary.items()):
            if result.get("status") == "success":
                m = result.get("metrics", {})
                print(f"  {key}: success | acc={m.get('accuracy', 0) * 100:.2f}% | f1={m.get('f1_score', 0):.2f}")
            else:
                print(f"  {key}: error | {result.get('error', 'desconhecido')}")
                if result.get("error"):
                    capture_training_error(result["error"])

    print(f"\nAuto-retrain concluido em {time.time() - started:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
