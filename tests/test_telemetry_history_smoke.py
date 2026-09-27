# -*- coding: utf-8 -*-
"""Smoke extra: historico de telemetria + rate limit por categoria.

Uso: .venv/Scripts/python.exe tests/test_telemetry_history_smoke.py
"""
import sys
import time
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _reload_gw(monkey_env):
    import os
    saved = {k: os.environ.get(k) for k in monkey_env}
    for key, value in monkey_env.items():
        os.environ[key] = value
    fake = ModuleType("MetaTrader5")
    sys.modules["MetaTrader5"] = fake
    import importlib
    import backend.watchdog as watchdog_mod
    import backend.mt5_gateway as gw_mod
    watchdog = importlib.reload(watchdog_mod)  # HISTORY_FILE usa XAU_TELEMETRY_FILE isolado
    module = importlib.reload(gw_mod)
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return module


def test_history_persiste_jsonl(tmp_path):
    gw_file = tmp_path / "hist.jsonl"
    gw = _reload_gw({"XAU_TELEMETRY_FILE": str(gw_file)})
    rows = []
    for _ in range(3):
        snap = gw.watchdog.snapshot_metrics("smoke")
        rows.append(snap)
        time.sleep(0.01)
    hist = gw.watchdog.history(10)
    assert hist["ok"] is True
    assert hist["count"] == 3
    assert hist["snapshots"][0]["ts"] >= hist["snapshots"][-1]["ts"]
    assert hist["last"] is not None
    assert gw_file.exists()


def test_rate_limit_separado_por_categoria(tmp_path):
    # O reload com XAU_RATE_LIMIT=2 deixava o limite valendo para o resto da
    # suíte (o módulo é global) e os testes seguintes began 429. O estado
    # anterior é restaurado ao final.
    import os
    from conftest import TOKEN_DE_TESTE

    env_salvo = {k: os.environ.get(k) for k in ("XAU_RATE_LIMIT", "XAU_RATE_LIMIT_CMD", "XAU_GATEWAY_TOKEN")}
    try:
        gw = _reload_gw({"XAU_RATE_LIMIT": "2", "XAU_RATE_LIMIT_CMD": "1", "XAU_GATEWAY_TOKEN": TOKEN_DE_TESTE})
        # Fail-closed: sem o Bearer correto, `_autorizado` nem chega no
        # rate limit. Enviamos o token de teste para exercitar o rate limit.
        auth = {"Authorization": f"Bearer {TOKEN_DE_TESTE}"}
        handler = gw.Handler.__new__(gw.Handler)
        handler.command = "GET"
        handler.headers = dict(auth)
        ok1, _ = gw.Handler._autorizado(handler)
        ok2, _ = gw.Handler._autorizado(handler)
        ok3, motivo3 = gw.Handler._autorizado(handler)
        assert ok1 and ok2
        assert not ok3 and motivo3 == "rate"
        post = gw.Handler.__new__(gw.Handler)
        post.command = "POST"
        post.headers = dict(auth)
        pok1, _ = gw.Handler._autorizado(post)
        pok2, motivo2 = gw.Handler._autorizado(post)
        assert pok1  # comando tem janela propria: ainda cabe 1
        assert not pok2 and motivo2 == "rate"  # cota de comandos = 1
    finally:
        for key, value in env_salvo.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import importlib

        import backend.mt5_gateway as gw_mod

        importlib.reload(gw_mod)


def test_gateway_recusa_sem_token():
    """Fail-closed: sem XAU_GATEWAY_TOKEN o gateway nega, em vez de aceitar.

    Antes a checagem era `if API_TOKEN:` — variavel vazia significava "sem
    senha". O gateway escuta em 127.0.0.1, mas qualquer processo da maquina
    (ou um mapeamento de porta) leria conta e enviaria ordem.
    """
    import os
    import importlib

    from conftest import TOKEN_DE_TESTE

    os.environ["XAU_GATEWAY_TOKEN"] = TOKEN_DE_TESTE
    import backend.mt5_gateway as gw_mod

    importlib.reload(gw_mod)
    gw_mod.API_TOKEN = ""  # simula o token ausente
    handler = gw_mod.Handler.__new__(gw_mod.Handler)
    handler.command = "GET"
    handler.headers = {}
    ok, motivo = gw_mod.Handler._autorizado(handler)
    assert not ok and motivo == "sem token configurado"
    # E com token configurado, header errado tambem nega.
    gw_mod.API_TOKEN = TOKEN_DE_TESTE
    ok2, motivo2 = gw_mod.Handler._autorizado(handler)
    assert not ok2 and motivo2 == "token"


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_history_persiste_jsonl(Path(tmp))
    import tempfile as _t
    with _t.TemporaryDirectory() as tmp2:
        test_rate_limit_separado_por_categoria(Path(tmp2))
    print("TELEMETRY_HISTORY_SMOKE_OK")
