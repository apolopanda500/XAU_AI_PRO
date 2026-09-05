# -*- coding: utf-8 -*-
"""Cliente de IA para o chat (OpenAI-compatible).

Lê a config do app (api.ai_*) e, como fallback, as variaveis de ambiente
OPENAI_API_KEY / CLINE_API_KEY, CLINE_BASE_URL e CLINE_MODEL.

ask_ai() nunca levanta: retorna {"ok": bool, "reply": str, "error": str}.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.config_manager import get_config


def ai_settings() -> dict[str, Any]:
    """Configuracoes de IA atuais (com defaults)."""
    c = get_config()
    return {
        "enabled": bool(c.get("api", "ai_enabled", default=False)),
        "base_url": str(c.get("api", "ai_base_url", default="") or "").strip().rstrip("/"),
        "api_key": str(c.get("api", "ai_api_key", default="") or "").strip(),
        "model": str(c.get("api", "ai_model", default="ollama/deepseek-v4-flash:cloud") or "").strip(),
    }


def _effective_settings() -> dict[str, Any]:
    """Retorna configuracao efetiva, priorizando env vars sobre config salva."""
    s = ai_settings()
    env_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CLINE_API_KEY") or ""
    env_base = os.environ.get("CLINE_BASE_URL") or ""
    env_model = os.environ.get("CLINE_MODEL") or ""
    return {
        "enabled": bool(env_key) or s["enabled"],
        "base_url": env_base or s["base_url"] or "https://api.openai.com/v1",
        "api_key": env_key or s["api_key"] or "anything",
        "model": env_model or s["model"] or "gpt-4o-mini",
    }


def _friendly_http_error(code: int, body: str) -> str:
    """Converte erros comuns da API em orientação acionável."""
    lower = body.lower()
    if code == 401:
        return "HTTP 401 - API key inválida, expirada ou sem permissão"
    if code == 403:
        return "HTTP 403 - acesso negado pelo provedor ou projeto"
    if code == 404:
        return "HTTP 404 - modelo ou endpoint não encontrado"
    if code == 429:
        if "quota" in lower or "billing" in lower or "credit" in lower:
            return "HTTP 429 - quota/créditos da OpenAI esgotados ou billing inativo"
        return "HTTP 429 - limite de requisições atingido; tente novamente mais tarde"
    return f"HTTP {code}"


def _codex_executable() -> str:
    """Localiza o executavel nativo do Codex autenticado no Windows."""
    local_bins = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI" / "Codex" / "bin"
    if local_bins.is_dir():
        candidates = sorted(local_bins.glob("*/codex.exe"), key=lambda item: item.stat().st_mtime, reverse=True)
        if candidates:
            return str(candidates[0])
    return shutil.which("codex.exe") or shutil.which("codex") or ""


def _ask_codex(messages: list[dict[str, str]], timeout: float) -> dict[str, Any]:
    """Usa a sessao ChatGPT autenticada no Codex como fallback local."""
    executable = _codex_executable()
    if not executable:
        return {"ok": False, "reply": "", "error": "Codex CLI nao encontrado"}

    transcript = "\n".join(
        f"{str(message.get('role', 'user')).upper()}: {str(message.get('content', '')).strip()}"
        for message in messages[-12:]
        if str(message.get("content", "")).strip()
    )
    prompt = (
        "Voce e o assistente do aplicativo XAU AI PRO. Responda em portugues, de forma objetiva e segura. "
        "Nao use ferramentas, nao altere arquivos e nao execute comandos.\n\nConversa:\n" + transcript
    )
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        with tempfile.TemporaryDirectory(prefix="xau-ai-codex-") as tmp:
            output_file = Path(tmp) / "reply.txt"
            completed = subprocess.run(
                [
                    executable, "exec", "--ephemeral", "--skip-git-repo-check",
                    "--sandbox", "read-only", "--color", "never",
                    "--output-last-message", str(output_file), "-",
                ],
                input=prompt,
                text=True,
                capture_output=True,
                timeout=max(timeout, 90.0),
                startupinfo=startupinfo,
                check=False,
            )
            reply = output_file.read_text(encoding="utf-8").strip() if output_file.exists() else ""
            if completed.returncode == 0 and reply:
                return {"ok": True, "reply": reply, "error": "", "provider": "codex"}
            return {"ok": False, "reply": "", "error": "Codex autenticado nao respondeu"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reply": "", "error": "Tempo limite excedido ao consultar o Codex"}
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "reply": "", "error": f"Falha no Codex local: {error}"}


def ask_ai(messages: list[dict[str, str]], timeout: float = 25.0) -> dict[str, Any]:
    """Envia mensagens para o modelo configurado e retorna a resposta.

    messages: [{"role": "user"|"assistant", "content": "..."}, ...]
    """
    s = _effective_settings()
    if not s["enabled"]:
        return _ask_codex(messages, timeout)
    base = s["base_url"] or "http://localhost:4000"
    model = s["model"] or "gpt-4o-mini"
    key = s["api_key"] or "anything"

    # Garante o sufixo /v1 quando faltar (LiteLLM local aceita /v1/chat/completions)
    url = base
    if not url.endswith("/v1"):
        # se base já termina em /chat/completions, mantém
        if url.endswith("/chat/completions"):
            endpoint = url
        else:
            endpoint = url + "/v1/chat/completions"
    else:
        endpoint = url + "/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 600,
    }).encode("utf-8")

    req = urllib.request.Request(
        endpoint, data=payload,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "User-Agent": "XAU_AI_PRO/1.3.2"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        reply = ""
        try:
            reply = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            # fallback: data.message.content (respostas do gateway)
            try:
                reply = data["message"]["content"]
            except Exception:
                reply = ""
        if reply:
            return {"ok": True, "reply": str(reply).strip(), "error": ""}
        return _ask_codex(messages, timeout)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            body = ""
        msg = _friendly_http_error(e.code, body)
        if "credit card" in body.lower():
            msg += " - AI Gateway exige cartao de credito na Vercel"
        elif "unauthorized" in body.lower() or "authentication" in body.lower():
            msg += " - chave de API invalida"
        fallback = _ask_codex(messages, timeout)
        if fallback["ok"]:
            return fallback
        return {"ok": False, "reply": "", "error": f"{msg}; {fallback['error']}"}
    except Exception as e:  # noqa: BLE001
        fallback = _ask_codex(messages, timeout)
        if fallback["ok"]:
            return fallback
        return {"ok": False, "reply": "", "error": f"{e}; {fallback['error']}"}


def health_text() -> str:
    """Texto de status curto sobre a IA (para a aba/status)."""
    s = _effective_settings()
    if not s["enabled"]:
        if _codex_executable():
            return "IA real: Codex autenticado (fallback local)"
        return "IA offline (configure uma API ou instale/autentique o Codex CLI)"
    if not s["base_url"]:
        return "IA configurada para LiteLLM local (localhost:4000)"
    suffix = " + fallback Codex" if _codex_executable() else ""
    return f"IA: {s['model']} @ {s['base_url']}{suffix}"
