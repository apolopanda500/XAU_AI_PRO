"""Movimentacoes de saldo no historico: deposito, saque, credito e bonus.

O QUE ESTE ARQUIVO TRAVA
========================
`mt5_gateway._history` reduzia o tipo do deal a dois estados:

    "type": "BUY" if deal_type == DEAL_TYPE_BUY else "SELL",

O MT5 tem DEZ tipos de deal. `BALANCE` (2) e `CREDIT` (3) — deposito, saque,
credito de boas-vindas — caiam no ramo do `else` e voltavam como "SELL". O
frontend entao desenhava uma VENDA de USD 5,62 sem simbolo, que era na
verdade um deposito.

MEDIDO NA CONTA REAL 391773676 (XMGlobal-MT5 14), 05/10/2026, com
`history_deals_get` de 10 anos:

    type=0 BUY     -> 1
    type=1 SELL    -> 1
    type=2 BALANCE -> 2   CD-AST-PIC 265376085 (+5,52)
                              EXP05-AST-PIC 265376085 (+0,10)
    type=3 CREDIT  -> 1   Credit-In-100%-$100-NewClients (+5,62)

Tres das CINCO linhas do historico da conta nao eram operacao. E o `comment`
da corretora ("CD-AST-PIC", "Credit-In-100%-...") e a prova: nenhum desses
nomes aparece numa compra ou numa venda.

O app so LE movimentacao. Nenhuma funcao aqui saca nem transfere: `withdrawals`
continua desligado em todo o codigo (ver AGENTS.md).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend import mt5_gateway as gw  # noqa: E402


def deal(**campos):
    """Um deal do MT5 com o minimo que `_history` le."""
    base = {
        "ticket": 1,
        "order": 1,
        "position_id": 0,
        "symbol": "BTCUSD",
        "type": 0,
        "entry": 0,
        "volume": 0.01,
        "price": 86384.85,
        "profit": 0.0,
        "commission": 0.0,
        "swap": 0.0,
        "fee": 0.0,
        "magic": 2026001,
        "time": 1790000000,
        "comment": "",
    }
    base.update(campos)
    return SimpleNamespace(**base)


class MT5Falso:
    """Duble minimo: as constantes de tipo que `_history` consulta."""

    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    DEAL_TYPE_BALANCE = 2
    DEAL_TYPE_CREDIT = 3
    DEAL_TYPE_CHARGE = 4
    DEAL_TYPE_CORRECTION = 5
    DEAL_TYPE_BONUS = 6
    DEAL_TYPE_COMMISSION = 7
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1


@pytest.fixture()
def mt5(monkeypatch):
    falso = MT5Falso()
    monkeypatch.setattr(gw, "_mt5", lambda: falso)
    return falso


def _history_com(deals, mt5_falso):
    """Roda `_history` sobre uma lista de deals e devolve as linhas."""
    mt5_falso.history_deals_get = lambda *a, **k: deals  # type: ignore[attr-defined]
    try:
        return gw._history(days=3650)["deals"]
    finally:
        del mt5_falso.history_deals_get  # type: ignore[attr-defined]


class TestClassificacaoDeTipo:
    """`type` precisa ser o nome VERDADEIRO, nao "tudo que nao e compra"."""

    def test_compra_e_venda_mantem_o_nome(self, mt5):
        # `time` DECRESCENTE porque `_history` ordena do mais novo para o mais
        # antigo. Com o mesmo `time` nos dois, o sort estavel manteria a ordem
        # de entrada e o teste mediria o duble, nao o codigo.
        linhas = _history_com(
            [deal(ticket=1, type=0, time=1790000200),
             deal(ticket=2, type=1, time=1790000100)],
            mt5,
        )
        assert [l["type"] for l in linhas] == ["BUY", "SELL"]

    def test_deposito_nao_vira_sell(self, mt5):
        linhas = _history_com(
            [deal(ticket=3, type=2, symbol="", volume=0.0, price=0.0,
                  profit=5.52, comment="CD-AST-PIC 265376085")],
            mt5,
        )
        assert linhas[0]["type"] == "BALANCE"
        assert linhas[0]["type"] != "SELL"

    def test_credito_nao_vira_sell(self, mt5):
        linhas = _history_com(
            [deal(ticket=4, type=3, symbol="", volume=0.0, price=0.0,
                  profit=5.62, comment="Credit-In-100%-$100-NewClients")],
            mt5,
        )
        assert linhas[0]["type"] == "CREDIT"
        assert linhas[0]["type"] != "SELL"


class TestCategoriaEMovimentacao:
    """`categoria` separa operacao de movimentacao para o frontend."""

    def test_operacao_e_operacao(self, mt5):
        linhas = _history_com([deal(ticket=5, type=0)], mt5)
        assert linhas[0]["categoria"] == "operacao"
        assert linhas[0]["movimentacao"] == ""

    def test_deposito_e_movimentacao(self, mt5):
        linhas = _history_com(
            [deal(ticket=6, type=2, symbol="", volume=0.0, price=0.0, profit=5.52)],
            mt5,
        )
        assert linhas[0]["categoria"] == "movimentacao"
        assert linhas[0]["movimentacao"] == "Deposito"

    def test_saque_e_movimentacao_negativa(self, mt5):
        # O SENTIDO vem do VALOR: BALANCE cobre deposito E saque.
        linhas = _history_com(
            [deal(ticket=7, type=2, symbol="", volume=0.0, price=0.0, profit=-100.0)],
            mt5,
        )
        assert linhas[0]["movimentacao"] == "Saque"

    def test_credito_positivo_e_credito(self, mt5):
        linhas = _history_com(
            [deal(ticket=8, type=3, symbol="", volume=0.0, price=0.0, profit=5.62)],
            mt5,
        )
        assert linhas[0]["movimentacao"] == "Credito"

    def test_comment_da_corretora_sobe_junto(self, mt5):
        # O comentario e a evidencia de que o registro e da corretora, nao da
        # bolsa. Sem ele, a tela perde a unica pista legivel.
        linhas = _history_com(
            [deal(ticket=9, type=2, symbol="", volume=0.0, price=0.0,
                  profit=5.52, comment="CD-AST-PIC 265376085")],
            mt5,
        )
        assert linhas[0]["comment"] == "CD-AST-PIC 265376085"


class TestPoolRealDaConta:
    """A pool medida na conta 391773676, ponta a ponta."""

    POOL = [
        deal(ticket=260002616, type=1, symbol="BTCUSD", volume=0.01,
             price=86384.85, profit=2.01, comment="[tp 86584.30]"),
        deal(ticket=260002615, type=3, symbol="", volume=0.0, price=0.0,
             profit=5.62, comment="Credit-In-100%-$100-NewClients"),
        deal(ticket=260002613, type=2, symbol="", volume=0.0, price=0.0,
             profit=5.52, comment="CD-AST-PIC 265376085"),
        deal(ticket=260002614, type=2, symbol="", volume=0.0, price=0.0,
             profit=0.10, comment="EXP05-AST-PIC 265376085"),
    ]

    def test_tres_das_quatro_linhas_sao_movimentacao(self, mt5):
        linhas = _history_com(self.POOL, mt5)
        assert len(linhas) == 4
        movimentos = [l for l in linhas if l["categoria"] == "movimentacao"]
        assert len(movimentos) == 3
        assert len([l for l in linhas if l["categoria"] == "operacao"]) == 1

    def test_nenhum_registro_de_saldo_aparece_como_sell(self, mt5):
        for linha in _history_com(self.POOL, mt5):
            if linha["categoria"] == "movimentacao":
                assert linha["type"] != "SELL", linha

    def test_o_credito_de_100_aparece_como_credito(self, mt5):
        credito = next(l for l in _history_com(self.POOL, mt5) if l["ticket"] == 260002615)
        assert credito["movimentacao"] == "Credito"
        assert credito["profit"] == 5.62


class TestNadaDeDinheiroForaDaCorretora:
    """Ler movimentacao nao pode virar uma porta de saque."""

    def test_nao_existe_rota_de_saque_nem_de_transferencia(self):
        fonte = Path(gw.__file__).read_text(encoding="utf-8")
        for proibido in ("/api/withdraw", "/api/transfer", "/api/saque",
                         "/api/transferencia"):
            assert proibido not in fonte, proibido

    def test_movimentacao_apenas_descreve_o_que_ja_aconteceu(self, mt5):
        # `_movimentacao_de` so LE `deal.type` e `deal.profit`: nao chama
        # ordem do MT5 e nao escreve nada. E um rotulo, nao um comando.
        rotulo = gw._movimentacao_de(deal(type=2, profit=-100.0))
        assert rotulo == "Saque"
        assert isinstance(rotulo, str)

