"""
  O LOOP DO GUARDIAN E A REGRA QUE NAO TEM POSICAO (06/10/2026)
  ============================================================

  MEDIDO na conta real 391773676: `guardian_rules.json` tinha UMA regra, do
  `ticket 999`, que nao existe — e nao havia NENHUMA regra em posicao real. A
  regra sobreviveu desde 15:32.

  O mecanismo de remocao EXISTE (`_guard_tick_rule` remove a regra quando
  `positions_get` volta vazio). Entao a regra ter sobrevivido mede que o ciclo
  nao rodou ate ela — e estes testes travam as DUAS coisas que podem impedir:

  1. `guardian_tick` remove a regra de posicao que nao existe mais;
  2. `guardian_tick` NAO engole o erro quando o MT5 esta fora, e devolve esse
     erro no estado, para o operador ter como ver que a protecao parou.

  O item 2 e o que media a conta real: com `gw._mt5()` levantando, o `except`
  externo devolvia `count` e nada mais, e as regras ficavam ali para sempre sem
  ninguem dizer que a protecao tinha parado.
"""

from __future__ import annotations

import pytest

from backend import guardian_engine as g


class _Pos:
    def __init__(self, ticket, symbol="btcusd", tipo=0):
        self.ticket = ticket
        self.symbol = symbol
        self.type = tipo
        self.price_open = 85754.35
        self.sl = 85615.69
        self.tp = 85942.76
        self.profit = 0.0
        self.volume = 0.01
        self.time = 1788700000.0


class _Mt5:
    DEAL_ENTRY_IN = 0

    def __init__(self, posicoes):
        self._posicoes = posicoes
        self.trade_action_sl = 1
        self.trade_action_deal = 1

    def positions_get(self, ticket=None):
        return [p for p in self._posicoes if p.ticket == ticket]

    def order_send(self, _request):
        raise AssertionError("este teste nao deve enviar nada")

    def symbol_info_tick(self, _symbol):
        return None


@pytest.fixture(autouse=True)
def limpo(tmp_path, monkeypatch):
    """Regras e estado zerados, e nada gravado no disco real."""
    monkeypatch.setattr(g, "RULES", {})
    monkeypatch.setattr(g, "STATE", {})
    monkeypatch.setattr(g, "_LOCK", __import__("threading").RLock())
    monkeypatch.setattr(g, "_save_rules", lambda: None)
    monkeypatch.setattr(g, "_emergency_stop", lambda: None)
    monkeypatch.setattr(g, "_TICK_INFO", {})
    monkeypatch.setattr(g, "RULES_FILE", tmp_path / "rules.json")
    yield


class TestRegraDePosicaoInexistente:
    def test_a_regra_do_ticket_999_sai(self):
        """A regra medida na conta real: ticket 999, que nao existe."""
        g.RULES[999] = {"ticket": 999, "breakeven": {"trigger": 5, "offset": 0.0,
                                                     "trigger_profit": 0.0}}
        resultado = g.guardian_tick()
        assert 999 not in g.RULES, (
            "regra de posicao inexistente tem que sair: ela nao protege nada e "
            "faz o operador achar que tem protecao ativa"
        )
        assert any(a.get("action") == "auto_remove" for a in resultado["actions"])

    def test_a_posicao_real_mantem_a_regra(self):
        g.RULES[77] = {"ticket": 77, "breakeven": {"trigger": 1.0, "offset": 0.0,
                                                   "trigger_profit": 0.0}}
        monkey = _Mt5([_Pos(77)])
        import backend.mt5_gateway as gw
        original = gw._mt5
        gw._mt5 = lambda: monkey
        try:
            g.guardian_tick()
        finally:
            gw._mt5 = original
        assert 77 in g.RULES, "posicao ABERTA nao pode perder a regra"

    def test_sem_regras_nao_faz_nada(self):
        """Ciclo vazio e ciclo normal, nao um erro escondido."""
        assert g.guardian_tick()["count"] == 0


class TestMt5ForaNaoSome:
    def test_o_erro_do_mt5_aparece_no_estado(self):
        """
        COM O MT5 FORA, o `except` externo devolvia so o `count`: as regras
        ficavam no disco, nenhuma era limpa, e o operador nao tinha como saber
        que a protecao tinha parado. O erro precisa aparecer.
        """
        g.RULES[999] = {"ticket": 999, "breakeven": {"trigger": 5}}
        import backend.mt5_gateway as gw
        original = gw._mt5
        gw._mt5 = lambda: (_ for _ in ()).throw(RuntimeError("terminal desconectado"))
        try:
            resultado = g.guardian_tick()
        finally:
            gw._mt5 = original
        assert resultado["error"], "terminal fora tem que virar erro visivel"
        assert "terminal desconectado" in resultado["error"]

    def test_o_estado_guardado_mostra_o_erro(self):
        """`_TICK_INFO` e o que `/api/guardian/status` le.

        A regra existe de proposito: sem nenhuma regra o ciclo sai antes de
        tocar o MT5, e nao ha o que proteger nem o que reportar.
        """
        g.RULES[77] = {"ticket": 77}
        import backend.mt5_gateway as gw
        original = gw._mt5
        gw._mt5 = lambda: (_ for _ in ()).throw(RuntimeError("terminal desconectado"))
        try:
            g.guardian_tick()
        finally:
            gw._mt5 = original
        assert "terminal desconectado" in str(g._TICK_INFO.get("error"))

    def test_a_parada_de_emergencia_pausa_sem_tocar_nas_regras(self):
        g.RULES[77] = {"ticket": 77}
        original = g._emergency_stop
        g._emergency_stop = lambda: True
        try:
            resultado = g.guardian_tick()
        finally:
            g._emergency_stop = original
        assert resultado["paused"] == "emergency_stop"
        # A regra fica: parada de emergencia nao e motivo para esquecer protecao.
        assert 77 in g.RULES