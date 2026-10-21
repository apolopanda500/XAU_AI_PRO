"""SL E TP EM DINHEIRO NO MOTOR — PROPRIEDADES E CASO MEDIDO (05/10/2026)
==========================================================================

O pedido do dono: o VALOR e do operador, o preco se move, e o nivel acompanha
para que o dinheiro continue sendo o mesmo numero.

O teste que motivou: a tela calculava `preco * volume * distancia`. Com BTCUSD a
85.865,35, volume 0,01 e distancia 8,45, devolvia 7.255,62 USD quando o risco
real e 0,08 — exagero de 85.865x, que era exatamente o preco.

Estes testes existem para o numero do preco nunca mais aparecer.
"""

from __future__ import annotations

import pytest

from backend.alvo_risco import (
    RiscoInvalido,
    SEM_CONTRATO,
    VALOR_INVALIDO,
    contrato_de,
    nivel_do_valor,
    niveis_do_valor,
    risco_real,
    valor_do_nivel,
)

CRIPTO = 1.0
FOREX = 100_000.0


class TestContaDoValor:
    def test_prova_negativa_do_defeito_medido(self):
        # BTCUSD: 8,45 de distancia x 0,01 de volume x 1 de contrato.
        v = valor_do_nivel(85_865.35, 85_865.35 - 8.45, 0.01, CRIPTO)
        assert v == pytest.approx(0.0845, abs=1e-9)
        # A conta antiga devolvia 7.255,62. Se este numero voltar, o bug voltou.
        assert v != pytest.approx(7255.6221, abs=0.01)

    def test_o_valor_nao_depende_do_preco(self):
        d = 8.45
        a = valor_do_nivel(85_865.35, 85_865.35 - d, 0.01, CRIPTO)
        b = valor_do_nivel(1_000.0, 1_000.0 - d, 0.01, CRIPTO)
        # Mesma distancia, mesmo dinheiro. Era o preco que multiplicava.
        assert a == pytest.approx(b, abs=1e-12)

    def test_forex_multiplica_pelo_contrato(self):
        # 0,0035 x 0,01 x 100.000 = 3,50 USD.
        assert valor_do_nivel(1.085, 1.0815, 0.01, FOREX) == pytest.approx(3.5)

    def test_o_valor_e_absoluto(self):
        assert valor_do_nivel(100, 95, 1, CRIPTO) == pytest.approx(
            valor_do_nivel(100, 105, 1, CRIPTO)
        )


