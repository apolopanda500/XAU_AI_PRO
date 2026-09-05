"""
XAU AI PRO - ConfigStore
Gerenciador de configuração, credenciais de API e autenticação (login).

Usado pela GUI (Ultimate/gui.py) para salvar API keys e usuário/senha
de forma local, com hash SHA-256 + salt. Nunca armazena senha em texto puro.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# CAMINHOS
# ============================================================
# Suporte a execucao dentro do PyInstaller (onefile coloca em _MEIPASS temporario)
_MEIPASS = os.getenv("_MEIPASS")
if _MEIPASS and Path(_MEIPASS).exists():
    ROOT = Path(_MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent.parent
ULT = ROOT / "Ultimate"
# Pasta de dados persistentes (config/db) definida no app_main.py; fallback para local
_DATA_DIR = os.getenv("XAU_AI_PRO_DATA")
if _DATA_DIR:
    _data_dir = Path(_DATA_DIR)
else:
    _data_dir = ULT
_data_dir.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = Path(os.getenv("XAU_AI_PRO_CONFIG", _data_dir / "config.json")).expanduser()
DB_PATH = _data_dir / "trading.db"


# ============================================================
# HELPERS DE HASH
# ============================================================
def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Retorna (hash_hex, salt_hex). Se salt for None, gera um novo."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()
    return digest, salt


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    digest, _ = _hash_password(password, salt)
    return secrets.compare_digest(digest, expected_hash)


# ============================================================
# CONFIG
# ============================================================
DEFAULTS: dict = {
    "users": {},  # {username: {"hash": ..., "salt": ...}}
    "session": None,
    "remember_me": False,  # "deixar logado" ao abrir o app
    "theme": "dark",  # tema da interface: dark | light
    "app": {
        "symbols": "XAUUSD, XAUUSDc, BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, SPX500, US30",
        "auto_connect_mt5": True,  # conectar ao MT5 automaticamente ao abrir
        "sync_robot": True,  # sincronizar status do robô (EA) com o MT5
        "start_services_on_login": False,  # subir backend/dashboard ao logar
    },
    "api": {
        "broker_api_key": "",
        "broker_api_secret": "",
        "alpha_api_key": "",
        "brave_api_key": "",
        "github_token": "",
        "gitlab_base_url": "https://gitlab.com",
        "gitlab_project_path": "",
        "gitlab_token": "",
        "figma_token": "",
        "figma_team_id": "",
        "figma_file_key": "",
        "litellm_port": 4000,
        "backend_port": 8000,
        "dashboard_port": 8501,
        "live_provider": "auto",  # auto | mt5 | yfinance
        "refresh_seconds": 5,
        "mt5_terminal_path": "C:\Program Files\MetaTrader 5\terminal64.exe",
        "slack_webhook_url": "",     # Incoming Webhook URL (https://hooks.slack.com/services/...)
        "slack_enabled": True,       # Ativa/desativa notificações Slack
        "slack_notify_trades": True, # Notificar abertura/fechamento de posições
        "slack_notify_errors": True, # Notificar erros críticos
        "slack_notify_risk": True,   # Notificar drawdown, circuit breaker, etc.
        "mcp_endpoint": "",
        "mcp_plugins_dir": "mcp",
    },
    "ui": {
        "theme": "dark",
        "wallpaper_enabled": True,
        "animations_enabled": True,
        "sidebar_collapsed": False,
    },
    "trading": {
        "asset": "XAUUSD",
        "timeframe": "M5",
        "max_risk_pct": 1.0,
        "max_lot": 0.1,
        "stop_loss_pct": 2.0,
        "take_profit_pct": 5.0,
    },
    "updated_at": None,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        cfg = dict(DEFAULTS)
        cfg = json.loads(json.dumps(cfg))  # deep copy
        save_config(cfg)
        return cfg
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        # mescla com defaults para nunca faltar chaves
        merged = json.loads(json.dumps(DEFAULTS))
        for k, v in cfg.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
    except Exception:
        return json.loads(json.dumps(DEFAULTS))


def save_config(cfg: dict) -> None:
    cfg["updated_at"] = datetime.now(timezone.utc).isoformat()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_api_config() -> dict:
    return load_config()["api"]


def save_api_config(api_cfg: dict) -> None:
    cfg = load_config()
    cfg["api"].update(api_cfg)
    save_config(cfg)


# ============================================================
# TEMA / APLICATIVO / SESSAO / UI
# ============================================================
VALID_THEMES = ["dark", "light", "cyberpunk", "crypto", "midnight"]


def get_theme() -> str:
    return load_config().get("theme", "dark")


def set_theme(theme: str) -> None:
    cfg = load_config()
    cfg["theme"] = theme if theme in VALID_THEMES else "dark"
    save_config(cfg)


def get_ui_config() -> dict:
    return load_config().get("ui", {})


def save_ui_config(ui_cfg: dict) -> None:
    cfg = load_config()
    cfg.setdefault("ui", {}).update(ui_cfg)
    save_config(cfg)


def get_app_config() -> dict:
    return load_config()["app"]


def save_app_config(app_cfg: dict) -> None:
    cfg = load_config()
    cfg["app"].update(app_cfg)
    save_config(cfg)


def get_trading_config() -> dict:
    return load_config()["trading"]


def save_trading_config(trading_cfg: dict) -> None:
    cfg = load_config()
    cfg["trading"].update(trading_cfg)
    save_config(cfg)


def get_remember_me() -> bool:
    return bool(load_config().get("remember_me"))


def set_remember_me(value: bool) -> None:
    cfg = load_config()
    cfg["remember_me"] = bool(value)
    save_config(cfg)


# ============================================================
# AUTENTICAÇÃO
# ============================================================
def create_user(username: str, password: str) -> bool:
    """Cria um usuário. Retorna False se já existir."""
    cfg = load_config()
    username = username.strip()
    if not username or not password:
        return False
    if username in cfg["users"]:
        return False
    digest, salt = _hash_password(password)
    cfg["users"][username] = {"hash": digest, "salt": salt}
    save_config(cfg)
    return True


def authenticate(username: str, password: str) -> bool:
    cfg = load_config()
    username = username.strip()
    rec = cfg["users"].get(username)
    if not rec:
        return False
    return _verify_password(password, rec["salt"], rec["hash"])


def ensure_default_user() -> None:
    """Cria o usuário padrão admin/admin na primeira execução, se não houver."""
    cfg = load_config()
    if not cfg["users"]:
        create_user("admin", "admin")
    cfg = load_config()
    if cfg["session"] is None:
        cfg["session"] = None
        save_config(cfg)


def set_session(username: str | None) -> None:
    cfg = load_config()
    cfg["session"] = username
    save_config(cfg)


def get_session() -> str | None:
    return load_config().get("session")


# ============================================================
# BANCO DE DADOS (SQLite)
# ============================================================
def ensure_schema(db_path: Path = DB_PATH) -> None:
    """Garante que o banco tenha as tabelas usadas pelo sistema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS account(
            id INTEGER PRIMARY KEY,
            login TEXT, balance REAL, equity REAL, margin REAL,
            company TEXT, server TEXT
        );
        CREATE TABLE IF NOT EXISTS predictions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, signal TEXT, confidence REAL, score REAL,
            price REAL, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS trades(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, side TEXT, lot REAL, entry REAL, exit_price REAL,
            pnl REAL, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS daily_pnl(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE, pnl REAL
        );
        """
    )
    conn.commit()
    conn.close()


def db_connect(db_path: Path = DB_PATH):
    return sqlite3.connect(str(db_path))




