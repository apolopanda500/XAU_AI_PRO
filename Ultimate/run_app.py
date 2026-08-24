"""
XAU AI PRO — Entry point da interface desktop.
Uso:
    python Ultimate/run_app.py

Abre a GUI (login + mercado em tempo real + treinamento + API).
Para usar o modo antigo (console ASCII + streamlit), use:
    python Ultimate/launcher.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Garante os imports relativos ao Ultimate
ULT = Path(__file__).resolve().parent
if str(ULT) not in sys.path:
    sys.path.insert(0, str(ULT))


def main() -> None:
    from gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    try:
        os.chdir(ULT)
    except Exception:
        pass
    main()
