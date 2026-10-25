"""Barreira de risco comum aos adaptadores de corretoras.

FALHA FECHADA
-------------
`max_spread` e `max_notional` eram `None` por padrao, e a checagen era
`if limits.max_spread is not None and ...`: com o padrao, **a checagem era
pulada** e a trava ficava desligada sem ninguem perceber. Alem disso
`validate_trade` nunca recebia `spread`/`notional` de nenhum chamador.

Agora todo limite tem valor numerico e a checagen e sempre executada. Dado
ausente e falha fechada, nao aprovacao.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_volume: float = 0.10
    max_daily_loss_pct: float = 2.0
    #: Exposicao aberta como PERCENTUAL DA CAPACIDADE do risk_gate
    #: (`max_volume * max_positions`, ver `mt5_gateway._risk_state`). 100 =
    #: capacidade cheia; 0 = nada aberto.
    #:
    #: MEDIDO em 25/10/2026: era `5.0`, e os dois lados do MESMO dado
    #: discordavam (AGENTS.md §5). O produtor calcula `volume / capacidade *
    #: 100`, entao `5.0` significa "bloqueie ao abrir 5% da capacidade" — com
    #: capacidade de 0,5 lote, isso e **0,025 lote**, menos que tres posicoes
    #: minimas de 0,01. O motor abria duas ou tres posicoes e passava a
    #: responder "exposicao atingiu o limite de 5.0%" para sempre, mesmo com o
    #: operador tendo declarado `max_posicoes = 2`. O numero era um erro de
    #: unidade, nao uma trava de risco: `5.0` esta na escala de "porcento da
    #: CAPACIDADE", e nessa escala o teto natural e `100.0`. A perda diaria, o
    #: drawdown, o nocional e o volume por ordem continuam intactos.
    max_exposure_pct: float = 100.0
    max_positions: int = 5
    max_daily_trades: int = 20
    max_drawdown_pct: float = 15.0
    # Antes None (=> checagem pulada). 50 pontos cobre Ouro/Forex/Indices com
    # folga em condicoes normais e barra o spread de noticia ou horario morto.
    max_spread: float = 50.0
    # Nocional por operacao. 0.10 lote de XAU a ~4000 com contrato 100 = 40.000
    # de nocional; 100.000 barra Forex/Indice sem barrar Ouro.
    max_notional: float = 100_000.0
    withdrawals_enabled: bool = False


def validate_trade(
    *,
    volume: float,
    daily_loss_pct: float,
    exposure_pct: float,
    open_positions: int,
    daily_trades: int,
    drawdown_pct: float,
    spread: float | None = None,
    notional: float | None = None,
    limits: RiskLimits = RiskLimits(),
) -> None:
    """Rejeita uma operação que exceda qualquer limite local.

    `spread` e `notional` sao obrigatorios porque os limites existem. Enviar
    `None` e recusado com mensagem explicita: sem dado de risco, a decisao e
    nao aprovada.
    """
    values = (volume, daily_loss_pct, exposure_pct, drawdown_pct)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("métricas de risco devem ser finitas")
    if isinstance(open_positions, bool) or isinstance(daily_trades, bool):
        raise ValueError("contagens de risco devem ser inteiras")
    if not all(math.isfinite(float(value)) for value in (open_positions, daily_trades)):
        raise ValueError("contagens de risco devem ser finitas")
    if int(open_positions) != open_positions or int(daily_trades) != daily_trades:
        raise ValueError("contagens de risco devem ser inteiras")
    if open_positions < 0 or daily_trades < 0:
        raise ValueError("contagens de risco não podem ser negativas")
    if volume <= 0 or volume > limits.max_volume:
        raise ValueError(f"volume fora do limite: máximo {limits.max_volume}")
    if daily_loss_pct >= limits.max_daily_loss_pct:
        raise ValueError(f"perda diária atingiu o limite de {limits.max_daily_loss_pct}%")
    if exposure_pct >= limits.max_exposure_pct:
        raise ValueError(f"exposição atingiu o limite de {limits.max_exposure_pct}%")
    if open_positions >= limits.max_positions:
        raise ValueError(f"limite de {limits.max_positions} posições atingido")
    if daily_trades >= limits.max_daily_trades:
        raise ValueError(f"limite diário de {limits.max_daily_trades} operações atingido")
    if drawdown_pct >= limits.max_drawdown_pct:
        raise ValueError(f"drawdown atingiu o limite de {limits.max_drawdown_pct}%")
    if spread is None:
        raise ValueError("spread é obrigatório: a trava de spread não pode ser pulada")
    if not math.isfinite(float(spread)) or spread < 0:
        raise ValueError("spread deve ser um número finito e não negativo")
    if spread > limits.max_spread:
        raise ValueError(f"spread fora do limite: máximo {limits.max_spread}")
    if notional is None:
        raise ValueError("notional é obrigatório: a trava de nocional não pode ser pulada")
    if not math.isfinite(float(notional)) or notional < 0:
        raise ValueError("notional deve ser um número finito e não negativo")
    if notional > limits.max_notional:
        raise ValueError(f"notional fora do limite: máximo {limits.max_notional}")


def withdrawal_allowed() -> bool:
    return False
