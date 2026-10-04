# -*- coding: utf-8 -*-
"""O contrato universal e o motor automatico falam o mesmo idioma.

O QUE ESTE TESTE TRAVA
=====================
Em 04/10/2026 o motor automatico nao conseguia enviar NENHUMA ordem, e o erro
que o operador via na tela era:

    envio falhou: symbol e quantity são obrigatórios

A causa nao era conta, corretora, EA ou configuracao. Era desacamento de nome:

    `auto_engine.ciclo_unico` montava   `volume` / `sl` / `tp`
    `UniversalOrderRequest` exigia      `quantity` / `stop_loss` / `take_profit`

`quantity` chegava vazio, `0 <= 0` disparava a recusa, e o motor gastava um
ciclo inteiro de inferencia e risco para morrer na ultima linha. O ciclo
automatico NUNCA produziu uma ordem antes desta correcao.

Este teste existe porque nada pegaria isso de novo:
- a suite passa com o defeito (o payload e um dicionario, nao uma chamada de
  rede, entao nenhum teste de integracao via a vida real dessa linha);
- o compilador nao reclama;
- o painel mostra o erro e o operador conclui que e conta.

A prova e a funcao `ciclo_unico` entregando ao CONTRATO REAL, e nao a um duble.
"""
from __future__ import annotations

import pytest

from backend.auto_engine import LimitesAuto, MotorAuto, pedido_para_router
from backend.universal_contracts import UniversalOrderRequest

ATIVO = "XAUUSD"
PERIODO = "H1"
# O `_loop` injeta broker/market/account_id no pedido; `ciclo_unico` nao os
# conhece. O duble abaixo e o MESMO caminho do router real, entao o teste
# exercita o contrato de verdade e nao um atalho.
ROTA = {"broker": "mt5", "market": "forex", "account_id": "conta-1"}


def enviar_pelo_contrato(capturado: dict, resposta=None):
    """Duble do `_loop.enviar`: completa o escopo e valida no contrato real."""
    def _enviar(payload):
        capturado.update(payload)
        pedido = {**ROTA, **payload}
        UniversalOrderRequest.from_payload(pedido)
        return resposta if resposta is not None else {"ok": True, "order": 1}
    return _enviar


def _payload_minimo(**extra):
    """Payload no vocabulario do PAINEL/GATEWAY legado (`volume`/`sl`/`tp`)."""
    base = {
        "broker": "mt5", "market": "forex", "account_id": "conta-1",
        "symbol": ATIVO, "side": "BUY", "volume": 0.02,
        "sl": 4000.0, "tp": 4100.0, "confirm": True, "request_id": "auto-teste",
    }
    base.update(extra)
    return base


class InferenciaFalsa:
    disponivel = True
    signal = "BUY"
    confianca = 80.0
    edge = 0.12
    atr = 20.0
    price = 4300.0
    motivo = "inferencia real"
    modelo = "Floresta"


def risco_ok():
    return {"ok": True, "open_positions": 0, "daily_trades": 0,
            "daily_loss_pct": 0.1, "exposure_pct": 1.0, "drawdown_pct": 0.5}


def motor_pronto() -> MotorAuto:
    m = MotorAuto()
    m.simbolo = ATIVO
    m.timeframe = PERIODO
    m.limites = LimitesAuto(
        banca=1000.0, risco_por_trade_pct=1.0, confianca_minima=50.0,
        edge_minimo=0.05, max_posicoes=5, max_operacoes_dia=20,
        sl_atr=2.0, tp_atr=3.0, intervalo_minutos=5,
    )
    return m


class TestVocabularioAceito:
    """Os dois nomes sao o MESMO campo. Nenhum dos dois pode quebrar ordem."""

    def test_vocabulario_legado_e_aceito(self):
        r = UniversalOrderRequest.from_payload(_payload_minimo())
        assert r.quantity == pytest.approx(0.02)
        assert r.stop_loss == pytest.approx(4000.0)
        assert r.take_profit == pytest.approx(4100.0)

    def test_vocabulario_canonico_e_aceito(self):
        r = UniversalOrderRequest.from_payload(_payload_minimo(
            quantity=0.02, stop_loss=4000.0, take_profit=4100.0,
            volume=None, sl=None, tp=None,
        ))
        assert r.quantity == pytest.approx(0.02)

    def test_canonico_vence_quando_os_dois_vem(self):
        """Precedencia FIXA: sem isso o resultado dependeria da ordem do dict."""
        r = UniversalOrderRequest.from_payload(_payload_minimo(
            quantity=0.05, stop_loss=3900.0, take_profit=4200.0,
        ))
        assert r.quantity == pytest.approx(0.05)
        assert r.stop_loss == pytest.approx(3900.0)

    def test_volume_zero_ainda_e_recusado(self):
        """Aceitar o alias NAO pode afrouxar a trava de tamanho."""
        with pytest.raises(ValueError, match="obrigat"):
            UniversalOrderRequest.from_payload(_payload_minimo(volume=0))

    def test_quantity_texto_e_recusado_com_motivo(self):
        """Erro legivel, nao TypeError cru vindo de float()."""
        with pytest.raises(ValueError, match="num"):
            UniversalOrderRequest.from_payload(_payload_minimo(quantity="dez"))


