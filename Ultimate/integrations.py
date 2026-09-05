"""
XAU AI PRO - Integracoes com apps externos.
GitHub, GitLab, Figma, MCP local e utilitarios de produtividade.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


class GitLabClient:
    """Cliente leve para a API do GitLab."""

    def __init__(self, base_url: str = "https://gitlab.com", token: str = "") -> None:
        self.base = (base_url or "https://gitlab.com").strip().rstrip("/")
        self.token = token.strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["PRIVATE-TOKEN"] = self.token
        return headers

    def test(self) -> IntegrationResult:
        if not self.base.startswith(("http://", "https://")):
            return IntegrationResult(ok=False, message="URL do GitLab deve comecar com http:// ou https://")
        try:
            r = requests.get(f"{self.base}/api/v4/version", headers=self._headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                return IntegrationResult(ok=True, message=f"GitLab online v{data.get('version', '?')}", data=data)
            return IntegrationResult(ok=False, message=f"Erro {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(ok=False, message=str(e))

    def project(self, project_path: str) -> IntegrationResult:
        project_path = (project_path or "").strip()
        if not project_path:
            return self.test()
        try:
            r = requests.get(
                f"{self.base}/api/v4/projects/{requests.utils.quote(project_path, safe='')}",
                headers=self._headers(),
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                return IntegrationResult(
                    ok=True,
                    message=f"Projeto OK: {data.get('path_with_namespace', project_path)}",
                    data=data,
                )
            if r.status_code == 401:
                return IntegrationResult(ok=False, message="Token GitLab invalido ou sem permissao")
            if r.status_code == 404:
                return IntegrationResult(ok=False, message="Projeto GitLab nao encontrado")
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


class MCPClient:
    """Inspeciona MCP local e testa endpoint HTTP simples."""

    def __init__(self, endpoint: str = "", plugins_dir: str = "") -> None:
        self.endpoint = (endpoint or "").strip()
        self.plugins_dir = (plugins_dir or "").strip()

    def test(self) -> IntegrationResult:
        if self.endpoint:
            if not self.endpoint.startswith(("http://", "https://")):
                return IntegrationResult(ok=False, message="Endpoint MCP deve comecar com http:// ou https://")
            try:
                r = requests.get(self.endpoint, timeout=8)
                return IntegrationResult(
                    ok=(r.status_code < 400),
                    message=f"Endpoint MCP respondeu HTTP {r.status_code}",
                    data={"status_code": r.status_code},
                )
            except Exception as e:
                return IntegrationResult(ok=False, message=str(e))

        base = Path(self.plugins_dir) if self.plugins_dir else (Path(__file__).resolve().parent.parent / "mcp")
        if not base.is_absolute():
            base = Path(__file__).resolve().parent.parent / base
        if not base.exists():
            return IntegrationResult(ok=False, message=f"Pasta MCP nao encontrada: {base}")
        files = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in (".json", ".py", ".yaml", ".yml", ".toml")]
        data = {"files": [str(p.relative_to(base.parent)) for p in files[:30]]}
        return IntegrationResult(ok=True, message=f"{len(files)} arquivo(s) MCP/plugin detectado(s)", data=data)
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
