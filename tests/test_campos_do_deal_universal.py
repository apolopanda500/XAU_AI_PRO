# -*- coding: utf-8 -*-
"""O deal que `/api/universal/history` devolve tem os campos que a tela usa?

O DEFEITO MEDIDO NO APP INSTALADO (06/10/2026)
==============================================
A tabela unica do Historico saiu com quatro colunas vazias ao vivo, na conta
391773676 (XMGlobal-MT5 14):

    23:12:25 BTCUSD  —  SELL —  0,0100  86.586,35  +2,01  −0,23%
    18:53:55 —        —  —    —                    +11,14
    18:53:54 —        —  —    —                     +0,10

`Bilhete` vazio, `Tipo` vazio nas movimentacoes, `Comentario` vazio — e o
`Lucro: +13,25` no rodape, que e a soma das DUAS movimentacoes somada ao
resultado da operacao (2,01 + 5,62 + 5,62 = 13,25). Somar entrada de saldo em
lucro e o que o AGENTS.md 10 proibe.

A CAUSA ESTA NO GATEWAY, E NAO NA TELA
=======================================
`_history()` (linha 1702) monta a linha com `ticket`, `type`, `categoria`,
`movimentacao` e `comment` — `_TIPOS_DEAL` traduz o enum e `_movimentacao_de`
classifica. `_universal_history()` (linha 743) recebe essas linhas e monta o
`deals` final REPASSANDO APENAS `id`, `side`, `quantity`, `price`, `profit`...

Cinco campos que a tabela depende NAO atravessam a fronteira. A tela estava
correta e o dado nao chegava — a armadilha do AGENTS.md 5, com o defeito do
lado que PRODUZ e o sintoma do lado que CONSOME.

E o `realizedPnl` e calculado para TODOS os deals, inclusive movimentacao de
saldo. `ehMovimentacao` (frontend) trata `realizedPnl` presente como prova de
que o deal e operacao, entao uma movimentacao com `realizedPnl` preenchido
classifica como OPERACAO — e vai para o Lucro.
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


# ---------------------------------------------------------------------------
# OS DEALS DA CAPTURA DO MT5 (05/10/2026), no formato que `_history` produz.
# ---------------------------------------------------------------------------
LINHAS_MT5 = [
    {
        # `CD-AST-PIC 265376085` — deposito de 5,52. tipo 2 = BALANCE.
        "ticket": 260002613,
        "order": 0,
        "position_id": 0,
        "symbol": "",
        "type": "BALANCE",
        "categoria": "movimentacao",
        "movimentacao": "Deposito",
        "comment": "CD-AST-PIC 265376085",
        "entry": None,
        "volume": 0.0,
        "price": 0.0,
        "profit": 5.52,
        "commission": None,
        "swap": None,
        "fee": None,
        "time": 1788000000,
    },
    {
        # `Credit-In-100%-$100-NewClients` — credito de 5,62. tipo 3 = CREDIT.
        "ticket": 260002615,
        "order": 0,
        "position_id": 0,
        "symbol": "",
        "type": "CREDIT",
        "categoria": "movimentacao",
        "movimentacao": "Credito",
        "comment": "Credit-In-100%-$100-NewClients",
        "entry": None,
        "volume": 0.0,
        "price": 0.0,
        "profit": 5.62,
        "commission": None,
        "swap": None,
        "fee": None,
        "time": 1788000060,
    },
    {
        # A operacao 24503922, FECHAMENTO. tipo 1 = SELL.
        "ticket": 24503922,
        "order": 24503921,
        "position_id": 24503922,
        "symbol": "btcusd",
        "type": "SELL",
        "categoria": "operacao",
        "movimentacao": "",
        "comment": "",
        "entry": "OUT",
        "volume": 0.01,
        "price": 86585.35,
        "profit": 2.01,
        "commission": -0.7,
        "swap": None,
        "fee": None,
        "time": 1788100000,
    },
]


@pytest.fixture
def deals_do_gateway(monkeypatch):
    """Roda a rota INTEIRA de `/api/universal/history` para `mt5`.

    Nao chama `_history` nem monta o deal a mao: o defeito esta no que a rota
    FAZ com a linha, e um teste que monta o deal esperado prova o esperado.
    """
    mod = importlib.import_module("mt5_gateway")

    class FalsoMt5:
        DEAL_ENTRY_IN = 0
        DEAL_ENTRY_OUT = 1

        def history_deals_get(self, *_a, **_k):
            return LINHAS_MT5

        def account_info(self):
            class Info:
                login = 391773676
            return Info()

    monkeypatch.setattr(mod, "_mt5", lambda: FalsoMt5())
    monkeypatch.setattr(mod, "_history", lambda days=30, symbol="": {"deals": LINHAS_MT5, "count": len(LINHAS_MT5), "days": days, "source": "mt5_gateway"})
    resposta = mod._universal_history(broker="mt5", market="other", days=30)
    return {str(d.get("id")): d for d in resposta["deals"]}


class TestCamposQueATabelaPrecisa:
    """Os cinco campos que a tabela unica le, medidos na rota real."""

    def test_o_ticket_sobrevive_a_rota(self, deals_do_gateway):
        # MEDIDO: a coluna `Bilhete` saiu vazia nas tres linhas do app instalado.
        # O operador nao tinha como abrir o registro exato na corretora.
        assert deals_do_gateway["260002613"].get("ticket") == 260002613
        assert deals_do_gateway["24503922"].get("ticket") == 24503922

    def test_o_tipo_sobrevive_a_rota(self, deals_do_gateway):
        # MEDIDO: a coluna `Tipo` saiu vazia nas movimentacoes, e a operacao saiu
        # `SELL` quando a captura do MT5 diz `buy` — o lado do FECHAMENTO.
        assert deals_do_gateway["260002613"].get("type") == "BALANCE"
        assert deals_do_gateway["260002615"].get("type") == "CREDIT"

    def test_a_categoria_sobrevive_a_rota(self, deals_do_gateway):
        # Este e o campo que impede um deposito de virar compra. Sem ele, o
        # frontend cai no RASCUNHO — e o rascunho exige `realizedPnl` ausente,
        # que a rota preenche para todos os deals.
        assert deals_do_gateway["260002613"].get("categoria") == "movimentacao"
        assert deals_do_gateway["24503922"].get("categoria") == "operacao"

    def test_o_comentario_sobrevive_a_rota(self, deals_do_gateway):
        # MEDIDO: a coluna `Comentario` saiu vazia. E o codigo da XM
        # (`CD-AST-PIC 265376085`) que permite ao operador bater o registro com
        # o MT5 — e de onde a forma do deposito e lida.
        assert deals_do_gateway["260002613"].get("comment") == "CD-AST-PIC 265376085"

    def test_o_rotulo_de_movimentacao_sobrevive_a_rota(self, deals_do_gateway):
        assert deals_do_gateway["260002613"].get("movimentacao") == "Deposito"
        assert deals_do_gateway["260002615"].get("movimentacao") == "Credito"


class TestRealizedPnlNaoPodeMarcarMovimentacaoComoOperacao:
    """A prova negativa que explica o `Lucro: +13,25` da tela.

    MEDIDO: o rodape somou 2,01 (operacao) + 5,62 + 5,62 (as duas
    movimentacoes) = 13,25. Somar entrada de saldo em lucro e o que o
    AGENTS.md 10 proibe, e `realizedPnl` preenchido em movimentacao e o que
    faz `ehMovimentacao` (frontend) errar a classificacao: a regra trata o
    campo como prova de execucao de ordem.
    """

    def test_deposito_nao_tem_realized_pnl(self, deals_do_gateway):
        assert deals_do_gateway["260002613"].get("realizedPnl") is None

    def test_credito_nao_tem_realized_pnl(self, deals_do_gateway):
        assert deals_do_gateway["260002615"].get("realizedPnl") is None

    def test_a_operacao_mantem_realized_pnl(self, deals_do_gateway):
        # A operacao PRECISA dele: e o que a tela soma no Lucro.
        # 2,01 de lucro com 0,70 de comissao: no MT5 a comissao ja vem NEGATIVA,
        # entao o resultado e a SOMA direta — 2,01 + (-0,70) = 1,31.
        assert deals_do_gateway["24503922"].get("realizedPnl") == pytest.approx(1.31)

    def test_a_comissao_ENTRA_NEGATIVA_e_nao_soma(self, deals_do_gateway):
        """
        PROVA NEGATIVA do sinal, e o segundo defeito medido nesta correcao.

        A formula era `profit - commission - swap - fee`. Subtrair uma comissao
        que ja vem negativa de −0,70 produz 2,71 — Setenta centavos a MAIS do
        que a operacao rendeu, numa conta de 7,63.

        Este e o tipo de erro que nao aparece em tela nenhuma: o numero sai
        plausivel, so que grande demais, e o operador so descobre comparando com
        a corretora.
        """
        assert deals_do_gateway["24503922"]["commission"] == pytest.approx(-0.7)
        realizado = deals_do_gateway["24503922"]["realizedPnl"]
        assert realizado < deals_do_gateway["24503922"]["profit"], (
            "comissao negativa tem que REDUZIR o resultado; "
            f"{realizado} nao e menor que {deals_do_gateway['24503922']['profit']}"
        )

    def test_swap_creditado_soma_e_swap_devedor_subtrai(self, monkeypatch):
        """
        PROVA NEGATIVA: nenhum dos dois lados pode virar o oposto.

        `abs()` "corrigiria" a comissao, mas transformaria swap CREDITADO
        (positivo, o MT5 paga) em perda. Os dois sentidos tem de valer, porque
        o swap muda de sinal conforme os juros.

        MEDIDO: este teste recebia o fixture `deals_do_gateway` so por convencao
        e por isso media o DEAL ERRADO. O `_mt5` do fixture continuava valendo
        (o `monkeypatch` dele reverte no fim do fixture, mas `_universal_history`
        e chamado aqui dentro de novo) e a rota devolvia o `BALANCE` de 5,52 em
        vez da operacao. `realizedPnl` de movimentacao e `None` — que e o
        comportamento correto do gateway — e o teste quebrava por causa disso.

        Nao depender de fixture que mexe no modulo: este teste monta o proprio.
        """
        mod = importlib.import_module("mt5_gateway")

        def rodar(swap: float) -> float:
            # MEDIDO: este teste media `linhas` SEM o `swap` que eu passava. O
            # `FalsoMt5.history_deals_get` — que e quem construiria a linha com o
            # swap — nunca era chamado, porque `_history` estava mockado. O swap
            # nao chegava, e o teste media a comissao de novo.
            #
            # A linha entra pelo MESMO caminho de producao que o resto do
            # arquivo: `_history` sobre um deal, e so `_universal_history`
            # mockado nada. Sem isso, o teste mede um fixture, nao a rota.
            linha = dict(LINHAS_MT5[-1], swap=swap, fee=0.0, commission=-0.7, type=1)

            # `_history` le o deal por ATRIBUTO (`getattr(deal, "type")`), e o
            # MT5 devolve um objeto. Um dict aqui daria `type = -1` em todo
            # deal e a linha sairia como `TIPO_-1` — e o `realizedPnl` viraria
            # `None`. O duble tem que ter a FORMA do MT5, nao a forma do JSON
            # que a rota devolve.
            class DealMt5:
                def __init__(self, dados: dict) -> None:
                    self.__dict__.update(dados)

            class FalsoMt5:
                DEAL_ENTRY_IN = 0
                DEAL_ENTRY_OUT = 1

                def history_deals_get(self, *_a, **_k):
                    return [DealMt5(linha)]

                def account_info(self):
                    class Info:
                        login = 391773676
                    return Info()

            monkeypatch.setattr(mod, "_mt5", lambda: FalsoMt5())
            resposta = mod._universal_history(broker="mt5", market="other", days=30)
            return float(resposta["deals"][0]["realizedPnl"])

        # A comissao de −0,70 da fixture entra nos dois casos:
        # Swap devedor (−1,25): 2,01 − 0,70 − 1,25 = 0,06
        assert rodar(-1.25) == pytest.approx(0.06)
        # Swap creditado (+1,25): 2,01 − 0,70 + 1,25 = 2,56
        assert rodar(1.25) == pytest.approx(2.56)

    def test_a_soma_do_lucro_nao_anexe_movimentacao(self, deals_do_gateway):
        # Reproduz a conta do rodape com a regra do `resumoMt5`: so `categoria`
        # "operacao" entra no Lucro.
        def eh_movimentacao(deal: dict) -> bool:
            if deal.get("categoria"):
                return deal["categoria"] == "movimentacao"
            if deal.get("realizedPnl") is not None:
                return False
            return not deal.get("symbol") and not deal.get("quantity") and not deal.get("price")

        lucro = sum(
            float(d.get("realizedPnl") or d.get("profit") or 0.0)
            for d in deals_do_gateway.values()
            if not eh_movimentacao(d)
        )
        # O que a tela mostrou foi 13,25. O correto e o resultado da operacao.
        assert lucro == pytest.approx(1.31)
        assert lucro != pytest.approx(13.25)


