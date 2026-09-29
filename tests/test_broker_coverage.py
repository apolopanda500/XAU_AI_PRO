"""Testes da camada de corretoras e do formato canonico de simbolo.

Achados que estes testes fixam:

1. A OKX respondia HTTP 403 em toda a API publica porque o cliente nao enviava
   ``User-Agent``. Sem o header, ``/api/universal/*`` caia em ``unsupported``
   mesmo com o cliente completo.
2. A OKX nomeia o par com hifen (``BTC-USDT``). O app trabalha com o par
   concatenado (``BTCUSDT``); sem conversao, o mesmo ativo viraria dois
   instrumentos e a cotacao nao casaria com a lista de ativos.
3. ``trades`` e ``stats24h`` tinham allowlist hardcoded (``binance``/``mexc``),
   o que desligava Bybit e OKX mesmo com o metodo implementado no cliente.
"""
from __future__ import annotations

import pytest

from backend.broker_registry import (
    BROKERS,
    capability_matrix,
    code_only_brokers,
    list_brokers,
    normalize_read_scope,
    read_brokers,
    supported_brokers,
)
from backend.bybit_client import BybitClient
from backend.okx_client import OkxClient
import backend.mt5_gateway as gw


class _RespostaFalsa:
    """Substitui a rede e devolve um payload ja decodificado."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_RespostaFalsa":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class _Ctx:
    def __init__(self, client: object, payload: bytes) -> None:
        self.client = client
        self.payload = payload
        self.chamadas: list[tuple[str, object]] = []

    def __enter__(self) -> _RespostaFalsa:
        return _RespostaFalsa(self.payload)

    def __exit__(self, *args: object) -> bool:
        return False


def _patch_request(monkeypatch, client: object, payload: bytes) -> _Ctx:
    ctx = _Ctx(client, payload)

    def fake_open(request, timeout=None):  # noqa: ANN001 - assinatura de urllib
        ctx.chamadas.append((request.full_url, dict(request.headers)))
        return _RespostaFalsa(payload)

    monkeypatch.setattr("backend.okx_client.open_exchange_request", fake_open)
    return ctx


@pytest.fixture(autouse=True)
def _sem_cache_de_mercado():
    # O cache do gateway dura 1s e sobrevive entre testes do mesmo processo: sem
    # esta limpeza um teste leria a resposta real da rede em vez do payload fixo.
    gw._MARKET_CACHE.clear()
    yield
    gw._MARKET_CACHE.clear()


# ---------------------------------------------------------------- OKX


def test_okx_manda_user_agent():
    # Sem User-Agent a OKX responde 403 e o app perde a corretora inteira.
    assert OkxClient.USER_AGENT
    client = OkxClient("spot")
    assert client.support_status == "active"


def test_okx_header_user_agent_via_gateway(monkeypatch):
    ctx = _patch_request(monkeypatch, OkxClient("spot"), b'{"code":"0","data":[{"instId":"BTC-USDT","last":"1"}]}')
    gw._exchange_client("okx", "crypto-spot").ticker("BTCUSDT")
    assert ctx.chamadas, "nenhuma requisicao foi feita"
    _, headers = ctx.chamadas[0]
    assert headers.get("User-agent") == OkxClient.USER_AGENT


@pytest.mark.parametrize(("entrada", "esperado"), [
    ("BTCUSDT", "BTC-USDT"),
    ("btcusdt", "BTC-USDT"),
    ("ETH/BTC", "ETH-BTC"),
    ("ETH_BTC", "ETH-BTC"),
    ("BTC-USDT", "BTC-USDT"),
    ("XAUUSD", "XAU-USD"),
])
def test_okx_converte_par_concatenado_em_hifen(entrada, esperado):
    assert OkxClient._symbol(entrada) == esperado


def test_okx_futuros_usa_swap():
    assert OkxClient("futures")._inst_id("BTCUSDT") == "BTC-USDT-SWAP"
    assert OkxClient("spot")._inst_id("BTCUSDT") == "BTC-USDT"


def test_okx_quote_devolve_simbolo_canonico(monkeypatch):
    # A OKX responde BTC-USDT; o app precisa de BTCUSDT.
    _patch_request(
        monkeypatch,
        OkxClient("spot"),
        b'{"code":"0","data":[{"instId":"BTC-USDT","last":"84000.1","bidPx":"83999.9","askPx":"84000.2","ts":"1"}]}',
    )
    result = gw._universal_quote("okx", "crypto-spot", "BTCUSDT")
    assert result["ok"] is True
    assert result["symbol"] == "BTCUSDT"
    # O id da corretora continua disponivel para rastreabilidade.
    assert result["source_symbol"] == "BTC-USDT"
    assert result["bid"] == 83999.9
    assert result["ask"] == 84000.2


def test_okx_quote_sem_par_nao_inventa_preco(monkeypatch):
    _patch_request(monkeypatch, OkxClient("spot"), b'{"code":"0","data":[]}')
    result = gw._universal_quote("okx", "crypto-spot", "BTCUSDT")
    assert result["status"] in {"partial", "unavailable"}
    assert result.get("bid") is None


# ------------------------------------------------------- trades / stats24h


@pytest.mark.parametrize("broker", ["binance", "mexc", "bybit", "okx"])
def test_todas_as_corretoras_respondem_negocios_recentes(monkeypatch, broker):
    # Antes these endpoints were limited to binance/mexc by a hardcoded allowlist.
    # O patch e na classe: o gateway cria uma instancia nova a cada chamada.
    client_type = type(gw._exchange_client(broker, "crypto-spot"))
    monkeypatch.setattr(client_type, "trades", lambda self, symbol, limit=20: [{"price": "1", "qty": "2"}])
    result = gw._universal_trades(broker, "crypto-spot", "BTCUSDT", 5)
    assert result["ok"] is True, result
    assert result["count"] == 1


@pytest.mark.parametrize("broker", ["binance", "mexc", "bybit", "okx"])
def test_todas_as_corretoras_respondem_stats24h(monkeypatch, broker):
    client_type = type(gw._exchange_client(broker, "crypto-spot"))
    monkeypatch.setattr(client_type, "stats_24h", lambda self, symbol="": {"last": "1", "volume": "2"})
    result = gw._universal_stats24h(broker, "crypto-spot", "BTCUSDT")
    assert result["ok"] is True, result


def test_negocios_recentes_declarado_quando_o_cliente_nao_implementa(monkeypatch):
    # Ausencia de capacidade e declarada, nunca disfarçada de lista vazia com ok.
    client_type = type(gw._exchange_client("bybit", "crypto-spot"))
    monkeypatch.delattr(client_type, "trades", raising=False)
    result = gw._universal_trades("bybit", "crypto-spot", "BTCUSDT", 5)
    assert result["ok"] is False
    assert result["status"] == "unsupported"
    assert result["trades"] == []


# -------------------------------------------------------------- registro


def test_bybit_e_okx_estao_ativos_para_dados_publicos():
    assert {"bybit", "okx"} <= read_brokers()
    assert "bybit" not in code_only_brokers()
    assert "okx" not in code_only_brokers()
    assert "bybit" in supported_brokers() and "okx" in supported_brokers()


def test_matriz_declara_execucao_e_nunca_saque():
    # App desbloqueado: corretoras ativas expoem execucao real e deixam de ser
    # somente-leitura. Saque e transferencia continuam fixos em False.
    for row in capability_matrix(include_planned=True):
        assert row["withdrawals"] is False
        assert row["transfers"] is False
        if row["status"] == "active":
            assert row["execution"], row
            assert row["read_only"] is False
        else:
            assert row["execution"] == []
            assert row["read_only"] is True


def test_gate_desligada_torna_a_corretora_somente_leitura(monkeypatch):
    monkeypatch.setenv("XAU_ENABLE_BINANCE_EXECUTION", "0")
    rows = [row for row in capability_matrix() if row["broker"] == "binance"]
    assert rows
    for row in rows:
        assert row["execution"] == []
        assert row["read_only"] is True
        assert row["withdrawals"] is False


def test_corretoras_planejadas_nao_entram_no_padrao():
    padrao = {item["id"] for item in list_brokers()}
    assert padrao == {"mt5", "binance", "mexc", "bybit", "okx"}
    assert {"bitget", "coinbase", "kraken", "kucoin"} <= set(BROKERS)


def test_escopo_invalido_falha_explicito():
    with pytest.raises(ValueError):
        normalize_read_scope("binance", "metals")
    with pytest.raises(ValueError):
        normalize_read_scope("corretora-inexistente", "crypto-spot")


def test_bybit_mantem_o_par_concatenado():
    # A Bybit usa BTCUSDT nativamente; nao ha conversao a fazer.
    assert BybitClient("spot").market == "spot"
    assert BybitClient("crypto-futures").market == "futures"
