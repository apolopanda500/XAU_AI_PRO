from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READ_ONLY_CAPABILITIES = frozenset({"assets", "quotes", "candles", "account", "positions", "orders", "history", "journal"})
FORBIDDEN_CAPABILITIES = frozenset({"order", "orders_write", "close", "modify", "cancel", "execution", "commands", "control", "protection", "withdrawals", "transfers"})
ADAPTER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
MANIFEST_FILE = Path(os.getenv("XAU_THIRD_PARTY_EA_MANIFEST", str(Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "third_party_ea_adapters.json")))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _number(value: Any, *, integer: bool = False) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed):
        return None
    return int(parsed) if integer else parsed


def load_manifest(path: Path = MANIFEST_FILE) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "adapters": []}
    if path.stat().st_size > 1_048_576:
        raise ValueError("manifesto de adaptadores excede 1 MiB")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or int(raw.get("schema_version", 0)) != 1 or not isinstance(raw.get("adapters"), list):
        raise ValueError("manifesto de adaptadores inválido")
    return {"schema_version": 1, "adapters": raw["adapters"]}


def _attribute(item: object, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def read_mt5_snapshot(mt5: Any) -> dict[str, Any]:
    account = mt5.account_info()
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if account is None:
        raise RuntimeError("conta MT5 indisponível")
    if positions is None:
        raise RuntimeError("posições MT5 indisponíveis")
    if orders is None:
        raise RuntimeError("ordens MT5 indisponíveis")
    now = datetime.now()
    deals = mt5.history_deals_get(now.replace(hour=0, minute=0, second=0, microsecond=0), now)
    if deals is None:
        raise RuntimeError("histórico MT5 indisponível")
    return {
        "account": {
            "login": str(_attribute(account, "login", "")),
            "server": str(_attribute(account, "server", "")),
            "currency": str(_attribute(account, "currency", "")),
            "trade_mode": _number(_attribute(account, "trade_mode"), integer=True),
        },
        "positions": list(positions),
        "orders": list(orders),
        "deals": list(deals),
    }


def _normalize_adapter(raw: Any) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not isinstance(raw, dict):
        return {}, ["adapter deve ser objeto"]
    adapter_id = str(raw.get("adapter_id", "")).strip().lower()
    vendor = str(raw.get("vendor", "")).strip()
    name = str(raw.get("name", "")).strip()
    version = str(raw.get("version", "")).strip()
    build = str(raw.get("build", "")).strip()
    login = str(raw.get("login", "")).strip()
    server = str(raw.get("server", "")).strip()
    issued_at = parse_datetime(raw.get("issued_at"))
    sequence = _number(raw.get("sequence"), integer=True)
    ttl_seconds = _number(raw.get("ttl_seconds", 120), integer=True)
    read_only = raw.get("read_only") is True
    commands_enabled = raw.get("commands_enabled") is True
    capabilities_raw = raw.get("capabilities")
    capabilities = tuple(sorted({str(item).strip().lower() for item in capabilities_raw if str(item).strip()})) if isinstance(capabilities_raw, list) else ()
    magics_raw = raw.get("magics")
    magic_values = set()
    if isinstance(magics_raw, list):
        for value in magics_raw:
            parsed = _number(value, integer=True)
            if parsed is not None:
                magic_values.add(int(parsed))
    magics = tuple(sorted(magic_values))
    symbols_raw = raw.get("symbols")
    symbols = tuple(sorted({str(value).strip().upper() for value in symbols_raw if str(value).strip()})) if isinstance(symbols_raw, list) else ()
    if not ADAPTER_ID_PATTERN.fullmatch(adapter_id):
        errors.append("adapter_id inválido")
    if not vendor or len(vendor) > 100:
        errors.append("vendor é obrigatório")
    if not name or len(name) > 100:
        errors.append("name é obrigatório")
    if not version or len(version) > 50:
        errors.append("version é obrigatória")
    if len(build) > 100:
        errors.append("build inválido")
    if not login or len(login) > 40:
        errors.append("login é obrigatório")
    if not server or len(server) > 120:
        errors.append("server é obrigatório")
    if issued_at is None:
        errors.append("issued_at inválido")
    if sequence is None or sequence < 0:
        errors.append("sequence inválido")
    if ttl_seconds is None or not 30 <= ttl_seconds <= 86_400:
        errors.append("ttl_seconds deve estar entre 30 e 86400")
    if not read_only:
        errors.append("read_only=true é obrigatório")
    if commands_enabled:
        errors.append("commands_enabled=true é proibido")
    if not capabilities:
        errors.append("capabilities são obrigatórias")
    unsupported = sorted(set(capabilities) - READ_ONLY_CAPABILITIES)
    forbidden = sorted(set(capabilities) & FORBIDDEN_CAPABILITIES)
    if unsupported:
        errors.append(f"capabilities não somente leitura: {', '.join(unsupported)}")
    if forbidden:
        errors.append(f"capabilities de controle proibidas: {', '.join(forbidden)}")
    if not magics or any(value <= 0 or value > 4_294_967_295 for value in magics):
        errors.append("magics deve conter inteiros positivos de 32 bits")
    if not symbols or any(not value or len(value) > 40 for value in symbols):
        errors.append("symbols deve conter até 40 caracteres por ativo")
    return {
        "adapter_id": adapter_id,
        "vendor": vendor,
        "name": name,
        "version": version,
        "build": build,
        "login": login,
        "server": server,
        "issued_at": issued_at,
        "sequence": sequence,
        "ttl_seconds": ttl_seconds,
        "read_only": read_only,
        "commands_enabled": False,
        "capabilities": capabilities,
        "magics": magics,
        "symbols": symbols,
        "terminal_id_hash": str(raw.get("terminal_id_hash", "")).strip() or None,
    }, errors


def evaluate_adapter(raw: Any, snapshot: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    observed_at = now or utc_now()
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    adapter, errors = _normalize_adapter(raw)
    account = snapshot.get("account", {}) if isinstance(snapshot.get("account"), dict) else {}
    account_match = bool(adapter) and str(account.get("login", "")) == adapter["login"] and str(account.get("server", "")).casefold() == adapter["server"].casefold()
    age_seconds: int | None = None
    if adapter.get("issued_at") is not None:
        raw_age = int((observed_at - adapter["issued_at"]).total_seconds())
        age_seconds = max(0, raw_age)
        if raw_age < -30:
            errors.append("issued_at está no futuro")
    magic_set = set(adapter.get("magics", ()))
    symbol_set = set(adapter.get("symbols", ()))
    candidates = []
    conflicts = []
    unknown = []
    for position in snapshot.get("positions", []) if isinstance(snapshot.get("positions"), list) else []:
        magic = _number(_attribute(position, "magic"), integer=True)
        symbol = str(_attribute(position, "symbol", "")).upper()
        if magic in magic_set and symbol in symbol_set:
            candidates.append({"ticket": str(_attribute(position, "ticket", "")), "symbol": symbol, "magic": magic})
        elif magic in magic_set:
            conflicts.append({"ticket": str(_attribute(position, "ticket", "")), "symbol": symbol, "magic": magic, "reason": "símbolo fora do escopo declarado"})
        else:
            unknown.append({"ticket": str(_attribute(position, "ticket", "")), "symbol": symbol or None, "magic": magic})
    if errors:
        state = "invalid"
    elif age_seconds is not None and adapter.get("ttl_seconds") is not None and age_seconds > adapter["ttl_seconds"]:
        state = "stale"
    elif account_match:
        state = "matched_read_only"
    else:
        state = "unverified"
    return {
        "adapter_id": adapter.get("adapter_id"),
        "vendor": adapter.get("vendor"),
        "name": adapter.get("name"),
        "version": adapter.get("version"),
        "build": adapter.get("build"),
        "state": state,
        "errors": errors,
        "account_match": account_match,
        "account_login": account.get("login"),
        "account_server": account.get("server"),
        "account_currency": account.get("currency"),
        "account_mode": "DEMO" if account.get("trade_mode") == 0 else "REAL_OR_UNKNOWN" if account.get("trade_mode") is not None else None,
        "age_seconds": age_seconds,
        "ttl_seconds": adapter.get("ttl_seconds"),
        "sequence": adapter.get("sequence"),
        "capabilities": list(adapter.get("capabilities", ())),
        "commands_enabled": False,
        "control_supported": False,
        "write_operations": [],
        "withdrawals_enabled": False,
        "transfers_enabled": False,
        "attribution": {
            "method": "magic_candidate",
            "cryptographically_verified": False,
            "owned_proven": False,
            "candidate_positions": candidates,
            "conflicts": conflicts,
            "unassigned_position_count": len(unknown),
        },
        "observed_at": iso_datetime(observed_at),
    }


def evaluate_all(mt5: Any, path: Path = MANIFEST_FILE, now: datetime | None = None) -> dict[str, Any]:
    observed_at = now or utc_now()
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    try:
        manifest = load_manifest(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "invalid", "error": str(exc), "read_only": True, "commands_enabled": False, "adapters": [], "matched": 0, "observed_at": iso_datetime(observed_at), "source": "local_manifest+mt5_read_only"}
    try:
        snapshot = read_mt5_snapshot(mt5)
    except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
        return {"ok": False, "status": "temporarily_unavailable", "error": str(exc), "read_only": True, "commands_enabled": False, "adapters": [], "matched": 0, "observed_at": iso_datetime(observed_at), "source": "local_manifest+mt5_read_only"}
    adapters = [evaluate_adapter(item, snapshot, observed_at) for item in manifest["adapters"]]
    return {
        "ok": True,
        "status": "ok",
        "schema_version": 1,
        "read_only": True,
        "commands_enabled": False,
        "control_supported": False,
        "production_ready": False,
        "cryptographic_identity": False,
        "adapters": adapters,
        "matched": sum(1 for item in adapters if item["state"] == "matched_read_only"),
        "observed_at": iso_datetime(observed_at),
        "source": "local_manifest+mt5_read_only",
    }
