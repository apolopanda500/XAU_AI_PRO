"""
XAU AI PRO - Integracoes com apps externos
GitHub, Figma e utilitarios de produtividade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class IntegrationResult:
    ok: bool
    message: str
    data: dict[str, Any] | None = None


class GitHubClient:
    """Cliente leve para a API do GitHub."""

    def __init__(self, token: str = "") -> None:
        self.token = token
        self.base = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def test(self) -> IntegrationResult:
        try:
            r = requests.get(f"{self.base}/user", headers=self._headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                return IntegrationResult(
                    ok=True,
                    message=f"Conectado como {data.get('login')} ({data.get('public_repos')} repos publicos)",
                    data=data,
                )
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))

    def list_repos(self, per_page: int = 10) -> IntegrationResult:
        try:
            r = requests.get(
                f"{self.base}/user/repos?sort=updated&per_page={per_page}",
                headers=self._headers(),
                timeout=10,
            )
            if r.status_code == 200:
                repos = r.json()
                return IntegrationResult(
                    ok=True,
                    message=f"{len(repos)} repositorios encontrados",
                    data={"repos": [{"name": x["full_name"], "url": x["html_url"]} for x in repos]},
                )
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))


class FigmaClient:
    """Cliente leve para a API do Figma."""

    def __init__(self, token: str = "") -> None:
        self.token = token
        self.base = "https://api.figma.com/v1"

    def _headers(self) -> dict[str, str]:
        return {"X-Figma-Token": self.token}

    def test(self) -> IntegrationResult:
        if not self.token:
            return IntegrationResult(ok=False, message="Token nao configurado")
        try:
            r = requests.get(f"{self.base}/me", headers=self._headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                return IntegrationResult(ok=True, message=f"Conectado: {data}", data=data)
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))

    def list_projects(self, team_id: str = "") -> IntegrationResult:
        if not self.token:
            return IntegrationResult(ok=False, message="Token nao configurado")
        if not team_id:
            return IntegrationResult(ok=False, message="Informe o team_id")
        try:
            r = requests.get(
                f"{self.base}/teams/{team_id}/projects",
                headers=self._headers(),
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                return IntegrationResult(ok=True, message=f"{len(data.get('projects', []))} projetos", data=data)
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))


class WebSearchClient:
    """Busca web via Brave Search API."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def search(self, query: str, count: int = 5) -> IntegrationResult:
        if not self.api_key:
            return IntegrationResult(ok=False, message="Brave API key nao configurado")
        try:
            r = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                params={"q": query, "count": count},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("web", {}).get("results", [])
                snippets = [f"{x.get('title')}\n{x.get('url')}" for x in results[:count]]
                return IntegrationResult(ok=True, message="Busca concluida", data={"results": snippets})
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))
class SlackClient:
    """Cliente leve para notificações via Incoming Webhook do Slack."""

    def __init__(self, webhook_url: str = "") -> None:
        self.webhook_url = webhook_url.strip() if webhook_url else ""

    def test(self) -> IntegrationResult:
        """Testa a conexão enviando uma mensagem de teste."""
        if not self.webhook_url:
            return IntegrationResult(ok=False, message="Webhook URL nao configurado")
        if not self.webhook_url.startswith("https://hooks.slack.com/services/"):
            return IntegrationResult(ok=False, message="URL invalida (deve ser https://hooks.slack.com/services/...)")
        try:
            payload = {"text": ":white_check_mark: XAU AI PRO — conexao Slack OK!"}
            r = requests.post(self.webhook_url, json=payload, timeout=10)
            if r.status_code == 200:
                return IntegrationResult(ok=True, message="Conectado ao Slack com sucesso")
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))

    def send(self, text: str) -> IntegrationResult:
        """Envia uma mensagem de texto para o canal Slack."""
        if not self.webhook_url:
            return IntegrationResult(ok=False, message="Webhook URL nao configurado")
        try:
            payload = {"text": text, "mrkdwn": True}
            r = requests.post(self.webhook_url, json=payload, timeout=10)
            if r.status_code == 200:
                return IntegrationResult(ok=True, message="Mensagem enviada")
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))
