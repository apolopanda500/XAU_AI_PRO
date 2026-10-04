# -*- coding: utf-8 -*-
"""Módulo de predição multi-ativo do XAU_AI_PRO."""

from __future__ import annotations

import sys
from pathlib import Path

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.append(str(BASE_DIR))

import logging

log = logging.getLogger(__name__)

from pipeline import Pipeline


def predict() -> None:
    """Executa a predição multi-ativa usando o Pipeline."""
    print("=" * 30)
    print(" XAU_AI_PRO AI PREDICT (MULTI-SYMBOL)")
    print("=" * 30)
    if log:
        # exemplo: log estruturado com atributos (vira coluna pesquisavel no Logs)
        log.info("predict iniciado", extra={"comando": "predict", "timeframe": "M5"})

    try:
        pipeline = Pipeline()
        pipeline.load_dataset()
        pipeline.clean_data()
        pipeline.generate_features()
        predictions = pipeline.predict_all(timeframes=["M5"])

        print()
        print("Predições geradas:", len(predictions))
        if log:
            log.info("predicoes geradas", extra={"total": len(predictions), "timeframes": "M5"})
        
        signals_count = 0
        errors_count = 0
        
        for symbol, result in predictions.items():
            if isinstance(result, dict) and "signal" in result:
                print(
                    f"  {symbol} | {result['signal']} | "
                    f"{result.get('confidence', 0):.1f}% | "
                    f"{result.get('score', 0):.1f}"
                )
                signals_count += 1
            else:
                error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
                print(f"  {symbol} | erro: {error_msg}")
                errors_count += 1
        
        print(f"\nResumo: {signals_count} sinais, {errors_count} erros")
        
    except Exception as e:
        print(f"Erro critico na predicao: {e}")
        # O `except` nao engolia mais nada: chamava `capture_prediction_error`,
        # que foi removida com o Sentry em 04/10/2026. O `NameError` que vinha
        # do tratamento DELETAVA a excecao original que operator estava vendo.
        # Agora o log recebe a causa e a excecao continua subindo.
        log.exception("predicao falhou")
        raise


if __name__ == "__main__":
    predict()
