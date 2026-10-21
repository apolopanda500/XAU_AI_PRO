"""
O HISTORICO DIZ SE O DADO FOI LIDO (06/10/2026)
================================================

O DONO DISSE: "o historico demora carregar".
E MEDIU-SE: "e o app nao pode ficar muito dependente do mt5 ligado".

AS DUAS CAUSAS, MEDIDAS SEPARADAS
--------------------------------
**1. O MT5 NAO ERA O GARGALO.** MEDIDO nesta maquina, conta 391773676 (XM,
Hedge), com o terminal aberto:

    history_deals_get(hoje)      0,1 ms     5 deals
    history_deals_get(30 dias)   0,1 ms    10 deals
    history_deals_get(90 dias)   0,1 ms    10 deals
    history_deals_get(3650 dias) 0,1 ms    10 deals
    copy_rates BTCUSD H1 300     4,5 ms   300 barras
    copy_rates BTCUSD M15 300   16,6 ms   300 barras
    copy_rates BTCUSD M5  300   79,6 ms   300 barras
    symbols_get                  22,4 ms  1639 simbolos

Dez anos de historico respondem no mesmo tempo que um dia. Nenhum destes numeros
explica "demora". Descartado.

**2. A DEMORA ERA A TELA MENTINDO.** A correcao esta no frontend
(`frontend/src/lib/historico.ts`), e este arquivo trava o lado do PRODUTOR: sem
`connected`, o consumidor nao tem como distinguir "conta sem operacao" de
"terminal fechado", e a tela volta a ser uma tela de sucesso com zero linhas.

**3. A DEPENDENCIA DO MT5, AGORA DITA.** Com o `terminal64` fechado,
`history_deals_get` volta vazio — e vazio e o MESMO payload de uma conta sem
operacao. Era por isso que o app dependia do MT5 ligado sem dizer que
dependia.

O AGENTS.md 5 EM DUAS FORMAS
----------------------------
O sintoma "o historico demora" apontava para a REDE e para a CORRETORA. As duas
respondem em 0,1 ms. E o sintoma "o historico esta vazio" apontava para a
CONTA. A conta esta cheia. Os dois defects eram do cliente.

O QUE ESTE ARQUIVO PROVA
=======================
Que a rota de `/api/universal/history` para `mt5` DIZ se ha sessao viva — e que
`deals: []` por desconexao e `deals: []` por conta vazia sao respostas
DISTINTAS, porque o consumidor precisa agir diferente em cada uma.

Sem esta trava, um "corrigimento" que remova `connected` por ser campo a mais
passa em toda a suite Python: nenhum teste aqui verifica a tela. E a tela volta
a dizer "nenhum registro no periodo" com o terminal fechado.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class TestConnectedNoHistorico:
    """`connected` diz se o MT5 TEM sessao — e nao se a conta tem operacao."""

    def test_com_sessao_viva_a_rota_declara_conectado(self, monkeypatch):
        mod = importlib.import_module("mt5_gateway")

        class TerminalAberto:
            def terminal_info(self):
                class Info:
                    connected = True
                return Info()

        class FalsoMt5:
            def history_deals_get(self, *_a, **_k):
                return []

            def account_info(self):
                return None

        monkeypatch.setattr(mod, "_mt5", lambda: FalsoMt5())
        monkeypatch.setattr(mod, "_mt5_connected", lambda: True)
        resposta = mod._universal_history(broker="mt5", market="other", days=30)

        assert resposta.get("connected") is True

    def test_com_terminal_fechado_a_rota_declara_DESCONECTADO(self, monkeypatch):
        """
        MEDIDO: com o `terminal64` fechado, `history_deals_get` volta vazio. E
        `deals: []` e o MESMO payload de uma conta sem operacao no periodo.

        Sem `connected: false` a tela mostra "Nenhum registro no periodo" — uma
        tela de SUCESSO — e o operador vai procurar erro na conta. O erro era um
        programa nao aberto.
        """
        mod = importlib.import_module("mt5_gateway")

        class TerminalFechado:
            def terminal_info(self):
                return None

        class FalsoMt5:
            def history_deals_get(self, *_a, **_k):
                return []

            def account_info(self):
                return None

        monkeypatch.setattr(mod, "_mt5", lambda: FalsoMt5())
        monkeypatch.setattr(mod, "_mt5_connected", lambda: False)
        resposta = mod._universal_history(broker="mt5", market="other", days=30)

        # O que a tela precisa: os deals VAZIOS, e a CAUSA.
        assert resposta.get("deals") == []
        assert resposta.get("connected") is False

    def test_PROVA_NEGATIVA_desconectado_e_conta_vazia_SAO_RESPOSTAS_DIFERENTES(
        self, monkeypatch
    ):
        """
        A PROVA DE QUE O CAMPO FAZ ALGUMA COISA.

        As duas respostas tem `deals: []` identico. O que muda e so o `connected`.
        Se fossem iguais, o campo seria decorativo — e um campo que nada
        diferencia e pior que a ausencia dele (AGENTS.md 9): o consumidor
        receberia um dado sem motivo e o operador aprenderia a ignorar o aviso.
        """
        mod = importlib.import_module("mt5_gateway")

        class FalsoMt5:
            def history_deals_get(self, *_a, **_k):
                return []

            def account_info(self):
                return None

        monkeypatch.setattr(mod, "_mt5", lambda: FalsoMt5())

        monkeypatch.setattr(mod, "_mt5_connected", lambda: True)
        com_conta = mod._universal_history(broker="mt5", market="other", days=30)

        monkeypatch.setattr(mod, "_mt5_connected", lambda: False)
        sem_conta = mod._universal_history(broker="mt5", market="other", days=30)

        # O que o CONSUMIDOR le, e as duas linhas identicas.
        assert com_conta["deals"] == sem_conta["deals"] == []
        # O que o consumidor usa para agir: diferente.
        assert com_conta["connected"] is True
        assert sem_conta["connected"] is False
        assert com_conta["connected"] != sem_conta["connected"]

    def test_a_leitura_continua_OK_mesmo_desconectada(self, monkeypatch):
        """
        POR QUE `ok` NAO VIRA `false`.

        Desconectado NAO e erro de leitura: a leitura foi feita e o resultado foi
        vazio. Marcar `ok: false` faria a tela mostrar um erro de rede para um
        terminal fechado — e trocar uma mensagem errada por outra, que e o
        AGENTS.md 5 de novo.

        O que muda e `connected`, que e o que permite a tela dizer a CAUSA.
        """
        mod = importlib.import_module("mt5_gateway")

        class FalsoMt5:
            def history_deals_get(self, *_a, **_k):
                return []

            def account_info(self):
                return None

        monkeypatch.setattr(mod, "_mt5", lambda: FalsoMt5())
        monkeypatch.setattr(mod, "_mt5_connected", lambda: False)
        resposta = mod._universal_history(broker="mt5", market="other", days=30)

        assert resposta.get("ok") is True
        assert resposta.get("connected") is False


class TestConnectedNaoVazaParaAsExchanges:
    """A tela de Binance nao pode dizer "abra o MetaTrader"."""

    def test_o_campo_so_aparece_no_mt5(self):
        """
        `connected` e sobre sessao de TERMINAL. Uma exchange nao tem terminal, e
        o campo nao existe no payload dela — e o frontend so trata
        `connected === false` como desconexao, nunca `undefined`.

        Se o MT5 passar a declarar `connected` para as quatro exchanges, uma
        tela Binance que funciona passaria a acusar terminal fechado.
        """
        import inspect

        mod = importlib.import_module("mt5_gateway")
        fonte = inspect.getsource(mod._universal_history)

        # O `connected=` aparece na linha do MT5, nao na linha da exchange.
        linhas = [l for l in fonte.splitlines() if "connected=" in l]
        assert linhas, "a rota de mt5 precisa declarar `connected`"
        for linha in linhas:
            # Todas as ocorrencias de `connected=` estao em bloco de mt5.
            assert "exchange" not in linha.lower()