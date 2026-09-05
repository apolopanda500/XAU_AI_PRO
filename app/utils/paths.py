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
        get_mql_data_path(),
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
    configured = os.getenv("XAU_AI_PRO_MQL_DATA")
    if configured:
        return Path(configured).expanduser()

    base = get_base_dir()
    if base.parent.name.lower() == "files" and base.parent.parent.name.lower() == "mql5":
        return base.parent / "Data"

    bundled = base / "MQL5" / "Files" / "Data"
    if bundled.exists():
        return bundled

    appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    terminal_root = appdata / "MetaQuotes" / "Terminal"
    candidates = list(terminal_root.glob("*/MQL5/Files/Data")) if terminal_root.exists() else []
    populated = [path for path in candidates if (path / "dataset.csv").exists()]
    if populated:
        return max(populated, key=lambda path: (path / "dataset.csv").stat().st_mtime)
    if candidates:
        return max(candidates, key=lambda path: path.stat().st_mtime)
    return bundled


def get_python_dir() -> Path:
    return get_base_dir() / "Python"
