# -*- coding: utf-8 -*-
"""Testes dos alertas de preco e helpers da aba Ferramentas."""
import os

from app.tabs.tools import _load_alerts_disk, _save_alerts_disk, _should_fire


def test_should_fire_acima():
    assert _should_fire(100.0, 90.0, "acima") is True
    assert _should_fire(89.0, 90.0, "acima") is False
    assert _should_fire(90.0, 90.0, "acima") is True  # igual conta


def test_should_fire_abaixo():
    assert _should_fire(80.0, 90.0, "abaixo") is True
    assert _should_fire(100.0, 90.0, "abaixo") is False


def test_should_fire_condicao_invalida():
    assert _should_fire(100.0, 90.0, "entre") is False


def test_alerts_disk_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_AI_PRO_DATA", str(tmp_path))
    alerts = [{"symbol": "XAUUSD", "price": 4350.5, "cond": "acima",
               "active": True, "fired": False},
              {"symbol": "EURUSD", "price": 1.10, "cond": "abaixo",
               "active": False, "fired": True}]
    _save_alerts_disk(alerts)
    loaded = _load_alerts_disk()
    assert len(loaded) == 2
    assert loaded[0]["symbol"] == "XAUUSD"
    assert loaded[0]["price"] == 4350.5
    assert loaded[1]["active"] is False


def test_alerts_disk_arquivo_inexistente(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_AI_PRO_DATA", str(tmp_path / "nao_existe"))
    assert _load_alerts_disk() == []


def test_alerts_disk_rejeita_json_invalido(tmp_path, monkeypatch):
    monkeypatch.setenv("XAU_AI_PRO_DATA", str(tmp_path))
    p = tmp_path / "alerts.json"
    p.write_text("{isto nao e json", encoding="utf-8")
    assert _load_alerts_disk() == []
    os.environ.pop("XAU_AI_PRO_DATA", None)