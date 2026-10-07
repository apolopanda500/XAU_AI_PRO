# -*- coding: utf-8 -*-
"""Escolher o modelo tem que TROCAR o periodo. Medido, nao presumido.

O DEFEITO (05/10/2026)
======================
O dono reportou: "quando seleciona modelos 15m nao mudar a selecao em cima
permanece 1h". E depois: "4h tambem sempre permanece 1h".

CAUSA RAIZ, MEDIDA
==================
Em `AutoEngine.configurar()`, a validacao dos limites de risco (`valido()`)
rodava ANTES de gravar `simbolo` e `timeframe`, e devolvia `False` enquanto
lote, SL e TP nao estivessem preenchidos — que e o estado normal antes de o
operador mexer em qualquer coisa.

Ou seja: clicar em `BTCUSD_M15` ou `EURUSD_H4` na linha da lista de modelos
chamava `/api/auto/config`, o backend respondia `{"ok": false, "error": "defina
lote, stop loss e take profit..."}` e **saiia antes de gravar**. O par ate mudava
(no estado do frontend), o periodo NO MOTOR nao, e a tela mostrava 1H para
sempre. O frontend ainda ignorava a resposta — entao nada era escrito em lugar
nenhum, e o operador achava que a lista de modelos nao funcionava.

A CORRECAO
==========
OBSERVAR e OPERAR sao dois atos:

  - escolher par e periodo e APONTAR A LENTE: nao arrisca dinheiro, e por isso
    nao pode depender de risco preenchido;
  - LIGAR o motor continua exigindo lote, SL e TP, com o mesmo motivo e a mesma
    mensagem de sempre.

E a resposta passou a dizer o que foi aplicado, para a tela nao parecer muda
nenhuma.

ESTE ARQUIVO PROVA OS DOIS ATOS, E O CASO QUE DEVERIA REPROVAR.
"""
from __future__ import annotations

import pytest

from backend.auto_engine import MotorAuto


@pytest.fixture()
def motor() -> MotorAuto:
    return MotorAuto()


class TestEscolherModeloTrocaPeriodo:
    def test_periodo_muda_mesmo_sem_risco_preenchido(self, motor: MotorAuto) -> None:
        # Este e o teste que trava a correcao. Sem lote/SL/TP, que e o estado
        # inicial de qualquer motor, o periodo PRECISA mudar.
        r = motor.configurar({"simbolo": "BTCUSD", "timeframe": "M15"})
        assert motor.timeframe == "M15"
        assert motor.simbolo == "BTCUSD"
        # A acao deu certo: trocou par e periodo, e nao pediu risco.
        assert r["ok"] is True

    @pytest.mark.parametrize("periodo", ["M5", "M15", "M30", "H1", "H4", "D1"])
    def test_todos_os_periodos_trocam(self, motor: MotorAuto, periodo: str) -> None:
        # O relato foi em M15 e H4. O defeito nao era de um periodo: era de
        # qualquer periodo diferente do que ja estava no motor.
        motor.configurar({"simbolo": "GOLD", "timeframe": "H1"})
        assert motor.timeframe == "H1"
        motor.configurar({"simbolo": "GOLD", "timeframe": periodo})
        assert motor.timeframe == periodo, f"{periodo} nao substituiu H1"

    def test_mudanca_repetida_acumula(self, motor: MotorAuto) -> None:
        motor.configurar({"timeframe": "M15"})
        motor.configurar({"timeframe": "H4"})
        motor.configurar({"timeframe": "H1"})
        assert motor.timeframe == "H1"

    def test_corretora_tambem_muda_antes_do_risco(self, motor: MotorAuto) -> None:
        # A corretora e o mercado estao no mesmo grupo: escolher onde observar
        # nao arrisca dinheiro.
        r = motor.configurar({"broker": "binance", "market": "crypto-spot"})
        assert motor.broker == "binance"
        assert motor.market == "crypto-spot"
        assert r["ok"] is True


class TestLigarContinuaExigindoRisco:
    """A correcao nao pode ter afrouxado a trava de risco."""

    def test_trocar_periodo_so_nao_pede_risco(self, motor: MotorAuto) -> None:
        # MEDIDO: a barra inferior manda `{timeframe}` e passava a receber
        # "defina lote, stop loss e take profit para operar" — aviso de risco em
        # acao que nao arrisca dinheiro, e que tinha dado certo. O operador lia a
        # barra inferior como quebrada.
        r = motor.configurar({"timeframe": "H4"})
        assert r["ok"] is True
        assert motor.timeframe == "H4"

    def test_pedido_de_lote_incompleto_e_recusado(self, motor: MotorAuto) -> None:
        # Se o pedido MEXE no risco, ele e julgado. Pedir lote sem SL e TP e
        # recusa, com o que falta.
        r = motor.configurar({"lote": 0.01})
        assert r["ok"] is False
        assert "stop loss" in r["error"]
        assert "take profit" in r["error"]

    def test_com_risco_completo_o_motor_aceita(self, motor: MotorAuto) -> None:
        r = motor.configurar(
            {
                "simbolo": "BTCUSD",
                "timeframe": "H4",
                "lote": 0.01,
                "sl_preco": 100.0,
                "tp_preco": 200.0,
            }
        )
        assert r["ok"] is True
        assert motor.timeframe == "H4"

    def test_corretora_desconhecida_ainda_e_recusada(self, motor: MotorAuto) -> None:
        # Gravar o alvo antes nao pode deixar passar corretora inventada: ela
        # e validada contra o catalogo, e a recusa vem antes de qualquer gravacao
        # de mercado.
        r = motor.configurar({"broker": "broker-que-nao-existe"})
        assert r["ok"] is False
        assert "desconhecida" in r["error"]


class TestLimitesContinuamSendoValidados:
    def test_valor_invalido_ainda_e_recusado(self, motor: MotorAuto) -> None:
        r = motor.configurar(
            {"lote": 0.01, "sl_preco": 1.0, "tp_preco": 2.0, "confianca_minima": "abc"}
        )
        assert r["ok"] is False
        assert "confianca_minima" in r["error"]

    def test_confianca_acima_de_100_e_recusada(self, motor: MotorAuto) -> None:
        # A regra do motor: 0 < confianca <= 100. 150 nao e "muita confianca",
        # e um valor invalido.
        r = motor.configurar(
            {"lote": 0.01, "sl_preco": 1.0, "tp_preco": 2.0, "confianca_minima": 150}
        )
        assert r["ok"] is False

    def test_campo_vazio_nao_e_enviado_como_valor(self, motor: MotorAuto) -> None:
        # MEDIDO: o painel mandava `''` para campo vazio, e `float('')` levanta
        # ValueError, que vira "valor invalido para confianca_minima". O
        # operador preenchia tres campos e recebia erro no quarto, que ele nao
        # preencheu.
        r = motor.configurar({"lote": 0.01, "sl_preco": 1.0, "tp_preco": 2.0})
        assert r["ok"] is True
        assert r["limites"]["confianca_minima"] == 0.0