from __future__ import annotations

import asyncio
import json

import pytest

from app import subscriptions


def test_planos_exigem_modos_paper(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(tmp_path / "subscriptions.json"))
    plans = subscriptions.list_plans()
    assert {plan["id"] for plan in plans} == {"free", "pro", "business"}
    assert all(plan["billing_mode"] == "local_only" for plan in plans)
    assert all(plan["commercial_signature"] is False for plan in plans)
    assert len({plan["catalog_sha256"] for plan in plans}) == 1


def test_ativa_plano_localmente(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(tmp_path / "subscriptions.json"))
    result = subscriptions.activate_local_plan("pro", "user-1")
    assert result["plan_id"] == "pro"
    assert result["entitlements"]["advanced_analytics"] is True
    assert result["live_execution"] is False
    assert json.loads((tmp_path / "subscriptions.json").read_text(encoding="utf-8"))["users"]["user-1"]["plan_id"] == "pro"


def test_plano_invalido_nao_altera_arquivo(tmp_path, monkeypatch):
    path = tmp_path / "subscriptions.json"
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(path))
    with pytest.raises(ValueError):
        subscriptions.activate_local_plan("enterprise")
    assert not path.exists()


def test_endpoints_de_planos_e_social_sao_locais(tmp_path, monkeypatch):
    from backend import fastapi_gateway

    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(tmp_path / "subscriptions.json"))
    monkeypatch.setenv("XAU_SOCIAL_PAPER_FILE", str(tmp_path / "social.json"))
    plans = asyncio.run(fastapi_gateway.subscription_plans())
    assert plans["live_execution"] is False
    activated = asyncio.run(fastapi_gateway.subscription_activate({"plan_id": "pro"}))
    assert activated.status_code == 200
    follow = asyncio.run(fastapi_gateway.social_follow({"strategy_id": "trend-filter-paper"}))
    assert follow.status_code == 200
    assert json.loads(follow.body)["strategy"]["live_execution"] is False


def test_integridade_adulterada_retorna_free(tmp_path, monkeypatch):
    path = tmp_path / "subscriptions.json"
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(path))
    subscriptions.activate_local_plan("pro", "user-1")
    persisted = json.loads(path.read_text(encoding="utf-8"))
    persisted["users"]["user-1"]["plan_id"] = "business"
    path.write_text(json.dumps(persisted), encoding="utf-8")
    result = subscriptions.get_subscription("user-1")
    assert result["plan_id"] == "free"
    assert result["entitlements"] == {}
    assert result["integrity_status"] == "integrity_error"
    assert result["commercial_signature"] is False


def test_plano_expirado_nao_concede_entitlements(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(tmp_path / "subscriptions.json"))
    result = subscriptions.activate_local_plan("pro", "user-1", expires_at="2020-01-01T00:00:00Z")
    assert result["requested_plan_id"] == "pro"
    assert result["effective_plan_id"] == "free"
    assert result["status"] == "expired"
    assert subscriptions.has_entitlement("social_paper", "user-1") is False


def test_arquivo_corrompido_falha_fechado(tmp_path, monkeypatch):
    path = tmp_path / "subscriptions.json"
    path.write_text("{invalid", encoding="utf-8")
    monkeypatch.setenv("XAU_SUBSCRIPTION_FILE", str(path))
    result = subscriptions.get_subscription("user-1")
    assert result["plan_id"] == "free"
    assert result["active"] is False
    assert result["integrity_status"] == "corrupt"
