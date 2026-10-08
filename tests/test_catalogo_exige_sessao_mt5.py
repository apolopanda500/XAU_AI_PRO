"""
O CATALOGO DE ATIVOS DEPENDE DA SESSAO MT5 (medido 08/10/2026)
===============================================================
MEDIDO na conta 391773676 (XMGlobal-MT5 14), com o terminal aberto e logado:

    terminal SEM sessao:  symbols_get() -> None   -> count=0     status=unavailable
    terminal COM sessao:  symbols_get() -> 1640   -> count=1640  status=ok

A MESMA rota, os MESMOS argumentos. O defeito esta em `mt5_gateway._symbols`,
que lia `symbols_get()` sem garantir a sessao — enquanto a rota de candles ja
exigia isso em `mt5_gateway.py:2036` e `:2087`. Dois leitores do mesmo
terminal, uma versao com a guarda e outra sem: AGENTS.md §5.

O sintoma do dono era `Grafico indisponivel: Identidade de mercado invalida` /
`BTCUSD sem candles reais para M1` / `0 candles`, com o operador culpando o
frontend. O frontend estava certo: ele consumia um catalogo vazio.

A prova negativa desta trava e o BLOCO `TestProvaNegativa`: com `initialize`
recusando, a rota tem de devolver `unavailable` e NAO fabricar ativo. Um
catalogo cheio seria pior que um vazio — um simbolo sem ficha vira preco e
contrato inventados.
"""
from __future__ import annotations

import importlib

import pytest

_gateway = importlib.import_module("backend.mt5_gateway")
_aliases = importlib.import_module("backend.symbol_aliases")

#: `{"mt5": {"XAUUSD": "GOLD"}}` e CONFIG do operador, e o AGENTS.md §3 proibe
#: nome de ativo no codigo. Este teste FIXA o mapa, em vez de depender do que
#: esta em disco ou do que outro teste deixou — sem isto a ordem dos testes
#: mudava o resultado: sozinho passava, na suite inteira reprovava.
MAPA_XM = {"mt5": {"XAUUSD": "GOLD"}}


@pytest.fixture(autouse=True)
def _mapa_fixo(monkeypatch):
    monkeypatch.setattr(_aliases, "carregar", lambda: MAPA_XM)

CATALOGO_MEDIDO = [
    ("GOLD", "Derivatives\\Spot Metals\\GOLD", 100.0, 0.01),
    ("BTCUSD", "Cryptocurrencies\\Standard\\BTCUSD", 1.0, 0.01),
    ("EURUSD", "Forex\\Standard\\Majors\\EURUSD", 100_000.0, 0.00001),
]


class _Symbol:
    def __init__(self, nome, path, contract_size, point):
        self.name = nome
        self.path = path
        self.trade_contract_size = contract_size
        self.volume_min = 0.01
        self.volume_max = 50.0
        self.volume_step = 0.01
        self.digits = 5
        self.point = point
        self.currency_base = ""
        self.currency_profit = "USD"
        self.description = nome
        self.visible = True
        self.trade_mode = 4


class _Terminal:
    """Terminal que so responde depois de `initialize()` — como o MT5 real.

    O `MetaTrader5.symbols_get()` devolve `None`, sem lancar, quando a sessao
    do processo nao foi aberta. E `terminal_info()` devolve `None` pelo mesmo
    motivo. E por isso que `_mt5_connected()` existe.
    """

    def __init__(self, *, conecta: bool = True):
        self.conecta = conecta
        self.sessao = False
        self.chamadas_initialize = 0

    # --- o que o MT5 faz de verdade -------------------------------------
    def initialize(self, *_a, **_k):
        self.chamadas_initialize += 1
        if not self.conecta:
            return False
        self.sessao = True
        return True

    def terminal_info(self):
        return {"nome": "terminal64"} if self.sessao else None

    def symbols_get(self, *_a, **_k):
        if not self.sessao:
            return None
        return [_Symbol(*linha) for linha in CATALOGO_MEDIDO]


