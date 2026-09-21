# -*- coding: utf-8 -*-
"""Smoke test do Guardian Engine (Fase 1) - roda sem MT5 instalado.

Uso: .venv/Scripts/python.exe tests/test_guardian_smoke.py
"""
import os
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("XAU_GUARDIAN_FILE", str(Path(tempfile.gettempdir()) / "guardian_test_rules.json"))
os.environ.setdefault("XAU_INTENT_FILE", str(Path(tempfile.gettempdir()) / "guardian_test_intents.jsonl"))

from backend import guardian_engine as g  # noqa: E402


def test_normalize_rule_ok():
    rule = g._normalize_rule({
        "ticket": 123,
        "breakeven": {"trigger": 5, "offset": 0.1},
        "trailing": {"mode": "step", "distance": 3, "step": 0.5},
        "partials": [{"trigger": 4, "volume": 0.01}, {"trigger_profit": 30, "volume": 0.02}],
        "profit_lock": {"trigger": 8, "giveback": 2},
        "time_exit": {"max_minutes": 90},
    })
    assert rule["ticket"] == 123
    assert rule["trailing"]["mode"] == "step"
    assert len(rule["partials"]) == 2
    assert rule["time_exit"]["max_minutes"] == 90


def test_normalize_rule_rejects_invalid():
    casos = [
        {"ticket": 0},                                   # sem ticket
        {"ticket": 1},                                   # sem modulo algum
        {"ticket": 1, "trailing": {"mode": "fixed", "distance": 0}},  # fixed sem distance
        {"ticket": 1, "trailing": {"mode": "weird", "distance": 5}},  # modo inexistente
        {"ticket": 1, "partials": [{"trigger": 0, "volume": 0.01}]},  # parcial sem gatilho
    ]
    for bad in casos:
        try:
            g._normalize_rule(bad)
            raise AssertionError(f"deveria recusar: {bad}")
        except ValueError:
            pass


def test_status_blocked_without_demo_env():
    os.environ.pop("XAU_ENABLE_DEMO_ORDERS", None)
    status = g.guardian_status()
    assert status["guardian"] == "blocked_demo_orders"
    assert status["demo_only"] is True


def test_set_requires_demo_env():
    os.environ.pop("XAU_ENABLE_DEMO_ORDERS", None)
    try:
        g.guardian_set({"ticket": 1})
        raise AssertionError("deveria recusar sem XAU_ENABLE_DEMO_ORDERS=1")
    except PermissionError:
        pass


def test_tick_vazio_ok():
    resultado = g.guardian_tick()
    assert resultado["ok"] is True
    assert resultado["count"] == 0


def test_persistencia_roundtrip():
    g.RULES.clear()
    g.STATE.clear()
    g.RULES[999] = {"ticket": 999, "breakeven": {"trigger": 5, "offset": 0.0, "trigger_profit": 0.0}}
    g.STATE[999] = {"executed_partials": []}
    g._save_rules()
    g.RULES.clear()
    g.STATE.clear()
    g._load_rules()
    assert 999 in g.RULES and 999 in g.STATE
    g.RULES.clear()
    g.STATE.clear()


def test_intent_log_basico():
    from backend import intent_log
    intent_log.INTENT_FILE = Path(os.environ["XAU_INTENT_FILE"])
    intent_id = intent_log.record_intent("demo_order", {"symbol": "XAUUSD"}, status="pending")
    pend = intent_log.pending_intents()
    assert any(e["intent_id"] == intent_id for e in pend)
    snap = intent_log.snapshot(10)
    assert snap["count"] >= 1


def test_reconcile_classifica_unknown():
    from backend import intent_log
    intent_log.INTENT_FILE = Path(os.environ["XAU_INTENT_FILE"])
    velho = intent_log.time_now() - 1000.0
    intent_id = intent_log.record_intent("demo_order", {"symbol": "XAUUSD"}, status="pending")
    # reescreve o arquivo forçando timestamp antigo no evento pending
    linhas = intent_log.INTENT_FILE.read_text(encoding="utf-8").splitlines()
    novas = []
    for linha in linhas:
        try:
            evento = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if evento.get("intent_id") == intent_id and evento.get("status") == "pending":
            evento["ts"] = velho
        novas.append(json.dumps(evento, ensure_ascii=False))
    intent_log.INTENT_FILE.write_text("\n".join(novas) + "\n", encoding="utf-8")

    class StubMt5:
        def positions_get(self, *a, **k):
            return []
        def history_deals_get(self, *a, **k):
            return []
    relatorio = intent_log.reconcile(StubMt5())
    assert relatorio["checked"] >= 1 and relatorio["unknown"] >= 1
    snap = intent_log.snapshot(50)
    alvo = next((i for i in snap["intents"] if i["intent_id"] == intent_id), None)
    assert alvo is not None and alvo["status"] == "unknown"


if __name__ == "__main__":
    test_normalize_rule_ok()
    test_normalize_rule_rejects_invalid()
    test_status_blocked_without_demo_env()
    test_set_requires_demo_env()
    test_tick_vazio_ok()
    test_persistencia_roundtrip()
    test_intent_log_basico()
    test_reconcile_classifica_unknown()
    print("GUARDIAN_SMOKE_OK")
