# -*- coding: utf-8 -*-
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
        raise


if __name__ == "__main__":
    main()
