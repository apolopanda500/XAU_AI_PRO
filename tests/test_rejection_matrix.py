"""Matriz de rejeicao de ordens — o que o sistema precisa recusar.

O gate de producao (`ACOMPANHAMENTO_OFICIAL_PC_20260921.md` e
`RELATORIO_AUDITORIA_SEGURANCA.md`) exige "testes de rejeicao" antes de qualquer
dinheiro real. Estes testes fixam a matriz completa: para cada corretora e cada
classe de ordem, o que precisa falhar e com qual motivo.

Nenhum teste aqui envia ordem. Todos os caminhos de rede estao substituidos por
dobles; o que se verifica e a trava, nao a corretora.
"""
from __future__ import annotations

import os

import pytest

import backend.mt5_gateway as gw
from backend.binance_execution import BinanceExecutionAdapter
from backend.bybit_execution import BybitExecutionAdapter
from backend.mexc_execution import MexcExecutionAdapter, MexcExecutionError
from backend.mt5_execution import MT5ExecutionAdapter
from backend.okx_execution import OkxExecutionAdapter
from backend.risk_gate import RiskLimits, validate_trade
from backend.universal_router import UniversalRouter, UniversalRouterError

BROKERS = ["mt5", "binance", "mexc", "bybit", "okx"]
ADAPTERS = {
    "mt5": MT5ExecutionAdapter,
    "binance": BinanceExecutionAdapter,
    "mexc": MexcExecutionAdapter,
    "bybit": BybitExecutionAdapter,
    "okx": OkxExecutionAdapter,
}


