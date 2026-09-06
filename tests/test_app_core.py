"""Testes de core, integracao, MCPs e UI do XAU_AI_PRO."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# 1. Importacao e estrutura
# ---------------------------------------------------------------------------

def test_import_core_app() -> None:
    from app.core import XAUAProApp
    from app.components.sidebar import Sidebar
    from app.components.animated_bg import AnimatedBackground
    from app.theme.mexc import Theme
    assert XAUAProApp
    assert Sidebar
    assert AnimatedBackground
    assert Theme.PRIMARY == "#00c6fb"


def test_all_tabs_importable() -> None:
    from app.tabs import dashboard, market, positions, robot
    from app.tabs import tools, search, charts, subgraph, system, settings
    from app.tabs import integrations
    for mod in (dashboard, market, positions, robot, tools,
                search, charts, subgraph, system, settings, integrations):
            assert hasattr(mod, "DashboardTab") or hasattr(mod, "MarketTab") or hasattr(mod, "TradingViewMarket") or mod.__name__


# ---------------------------------------------------------------------------
# 2. Configuracoes
# ---------------------------------------------------------------------------

def test_config_manager_defaults() -> None:
    from app.config_manager import ConfigManager
    cfg = ConfigManager(path=Path(ROOT) / "Temp" / "test_config.json")
    assert cfg.get("app_version") == "1.2.0"
    assert cfg.get("market", "default_symbol", default="XAUUSD") == "XAUUSD"


# ---------------------------------------------------------------------------
# 3. MCPs (sem env vars reais, apenas estrutura)
# ---------------------------------------------------------------------------

def test_mcp_servers_registry() -> None:
    import json
    registry = json.loads((ROOT / "mcp" / "servers" / "registry.json").read_text())
    assert registry["servers"] == ["mt5_gateway.json", "tradingview.json"]


def test_mcp_tools_dispatcher_has_operational_connectors() -> None:
    from app import mcp_tools
    assert "mt5_gateway" in mcp_tools._ACTIONS_SPECIFIC
    assert "tradingview" in mcp_tools._ACTIONS_SPECIFIC


# ---------------------------------------------------------------------------
# 4. IA / AI Client
# ---------------------------------------------------------------------------

def test_ai_client_effective_settings_reads_env() -> None:
    from app.ai_client import _effective_settings
    os.environ["CLINE_API_KEY"] = "sk-test"
    os.environ["CLINE_BASE_URL"] = "https://api.test/v1"
    os.environ["CLINE_MODEL"] = "gpt-test"
    s = _effective_settings()
    assert s["enabled"] is True
    assert s["base_url"] == "https://api.test/v1"
    assert s["model"] == "gpt-test"


def test_ai_client_env_fallback_openai() -> None:
    from app.ai_client import _effective_settings
    os.environ.pop("CLINE_API_KEY", None)
    os.environ["OPENAI_API_KEY"] = "sk-openai-test"
    s = _effective_settings()
    assert s["enabled"] is True
    assert s["api_key"] == "sk-openai-test"


# ---------------------------------------------------------------------------
# 5. Build spec
# ---------------------------------------------------------------------------

def test_launcher_spec_compiles() -> None:
    spec_path = ROOT / "launcher.spec"
    assert spec_path.exists()
    text = spec_path.read_text()
    assert "Tree as _Tree" in text
    assert "from PyInstaller.building.datastruct" in text


# ---------------------------------------------------------------------------
# 6. Env / integracoes
# ---------------------------------------------------------------------------

def test_env_local_has_keys(monkeypatch) -> None:
    env_path = ROOT / ".env.local"
    if not env_path.exists():
        pytest.skip(".env.local nao encontrado")
    text = env_path.read_text()
    assert "QUANTCONNECT_USER_ID" in text
    assert "CLINE_API_KEY" in text or "OPENAI_API_KEY" in text
