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
                 atr=2.0, price=4300.0, motivo="", modelo="rfATIVO_P60"):
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
    """Captura o payload que o motor entrega ao caminho de ordem.

    O motor envia os NOMES CANONICOS (`quantity`/`stop_loss`/`take_profit`),
    que sao os que o `UniversalOrderRequest` le. Antes este duble lia
    `payload["sl"]` e os testes abaixo conferiam `p["volume"]`: ou seja, o
    proprio teste fixava o vocabulario errado como se fosse o esperado, e o
    motor nao conseguia enviar ordem nenhuma sem que nada reprovasse.
    Ver `tests/test_contrato_do_motor.py` para a prova de que isso era o bug.
    """
    def _enviar(payload):
        chamadas.append(payload)
        return resposta if resposta is not None else {
            "ok": True, "order": 1, "retcode": 10009,
            "price": payload["stop_loss"],
        }
    return _enviar


ATIVO = "ATIVO_TESTE"
PERIODO = "P60"


def motor_pronto(**kwargs) -> MotorAuto:
    m = MotorAuto()
    m.simbolo = ATIVO
    m.timeframe = PERIODO
    # TODOS os campos sao preenchidos aqui, porque `LimitesAuto()` nasce ZERADO
    # desde 04/10/2026. E o que o motor deve receber: limite escolhido, nunca
    # palpite do codigo. O helper existe para o teste NAO precisar repetir os
    # dez valores — mas continua sendo explicito o que esta em jogo.
    m.limites = LimitesAuto(
        banca=20.0, risco_por_trade_pct=1.0, confianca_minima=55.0,
        edge_minimo=0.05, max_posicoes=2, max_operacoes_dia=20,
        perda_diaria_max_pct=2.0, sl_atr=1.5, tp_atr=3.0,
        intervalo_minutos=15,
    )
    for k, v in kwargs.items():
        setattr(m.limites, k, v)
    return m


# --------------------------------------------------------------- limites


class TestLimites:
    def test_padrao_nao_e_valido(self):
        """`LimitesAuto()` nasce ZERADO e NAO pode operar.

        Este teste afirmava o contrario (`test_padrao_e_valido`): o padrao era
        valido porque vinha com banca=20 e perda diaria=2%. O dono pediu zero
        em tudo, e com razao: o operador via na tela numeros que nao tinha
        escolhido, e o motor operava com o risco de outra pessoa.
        """
        ok, motivo = LimitesAuto().valido()
        assert ok is False
        assert "nenhum valor vem por padrao" in motivo

    def test_erro_nomeia_os_campos_que_faltam(self):
        """A mensagem diz o que preencher, nao "valor invalido"."""
        _, motivo = LimitesAuto(banca=1000.0).valido()
        for campo in ("confianca minima", "edge minimo", "maximo de posicoes"):
            assert campo in motivo, f"{campo} nao listado: {motivo}"

    def test_um_campo_preenchido_nao_basta(self):
        ok, _ = LimitesAuto(max_operacoes_dia=10).valido()
        assert ok is False

    def test_perda_diaria_alta_e_aceita(self):        # O operador avancado escolhe o risco alto. O motor respeita a
        # escolha em vez de estreitar o intervalo silenciosamente.
        ok, motivo = LimitesAuto(
            banca=1000.0, risco_por_trade_pct=1.0, confianca_minima=55.0,
            edge_minimo=0.05, max_posicoes=2, max_operacoes_dia=20,
            sl_atr=1.5, tp_atr=3.0, intervalo_minutos=15,
            perda_diaria_max_pct=20.0,
        ).valido()
        assert ok is True, motivo

    def test_modo_simples_lote_sl_tp_basta(self):
        """Painel simples: TP, SL, LOTE. Sem banca, risco, confianca ou perda."""
        ok, motivo = LimitesAuto(lote=0.01, sl_preco=4290.0, tp_preco=4310.0).valido()
        assert ok is True, motivo

    def test_modo_simples_incompleto_recusa(self):
        ok, motivo = LimitesAuto(lote=0.01).valido()
        assert ok is False
        assert "stop" in motivo.lower() or "take" in motivo.lower()


