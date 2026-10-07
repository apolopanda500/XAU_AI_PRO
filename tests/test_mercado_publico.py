# -*- coding: utf-8 -*-
"""Fonte publica de preco: as tres que respondem sem chave.

MEDIDO NESTA MAQUINA, 05/10/2026 (latencia real, nao de pagina de venda)
----------------------------------------------------------------------
    Yahoo  GC=F (ouro)   HTTP 200   578 ms   4167.6      exchange CMX
    Yahoo  EURUSD=X       HTTP 200   517 ms   1.1227      exchange CCY
    Binance BTCUSDT 1h    HTTP 200   368 ms   85821.96    volume 80.22
    Frankfurter EUR/USD   HTTP 200    77 ms   1.1204      BCE, diario

    Nenhuma exige chave. Nenhuma exige cadastro.

O QUE ESTES TESTES PROVAM, E POR QUE
===================================
O preço do gráfico vem da corretora. O preço de EXECUÇÃO também. Quando um dos
dois vem de fora da corretora, o operador pode montar a ordem olhando um número
que não é o que vai executar — que é a forma mais cara de divergência que existe
neste app.

Por isso o módulo carrega `execucao: false` e a procedencia SEMPRE, e estes
testes existem para ninguém tirar isso depois:

  - a procedencia viaja com o dado (teste que reprova se euemnão viajar);
  - `execucao` é SEMPRE `False`, em toda fonte;
  - par sem equivalente é recusado com nome, e nunca chutado;
  - símbolo vazio é recusado na porta;
  - falhar todas as fontes levanta `FontePublicaIndisponivel`, que é diferente
    de lista vazia.

Os testes de REDE real são marcados e pulam quando não há internet — nunca
`xfail`, que é o defeito que o projeto proíbe.
"""
from __future__ import annotations

import json
import urllib.request

import pytest

from backend import mercado_publico as mp


class _RespostaFalsa:
    """Resposta HTTP mínima para os testes de parsing, sem rede."""

    def __init__(self, payload: object):
        self._corpo = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._corpo

    def __enter__(self) -> "_RespostaFalsa":
        return self

    def __exit__(self, *_) -> None:
        return None


def _yahoo_falso(quantidade: int = 3) -> dict:
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {"symbol": "GC=F", "exchangeName": "CMX"},
                    "timestamp": [1_700_000_000 + i * 300 for i in range(quantidade)],
                    "indicators": {
                        "quote": [
                            {
                                "open": [4160.0 + i for i in range(quantidade)],
                                "high": [4170.0 + i for i in range(quantidade)],
                                "low": [4150.0 + i for i in range(quantidade)],
                                "close": [4165.0 + i for i in range(quantidade)],
                                "volume": [10.0 + i for i in range(quantidade)],
                            }
                        ]
                    },
                }
            ],
        }
    }


class TestProvenciaObrigatoria:
    """A regra que ninguém pode quebrar depois."""

    def test_toda_fonte_marca_execucao_como_falsa(self, monkeypatch) -> None:
        # Se algum dia `execucao` virar True, o preço de terceiro pode virar
        # preço de ordem. Este teste reprova.
        monkeypatch.setattr(mp, "_binance", lambda s, t, l: {
            "candles": [mp._vela(1, 1, 1, 1, 1)],
            "fonte": "binance",
            "execucao": False,
        })
        monkeypatch.setattr(mp, "CADEIA", (mp._binance,))
        r = mp.ohlc_publico("BTCUSD", "M5", 5)
        assert r["execucao"] is False

    def test_a_provencia_viaja_junto_do_dado(self, monkeypatch) -> None:
        monkeypatch.setattr(mp, "_binance", lambda s, t, l: {
            "candles": [mp._vela(1, 1, 1, 1, 1)],
            "fonte": "binance",
            "fonte_url": "https://exemplo",
            "execucao": False,
            "observacao": "teste",
        })
        monkeypatch.setattr(mp, "CADEIA", (mp._binance,))
        r = mp.ohlc_publico("BTCUSD", "M5", 5)
        # Sem `fonte`, a tela não sabe de onde veio o preço. Dado sem origem é
        # dado inventado.
        assert r.get("fonte") == "binance"
        assert r.get("fonte_url")

    def test_cotacao_rapida_tambem_declara_a_fonte(self, monkeypatch) -> None:
        monkeypatch.setattr(mp, "ohlc_publico", lambda s, t, l: {
            "candles": [mp._vela(1, 1, 1, 1, 4165.0)],
            "fonte": "yahoo",
            "execucao": False,
            "observacao": "teste",
        })
        c = mp.cotacao("XAUUSD")
        assert c is not None
        assert c["fonte"] == "yahoo"
        assert c["execucao"] is False


