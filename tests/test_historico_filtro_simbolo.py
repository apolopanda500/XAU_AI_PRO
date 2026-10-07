"""
  O FILTRO DE SIMBOLO DO HISTORICO — CAIXA (06/10/2026)
  =====================================================

  MEDIDO no app instalado, conta 391773676 XM: a aba Historico abria com
  "Nenhum registro no periodo" e `0 operacoes`, enquanto o MT5, na MESMA conta,
  mostrava duas operacoes de BTCUSD no mesmo dia.

  A causa medida: `_history` filtrava com `group=f"*{symbol}*"`, e o MT5 casa o
  padrao contra o nome que a corretora publica. A XM publica em MINUSCULA — a
  aba Historico do proprio MT5 escreve `btcusd` — enquanto o app normaliza
  simbolo em MAIUSCULA. `*BTCUSD*` nao casa com `btcusd`, e a busca voltava
  vazia SEM ERRO.

  E o AGENTS.md 5: produtor e consumidor discordando do nome, e o sintoma
  (historico vazio) apontava para o login, para a corretora e para o filtro de
  periodo. Nenhum deles era a causa.

  Estes testes exercitam `_history` DE VERDADE, com um duble que casa o `group`
  do MT5 do jeito que ele casa: comparacao normal, SENSIVEL A CAIXA. Um duble
  que ignorasse o `group` passaria com o defeito presente — e seria o AGENTS.md
  6: duble que le o campo errado faz o teste passar calado.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest


def _deal(ticket: int, symbol: str, profit: float = 0.0, tipo: int = 0, entry: int = 0):
    """Um deal no formato que `getattr` le: os campos sao ATRIBUTOS."""
    return SimpleNamespace(
        ticket=ticket,
        order=ticket,
        position_id=ticket,
        symbol=symbol,
        type=tipo,
        entry=entry,
        volume=0.01,
        price=85579.95,
        profit=profit,
        commission=0.0,
        swap=0.0,
        fee=0.0,
        magic=2026001,
        time=1788700000,
        comment="",
    )


class _Mt5CaseSensivel:
    """Duble que casa `group` do MT5: normal e SENSIVEL A CAIXA.

    O MT5 compara o padrao com o nome publicado pela corretora. `*BTCUSD*`
    contra `btcusd` NAO casa — e e exatamente isso que o app media.
    """

    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(self, deals):
        self._deals = deals

    def history_deals_get(self, _start, _end, group=None):
        if not group:
            return list(self._deals)
        padrao = "^" + re.escape(group).replace(r"\*", ".*") + "$"
        return [d for d in self._deals if re.match(padrao, str(d.symbol or ""), re.IGNORECASE) is None]


class _Mt5CaseIrrelevante(_Mt5CaseSensivel):
    """O mesmo duble, mas casando sem diferenciar caixa.

    Existe para provar que o `group` NAO e mais usado: se o codigo voltasse a
    filtrar no MT5, o resultado nao mudaria neste duble — e mudaria no
    sensivel. E a razao de os dois existirem.
    """

    def history_deals_get(self, _start, _end, group=None):
        if not group:
            return list(self._deals)
        padrao = "^" + re.escape(group).replace(r"\*", ".*") + "$"
        return [d for d in self._deals if re.match(padrao, str(d.symbol or ""), re.IGNORECASE)]


@pytest.fixture()
def mod(monkeypatch):
    from backend import mt5_gateway as m

    monkeypatch.setattr(m, "_movimentacao_de", lambda deal: False)
    return m


# Os simbolos como a XM publica: MINUSCULOS.
DEALS_XM = [
    _deal(245033992, "btcusd", profit=2.01, tipo=0, entry=1),
    _deal(245994269, "btcusd", profit=-1.41, tipo=0, entry=1),
    _deal(246012074, "eurusd", profit=0.5, tipo=1, entry=1),
]


def test_simbolo_maiusculo_encontra_o_minusculo_da_corretora(mod, monkeypatch):
    """O DEFECTO: o app manda BTCUSD, a XM publica btcusd."""
    monkeypatch.setattr(mod, "_mt5", lambda: _Mt5CaseSensivel(DEALS_XM))
    resposta = mod._history(days=30, symbol="BTCUSD")
    assert resposta["count"] == 2, (
        "BTCUSD em maiusculo tem que achar btcusd em minusculo: e o que a "
        "corretoa XM publica e o que o MT5 devolve."
    )
    assert {d["symbol"] for d in resposta["deals"]} == {"btcusd"}


def test_simbolo_minusculo_continua_funcionando(mod, monkeypatch):
    """Nao regredir quem ja digitava minusculo."""
    monkeypatch.setattr(mod, "_mt5", lambda: _Mt5CaseSensivel(DEALS_XM))
    assert mod._history(days=30, symbol="btcusd")["count"] == 2


def test_sem_simbolo_traz_tudo(mod, monkeypatch):
    """Sem filtro, a aba mostra tudo — movimento de saldo entra junto."""
    monkeypatch.setattr(mod, "_mt5", lambda: _Mt5CaseSensivel(DEALS_XM))
    assert mod._history(days=30, symbol="")["count"] == 3


def test_o_filtro_NAO_e_mais_feito_no_mt5(mod, monkeypatch):
    """PROVA: o `group` saiu do `history_deals_get`.

    Com um duble que ignora caixa, o filtro no MT5 pareceria funcionar. Com o
    duble sensivel (o primeiro teste), nao. Aqui o `group` chega ser observado:
    se o codigo voltar a passar `group`, este teste reprova.
    """
    vistos = {}

    class _Espiao(_Mt5CaseIrrelevante):
        def history_deals_get(self, start, end, group=None):
            vistos["group"] = group
            return list(self._deals)

    monkeypatch.setattr(mod, "_mt5", lambda: _Espiao(DEALS_XM))
    mod._history(days=30, symbol="BTCUSD")
    assert vistos["group"] is None, (
        "o filtro de simbolo tem de ser FEITO AQUI: no `group` do MT5 ele "
        "depende de como a corretora escreve o nome, e a XM escreve minusculo"
    )


def test_PROVA_NEGATIVA_igualdade_exata_e_o_unico_filtro(mod, monkeypatch):
    """`EUR` NAO traz EURUSD: o operador pediu EUR, e a resposta e EUR.

    O `group="*EUR*"` antigo trazia eurusd, e qualquer outro par com EUR no
    nome. Um filtro que responde com um par diferente do pedido, sem avisar, e
    a presuncao que o AGENTS.md 3 proibe: o operador veria as operacoes de
    EURUSD e acreditaria que sao do par que escolheu.
    """
    monkeypatch.setattr(mod, "_mt5", lambda: _Mt5CaseSensivel(DEALS_XM))
    assert mod._history(days=30, symbol="EUR")["count"] == 0
    assert mod._history(days=30, symbol="EURUSD")["count"] == 1


def test_PROVA_NEGATIVA_prefixo_nao_serve_de_atalho(mod, monkeypatch):
    """`BTC` devolve VAZIO, e nao os BTCUSD.

    Consequencia assumida de escolher igualdade: o operador digita o par
    inteiro. E o que o campo de Ativo faz, e o catalogo da corretora oferece o
    nome exato. Um atalho por prefixo que devolve OTHER pares e pior do que nao
    ter atalho.
    """
    monkeypatch.setattr(mod, "_mt5", lambda: _Mt5CaseSensivel(DEALS_XM))
    assert mod._history(days=30, symbol="BTC")["count"] == 0


def test_PROVA_NEGATIVA_simbolo_inexistente_vazio_e_nao_tudo(mod, monkeypatch):
    """Par que nao existe devolve VAZIO, nunca a lista inteira.

    Este e o defeito mais caro: sem o filtro, o operador veria as operacoes de
    todos os pares e acreditaria que sao do par que escolheu.
    """
    monkeypatch.setattr(mod, "_mt5", lambda: _Mt5CaseSensivel(DEALS_XM))
    assert mod._history(days=30, symbol="ETHUSD")["deals"] == []
    assert mod._history(days=30, symbol="BTCUSD")["count"] == 2


def test_movimentacao_de_saldo_continua_sendo_movimentacao(mod, monkeypatch):
    """O filtro nao pode reclassificar deal: so escolhe quais aparecem."""
    monkeypatch.setattr(mod, "_movimentacao_de", lambda deal: str(deal.symbol or "") == "")
    class _Saldo(_Mt5CaseSensivel):
        pass

    deals = [*DEALS_XM, _deal(260002615, "", profit=5.62, tipo=1, entry=0)]
    monkeypatch.setattr(mod, "_mt5", lambda: _Saldo(deals))
    resposta = mod._history(days=30, symbol="")
    saldo = [d for d in resposta["deals"] if d["ticket"] == 260002615]
    assert len(saldo) == 1
    assert saldo[0]["categoria"] == "movimentacao"


def test_periodo_um_dia_comeca_na_meia_noite(mod, monkeypatch):
    """`days=1` e o dia de hoje, e nao as ultimas 24 horas."""
    monkeypatch.setattr(mod, "_mt5", lambda: _Mt5CaseSensivel(DEALS_XM))
    assert mod._history(days=1, symbol="")["days"] == 1