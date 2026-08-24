"""Módulo de predição multi-ativo do XAU_AI_PRO."""

from __future__ import annotations

import sys
from pathlib import Path

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.append(str(BASE_DIR))

# Sentry integration (importar sentry_config já inicializa o SDK automaticamente)
try:
    from sentry_config import capture_prediction_error
except ImportError:
    pass

from pipeline import Pipeline


def predict() -> None:
    """Executa a predição multi-ativa usando o Pipeline."""
    print("=" * 30)
    print(" XAU_AI_PRO AI PREDICT (MULTI-SYMBOL)")
    print("=" * 30)

    try:
        pipeline = Pipeline()
        pipeline.load_dataset()
        pipeline.clean_data()
        pipeline.generate_features()
        predictions = pipeline.predict_all(timeframes=["M5"])

        print()
        print("Predições geradas:", len(predictions))
        
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
                
                # Captura erro no Sentry
                try:
                    capture_prediction_error(
                        symbol=symbol,
                        prediction_type="multi_symbol",
                        error_msg=error_msg
                    )
                except:
                    pass
        
        print(f"\nResumo: {signals_count} sinais, {errors_count} erros")
        
    except Exception as e:
        print(f"Erro critico na predicao: {e}")
        try:
            capture_prediction_error(
                symbol="ALL",
                prediction_type="pipeline",
                error_msg=str(e)
            )
        except:
            pass
        raise


if __name__ == "__main__":
    predict()
