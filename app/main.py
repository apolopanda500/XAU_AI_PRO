"""
Ponto de entrada do app XAU_AI_PRO v1.2.0.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Adiciona raiz do projeto ao PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import main

if __name__ == "__main__":
    main()
