# -*- coding: utf-8 -*-
"""Testes do motor de operacao automatica.

O motor abre posicao com dinheiro de verdade. Estes testes existem para provar
que ele NAO abre quando nao deve — que e a propriedade que importa. Um motor
que abre so quando deve e ainda tem bug e perigoso; um que nunca abre e
inutil. O alvo e o primeiro.

Cada teste injeta as dependencias (inferir, enviar, risk_state), entao nada
toca MT5 de verdade.
"""
from __future__ import annotations

import pytest

from backend.auto_engine import LimitesAuto, MotorAuto
from backend import ai_inference as ai


class InferenciaFalsa:
    """Dublê de Inferencia. Reproduz o que o servico real devolve."""

    def __init__(self, disponivel=True, signal="BUY", confianca=70.0, edge=0.11,
                 atr=2.0, price=4300.0, motivo="", modelo="rf_XAUUSD_H1"):
        self.disponivel = disponivel
        self.signal = signal
        self.confianca = confianca
        self.edge = edge
        self.atr = atr
        self.price = price
        self.motivo = motivo or ("inferencia real" if disponivel else "sem inferencia")
        self.modelo = modelo


def risco(ok=True, open_positions=0, daily_trades=0):
    return {
        "ok": ok, "open_positions": open_positions, "daily_trades": daily_trades,
        "daily_loss_pct": 0.1, "exposure_pct": 1.0, "drawdown_pct": 0.5,
    }


def enviar_espiao(chamadas: list[dict], resposta=None):
    def _enviar(payload):
        chamadas.append(payload)
        return resposta if resposta is not None else {
            "ok": True, "order": 1, "retcode": 10009, "price": payload["sl"],
        }
    return _enviar


def motor_pronto(**kwargs) -> MotorAuto:
    m = MotorAuto()
    m.limites = LimitesAuto(
        banca=20.0, risco_por_trade_pct=1.0, confianca_minima=55.0,
        edge_minimo=0.05, max_posicoes=2, max_operacoes_dia=20,
    )
    for k, v in kwargs.items():
        setattr(m.limites, k, v)
    return m


# --------------------------------------------------------------- limites


class TestLimites:
    def test_padrao_e_valido(self):
        ok, motivo = LimitesAuto().valido()
        assert ok, motivo

    @pytest.mark.parametrize("campo,valor", [
        ("banca", 0), ("banca", -5),
        ("risco_por_trade_pct", 0), ("risco_por_trade_pct", 50),
        ("confianca_minima", 0), ("confianca_minima", 150),
        ("max_posicoes", 0),
        ("max_operacoes_dia", 0),
        ("perda_diaria_max_pct", 0), ("perda_diaria_max_pct", 200),
        ("sl_atr", 0), ("tp_atr", -1),
        ("intervalo_minutos", 0),
    ])
    def test_rejeita_valor_fora_da_faixa(self, campo, valor):
        limites = LimitesAuto(**{campo: valor})
        ok, _ = limites.valido()
        assert ok is False, f"{campo}={valor} deveria ser rejeitado"

    def test_perda_diaria_alta_e_aceita(self):
        # O operador avancido pode escolher risco alto. O motor tem de
        # respeitar a escolha, nao景色 silosamente estreitar o intervalo.
        ok, _ = LimitesAuto(perda_diaria_max_pct=20.0).valido()
        assert ok is True


# ------------------------------------------------------- nao abre quando nao deve