@pytest.fixture
def terminal(monkeypatch):
    t = _Terminal()
    monkeypatch.setattr(_gateway, "_mt5", lambda: t)
    monkeypatch.setattr(_gateway, "_ensure_mt5", lambda: t.initialize())
    _gateway._MARKET_CACHE.clear()
    yield t
    _gateway._MARKET_CACHE.clear()


class TestOCatalogoExigeSessao:
    def test_sem_sessao_no_processo_a_rota_ABRE_a_sessao(self, terminal):
        """O ponto: `terminal_info()` e `None` na entrada, e mesmo assim sai tudo."""
        assert terminal.terminal_info() is None, "a pre-condicao deste teste e nao haver sessao"
        assert terminal.symbols_get() is None, "sem sessao o MT5 devolve None, e nao lanca"

        r = _gateway._symbols()

        assert terminal.chamadas_initialize == 1, "a guarda nao disparou"
        assert r["status"] == "ok"
        assert r["count"] == len(CATALOGO_MEDIDO)
        # `discover_assets` ordena por `symbol.upper()` — a ordem do duble nao
        # e a ordem de saida, e o teste nao pode fingir que e.
        assert [linha["symbol"] for linha in r["symbols"]] == [
            "BTCUSD", "EURUSD", "GOLD",
        ]

    def test_a_ficha_do_ouro_vem_com_contrato_100(self, terminal):
        r = _gateway._symbols()
        ouro = next(linha for linha in r["symbols"] if linha["symbol"] == "GOLD")

        assert ouro["contract_size"] == 100.0
        assert ouro["asset_class"] == "metal"
        assert ouro["model_symbol"] == "XAUUSD"

    def test_a_cadeia_inteira_do_grafico_agora_responde(self, terminal):
        """O que a tela consome: catalogo -> ficha -> candles, sem lance."""
        assets = _gateway._universal_assets("mt5", "")

        assert assets["ok"] is True
        assert assets["count"] == len(CATALOGO_MEDIDO)
        # A resposta de sucesso NAO traz a chave `error` — a ausencia e o
        # estado, e `canonical_market_response` so a escreve na falha.
        assert assets.get("error") is None
        assert any(linha["symbol"] == "BTCUSD" for linha in assets["assets"])


class TestProvaNegativa:
    def test_com_initialize_recusado_a_rota_diz_nao_verificado(self, monkeypatch):
        """
        O caso que DEVE reprovar se a guarda encher o catalogo.

        Terminal que nao conecta: `symbols_get()` continua `None`. A resposta
        tem de ser `unavailable`, com contagem zero e o motivo do upstream —
        nunca um ativo inventado.
        """
        t = _Terminal(conecta=False)
        monkeypatch.setattr(_gateway, "_mt5", lambda: t)
        monkeypatch.setattr(_gateway, "_ensure_mt5", lambda: False)
        _gateway._MARKET_CACHE.clear()
        try:
            r = _gateway._symbols()

            assert r["status"] == "unavailable"
            assert r["count"] == 0
            assert r["symbols"] == []
        finally:
            _gateway._MARKET_CACHE.clear()

    def test_nao_presume_mercado_nem_corretora(self, monkeypatch):
        """Mercado vazio continua virando `other` no MT5 — a reserva do scope."""
        t = _Terminal()
        monkeypatch.setattr(_gateway, "_mt5", lambda: t)
        monkeypatch.setattr(_gateway, "_ensure_mt5", lambda: t.initialize())
        _gateway._MARKET_CACHE.clear()
        try:
            r = _gateway._universal_assets("mt5", "")
            assert r["market"] == "other"

            for mercado in ("forex", "metals", "indices", "other"):
                porMercado = _gateway._universal_assets("mt5", mercado)
                assert porMercado["count"] == len(CATALOGO_MEDIDO), mercado
        finally:
            _gateway._MARKET_CACHE.clear()