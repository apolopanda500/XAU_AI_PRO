"""Testes do servidor MCP de trading (roteamento puro, sem rede real)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import backend.trading_mcp as mcp  # noqa: E402


@pytest.fixture()
def http_stub(monkeypatch):
    chamadas: list[tuple[str, object]] = []

    def fake_http(path, payload=None, timeout=10.0):
        chamadas.append((path, payload))
        return {"http": 200, "ok": True, "path": path, "payload": payload}

    monkeypatch.setattr(mcp, "_http", fake_http)
    return chamadas


def test_tools_list_11_ferramentas():
    resposta = mcp.processar({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert len(resposta["result"]["tools"]) == 11


def test_initialize_handshake():
    resposta = mcp.processar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resposta["result"]["serverInfo"]["name"] == "xau-ai-pro-trading"


def test_notificacao_sem_resposta():
    assert mcp.processar({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_health_chama_gateway(http_stub):
    resultado = mcp.tool_call("health", {})
    assert resultado["path"] == "/api/health"


def test_place_order_nasce_dry_run(http_stub):
    mcp.tool_call("place_order", {"symbol": "XAUUSD", "side": "buy", "quantity": 0.01})
    path, payload = http_stub[-1]
    assert path == "/api/universal/order"
    assert payload["execute"] is False  # freio 1: toda ordem nasce dry-run


def test_place_order_bloqueado_sem_env(http_stub, monkeypatch):
    # Freio 2: com XAU_MCP_TRADING=0 o MCP nao manda ordem nenhuma.
    monkeypatch.setattr(mcp, "TRADING_HABILITADO", False)
    resultado = mcp.tool_call("place_order", {"symbol": "XAUUSD", "execute": True})
    assert resultado.get("bloqueado") is True
    assert not http_stub  # nenhuma ordem saiu do MCP


def test_place_order_executa_com_env(http_stub, monkeypatch):
    monkeypatch.setattr(mcp, "TRADING_HABILITADO", True)
    mcp.tool_call("place_order", {"symbol": "XAUUSD", "execute": True})
    _, payload = http_stub[-1]
    assert payload["execute"] is True


def test_request_id_unico_por_chamada(http_stub):
    mcp.tool_call("place_order", {"symbol": "XAUUSD"})
    mcp.tool_call("place_order", {"symbol": "XAUUSD"})
    ids = {http_stub[-2][1]["request_id"], http_stub[-1][1]["request_id"]}
    assert len(ids) == 2  # dedupe do gateway não pode engolir a segunda ordem


def test_close_position_respeita_travas(http_stub, monkeypatch):
    """Mesmas travas, e agora com a corretora obrigatoria.

    O teste chamava `close_position` sem `broker` e o MCP usava o default
    "mt5". Agora a corretora e exigida: uma chamada sem corretora e recusada
    antes de qualquer rota, e o teste precisa dizer para ONDE esta fechando.
    """
    monkeypatch.setattr(mcp, "TRADING_HABILITADO", False)
    escopo = {"broker": "binance", "market": "crypto-spot"}

    # Sem corretora: recusa na porta, sem tocar em rota nenhuma.
    resultado = mcp.tool_call("close_position", {"ticket": 1, "symbol": "BTCUSDT"})
    assert resultado.get("ok") is False
    assert "corretora" in resultado["error"].lower()
    assert not http_stub

    # Dry-run por padrao.
    mcp.tool_call("close_position", {"ticket": 1, "symbol": "BTCUSDT", **escopo})
    _, payload = http_stub[-1]
    assert payload["execute"] is False  # dry-run por padrao

    resultado = mcp.tool_call(
        "close_position", {"ticket": 1, "symbol": "BTCUSDT", "execute": True, **escopo})
    assert resultado.get("bloqueado") is True  # com XAU_MCP_TRADING=0, bloqueia

    monkeypatch.setattr(mcp, "TRADING_HABILITADO", True)
    mcp.tool_call(
        "close_position", {"ticket": 1, "symbol": "BTCUSDT", "execute": True, **escopo})
    _, payload = http_stub[-1]
    assert payload["execute"] is True
    assert payload["broker"] == "binance"


def test_ferramentas_de_leitura_exigem_corretora(http_stub):
    """account_summary, list_positions e get_quote sem default.

    As tres usavam `args.get("broker", "mt5")`. Sem corretora, o MCP precisa
    recusar - quem pede saldo, posicao ou cotacao tem de dizer de ONDE.
    """
    for nome, argumentos in (
        ("account_summary", {}),
        ("list_positions", {}),
        ("get_quote", {"symbol": "BTCUSDT"}),
    ):
        resultado = mcp.tool_call(nome, argumentos)
        assert resultado.get("ok") is False, nome
        assert "corretora" in resultado["error"].lower(), nome
    assert not http_stub, "nenhuma requisicao pode sair sem corretora definida"


def test_catalogo_de_corretoras_vem_do_registro():
    """A lista de corretoras do MCP nao pode ser escrita a mao."""
    from backend.broker_registry import BROKERS

    esperado = {d.id for d in BROKERS.values() if d.public_data}
    assert set(mcp.BROKERS_EXECUCAO) == esperado
    assert len(esperado) >= 5, "o catalogo do projeto lista 9 corretoras"


def test_ferramenta_desconhecida(http_stub):
    assert "desconhecida" in mcp.tool_call("nao_existe", {})["error"]


def test_emergency_resume_bloqueado_sem_trava(http_stub, monkeypatch):
    monkeypatch.setattr(mcp, "TRADING_HABILITADO", False)
    monkeypatch.setenv("XAU_ENABLE_EMERGENCY_RESUME", "0")
    resultado = mcp.tool_call("emergency_resume", {})
    assert resultado.get("bloqueado") is True
    assert not http_stub
    monkeypatch.setattr(mcp, "TRADING_HABILITADO", True)
    monkeypatch.setenv("XAU_ENABLE_EMERGENCY_RESUME", "1")
    mcp.tool_call("emergency_resume", {})
    assert http_stub[-1][0] == "/api/universal/emergency-resume"


def test_metodo_desconhecido_erro_rpc():
    resposta = mcp.processar({"jsonrpc": "2.0", "id": 9, "method": "metodo/que/nao/existe"})
    assert resposta["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Porta do gateway: um dado, uma fonte (AGENTS.md §5 - dois lados divergindo)
# ---------------------------------------------------------------------------


def test_gateway_padrao_segue_a_porta_do_gateway():
    """MEDIDO 22/10/2026: gateway em 9011, MCP em 9001 = tools mortos."""
    url = mcp.gateway_padrao({"XAU_GATEWAY_PORT": "9011"})
    assert url == "http://127.0.0.1:9011"
    # prova negativa: o padrao antigo (9001) e exatamente o defeito medido.
    assert url != "http://127.0.0.1:9001"


def test_gateway_explicito_vence_a_porta():
    url = mcp.gateway_padrao({"XAU_MCP_GATEWAY": "http://127.0.0.1:9001/",
                              "XAU_GATEWAY_PORT": "9011"})
    assert url == "http://127.0.0.1:9001"


def test_porta_invalida_volta_para_o_padrao():
    for estranho in ("9011abc", "0", "70000", "-1", " "):
        url = mcp.gateway_padrao({"XAU_GATEWAY_PORT": estranho})
        assert url == "http://127.0.0.1:9001", (estranho, url)


def test_ambiente_sem_nada_cai_no_padrao():
    assert mcp.gateway_padrao({}) == "http://127.0.0.1:9001"


def test_gateway_do_modulo_coerente_com_o_ambiente():
    """O valor carregado no import tem de ser o que a funcao calcula hoje."""
    assert mcp.GATEWAY == mcp.gateway_padrao(os.environ)


def test_gateway_do_modulo_e_uma_url_local():
    """Prova negativa: fora de loopback o MCP nao fala com ninguem."""
    assert mcp.GATEWAY.startswith("http://127.0.0.1:")


# ---------------------------------------------------------------------------
# Header de autorizacao (MEDIDO 25/10/2026)
# ---------------------------------------------------------------------------
# O gateway le `Authorization: Bearer <XAU_GATEWAY_TOKEN>` em
# `mt5_gateway._autorizado`, e `_http()` nao enviava NENHUM header - entao
# TODO caminho respondia 401, inclusive o de leitura, com o token certo na
# mao. Dois lados do mesmo dado divergindo (AGENTS.md §5).
#
# A ORDEM do leitor tem de ser a mesma do gateway: ambiente vence `.env`.
# ---------------------------------------------------------------------------


class _RespostaFake:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"ok": true}'


def _http_com_urlopen_fake(monkeypatch) -> dict[str, str]:
    """Roda `_http` de verdade com `urlopen` fake; devolve o que saiu no header."""
    vistos: dict[str, str] = {}

    def fake_urlopen(requisicao, timeout=None):
        for chave, valor in requisicao.header_items():
            vistos[chave.lower()] = valor
        return _RespostaFake()

    monkeypatch.setattr(mcp.urllib.request, "urlopen", fake_urlopen)
    assert mcp._http("/health")["ok"] is True
    return vistos


def test_http_envia_authorization_bearer(monkeypatch):
    monkeypatch.setattr(mcp, "GATEWAY_TOKEN", "token-de-teste")
    vistos = _http_com_urlopen_fake(monkeypatch)
    assert vistos.get("authorization") == "Bearer token-de-teste"


def test_http_sem_token_nao_envia_authorization(monkeypatch):
    """Prova negativa: sem token nao ha header - `Bearer ` vazio e pior que nada."""
    monkeypatch.setattr(mcp, "GATEWAY_TOKEN", "")
    vistos = _http_com_urlopen_fake(monkeypatch)
    assert "authorization" not in vistos


def test_token_do_ambiente_vence_o_dotenv(monkeypatch):
    """Mesma ordem do gateway: ambiente vence `.env`, nunca o contrario."""
    monkeypatch.setattr(mcp, "_token_do_dotenv", lambda: "do-arquivo")
    assert mcp.token_gateway({"XAU_GATEWAY_TOKEN": "  da-sessao  "}) == "da-sessao"
    # prova negativa: sem ambiente, cai no arquivo
    assert mcp.token_gateway({}) == "do-arquivo"


def test_config_do_mcp_nao_fixa_porta():
    """Nenhum dos dois arquivos pode pinar porta: quem manda e o ambiente.

    MEDIDO 25/10/2026: `XAU_MCP_GATEWAY=http://127.0.0.1:9001` estava nos
    DOIS arquivos, e a 9001 e do `terminal64.exe` - o gateway ativo estava em
    9011. Lido por JSON, nao por texto (AGENTS.md §6).
    """
    raiz = Path(ROOT)
    for nome in ("opencode.json", ".mcp.json"):
        dados = json.loads((raiz / nome).read_text(encoding="utf-8"))
        bloco = (dados.get("mcp") or dados.get("mcpServers"))["xau-trading"]
        ambiente = bloco.get("environment") or bloco.get("env") or {}
        assert "XAU_MCP_GATEWAY" not in ambiente, nome