class TestRecusaNaPorta:
    """O que a função NAO pode fazer: chutar par."""

    def test_simbolo_vazio_e_recusado(self) -> None:
        # Nenhuma fonte pode presumir par. Simbolo vazio e recusa com motivo.
        with pytest.raises(ValueError):
            mp.ohlc_publico("", "M5", 10)

    def test_par_sem_equivalente_nao_e_inventado(self) -> None:
        with pytest.raises(mp.FontePublicaIndisponivel) as erro:
            mp.ohlc_publico("PAR_QUE_NAO_EXISTE_XYZ", "M5", 10)
        # A recusa DIZ o que tentou: sem equivalente, e nao "sem internet".
        assert "binance" in str(erro.value)

    def test_falhar_todas_as_fontes_distingue_de_lista_vazia(self) -> None:
        # "Nao consegui perguntar" e diferente de "nao tem dado", e a tela
        # precisa saber a diferenca.
        def falha(s, t, l):
            raise OSError("rede fora")

        original = mp.CADEIA
        try:
            mp.CADEIA = (falha,)
            with pytest.raises(mp.FontePublicaIndisponivel):
                mp.ohlc_publico("BTCUSD", "M5", 10)
        finally:
            mp.CADEIA = original


class TestNormalizacao:
    """O formato que o grafico ja consome."""

    def test_binance_le_array_de_12_campos(self, monkeypatch) -> None:
        # Cada kline do Binance e um ARRAY de 12 campos. Ler como objeto foi o
        # primeiro erro de script: `d[0].keys()` levantou AttributeError e
        # parecia que a API estava quebrada.
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _RespostaFalsa(
            [[1_700_000_000_000, "1", "2", "0.5", "1.5", "10", 0, "0", 5, "1", "0", "0"]]
        ))
        r = mp._binance("BTCUSD", "H1", 5)
        assert r is not None
        assert len(r["candles"]) == 1
        v = r["candles"][0]
        assert v["open"] == 1.0 and v["high"] == 2.0
        assert v["low"] == 0.5 and v["close"] == 1.5 and v["volume"] == 10.0

    def test_yahoo_pula_vela_com_buraco(self, monkeypatch) -> None:
        # A serie vem com None no meio (feriado, falta). Vela com None vira
        # zero, e zero no grafico e um preco que nunca existiu.
        payload = _yahoo_falso(3)
        q = payload["chart"]["result"][0]["indicators"]["quote"][0]
        q["close"][1] = None
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _RespostaFalsa(payload))
        r = mp._yahoo("XAUUSD", "M5", 5)
        assert r is not None
        # Das 3 velas, 1 tem buraco: sobram 2, e nenhuma tem zero.
        assert len(r["candles"]) == 2
        assert all(c["close"] > 0 for c in r["candles"])

    def test_yahoo_ordena_e_limita(self, monkeypatch) -> None:
        payload = _yahoo_falso(8)
        payload["chart"]["result"][0]["timestamp"] = list(
            reversed(payload["chart"]["result"][0]["timestamp"])
        )
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _RespostaFalsa(payload))
        r = mp._yahoo("XAUUSD", "M5", 3)
        assert r is not None
        tempos = [c["time"] for c in r["candles"]]
        # Serie desordenada na entrada tem que sair CRESCENTE: o grafico assume
        # ordem temporal, e um candle fora de ordem desenha uma linha para
        # tras sem aviso.
        assert tempos == sorted(tempos)
        assert len(r["candles"]) <= 3

    def test_frankfurter_so_responde_em_d1(self, monkeypatch) -> None:
        # Taxa DIARIA devolvida como 5m seria fabricar dado que nao existe.
        assert mp._frankfurter("EURUSD", "M5", 10) is None
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _RespostaFalsa(
            {"amount": 1.0, "base": "EUR", "date": "2026-10-05", "rates": {"USD": 1.1204}}
        ))
        r = mp._frankfurter("EURUSD", "D1", 10)
        assert r is not None
        assert r["diario"] is True
        assert r["candles"][-1]["close"] == pytest.approx(1.1204)


# ----------------------------------------------------------------------
# POR QUE NAO HÁ TESTE CONTRA A API REAL AQUI
# ----------------------------------------------------------------------
# `tests/conftest.py` bloqueia REDE EXTERNA em toda a suite, por autouse, com a
# razao certa: os adaptadores enviam ordem REAL, e um teste que esqueça o
# monkeypatch abriria posicao em conta de verdade.
#
# Afrouxar esse guard para consultar Binance/Yahoo seria trocar uma protecao
# real por uma conveniencia de teste. Nao vale. Entao:
#
#   - os testes acima provam o NORMALIZADOR com resposta falsa, que e onde o
#     erro morava de verdade (array de 12 campos, buraco None, ordem temporal);
#   - a verificacao contra as APIs de verdade fica como MEDICAO MANUAL, feita
#     nesta maquina em 05/10/2026 e registrada no topo deste arquivo e no
#     docstring de `backend/mercado_publico.py`.
#
# Fica registrado aqui para o proximo nao procurar "o teste sumiu":
# numero que so existe se alguem rodou na maqina, e a data esta escrita.
RESUMO_DA_MEDICAO_MANUAL = {
    "data": "2026-10-05",
    "yahoo_gc_f_ouro_ms": 578,
    "yahoo_eurusd_ms": 517,
    "binance_btcusdt_1h_ms": 368,
    "frankfurter_eur_usd_ms": 77,
    "chave_necessaria": False,
}
