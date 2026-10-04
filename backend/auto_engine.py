# -*- coding: utf-8 -*-
"""Motor de operacao automatica: inferencia -> decisao -> ordem.

O QUE ESTE MOTOR FAZ
====================
A cada ciclo ele: lê a inferencia real do modelo treinado, decide se ha sinal
suficiente, calcula o tamanho da posicao a partir do risco que o OPERADOR
configurou, consulta o risk_gate e so entao chama o caminho de ordem do gateway.

O QUE ESTE MOTOR NAO FAZ
========================
- Nao inventa sinal. Se a inferencia nao rodou, o ciclo termina sem ordem.
- Nao ignora o risk_gate. `validate_trade` e chamado e pode recusar.
- Nao contorna a trava de emergencia.
- Nao envia ordem sem as protecoes: SL e TP sao obrigatorios no gateway, e o
  motor calcula os dois a partir do ATR real do simbolo.
- Nao abre posicao se ja houver o maximo simultaneo, nem se o dia ja perdeu
  mais que o limite.

SOBRE RISCO
============
O motor implementa exatamente o risco que o operador configurar — e nada mais.
Os limites vivem em `LimitesAuto` e sao aplicados a CADA ciclo, nao apenas
avisados na tela. Configurar risco alto aqui nao e um toggle: e assumir
responsabilidade por perder dinheiro, que e a intencao de quem opera.

Este motor opera em DEMO e REAL pelo mesmo caminho. `_trade_order` no gateway exige
REAL, e o motor nao tenta contornar: abrir posicao em conta real exige uma
etapa separada e explicita, com credencial propria.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# --------------------------------------------------------------- traducao


def pedido_para_router(payload: dict[str, Any], broker: str, market: str,
                       account_id: str) -> dict[str, Any]:
    """Traduz o payload do painel para o pedido do `UniversalRouter`.

    POR QUE ESTA FUNCAO FOI EXTRAIDA
    ================================
    Ela vivia dentro do `_loop.enviar`, marcado `# pragma: no cover` por ser
    thread de producao. Sem cobertura, a traducao ficou sem teste: e la que
    `payload["volume"]` continuou lendo uma chave que a montagem nao produz.
    O resultado na tela do operador era `envio falhou: 'volume'` — e o motor
    nao enviava ordem nenhuma.

    O teste anterior replicava a traducao dentro do proprio teste, e por isso
    passava com o codigo real quebrado: um duble que repete a logica prova
    que a logica foi escrita, nao que ela esta no caminho.

    `quantity` e o nome canonico do `UniversalOrderRequest`, e o mesmo que a
    montagem em `ciclo_unico` usa. Os dois lados falam a mesma lingua por
    construcao, e nao por Dois dicionarios que cada um le por sua conta.
    """
    return {
        "request_id": payload["request_id"],
        "broker": broker,
        "market": market,
        "symbol": payload["symbol"],
        "side": "buy" if str(payload["side"]).upper() == "BUY" else "sell",
        "quantity": payload["quantity"],
        "price": payload.get("price"),
        "order_type": "market",
        "confirm": True,
        "account_id": account_id,
    }


# ------------------------------------------------------------------ limites


@dataclass
class LimitesAuto:
    """Parametros de risco que o OPERADOR define. Aplicados a cada ciclo.

    Estes limites sao o preco do produto. Um operador avancido escolhe o risco
    que aceita perder; o motor nao tem opinion a respeito, apenas o respeita.
    """

    #: Banco declarado pelo operador (moeda da conta). ZERO = nao declarado.
    banca: float = 0.0
    #: Percentual da banca arriscado por operacao.
    risco_por_trade_pct: float = 0.0
    #: Confianca minima do modelo para operar (probabilidade real, 0-100).
    confianca_minima: float = 0.0
    #: Edge minimo aceitavel do modelo.
    edge_minimo: float = 0.0
    #: Numero maximo de posicoes simultaneas.
    max_posicoes: int = 0
    #: Numero maximo de operacoes por dia.
    max_operacoes_dia: int = 0
    #: Perda maxima diaria como percentual da banca. Ao atingir, o motor para.
    perda_diaria_max_pct: float = 0.0
    #: Multiplicador de ATR usado no Stop Loss.
    sl_atr: float = 0.0
    #: Multiplicador de ATR usado no Take Profit.
    tp_atr: float = 0.0
    #: Intervalo minimo entre duas avaliacoes do mesmo simbolo.
    intervalo_minutos: int = 0
    # MODO SIMPLES (painel so mostra LOTE + SL + TP + AUTO).
    # Lote direto, sem conta de banca; SL/TP em preco absoluto, sem ATR.
    # Zero = nao declarado. Quando os tres estao preenchidos, o resto e
    # opcional: o risk_gate do gateway continua limitando a exposicao real.
    lote: float = 0.0
    sl_preco: float = 0.0
    tp_preco: float = 0.0

    #: Rotulo de cada campo: o erro diz o que FALTA, nao "valor invalido".
    ROTULOS = {
        "banca": "banca",
        "risco_por_trade_pct": "risco por operacao (%)",
        "confianca_minima": "confianca minima (%)",
        "edge_minimo": "edge minimo",
        "max_posicoes": "maximo de posicoes",
        "max_operacoes_dia": "maximo de operacoes por dia",
        "perda_diaria_max_pct": "perda diaria maxima (%)",
        "sl_atr": "multiplicador de ATR do stop loss",
        "tp_atr": "multiplicador de ATR do take profit",
        "intervalo_minutos": "intervalo entre avaliacoes (minutos)",
        "lote": "lote",
        "sl_preco": "stop loss (preco)",
        "tp_preco": "take profit (preco)",
    }

    def modo_simples(self) -> bool:
        """Lote + SL + TP preenchidos: o painel simples decide tudo."""
        return self.lote > 0 and self.sl_preco > 0 and self.tp_preco > 0

    def valido(self) -> tuple[bool, str]:
        """Zero e AUSENTE, nao "pode ser zero".

        Antes a mensagem dizia "banca tem de ser maior que zero" para quem
        digitou 0 e para quem digitou -5 — o operador nao sabia se tinha
        escolhido o valor ou se o sistema tinha preenchido por ele.
        """
        # Modo simples primeiro: lote + SL + TP bastam. O risk_gate do
        # gateway limita volume e exposicao; nada aqui e presumido.
        simples = [n for n in ("lote", "sl_preco", "tp_preco") if getattr(self, n) != 0]
        if simples:
            faltam = [self.ROTULOS[n] for n in ("lote", "sl_preco", "tp_preco")
                      if getattr(self, n) <= 0]
            if faltam:
                return False, "defina lote, stop loss e take profit para operar"
            return True, ""
        faltando = [
            self.ROTULOS[nome]
            for nome in self.ROTULOS
            if nome not in ("lote", "sl_preco", "tp_preco") and getattr(self, nome) == 0
        ]
        if faltando:
            return False, (
                "defina no painel de operacao automatica: "
                + ", ".join(faltando)
                + " — nenhum valor vem por padrao"
            )
        if self.banca < 0:
            return False, "banca nao pode ser negativa"
        # Sem teto e sem piso alem de $1: a partir de 1 dolar ja opera. O
        # risco por operacao e escolha do operador (o risk_gate limita a
        # exposicao real); travar em 10% seria o codigo decidindo o risco.
        if not 1 <= self.banca:
            return False, "banca minima de 1 para operar"
        if not self.risco_por_trade_pct > 0:
            return False, "risco por operacao tem de ser maior que zero"
        if not 0 < self.confianca_minima <= 100:
            return False, "confianca minima tem de estar entre 0 e 100"
        if not self.edge_minimo > 0:
            return False, "edge minimo tem de ser maior que zero"
        if self.max_posicoes < 1:
            return False, "maximo de posicoes tem de ser ao menos 1"
        if self.max_operacoes_dia < 1:
            return False, "maximo de operacoes por dia tem de ser ao menos 1"
        if not self.perda_diaria_max_pct > 0:
            return False, "perda diaria maxima tem de ser maior que zero"
        if self.sl_atr <= 0 or self.tp_atr <= 0:
            return False, "multiplicadores de ATR tem de ser positivos"
        if self.intervalo_minutos < 1:
            return False, "intervalo tem de ser ao menos 1 minuto"
        return True, ""


# ------------------------------------------------------------------- estado


@dataclass
class Decisao:
    """Por que o motor fez (ou nao fez) o que fez. Tudo fica registrado."""

    timestamp: str
    symbol: str
    timeframe: str
    agir: bool
    motivo: str
    sinal: str = "NEUTRAL"
    confianca: float = 0.0
    edge: float | None = None
    volume: float = 0.0
    risco_moeda: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    resultado: dict[str, Any] = field(default_factory=dict)
    #: Nome do artefato que produziu a inferencia deste ciclo, lido do
    #: `.meta.json` (campo `algorithm`). Antes nao existia, e o terminal ao vivo
    #: FABRICAVA um nome a partir de `simbolo`/`timeframe` — mostrando
    #: `random_forest_XAUUSD_H1` sem ter lido aquilo de lugar nenhum.
    #: Vazio quando o ciclo nem chegou a inferir.
    modelo: str = ""

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


class MotorAuto:
    """Estado e ciclo do motor. Thread unica, com trava de concorrencia.

    MULTI-CORRETORA (2026-09-29)
    ===========================
    Ate aqui o motor so tinha `simbolo` e `timeframe` e chamava `_trade_order`
    do MT5 direto — a unica saida era o terminal. Os cinco adaptadores de
    execucao (mt5, binance, mexc, bybit, okx) ja existiam em
    `backend/*_execution.py`, e o `UniversalRouter.adapter_for` ja sabia
    escolher entre eles por corretora e mercado; o motor simplesmente nao
    usava esse caminho.

    Agora `broker` e `market` sao estado do motor, validados contra o
    catalogo de `broker_registry`. `market` vem de `MT5_MARKETS`
    (forex, metals, indices, stocks, commodities, bonds, crypto-spot,
    crypto-futures, other) para o MT5 e de `EXCHANGE_MARKETS`
    (crypto-spot, crypto-futures) para as exchanges.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self.limites = LimitesAuto()
        self.ativo = False
        self.simbolo = ""
        self.timeframe = ""
        # Corretora e classe de mercado do par que o motor opera. Vazio
        # significa MT5/forex, o unico caminho que funcionava ate aqui.
        self.broker = ""
        self.market = ""
        self.decisoes: list[Decisao] = []
        self.ciclo = 0
        # request_id por decisao, para idempotencia: o mesmo ciclo nao pode
        # gerar duas ordens se a resposta se perder e o motor repetir.
        self._vistos: dict[str, float] = {}
        # Multi-alvos: [{broker, market, symbol, timeframe}]. Um TF por
        # ativo: dois TFs do mesmo ativo na mesma janela gerariam duas
        # ordens do mesmo sinal — duplicata, nao diversificacao.
        self.alvos: list[dict[str, str]] = []

    # ------------------------------------------------------------- estado

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ativo": self.ativo,
                "simbolo": self.simbolo,
                "timeframe": self.timeframe,
                # Sem `or "mt5"`: com broker vazio o painel mostrava MT5, e o
                # `_loop` usava MT5 de verdade. O valor vazio e o honesto —
                # ainda nao foi escolhida nenhuma corretora.
                "broker": self.broker or "",
                "market": self.market or "",
                "alvos": [dict(a) for a in self.alvos],
                "ciclo": self.ciclo,
                "limites": asdict(self.limites),
                "decisoes": [d.para_dict() for d in self.decisoes[-20:]],
                "threads": threading.active_count(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    def configurar(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for campo in asdict(self.limites):
                if campo in payload and payload[campo] is not None:
                    try:
                        setattr(self.limites, campo, type(getattr(self.limites, campo))(payload[campo]))
                    except (TypeError, ValueError):
                        return {"ok": False, "error": f"valor invalido para {campo}"}
            ok, motivo = self.limites.valido()
            if not ok:
                return {"ok": False, "error": motivo}
            if payload.get("simbolo"):
                self.simbolo = str(payload["simbolo"]).upper()
            if payload.get("timeframe"):
                self.timeframe = str(payload["timeframe"]).upper()
            # Corretora e mercado: validados contra o catalogo, nao aceitos
            # como texto livre. Mandar "binance" com "metals" nao existe e
            # falharia so na hora do envio, depois de um ciclo inteiro de
            # inferencia.
            if payload.get("broker"):
                from backend.broker_registry import get_broker

                broker = str(payload["broker"]).strip().lower()
                definicao = get_broker(broker)
                if definicao is None:
                    return {
                        "ok": False,
                        "error": f"corretora desconhecida: {broker}",
                    }
                if not definicao.execution:
                    return {
                        "ok": False,
                        "error": f"{definicao.label} nao tem execucao habilitada no catalogo",
                    }
                self.broker = broker
            if payload.get("market"):
                from backend.broker_registry import normalize_market

                self.market = normalize_market(str(payload["market"]))
            # A classe de mercado precisa existir NA CORRETORA escolhida. Binance
            # so faz cripto (spot e futuros); MT5 faz forex, metals, indices e
            # mais. Aceitar "binance + metals" deixaria o operador descobrir o
            # erro so na hora do envio, depois de um ciclo inteiro de inferencia.
            if self.broker and self.market:
                from backend.broker_registry import get_broker

                definicao = get_broker(self.broker)
                if definicao is not None and definicao.markets:
                    if self.market not in definicao.markets:
                        return {
                            "ok": False,
                            "error": (
                                f"{definicao.label} nao opera em '{self.market}'. "
                                f"Mercados desta corretora: {', '.join(definicao.markets)}"
                            ),
                            "markets": list(definicao.markets),
                        }
            return {
                "ok": True,
                "limites": asdict(self.limites),
                "broker": self.broker or "",
                "market": self.market or "",
                "alvos": [dict(a) for a in self.alvos],
            }

    def configurar_alvos(self, alvos: list[dict[str, Any]]) -> dict[str, Any]:
        """Define os alvos operacionais. Um TF por ativo, sem duplicar.

        Cada alvo e {broker, market, symbol, timeframe}, validado contra o
        catalogo. Dois alvos com mesmo (broker, symbol, timeframe) sao a
        mesma operacao — o segundo e recusado. Timeframes diferentes do
        MESMO ativo na MESMA corretora sao recusados: o sinal se repetiria
        em duas janelas e viraria duas ordens do mesmo modelo.
        """
        from backend.broker_registry import get_broker, normalize_market

        if not isinstance(alvos, list) or not alvos:
            return {"ok": False, "error": "informe ao menos um alvo {broker, market, symbol, timeframe}"}
        normalizados: list[dict[str, str]] = []
        vistos: set[str] = set()
        for item in alvos:
            if not isinstance(item, dict):
                return {"ok": False, "error": "cada alvo precisa ser {broker, market, symbol, timeframe}"}
            broker = str(item.get("broker") or "").strip().lower()
            market = normalize_market(str(item.get("market") or ""))
            symbol = str(item.get("symbol") or "").strip().upper()
            timeframe = str(item.get("timeframe") or "").strip().upper()
            if not broker or not market or not symbol or not timeframe:
                return {"ok": False, "error": f"alvo incompleto: {item}"}
            definicao = get_broker(broker)
            if definicao is None:
                return {"ok": False, "error": f"corretora desconhecida: {broker}"}
            if not definicao.execution:
                return {"ok": False, "error": f"{definicao.label} nao tem execucao no catalogo"}
            if market not in definicao.markets:
                return {"ok": False, "error": f"{definicao.label} nao opera em '{market}'"}
            chave = f"{broker}:{symbol}:{timeframe}"
            if chave in vistos:
                return {"ok": False, "error": f"alvo duplicado: {chave}"}
            vistos.add(chave)
            # Mesmo ativo na mesma corretora em outro TF: o par (broker,
            # symbol) ja apareceu com timeframe diferente — duplicata de sinal.
            for outro in normalizados:
                if outro["broker"] == broker and outro["symbol"] == symbol:
                    return {"ok": False, "error": (
                        f"{symbol} em {broker} ja opera em {outro['timeframe']}: "
                        "um TF por ativo, sem duplicar sinal"
                    )}
            normalizados.append({"broker": broker, "market": market,
                                 "symbol": symbol, "timeframe": timeframe})
        with self._lock:
            self.alvos = normalizados
        return {"ok": True, "alvos": [dict(a) for a in normalizados]}

    def ciclo_alvos(
        self,
        inferir: Callable[[str, str], Any],
        enviar: Callable[[dict[str, Any]], dict[str, Any]],
        risk_state: Callable[[], dict[str, Any]],
    ) -> list[Decisao]:
        """Um ciclo por alvo, sem duplicar. Falha de um nao derruba os outros."""
        with self._lock:
            alvos = [dict(a) for a in self.alvos]
        if not alvos:
            return [self.ciclo_unico(inferir, enviar, risk_state)]
        resultados: list[Decisao] = []
        for alvo in alvos:
            with self._lock:
                self.simbolo = alvo["symbol"]
                self.timeframe = alvo["timeframe"]
                self.broker = alvo["broker"]
                self.market = alvo["market"]
            try:
                resultados.append(self.ciclo_unico(inferir, enviar, risk_state))
            except Exception as exc:
                resultados.append(self._registrar(Decisao(
                    datetime.now(timezone.utc).isoformat(), alvo["symbol"],
                    alvo["timeframe"], False, f"alvo falhou sem derrubar os outros: {exc}")))
        return resultados

    def ligar(self) -> dict[str, Any]:
        ok, motivo = self.limites.valido()
        if not ok:
            return {"ok": False, "error": motivo}
        # thread nascia e quebrava em toda iteracao: `_trava_instrumento`
        # devolve cedo com simbolo vazio, `_mt5_candles("", "", 600)` recusa, e
        # o operador via so "erro no ciclo" sem descobrir que faltava escolher
        # o ativo. Ligar sem ativo nao tem sentido, entao agora e recusado na
        # porta, com motivo.
        if not str(self.simbolo or "").strip():
            return {
                "ok": False,
                "error": "escolha o ativo (simbolo) e o timeframe antes de ligar a operacao automatica",
            }
        if not str(self.timeframe or "").strip():
            return {"ok": False, "error": "escolha o timeframe antes de ligar a operacao automatica"}
        # Corretora tambem e obrigatoria, pelo mesmo motivo do ativo: sem ela o
        # motor nao tem para onde mandar a ordem, e descobrir isso no meio de
        # um ciclo significa inferencia, risco e sizing jogados fora. Sem o
        # default "mt5", que era a mentira que o painel contava.
        if not str(self.broker or "").strip():
            return {
                "ok": False,
                "error": "escolha a corretora antes de ligar a operacao automatica: "
                         "nenhuma corretora e caminho padrao",
            }
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return {"ok": True, "status": "ja ligado"}
            self._parar.clear()
            self.ativo = True
            self._thread = threading.Thread(target=self._loop, name="xau-motor-auto", daemon=True)
            self._thread.start()
            return {"ok": True, "status": "ligado"}

    def desligar(self) -> dict[str, Any]:
        with self._lock:
            self.ativo = False
        self._parar.set()
        return {"ok": True, "status": "desligado"}
    # -------------------------------------------------------------- ciclo

    def _registrar(self, decisao: Decisao) -> Decisao:
        with self._lock:
            self.decisoes.append(decisao)
            # Janela curta: o painel mostra o que aconteceu agora, nao um
            # historico que so ocupa espaco.
            if len(self.decisoes) > 100:
                del self.decisoes[:-100]
        return decisao

    def ciclo_unico(
        self,
        inferir: Callable[[str, str], Any],
        enviar: Callable[[dict[str, Any]], dict[str, Any]],
        risk_state: Callable[[], dict[str, Any]],
    ) -> Decisao:
        """Executa UM ciclo. Exposto para teste e para execucao sob demanda.

        Todo motorauto precisa poder rodar "uma vez" sem depender de thread:
        e assim que se testa, e assim que o operador dispara na mao.
        """
        agora = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.ciclo += 1
            limites = asdict(self.limites)
            simbolo, timeframe = self.simbolo, self.timeframe
        # Nome do artefato que decides este ciclo. Comeca vazio e so e
        # preenchido DEPOIS da inferencia — uma decisao anterior a ela nao tem
        # modelo, e mostrar o do ciclo passado seria mentira de novo.
        modelo_ciclo = ""

        # 1. Risco real do gateway. Se nao vier, nao opera: falha fechado.
        try:
            risco = risk_state()
        except Exception as exc:  # pragma: no cover
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False, f"risk_gate indisponivel: {exc}"))
        if not risco or not risco.get("ok"):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"risk_gate nao respondeu: {(risco or {}).get('error', 'sem dados')}"))

        # 2. Inferencia real. Sem inferencia, sem decisao.
        try:
            inf = inferir(simbolo, timeframe)
        except Exception as exc:  # pragma: no cover
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False, f"inferencia falhou: {exc}"))

        if not getattr(inf, "disponivel", False):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"sem inferencia: {getattr(inf, 'motivo', 'motivo desconhecido')}"))

        sinal = getattr(inf, "signal", "NEUTRAL")
        confianca = float(getattr(inf, "confianca", 0.0) or 0.0)
        edge = getattr(inf, "edge", None)
        atr = float(getattr(inf, "atr", 0.0) or 0.0)
        preco = float(getattr(inf, "price", 0.0) or 0.0)
        # LIDO DA INFERENCIA, que por sua vez leu do `.meta.json`. E o unico
        # lugar em que o nome do modelo pode ser verdadeiro.
        modelo_ciclo = str(getattr(inf, "modelo", "") or "")

        # 3. O modelo precisa ter edge e confianca minima.
        # Modo simples: sem travas de confianca/edge/perda — o operador
        # decidiu o lote e as protecoes; o risk_gate do gateway limita.
        simples = bool(limites.get("lote")) and bool(limites.get("sl_preco")) and bool(limites.get("tp_preco"))
        if not simples and edge is not None and float(edge) < float(limites["edge_minimo"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"edge {float(edge):+.4f} abaixo do minimo {float(limites['edge_minimo']):+.4f}",
                sinal, confianca, edge, modelo=modelo_ciclo))
        if not simples and confianca < float(limites["confianca_minima"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"confianca {confianca:.1f}% abaixo do minimo {float(limites['confianca_minima']):.1f}%",
                sinal, confianca, edge, modelo=modelo_ciclo))
        if sinal not in ("BUY", "SELL"):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                "modelo em NEUTRAL", sinal, confianca, edge, modelo=modelo_ciclo))
        if atr <= 0 or preco <= 0:
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                "sem ATR ou preco real para dimensionar protecao", sinal, confianca, edge, modelo=modelo_ciclo))

        # 4. Limites de exposicao vindos do risk_gate (modo avancado; no
        # simples o risk_gate do gateway continua valendo no envio).
        if not simples and int(risco.get("open_positions", 0)) >= int(limites["max_posicoes"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"ja ha {risco.get('open_positions')} posicoes (max {limites['max_posicoes']})",
                sinal, confianca, edge, modelo=modelo_ciclo))
        if not simples and int(risco.get("daily_trades", 0)) >= int(limites["max_operacoes_dia"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"limite diario de {limites['max_operacoes_dia']} operacoes atingido",
                sinal, confianca, edge, modelo=modelo_ciclo))

        # 5. Tamanho e protecao. Simples: lote e precos do painel, com
        # coerencia por lado (BUY: SL < preco < TP). Avancado: banca/risco/ATR.
        if simples:
            volume = round(float(limites["lote"]), 2)
            sl, tp = round(float(limites["sl_preco"]), 2), round(float(limites["tp_preco"]), 2)
            if volume <= 0:
                return self._registrar(Decisao(
                    agora, simbolo, timeframe, False, "lote zerado", sinal, confianca, edge, modelo=modelo_ciclo))
            if sinal == "BUY" and not (sl < preco < tp):
                return self._registrar(Decisao(
                    agora, simbolo, timeframe, False,
                    f"para BUY exija SL < preco < TP (SL {sl}, preco {preco}, TP {tp})",
                    sinal, confianca, edge, modelo=modelo_ciclo))
            if sinal == "SELL" and not (tp < preco < sl):
                return self._registrar(Decisao(
                    agora, simbolo, timeframe, False,
                    f"para SELL exija TP < preco < SL (TP {tp}, preco {preco}, SL {sl})",
                    sinal, confianca, edge, modelo=modelo_ciclo))
            risco_moeda = 0.0
            distancia = abs(preco - sl)
        else:
            sl = preco - atr * float(limites["sl_atr"]) if sinal == "BUY" else preco + atr * float(limites["sl_atr"])
            tp = preco + atr * float(limites["tp_atr"]) if sinal == "BUY" else preco - atr * float(limites["tp_atr"])
            distancia = abs(preco - sl)
            if distancia <= 0:
                return self._registrar(Decisao(
                    agora, simbolo, timeframe, False, "Stop Loss calculou zero", sinal, confianca, edge, modelo=modelo_ciclo))
            risco_moeda = float(limites["banca"]) * float(limites["risco_por_trade_pct"]) / 100.0
            volume = risco_moeda / distancia
        # O gateway recusa acima de 0.10 e o volume do MT5 tem degraus. O
        # motor respeita o teto em vez de descobrir a recusa na ordem.
        # Piso de 0.01 (lote minimo): conta de $1 calcula volume fracionario
        # que arredonda para zero — sem o piso, banca pequena nunca opera.
        volume = min(volume, 0.10)
        if 0 < volume < 0.01:
            volume = 0.01
        if volume <= 0:
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False, "volume calculado zero", sinal, confianca, edge, modelo=modelo_ciclo))
        # Arredonda para 2 casas: o MT5 so aceita volume com passo do simbolo.
        volume = round(volume, 2)

        # 6. Idempotencia: um ciclo por slot de tempo, sem repetir ordem.
        # O slot inclui a corretora: o mesmo ativo na MEXC e no MT5 na
        # mesma janela sao duas operacoes legitimas; repetir o MESMO
        # (broker, ativo, TF) na mesma janela e duplicata e nao envia.
        with self._lock:
            _broker_slot = str(self.broker or "").strip().lower()
        _intervalo = max(1, int(limites.get("intervalo_minutos") or 0))
        slot = f"{_broker_slot}:{simbolo}:{timeframe}:{int(time.time() // (_intervalo * 60))}"
        with self._lock:
            if slot in self._vistos:
                return self._registrar(Decisao(
                    agora, simbolo, timeframe, False,
                    "ciclo ja processado nesta janela", sinal, confianca, edge, modelo=modelo_ciclo))
            self._vistos[slot] = time.time()
            if len(self._vistos) > 500:
                corte = time.time() - 86400
                self._vistos = {k: v for k, v in self._vistos.items() if v >= corte}

        # 7. Envio pelo caminho de ordem do gateway (que revalida tudo).
        #
        # NOMES CANONICOS DO CONTRATO, NAO O VOCABULARIO DO PAINEL
        # ============================================================
        # Aqui usava `volume`/`sl`/`tp`. O `UniversalOrderRequest` le
        # `quantity`/`stop_loss`/`take_profit`, entao `quantity` chegava vazio e
        # TODA ordem morria com "symbol e quantity sao obrigatorios" — visivel
        # na tela como "envio falhou". Nao era conta, corretora ou EA: era
        # desacamento de nome.
        #
        # O contrato agora aceita os dois nomes (ver `universal_contracts`), mas
        # o motor envia o canonico de proposito: dois lugares falando o mesmo
        # idioma e o que impede o desacamento de voltar.
        #
        # ALIAS POR CORRETORA: a decisao e do MODELO (`XAUUSD`), mas a ordem
        # vai com o simbolo que a corretora entende (`GOLD` na XM). O mapa
        # e configuracao do operador (`symbol_aliases.json`), nunca codigo.
        with self._lock:
            _broker_envio = str(self.broker or "").strip().lower()
        try:
            from backend.symbol_aliases import para_corretora as _para_corretora

            simbolo_envio = _para_corretora(_broker_envio, simbolo) or simbolo
        except Exception:
            simbolo_envio = simbolo
        payload = {
            "symbol": simbolo_envio,
            "side": sinal,
            "quantity": volume,
            "stop_loss": round(sl, 2),
            "take_profit": round(tp, 2),
            "confirm": True,
            "request_id": f"auto-{slot}",
            "origin": "motor_auto",
            "model": getattr(inf, "modelo", ""),
            "confidence": confianca,
            "edge": edge,
        }
        try:
            resultado = enviar(payload)
        except Exception as exc:  # pragma: no cover
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False, f"envio falhou: {exc}",
                sinal, confianca, edge, volume, risco_moeda, round(sl, 2), round(tp, 2),
                modelo=modelo_ciclo))

        ok = bool(resultado.get("ok"))
        return self._registrar(Decisao(
            agora, simbolo, timeframe, ok,
            "ordene enviada ao gateway" if ok else str(resultado.get("error") or resultado.get("comment") or "recusada"),
            sinal, confianca, edge, volume, risco_moeda, round(sl, 2), round(tp, 2), resultado,
            modelo=modelo_ciclo))

    def _trava_instrumento(self) -> None:
        """RECUSA o ciclo se o modelo nao foi treinado para este ativo.

        POR QUE ISTO EXISTE
        ===================
        O motor aceita `simbolo` e `timeframe` configuraveis e chamava
        `inferir(self.simbolo, ...)` sem checar nada. O unico modelo treinado
        e XAUUSD H1: com o motor em `BTCUSDT`, a funcao carregava o modelo de
        ouro, devolvia uma confianca e o motor ENVIAVA a ordem. Um modelo de
        ouro decidindo sobre Bitcoin e exatamente o modo de falha que esvazia
        conta.

        Aqui a recusa e silenciosa e explicita: nenhuma ordem e gerada, e o
        motivo aparece no historico de decisoes. Nao e aviso — e bloqueio.
        """
        simbolo = str(self.simbolo or "").upper()
        if not simbolo:
            return
        try:
            from backend import ai_inference
            modelo, meta = ai_inference._carregar(simbolo, self.timeframe)
        except Exception:
            return
        if modelo is None:
            self._registrar(Decisao(
                datetime.now(timezone.utc).isoformat(), self.simbolo, self.timeframe,
                False, f"sem modelo carregado para {self.timeframe}; nada foi enviado"))
            raise RuntimeError(f"modelo ausente para {self.timeframe}")
        treino = str(meta.get("symbol") or "").upper()
        # Mesmo ativo em quote de outra corretora (MEXC: `BTCUSDT`, modelo:
        # `BTCUSD`): comparacao pela base, sem lista de ativos no codigo.
        try:
            from backend.ai_inference import mesmo_ativo as _mesmo_ativo
            _igual = _mesmo_ativo(treino, simbolo)
        except Exception:
            _igual = (treino == simbolo)
        if treino and not _igual:
            self._registrar(Decisao(
                datetime.now(timezone.utc).isoformat(), self.simbolo, self.timeframe,
                False,
                f"modelo {treino} treinado para outro ativo; recusado em {simbolo}"))
            raise RuntimeError(
                f"modelo {treino} nao pode operar {simbolo} (treinado em {treino})")

    def _loop(self) -> None:  # pragma: no cover - thread de producao
        """Ciclo periodico pela CORRETORA E MERCADO CONFIGURADOS.

        POR QUE ESTE METODO MUDOU (2026-09-30)
        =======================================
        Antes importava `mt5_gateway` direto e ignorava `self.broker`:

            def risk_state():  from backend.mt5_gateway import _risk_state, _mt5
            def enviar(...):   from backend.mt5_gateway import _trade_order
            resposta = _mt5_candles(self.simbolo, self.timeframe, 600)

        O `configurar()` validava a corretora contra o catalogo, o `snapshot()`
        devolvia a corretora escolhida e o painel mostrava isso — mas o envio
        ia para o MT5 de qualquer jeito. Escolher Binance e ver "Binance" na
        tela era mentira sobre para onde o dinheiro estava indo.

        Agora as tres dependencias (candles, risco e envio) sao resolvidas por
        `(broker, market)`, e o ENVIO continua sendo do `UniversalRouter` com
        `intent_log` — o motor nao tem caminho proprio de ordem.
        """
        from backend import ai_inference
        from backend.market_access import candles as candles_da_corretora
        from backend.market_access import estado_de_risco
        from backend.universal_router import UniversalRouter, UniversalRouterError

        router = UniversalRouter()

        def escopo() -> tuple[str, str]:
            """Corretora e mercado do ciclo, sem default.

            `self.broker` vazio e recusa, nao "MT5". O `ligar()` ja exige ativo
            e timeframe; falta exigir a corretora, e a diferenca entre exigir
            aqui e descobrir no envio e um ciclo inteiro de inferencia jogado
            fora.
            """
            broker = str(self.broker or "").strip().lower()
            market = str(self.market or "").strip().lower()
            if not broker:
                raise RuntimeError(
                    "escolha a corretora antes de ligar a operacao automatica: "
                    "nenhuma corretora e padrao"
                )
            return broker, market

        def conta_da_corretora(broker: str, market: str) -> str:
            """Descobre a conta ativa da corretora escolhida.

            POR QUE ISTO EXISTE
            -------------------
            O envio exigia `account_id` e o motor mandava `""` sempre
            (`payload.get("account_id", "")`). Toda ordem de operacao
            automatica morria em `UniversalOrderRequest.from_payload` com
            "account_id e obrigatorio" — depois de gastar um ciclo inteiro de
            inferencia. O painel nao tinha de onde pegar o valor: a tela
            mostrava corretora e mercado, e nao a conta.

            A resolucao fica aqui, e nao no painel, porque quem decide qual
            conta opera e o proprio motor: ele ja sabe a corretora e o
            mercado do ciclo.

            O QUE NAO MUDOU
            ---------------
            Nenhuma conta e inventada. Se houver mais de uma ativa para a
            mesma corretora e mercado, `resolve_connection` recusa com
            "account_id e obrigatorio quando ha mais de uma conta ativa" —
            e essa recusa e o comportamento correto: escolher entre duas
            contas do mesmo par e uma decisao do operador. O motor so
            escolhe sozinho quando a escolha e unica.
            """
            from backend.connection_store import resolve_connection

            try:
                conta = resolve_connection("", broker, market)
            except LookupError as exc:
                raise RuntimeError(str(exc)) from exc
            account_id = str(conta.get("id", "")).strip()
            if not account_id:
                raise RuntimeError(
                    f"a conexao ativa de {broker} nao tem identificador de conta; "
                    "cadastre a conexao novamente"
                )
            return account_id

        def enviar(payload: dict[str, Any]) -> dict[str, Any]:
            """Ordem pelo UniversalRouter, com intent_log e gate da corretora.

            A traducao vive em `pedido_para_router`, no modulo, porque ela e o
            ponto onde o payload do painel vira pedido do router — e onde o
            `volume`/`quantity` ja desacou duas vezes.
            """
            broker, market = escopo()
            pedido = pedido_para_router(
                payload, broker, market, conta_da_corretora(broker, market))
            return router.execute(pedido, explicit_authorization=True)

        while not self._parar.is_set():
            try:
                import pandas as pd

                broker, market = escopo()
                self._trava_instrumento()

                # `candles()` ja devolve a serie no formato do treino e ja
                # recusa com motivo quando a corretora nao tem dado. A traducao
                # MT5 -> treino (que ja falhou em tres lugares isolados) fica
                # em um unico ponto, dentro dele. O simbolo pedido e o da
                # CORRETORA (alias: `GOLD` na XM); a inferencia abaixo usa o
                # do MODELO (`XAUUSD`).
                from backend.symbol_aliases import para_corretora as _para_corretora

                linhas = candles_da_corretora(
                    broker, market, _para_corretora(broker, self.simbolo) or self.simbolo,
                    self.timeframe, 600,
                )
                df = linhas if hasattr(linhas, "empty") else pd.DataFrame(linhas)
                if df.empty:
                    raise RuntimeError(
                        f"serie de {self.simbolo} {self.timeframe} em {broker} "
                        "ficou vazia depois da conversao para o formato do treino"
                    )
                inf = ai_inference.inferir(self.simbolo, df, self.timeframe)
                self.ciclo_unico(
                    lambda s, t: inf,
                    enviar,
                    lambda: estado_de_risco(broker, market),
                )
            except (UniversalRouterError, RuntimeError, ValueError) as exc:
                # O loop nao pode morrer por um erro pontual, mas esconder a
                # causa e o que deixou o bug invisivel: o operador via
                # "erro no ciclo" por horas sem saber o porquep. O tipo e a
                # mensagem vao para o historico de decisoes.
                self._registrar(Decisao(
                    datetime.now(timezone.utc).isoformat(), self.simbolo, self.timeframe,
                    False, f"erro no ciclo: {type(exc).__name__}: {exc}"))
            self._parar.wait(max(60, self.limites.intervalo_minutos * 60))


# Instancia unica do processo.
motor = MotorAuto()
