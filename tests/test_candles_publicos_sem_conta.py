# -*- coding: utf-8 -*-
"""Candles: quem responde, quem recusa e com que motivo.

REESCRITO em 12/11/2026 23:20 sob a decisao (a) do dono para a P1.3623. O
contrato antigo deste arquivo descrevia um mundo que ja nao existe: exigia
candles publicos de `mexc` e `binance` quando o cofre estivesse vazio. Nada
aqui foi afrouxado — onde o teste antigo exigia candle, este exige a RECUSA
COM MOTIVO, que e mais exigente porque tambem nomeia quem recusou e proibe
inventar dado de outra origem.

MEDIDO (nao presumido) em 12/11/2026 23:14, `.venv` deste repositorio:

    READ_BROKERS        ['mt5']
    CODE_ONLY_BROKERS   []
    read_brokers()      ['mt5']
    code_only_brokers() []
    BROKERS             mt5 -> active
                        binance, mexc, bybit, okx, bitget,
                        coinbase, kraken, kucoin -> planned
    _universal_candles('mexc', 'crypto-spot', 'BTCUSDT', 'M15', 5)
        -> {'ok': False, 'status': 'unsupported', 'broker': 'mexc',
            'market': 'crypto-spot', 'source': 'universal_gateway',
            'candles': [], 'count': 0,
            'error': 'corretora não suportada'}      (sem `fallback_publico`)
        -> _response_status(...) == 501
    _universal_candles('mt5', 'metals', 'XAUUSD', 'M1', 3)
        -> {'ok': True, 'status': 'ok', 'source': 'mt5_gateway',
            'candles': [... 3 velas reais ...]}       (sem `fallback_publico`)

PORQUE — lendo o codigo, nao a conclusao: `_universal_candles` recusa ANTES de
instanciar cliente de exchange (`if broker not in READ_BROKERS: return
canonical_unavailable(..., reason='corretora não suportada')`), e
`_com_fallback_publico` so e alcancavel pela saida do ramo `mt5` e pela saida
do ramo de exchange JA suportada. Corretora `planned` nao chega a nenhuma das
duas. A premissa antiga ("mexc/binance viraram code_only") estava ERRADA:
`code_only` e conjunto VAZIO; o que existe e so o `mt5` em `READ_BROKERS`.

A decisao do dono de 12/10/2026 — "o grafico nunca morre" — continua de pe e
este arquivo continua a prova-la: o fallback publico SOBREVIVE para o `mt5`
(`test_mt5_sem_vela_cai_no_publico_e_declara`) e nunca e apresentado como dado
de execucao (`execucao is False`). O que deixou de existir foi o caminho em que
uma corretora `planned` era lida mesmo assim.

Sem rede: os dubles entram so onde a venue falaria; o resto e o caminho de
producao (`_universal_candles` -> `_candles_from_raw` -> `_com_fallback_publico`).
"""
from __future__ import annotations

import pytest

import backend.mt5_gateway as gw
from backend.broker_registry import BROKERS

#: Corretoras do catalogo que NAO estao na lista de leitura e nao sao
#: `code_only` — hoje, todas as `planned`. Derivado das duas fontes reais
#: (catalogo e `READ_BROKERS`), nunca de uma lista escrita a mao.
PLANEJADAS = sorted(set(BROKERS) - set(gw.READ_BROKERS) - set(gw.CODE_ONLY_BROKERS))


class NaoDeviaChamar(BaseException):
    """`BaseException` de proposito.

    `_com_fallback_publico` engole `Exception` (`except Exception: return
    resposta`), entao um duble que levantasse `AssertionError` seria COMIDO em
    silencio e o teste negativo passaria sem medir nada. Este tipo atravessa.
    """


@pytest.fixture
def sem_cofre(monkeypatch):
    """O cofre de credenciais nao existe — e nem pode ser consultado.

    Se qualquer ponto do caminho de LEITURA encostar no cofre, este duble
    levanta e o teste reprova com o nome de quem chamou.
    """
    def _proibido(*args, **kwargs):
        raise AssertionError(
            "a leitura encostou no cofre de credenciais: "
            f"args={args} kwargs={kwargs}"
        )

    monkeypatch.setattr(gw, "_stored_exchange_credentials", _proibido)


@pytest.fixture
def cliente_proibido(monkeypatch):
    """Corretora fora da leitura nao pode nem INSTANCIAR cliente de exchange."""
    def _proibido(broker, market, *args, **kwargs):
        raise AssertionError(
            "corretora fora de READ_BROKERS instanciou cliente de exchange: "
            f"broker={broker} market={market} args={args} kwargs={kwargs}"
        )

    monkeypatch.setattr(gw, "_exchange_client", _proibido)