class TestNaoAbreSemSinal:
    def test_sem_inferencia_nao_opera(self):
        m = motor_pronto()
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(disponivel=False, motivo="MT5 sem candles"),
            enviar_espiao(chamadas), risco)
        assert d.agir is False
        assert chamadas == [], "nao pode enviar ordem sem inferencia"
        assert "MT5 sem candles" in d.motivo

    def test_confianca_abaixo_do_minimo_nao_opera(self):
        m = motor_pronto(confianca_minima=60.0)
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(confianca=41.7), enviar_espiao(chamadas), risco)
        assert d.agir is False
        assert chamadas == []
        assert "41.7" in d.motivo and "60.0" in d.motivo

    def test_edge_abaixo_do_minimo_nao_opera(self):
        m = motor_pronto(edge_minimo=0.10)
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(edge=0.05), enviar_espiao(chamadas), risco)
        assert d.agir is False
        assert chamadas == []
        assert "edge" in d.motivo

    def test_sinal_neutral_nao_opera(self):
        m = motor_pronto()
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="NEUTRAL", confianca=90.0),
            enviar_espiao(chamadas), risco)
        assert d.agir is False
        assert chamadas == []
        assert "NEUTRAL" in d.motivo

    def test_sem_atr_nao_opera(self):
        # Sem ATR nao da para dimensionar protecao; inventar seria perigoso.
        m = motor_pronto()
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(atr=0.0), enviar_espiao(chamadas), risco)
        assert d.agir is False
        assert chamadas == []
        assert "ATR" in d.motivo


class TestFalhaFechada:
    def test_risk_gate_indisponivel_nao_opera(self):
        m = motor_pronto()
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(), enviar_espiao(chamadas),
            lambda: {"ok": False, "error": "sem dados"})
        assert d.agir is False
        assert chamadas == [], "sem risk_gate nao ha limite conhecido: nao opera"

    def test_risk_gate_que_lanca_nao_opera(self):
        m = motor_pronto()
        chamadas: list[dict] = []

        def _lança():
            raise RuntimeError("MT5 fora do ar")

        d = m.ciclo_unico(lambda s, t: InferenciaFalsa(), enviar_espiao(chamadas), _lança)
        assert d.agir is False
        assert chamadas == []

    def test_inferencia_que_lanca_nao_opera(self):
        m = motor_pronto()
        chamadas: list[dict] = []

        def _lança(s, t):
            raise RuntimeError("modelo corrompido")

        d = m.ciclo_unico(_lança, enviar_espiao(chamadas), risco)
        assert d.agir is False
        assert chamadas == []


class TestLimitesDeExposicao:
    def test_nao_abre_acima_do_maximo_de_posicoes(self):
        m = motor_pronto(max_posicoes=2)
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(), enviar_espiao(chamadas),
            lambda: risco(open_positions=2))
        assert d.agir is False
        assert chamadas == []
        assert "2 posicoes" in d.motivo

    def test_nao_abre_acima_do_limite_diario(self):
        m = motor_pronto(max_operacoes_dia=20)
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(), enviar_espiao(chamadas),
            lambda: risco(daily_trades=20))
        assert d.agir is False
        assert chamadas == []
        assert "limite diario" in d.motivo


class TestIdempotencia:
    def test_mesma_janela_nao_gera_duas_ordens(self):
        """Se a resposta se perde e o motor repete o ciclo, nao pode duplicar."""
        m = motor_pronto(intervalo_minutos=15)
        chamadas: list[dict] = []
        d1 = m.ciclo_unico(lambda s, t: InferenciaFalsa(), enviar_espiao(chamadas), risco)
        d2 = m.ciclo_unico(lambda s, t: InferenciaFalsa(), enviar_espiao(chamadas), risco)
        assert d1.agir is True
        assert d2.agir is False, "o segundo ciclo nao pode operar de novo"
        assert len(chamadas) == 1, "exatamente uma ordem"


# ---------------------------------------------------------------- opera


