"""Main entry point for XAU_AI_PRO."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Sentry: importar sentry_config já inicializa o SDK automaticamente (auto-init no final do módulo).
try:
    from sentry_config import capture_training_error, capture_prediction_error
except ImportError:
    logging.warning("Sentry nao disponivel - instale com: pip install sentry-sdk")

COMMANDS = ("train", "predict", "dashboard", "help")

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _usage() -> None:
    """Exibe mensagem de uso do CLI."""
    print("Usage: python main.py [train|predict|dashboard|help]")


def main() -> None:
    """Ponto de entrada principal da aplicação."""
    if len(sys.argv) < 2:
        _usage()
        sys.exit(1)

    arg = sys.argv[1].lower().strip()

    if arg == "help":
        _usage()
        return

    sys.path.append(str(BASE_DIR))

    if arg == "predict":
        import predict

        predict.predict()
    elif arg == "train":
        import train

        train.train()
    elif arg == "dashboard":
        import dashboard.app as dashboard_app

        dashboard_app.main()
    else:
        print(f"Unknown command: {arg}")
        _usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