@pytest.fixture
def sem_cache(monkeypatch):
    """Cache de mercado isolado: `_cached_market` guarda 1 s por chave."""
    monkeypatch.setattr(gw, "_MARKET_CACHE", {})


def _publico_com_candles(monkeypatch, fonte: str = "publica-teste"):
    """Fonte publica que responde (formato de `mercado_publico.ohlc_publico`)."""
    def _responde(symbol, timeframe="M5", limit=300):
        return {
            "candles": [
                {"time": 1_769_000_000 + i * 900, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 3.0}
                for i in range(3)
            ],
            "fonte": fonte,
            "fonte_url": "https://exemplo",
            "execucao": False,
            "observacao": "duble de fonte publica",
        }

    monkeypatch.setattr("backend.mercado_publico.ohlc_publico", _responde)


def _velas_mt5(n: int = 2) -> list[dict]:
    """Linhas no formato que `_mt5_candles` devolve (`_candle_row`)."""
    base = 1_794_542_700
    return [
        {
            "time": base + i * 900,
            "open": 3900.0 + i,
            "high": 3901.0 + i,
            "low": 3899.0 + i,
            "close": 3900.5 + i,
            "volume": 100.0 + i,
        }
        for i in range(n)
    ]


def _mt5_devolve(monkeypatch, velas: list[dict]):
    """A corretora devolve estas velas (ou nenhuma) — sem tocar no terminal."""
    monkeypatch.setattr(
        gw,
        "_mt5_candles",
        lambda symbol, timeframe="M5", count=300: {"candles": list(velas)},
    )


# ---------------------------------------------------------------- corretora fora da leitura


def test_corretora_planejada_recusa_com_motivo_e_nao_lanca(sem_cofre, cliente_proibido):
    """PROVA: `mexc` nao entrega candle, nao toca no cofre e diz PORQUE.

    O grafico nao pode morrer sem nome: a recusa carrega o motivo, o status
    HTTP vem 501 (nao um 200 com lista vazia) e nenhum dado de outra origem e
    apresentado no lugar.
    """
    resposta = gw._universal_candles("mexc", "crypto-spot", "BTCUSDT", "M15", 5)

    assert resposta["candles"] == []
    assert resposta["count"] == 0
    assert resposta["ok"] is False
    assert resposta["status"] == "unsupported"
    assert resposta["error"] == "corretora não suportada"
    assert resposta["source"] == "universal_gateway"
    # Recusa COM nome chega ao cliente como 501 — nunca 200 de grafico vazio.
    assert gw._response_status(resposta) == 501
    # PUBLICO NAO E INVENTADO para corretora fora da lista de leitura.
    assert "fallback_publico" not in resposta


@pytest.mark.parametrize("broker", PLANEJADAS)
def test_toda_corretora_fora_da_leitura_segue_o_mesmo_contrato(
    broker, sem_cofre, cliente_proibido
):
    """A recusa e da CLASSE, nao de uma corretora: o catalogo manda."""
    resposta = gw._universal_candles(broker, "crypto-spot", "BTCUSDT", "M15", 5)

    assert resposta["candles"] == []
    assert resposta["count"] == 0
    assert resposta["status"] == "unsupported"
    assert resposta["error"] == "corretora não suportada"
    assert resposta["broker"] == broker.lower()
    assert gw._response_status(resposta) == 501
    assert "fallback_publico" not in resposta


def test_o_conjunto_medido_nao_e_vazio_e_nao_engole_o_mt5():
    """Guarda da propria guarda: parametrizacao vazia passa calada.

    Um `parametrize` sem casos nao mede nada e o CI fica verde do mesmo jeito.
    """
    assert "mt5" in gw.READ_BROKERS, "o mt5 saiu de READ_BROKERS: reescrever este arquivo"
    assert PLANEJADAS, "sem corretoras fora da leitura, o teste parametrizado nao mede nada"
    assert "mt5" not in PLANEJADAS
    assert set(gw.READ_BROKERS) <= set(BROKERS)
    assert not (set(gw.READ_BROKERS) & set(gw.CODE_ONLY_BROKERS))


