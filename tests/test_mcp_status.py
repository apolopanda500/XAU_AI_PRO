from unittest.mock import patch


def test_tool_status_respects_disabled_server_and_keeps_valid_server() -> None:
    from app.mcp_tools import tool_status

    servers = {
        "mt5_gateway": {"name": "MT5", "enabled": False, "type": "http", "endpoint": "http://127.0.0.1:9001"},
        "tradingview": {"name": "TradingView", "enabled": True, "type": "http", "endpoint": "https://scanner.tradingview.com"},
    }
    with patch("app.mcp_tools.load_mcp_servers", return_value=servers):
        status = {item["id"]: item for item in tool_status()}

    assert status["mt5_gateway"]["configured"] is False
    assert status["mt5_gateway"]["enabled"] is False
    assert status["mt5_gateway"]["reason"] == "desativado pelo usuario"
    assert status["tradingview"]["enabled"] is True


def test_operational_connector_requires_no_extra_key() -> None:
    from app.mcp_tools import _availability

    available, reason = _availability("tradingview", {"enabled": True, "api_key": ""})

    assert available is True
    assert reason == "configurado"


def test_conector_mt5_gateway_envia_o_header_de_autorizacao(monkeypatch) -> None:
    """A8: o conector tem de mandar `Authorization: Bearer <token>`.

    MEDIDO antes de corrigir: `call_tool("mt5_gateway", "health")` devolvia
    `MT5 Gateway: HTTP Error 401: Unauthorized` mesmo com o gateway no ar na
    porta certa - `_http_json` mandava so `User-Agent`. O teste exercita o
    caminho inteiro (loader -> conector -> urlopen), nao so o helper.
    """
    import urllib.request

    from app import mcp_tools

    capturado: dict[str, str | None] = {}

    class _Resp:
        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    def _fake(request, timeout=None):  # noqa: ANN001
        capturado["url"] = request.full_url
        capturado["auth"] = request.get_header("Authorization")
        return _Resp()

    monkeypatch.setenv("XAU_GATEWAY_TOKEN", "token-de-teste")
    monkeypatch.setattr(urllib.request, "urlopen", _fake)

    resultado = mcp_tools.call_tool("mt5_gateway", "health")

    assert resultado["ok"] is True, resultado
    assert capturado["auth"] == "Bearer token-de-teste", capturado


def test_conector_mt5_gateway_sem_token_nao_manda_bearer_vazio(monkeypatch) -> None:
    """Sem token configurado o header some: nada de `Bearer ` vazio (§4)."""
    import urllib.request

    from app import mcp_tools
    from backend import trading_mcp

    capturado: dict[str, str | None] = {}

    class _Resp:
        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    def _fake(request, timeout=None):  # noqa: ANN001
        capturado["auth"] = request.get_header("Authorization")
        return _Resp()

    monkeypatch.setattr(trading_mcp, "_token_do_dotenv", lambda: "")
    monkeypatch.delenv("XAU_GATEWAY_TOKEN", raising=False)
    monkeypatch.setattr(urllib.request, "urlopen", _fake)

    resultado = mcp_tools.call_tool("mt5_gateway", "health")

    assert resultado["ok"] is True, resultado
    assert capturado["auth"] is None, capturado