class TestMotorEntregaContratoValido:
    """A prova que faltava: o payload do motor passa no contrato DE VERDADE."""

    def test_payload_do_motor_passa_no_contrato_real(self):
        m = motor_pronto()
        capturado: dict = {}
        decisao = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(),
            enviar_pelo_contrato(capturado),
            risco_ok,
        )
        assert capturado, "o motor nao chamou o envio"
        assert decisao.agir is True, decisao.motivo
        # Este e o assertion que reprovava antes da correcao.
        request = UniversalOrderRequest.from_payload({**ROTA, **capturado})
        assert request.symbol == ATIVO
        assert request.quantity > 0
        assert request.stop_loss and request.take_profit

    def test_motor_usa_o_nome_canonico(self):
        """Dois lugares falando o mesmo idioma impede o desacamento de voltar."""
        m = motor_pronto()
        capturado: dict = {}
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(),
            lambda p: (capturado.update(p), {"ok": True})[1],
            risco_ok,
        )
        assert "quantity" in capturado
        assert "stop_loss" in capturado
        assert "take_profit" in capturado
        assert "volume" not in capturado

    def test_decisao_nao_e_falha_por_descasamento(self):
        """O sintoma na tela: motivo com 'envio falhou' e sem ordem real."""
        m = motor_pronto()
        decisao = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(),
            enviar_pelo_contrato({}),
            risco_ok,
        )
        assert decisao.agir is True, decisao.motivo
        assert "envio falhou" not in decisao.motivo
        assert decisao.resultado.get("order") == 1



class TestTraducaoParaORouter:
    """A traducao do payload precisa ser testada no codigo REAL.

    POR QUE ESTE TESTE EXISTE
    ========================
    A traducao vivia dentro de `_loop.enviar`, marcado `# pragma: no cover`.
    Nenhum teste a executava, e nela `payload["volume"]` continuava lendo uma
    chave que a montagem nao produz. O operador via `envio falhou: 'volume'`.

    A primeira versao deste teste REPLICAVA a traducao dentro do proprio
    teste — e por isso passava com o codigo real quebrado. Medido em
    04/10/2026: reintroduzir `payload["volume"]` deixou os 50 testes verdes.
    Um duble que repete a logica prova que a logica foi escrita, nao que ela
    esta no caminho.

    A REGRA: quem verifica traducao importa a funcao, nao reescreve o corpo.
    """

    def _payload(self, **extra):
        base = {
            "request_id": "auto-teste", "symbol": ATIVO, "side": "BUY",
            "quantity": 0.02, "stop_loss": 4000.0, "take_profit": 4100.0,
            "confirm": True,
        }
        base.update(extra)
        return base

    def test_a_traducao_usa_o_nome_canonico(self):
        pedido = pedido_para_router(self._payload(), "mt5", "forex", "conta-1")
        assert pedido["quantity"] == pytest.approx(0.02)
        assert "volume" not in pedido

    def test_o_pedido_survive_ao_contrato_universal(self):
        """O pedido final tem de passar no contrato de verdade, nao num duble."""
        pedido = pedido_para_router(self._payload(), "mt5", "forex", "conta-1")
        r = UniversalOrderRequest.from_payload(pedido)
        assert r.quantity == pytest.approx(0.02)
        assert r.symbol == ATIVO

    def test_o_lado_compra_vira_buy(self):
        pedido = pedido_para_router(self._payload(side="BUY"), "mt5", "forex", "c")
        assert pedido["side"] == "buy"

    def test_o_lado_venda_vira_sell(self):
        pedido = pedido_para_router(self._payload(side="SELL"), "mt5", "forex", "c")
        assert pedido["side"] == "sell"

    def test_a_conta_vem_do_argumento_e_nao_do_payload(self):
        """A conta e resolvida pela corretora ativa; o `Decisao` nao a tem.

        Antes era `payload.get("account_id", "")`, sempre vazio: toda ordem
        morria em "account_id e obrigatorio" no contrato universal.
        """
        pedido = pedido_para_router(self._payload(), "mt5", "forex", "conta-real")
        assert pedido["account_id"] == "conta-real"


class TestCicloInteiroNaoDaKeyError:
    """Do `ciclo_unico` ate o router: nenhuma excecao no caminho."""

    def test_o_ciclo_completo_monta_e_traduz(self):
        m = motor_pronto()
        m.broker = "mt5"
        m.market = "forex"
        pedidos: list[dict] = []

        def _enviar(payload):
            # Usa a traducao REAL do modulo.
            pedido = pedido_para_router(payload, "mt5", "forex", "conta-1")
            UniversalOrderRequest.from_payload(pedido)
            pedidos.append(pedido)
            return {"ok": True, "order": 11}

        decisao = m.ciclo_unico(lambda s, t: InferenciaFalsa(), _enviar, risco_ok)
        assert "envio falhou" not in decisao.motivo, decisao.motivo
        assert decisao.agir is True, decisao.motivo
        assert pedidos and pedidos[0]["quantity"] == pytest.approx(decisao.volume)

    def test_erro_de_traducao_vira_recusa_com_motivo_nao_crash(self):
        """Excecao na traducao precisa virar `Decisao(agir=False)` com motivo.

        Sem o `except`, um nome errado derrubaria a thread do `_loop` e o
        operador veria o motor ligado e nenhum ciclo acontecendo — sem uma
        linha de log que explicasse.
        """
        m = motor_pronto()

        def _enviar(payload):
            pedido = pedido_para_router(
                {k: v for k, v in payload.items() if k != "quantity"},
                "mt5", "forex", "conta-1")
            return {"ok": True}

        decisao = m.ciclo_unico(lambda s, t: InferenciaFalsa(), _enviar, risco_ok)
        assert decisao.agir is False
        assert "quantity" in decisao.motivo

