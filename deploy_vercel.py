# -*- coding: utf-8 -*-
"""Deploy automatico do backend XAU_AI_PRO para a Vercel.

Le VERCEL_TOKEN e VERCEL_PROJECT_ID do .env.local e executa o Vercel CLI
em modo nao-interativo. Pode ser usado standalone ou chamado pelo app.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
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


def deploy(token: str | None = None, project_id: str | None = None,
           prod: bool = True, cwd: Path | None = None) -> dict[str, Any]:
    """Faz deploy do backend via Vercel CLI.

    Retorna dict com ok, message, stdout, stderr, url.
    """
    env = _load_env(ENV)
    token = (token or os.environ.get("VERCEL_TOKEN") or env.get("VERCEL_TOKEN") or "").strip()
    project_id = (project_id or os.environ.get("VERCEL_PROJECT_ID") or env.get("VERCEL_PROJECT_ID") or "").strip()

    if not token:
        return {"ok": False, "message": "VERCEL_TOKEN nao configurado em .env.local", "url": ""}
    if not project_id:
        return {"ok": False, "message": "VERCEL_PROJECT_ID nao configurado em .env.local", "url": ""}

    cwd = cwd or BACKEND
    if not cwd.is_dir():
        return {"ok": False, "message": f"Diretorio do backend nao encontrado: {cwd}", "url": ""}

    cmd = [
        "npx", "vercel", "--token", token, "--yes", "--cwd", str(cwd),
        "--project-id", project_id,
    ]
    if prod:
        cmd.append("--prod")

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
            cwd=str(ROOT),
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined = stdout + "\n" + stderr

        # Procura URL de preview/production no output
        url_match = re.search(r"https://[a-zA-Z0-9._-]+\.vercel\.app", combined)
        url = url_match.group(0) if url_match else ""

        if proc.returncode == 0:
            return {
                "ok": True,
                "message": f"Deploy concluido: {url or 'URL nao detectada no output'}",
                "url": url,
                "stdout": stdout,
                "stderr": stderr,
            }
        return {
            "ok": False,
            "message": f"Deploy falhou (exit {proc.returncode}). Verifique VERCEL_TOKEN e permissao do projeto.",
            "url": url,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "Deploy timeout (180s)", "url": ""}
    except Exception as e:
        return {"ok": False, "message": f"Erro ao executar deploy: {e}", "url": ""}


def main() -> int:
    r = deploy()
    print(r["message"])
    if r.get("url"):
        print(f"URL: {r['url']}")
    if not r["ok"]:
        if r.get("stderr"):
            print("--- stderr ---")
            print(r["stderr"])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
