from unittest.mock import patch


def test_full_sync_reports_offline_account_as_failure() -> None:
    from app.mt5_sync import run_full_sync

    with patch("app.mt5_sync.sync_account", return_value={"ok": False, "error": "offline"}), patch(
        "app.mt5_sync.sync_positions", return_value={"ok": True}
    ), patch("app.mt5_sync.sync_history", return_value={"ok": True}), patch(
        "app.mt5_sync.sync_journal", return_value={"ok": True}
    ):
        result = run_full_sync()

    assert result["ok"] is False


def test_full_sync_requires_every_stage() -> None:
    from app.mt5_sync import run_full_sync

    with patch("app.mt5_sync.sync_account", return_value={"ok": True}), patch(
        "app.mt5_sync.sync_positions", return_value={"ok": True}
    ), patch("app.mt5_sync.sync_history", return_value={"ok": True}), patch(
        "app.mt5_sync.sync_journal", return_value={"ok": True}
    ):
        result = run_full_sync()

    assert result["ok"] is True