def test_code_only_tem_motivo_proprio_e_nao_se_confunde_com_planejada(monkeypatch, sem_cofre, cliente_proibido):
    """O ramo `code_only` hoje esta VAZIO — por isso o conjunto e injetado.

    Injetar aqui NAO repete a logica: exercita a producao
    (`_unsupported_read_response`) com a condicao que a torna alcancavel. O que
    se mede e que ele diz outra coisa: "esta em code_only", nao "nao suportada".
    """
    monkeypatch.setattr(gw, "CODE_ONLY_BROKERS", {"mexc"})

    resposta = gw._universal_candles("mexc", "crypto-spot", "BTCUSDT", "M15", 5)

    assert resposta["candles"] == []
    assert resposta["status"] == "unsupported"
    assert resposta["source"] == "mexc_code_only"
    assert resposta["supported"] is False
    assert resposta["production_ready"] is False
    assert "code_only" in resposta["error"]
    assert resposta["error"] != "corretora não suportada"
    assert gw._response_status(resposta) == 501


# ---------------------------------------------------------------- conta continua privada


def test_conta_ainda_exige_credencial(monkeypatch):
    """PROVA NEGATIVA: liberar leitura nao libera conta.

    O `private=True` continua lendo o cofre: este teste falha se a leitura
    publica e a privada passarem a usar o mesmo caminho sem distinguir.
    """
    chamadas: list = []

    def _cofre(*args, **kwargs):
        chamadas.append(args)
        return None

    monkeypatch.setattr(gw, "_stored_exchange_credentials", _cofre)
    cliente = gw._exchange_client("mexc", "crypto-spot", private=True)
    assert chamadas, "caminho privado nao consultou o cofre"
    assert cliente.account_id == ""


# ---------------------------------------------------------------- mt5: corretora, sempre


def test_mt5_com_vela_entrega_a_vela_da_corretora_e_nao_encosta_no_publico(
    monkeypatch, sem_cache, sem_cofre
):
    """A REGRESSAO DO BUG DE 12/11/2026: MT5 aberto => candle do MT5.

    O grafico caiu no yahoo GC=F com a ultima vela degenerada mesmo com o
    terminal ligado. Aqui o publico esta armado para EXPLODIR: se a resposta
    da corretora for descartada, o teste reprova em vez de mostrar dado de
    terceiro sem aviso.
    """
    _mt5_devolve(monkeypatch, _velas_mt5(2))

    def _publico_proibido(*args, **kwargs):
        raise NaoDeviaChamar("MT5 entregou vela e o publico foi chamado mesmo assim")

    monkeypatch.setattr("backend.mercado_publico.ohlc_publico", _publico_proibido)

    resposta = gw._universal_candles("mt5", "metals", "XAUUSD", "M15", 7)

    assert resposta["ok"] is True
    assert resposta["status"] == "ok"
    assert resposta["count"] == 2
    assert resposta["candles"][0]["close"] == 3900.5
    assert resposta["source"] == "mt5_gateway"
    assert resposta["market"] == "metals"
    assert "fallback_publico" not in resposta


def test_mt5_sem_vela_cai_no_publico_e_declara(monkeypatch, sem_cache, sem_cofre):
    """A decisao do dono (12/10/2026): sem vela da corretora, o grafico VIVE.

    Vive DECLARANDO de onde veio — `execucao: false` viaja junto, e e o que
    impede montar ordem sobre preco de terceiro.
    """
    _mt5_devolve(monkeypatch, [])
    _publico_com_candles(monkeypatch)

    resposta = gw._universal_candles("mt5", "metals", "XAUUSD", "M15", 9)

    assert resposta["candles"], "sem fallback, o grafico morre sem motivo"
    assert resposta["count"] == 3
    assert resposta.get("fallback_publico") is True
    assert resposta.get("execucao") is False
    assert resposta.get("fonte") == "publica-teste"
    # A corretora continua nomeada: o publico entrou no LUGAR do dado, nao no
    # lugar do nome de quem devia responder.
    assert resposta["source"] == "mt5_gateway"


def test_tudo_falhando_devolve_motivo_sem_excecao(monkeypatch, sem_cache, sem_cofre):
    """Corretora e publico falhando: resposta intacta, com motivo, sem crash.

    E sem `fallback_publico`: falhar duas vezes nao e motivo para inventar vela.
    """
    _mt5_devolve(monkeypatch, [])
    monkeypatch.setattr(
        "backend.mercado_publico.ohlc_publico",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sem rede")),
    )

    resposta = gw._universal_candles("mt5", "metals", "XAUUSD", "M15", 11)

    assert resposta["candles"] == []
    assert str(resposta.get("error") or ""), "falha sem motivo e grafico morto sem nome"
    assert "fallback_publico" not in resposta


# ---------------------------------------------------------------- nenhum ativo presumido


def test_simbolo_vazio_recusa_sem_inventar_ativo():
    """AGENTS.md §3: simbolo vazio e RECUSA COM MOTIVO, nunca ativo padrao."""
    with pytest.raises(ValueError, match="symbol é obrigatório"):
        gw._universal_candles("mt5", "metals", "", "M15", 5)