class TestNivelDoValor:
    def test_o_papel_decide_a_direcao_em_compra(self):
        # Stop de compra fica ABAIXO; alvo de compra fica ACIMA.
        assert nivel_do_valor(100, 5, 1, "buy", CRIPTO, papel="stop") == pytest.approx(95)
        assert nivel_do_valor(100, 5, 1, "buy", CRIPTO, papel="alvo") == pytest.approx(105)

    def test_o_papel_decide_a_direcao_em_venda(self):
        # Venda inverte: stop acima, alvo abaixo.
        assert nivel_do_valor(100, 5, 1, "sell", CRIPTO, papel="stop") == pytest.approx(105)
        assert nivel_do_valor(100, 5, 1, "sell", CRIPTO, papel="alvo") == pytest.approx(95)

    def test_ida_e_volta_preserva_o_valor(self):
        """
        ESTE e o teste do que o dono pediu: o valor e fixo, o nivel e derivado.
        Se o dinheiro nao volta, o operador escreveu um numero que o motor nao
        cumpre — pior que nao ter o campo.
        """
        casos = [
            (85_865.35, 2.0, 0.01, CRIPTO),
            (85_865.35, 0.0845, 0.01, CRIPTO),
            (1.085, 3.5, 0.01, FOREX),
            (2_400.5, 350.0, 0.02, FOREX),
        ]
        for entrada, valor, volume, contrato in casos:
            for lado in ("buy", "sell"):
                nivel = nivel_do_valor(entrada, valor, volume, lado, contrato, papel="stop")
                assert risco_real(entrada, nivel, volume, contrato) == pytest.approx(
                    valor, rel=1e-9
                )

    def test_o_nivel_acompanha_a_entrada_e_mantem_o_valor(self):
        """
        O preco andou de 100 para 120: o nivel acompanha, e o dinheiro e o
        mesmo. E o que "mantendo o valor predeterminado" quer dizer.
        """
        v1 = nivel_do_valor(100, 5, 1, "buy", CRIPTO, papel="alvo")
        v2 = nivel_do_valor(120, 5, 1, "buy", CRIPTO, papel="alvo")
        assert v1 == pytest.approx(105)
        assert v2 == pytest.approx(125)
        assert risco_real(120, v2, 1, CRIPTO) == pytest.approx(5)

    def test_PROVA_NEGATIVA_stop_nunca_fica_do_lado_contrario(self):
        """
        O bug que a geometria pegou: a primeira versao usava SO o lado e
        devolvia o stop ACIMA da entrada numa compra (105 em vez de 95). Um stop
        acima do preco de uma compra e executado no primeiro tick.

        Este teste existe para o stop nao voltar para o lado errado, nos dois
        lados da posicao.
        """
        for lado, stop_esperado in (("buy", 95.0), ("sell", 105.0)):
            stop = nivel_do_valor(100, 5, 1, lado, CRIPTO, papel="stop")
            assert stop == pytest.approx(stop_esperado)
            assert (stop < 100) if lado == "buy" else (stop > 100)

    def test_papel_invalido_recusa(self):
        with pytest.raises(RiscoInvalido):
            nivel_do_valor(100, 5, 1, "buy", CRIPTO, papel="meio")  # type: ignore[arg-type]


    def test_geometria_da_posicao(self):
        """
        PROVA NEGATIVA: o lado decide para onde cada nivel vai.

        Um stop ACIMA do preco em uma compra e executado no primeiro tick. Esta
        e a razao de `niveis_do_valor` precisar do lado, e de a tela nao poder
        escolher um nivel so — ela nao sabe o lado.
        """
        compra = niveis_do_valor(100, 5, 5, 1.0, "buy", CRIPTO)
        assert compra["sl_preco"] < 100 < compra["tp_preco"]
        venda = niveis_do_valor(100, 5, 5, 1.0, "sell", CRIPTO)
        assert venda["sl_preco"] > 100 > venda["tp_preco"]


class TestRecusaComMotivo:
    def test_sem_contrato_recusa_e_diz_qual_e_o_motivo(self):
        # Numero de risco inventado e o pior defeito de uma tela de operacao.
        with pytest.raises(RiscoInvalido) as e:
            nivel_do_valor(85_865.35, 2.0, 0.01, "buy", None)
        assert str(e.value) == SEM_CONTRATO

    def test_contrato_ausente_nao_vira_um(self):
        # Assumir contrato 1 seria assumir que todo ativo e crypto: em forex o
        # numero sairia 100.000x errado, em silencio.
        assert contrato_de(None) is None
        assert contrato_de({}) is None
        assert contrato_de({"contract_size": 0}) is None
        assert contrato_de({"contract_size": -1}) is None
        assert contrato_de({"contract_size": 1}) == 1.0

    def test_zero_e_negativo_recusam(self):
        with pytest.raises(RiscoInvalido):
            nivel_do_valor(100, 0, 1, "buy", CRIPTO)
        with pytest.raises(RiscoInvalido) as e:
            nivel_do_valor(100, -5, 1, "buy", CRIPTO)
        assert str(e.value) == VALOR_INVALIDO

    def test_volume_zero_nao_divide_por_zero(self):
        with pytest.raises(RiscoInvalido):
            nivel_do_valor(100, 5, 0, "buy", CRIPTO)

    def test_entrada_invalida_recusa(self):
        with pytest.raises(RiscoInvalido):
            nivel_do_valor(0, 5, 1, "buy", CRIPTO)


class TestCamposAusentes:
    def test_campo_vazio_vem_none_e_nao_inventado(self):
        # Um nivel para campo vazio manda ordem com protecao que o operador nao
        # pediu. `None` deixa a decisao visivel.
        r = niveis_do_valor(100, None, None, 1.0, "buy", CRIPTO)
        assert r == {"sl_preco": None, "tp_preco": None}

    def test_so_o_sl_pedido(self):
        r = niveis_do_valor(100, 5, None, 1.0, "buy", CRIPTO)
        # Stop de COMPRA fica ABAIXO da entrada. A primeira versao deste teste
        # esperava 105 — que e o stop do lado errado, executado no primeiro tick.
        assert r["sl_preco"] == pytest.approx(95)
        assert r["tp_preco"] is None