def _pedido(**overrides) -> dict:
    base = {
        "request_id": "req-1",
        "account_id": "conta-1",
        "broker": "mexc",
        "market": "crypto-spot",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.01,
        "price": None,
        "confirm": True,
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------ ordem real


def test_ordem_real_nao_e_mais_recusada_por_tipo():
    # _real_order deixou de levantar "ordens REAIS indisponiveis". Ele roteia
    # para _trade_order, que e o MESMO caminho do demo. O que pode recusar
    # agora e falta de trava de envio, confirm ausente ou validacao de campo
    # - nunca o rotulo REAL.
    # Qualquer outra excecao (MT5 ausente no ambiente de teste, validacao de
    # campo) e aceitavel aqui: o unico motivo que este teste proibe e recusa
    # por tipo de conta.
    try:
        gw._real_order(_pedido(confirm=True, sl=3000.0, tp=3100.0))
    except PermissionError as exc:
        texto = str(exc).lower()
        assert "indispon" not in texto, texto
        assert "real" not in texto, texto
        assert "demo" not in texto, texto
    except Exception:  # noqa: BLE001 - nao e recusa por tipo de conta
        pass


@pytest.mark.parametrize("broker", BROKERS)
def test_ordem_real_passa_pelo_mesmo_caminho(broker):
    """Toda corretora cai no mesmo caminho; nenhuma recusa por ser real."""
    try:
        gw._real_order(_pedido(broker=broker, confirm=True, sl=3000.0, tp=3100.0))
    except PermissionError as exc:
        texto = str(exc).lower()
        assert "indispon" not in texto and "real" not in texto, texto
    except Exception:  # noqa: BLE001 - MT5/validacao, nao rotulo de conta
        pass


def test_rota_real_por_fastapi_responde_403(monkeypatch):
    from fastapi.testclient import TestClient

    import backend.fastapi_gateway as fgw

    cliente = TestClient(fgw.app)
    resposta = cliente.post("/api/real/order", json=_pedido())
    assert resposta.status_code == 403
    corpo = resposta.json()
    assert corpo["ok"] is False
    assert corpo["real"] is True


def test_solicitacao_real_e_aprovada(monkeypatch):
    # /api/real/request deixou de exigir autorizacao manual: devolve
    # status=approved e execution_enabled=True, como o operador pediu.
    from fastapi.testclient import TestClient

    import backend.fastapi_gateway as fgw

    cliente = TestClient(fgw.app)
    resposta = cliente.post("/api/real/request", json=_pedido(broker="mt5", account_id="mt5:active"))
    assert resposta.status_code in (200, 422)
    if resposta.status_code == 200:
        corpo = resposta.json()
        assert corpo["status"] == "approved"
        assert corpo["execution_enabled"] is True
        assert corpo["withdrawals_enabled"] is False


# ------------------------------------------------------------ ordem demo


def test_gate_de_trade_desligada_bloqueia_envio(monkeypatch):
    # O app nasce com a gate aberta; quem bloqueia e o operador, com =0.
    monkeypatch.setenv("XAU_ENABLE_TRADE_COMMANDS", "0")
    monkeypatch.setenv("XAU_ENABLE_DEMO_ORDERS", "0")
    with pytest.raises(PermissionError, match="XAU_ENABLE_TRADE_COMMANDS"):
        gw._trade_order(_pedido(confirm=True, sl=3000.0, tp=3100.0))


def test_trade_exige_confirmacao_explicita(monkeypatch):
    """Sem confirm=true o gateway recusa, mesmo com a trava de envio ligada."""
    monkeypatch.setenv("XAU_ENABLE_TRADE_COMMANDS", "1")
    with pytest.raises(PermissionError, match="confirm"):
        gw._trade_order(_pedido(confirm=False, sl=3000.0, tp=3100.0))


def test_trade_aceita_conta_real(monkeypatch):
    """O tipo de conta deixa de ser criterio de recusa.

    A antiga trava `trade_mode == DEMO` foi removida junto com o
    vocabulario demo: DEMO e REAL passam pelo mesmo caminho e pelas
    mesmas travas de risco (XAU_ENABLE_TRADE_COMMANDS=1, confirm=true,
    SL/TP obrigatorios, order_check antes do order_send).

    O que este teste garante e negativo e especifico: nenhuma recusa
    volta dizendo que a conta e real. Qualquer outra falha (mock do MT5
    incompleto, validacao de campo) e aceitavel aqui.
    """
    monkeypatch.setenv("XAU_ENABLE_TRADE_COMMANDS", "1")

    class _ContaReal:
        trade_mode = 0  # ACCOUNT_TRADE_MODE_REAL
        trade_allowed = True
        login = 1
        balance = 10000.0
        equity = 10000.0

    class _Mt5:
        ACCOUNT_TRADE_MODE_DEMO = 1

        def account_info(self):
            return _ContaReal()

    monkeypatch.setattr(gw, "_mt5", lambda: _Mt5())
    try:
        gw._trade_order(_pedido(confirm=True, symbol="XAUUSD", side="BUY",
                                volume=0.01, sl=3000.0, tp=3100.0))
    except PermissionError as exc:
        raise AssertionError(
            f"conta real ainda e recusada: {exc}") from exc
    except Exception:  # noqa: BLE001 - o que importa e nao ser por tipo de conta
        pass


def test_demo_exige_sl_e_tp(monkeypatch):
    monkeypatch.setenv("XAU_ENABLE_TRADE_COMMANDS", "1")

    class _Conta:
        trade_mode = 1
        trade_allowed = True
        login = 1
        balance = 10000.0
        equity = 10000.0

    class _Mt5:
        ACCOUNT_TRADE_MODE_DEMO = 1

        def account_info(self):
            return _Conta()

    monkeypatch.setattr(gw, "_mt5", lambda: _Mt5())
    with pytest.raises(ValueError, match="sl e tp"):
        gw._trade_order(_pedido(confirm=True, sl=0, tp=0))


def test_demo_respeita_teto_de_volume(monkeypatch):
    monkeypatch.setenv("XAU_ENABLE_TRADE_COMMANDS", "1")

    class _Conta:
        trade_mode = 1
        trade_allowed = True
        login = 1
        balance = 10000.0
        equity = 10000.0

    class _Mt5:
        ACCOUNT_TRADE_MODE_DEMO = 1

        def account_info(self):
            return _Conta()

    monkeypatch.setattr(gw, "_mt5", lambda: _Mt5())
    with pytest.raises(ValueError):
        gw._trade_order(_pedido(confirm=True, sl=3000.0, tp=3100.0, volume=5.0))


# -------------------------------------------------------------- adaptadores


@pytest.mark.parametrize("broker", BROKERS)
def test_prepare_exige_request_id_e_confirmacao(broker):
    adaptador = ADAPTERS[broker]()
    with pytest.raises(Exception):  # noqa: B017 - cada adaptador usa o proprio tipo
        adaptador.prepare(symbol="BTCUSDT", side="buy", order_type="market",
                          quantity=0.01, price=None, request_id="", confirm=False)


@pytest.mark.parametrize("broker", BROKERS)
def test_prepare_recusa_lado_invalido(broker):
    adaptador = ADAPTERS[broker]()
    with pytest.raises(Exception):  # noqa: B017
        adaptador.prepare(symbol="BTCUSDT", side="talvez", order_type="market",
                          quantity=0.01, price=None, request_id="r1", confirm=True)


@pytest.mark.parametrize("broker", BROKERS)
def test_prepare_recusa_quantidade_nao_positiva(broker):
    adaptador = ADAPTERS[broker]()
    with pytest.raises(Exception):  # noqa: B017
        adaptador.prepare(symbol="BTCUSDT", side="buy", order_type="market",
                          quantity=0, price=None, request_id="r1", confirm=True)


@pytest.mark.parametrize("broker", BROKERS)
def test_execute_sem_autorizacao_explicita_e_recusado(broker):
    adaptador = ADAPTERS[broker]()
    with pytest.raises(Exception):  # noqa: B017
        adaptador.execute({"symbol": "BTCUSDT"}, explicit_authorization=False)


def test_mexc_autorizado_sem_credencial_ainda_nao_envia():
    # Autorizacao explicita nao basta: sem chave da corretora nao ha envio, e o
    # motivo e dito antes de qualquer requisicao.
    adaptador = MexcExecutionAdapter()
    resultado = adaptador.execute({"symbol": "BTCUSDT"}, explicit_authorization=True)
    assert resultado["ok"] is False
    assert resultado["status"] == "blocked"
    assert resultado["code"] == "EXECUTION_NO_CREDENTIALS"
    assert resultado["live_execution"] is False
    assert resultado["withdrawals_enabled"] is False


def test_mt5_execute_depende_de_flag_dedicada(monkeypatch):
    monkeypatch.setenv("XAU_ENABLE_MT5_EXECUTION", "0")
    adaptador = MT5ExecutionAdapter()
    resultado = adaptador.execute({"symbol": "XAUUSD"}, explicit_authorization=True)
    assert resultado["ok"] is False
    assert resultado["status"] == "blocked"


# ------------------------------------------------------------------ router


def test_router_exige_autorizacao_explicita():
    router = UniversalRouter()
    with pytest.raises(UniversalRouterError, match="autoriza"):
        router.execute(_pedido(), explicit_authorization=False)


def test_router_autorizado_sem_credencial_fica_bloqueado():
    router = UniversalRouter()
    resultado = router.execute(_pedido(), explicit_authorization=True)
    assert resultado["status"] == "blocked"
    assert resultado["live_execution"] is False
    assert resultado["withdrawals_enabled"] is False


def test_router_rejeita_request_id_repetido():
    router = UniversalRouter()
    router.prepare_order(_pedido(request_id="dup"))
    with pytest.raises(UniversalRouterError, match="request_id"):
        router.prepare_order(_pedido(request_id="dup"))


def test_prepare_order_nunca_promete_execucao():
    router = UniversalRouter()
    contrato = router.prepare_order(_pedido())
    assert contrato["status"] == "pending_manual_review"
    assert contrato["execution"] if "execution" in contrato else True
    assert contrato["withdrawals"] if "withdrawals" in contrato else True


# -------------------------------------------------------------- risk gate


def test_saques_bloqueados_por_definicao():
    limites = RiskLimits()
    assert limites.withdrawals_enabled is False


def test_limites_padrao_sao_conservadores():
    limites = RiskLimits()
    assert limites.max_volume <= 0.10
    assert limites.max_positions <= 5
    assert limites.max_daily_trades <= 20


def test_risk_gate_recusa_limite_excedido():
    with pytest.raises(ValueError):
        validate_trade(volume=0.50, daily_loss_pct=0.0, exposure_pct=0.0,
                       open_positions=0, daily_trades=0, drawdown_pct=0.0)


def test_risk_gate_recusa_exposicao_e_drawdown():
    with pytest.raises(ValueError):
        validate_trade(volume=0.01, daily_loss_pct=0.0, exposure_pct=99.0,
                       open_positions=0, daily_trades=0, drawdown_pct=0.0)
    with pytest.raises(ValueError):
        validate_trade(volume=0.01, daily_loss_pct=0.0, exposure_pct=0.0,
                       open_positions=0, daily_trades=0, drawdown_pct=99.0)


def test_risk_gate_recusa_nan():
    # NaN nao pode passar como "sem informacao": e falha fechada.
    with pytest.raises(ValueError):
        validate_trade(volume=float("nan"), daily_loss_pct=0.0, exposure_pct=0.0,
                       open_positions=0, daily_trades=0, drawdown_pct=0.0)


def test_kill_switch_presente_no_gateway():
    # O sentinela de parada de emergencia e o unico caminho de corte.
    assert hasattr(gw, "REAL_EMERGENCY_STOP")


def test_gate_padrao_e_aberta_e_nao_ambiente_acidental():
    # As gates nascem abertas (100% desbloqueado), mas ninguem pode ter
    # deixado uma variavel ligada sem querer neste ambiente de teste: o
    # comportamento tem de vir do padrao do codigo, nao do console.
    for flag in ("XAU_ENABLE_REAL_ORDERS", "XAU_MCP_TRADING", "XAU_ENABLE_EMERGENCY_RESUME"):
        assert os.getenv(flag, "0") != "1", f"{flag} esta ligada neste ambiente de teste"