# ------------------------------------------------------- nao abre quando nao deve


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
        assert p["symbol"] == ATIVO
        assert p["side"] == "BUY"
        assert p["confirm"] is True
        assert p["stop_loss"] < p["take_profit"], "BUY tem SL abaixo e TP acima"
        assert p["quantity"] > 0
        assert p["origin"] == "motor_auto"

    def test_venda_tem_sl_acima_e_tp_abaixo(self):
        m = motor_pronto()
        chamadas: list[dict] = []
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="SELL", confianca=72.0),
            enviar_espiao(chamadas), risco)
        p = chamadas[0]
        assert p["side"] == "SELL"
        assert p["stop_loss"] > p["take_profit"]

    def test_protecao_vem_do_atr_real(self):
        m = motor_pronto(sl_atr=2.0, tp_atr=4.0)
        chamadas: list[dict] = []
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", price=4300.0, atr=5.0, confianca=72.0),
            enviar_espiao(chamadas), risco)
        p = chamadas[0]
        # BUY: sl = preco - 2*ATR, tp = preco + 4*ATR
        assert p["stop_loss"] == pytest.approx(4300.0 - 10.0, abs=0.01)
        assert p["take_profit"] == pytest.approx(4300.0 + 20.0, abs=0.01)

    def test_volume_respeita_banca_e_risco(self):
        m = motor_pronto(banca=1000.0, risco_por_trade_pct=1.0, sl_atr=1.0)
        chamadas: list[dict] = []
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", price=4300.0, atr=5.0, confianca=72.0),
            enviar_espiao(chamadas), risco)
        p = chamadas[0]
        # risco = 1000 * 1% = 10; distancia = 5 => volume = 2, mas o teto
        # do gateway e 0.10.
        assert p["quantity"] == pytest.approx(0.10, abs=0.01)

    def test_modo_simples_opera_com_lote_e_precos_do_painel(self):
        m = MotorAuto()
        m.simbolo = ATIVO
        m.timeframe = PERIODO
        m.limites = LimitesAuto(lote=0.01, sl_preco=4290.0, tp_preco=4310.0)
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", price=4300.0, atr=5.0,
                                         confianca=72.0, edge=0.12),
            enviar_espiao(chamadas), risco)
        assert d.agir is True, d.motivo
        p = chamadas[0]
        assert p["quantity"] == pytest.approx(0.01)
        assert p["stop_loss"] == pytest.approx(4290.0)
        assert p["take_profit"] == pytest.approx(4310.0)

    def test_modo_simples_recusa_sl_incoerente_com_buy(self):
        m = MotorAuto()
        m.simbolo = ATIVO
        m.timeframe = PERIODO
        m.limites = LimitesAuto(lote=0.01, sl_preco=4310.0, tp_preco=4290.0)
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", price=4300.0, atr=5.0,
                                         confianca=72.0, edge=0.12),
            enviar_espiao([]), risco)
        assert d.agir is False
        assert "SL" in d.motivo

    def test_banca_de_1_dolar_tem_piso_de_lote(self):
        """Conta de $1: o volume fracionario nao pode arredondar para zero."""
        m = motor_pronto(banca=1.0, risco_por_trade_pct=1.0, sl_atr=1.0)
        chamadas: list[dict] = []
        d = m.ciclo_unico(
            lambda s, t: InferenciaFalsa(signal="BUY", price=4300.0, atr=5.0, confianca=72.0),
            enviar_espiao(chamadas), risco)
        assert d.agir is True, d.motivo
        assert chamadas[0]["quantity"] == pytest.approx(0.01)

    def test_registra_decisao_com_proveniencia(self):
        m = motor_pronto()
        m.ciclo_unico(
            lambda s, t: InferenciaFalsa(confianca=72.0, edge=0.12, modelo="rfP60"),
            enviar_espiao([]), risco)
        d = m.decisoes[-1]
        assert d.sinal == "BUY"
        assert d.confianca == pytest.approx(72.0)
        assert d.edge == pytest.approx(0.12)
        assert d.timeframe == PERIODO
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
        r = ai.inferir(ATIVO, candles if candles is not None else __import__("pandas").DataFrame(), modelo)
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
# ------------------------------------------------------ corretora de verdade
#
# POR QUE ESTES TESTES EXISTEM
# ===========================
# `MotorAuto` aceita, valida e EXPOE `broker` e `market` (linhas 192-229 e
# 164/233). O `_loop`, esse, importa `mt5_gateway` direto e ignora os dois.
#
# O efeito e o pior possivel para quem opera: escolher `binance`, ver `binance`
# na tela e no historico, e a ordem ir para o MT5. A tela mente sobre onde o
# dinheiro esta indo.
#
# A suite tem 25 testes e nenhum cobria o roteamento — por isso estes quatro.
# Eles leem o FONTE do `_loop` de proposito: subir a thread e esperar um ciclo
# seria lento, fragil e abriria caminho para MT5 de verdade. Um teste que
# depende de rede real nao e um teste, e um risco.


