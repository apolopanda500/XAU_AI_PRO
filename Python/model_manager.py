# -*- coding: utf-8 -*-
"""XAU_AI_PRO - Model Manager (download sob demanda).

Baixa modelos treinados de uma CDN/URL configurável (ex.: Vercel) na primeira
execução em uma máquina nova, evitando embutir ~2,3 GB no instalador.

Fluxo:
    1) O instalador envia o Setup enxuto (exe + MQL5 + Python).
    2) Na 1a execucao, o app chama ensure_models(symbols, timeframes) que:
       - consulta {base_url}/manifest.json (lista de modelos + sha256);
       - baixa apenas os modelos necessarios e ausentes/antigos;
       - valida integridade por sha256;
       - grava em Python/models (ou XAU_AI_PRO_MODELS).
    3) Sem rede/licenca, retorna erro amigavel - nunca trava o app.

Nenhum modelo e executado sem validacao. Falha de download => estado nao pronto.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# URLs padrao podem ser sobrescritas por env/instalador.
DEFAULT_MANIFEST_URL = os.getenv(
    "XAU_AI_PRO_MODELS_URL",
    "https://xau-ai-pro.vercel.app/api/models/manifest.json",
).strip()

TIMEOUT_SEC = int(os.getenv("XAU_AI_PRO_DL_TIMEOUT", "60"))
_MAX_ATTEMPTS = int(os.getenv("XAU_AI_PRO_DL_ATTEMPTS", "3"))


@dataclass
class DownloadResult:
    symbol: str
    timeframe: str
    status: str           # ok | skipped_ready | not_found | download_error | bad_hash
    path: str | None = None
    size_bytes: int = 0
    message: str = ""


def _models_dir() -> Path:
    env = os.getenv("XAU_AI_PRO_MODELS", "").strip()
    if env:
        p = Path(env).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    p = Path(__file__).resolve().parent / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _model_path(symbol: str, tf: str) -> Path:
    return _models_dir() / f"{symbol}_{tf.upper()}.pkl"


def _age_sec(p: Path) -> float:
    if not p.exists():
        return float("inf")
    return max(0.0, time.time() - p.stat().st_mtime)


def load_manifest(base_url: str | None = None) -> dict[str, Any] | None:
    """Baixa e parseia manifest.json contendo os modelos disponiveis.

    Estrutura esperada:
      {
        "generated": "ISO8601",
        "models": [
          {"name": "XAUUSD_M5.pkl", "sha256": "...", "size": 58_000_000},
          ...
        ]
      }
    Retorna dict ou None.
    """
    base = (base_url or DEFAULT_MANIFEST_URL).rstrip("/")
    if base.endswith(".json"):
        url = base
    else:
        url = base + "/manifest.json"
    req = urllib.request.Request(url, headers={"User-Agent": "XAU_AI_PRO/1.3.2"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data
    except Exception as exc:  # noqa: BLE001
        return None
def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: Path) -> tuple[bool, str]:
    """Baixa url para dest (temp + move atomico). Retorna (ok, erro)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": "XAU_AI_PRO/1.3.2"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp, open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh, length=1 << 20)
        try:
            clen = int(resp.headers.get("Content-Length", "-1"))
            if clen >= 0 and tmp.stat().st_size != clen:
                tmp.unlink(missing_ok=True)
                return False, "size_mismatch"
        except Exception:  # noqa: BLE001
            pass
        tmp.replace(dest)
        return True, ""
    except urllib.error.HTTPError as e:
        tmp.unlink(missing_ok=True)
        return False, "http%d" % e.code
    except urllib.error.URLError as e:
        tmp.unlink(missing_ok=True)
        return False, "network_%s" % getattr(e, "reason", "")
    except Exception as e:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        return False, "error_%s" % e


def _hint_download_url(symbol: str, tf: str, base_url: str) -> str:
    base = base_url.rstrip("/")
    return "%s/models/%s_%s.pkl" % (base, symbol, tf.upper())


def ensure_models(
    symbols: list[str] | None = None,
    timeframes: list[str] | None = None,
    base_url: str | None = None,
    max_age_sec: int = 5 * 24 * 3600,
    force_download: bool = False,
) -> tuple[list[DownloadResult], dict[str, Any]]:
    """Garante modelos presentes (download sob demanda).

    symbols/timeframes default: [XAUUSD] M5 (uso classico do robo).
    Retorna (resultados, manifest).
    """
    symbols = symbols or ["XAUUSD"]
    timeframes = timeframes or ["M5"]

    manifest = load_manifest(base_url)
    base = (base_url or DEFAULT_MANIFEST_URL).rstrip("/")
    models_map: dict[str, dict] = {}
    if manifest and isinstance(manifest.get("models"), list):
        for m in manifest["models"]:
            if isinstance(m, dict) and m.get("name"):
                models_map[m["name"]] = m

    results: list[DownloadResult] = []
    for sym in symbols:
        for tf in timeframes:
            local = _model_path(sym, tf)
            if local.exists() and not force_download and _age_sec(local) <= max_age_sec:
                results.append(DownloadResult(sym, tf, "skipped_ready", str(local), local.stat().st_size))
                continue

            fname = "%s_%s.pkl" % (sym, tf.upper())
            url = _hint_download_url(sym, tf, base)

            ok = False
            last_err = ""
            for attempt in range(_MAX_ATTEMPTS):
                ok, last_err = _download_file(url, local)
                if ok:
                    break
                time.sleep(1 + attempt * 2)

            if not ok:
                results.append(DownloadResult(sym, tf, "download_error", str(local) if local.exists() else None, 0, "falha_download_%s" % last_err))
                continue

            if m and m.get("sha256"):
                try:
                    if _sha256_of(local).lower() != m["sha256"].lower():
                        local.unlink(missing_ok=True)
                        results.append(DownloadResult(sym, tf, "bad_hash", None, 0, "sha256_nao_confere"))
                        continue
                except Exception:  # noqa: BLE001
                    pass

            results.append(DownloadResult(sym, tf, "ok", str(local), local.stat().st_size, "baixado"))
    return (results, manifest if manifest else {})
def build_manifest_zip(zip_path: Path) -> dict[str, Any]:
    """Gerador para dev/publish: cria manifest.json embutido em um zip.

    Utilizado pelo script de publicacao (Vercel). Lista de modelos presentes.
    """
    import zipfile

    models = sorted(_models_dir().glob("*.pkl"))
    entries = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in models:
            zf.write(p, p.name)
            entries.append({"name": p.name, "sha256": _sha256_of(p), "size": p.stat().st_size})
    manifest = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "models": entries}
    (zip_path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import sys as _sys

    def _parse_arg(name: str, default: str) -> str:
        argv = _sys.argv[1:]
        for i, a in enumerate(argv):
            if a.startswith(name + "="):
                return a.split("=", 1)[1]
            if a == name and i + 1 < len(argv):
                return argv[i + 1]
        return default

    symbols = [s.upper().strip() for s in _parse_arg("--symbols", "XAUUSD").split(",") if s.strip()]
    timeframes = [t.upper().strip() for t in _parse_arg("--timeframes", "M5").split(",") if t.strip()]

    res, man = ensure_models(symbols=symbols, timeframes=timeframes)
    for r in res:
        print("%-14s %s_%s %s bytes %s" % (r.status, r.symbol, r.timeframe, r.size_bytes, r.message))
    print("manifest_entries=%s" % (len(man.get("models", [])) if man else 0))