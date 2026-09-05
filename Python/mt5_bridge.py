"""MT5 terminal path resolver and symbol mapping for XAU_AI_PRO.

Resolve dinamicamente o caminho do terminal MetaTrader 5,
eliminando o hardcoded path no pipeline.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# ============================================================
# CONFIGURACOES
# ============================================================

symbol_aliases = {
    "XAUUSD": ["XAUUSD", "XAUUSD.", "XAUUSDc", "XAUUSDm", "GOLD", "GOLD#", "XAUUSD.pro", "XAUUSD_i"],
    "BTCUSD": ["BTCUSD", "BTCUSD#", "BTCUSDc", "BTCUSDm", "BTCUSD.", "BTCUSD.pro"],
    "ETHUSD": ["ETHUSD", "ETHUSD#", "ETHUSDc", "ETHUSDm", "ETHUSD.", "ETHUSD.pro"],
    "EURUSD": ["EURUSD", "EURUSD#", "EURUSDc", "EURUSDm", "EURUSD.", "EURUSD.pro"],
    "GBPUSD": ["GBPUSD", "GBPUSD#", "GBPUSDc", "GBPUSDm", "GBPUSD.", "GBPUSD.pro"],
    "USDJPY": ["USDJPY", "USDJPY#", "USDJPYc", "USDJPYm", "USDJPY.", "USDJPY.pro"],
    "AUDUSD": ["AUDUSD", "AUDUSD#", "AUDUSDc", "AUDUSDm", "AUDUSD.", "AUDUSD.pro"],
    "USDCAD": ["USDCAD", "USDCAD#", "USDCADc", "USDCADm", "USDCAD.", "USDCAD.pro"],
    "NZDUSD": ["NZDUSD", "NZDUSD#", "NZDUSDc", "NZDUSDm", "NZDUSD.", "NZDUSD.pro"],
}

max_prediction_age_seconds = 300  # 5 minutes


def get_mt5_terminal_id():
    """Tenta encontrar o terminal ID do MT5."""
    appdata = os.getenv("APPDATA", "")
    if not appdata:
        return None

    mt5_base = Path(appdata) / "MetaQuotes" / "Terminal"
    if not mt5_base.exists():
        return None

    for item in mt5_base.iterdir():
        if item.is_dir() and len(item.name) == 32:
            if (item / "MQL5" / "Files").exists():
                return item.name
    return None


def get_mt5_files_path():
    """Resolve o caminho MT5 Files dinamicamente."""
    configured = os.getenv("XAU_AI_PRO_MT5_FILES")
    if configured:
        return Path(configured).expanduser()

    project_root = Path(__file__).resolve().parent.parent
    if project_root.parent.name.lower() == "files" and project_root.parent.parent.name.lower() == "mql5":
        return project_root.parent

    appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    terminal_root = appdata / "MetaQuotes" / "Terminal"
    candidates = list(terminal_root.glob("*/MQL5/Files")) if terminal_root.exists() else []
    populated = [path for path in candidates if (path / "Data" / "dataset.csv").exists()]
    if populated:
        return max(populated, key=lambda path: (path / "Data" / "dataset.csv").stat().st_mtime)
    if candidates:
        return max(candidates, key=lambda path: path.stat().st_mtime)
    return None


def get_mt5_data_path():
    """Retorna o caminho do diretorio Data no MT5 Files."""
    configured = os.getenv("XAU_AI_PRO_MQL_DATA")
    if configured:
        return Path(configured).expanduser()
    files_path = get_mt5_files_path()
    if files_path:
        return files_path / "Data"
    return Path.cwd() / "MQL5" / "Files" / "Data"


# Caminho resolvido dinamicamente
mt5_files_path = get_mt5_data_path()


def normalize_symbol(symbol):
    """Normaliza um symbol do broker para nome base.
    Ex: GOLD# -> XAUUSD, XAUUSDc -> XAUUSD
    """
    symbol = symbol.strip().upper()

    for suffix in ["C", "M", "#", "."]:
        if symbol.endswith(suffix) and len(symbol) > len(suffix):
            symbol = symbol[:-len(suffix)]

    for base, aliases in symbol_aliases.items():
        if symbol in [a.upper() for a in aliases]:
            return base

    return symbol


def is_prediction_stale(timestamp_str, max_age_seconds=max_prediction_age_seconds):
    """Verifica se um timestamp de predicao esta desatualizado."""
    try:
        from datetime import datetime
        pred_time = datetime.fromisoformat(timestamp_str)
        age_seconds = (datetime.now() - pred_time).total_seconds()
        return age_seconds > max_age_seconds
    except Exception:
        return True


def save_prediction_json(result, output_dir=None):
    """Salva JSON de predicao no diretorio MT5 Files/Data."""
    if output_dir is None:
        output_dir = mt5_files_path

    output_dir.mkdir(parents=True, exist_ok=True)

    symbol = result.get("symbol", "UNKNOWN")
    normalized = normalize_symbol(symbol)

    primary_path = output_dir / f"prediction_{normalized}.json"
    primary_path.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    if symbol != normalized:
        alt_path = output_dir / f"prediction_{symbol}.json"
        alt_path.write_text(
            json.dumps(result, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

    return str(primary_path)
