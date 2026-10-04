# -*- coding: utf-8 -*-
"""Módulo de treinamento multi-ativo do XAU_AI_PRO."""

from __future__ import annotations

import sys
from pathlib import Path

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.append(str(BASE_DIR))

from pipeline import Pipeline


def train() -> None:
    """Executa o treinamento multi-ativo usando o Pipeline."""
    print("=" * 30)
    print(" XAU_AI_PRO TRAINING ENGINE")
    print("=" * 30)

    try:
        pipeline = Pipeline()
        pipeline.load_dataset()
        pipeline.clean_data()
        pipeline.generate_features()
        summary = pipeline.train_all_models(timeframes=["M5"])

        print()
        print("Treinamento concluído.")
        print("Resumo:")
        
        total_trades = 0
        successful_models = 0
        
        for symbol, info in summary.items():
            status = info.get("status", "unknown")
            if status == "success":
                metrics = info.get("metrics", {})
                accuracy = metrics.get('accuracy', 0) * 100
                f1 = metrics.get('f1_score', 0)
                print(
                    f"  {symbol}: {status} | "
                    f"acc={accuracy:.2f}% | "
                    f"f1={f1:.2f}"
                )
                successful_models += 1
            else:
                error_msg = info.get('error', 'Unknown error')
                print(f"  {symbol}: {status} | {error_msg}")

    except Exception as e:
        print(f"Erro critico no treinamento: {e}")
        raise


if __name__ == "__main__":
    train()
