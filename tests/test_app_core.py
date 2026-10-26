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
    from app.tabs import tools, charts, settings
    from app.tabs import integrations
    for mod in (dashboard, market, positions, robot, tools,
                charts, settings, integrations):
            assert hasattr(mod, "DashboardTab") or hasattr(mod, "MarketTab") or hasattr(mod, "TradingViewMarket") or mod.__name__


# ---------------------------------------------------------------------------
# 2. Configuracoes
# ---------------------------------------------------------------------------

def test_config_manager_defaults(tmp_path: Path) -> None:
    """Verifica os defaults reais do ConfigManager.

    Antes este teste escrevia em `ROOT/Temp/test_config.json` e afirmava uma
    versao fixa. Passava por acidente: lia o arquivo leftover de uma execucao
    antiga em vez de exercitar o default. Alem disso procurava
    `market.default_symbol`, que nao existe — a chave real e
    `trading.default_symbol` — entao o `get()` devolvia o proprio fallback
    `"XAUUSD"` do teste e a assert nunca verificava a configuracao. Agora o
    arquivo e isolado por teste e os valores vem da fonte da verdade, entao
    nao podem voltar a divergir em silencio.
    """
    from app.config_manager import DEFAULT_CONFIG, ConfigManager

    cfg = ConfigManager(path=tmp_path / "test_config.json")
    assert cfg.get("app_version") == DEFAULT_CONFIG["app_version"]
    assert cfg.get("trading", "default_symbol") == DEFAULT_CONFIG["trading"]["default_symbol"]


# ---------------------------------------------------------------------------
# 3. MCPs (sem env vars reais, apenas estrutura)
# ---------------------------------------------------------------------------

def test_mcp_servers_a_pasta_e_a_unico_catalogo(tmp_path: Path) -> None:
    """`mcp/servers/*.json` e a UNICA fonte do catalogo, e o loader confere.

    Antes este teste lia `registry.json` e comparava a lista literal:
    `assert registry["servers"] == ["mt5_gateway.json", "tradingview.json"]`.
    Mas o loader IGNORA o registry (faz `glob` da pasta), entao a trava punia
    quem documentava (adicionar no registry sem criar o arquivo reprovava) e
    deixava passar quem nao documentava (criar o arquivo sem registrar
    passava em verde). Agora o teste exercita o consumidor de verdade.

    MEDIDO em 25/10/2026, quatro casos, mesmo commit:
      - arquivo novo e valido na pasta   -> VERDE (a pasta e a fonte)
      - `registry.json` recriado         -> VERMELHO, motivo escrito
      - arquivo sem campo obrigatorio    -> VERMELHO, nome do arquivo
      - arquivo que nao parseia          -> VERMELHO, nome do arquivo

    O que este teste NAO pega, por desenho: apagar um servidor da pasta. Sem
    manifest a parte nao ha segundo lado para comparar - quem apaga o arquivo
    apaga tambem a entrada do catalogo. Isso e vazio de produto, nao
    divergencia de dado, e depende de revisao humana.
    """
    import json
    from unittest.mock import patch

    from app.config_manager import ConfigManager
    from app.integrations_client import load_mcp_servers

    pasta = ROOT / "mcp" / "servers"
    arquivos = sorted(pasta.glob("*.json"))
    assert arquivos, f"catalogo vazio: nenhum *.json em {pasta}"
    # Manifest separado = dois lados do mesmo dado. Nao pode existir.
    assert not (pasta / "registry.json").exists(), (
        "mcp/servers/registry.json voltou: a pasta e o catalogo, "
        "o loader ignora manifest separado"
    )
    # Arquivo quebrado reprova AQUI, com o nome do arquivo, em vez de virar
    # servidor anonimo no marketplace (ver load_mcp_servers).
    # `utf-8-sig`: BOM do PowerShell 5.1 e arquivo VALIDO, nao quebrado.
    for f in arquivos:
        try:
            rec = json.loads(f.read_text(encoding="utf-8-sig"))
        except ValueError as error:
            pytest.fail(f"{f.name}: JSON invalido: {error}")
        assert isinstance(rec, dict), f"{f.name}: conteudo nao e objeto JSON"
        for campo in ("name", "description", "type", "default_endpoint", "enabled"):
            assert campo in rec, f"{f.name}: campo obrigatorio ausente: {campo}"

    with patch(
        "app.config_manager.get_config",
        return_value=ConfigManager(tmp_path / "cfg.json"),
    ):
        servidores = load_mcp_servers()

    esperados = {f.stem for f in arquivos}
    assert set(servidores) == esperados, (
        f"loader e pasta divergem: no loader {sorted(set(servidores) - esperados)} "
        f"faltando {sorted(esperados - set(servidores))}"
    )


