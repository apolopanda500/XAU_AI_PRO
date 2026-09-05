# -*- coding: utf-8 -*-
"""Deploy automatico do backend XAU_AI_PRO via Vercel Deploy Hook.

O Deploy Hook permite disparar um novo deploy sem autenticacao adicional,
bastando fazer um POST na URL fornecida no dashboard do projeto Vercel.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    import requests
except Exception:  # noqa: BLE001
    requests = None

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
ENV = ROOT / ".env.local"


def _load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def get_deploy_hook() -> str:
    """Retorna a URL do deploy hook a partir das env vars ou .env.local."""
    env = _load_env(ENV)
    return (
        os.environ.get("VERCEL_DEPLOY_HOOK_URL", "")
        or env.get("VERCEL_DEPLOY_HOOK_URL", "")
        or ""
    )


def trigger_deploy(hook_url: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """Dispara o deploy hook do Vercel.

    Retorna dict com ok, message, job_id, state, url.
    """
    if requests is None:
        return {
            "ok": False,
            "message": "Dependencia 'requests' nao instalada. Instale requirements.txt para habilitar deploy Vercel.",
            "job_id": "",
            "state": "",
            "url": "",
        }

    url = (hook_url or get_deploy_hook()).strip()
    if not url:
        return {
            "ok": False,
            "message": "VERCEL_DEPLOY_HOOK_URL nao configurada.\n"
                       "Va em Integracoes > Deploy Vercel e cole a URL do Deploy Hook.",
            "job_id": "",
            "state": "",
            "url": "",
        }

    if not url.startswith("https://api.vercel.com/v1/integrations/deploy/"):
        return {
            "ok": False,
            "message": "URL do Deploy Hook invalida.",
            "job_id": "",
            "state": "",
            "url": "",
        }

    try:
        resp = requests.post(url, timeout=timeout)
        data = resp.json() if resp.text else {}
        if resp.status_code in (200, 201):
            job = data.get("job", {})
            return {
                "ok": True,
                "message": f"Deploy iniciado com sucesso (job: {job.get('id', 'n/a')}, state: {job.get('state', 'n/a')}).",
                "job_id": job.get("id", ""),
                "state": job.get("state", ""),
                "url": data.get("url", ""),
            }
        return {
            "ok": False,
            "message": f"Deploy hook retornou {resp.status_code}: {data.get('error', {}).get('message', resp.text)}",
            "job_id": data.get("job", {}).get("id", ""),
            "state": data.get("job", {}).get("state", ""),
            "url": "",
        }
    except requests.exceptions.Timeout:
        return {"ok": False, "message": "Timeout ao acionar deploy hook.", "job_id": "", "state": "", "url": ""}
    except Exception as e:
        return {"ok": False, "message": f"Erro ao acionar deploy hook: {e}", "job_id": "", "state": "", "url": ""}


def check_status(job_id: str, token: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """Consulta status do job de deploy via API Vercel (requer token)."""
    if requests is None:
        return {"ok": False, "message": "Dependencia 'requests' nao instalada."}
    if not job_id:
        return {"ok": False, "message": "job_id vazio"}
    tok = (token or os.environ.get("VERCEL_TOKEN", "") or _load_env(ENV).get("VERCEL_TOKEN", "")).strip()
    if not tok:
        return {"ok": True, "message": "Deploy em andamento (token nao configurado para consulta de status)."}
    try:
        resp = requests.get(
            f"https://api.vercel.com/v2/deployments/{job_id}",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=timeout,
        )
        data = resp.json() if resp.text else {}
        if resp.status_code == 200:
            state = data.get("readyState", "UNKNOWN")
            url = data.get("url", "")
            return {"ok": True, "message": f"Status do deploy: {state} | URL: {url}", "state": state, "url": url}
        return {"ok": False, "message": f"API retornou {resp.status_code}: {data}"}
    except Exception as e:
        return {"ok": False, "message": f"Erro ao consultar status: {e}"}


def main() -> int:
    r = trigger_deploy()
    print(r["message"])
    if r.get("job_id"):
        print(f"Job ID: {r['job_id']}")
    if r.get("url"):
        print(f"URL: {r['url']}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
