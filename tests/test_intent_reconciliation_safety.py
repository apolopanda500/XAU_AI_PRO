"""Garantias de que resultados incertos não autorizam repetição de ordem."""

import json

from backend import intent_log


def test_resultado_incerto_permanece_pendente_apos_reinicio(tmp_path, monkeypatch):
    path = tmp_path / "intents.jsonl"
    monkeypatch.setattr(intent_log, "INTENT_FILE", path)
    intent_id = intent_log.record_intent("demo_close", {"ticket": 42, "symbol": "XAUUSD"})
    linhas = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    linhas[0]["ts"] = intent_log.time_now() - 90000
    path.write_text("\n".join(json.dumps(item) for item in linhas) + "\n", encoding="utf-8")

    class NoMT5:
        def __getattr__(self, name):
            raise AssertionError("MT5 não pode ser usado para inferir ausência de execução")

    result = intent_log.reconcile(NoMT5())
    assert result["checked"] == 1 and result["still_pending"] == 1
    assert result["reconciled"] == 0
    assert intent_log.reconcile(NoMT5())["unknown"] == 0
    assert [event["intent_id"] for event in intent_log.pending_intents()] == [intent_id]
    assert intent_log.snapshot()["intents"][0]["status"] == "unknown"


def test_resultado_confirmado_nao_sera_reconciliado_novamente(tmp_path, monkeypatch):
    monkeypatch.setattr(intent_log, "INTENT_FILE", tmp_path / "intents.jsonl")
    intent_id = intent_log.record_intent("demo_close", {"ticket": 42})
    intent_log.record_intent("demo_close", {"ticket": 42}, intent_id=intent_id,
                             status="sent", extra={"deal": 9})
    assert intent_log.pending_intents() == []
    assert intent_log.reconcile(None)["checked"] == 0