# -*- coding: utf-8 -*-
"""Smoke test da fila persistente (Fase 4) - roda sem terminal MT5.

Uso: .venv/Scripts/python.exe tests/test_queue_smoke.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Arquivo unico por processo: evita itens "pending" deixados por execucoes anteriores.
os.environ["XAU_QUEUE_FILE"] = str(Path(tempfile.gettempdir()) / f"queue_test_{os.getpid()}.json")
os.environ["XAU_ENABLE_DEMO_ORDERS"] = "1"
Path(os.environ["XAU_QUEUE_FILE"]).unlink(missing_ok=True)

from backend import persistent_queue as q  # noqa: E402
from backend import mt5_gateway as gw  # noqa: E402

emergencia = gw.REAL_EMERGENCY_STOP.exists()
if emergencia:
    print("AVISO: parada de emergencia ativa; testes de processamento serao pulados")


def test_fatal_classificacao():
    assert q._is_fatal("posicao DEMO nao encontrada")
    assert q._is_fatal("somente conta DEMO aceita")
    assert q._is_fatal("ordens DEMO desabilitadas")
    assert q._is_fatal("confirm_demo=true obrigatorio")
    assert q._is_fatal("volume parcial deve ser maior que zero")
    assert not q._is_fatal("connection timeout")
    assert not q._is_fatal("contexto ocupado, tente novamente")


def test_sem_runner_falha():
    if emergencia:
        return
    queue_id = q.enqueue("tipo_inexistente", {})
    report = q.process_one()
    assert report.get("queue_id") == queue_id and report.get("ok") is False


def test_ordem_nunca_executa_sozinha():
    if emergencia:
        return
    queue_id = q.enqueue("order", {"symbol": "XAUUSD", "side": "BUY"})
    report = q.process_one()
    assert report.get("skipped") is True and report.get("queue_id") == queue_id


def test_retry_e_sucesso():
    if emergencia:
        return
    tentativas = {"n": 0}

    def runner_instavel(payload, **kwargs):
        tentativas["n"] += 1
        if tentativas["n"] < 2:
            raise ConnectionError("terminal temporariamente ocupado")
        return {"ok": True, "retcode": 10009}

    q.register_runner("close", runner_instavel)
    queue_id = q.enqueue("close", {"ticket": 1})
    report = q.process_one()  # 1a: retry
    assert report.get("retry") is True and report.get("queue_id") == queue_id
    report = q.process_one()  # 2a: sucesso
    assert report.get("ok") is True and report.get("retcode") == 10009


def test_fatal_nao_reenvia():
    if emergencia:
        return

    def runner_fatal(payload, **kwargs):
        raise LookupError("posicao DEMO nao encontrada")

    q.register_runner("close", runner_fatal)
    queue_id = q.enqueue("close", {"ticket": 42})
    report = q.process_one()
    assert report.get("ok") is False and "retry" not in report


def test_status_e_fallback_offline():
    status = q.queue_status()
    assert status["ok"] is True and status["count"] >= 1
    resultado = q.offline_fallback_kind("close", {"ticket": 7}, LookupError("x"))
    # Com/sem pacote MT5, offline_fallback enfileira quando terminal esta offline
    if resultado is not None:
        assert resultado.get("queued") is True and resultado.get("queue_id")


def test_fallback_recusa_ordem_nova():
    assert q.offline_fallback_kind("order", {"symbol": "XAUUSD"}, ConnectionError("x")) is None
    assert q.offline_fallback_kind("", {}, ConnectionError("x")) is None


if __name__ == "__main__":
    test_fatal_classificacao()
    test_sem_runner_falha()
    test_ordem_nunca_executa_sozinha()
    test_retry_e_sucesso()
    test_fatal_nao_reenvia()
    test_status_e_fallback_offline()
    test_fallback_recusa_ordem_nova()
    print("QUEUE_SMOKE_OK")
