"""
XAU_AI_PRO - Trade Gate Test
V1.0

Roda em estado TEMPORARIO (tempfile) para nao tocar
em risk_state.json de producao.

Cobre:
1. Gate sem RiskManager -> permitido
2. Posicao duplicada -> bloqueado
3. Debounce -> bloqueia no mesmo candle
4. Debounce libera no candle seguinte
5. RiskManager equity limpa -> permite
6. RiskManager 4 perdas -> pausa ativa
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from risk.risk_manager import (
    RiskConfig,
    RiskManager,
)

from core.trade_gate import (
    TradeGate,
    TradeGateConfig,
)


def run() -> None:
    print("=" * 70)
    print(" XAU_AI_PRO TRADE GATE - TESTE")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # 1. GATE SEM RISK MANAGER
    # --------------------------------------------------------

    gate = TradeGate(
        config=TradeGateConfig(
            allow_when_no_risk_manager=True,
        )
    )

    decision = gate.can_trade(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.7,
        bar_index=10,
    )

    print("[1] Gate sem risk_manager:")
    print("    ", decision.to_dict())
    print()

    # --------------------------------------------------------
    # 2. POSICAO DUPLICADA
    # --------------------------------------------------------

    gate.register_entry(
        symbol="XAUUSDc",
        side="BUY",
        lot=0.10,
        bar_index=10,
    )

    decision = gate.can_trade(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.7,
        bar_index=10,
    )

    print("[2] Gate com posicao aberta (mesmo candle):")
    print("    ", decision.to_dict())
    print()

    # --------------------------------------------------------
    # 3. DEBOUNCE
    # --------------------------------------------------------

    gate.register_exit(
        symbol="XAUUSDc",
        bar_index=10,
    )

    decision = gate.can_trade(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.7,
        bar_index=10,
    )

    print("[3] Gate com debounce (mesmo candle apos saida):")
    print("    ", decision.to_dict())
    print()

    # --------------------------------------------------------
    # 4. CANDLE SEGUINTE
    # --------------------------------------------------------

    decision = gate.can_trade(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.7,
        bar_index=11,
    )

    print("[4] Gate apos debounce (candle seguinte):")
    print("    ", decision.to_dict())
    print()

    # --------------------------------------------------------
    # 5. RISK MANAGER - EQUITY LIMPA
    # --------------------------------------------------------

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_risk = Path(tmpdir) / "risk_state.json"

        risk = RiskManager(RiskConfig(state_file=tmp_risk))

        risk.initialize(equity=10000.0, base_lot=0.10)

        gate_with_risk = TradeGate(
            risk_manager=risk,
            config=TradeGateConfig(
                allow_when_no_risk_manager=False,
            ),
        )

        decision = gate_with_risk.can_trade(
            symbol="XAUUSDc",
            signal="BUY",
            confidence=0.7,
            bar_index=20,
        )

        print("[5] Gate com RiskManager (equity limpa):")
        print("    ", decision.to_dict())
        print()

        # --------------------------------------------------------
        # 6. RISK MANAGER - 4 PERDAS
        # --------------------------------------------------------

        for _ in range(4):
            risk.record_trade(
                symbol="XAUUSDc",
                signal="BUY",
                lot=0.10,
                pnl=-100.0,
            )

        decision = gate_with_risk.can_trade(
            symbol="XAUUSDc",
            signal="BUY",
            confidence=0.7,
            bar_index=25,
        )

        print("[6] Gate com RiskManager (apos 4 perdas):")
        print("    ", decision.to_dict())
        print()

    print("=" * 70)
    print(" OK - risk_state.json de producao NAO foi tocado")
    print("=" * 70)


if __name__ == "__main__":
    run()
