# -*- coding: utf-8 -*-
"""Clientes de integracao do XAU_AI_PRO (GitHub, Sentry, Slack, Vercel/Modelos, MCP/Plugins).

Funcoes de teste de conexao usadas pela aba de Integracoes.
Todas retornam dict {ok, message} e NUNCA levantam excecao.
"""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_UA = {"User-Agent": "XAU_AI_PRO/1.3.2"}


def _res(ok: bool, message: str) -> dict[str, Any]:
    return {"ok": ok, "message": message}


# ============================================================
# GitHub
# ============================================================

def github_test(repo_url: str, token: str = "") -> dict[str, Any]:
    """Testa acesso ao repositorio via 'git ls-remote' (publico ou com token)."""
    url = (repo_url or "").strip()
    if not url:
        return _res(False, "URL do repositorio vazia")
    if token and url.startswith("https://") and "@" not in url:
        url = url.replace("https://", "https://" + token + "@", 1)
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--heads", url],
            capture_output=True, text=True, timeout=25,
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
    if not token:
        return _res(False, "Sem token: push exigira credenciais do Credential Manager")
    return _res(True, "Token configurado (escopo repo necessario para push)")


# ============================================================
# Slack (webhook)
# ============================================================

def slack_test(webhook_url: str, text: str = "XAU AI PRO - teste de conexao") -> dict[str, Any]:
    url = (webhook_url or "").strip()
    if not url:
        return _res(False, "Webhook URL vazia")
    if not url.startswith("https://hooks.slack.com/"):
        return _res(False, "URL nao parece ser um webhook do Slack (hooks.slack.com)")
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={**_UA, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return _res(True, "Mensagem de teste enviada ao canal")
            return _res(False, "HTTP %d" % resp.status)
    except urllib.error.HTTPError as e:
        return _res(False, "HTTP %d: webhook invalido ou revogado" % e.code)
    except Exception as e:  # noqa: BLE001
        return _res(False, "Erro de rede: %s" % e)


# ============================================================
# Sentry
# ============================================================

def sentry_test(dsn: str) -> dict[str, Any]:
    """Valida o formato do DSN e envia um evento de teste (level info)."""
    dsn = (dsn or "").strip()
    if not dsn:
        return _res(False, "DSN vazio")
    if not (dsn.startswith("https://") and ".ingest." in dsn):
        return _res(False, "DSN com formato inesperado (esperado https://<key>@<org>.ingest.sentry.io/<id>)")
    try:
        import sentry_sdk  # noqa: PLC0415
        # Novo client isolado apenas para o teste (nao interfere no global)
        client = sentry_sdk.Client(dsn=dsn)
        transport_ok = client.transport is not None
        if not transport_ok:
            return _res(False, "Transporte do Sentry nao inicializado")
        from sentry_sdk import Scope  # noqa: PLC0415
        scope = Scope(client=client)
        event_id = scope.capture_message("XAU AI PRO - teste de conexao", level="info")
        client.close()
        if event_id:
            return _res(True, f"Evento de teste enviado (id {str(event_id)[:8]})")
        return _res(False, "Evento nao enviado (DSN recusado?)")
    except ImportError:
        return _res(False, "sentry_sdk nao instalado neste ambiente")
    except Exception as e:  # noqa: BLE001
        return _res(False, f"Erro: {e}")


# ============================================================
# Vercel / CDN de modelos (manifest)
# ============================================================

def models_url_test(base_url: str) -> dict[str, Any]:
    """Testa se o manifest.json de modelos responde e quantos modelos tem."""
    url = (base_url or "").strip()
    if not url:
        return _res(False, "URL dos modelos vazia")
    try:
        # import tardio: Python/model_manager.py (raiz do projeto no sys.path)
        import model_manager  # noqa: PLC0415
    except ImportError:
        try:  # fallback quando rodando como pacote app.*
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Python"))
            import model_manager  # noqa: PLC0415
        except ImportError:
            return _res(False, "model_manager.py nao encontrado")
    try:
        man = model_manager.load_manifest(url)
        if not man:
            return _res(False, "Manifest nao respondeu (URL offline?)")
        n = len(man.get("models", []))
        gen = man.get("generated", "?")
        return _res(True, f"Manifest OK: {n} modelo(s) publicado(s) em {gen}")
    except Exception as e:  # noqa: BLE001
        return _res(False, f"Erro: {e}")


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