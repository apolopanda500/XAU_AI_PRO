# -*- coding: utf-8 -*-
"""MCP Marketplace - pesquisa e instala MCP servers dentro do app.

Catalogo embutido de MCPs conhecidos (OpenAI, GitHub, Brave, Filesystem,
Fetch, Memory, Time, Puppeteer, Playwright, etc.) + registro local.
Instalar = cria o json em mcp/servers e registra no registry.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

_SERVERS_DIR = Path(__file__).resolve().parent.parent / "mcp" / "servers"

# Catalogo embutido (instalacao offline, sem depender de API externa)
CATALOGO: list[dict[str, Any]] = [
    {"id": "openai", "name": "OpenAI MCP", "type": "stdio",
     "endpoint": "npx -y @openai/mcp", "desc": "Executa modelos OpenAI via npx.", "chave": True},
    {"id": "github_mcp", "name": "GitHub MCP", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-github", "desc": "Repos, issues e PRs do GitHub.", "chave": True},
    {"id": "brave", "name": "Brave Search MCP", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-brave-search", "desc": "Pesquisa web com Brave Search.", "chave": True},
    {"id": "filesystem", "name": "Filesystem MCP", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-filesystem", "desc": "Acesso a arquivos locais.", "chave": False},
    {"id": "fetch", "name": "Fetch MCP", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-fetch", "desc": "Baixa paginas web (scraping).", "chave": False},
    {"id": "memory", "name": "Memory MCP", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-memory", "desc": "Memoria persistente de conhecimento.", "chave": False},
    {"id": "time", "name": "Time MCP", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-time", "desc": "Data/hora e fuso em varios formatos.", "chave": False},
    {"id": "puppeteer", "name": "Puppeteer MCP", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-puppeteer", "desc": "Automacao de navegador (browser).", "chave": False},
    {"id": "playwright", "name": "Playwright MCP", "type": "stdio",
     "endpoint": "npx -y @playwright/mcp@latest", "desc": "Automacao de navegador alternativa.", "chave": False},
    {"id": "sqlite_db", "name": "SQLite MCP (tabela PCA)", "type": "stdio",
     "endpoint": "npx -y @modelcontextprotocol/server-sqlite", "desc": "SQLite com esquema de trading.", "chave": False},
    {"id": "databases", "name": "MCP Databases", "type": "stdio",
     "endpoint": "npx -y @databases/mcp", "desc": "Postgres, MySQL, SQLite via uma lib.", "chave": True},
    {"id": "mongodb", "name": "MongoDB MCP", "type": "stdio",
     "endpoint": "npx -y @mongodb-ya/mcp", "desc": "Banco MongoDB.", "chave": True},
    {"id": "redis", "name": "Redis MCP", "type": "stdio",
     "endpoint": "npx -y @redis-io/mcp", "desc": "Cache/Filas Redis.", "chave": True},
    {"id": "sentry_mcp", "name": "Sentry MCP", "type": "stdio",
     "endpoint": "npx -y @sentry/mcp", "desc": "Erros e traces do Sentry.", "chave": True},
    {"id": "clickhouse", "name": "ClickHouse MCP", "type": "stdio",
     "endpoint": "npx -y @clickhouse/mcp", "desc": "Analise de dados ClickHouse.", "chave": True},
]


def catalogo() -> list[dict[str, Any]]:
    return [dict(x) for x in CATALOGO]


def instalados() -> list[str]:
    if not _SERVERS_DIR.exists():
        return []
    return [p.stem for p in _SERVERS_DIR.glob("*.json")]


def instalar(server_id: str, enabled: bool = True) -> dict[str, Any]:
    """Instala um MCP do catalogo. Retorna {ok, message}."""
    item = next((x for x in CATALOGO if x["id"] == server_id), None)
    if not item:
        return {"ok": False, "message": f"MCP '{server_id}' nao existe no catalogo"}
    _SERVERS_DIR.mkdir(parents=True, exist_ok=True)
    rec = {
        "name": item["name"],
        "id": item["id"],
        "description": item["desc"],
        "type": item.get("type", "stdio"),
        "default_endpoint": item["endpoint"],
        "needs_api_key": item.get("chave", False),
        "api_key_env": "",
        "enabled": enabled,
    }
    try:
        (_SERVERS_DIR / f"{server_id}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return {"ok": False, "message": f"Erro ao salvar: {e}"}
    # registry
    reg_file = _SERVERS_DIR / "registry.json"
    reg = {"servers": []}
    if reg_file.exists():
        try:
            reg = json.loads(reg_file.read_text(encoding="utf-8"))
        except Exception:
            reg = {"servers": []}
    fname = f"{server_id}.json"
    if fname not in reg.setdefault("servers", []):
        reg["servers"].append(fname)
    try:
        reg_file.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return {"ok": False, "message": f"Erro no registry: {e}"}
    # sincroniza config do app
    try:
        from app.config_manager import get_config
        c = get_config()
        servers = dict(c.get("integrations", "mcp", "servers", default={}) or {})
        servers[server_id] = {"enabled": enabled, "endpoint": item["endpoint"], "api_key": ""}
        c.set("integrations", "mcp", "servers", value=servers)
    except Exception:
        pass
    return {"ok": True, "message": f"{item['name']} instalado"}


def pesquisar(query: str) -> list[dict[str, Any]]:
    """Filtra o catalogo pelo nome/descricao (case-insensitive)."""
    q = (query or "").strip().lower()
    if not q:
        return catalogo()
    return [x for x in CATALOGO
            if q in x["name"].lower() or q in x["desc"].lower() or q in x["id"].lower()]


def desinstalar(server_id: str) -> dict[str, Any]:
    """Remove um MCP instalado (json + registry + config)."""
    f = _SERVERS_DIR / f"{server_id}.json"
    if f.exists():
        try:
            f.unlink()
        except Exception as e:
            return {"ok": False, "message": str(e)}
    reg_file = _SERVERS_DIR / "registry.json"
    if reg_file.exists():
        try:
            reg = json.loads(reg_file.read_text(encoding="utf-8"))
            reg["servers"] = [x for x in reg.get("servers", []) if x != f"{server_id}.json"]
            reg_file.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    try:
        from app.config_manager import get_config
        c = get_config()
        servers = dict(c.get("integrations", "mcp", "servers", default={}) or {})
        servers.pop(server_id, None)
        c.set("integrations", "mcp", "servers", value=servers)
    except Exception:
        pass
    return {"ok": True, "message": f"{server_id} removido"}