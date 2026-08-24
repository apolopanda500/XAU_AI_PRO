"""Export helpers for XAU_AI_PRO.

Usa o mt5_bridge para resolver caminho dinamico do terminal.
"""

import json
from pathlib import Path
import sys
import os

# Importar mt5_bridge
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mt5_bridge import mt5_files_path, normalize_symbol, save_prediction_json


def save_prediction(result, output_path: str = None):
    """Salva JSON de predicao.
    
    Se output_path for None, usa o caminho dinamico do terminal MT5.
    """
    if output_path is None:
        # Usar mt5_bridge para resolver caminho dinamicamente
        return save_prediction_json(result)
    else:
        # Fallback para output_path explicito
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
        return path


def get_output_dir():
    """Retorna o diretorio de output para arquivos MT5."""
    return mt5_files_path / "Data"
