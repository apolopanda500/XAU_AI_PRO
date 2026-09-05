"""Main entry point for XAU_AI_PRO."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Forca UTF-8 no stdout/stderr para evitar UnicodeEncodeError em consoles
# com encoding cp1252 (padrao no Windows).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Sentry: importar sentry_config inicializa o SDK automaticamente (auto-init no final do modulo).
try:
    from sentry_config import capture_training_error, capture_prediction_error
except ImportError:
    logging.warning("Sentry nao disponivel - instale com: pip install sentry-sdk")

try:
    from sentry_config import start_sentry_session, end_sentry_session
except Exception:
    def start_sentry_session():  # noqa: E305
        pass

    def end_sentry_session():  # noqa: E305
        pass

COMMANDS = ("train", "predict", "dashboard", "help")

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _usage() -> None:
    """Exibe mensagem de uso do CLI."""
    print("Uso: XAU_AI_PRO.exe [predict|train|help]")


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

    start_sentry_session()
    try:
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
    except SystemExit:
        raise
    except Exception:
        # Nao fecha a sessao aqui: a excecao nao tratada abaixo faz o
        # excepthook do SDK marcar a sessao como 'crashed' (Release Health).
        raise
    else:
        end_sentry_session()


if __name__ == "__main__":
    main()
