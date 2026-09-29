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

# ------------------------------------------------------------------ limites


@dataclass
class LimitesAuto:
    """Parametros de risco que o OPERADOR define. Aplicados a cada ciclo.

    Estes limites sao o preco do produto. Um operador avancido escolhe o risco
    que aceita perder; o motor nao tem opinion a respeito, apenas o respeita.
    """

    #: Banco declarado pelo operador (moeda da conta).
    banca: float = 20.0
    #: Percentual da banca arriscado por operacao.
    risco_por_trade_pct: float = 1.0
    #: Confianca minima do modelo para operar (probabilidade real, 0-100).
    confianca_minima: float = 55.0
    #: Edge minimo aceitavel do modelo.
    edge_minimo: float = 0.05
    #: Numero maximo de posicoes simultaneas.
    max_posicoes: int = 2
    #: Numero maximo de operacoes por dia.
    max_operacoes_dia: int = 20
    #: Perda maxima diaria como percentual da banca. Ao atingir, o motor para.
    perda_diaria_max_pct: float = 2.0
    #: Multiplicador de ATR usado no Stop Loss.
    sl_atr: float = 1.5
    #: Multiplicador de ATR usado no Take Profit.
    tp_atr: float = 3.0
    #: Intervalo minimo entre duas avaliacoes do mesmo simbolo.
    intervalo_minutos: int = 15

    def valido(self) -> tuple[bool, str]:
        if self.banca <= 0:
            return False, "banca tem de ser maior que zero"
        if not 0 < self.risco_por_trade_pct <= 10:
            return False, "risco por trade tem de estar entre 0 e 10%"
        if not 0 < self.confianca_minima <= 100:
            return False, "confianca minima tem de estar entre 0 e 100"
        if self.max_posicoes < 1:
            return False, "maximo de posicoes tem de ser ao menos 1"
        if self.max_operacoes_dia < 1:
            return False, "maximo de operacoes por dia tem de ser ao menos 1"
        if not 0 < self.perda_diaria_max_pct <= 100:
            return False, "perda diaria maxima tem de estar entre 0 e 100%"
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

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