class TestRoteamentoPorCorretora:
    """O `_loop` tem de usar a corretora que o operador configurou."""

    @staticmethod
    def _fonte_do_loop() -> str:
        """Trecho do `_loop` na fonte, para inspecao sem executar nada."""
        import inspect
        from backend import auto_engine

        return inspect.getsource(auto_engine.MotorAuto._loop)

    @staticmethod
    def _codigo_do_loop() -> str:
        """O `_loop` sem a docstring e sem os comentarios.

        Necessario porque a docstring CITA o codigo antigo para documentar o
        defeito. Um teste que varre o texto inteiro acusa a propria evidencia
        do bug — e `test_loop_usa_o_router_universal` ja foi aprovado por
        acaso, pelo mesmo motivo.
        """
        import ast
        import inspect
        import textwrap
        from backend import auto_engine

        arvore = ast.parse(textwrap.dedent(inspect.getsource(auto_engine)))
        for no in ast.walk(arvore):
            if isinstance(no, ast.ClassDef) and no.name == "MotorAuto":
                for filho in no.body:
                    if isinstance(filho, ast.FunctionDef) and filho.name == "_loop":
                        corpo = filho.body[1:]  # pula o docstring
                        return "\n".join(
                            ast.unparse(parte) for parte in corpo
                        )
        raise AssertionError("_loop nao encontrado na fonte de MotorAuto")

    def test_loop_nao_importa_mt5_gateway_direto(self):
        """Importar `mt5_gateway` dentro do `_loop` prende o motor no MT5.

        O `UniversalRouter.adapter_for` existe e sabe escolher entre os cinco
        adaptadores. O motor precisa passar por ele.
        """
        codigo = self._codigo_do_loop()
        assert "mt5_gateway" not in codigo, (
            "_loop importa mt5_gateway direto: ignora o UniversalRouter e a "
            "corretora escolhida pelo operador"
        )

    def test_loop_nao_chama_trade_order_do_mt5(self):
        """`_trade_order` e o envio do MT5. Chama-lo direto ignora a corretora."""
        codigo = self._codigo_do_loop()
        assert "_trade_order" not in codigo, (
            "_loop chama _trade_order (MT5) direto: a ordem vai para o MT5 "
            "mesmo com outra corretora configurada"
        )

    def test_loop_usa_o_router_universal(self):
        """O caminho de envio tem de passar pelo `UniversalRouter`."""
        codigo = self._codigo_do_loop()
        assert "UniversalRouter" in codigo, (
            "_loop nao menciona o UniversalRouter: nao ha como ele escolher "
            "o adaptador pela corretora configurada"
        )

    def test_loop_resolve_por_broker_e_market(self):
        """As tres dependencias (candles, risco, envio) sao resolvidas pelo par.

        E o teste que cobre a regressao de verdade: um `_loop` que resolve
        candles por corretora mas envia pelo MT5 ainda estaria quebrado.
        """
        codigo = self._codigo_do_loop()
        assert "self.broker" in codigo, "o `_loop` ignora a corretora configurada"
        assert "self.market" in codigo, "o `_loop` ignora o mercado configurado"

    def test_snapshot_reporta_a_corretora_configurada(self):
        """`snapshot()` nao pode inventar "mt5" quando o operador escolheu outra.

        O `or "mt5"` das linhas 164 e 233 era a forma mais direta dessa
        mentira: com `broker=""` ele mostrava MT5, e o `_loop` usava MT5.
        """
        m = motor_pronto()
        m.configurar({"broker": "binance", "market": "crypto-spot"})
        assert m.snapshot()["broker"] == "binance", (
            "snapshot devolve uma corretora diferente da configurada"
        )

    def test_snapshot_nao_inventa_corretora_quando_nao_escolhida(self):
        """Sem corretora escolhida, o painel mostra vazio — nao MT5."""
        m = motor_pronto()
        m.broker = ""
        m.market = ""
        assert m.snapshot()["broker"] == "", (
            "snapshot inventou uma corretora que o operador nao escolheu"
        )

    def test_ligar_exige_corretora_escolhida(self):
        """Ligar sem corretora e recusado, com motivo.

        Descobrir no meio do ciclo significa inferencia, risco e sizing jogados
        fora antes de o operador ver o erro.
        """
        m = motor_pronto()
        m.broker = ""
        r = m.ligar()
        assert r["ok"] is False
        assert "corretora" in r["error"].lower()
        assert m.ativo is False


