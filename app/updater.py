# -*- coding: utf-8 -*-
"""Auto-atualizacao do XAU_AI_PRO via GitHub Releases.

Fluxo (modelo de atualizacao mensal v1.3.x):
  1) latest_release() consulta a API do GitHub pelo release mais recente;
  2) check_update() compara a versao local (VERSION) com a do release;
  3) download_asset() baixa o XAU_AI_PRO_Setup.exe com progresso;
  4) install_update() executa o instalador baixado (o app deve ser fechado).

Seguranca: so baixa assets do repositorio oficial (owner/repo fixos).
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

GITHUB_OWNER = "apolopanda500"
GITHUB_REPO = "XAU_AI_PRO"
API_LATEST = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
_UA = {"User-Agent": "XAU_AI_PRO-updater/1.3.2"}


def _res(ok: bool, **kw: Any) -> dict[str, Any]:
    return {"ok": ok, **kw}


def local_version() -> str:
    """Le a versao local do arquivo VERSION na raiz do projeto."""
    root = Path(__file__).resolve().parent.parent
    vfile = root / "VERSION"
    if vfile.exists():
        return vfile.read_text(encoding="utf-8").strip()
    return "1.3.2"


def parse_semver(v: str) -> tuple[int, ...]:
    """'v1.3.2' -> (1, 3, 2). Ignora prefixo v/V e sufixos (-rc1 etc.)."""
    v = v.strip().lstrip("vV")
    core = v.split("-")[0]
    parts = []
    for p in core.split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(remote: str, local: str) -> bool:
    return parse_semver(remote) > parse_semver(local)


def latest_release(timeout: int = 15) -> dict[str, Any]:
    """Consulta o release mais recente publicado. Nunca levanta excecao."""
    req = urllib.request.Request(API_LATEST, headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return _res(True,
                    tag=data.get("tag_name", ""),
                    name=data.get("name", ""),
                    notes=(data.get("body") or "")[:500],
                    assets=data.get("assets", []))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return _res(False, error="Nenhum release publicado ainda")
        return _res(False, error=f"HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        return _res(False, error=f"Sem conexao: {e}")


def check_update() -> dict[str, Any]:
    """Compara versao local com o ultimo release.

    Retorna {ok, has_update, local, remote, asset{name,url,size}, notes, error}.
    """
    local = local_version()
    rel = latest_release()
    if not rel.get("ok"):
        return _res(False, has_update=False, local=local, error=rel.get("error", ""))
    remote = rel.get("tag", "")
    has = is_newer(remote, local)
    asset = None
    for a in rel.get("assets", []):
        if a.get("name", "").lower() == "xau_ai_pro_setup.exe":
            asset = {"name": a["name"], "url": a.get("browser_download_url", ""),
                     "size": a.get("size", 0)}
            break
    return _res(True, has_update=has, local=local, remote=remote,
                asset=asset, notes=rel.get("notes", ""))


def download_asset(url: str, dest: Path,
                   progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    """Baixa o asset com callback de progresso (baixados, total)."""
    if not url.startswith(f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/"):
        return _res(False, error="URL de origem nao autorizada")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as fh:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        tmp.replace(dest)
        return _res(True, path=str(dest), size=dest.stat().st_size)
    except Exception as e:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        return _res(False, error=f"Falha no download: {e}")


def install_update(setup_path: str | Path) -> dict[str, Any]:
    """Executa o instalador baixado. O app deve ser fechado pelo usuario."""
    p = Path(setup_path)
    if not p.exists():
        return _res(False, error="Instalador nao encontrado")
    try:
        subprocess.Popen(["cmd", "/c", "start", "", str(p)], close_fds=True)
        return _res(True, message="Instalador iniciado. Feche o XAU AI PRO para concluir.")
    except Exception as e:  # noqa: BLE001
        return _res(False, error=f"Falha ao iniciar: {e}")


class AppUpdater:
    """Interface orientada a objetos para o sistema de atualizacao.

    Mantida como wrapper leve em cima das funcoes modulares definidas acima
    (latest_release, check_update, download_asset, install_update) para facilitar
    o uso dentro da GUI sem precisar importar cada funcao individualmente.
    """
    owner = GITHUB_OWNER
    repo = GITHUB_REPO

    @staticmethod
    def latest_release(timeout: int = 15) -> dict:
        return latest_release(timeout=timeout)

    @staticmethod
    def check_update() -> dict:
        return check_update()

    @staticmethod
    def download_asset(url: str, dest, progress=None) -> dict:
        if isinstance(dest, str):
            dest = Path(dest)
        return download_asset(url, dest, progress)

    @staticmethod
    def install_update(setup_path) -> dict:
        return install_update(setup_path)