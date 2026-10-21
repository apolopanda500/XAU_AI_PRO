# -*- coding: utf-8 -*-
"""O `lado` do deal: o MT5 devolve inteiro, as exchanges devolvem texto.

O DEFEITO
=========
A tabela de operacoes do Historico mostrava `0` e `1` na coluna "Operacao", no
lugar de compra e venda, e a cor da linha caia no ramo vazio.

Motivo: o MT5 devolve `type` como INTEIRO (0 = compra, 1 = venda) e as
exchanges devolvem `side` como TEXTO ("BUY"/"SELL"). O gateway repassava o valor
cru, entao o mesmo campo tinha dois tipos no mesmo payload dependendo da
corretora — e o frontend so lidava com texto.

O QUE ESTE ARQUIVO PROVA
=======================
1. `_lado_de_deal` traduz `0`/`1` para `BUY`/`SELL`.
2. Texto que JÁ vem pronto passa direto — outra rota pode mandar o rotulo pronto.
3. Valor desconhecido vira `None`, e NAO vira `BUY`.

O ponto 3 e a prova negativa. Um `else` que devolvesse "BUY" para qualquer coisa
nao desconhecida faria a tela mostrar COMPRA para uma movimentacao de saldo, e
essa linha apareceria verde. Falso verde em historico e pior que celula vazia.
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


@pytest.fixture(scope="module")
def gateway():
    """Importa o gateway e devolve SO a funcao testada.

    A funcao e importada, nunca reimplementada: um teste que copia o codigo
    prova que o codigo esta certo mesmo quando esta errado.
    """
    mod = importlib.import_module("mt5_gateway")
    return mod._lado_de_deal


class TestLadoDeDeal:
    def test_mt5_inteiro_vira_texto(self, gateway):
        # 0 = compra, 1 = venda. E o que o MT5 manda em `type`.
        assert gateway(0) == "BUY"
        assert gateway(1) == "SELL"

    def test_texto_ja_pronto_passa_direto(self, gateway):
        # As exchanges mandam "BUY"/"SELL", as vezes minusculo. Traduzir de novo
        # seria redundante; devolver None aqui apagaria a operacao.
        assert gateway("BUY") == "BUY"
        assert gateway("sell") == "SELL"
        assert gateway("  buy  ") == "BUY"

    def test_valor_desconhecido_vira_none(self, gateway):
        # PROVA NEGATIVA. Este e o teste que segura a promessa.
        #
        # Aqui so entram valores que nao sao TEXTO. Texto desconhecido NAO e
        # recusado, e a distincao importa: o MT5 tambem grava entrada e saida de
        # posicao como "IN"/"OUT", e o frontend precisa mostrar esses rotulos. A
        # funcao normaliza, nao valida — o `.upper()` e a conversao do inteiro
        # sao o contrato dela.
        for valor in (None, "", "   ", 2, -1, 99, 1.5, 0.0, [], {}, object()):
            assert gateway(valor) is None, f"{valor!r} nao deveria virar lado"

    def test_texto_desconhecido_passa_direto(self, gateway):
        # Contrapartida do teste acima, para deixar o contrato explicito: "IN",
        # "OUT" e qualquer rotulo de entrada/saida chegam intactos e maiusculos.
        assert gateway("IN") == "IN"
        assert gateway("out") == "OUT"

    def test_booleano_nao_e_o_inteiro_que_se_parece(self, gateway):
        # `True == 1` em Python, entao um `tipo in _LADO_DE_DEAL` sem cuidado
        # traduziria `True` em "SELL". E verdade: True e o indice 1 do dicionario.
        # Traduzir um booleano seria inventar uma operacao de venda.
        assert gateway(True) is None
        assert gateway(False) is None


class TestLadoNaRotaDoHistorico:
    """O `_lado_de_deal` esta LIGADO na rota que produz os deals?"""

    def test_universal_history_usa_o_tradutor(self):
        fonte = (BACKEND / "mt5_gateway.py").read_text(encoding="utf-8")
        # A funcao existir nao basta: ela tem de ser CHAMADA dentro de
        # `_universal_history`, que e o que monta os deals da tabela.
        corpo = fonte.split("def _universal_history", 1)[1]
        # Corta na proxima def de nivel superior para nao pegar outras rotas.
        corte = corpo.find("\ndef ", 1)
        if corte > 0:
            corpo = corpo[:corte]
        assert "_lado_de_deal(" in corpo, (
            "_universal_history nao chama _lado_de_deal: a tabela continuaria "
            "mostrando o inteiro cru do MT5"
        )