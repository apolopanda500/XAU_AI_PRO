from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from backend.third_party_ea import evaluate_adapter, evaluate_all, read_mt5_snapshot

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)


class ReadOnlyMT5:
    def __init__(self, login: int = 12345, positions: list[object] | None = None) -> None:
        self.login = login
        self.positions = positions if positions is not None else [SimpleNamespace(ticket=10, symbol="XAUUSD", magic=7001)]
        self.reads: list[str] = []

    def account_info(self):
        self.reads.append("account_info")
        return SimpleNamespace(login=self.login, server="Demo-Server", currency="USD", trade_mode=0)

    def positions_get(self):
        self.reads.append("positions_get")
        return self.positions

    def orders_get(self):
        self.reads.append("orders_get")
        return []

    def history_deals_get(self, start, end):
        self.reads.append("history_deals_get")
        return []

    def symbol_select(self, *args):
        raise AssertionError("somente leitura não pode selecionar símbolo")

    def order_send(self, *args):
        raise AssertionError("somente leitura não pode enviar ordem")

    def order_delete(self, *args):
        raise AssertionError("somente leitura não pode cancelar ordem")


def manifest(adapter: dict | None = None) -> dict:
    return {
        "adapter_id": "acme-gold-v3",
        "vendor": "ACME",
        "name": "Gold Observer",
        "version": "3.2.1",
        "build": "2026.09",
        "login": 12345,
        "server": "Demo-Server",
        "terminal_id_hash": None,
        "issued_at": "2026-09-24T11:59:30Z",
        "sequence": 42,
        "ttl_seconds": 120,
        "read_only": True,
        "commands_enabled": False,
        "capabilities": ["account", "positions", "orders", "history"],
        "magics": [7001],
        "symbols": ["XAUUSD"],
        **(adapter or {}),
    }


def snapshot(mt5: ReadOnlyMT5) -> dict:
    return read_mt5_snapshot(mt5)


def test_matching_adapter_is_observational_only() -> None:
    mt5 = ReadOnlyMT5(positions=[
        SimpleNamespace(ticket=10, symbol="XAUUSD", magic=7001),
        SimpleNamespace(ticket=11, symbol="EURUSD", magic=7001),
        SimpleNamespace(ticket=12, symbol="GBPUSD", magic=0),
    ])
    result = evaluate_adapter(manifest(), snapshot(mt5), NOW)
    assert result["state"] == "matched_read_only"
    assert result["commands_enabled"] is False
    assert result["control_supported"] is False
    assert result["write_operations"] == []
    assert result["attribution"]["owned_proven"] is False
    assert result["attribution"]["candidate_positions"] == [{"ticket": "10", "symbol": "XAUUSD", "magic": 7001}]
    assert result["attribution"]["conflicts"][0]["symbol"] == "EURUSD"
    assert result["attribution"]["unassigned_position_count"] == 1
    assert set(mt5.reads) == {"account_info", "positions_get", "orders_get", "history_deals_get"}


def test_account_mismatch_remains_unverified() -> None:
    result = evaluate_adapter(manifest(), snapshot(ReadOnlyMT5(login=999)), NOW)
    assert result["state"] == "unverified"
    assert result["account_match"] is False


def test_expired_manifest_is_stale() -> None:
    result = evaluate_adapter(manifest({"issued_at": "2026-09-24T11:50:00Z"}), snapshot(ReadOnlyMT5()), NOW)
    assert result["state"] == "stale"
    assert result["age_seconds"] == 600


def test_control_capability_is_rejected() -> None:
    result = evaluate_adapter(manifest({"capabilities": ["positions", "close"]}), snapshot(ReadOnlyMT5()), NOW)
    assert result["state"] == "invalid"
    assert any("somente leitura" in error for error in result["errors"])
    assert result["commands_enabled"] is False


def test_magic_does_not_prove_ownership() -> None:
    result = evaluate_adapter(manifest(), snapshot(ReadOnlyMT5()), NOW)
    assert result["attribution"]["method"] == "magic_candidate"
    assert result["attribution"]["cryptographically_verified"] is False


def test_manifest_evaluation_fails_closed_when_position_read_fails(tmp_path: Path) -> None:
    path = tmp_path / "adapters.json"
    path.write_text(json.dumps({"schema_version": 1, "adapters": [manifest()]}), encoding="utf-8")
    mt5 = ReadOnlyMT5()
    mt5.positions_get = lambda: None
    result = evaluate_all(mt5, path, NOW)
    assert result["ok"] is False
    assert result["status"] == "temporarily_unavailable"
    assert result["commands_enabled"] is False
    assert result["adapters"] == []


def test_evaluate_all_returns_only_manifest_metadata(tmp_path: Path) -> None:
    path = tmp_path / "adapters.json"
    path.write_text(json.dumps({"schema_version": 1, "adapters": [manifest()]}), encoding="utf-8")
    result = evaluate_all(ReadOnlyMT5(), path, NOW)
    assert result["ok"] is True
    assert result["matched"] == 1
    assert result["production_ready"] is False
    assert result["cryptographic_identity"] is False
    assert result["adapters"][0]["state"] == "matched_read_only"
    assert "api_key" not in json.dumps(result).lower()
