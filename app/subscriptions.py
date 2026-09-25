from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.paths import get_data_dir

_LOCK = threading.RLock()
_DEFAULT_USER_ID = "local"
_STATE_VERSION = 2
_ACTIVE_STATUSES = {"active", "local_active"}

_PLAN_CATALOG: dict[str, dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Free",
        "description": "Operação local básica em paper/demo.",
        "reference_price_monthly": 0,
        "currency": "BRL",
        "billing_mode": "local_only",
        "entitlements": {
            "paper_execution": True,
            "core_market_data": True,
            "price_alerts": True,
            "advanced_analytics": False,
            "advanced_audit": False,
            "ai_signals": True,
            "economic_calendar": False,
            "multi_account": False,
            "social_paper": False,
            "priority_support": False,
        },
        "limits": {"workspaces": 1, "alerts": 10, "ai_signals_per_day": 25, "paper_strategies": 0},
        "features": ["Paper/demo", "Mercado principal", "Alertas de preço", "IA básica"],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "description": "Desk local completo para estudo, automação paper e análise avançada.",
        "reference_price_monthly": 49,
        "currency": "BRL",
        "billing_mode": "local_only",
        "entitlements": {
            "paper_execution": True,
            "core_market_data": True,
            "price_alerts": True,
            "advanced_analytics": True,
            "advanced_audit": False,
            "ai_signals": True,
            "economic_calendar": True,
            "multi_account": True,
            "social_paper": True,
            "priority_support": False,
        },
        "limits": {"workspaces": 5, "alerts": 100, "ai_signals_per_day": 500, "paper_strategies": 3},
        "features": ["Tudo do Free", "Analytics avançado", "Calendário econômico", "Social paper", "5 workspaces"],
    },
    "business": {
        "id": "business",
        "name": "Business",
        "description": "Operação local ampliada para estratégias paper e análise de equipe.",
        "reference_price_monthly": 149,
        "currency": "BRL",
        "billing_mode": "local_only",
        "entitlements": {
            "paper_execution": True,
            "core_market_data": True,
            "price_alerts": True,
            "advanced_analytics": True,
            "advanced_audit": True,
            "ai_signals": True,
            "economic_calendar": True,
            "multi_account": True,
            "social_paper": True,
            "priority_support": True,
        },
        "limits": {"workspaces": 20, "alerts": 1000, "ai_signals_per_day": 5000, "paper_strategies": 20},
        "features": ["Tudo do Pro", "20 workspaces", "20 estratégias paper", "Auditoria avançada", "Suporte prioritário"],
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _user_id(value: str | None) -> str:
    normalized = str(value or os.getenv("XAU_USER_ID") or _DEFAULT_USER_ID).strip()
    return normalized[:80] if normalized else _DEFAULT_USER_ID


def _path() -> Path:
    return Path(os.getenv("XAU_SUBSCRIPTION_FILE", str(get_data_dir() / "subscriptions.json"))).expanduser()


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _catalog_digest() -> str:
    return _digest({"plans": _PLAN_CATALOG})


def _empty_state() -> dict[str, Any]:
    payload = {"version": _STATE_VERSION, "users": {}, "updated_at": _now()}
    return {**payload, "integrity_sha256": _digest(payload)}


def _normalized_record(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    plan_id = str(value.get("plan_id", "")).strip().lower()
    if plan_id not in _PLAN_CATALOG:
        return None
    status = str(value.get("status", "local_active")).strip().lower()
    if status not in _ACTIVE_STATUSES | {"expired", "revoked"}:
        return None
    expires_at = value.get("expires_at")
    if expires_at is not None and _parse_time(expires_at) is None:
        return None
    return {
        "plan_id": plan_id,
        "status": status,
        "source": "local",
        "activated_at": str(value.get("activated_at") or _now()),
        "expires_at": str(expires_at) if expires_at else None,
        "billing": "not_configured",
    }


def _migrate_v1(raw: dict[str, Any]) -> dict[str, Any]:
    users = raw.get("users") if isinstance(raw.get("users"), dict) else {}
    normalized = {str(user_id): record for user_id, value in users.items() if (record := _normalized_record(value)) is not None}
    return {"version": _STATE_VERSION, "users": normalized, "updated_at": _now(), "migrated_from": 1}


def _load() -> tuple[dict[str, Any], str]:
    path = _path()
    if not path.exists():
        return _empty_state(), "default"
    try:
        if path.stat().st_size > 1_048_576:
            return _empty_state(), "invalid"
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return _empty_state(), "corrupt"
    if not isinstance(raw, dict):
        return _empty_state(), "invalid"
    version = raw.get("version")
    if version == 1:
        return _migrate_v1(raw), "migrated_unverified"
    if version != _STATE_VERSION or not isinstance(raw.get("users"), dict):
        return _empty_state(), "unsupported_version"
    payload = {key: value for key, value in raw.items() if key != "integrity_sha256"}
    if not isinstance(raw.get("integrity_sha256"), str) or not hmac.compare_digest(str(raw["integrity_sha256"]), _digest(payload)):
        return _empty_state(), "integrity_error"
    return {"version": _STATE_VERSION, "users": raw["users"], "updated_at": str(raw.get("updated_at") or _now())}, "verified"


def _save(state: dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": _STATE_VERSION,
        "users": state.get("users") if isinstance(state.get("users"), dict) else {},
        "updated_at": _now(),
    }
    persisted = {**payload, "integrity_sha256": _digest(payload)}
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(persisted, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def list_plans() -> list[dict[str, Any]]:
    catalog_hash = _catalog_digest()
    return [{**copy.deepcopy(plan), "catalog_sha256": catalog_hash, "commercial_signature": False} for plan in _PLAN_CATALOG.values()]


def _record_effective(record: dict[str, Any], now: datetime) -> tuple[bool, str]:
    status = str(record.get("status", "")).lower()
    if status in {"revoked", "expired"}:
        return False, status
    if status not in _ACTIVE_STATUSES:
        return False, "invalid_record"
    expires = _parse_time(record.get("expires_at"))
    if record.get("expires_at") and expires is None:
        return False, "invalid_expiry"
    if expires is not None and expires <= now:
        return False, "expired"
    return True, "active"


def get_subscription(user_id: str | None = None) -> dict[str, Any]:
    uid = _user_id(user_id)
    now = datetime.now(timezone.utc)
    with _LOCK:
        state, load_status = _load()
        raw_record = state.get("users", {}).get(uid)
        record = _normalized_record(raw_record)
        if record is None:
            record = {"plan_id": "free", "status": "active", "source": "local_default", "activated_at": _now(), "expires_at": None, "billing": "not_configured"}
        effective, status = _record_effective(record, now)
        requested_plan_id = record["plan_id"]
        plan_id = requested_plan_id if effective else "free"
        plan = _PLAN_CATALOG[plan_id]
        if load_status in {"corrupt", "invalid", "integrity_error", "unsupported_version"}:
            status = load_status
            effective = False
            plan = _PLAN_CATALOG["free"]
        return {
            "user_id": uid,
            "requested_plan_id": requested_plan_id,
            "plan_id": plan_id,
            "effective_plan_id": plan_id,
            "status": status,
            "active": effective,
            "source": record.get("source", "local_default"),
            "activated_at": record.get("activated_at"),
            "expires_at": record.get("expires_at"),
            "plan": copy.deepcopy(plan),
            "entitlements": copy.deepcopy(plan["entitlements"]) if effective else {},
            "limits": copy.deepcopy(plan["limits"]) if effective else {"workspaces": 1, "alerts": 0, "ai_signals_per_day": 0, "paper_strategies": 0},
            "execution_mode": "paper_demo",
            "live_execution": False,
            "withdrawals_enabled": False,
            "transfers_enabled": False,
            "billing_status": "not_configured",
            "commercial_signature": False,
            "integrity_status": load_status,
            "integrity_verified": load_status in {"verified", "default"},
            "catalog_sha256": _catalog_digest(),
        }


def activate_local_plan(plan_id: str, user_id: str | None = None, expires_at: str | None = None) -> dict[str, Any]:
    uid = _user_id(user_id)
    normalized = str(plan_id or "").strip().lower()
    if normalized not in _PLAN_CATALOG:
        raise ValueError(f"plano inválido: {plan_id}")
    expiry = str(expires_at).strip() if expires_at else None
    if expiry and _parse_time(expiry) is None:
        raise ValueError("expires_at inválido")
    with _LOCK:
        state, load_status = _load()
        if load_status not in {"default", "verified", "migrated_unverified"}:
            state = _empty_state()
        state.setdefault("users", {})[uid] = {
            "plan_id": normalized,
            "status": "local_active",
            "source": "local",
            "activated_at": _now(),
            "expires_at": expiry,
            "billing": "not_configured",
        }
        _save(state)
    return get_subscription(uid)


def has_entitlement(feature: str, user_id: str | None = None) -> bool:
    subscription = get_subscription(user_id)
    return bool(subscription.get("active")) and bool(subscription.get("entitlements", {}).get(str(feature), False))


def require_entitlement(feature: str, user_id: str | None = None) -> None:
    if not has_entitlement(feature, user_id):
        raise PermissionError(f"plano local atual não inclui: {feature}")
