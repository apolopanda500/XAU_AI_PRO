from __future__ import annotations

import pytest

from app import social_paper, subscriptions


def test_social_requires_entitlement(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(tmp_path / "subscriptions.json"))
    monkeypatch.setenv("XAU_SOCIAL_PAPER_FILE", str(tmp_path / "social.json"))
    with pytest.raises(PermissionError):
        social_paper.follow_strategy("trend-filter-paper", "local")


def test_social_paper_is_persisted_without_live_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(tmp_path / "subscriptions.json"))
    monkeypatch.setenv("XAU_SOCIAL_PAPER_FILE", str(tmp_path / "social.json"))
    subscriptions.activate_local_plan("pro", "local")
    result = social_paper.follow_strategy("trend-filter-paper", "local")
    assert result["following"] is True
    assert result["live_execution"] is False
    assert social_paper.following_strategies("local")[0]["id"] == "trend-filter-paper"
