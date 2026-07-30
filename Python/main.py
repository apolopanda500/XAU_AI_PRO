"""Main entry point for XAU_AI_PRO."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

COMMANDS = ("train", "predict", "help")

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _usage() -> None:
    """Exibe mensagem de uso do CLI."""
    print("Usage: python main.py [train|predict|help]")


def main() -> None:
    """Ponto de entrada principal da aplicação."""
    if len(sys.argv) < 2:
        _usage()
        sys.exit(1)

    arg = sys.argv[1].lower().strip()

    if arg == "help":
        _usage()
        return

    if arg == "predict":
        sys.path.append(str(BASE_DIR))
        import predict

        predict.predict()
    elif arg == "train":
        sys.path.append(str(BASE_DIR))
        import train

        train.train()
    else:
        print(f"Unknown command: {arg}")
        _usage()
        sys.exit(1)


if __name__ == "__main__":
    main()

