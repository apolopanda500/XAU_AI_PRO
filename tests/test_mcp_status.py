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
