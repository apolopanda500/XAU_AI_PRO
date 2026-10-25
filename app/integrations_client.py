# -*- coding: utf-8 -*-
"""Clientes de integracao do XAU_AI_PRO (GitHub, GitLab, Figma, MCP/Plugins).

Funcoes de teste de conexao usadas pela aba de Integracoes.
Todas retornam dict {ok, message} e NUNCA levantam excecao.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_UA = {"User-Agent": "XAU_AI_PRO/1.3.2"}


def _res(ok: bool, message: str) -> dict[str, Any]:
    return {"ok": ok, "message": message}


# ============================================================
# GitHub
# ============================================================

def _github_slug(repo_url: str) -> str:
    value = repo_url.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]

    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()

    if host == "github.com":
        return parsed.path.lstrip("/").rstrip("/")

    return value


def _github_cli_test(repo_url: str) -> dict[str, Any] | None:
    slug = _github_slug(repo_url)
    try:
        process = subprocess.run(
            ["gh", "repo", "view", slug, "--json", "nameWithOwner,viewerPermission"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return _res(False, "Timeout ao consultar o GitHub CLI")
    if process.returncode != 0:
        return None
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError:
        return _res(False, "Resposta invalida do GitHub CLI")
    name = str(payload.get("nameWithOwner") or slug)
    permission = str(payload.get("viewerPermission") or "READ")
    return _res(True, f"Conectado via GitHub CLI: {name} ({permission})")

def github_test(repo_url: str, token: str = "") -> dict[str, Any]:
    """Testa acesso ao repositorio via 'git ls-remote' (publico ou com token)."""
    url = (repo_url or "").strip()
    if not url:
        return _res(False, "URL do repositorio vazia")
    cli_result = _github_cli_test(url)
    if cli_result is not None:
        return cli_result
    git_env = os.environ.copy()
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    if token:
        git_env.update({
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": "Authorization: Bearer " + token,
        })
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--heads", url],
            capture_output=True, text=True, timeout=25, env=git_env,
        )
        if proc.returncode == 0:
            n = len(proc.stdout.strip().splitlines())
            return _res(True, "Conectado ao repositorio (%d branch(es) visiveis)" % n)
        err = (proc.stderr or "").strip().splitlines()
        detalhe = err[-1] if err else "exit %d" % proc.returncode
        return _res(False, "Falha: %s" % detalhe[:140])
    except FileNotFoundError:
        return _res(False, "git nao encontrado no PATH")
    except subprocess.TimeoutExpired:
        return _res(False, "Timeout ao contatar o repositorio")
    except Exception as e:  # noqa: BLE001
        return _res(False, "Erro: %s" % e)


def github_push_test(repo_url: str, token: str = "") -> dict[str, Any]:
    """Informa o status de credenciais para push."""
    try:
        process = subprocess.run(
            ["gh", "auth", "status", "--hostname", "github.com"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if process.returncode == 0:
            return _res(True, "GitHub CLI autenticado; push disponivel (nenhum envio realizado)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    if token:
        return _res(True, "Token configurado (nenhum envio realizado)")
    return _res(False, "GitHub CLI e token indisponiveis para push")


# ============================================================
# GitLab
# ============================================================

def gitlab_test(base_url: str, token: str = "", project_path: str = "") -> dict[str, Any]:
    """Testa conectividade com GitLab via API REST."""
    url = (base_url or "").strip().rstrip("/")
    if not url:
        return _res(False, "URL do GitLab vazia")
    if not url.startswith(("http://", "https://")):
        return _res(False, "URL do GitLab deve ser http(s)://")

    endpoint = url + "/api/v4/version"
    headers = dict(_UA)
    if token:
        headers["PRIVATE-TOKEN"] = token

    try:
        with urllib.request.urlopen(urllib.request.Request(endpoint, headers=headers), timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        return _res(False, f"HTTP {e.code} ao consultar GitLab")
    except Exception as e:  # noqa: BLE001
        return _res(False, f"Erro de rede: {e}")

    version = str(data.get("version") or "?")
    if project_path and not token:
        return _res(True, f"GitLab online v{version} (adicione token para validar projeto)")
    if not project_path:
        return _res(True, f"GitLab online v{version}")

    project_api = url + "/api/v4/projects/" + urllib.parse.quote_plus(project_path.strip())
    try:
        with urllib.request.urlopen(urllib.request.Request(project_api, headers=headers), timeout=15) as resp:
            pdata = json.loads(resp.read().decode("utf-8", errors="replace"))
        return _res(True, f"Projeto OK: {pdata.get('path_with_namespace', project_path)}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return _res(False, "Token GitLab invalido ou sem permissao")
        if e.code == 404:
            return _res(False, "Projeto GitLab nao encontrado")
        return _res(False, f"HTTP {e.code} ao validar projeto")
    except Exception as e:  # noqa: BLE001
        return _res(False, f"Erro de rede: {e}")


# ============================================================
# Figma
# ============================================================

def figma_test(token: str = "", file_key: str = "") -> dict[str, Any]:
    """Testa conectividade com a API do Figma."""
    token = (token or "").strip()
    if not token:
        return _res(False, "Token do Figma vazio")

    headers = {**_UA, "X-Figma-Token": token}
    me_url = "https://api.figma.com/v1/me"
    try:
        with urllib.request.urlopen(urllib.request.Request(me_url, headers=headers), timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return _res(False, "Token do Figma invalido ou sem permissao")
        return _res(False, f"HTTP {e.code} ao consultar Figma")
    except Exception as e:  # noqa: BLE001
        return _res(False, f"Erro de rede: {e}")

    handle = str((data.get("handle") or data.get("email") or "usuario")).strip()
    if not file_key:
        return _res(True, f"Figma online ({handle})")

    file_url = "https://api.figma.com/v1/files/" + file_key.strip()
    try:
        with urllib.request.urlopen(urllib.request.Request(file_url, headers=headers), timeout=20) as resp:
            fdata = json.loads(resp.read().decode("utf-8", errors="replace"))
        return _res(True, f"Arquivo OK: {fdata.get('name', file_key)}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return _res(False, "Arquivo Figma nao encontrado")
        return _res(False, f"HTTP {e.code} ao validar arquivo Figma")
    except Exception as e:  # noqa: BLE001
        return _res(False, f"Erro de rede: {e}")


# ============================================================
# MCP / Plugins / Extensoes
# ============================================================

def list_plugins(plugins_dir: str) -> list[dict[str, Any]]:
    """Enumera plugins/agentes MCP detectados na pasta informada.

    Reconhece manifest.json, *.json, *.py e *.mqh como candidatos.
    """
    out: list[dict[str, Any]] = []
    p = Path(plugins_dir) if plugins_dir else Path("plugins")
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    if not p.exists():
        return out
    for f in sorted(p.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() in (".json", ".py", ".mqh", ".yaml", ".yml", ".toml"):
            item = {
                "name": f.stem,
                "file": str(f.relative_to(p.parent)) if f.parent != p else f.name,
                "type": (f.suffix.lstrip(".") or "?").lower(),
                "size": f.stat().st_size,
            }
            out.append(item)
    return out


def mcp_ping(endpoint: str) -> dict[str, Any]:
    """Testa um endpoint MCP/HTTP simples (HEAD/GET)."""
    url = (endpoint or "").strip()
    if not url:
        return _res(False, "Endpoint vazio")
    if not url.startswith(("http://", "https://")):
        return _res(False, "Endpoint deve ser http(s)://")
    req = urllib.request.Request(url, headers=_UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _res(True, f"Endpoint respondeu HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        # 4xx ainda significa que o servidor existe e responde
        if 400 <= e.code < 500:
            return _res(True, f"Endpoint respondeu HTTP {e.code} (autenticacao necessaria)")
        return _res(False, f"HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        return _res(False, f"Sem resposta: {e}")


# ============================================================
# MCP Servers (catalogo configurado em mcp/servers/*.json)
# ============================================================

def instalados() -> list[str]:
    """Lista os IDs dos MCP servers configurados (mcp/servers/*.json).

    Usado pelo marketplace da aba Integracoes para marcar o que já existe.
    """
    try:
        return list(load_mcp_servers().keys())
    except Exception:  # noqa: BLE001
        return []


def catalogo() -> list[dict[str, Any]]:
    """Catálogo de MCP servers disponíveis (formato do marketplace)."""
    try:
        servers = load_mcp_servers()
    except Exception:  # noqa: BLE001
        return []
    return [
        {
            "id": sid,
            "name": rec.get("name", sid),
            "desc": rec.get("description", ""),
            "type": rec.get("type", "http"),
        }
        for sid, rec in servers.items()
    ]


def mcp_pesquisar(termo: str) -> list[dict[str, Any]]:
    """Pesquisa no catálogo de MCP servers por id/nome/descrição/tipo."""
    t = (termo or "").strip().lower()
    if not t:
        return catalogo()
    resultados = [
        it for it in catalogo()
        if t in it.get("id", "").lower()
        or t in it.get("name", "").lower()
        or t in it.get("desc", "").lower()
        or t in it.get("type", "").lower()
    ]
    return resultados


def _endpoint_gateway_mt5(default_endpoint: str, salvo: str) -> str:
    """Endpoint do `mt5_gateway` seguindo o ambiente, como o proprio gateway.

    MEDIDO em 25/10/2026: o gateway ativo escutava em **9011**
    (`XAU_GATEWAY_PORT` no ambiente, processo `mt5-gateway` pid 12044,
    `/health` -> 401) enquanto o catalogo e a config salva apontavam para
    `http://127.0.0.1:9001` - que aqui estava LIVRE. O conector consultava a
    porta errada, dois lados do mesmo dado divergindo (AGENTS.md §5), e o
    sintoma seria "gateway fora do ar" para um gateway no ar.

    Mesma regra, mesma fonte: `backend.trading_mcp.gateway_padrao` - stdlib
    puro, e o mesmo resolver que ja corrigiu o lado do MCP em 22/10/2026.
    Nao ha segunda copia da regra de porta aqui.

    So mexe no que ainda e DEFAULT DE FABRICA (o `9001` do `.json`, ou vazio).
    Porta que o operador digitou e respeitada: o ambiente vence o padrao, nao
    a escolha explicita.
    """
    atual = (salvo or default_endpoint or "").strip().rstrip("/")
    if atual and atual != "http://127.0.0.1:9001":
        return atual
    try:
        from backend.trading_mcp import gateway_padrao  # noqa: PLC0415

        return gateway_padrao(os.environ)
    except Exception:  # noqa: BLE001
        return "http://127.0.0.1:9001"


def load_mcp_servers(
    base: Path | None = None,
    defeitos: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Carrega o catalogo de MCP servers de mcp/servers/*.json.

    Estrutura por server:
      {id: {name, description, type, default_endpoint, enabled, api_key, endpoint}}

    A PASTA E A UNICA FONTE. Nao ha manifest separado: medido em 25/10/2026
    existia `mcp/servers/registry.json` com a lista dos servidores, e este
    loader o IGNORAVA — fazia `glob("*.json")` pulando o proprio registry. O
    arquivo so era lido por um teste que comparava a lista literal, entao a
    pasta e o registro podiam divergir nos dois sentidos sem que nada falhasse.

    Um `.json` que nao parseia ou que nao e objeto VIRAVA SERVIDOR ANONIMO:
    `rec = {}` fazia o catalogo mostrar `name = stem`, `description = ""`, com
    aspecto de servidor valido (regra 5 do AGENTS.md: dois lados do mesmo
    dado, e o operador culpa a coisa errada). Por isso arquivo invalido agora
    e IGNORADO, o motivo vai para `defeitos` - consumido pela etiqueta
    "Instalados" da aba Integracoes - e o teste da pasta reprova em CI com o
    nome do arquivo.

    Parametros:
      `base`      so para teste: pasta temporaria com arquivos quebrados,
                  sem tocar no catalogo real.
      `defeitos`  lista que recebe `{"id": stem, "motivo": str}` de cada
                  arquivo recusado. O loader nao guarda estado: quem quiser
                  os defeitos passa a propria lista, e a regra de parse continua
                  sendo UNICA (nada de segundo lado para divergir).

    `utf-8-sig`, nao `utf-8`: MEDIDO em 25/10/2026 - `Set-Content -Encoding
    UTF8` do PowerShell 5.1 grava BOM, e `json.loads` responde
    `Unexpected UTF-8 BOM`. Com BOM o arquivo e VALIDO (RFC 8259 deixa BOM ser
    ignorado); lido como `utf-8` ele cairia no `except` e sumiria do catalogo
    em silencio. `utf-8-sig` aceita com e sem BOM.

    CAMPOS REMOVIDOS DOS `.json`, com o uso MEDIDO antes de apagar (regra 9 do
    AGENTS.md - controle sem consumidor e pior que ausencia de controle):

      `id`              zero leitores: o loader usa o `stem` do arquivo, e o
                        valor escrito ali podia divergir sem que ninguem visse.
      `needs_api_key`,
      `api_key_env`     zero leitores em Python e zero em `core/src` (o
                        `api_key_env` de `connector_trait.rs` e outro campo,
                        de conector de corretora, e sempre `None`).
      `database_url`,
      `user_id`         liam apenas os ramos `postgres_sqlite`, inalcancaveis:
                        nao ha `.json` com esse id em `mcp/servers/` e
                        `call_tool` recusaria o id como "nao aprovado".

    O teste guarda a lista: `tests/test_app_core.py` reprova campo novo sem
    consumidor, entao nada volta aqui por descuido.

    `base` existe so para teste: permite montar uma pasta temporaria com um
    arquivo quebrado e provar que o loader o rejeita, sem tocar no catalogo real.
    """
    import app.config_manager  # noqa: PLC0415

    cfg = app.config_manager.get_config()
    saved = cfg.get("integrations", "mcp", "servers", default={}) or {}
    pasta = base if base is not None else Path(__file__).resolve().parent.parent / "mcp" / "servers"
    out: dict[str, dict[str, Any]] = {}
    if pasta.is_dir():
        for f in sorted(pasta.glob("*.json")):
            try:
                rec = json.loads(f.read_text(encoding="utf-8-sig"))
            except (ValueError, OSError) as error:
                # Nao vira servidor anonimo: fica DE FORA, com motivo.
                if defeitos is not None:
                    defeitos.append({"id": f.stem, "motivo": f"JSON invalido: {error}"})
                continue
            if not isinstance(rec, dict):
                if defeitos is not None:
                    defeitos.append({"id": f.stem, "motivo": "conteudo nao e um objeto JSON"})
                continue
            sid = f.stem
            saved_rec = saved.get(sid, {}) or {}
            padrao_ep = str(rec.get("default_endpoint", ""))
            salvo_ep = str(saved_rec.get("endpoint", "") or "")
            if sid == "mt5_gateway":
                endpoint = _endpoint_gateway_mt5(padrao_ep, salvo_ep)
            else:
                endpoint = salvo_ep or padrao_ep
            out[sid] = {
                "id": sid,
                "name": rec.get("name", sid.replace("_", " ").title()),
                "description": rec.get("description", ""),
                "type": rec.get("type", "http"),
                "default_endpoint": rec.get("default_endpoint", ""),
                "enabled": bool(saved_rec.get("enabled", rec.get("enabled", False))),
                "endpoint": endpoint,
                "api_key": str(saved_rec.get("api_key", "") or ""),
            }
    return out


def catalogo_defeitos(base: Path | None = None) -> list[dict[str, Any]]:
    """Arquivos do catalogo que o loader recusou, cada um com o motivo.

    Existe para o operador nao ficar sem explicacao: um `.json` corrompido nao
    pode simplesmente sumir do marketplace. Consumidor real: a etiqueta
    "Instalados" da aba Integracoes (app/tabs/integrations.py). Sem consumidor
    isto seria controle de vitrine - regra 9 do AGENTS.md.
    """
    coletados: list[dict[str, Any]] = []
    load_mcp_servers(base, defeitos=coletados)
    return coletados


def mcp_server_ping(server: dict[str, Any]) -> dict[str, Any]:
    """Testa um MCP server pelo conector aprovado dele.

    REMOVIDO em 25/10/2026, com o uso medido antes de apagar:

    - Ramos `sequential_thinking` e `postgres_sqlite`: nenhum dos dois tem
      `.json` em `mcp/servers/`, e `call_tool` rejeita id fora de
      `_ACTIONS_SPECIFIC` com "Server MCP nao aprovado". O ramo era
      inalcancavel DOS DOIS LADOS: nao ha servidor com aquele id, e se
      houvesse, o `call_tool` logo abaixo o recusaria antes de ler a acao.
      (Removido junto o campo `database_url` que so esses ramos liam.)

    - Trecho generico depois do `try` (`type == "http"` -> `mcp_ping`, e
      comando `npx|node|python|uvx` -> `--version`): INALCANCAVEL. `server_id`
      vem do loader sempre preenchido, entao o `if server_id` sempre entrava e
      sempre saia por um dos tres `return` - o codigo abaixo dele nunca rodava.
      Contradizia de proposito `call_tool`, que e explicito: "somente
      conectores aprovados, sem fallback generico". Um fallback generico
      executaria qualquer comando escrito num `.json` solto na pasta.

    Consequencia intencional: servidor fora de `_ACTIONS_SPECIFIC` responde
    "Server MCP nao aprovado: <id>" - recusa com motivo, nao default.
    `mcp_ping` continua existindo: a aba Integracoes o chama direto
    (app/tabs/integrations.py:480).
    """
    server_id = str(server.get("id") or "").strip()
    if not server_id:
        return _res(False, "Servidor sem id")
    try:
        from app.mcp_tools import call_tool

        result = call_tool(
            server_id,
            "health",
            endpoint=server.get("endpoint", ""),
            api_key=server.get("api_key", ""),
        )
        if result.get("ok"):
            payload = result.get("result")
            count = payload.get("count") if isinstance(payload, dict) else None
            suffix = f" ({count} ferramenta(s))" if count is not None else ""
            return _res(True, "Teste funcional concluido" + suffix)
        return _res(False, str(result.get("error") or result.get("result") or "teste falhou"))
    except Exception as error:  # noqa: BLE001
        return _res(False, f"Erro no teste funcional: {error}")