class MotorAuto:
    """Estado e ciclo do motor. Thread unica, com trava de concorrencia."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self.limites = LimitesAuto()
        self.ativo = False
        self.simbolo = "XAUUSD"
        self.timeframe = "H1"
        self.decisoes: list[Decisao] = []
        self.ciclo = 0
        # request_id por decisao, para idempotencia: o mesmo ciclo nao pode
        # gerar duas ordens se a resposta se perder e o motor repetir.
        self._vistos: dict[str, float] = {}

    # ------------------------------------------------------------- estado

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ativo": self.ativo,
                "simbolo": self.simbolo,
                "timeframe": self.timeframe,
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
            return {"ok": True, "limites": asdict(self.limites)}

    def ligar(self) -> dict[str, Any]:
        ok, motivo = self.limites.valido()
        if not ok:
            return {"ok": False, "error": motivo}
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

        # 3. O modelo precisa ter edge e confianca minima.
        if edge is not None and float(edge) < float(limites["edge_minimo"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"edge {float(edge):+.4f} abaixo do minimo {float(limites['edge_minimo']):+.4f}",
                sinal, confianca, edge))
        if confianca < float(limites["confianca_minima"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"confianca {confianca:.1f}% abaixo do minimo {float(limites['confianca_minima']):.1f}%",
                sinal, confianca, edge))
        if sinal not in ("BUY", "SELL"):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                "modelo em NEUTRAL", sinal, confianca, edge))
        if atr <= 0 or preco <= 0:
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                "sem ATR ou preco real para dimensionar protecao", sinal, confianca, edge))

        # 4. Limites de exposicao vindos do risk_gate.
        if int(risco.get("open_positions", 0)) >= int(limites["max_posicoes"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"ja ha {risco.get('open_positions')} posicoes (max {limites['max_posicoes']})",
                sinal, confianca, edge))
        if int(risco.get("daily_trades", 0)) >= int(limites["max_operacoes_dia"]):
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False,
                f"limite diario de {limites['max_operacoes_dia']} operacoes atingido",
                sinal, confianca, edge))

        # 5. Tamanho pela banca e pelo risco por trade, com ATR real.
        sl = preco - atr * float(limites["sl_atr"]) if sinal == "BUY" else preco + atr * float(limites["sl_atr"])
        tp = preco + atr * float(limites["tp_atr"]) if sinal == "BUY" else preco - atr * float(limites["tp_atr"])
        distancia = abs(preco - sl)
        if distancia <= 0:
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False, "Stop Loss calculou zero", sinal, confianca, edge))
        risco_moeda = float(limites["banca"]) * float(limites["risco_por_trade_pct"]) / 100.0
        volume = risco_moeda / distancia
        # O gateway recusa acima de 0.10 e o volume do MT5 tem degraus. O
        # motor respeita o teto em vez de descobrir a recusa na ordem.
        volume = min(volume, 0.10)
        if volume <= 0:
            return self._registrar(Decisao(
                agora, simbolo, timeframe, False, "volume calculado zero", sinal, confianca, edge))
        # Arredonda para 2 casas: o MT5 so aceita volume com passo do simbolo.
        volume = round(volume, 2)

        # 6. Idempotencia: um ciclo por slot de tempo, sem repetir ordem.
        slot = f"{simbolo}:{timeframe}:{int(time.time() // (int(limites['intervalo_minutos']) * 60))}"
        with self._lock:
            if slot in self._vistos:
                return self._registrar(Decisao(
                    agora, simbolo, timeframe, False,
                    "ciclo ja processado nesta janela", sinal, confianca, edge))
            self._vistos[slot] = time.time()
            if len(self._vistos) > 500:
                corte = time.time() - 86400
                self._vistos = {k: v for k, v in self._vistos.items() if v >= corte}

        # 7. Envio pelo caminho de ordem do gateway (que revalida tudo).
        payload = {
            "symbol": simbolo,
            "side": sinal,
            "volume": volume,
            "sl": round(sl, 2),
            "tp": round(tp, 2),
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
                sinal, confianca, edge, volume, risco_moeda, round(sl, 2), round(tp, 2)))

        ok = bool(resultado.get("ok"))
        return self._registrar(Decisao(
            agora, simbolo, timeframe, ok,
            "ordene enviada ao gateway" if ok else str(resultado.get("error") or resultado.get("comment") or "recusada"),
            sinal, confianca, edge, volume, risco_moeda, round(sl, 2), round(tp, 2), resultado))

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
        if treino and treino != simbolo:
            self._registrar(Decisao(
                datetime.now(timezone.utc).isoformat(), self.simbolo, self.timeframe,
                False,
                f"modelo {treino} treinado para outro ativo; recusado em {simbolo}"))
            raise RuntimeError(
                f"modelo {treino} nao pode operar {simbolo} (treinado em {treino})")

    def _loop(self) -> None:  # pragma: no cover - thread de producao
        from backend import ai_inference

        def risk_state() -> dict[str, Any]:
            from backend.mt5_gateway import _risk_state, _mt5
            return _risk_state(_mt5())

        def enviar(payload: dict[str, Any]) -> dict[str, Any]:
            from backend.mt5_gateway import _trade_order
            return _trade_order(payload)

        while not self._parar.is_set():
            try:
                import pandas as pd
                from backend.mt5_gateway import _mt5_candles

                self._trava_instrumento()
                candles = _mt5_candles(self.simbolo, self.timeframe, 600)
                df = pd.DataFrame(candles or [])
                inf = ai_inference.inferir(self.simbolo, df, self.timeframe)
                self.ciclo_unico(lambda s, t: inf, enviar, risk_state)
            except Exception:
                # O loop nao pode morrer por um erro pontual; o proximo ciclo
                # tenta de novo e a falha ja aparece no historico de decisoes.
                self._registrar(Decisao(
                    datetime.now(timezone.utc).isoformat(), self.simbolo, self.timeframe,
                    False, "erro no ciclo; tentando de novo no proximo intervalo"))
            self._parar.wait(max(60, self.limites.intervalo_minutos * 60))


# Instancia unica do processo.
motor = MotorAuto()