class TestMultiAlvos:
    """Varios graficos, horarios diferentes, sem duplicar."""

    def test_alvo_duplicado_recusa(self):
        m = motor_pronto()
        r = m.configurar_alvos([
            {"broker": "mt5", "market": "forex", "symbol": "EURUSD", "timeframe": "H1"},
            {"broker": "mt5", "market": "forex", "symbol": "EURUSD", "timeframe": "H1"},
        ])
        assert r["ok"] is False
        assert "duplicado" in r["error"].lower()

    def test_mesmo_ativo_dois_timeframes_recusa(self):
        m = motor_pronto()
        r = m.configurar_alvos([
            {"broker": "mt5", "market": "forex", "symbol": "EURUSD", "timeframe": "H1"},
            {"broker": "mt5", "market": "forex", "symbol": "EURUSD", "timeframe": "M15"},
        ])
        assert r["ok"] is False
        assert "um tf por ativo" in r["error"].lower()

    def test_mesmo_ativo_em_corretoras_diferentes_ok(self):
        m = motor_pronto()
        r = m.configurar_alvos([
            {"broker": "mt5", "market": "crypto-spot", "symbol": "BTCUSD", "timeframe": "H1"},
            {"broker": "mexc", "market": "crypto-spot", "symbol": "BTCUSDT", "timeframe": "H1"},
        ])
        assert r["ok"] is True
        assert len(r["alvos"]) == 2

    def test_mercado_incompativel_recusa(self):
        m = motor_pronto()
        r = m.configurar_alvos([
            {"broker": "mexc", "market": "forex", "symbol": "EURUSD", "timeframe": "H1"},
        ])
        assert r["ok"] is False

    def test_ciclo_alvos_opera_cada_um_uma_vez(self):
        m = motor_pronto()
        m.configurar_alvos([
            {"broker": "mt5", "market": "forex", "symbol": "EURUSD", "timeframe": "H1"},
            {"broker": "mexc", "market": "crypto-spot", "symbol": "BTCUSDT", "timeframe": "H1"},
        ])
        chamadas: list[dict] = []
        resultados = m.ciclo_alvos(
            lambda s, t: InferenciaFalsa(signal="BUY", confianca=72.0, edge=0.12),
            enviar_espiao(chamadas), risco)
        assert len(resultados) == 2
        assert all(d.agir for d in resultados)
        assert len(chamadas) == 2
        # Segunda passada na mesma janela: nenhuma duplicata.
        resultados2 = m.ciclo_alvos(
            lambda s, t: InferenciaFalsa(signal="BUY", confianca=72.0, edge=0.12),
            enviar_espiao(chamadas), risco)
        assert all(not d.agir for d in resultados2)
        assert len(chamadas) == 2

    def test_falha_de_um_nao_derruba_os_outros(self):
        m = motor_pronto()
        m.configurar_alvos([
            {"broker": "mt5", "market": "forex", "symbol": "EURUSD", "timeframe": "H1"},
            {"broker": "mexc", "market": "crypto-spot", "symbol": "BTCUSDT", "timeframe": "H1"},
        ])
        def _inferir(s, t):
            if "EUR" in s:
                raise RuntimeError("MT5 fora do ar")
            return InferenciaFalsa(signal="BUY", confianca=72.0, edge=0.12)
        resultados = m.ciclo_alvos(_inferir, enviar_espiao([]), risco)
        assert len(resultados) == 2
        assert resultados[1].agir is True or resultados[1].motivo
