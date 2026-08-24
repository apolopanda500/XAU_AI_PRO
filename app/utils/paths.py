"""
Utilitários de caminho para o app XAU_AI_PRO.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Retorna a pasta raiz do projeto (ou _MEIPASS no executável PyInstaller)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """Pasta de dados persistentes (fora do _MEIPASS quando empacotado)."""
    env = os.getenv("XAU_AI_PRO_DATA")
    if env:
        return Path(env).expanduser()
    base = get_base_dir()
    # Se estiver empacotado, usa AppData do usuário para persistência
    if getattr(sys, "frozen", False):
        appdata = Path(os.getenv("APPDATA", base))
        data = appdata / "XAU_AI_PRO"
        data.mkdir(parents=True, exist_ok=True)
        return data
    return base / "app" / "data"


def ensure_paths() -> None:
    """Garante que as pastas necessárias existam."""
    for p in (
        get_data_dir(),
        get_base_dir() / "MQL5" / "Files" / "Data",
        get_base_dir() / "Python" / "models",
        get_base_dir() / "Reports",
        get_base_dir() / "Logs",
    ):
        p.mkdir(parents=True, exist_ok=True)


def get_config_path() -> Path:
    return Path(os.getenv("XAU_AI_PRO_CONFIG", get_data_dir() / "config.json")).expanduser()


def get_db_path() -> Path:
    return get_data_dir() / "trading.db"


def get_mql_data_path() -> Path:
    return get_base_dir() / "MQL5" / "Files" / "Data"


def get_python_dir() -> Path:
    return get_base_dir() / "Python"