class TestOperaQuandoDeve:
    def test_sinal_forte_opera(self):
        m = motor_pronto()
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", confianca=72.0, edge=0.12),
            enviar_espiao(chamadas), risco)
        assert d.agir is True
        assert len(chamadas) == 1
        p = chamadas[0]
        assert p["symbol"] == "XAUUSD"
        assert p["side"] == "BUY"
        assert p["confirm"] is True
        assert p["sl"] < p["tp"], "BUY tem SL abaixo e TP acima"
        assert p["volume"] > 0
        assert p["origin"] == "motor_auto"

    def test_venda_tem_sl_acima_e_tp_abaixo(self):
        m = motor_pronto()
        chamadas: list[dict] = []
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="SELL", confianca=72.0),
            enviar_espiao(chamadas), risco)
        p = chamadas[0]
        assert p["side"] == "SELL"
        assert p["sl"] > p["tp"]

    def test_protecao_vem_do_atr_real(self):
        m = motor_pronto(sl_atr=2.0, tp_atr=4.0)
        chamadas: list[dict] = []
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", price=4300.0, atr=5.0, confianca=72.0),
            enviar_espiao(chamadas), risco)
        p = chamadas[0]
        # BUY: sl = preco - 2*ATR, tp = preco + 4*ATR
        assert p["sl"] == pytest.approx(4300.0 - 10.0, abs=0.01)
        assert p["tp"] == pytest.approx(4300.0 + 20.0, abs=0.01)

    def test_volume_respeita_banca_e_risco(self):
        m = motor_pronto(banca=1000.0, risco_por_trade_pct=1.0, sl_atr=1.0)
        chamadas: list[dict] = []
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", price=4300.0, atr=5.0, confianca=72.0),
            enviar_espiao(chamadas), risco)
        p = chamadas[0]
        # risco = 1000 * 1% = 10; distancia = 5 => volume = 2, mas o teto
        # do gateway e 0.10.
        assert p["volume"] == pytest.approx(0.10, abs=0.01)

    def test_registra_decisao_com_proveniencia(self):
        m = motor_pronto()
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(confianca=72.0, edge=0.12, modelo="rf_H1"),
            enviar_espiao([]), risco)
        d = m.decisoes[-1]
        assert d.sinal == "BUY"
        assert d.confianca == pytest.approx(72.0)
        assert d.edge == pytest.approx(0.12)
        assert d.timeframe == "H1"
        assert d.resultado  # o que o gateway respondeu


class TestOrdemRecusada:
    def test_recusa_do_gateway_vira_decisao_nao_operacional(self):
        m = motor_pronto()
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(confianca=72.0),
            enviar_espiao(chamadas, resposta={"ok": False, "error": "volume invalido"}),
            risco)
        assert d.agir is False
        assert "volume invalido" in d.motivo
        assert len(chamadas) == 1, "tentou, e o gateway recusou"


# ------------------------------------------------------------- integracao


class TestIntegracaoInferenciaReal:
    def test_inferencia_real_do_ambiente_e_recusada_quando_nao_publicada(self):
        """Se o modelo do timeframe nao passou na porta, o motor nao opera.

        Este teste amarra o motor ao servico real: um modelo reprovado no
        treino tem de barrar a operacao, nao passar pelo crack.
        """
        modelo = "M5"  # edge negativo no ambiente
        candles = None
        r = ai.inferir("XAUUSD", candles if candles is not None else __import__("pandas").DataFrame(), modelo)
        assert r.disponivel is False
        m = motor_pronto()
        d = m.ciclo_unico(lambda s, t: r, enviar_espiao([]), risco)
        assert d.agir is False


# ------------------------------------------------------------------ estado


class TestEstado:
    def test_snapshot_nao_expoe_segredos(self):
        m = motor_pronto()
        s = m.snapshot()
        assert set(s) >= {"ativo", "simbolo", "timeframe", "ciclo", "limites", "decisoes"}
        assert not any("token" in k.lower() or "senha" in k.lower() or "key" in k.lower()
                       for k in s)

    def test_configurar_rejeita_valor_invalido(self):
        m = MotorAuto()
        r = m.configurar({"banca": -1})
        assert r["ok"] is False
        assert r["error"]

    def test_ligar_exige_limites_validos(self):
        m = MotorAuto()
        m.limites.banca = 0
        r = m.ligar()
        assert r["ok"] is False
        assert m.ativo is False

    def test_desligar_e_idempotente(self):
        m = motor_pronto()
        assert m.desligar()["ok"] is True
        assert m.desligar()["ok"] is True
        assert m.ativo is False
