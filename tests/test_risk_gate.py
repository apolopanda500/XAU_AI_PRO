import pytest

from backend.risk_gate import RiskLimits, validate_trade, withdrawal_allowed


def test_withdrawals_are_always_blocked():
    assert withdrawal_allowed() is False
    assert RiskLimits().withdrawals_enabled is False


# Metricas de uma operacao dentro de todos os limites: 0.01 lote, spread de 20
# pontos e nocional de 4.000 (0.01 x contrato 100 x preco 4.000).
BASE_RISK = {
    'volume': 0.01,
    'daily_loss_pct': 0.2,
    'exposure_pct': 1.0,
    'open_positions': 0,
    'daily_trades': 0,
    'drawdown_pct': 0.0,
    'spread': 20.0,
    'notional': 4_000.0,
}


def test_trade_within_limits_is_allowed():
    validate_trade(**BASE_RISK)


@pytest.mark.parametrize('overrides', [
    {'volume': 0.11},
    {'daily_loss_pct': 2},
    # A exposicao e medida como % da CAPACIDADE (0-100). O teto padrao e 100
    # (capacidade cheia); para provar a trava, o limite de 5% e declarado
    # explicitamente aqui — o teste mede a REGRA, nao o acidente de default.
    # Ver `test_exposicao_e_percentual_da_capacidade`.
    {'exposure_pct': 5, 'limits': RiskLimits(max_exposure_pct=5.0)},
    {'open_positions': 5},
    {'daily_trades': 20},
    {'drawdown_pct': 15},
    {'daily_trades': float('nan')},
    {'daily_trades': 1.5},
    {'open_positions': -1},
    {'spread': 51},
    {'notional': 100_001},
])
def test_trade_outside_limits_is_rejected(overrides):
    with pytest.raises(ValueError):
        validate_trade(**{**BASE_RISK, **overrides})


# --- fail-closed: trava presente nao pode ser pulada -------------------------
#
# Antes `max_spread` e `max_notional` eram `None` e a checagem era
# `if limits.max_spread is not None and ...`: com o padrao, as duas travas
# ficavam desligadas sem aviso. `None` e ausencia de dado, e ausencia de dado
# de risco e recusa, nao aprovacao.


def test_limites_de_spread_e_nocional_tem_valor_padrao():
    limites = RiskLimits()
    assert limites.max_spread is not None and limites.max_spread > 0
    assert limites.max_notional is not None and limites.max_notional > 0


def test_spread_ausente_e_recusado():
    with pytest.raises(ValueError, match='spread'):
        validate_trade(**{**BASE_RISK, 'spread': None})


def test_notional_ausente_e_recusado():
    with pytest.raises(ValueError, match='notional'):
        validate_trade(**{**BASE_RISK, 'notional': None})


def test_spread_negativo_ou_nan_e_recusado():
    with pytest.raises(ValueError):
        validate_trade(**{**BASE_RISK, 'spread': -1})
    with pytest.raises(ValueError):
        validate_trade(**{**BASE_RISK, 'spread': float('nan')})


def test_notional_negativo_ou_nan_e_recusado():
    with pytest.raises(ValueError):
        validate_trade(**{**BASE_RISK, 'notional': -1})
    with pytest.raises(ValueError):
        validate_trade(**{**BASE_RISK, 'notional': float('inf')})


def test_spread_zero_e_aceito():
    # Spread zero e legitimo em horario de pico; nao e erro de dado.
    validate_trade(**{**BASE_RISK, 'spread': 0.0})


# --- exposicao: % da capacidade, nao um teto magico de 5% --------------------
#
# MEDIDO em 25/10/2026: com `max_exposure_pct = 5.0` o motor parava em 0,025
# lote (5% de 0,5 de capacidade) e respondia "exposicao atingiu o limite de
# 5.0%" para sempre. Aqui ficam as duas provas: a capacidade cheia passa, e
# acima dela reprova.


def test_exposicao_e_percentual_da_capacidade():
    # 3 posicoes minimas (0,03 lote) = 6% da capacidade de 0,5: precisa PASSAR.
    # Era este o caso real que o motor recusava.
    validate_trade(**{**BASE_RISK, 'exposure_pct': 6.0})
    # Quase a capacidade cheia ainda passa; o teto `>= 100` fica para o teste
    # seguinte (quem barra volume e nocional e o proprio `max_volume`).
    validate_trade(**{**BASE_RISK, 'exposure_pct': 99.99})


def test_exposicao_acima_da_capacidade_e_recusada():
    with pytest.raises(ValueError, match='exposi'):
        validate_trade(**{**BASE_RISK, 'exposure_pct': 100.01})
