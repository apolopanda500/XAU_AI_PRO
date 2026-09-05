from unittest.mock import patch


def test_tool_status_respects_disabled_server_and_keeps_valid_server() -> None:
    from app.mcp_tools import tool_status

    servers = {
        "cline": {"name": "Cline", "enabled": False, "type": "stdio", "endpoint": "cline mcp"},
        "memory": {"name": "Memory", "enabled": True, "type": "stdio", "endpoint": "npx memory"},
    }
    with patch("app.mcp_tools.load_mcp_servers", return_value=servers):
        status = {item["id"]: item for item in tool_status()}

    assert status["cline"]["configured"] is False
    assert status["cline"]["enabled"] is False
    assert status["cline"]["reason"] == "desativado pelo usuario"
    assert status["memory"]["enabled"] is True


def test_github_requires_token() -> None:
    from app.mcp_tools import _availability

    with patch.dict("app.mcp_tools.os.environ", {}, clear=True):
        available, reason = _availability("github_mcp", {"enabled": True, "api_key": ""})

    assert available is False
    assert reason == "token GitHub ausente"


def test_marketplace_excludes_incompatible_packages() -> None:
    from app.mcp_marketplace import catalogo

    ids = {item["id"] for item in catalogo()}
    incompatible = {
        "clickhouse", "databases", "fetch", "mongodb", "openai",
        "puppeteer", "redis", "sentry_mcp", "sqlite_db", "time",
    }
    assert ids.isdisjoint(incompatible)