def test_mcp_servers_arquivo_invalido_nao_vira_servidor_anonimo(tmp_path: Path) -> None:
    """PROVA NEGATIVA: `.json` quebrado NAO vira servidor com aspecto de valido.

    Contra o codigo anterior o teste reprova: o loader antigo fazia
    `rec = {}` no `except` e o catalogo devolvia `quebrado` com
    `name = "Quebrado"`, `description = ""` — um servidor inventado que o
    marketplace mostrava como se fosse configurado.
    """
    import json
    from unittest.mock import patch

    from app.config_manager import ConfigManager
    from app.integrations_client import load_mcp_servers

    (tmp_path / "bom.json").write_text(json.dumps({
        "name": "Servidor Bom", "description": "d", "type": "http",
        "default_endpoint": "http://127.0.0.1:9001", "enabled": True,
    }), encoding="utf-8")
    (tmp_path / "quebrado.json").write_text("{isto nao e json", encoding="utf-8")
    (tmp_path / "lista.json").write_text(json.dumps(["nao", "e", "objeto"]), encoding="utf-8")
    # BOM do `Set-Content -Encoding UTF8` (PowerShell 5.1) e arquivo VALIDO:
    # tem de entrar no catalogo, nao cair no mesmo caminho do arquivo quebrado.
    (tmp_path / "com_bom.json").write_text(json.dumps({
        "name": "Com BOM", "description": "d", "type": "http",
        "default_endpoint": "http://127.0.0.1:2", "enabled": False,
    }), encoding="utf-8-sig")

    with patch(
        "app.config_manager.get_config",
        return_value=ConfigManager(tmp_path / "cfg" / "config.json"),
    ):
        servidores = load_mcp_servers(tmp_path)

    assert set(servidores) == {"bom", "com_bom"}, (
        f"catalogo divergente: {sorted(servidores)}"
    )


# Campos que tem consumidor de verdade no loader. MEDIDO antes de apagar os
# outros (regra 9 do AGENTS.md): `id` (loader usa o stem), `needs_api_key` e
# `api_key_env` (zero leitores em Python e zero em core/src) e `database_url`
# / `user_id` (so o ramo inalcancavel `postgres_sqlite` os lia).
CAMPOS_CATALOGO_MCP = {"name", "description", "type", "default_endpoint", "enabled"}


