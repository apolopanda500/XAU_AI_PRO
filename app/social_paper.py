from __future__ import annotations

import copy
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.subscriptions import get_subscription, require_entitlement
from app.utils.paths import get_data_dir

_LOCK = threading.RLock()
_DEFAULT_USER_ID = "local"
_STRATEGIES: tuple[dict[str, Any], ...] = (
    {
        "id": "trend-filter-paper",
        "name": "Trend Filter",
        "description": "Perfil de tendência com confirmação de timeframe superior.",
        "risk_profile": "conservative",
        "timeframes": ["M15", "H1", "H4"],
        "symbols": ["XAUUSD", "EURUSD"],
        "paper_only": True,
    },
    {
        "id": "mean-reversion-paper",
        "name": "Mean Reversion",
        "description": "Perfil de reversão à média para estudo em paper/demo.",
        "risk_profile": "moderate",
        "timeframes": ["M5", "M15"],
        "symbols": ["XAUUSD"],
        "paper_only": True,
    },
    {
        "id": "session-breakout-paper",
        "name": "Session Breakout",
        "description": "Perfil de rompimento de sessão com spread e horário sob observação.",
        "risk_profile": "moderate",
        "timeframes": ["M5", "M15"],
        "symbols": ["XAUUSD", "GBPUSD"],
        "paper_only": True,
    },
)


def _user_id(value: str | None) -> str:
    return str(value or os.getenv("XAU_USER_ID") or _DEFAULT_USER_ID).strip()[:80] or _DEFAULT_USER_ID


def _path() -> Path:
    return Path(os.getenv("XAU_SOCIAL_PAPER_FILE", str(get_data_dir() / "social_paper.json"))).expanduser()


def _load() -> dict[str, list[str]]:
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): [str(item) for item in value] if isinstance(value, list) else [] for key, value in raw.items()}


def _save(data: dict[str, list[str]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_strategies(user_id: str | None = None) -> list[dict[str, Any]]:
    subscription = get_subscription(user_id)
    available = bool(subscription.get("entitlements", {}).get("social_paper"))
    following = set(_load().get(_user_id(user_id), []))
    return [{**copy.deepcopy(item), "available": available, "following": item["id"] in following} for item in _STRATEGIES]


def following_strategies(user_id: str | None = None) -> list[dict[str, Any]]:
    ids = set(_load().get(_user_id(user_id), []))
    return [copy.deepcopy(item) for item in _STRATEGIES if item["id"] in ids]


def follow_strategy(strategy_id: str, user_id: str | None = None) -> dict[str, Any]:
    require_entitlement("social_paper", user_id)
    normalized = str(strategy_id or "").strip().lower()
    strategy = next((item for item in _STRATEGIES if item["id"] == normalized), None)
    if strategy is None:
        raise LookupError(f"estratégia inexistente: {strategy_id}")
    with _LOCK:
        data = _load()
        ids = set(data.get(_user_id(user_id), []))
        ids.add(normalized)
        data[_user_id(user_id)] = sorted(ids)
        _save(data)
    return {**copy.deepcopy(strategy), "following": True, "execution_mode": "paper_demo", "live_execution": False}


def unfollow_strategy(strategy_id: str, user_id: str | None = None) -> dict[str, Any]:
    normalized = str(strategy_id or "").strip().lower()
    with _LOCK:
        data = _load()
        ids = set(data.get(_user_id(user_id), []))
        ids.discard(normalized)
        data[_user_id(user_id)] = sorted(ids)
        _save(data)
    return {"strategy_id": normalized, "following": False, "execution_mode": "paper_demo", "live_execution": False}
