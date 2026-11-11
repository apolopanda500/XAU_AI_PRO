# -*- coding: utf-8 -*-
"""Smoke test do Watchdog/Telemetria (Fase 3) - roda sem MT5 instalado.

Uso: .venv/Scripts/python.exe tests/test_watchdog_smoke.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import watchdog as w  # noqa: E402


def test_classificacao_heartbeat():
    agora = w._now()
    assert w._classify_heartbeat({"invalid": True}, 0, 0) == "unknown"
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": 0}, 0, 0) == "unknown"
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": agora}, 0, 0) == "alive"
    # arquivo fresh + timestamp estagnado -> frozen
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": agora - 3600}, 3600, 5) == "frozen"
    # arquivo antigo -> stale
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": agora - 3600}, 3600, 3600) == "stale"


def test_telemetria_ring():
    w._RING.clear()
    w.record("teste", {"x": 1})
    w.record("teste", {"x": 2}, severity="warning")
    snapshot = w.telemetry(10)
    assert snapshot["ok"] is True
    assert snapshot["count"] == 2
    assert snapshot["by_kind"].get("teste") == 2
    assert snapshot["by_severity"].get("warning") == 1
    assert snapshot["events"][0]["kind"] == "teste"  # mais recente primeiro


def test_recovery_somente_leitura():
    resultado = w.recovery()
    assert resultado["ok"] is True
    assert resultado["state"] in {"alive", "frozen", "stale", "missing", "unknown"}
    assert resultado["actions"] == []


def test_timestamp_futuro_nao_e_vida():
    """PROVA NEGATIVA do defeito medido no aparelho em 11/11/2026.

    MEDIDO: o EA gravava `TimeCurrent()` (hora do SERVIDOR, UTC+2) e este
    modulo lia o campo como UTC. `age = agora - (agora + 2h)` ficava
    NEGATIVO, o `max(0.0, ...)` de `ea_state` truncava em 0, e o resultado
    era `state=alive, heartbeat_age_sec=0` enquanto o EA nao escrevia o
    arquivo ha 27 minutos (write_count=1, mtime 1638 s atras).

    Este teste reprovaria o codigo antigo nos DOIS pontos:
      - classificador: `ts_epoch = agora + 2h` dava `alive`, agora da `unknown`;
      - `ea_state`   : `heartbeat_age_sec` era 0.0, agora e negativo.
    O caso `+5 s` cobre a tolerancia normal de escrita/leitura e continua
    `alive` - sem ela, o proprio teste reprovaria o codigo certo.
    """
    import json
    from datetime import datetime, timedelta, timezone

    # --- 1) classificador: futuro longe e "unknown", futuro perto e vivo ---
    agora = w._now()
    assert w._classify_heartbeat(
        {"invalid": False, "ts_epoch": agora + 7200}, 0, 0) == "unknown"
    assert w._classify_heartbeat(
        {"invalid": False, "ts_epoch": agora + 5}, 5, 5) == "alive"

    # --- 2) caminho inteiro do ea_state, com arquivo de verdade ---
    original = w.HEARTBEAT_FILE
    arquivo = Path(__file__).resolve().parent / "_heartbeat_futuro_teste.json"
    try:
        futuro = datetime.now(timezone.utc) + timedelta(hours=2)
        arquivo.write_text(json.dumps({
            "schema": "ea-heartbeat.v1",
            "state": "RUNNING",
            "timestamp": futuro.strftime("%Y.%m.%d %H:%M:%S"),
            "login": 1, "server": "TESTE",
        }), encoding="utf-8")
        w.HEARTBEAT_FILE = arquivo
        r = w.ea_state()
        assert r["state"] == "unknown", r
        # Negativo de verdade: nem 0 (era o `max(0.0, ...)`) nem None
        # (None continua reservado a "sem timestamp valido").
        assert r["heartbeat_age_sec"] is not None, r
        assert r["heartbeat_age_sec"] < -7000, r
    finally:
        w.HEARTBEAT_FILE = original
        arquivo.unlink(missing_ok=True)


if __name__ == "__main__":
    test_classificacao_heartbeat()
    test_telemetria_ring()
    test_recovery_somente_leitura()
    test_timestamp_futuro_nao_e_vida()
    print("WATCHDOG_SMOKE_OK")