def test_mcp_servers_nenhum_campo_sem_consumidor() -> None:
    """PROVA NEGATIVA: campo novo no `.json` reprova, mesmo que ninguem leia.

    Este e o guard que impede `needs_api_key` de voltar. Sem ele, um campo
    decorativo passa despercebido e quem le o arquivo acredita que ele faz
    algo - controle de vitrine, pior que ausencia (regra 9).
    """
    import json

    pasta = ROOT / "mcp" / "servers"
    for f in sorted(pasta.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8-sig"))
        extras = set(rec) - CAMPOS_CATALOGO_MCP
        assert not extras, f"{f.name}: campo sem consumidor: {sorted(extras)}"


def test_catalogo_defeitos_da_o_motivo_de_arquivo_recusado(tmp_path: Path) -> None:
    """A4: recusa com motivo, e nao sumicao silenciosa do marketplace."""
    import json
    from unittest.mock import patch

    from app.config_manager import ConfigManager
    from app.integrations_client import catalogo_defeitos, load_mcp_servers

    (tmp_path / "quebrado.json").write_text("{isto nao e json", encoding="utf-8")
    (tmp_path / "lista.json").write_text(json.dumps(["nao", "e", "objeto"]), encoding="utf-8")
    (tmp_path / "bom.json").write_text(json.dumps({
        "name": "Bom", "description": "d", "type": "http",
        "default_endpoint": "http://127.0.0.1:9001", "enabled": True,
    }), encoding="utf-8")

    with patch(
        "app.config_manager.get_config",
        return_value=ConfigManager(tmp_path / "cfg" / "config.json"),
    ):
        servidores = load_mcp_servers(tmp_path)
        defeitos = catalogo_defeitos(tmp_path)

    assert "quebrado" not in servidores and "lista" not in servidores
    assert {d["id"] for d in defeitos} == {"quebrado", "lista"}
    assert all(d["motivo"].strip() for d in defeitos), defeitos


def test_ui_do_catalogo_consome_os_defeitos() -> None:
    """O motivo tem de chegar na tela: consumidor real, nao so teste (regra 9)."""
    fonte = (ROOT / "app" / "tabs" / "integrations.py").read_text(encoding="utf-8")
    assert "catalogo_defeitos()" in fonte, (
        "aba Integracoes deixou de exibir os defeitos do catalogo"
    )


def test_mcp_server_ping_conector_nao_aprovado_nao_executa_comando() -> None:
    """INVARIANTE: `.json` da pasta NUNCA manda o app rodar comando.

    O `endpoint` abaixo e um comando npx. O trecho generico que existiu em
    `mcp_server_ping` (removido em 25/10/2026) executaria ele para id
    desconhecido; a travado e que a resposta venha de `call_tool`, que recusa
    id fora de `_ACTIONS_SPECIFIC`. Nao e diferencial - o codigo antigo tambem
    recusava - e um cadeado para o fallback nao voltar.
    """
    from app.integrations_client import mcp_server_ping

    comando = "npx -y @modelcontextprotocol/server-sequential-thinking"
    for sid in ("sequential_thinking", "postgres_sqlite", "qualquer_coisa"):
        r = mcp_server_ping({"id": sid, "type": "stdio", "endpoint": comando})
        assert r["ok"] is False, f"{sid} foi aprovado sem estar em _ACTIONS_SPECIFIC"
        assert "nao aprovado" in str(r["message"]).lower(), r["message"]


def test_mcp_server_ping_diferencial_servidor_sem_id_e_recusa() -> None:
    """PROVA NEGATIVA (diferencial): id vazio NAO vira probe de rede.

    No codigo anterior `server_id` vazio escapava do `if server_id` e caia no
    trecho generico: `type: "http"` chamava `mcp_ping(endpoint)` e o app abria
    uma conexao a partir de um `.json` sem id. Medido: a mensagem antiga era
    "Sem resposta: ..." (ou "Endpoint vazio"); agora e "Servidor sem id".
    """
    from app.integrations_client import mcp_server_ping

    r = mcp_server_ping({"id": "", "type": "http", "endpoint": "http://127.0.0.1:1"})

    assert r["ok"] is False
    assert r["message"] == "Servidor sem id", r["message"]


def test_mcp_servers_endpoint_do_gateway_segue_o_ambiente(tmp_path: Path, monkeypatch) -> None:
    """A7: o endpoint do `mt5_gateway` segue `XAU_GATEWAY_PORT`, como o gateway.

    MEDIDO antes de corrigir: gateway em 9011 (`mt5-gateway` pid 12044,
    `/health` -> 401), catalogo e config salva apontando 9001 - livre. Dois
    lados do mesmo dado divergindo na porta (AGENTS.md §5).

    As tres pernas: ambiente manda no default de fabrica; porta digitada pelo
    operador nao e sobrescrita; valor invalido de volta ao padrao.
    """
    import json
    from unittest.mock import patch

    from app.config_manager import ConfigManager
    from app.integrations_client import load_mcp_servers

    pasta = tmp_path / "servers"
    pasta.mkdir()
    (pasta / "mt5_gateway.json").write_text(json.dumps({
        "name": "MT5", "description": "d", "type": "http",
        "default_endpoint": "http://127.0.0.1:9001", "enabled": True,
    }), encoding="utf-8")

    cfg = ConfigManager(tmp_path / "cfg" / "config.json")

    def endpoint_salvo(url: str) -> str:
        cfg.set("integrations", "mcp", "servers",
                value={"mt5_gateway": {"enabled": True, "endpoint": url}})
        with patch("app.config_manager.get_config", return_value=cfg):
            return load_mcp_servers(pasta)["mt5_gateway"]["endpoint"]

    monkeypatch.setenv("XAU_GATEWAY_PORT", "9011")
    assert endpoint_salvo("") == "http://127.0.0.1:9011", "default de fabrica deve seguir o ambiente"

    assert endpoint_salvo("http://127.0.0.1:9005") == "http://127.0.0.1:9005", (
        "porta escolhida pelo operador foi sobrescrita"
    )

    monkeypatch.setenv("XAU_GATEWAY_PORT", "nao-e-porta")
    assert endpoint_salvo("http://127.0.0.1:9001") == "http://127.0.0.1:9001"

    monkeypatch.delenv("XAU_GATEWAY_PORT", raising=False)
    assert endpoint_salvo("") == "http://127.0.0.1:9001"


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
    assert "_source_datas" in text
    assert "'node_modules'" in text
    assert "'__pycache__'" in text
    assert "_BACKEND_DATAS = _source_datas" in text


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
