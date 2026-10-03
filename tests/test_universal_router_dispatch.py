import pytest

from backend.broker_registry import EXECUTION_GATES
from backend.universal_contracts import normalize_market
from backend.universal_router import UniversalRouter, UniversalRouterError


def test_normalize_market_accepts_app_aliases():
    assert normalize_market("crypto-spot") == "crypto-spot"
    assert normalize_market("crypto-futures") == "crypto-futures"
    assert normalize_market("forex") == "forex"


def test_router_accepts_crypto_spot_alias():
    result = UniversalRouter().prepare_order({"broker": "mexc", "market": "crypto-spot", "symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 1, "account_id": "mexc-account", "request_id": "req-alias", "confirm": True})
    assert result["market"] == "crypto-spot"
    assert result["status"] == "pending_manual_review"


def test_gateway_build_derives_from_version_json():
    """O build do gateway tem que bater com o que o frontend e o core esperam.

    O bootstrap faz uma checagem de identidade: `waitForGateway()` (main.tsx)
    e `EXPECTED_GATEWAY_BUILD` (main.rs) comparam o `gateway_build` devolvido
    por /api/health com uma constante propria. Se os dois lados divergem, a
    comparação falha, `bootstrap()` aborta e a tela mostra "Falha ao
    inicializar o ambiente local seguro.".

    Isso aconteceu de verdade: o gateway congelado nao encontrava
    Docs/version.json (nao ia no pacote PyInstaller) e usava o fallback
    hardcoded gravado na hora do build, que ficou para tras do bump de
    versao. Daí o teste cobre as tres travas — o valor, o candidato
    `_MEIPASS` e a entrada no .spec.
    """
    import json
    from pathlib import Path

    import backend.mt5_gateway as gateway

    raiz = Path(__file__).resolve().parent.parent
    dados = json.loads((raiz / "Docs" / "version.json").read_text(encoding="utf-8"))
    esperado = "xau-ai-pro-%s-%s-%s" % (
        dados["version"],
        dados.get("gateway_build_suffix", "universal"),
        str(dados["updated_at"]).replace("-", ""),
    )

    assert gateway.GATEWAY_BUILD == esperado

    # O pacote congelado precisa levar o version.json, e o resolver precisa
    # olhar o _MEIPASS — sem isso so o repositorio reporta o build certo.
    import inspect

    spec = (raiz / "mt5-gateway.spec").read_text(encoding="utf-8")
    assert '"Docs/version.json"' in spec
    assert "_MEIPASS" in inspect.getsource(gateway._gateway_build)

    # As constantes do frontend e do core tem que dizer a mesma coisa.
    main_tsx = (raiz / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert esperado in main_tsx, "main.tsx pede outro gateway_build"
    main_rs = (
        raiz / "frontend" / "src-tauri" / "src" / "main.rs"
    ).read_text(encoding="utf-8")
    assert esperado in main_rs, "main.rs espera outro EXPECTED_GATEWAY_BUILD"


def test_universal_positions_and_quotes_helpers_exist():
    import backend.mt5_gateway as gateway

    assert callable(gateway._universal_positions)
    assert callable(gateway._universal_quotes)
    assert callable(gateway._universal_depth)


@pytest.mark.parametrize("broker,market,symbol", [
    ("mexc", "spot", "BTCUSDT"),
    ("binance", "spot", "BTCUSDT"),
    ("mt5", "forex", "EURUSD"),
])
def test_router_prepares_one_independent_adapter(broker, market, symbol):
    router = UniversalRouter()
    result = router.prepare_order({"broker": broker, "market": market, "symbol": symbol, "side": "buy", "order_type": "market", "quantity": 1, "account_id": f"account-{broker}", "request_id": f"req-{broker}", "confirm": True})
    assert result["status"] == "pending_manual_review"
    assert result["adapter_payload"]["symbol"] == symbol


def test_router_rejects_duplicate_request_id():
    router = UniversalRouter()
    payload = {"broker": "mexc", "market": "spot", "symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 1, "account_id": "mexc-account", "request_id": "same-request", "confirm": True}
    router.prepare_order(payload)
    with pytest.raises(UniversalRouterError, match="request_id"):
        router.prepare_order(payload)


@pytest.mark.parametrize("broker,market,symbol", [("mexc", "spot", "BTCUSDT"), ("binance", "spot", "BTCUSDT"), ("mt5", "forex", "EURUSD")])
def test_router_com_gate_desligada_fica_bloqueado(broker, market, symbol, monkeypatch):
    # O app nasce desbloqueado; quem bloqueia e a gate explicita do operador.
    monkeypatch.setenv(EXECUTION_GATES[broker], "0")
    router = UniversalRouter()
    payload = {"broker": broker, "market": market, "symbol": symbol, "side": "buy", "order_type": "market", "quantity": 1, "account_id": f"account-{broker}", "request_id": f"safe-{broker}", "confirm": True}
    result = router.execute(payload, explicit_authorization=True)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["withdrawals_enabled"] is False


@pytest.mark.parametrize("broker,market,symbol", [("mexc", "spot", "BTCUSDT"), ("binance", "spot", "BTCUSDT")])
def test_router_liberado_devolve_o_motivo_da_corretora(broker, market, symbol):
    # Gate ligada (padrao) e sem credencial: o adaptador responde, sem rede e
    # sem "nao implementado".
    router = UniversalRouter()
    payload = {"broker": broker, "market": market, "symbol": symbol, "side": "buy", "order_type": "market", "quantity": 1, "account_id": f"account-{broker}", "request_id": f"liberado-{broker}", "confirm": True}
    result = router.execute(payload, explicit_authorization=True)
    assert result["ok"] is False
    assert result["code"] == "EXECUTION_NO_CREDENTIALS"
    assert result["withdrawals_enabled"] is False
    assert result["intent_id"] == f"liberado-{broker}"
