"""
Gerenciador de configuracao persistente do app XAU_AI_PRO.
Salva em JSON com merge de defaults para nunca quebrar em atualizacoes.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.paths import get_config_path


DEFAULT_CONFIG: dict[str, Any] = {
    "app_version": "1.2.0",
    "theme": "mexc_dark",
    "language": "pt_BR",
    "session": None,
    "remember_me": False,
    "users": {},
    "window": {"width": 1280, "height": 800, "maximized": False},
    "market": {
        "symbols": [
            "XAUUSD", "XAUUSDc", "BTCUSD", "ETHUSD", "EURUSD",
            "GBPUSD", "USDJPY", "AUDUSD", "SPX500", "US30",
        ],
        "futures": ["BTC=F", "ES=F", "NQ=F", "YM=F", "GC=F"],
        "mode": "spot",
        "provider": "auto",
        "refresh_seconds": 3,
        "alert_change_pct": 2.0,
    },
    "mt5": {
        "auto_connect": True,
        "terminal_path": r"C:\Program Files\MetaTrader 5\terminal64.exe",
        "magic_number": 2026001,
        "filling_mode": "ioc",
    },
    "trading": {
        "default_symbol": "XAUUSD",
        "timeframe": "M5",
        "risk_percent": 1.0,
        "max_lot": 0.5,
        "max_spread_points": 50,
        "stop_loss_points": 300,
        "take_profit_points": 600,
        "max_daily_loss_pct": 5.0,
        "max_drawdown_pct": 15.0,
    },
    "learning": {
        "enabled": True,
        "daily_time": "02:00",
        "interval_minutes": 60,
        "min_new_candles": 10,
        "keep_models": 10,
        "auto_sync_predictions": True,
    },
    "api": {
        "backend_port": 8000,
        "dashboard_port": 8501,
        "litellm_port": 4000,
        "brave_api_key": "",
        "github_token": "",
        "figma_token": "",
        "figma_team_id": "",
        "alpha_vantage_key": "",
    },
    "notifications": {
        "enabled": True,
        "on_trade": True,
        "on_learning": True,
        "on_error": True,
    },
    "updated_at": None,
}


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_config_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cfg = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            cfg = self._deep_copy(DEFAULT_CONFIG)
            self._save(cfg)
            return cfg
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        return self._merge(self._deep_copy(DEFAULT_CONFIG), raw)

    @staticmethod
    def _deep_copy(obj: Any) -> Any:
        return json.loads(json.dumps(obj))

    @staticmethod
    def _merge(defaults: Any, override: Any) -> Any:
        if isinstance(defaults, dict) and isinstance(override, dict):
            result = dict(defaults)
            for key, value in override.items():
                if key in result:
                    result[key] = ConfigManager._merge(result[key], value)
                else:
                    result[key] = value
            return result
        return override

    def _save(self, cfg: dict[str, Any] | None = None) -> None:
        if cfg is None:
            cfg = self._cfg
        cfg["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self._cfg
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def set(self, *keys: str, value: Any) -> None:
        if not keys:
            return
        node = self._cfg
        for key in keys[:-1]:
            if key not in node or not isinstance(node[key], dict):
                node[key] = {}
            node = node[key]
        node[keys[-1]] = value
        self._save()

    def all(self) -> dict[str, Any]:
        return self._deep_copy(self._cfg)

    def save_all(self, cfg: dict[str, Any]) -> None:
        self._cfg = self._merge(self._deep_copy(DEFAULT_CONFIG), cfg)
        self._save()

    # Autenticacao
    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        return digest, salt

    def create_user(self, username: str, password: str) -> bool:
        username = username.strip()
        if not username or not password:
            return False
        users = self._cfg.setdefault("users", {})
        if username in users:
            return False
        digest, salt = self._hash_password(password)
        users[username] = {"hash": digest, "salt": salt}
        self._save()
        return True

    def authenticate(self, username: str, password: str) -> bool:
        username = username.strip()
        rec = self._cfg.get("users", {}).get(username)
        if not rec:
            return False
        digest, _ = self._hash_password(password, rec["salt"])
        return secrets.compare_digest(digest, rec["hash"])

    def ensure_default_user(self) -> None:
        if not self._cfg.get("users"):
            self.create_user("admin", "admin")

    def set_session(self, username: str | None) -> None:
        self.set("session", value=username)

    def get_session(self) -> str | None:
        return self._cfg.get("session")


_config: ConfigManager | None = None


def get_config() -> ConfigManager:
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config

