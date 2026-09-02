# -*- coding: utf-8 -*-
"""Cliente de IA para o chat (OpenAI-compatible).

Lê a config do app (api.ai_*):
  - api.ai_enabled   : se True tenta conexão real; senão offline
  - api.ai_base_url  : URL base OpenAI-compatible (ex.: http://localhost:4000/v1,
                       https://ai-gateway.vercel.sh/v1)
  - api.ai_api_key   : chave (para LiteLLM local pode ser "anything")
  - api.ai_model     : modelo (ex.: ollama/deepseek-v4-flash:cloud,
                       openai/gpt-5.6-sol)

ask_ai() nunca levanta: retorna {"ok": bool, "reply": str, "error": str}.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
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


def ask_ai(messages: list[dict[str, str]], timeout: float = 25.0) -> dict[str, Any]:
    """Envia mensagens para o modelo configurado e retorna a resposta.

    messages: [{"role": "user"|"assistant", "content": "..."}, ...]
    """
    s = ai_settings()
    if not s["enabled"]:
        return {"ok": False, "reply": "", "error": "IA desativada (marque 'Habilitar IA' nas Configuracoes)"}
    base = s["base_url"] or "http://localhost:4000"
    model = s["model"] or "ollama/deepseek-v4-flash:cloud"
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
        return {"ok": False, "reply": "", "error": "Resposta vazia do modelo"}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            body = ""
        msg = f"HTTP {e.code}"
        if "credit card" in body.lower():
            msg += " - AI Gateway exige cartao de credito na Vercel"
        elif "unauthorized" in body.lower() or "authentication" in body.lower():
            msg += " - chave de API invalida"
        return {"ok": False, "reply": "", "error": msg}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reply": "", "error": str(e)}


def health_text() -> str:
    """Texto de status curto sobre a IA (para a aba/status)."""
    s = ai_settings()
    if not s["enabled"]:
        return "IA offline (desativada)"
    if not s["base_url"]:
        return "IA configurada para LiteLLM local (localhost:4000)"
    return f"IA: {s['model']} @ {s['base_url']}"