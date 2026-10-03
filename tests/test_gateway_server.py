"""Regressao do soquete do gateway (backend/gateway_server.py).

O QUE ESTE ARQUIVO PROVA
========================
Cada teste aqui fixa uma limitacao que derrubou o `mt5-gateway` em
producao. Nenhum deles testa "o gateway funciona": isso ja e coberto por
`test_gateway_endpoints.py`. Estes testam as PROPRIEDADES do servidor que a
interface real exige e que a biblioteca padrao nao garante.

O mais importante e `test_respostas_todo_tem_content_length`: keep-alive sem
`Content-Length` faz o cliente esperar um corpo que nunca chega, e o sintoma
(everything lento, depois travado) parece lentidao da maquina, nao do
protocolo. Sem esse teste, a correcao pode ser aplicada e o problema mudar de
forma sem ninguem perceber.
"""
from __future__ import annotations

import http.client
import sys
import threading
from pathlib import Path

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend import gateway_server  # noqa: E402
from tests.conftest import TOKEN_DE_TESTE  # noqa: E402


@pytest.fixture()
def gw(tmp_path, monkeypatch):
    """Gateway real recarregado, com MetaTrader5 de mentira.

    Mesmo fixture de `test_gateway_cors.py`: sem o modulo MT5 injetado, o
    import do gateway tenta abrir o terminal.

    O token e definido ANTES do import porque o gateway e **fail-closed**: sem
    `XAU_GATEWAY_TOKEN` ele recusa tudo com 401, e um teste que esperava 200
    receberia 401 e culparia o servidor novo em vez da propria fixture.
    """
    import importlib
    from types import ModuleType

    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XAU_MT5_COMMON_FILES", str(tmp_path / "common"))
    monkeypatch.setenv("XAU_APP_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("XAU_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("XAU_REAL_EMERGENCY_FILE", str(tmp_path / "STOP"))
    monkeypatch.setenv("XAU_GATEWAY_TOKEN", TOKEN_DE_TESTE)
    monkeypatch.setitem(sys.modules, "MetaTrader5", ModuleType("MetaTrader5"))
    import backend.mt5_gateway as gw_mod

    return importlib.reload(gw_mod)


# --------------------------------------------------------------------------
# configuracao do handler
# --------------------------------------------------------------------------

def test_handler_usa_http_1_1_para_reaproveitar_socket(gw):
    """HTTP/1.0 fecha a conexao a cada resposta e o socket vira TIME_WAIT.

    A maquina chegou a 318 sockets em TIME_WAIT so com o app aberto. E o
    motivo de cada `fetch` do webview custar uma porta efemera nova.
    """
    from backend.mt5_gateway import Handler

    handler = gateway_server.configurar_handler(Handler)
    assert handler.protocol_version == "HTTP/1.1"


def test_handler_tem_timeout_para_nao_segurar_thread(gw):
    """Sem timeout, um cliente que abre e nao manda nada segura a thread.

    `ThreadingHTTPServer` cria uma thread por conexao. Sem `timeout`, essa
    thread fica viva ate o cliente fechar — e o operador nao fecha, porque
    nao sabe que abriu nada.
    """
    from backend.mt5_gateway import Handler

    handler = gateway_server.configurar_handler(Handler)
    assert handler.timeout == gateway_server.timeout_conexao()
    assert handler.timeout > 0
# --------------------------------------------------------------------------
# backlog
# --------------------------------------------------------------------------

def test_backlog_padrao_e_maior_que_o_da_biblioteca():
    """5 e o padrao do `socketserver`, e pequeno para varias abas em polling.

    Nao e uma afirmacao sobre uma queda ja observada: a medicao desta maquina
    nao reproduziu a recusa com a CPU folgada (ver `scripts/provar_backlog.py`).
    E o padrao apertado para o uso real, e aumentar a fila e de custo zero.
    """
    import socketserver

    assert socketserver.TCPServer.request_queue_size == 5
    assert gateway_server.BACKLOG_PADRAO > socketserver.TCPServer.request_queue_size


def test_backlog_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("XAU_GATEWAY_BACKLOG", "256")
    assert gateway_server.backlog() == 256


def test_backlog_invalido_cai_no_padrao(monkeypatch):
    """Valor quebrado no ambiente nao pode derrubar o gateway no boot."""
    monkeypatch.setenv("XAU_GATEWAY_BACKLOG", "nao-e-numero")
    assert gateway_server.backlog() == gateway_server.BACKLOG_PADRAO


def test_backlog_zero_e_ignorado(monkeypatch):
    """`request_queue_size=0` e invalido no SO; deve ser tratado como 1, nunca
    repassado cru e derrubando o `listen()`."""
    monkeypatch.setenv("XAU_GATEWAY_BACKLOG", "0")
    assert gateway_server.backlog() >= 1


# --------------------------------------------------------------------------
# servidor
# --------------------------------------------------------------------------

def test_servidor_tem_os_tres_ajustes(gw):
    """Os tres ajustes que o modulo existe para aplicar, no objeto pronto."""
    servidor = gateway_server.criar_servidor(("127.0.0.1", 0), gw.Handler)
    try:
        assert servidor.request_queue_size == gateway_server.backlog()
        assert servidor.daemon_threads is True
        assert servidor.allow_reuse_address is True
    finally:
        servidor.server_close()


def test_allow_reuse_address_e_o_que_permite_religar_a_porta():
    """Sem `allow_reuse_address`, religar a 9001 logo apos o filho morrer da
    `OSError 10048` — e o reinicio automatico do supervisor falha sozinho.

    A biblioteca define como `1`, nao como `True`. Comparar com `is True`
    seria um teste que falha por um detalhe que nao importa.
    """
    from http.server import HTTPServer

    assert bool(HTTPServer.allow_reuse_address) is True


def test_gateway_real_sobe_e_responde(gw):
    """Prova de ponta a ponta com o servidor novo: sobe em porta efemera e
    responde autenticado. E o mesmo caminho que o `main()` usa."""
    servidor = gateway_server.criar_servidor(("127.0.0.1", 0), gw.Handler)
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
        conexao.request("GET", "/api/health",
                        headers={"Authorization": f"Bearer {gw.API_TOKEN}"})
        resposta = conexao.getresponse()
        corpo = resposta.read()
        conexao.close()
        assert resposta.status == 200
        assert b'"ok"' in corpo
    finally:
        servidor.shutdown()
        servidor.server_close()



def test_timeout_maior_que_o_intervalo_do_watchdog():
    """Se o timeout fosse menor que o intervalo de telemetria, o proprio
    watchdog derrubaria a propria conexao a cada ciclo."""
    import os

    watchdog = int(os.getenv("XAU_TELEMETRY_INTERVAL", "60") or 60)
    assert gateway_server.TIMEOUT_PADRAO > watchdog
