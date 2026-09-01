# -*- coding: utf-8 -*-
"""Publica os modelos de IA do XAU_AI_PRO como CDN (GitHub Releases + manifest).

Estrategia (thin-installer):
  - Os .pkl (2,3 GB no total) sao publicados num GitHub Release (ate 2 GB/arquivo);
  - O manifest.json (pequeno, com nome/sha256/tamanho/URL de cada modelo) e
    commitado em Models/manifest.json e servido via raw.githubusercontent.com;
  - O app (model_manager.ensure_models) le o manifest e baixa so o que falta.

Uso:
  python publish_models.py --dry-run                 # so mostra o plano
  python publish_models.py --tf M5                   # so modelos M5 (essenciais)
  python publish_models.py --symbols XAUUSD,EURUSD   # filtro por simbolo
  python publish_models.py --upload                  # cria/atualiza o release via gh CLI

Requisitos para --upload: GitHub CLI (gh) autenticado (gh auth login).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "Python" / "models"
OUT_MANIFEST = ROOT / "Models" / "manifest.json"

GITHUB_OWNER = "apolopanda500"
GITHUB_REPO = "XAU_AI_PRO"
RELEASE_TAG = "models-v1.2.0"
RELEASE_URL_BASE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{RELEASE_TAG}"
RAW_MANIFEST_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/Models/manifest.json"


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(models_dir: Path, tf_filter: str | None, symbols: list[str] | None) -> list[Path]:
    pkls = sorted(models_dir.glob("*.pkl"))
    out = []
    for p in pkls:
        stem = p.stem
        if "_" not in stem:
            continue
        sym, tf = stem.rsplit("_", 1)
        if tf_filter and tf.upper() != tf_filter.upper():
            continue
        if symbols and sym.upper() not in [s.upper() for s in symbols]:
            continue
        out.append(p)
    return out


def build_manifest(files: list[Path]) -> dict:
    models = []
    total = 0
    for p in files:
        size = p.stat().st_size
        total += size
        models.append({
            "name": p.name,
            "sha256": sha256_of(p),
            "size": size,
            "url": f"{RELEASE_URL_BASE}/{p.name}",
        })
    return {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "github-releases",
        "manifest_url": RAW_MANIFEST_URL,
        "total_bytes": total,
        "models": models,
    }


def gh_upload(files: list[Path], tag: str) -> int:
    """Cria release DRAFT, faz upload dos arquivos e publica ao final.

    O GitHub (com 'immutable releases' habilitado) so aceita upload de
    assets em releases DRAFT. Por isso: create --draft -> upload -> publish.
    """
    gh = "gh"
    try:
        subprocess.run([gh, "--version"], capture_output=True, check=True)
    except Exception:
        print("[ERRO] gh CLI nao encontrado. Instale: winget install GitHub.cli && gh auth login")
        return 2
    repo = f"{GITHUB_OWNER}/{GITHUB_REPO}"
    # release existe?
    r = subprocess.run([gh, "release", "view", tag, "-R", repo], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[INFO] Release {tag} nao existe; criando como DRAFT...")
        c = subprocess.run([gh, "release", "create", tag, "-R", repo, "--draft",
                            "--title", "XAU AI PRO - Modelos de IA pre-treinados",
                            "--notes", "Modelos .pkl por simbolo/timeframe. Baixados sob demanda pelo app."],
                           capture_output=True, text=True)
        if c.returncode != 0:
            print(f"[ERRO] falha ao criar release: {c.stderr[:300]}")
            return 2
    ok = 0
    for p in files:
        size_mb = p.stat().st_size / 1e6
        print(f"  upload {p.name} ({size_mb:.1f} MB)...")
        u = subprocess.run([gh, "release", "upload", tag, str(p), "-R", repo, "--clobber"],
                           capture_output=True, text=True)
        if u.returncode == 0:
            ok += 1
        else:
            print(f"    [ERRO] {u.stderr[:200]}")
    if ok == len(files):
        # publica o draft (torna o download publico/disponivel)
        pub = subprocess.run([gh, "release", "edit", tag, "-R", repo, "--draft=false"],
                             capture_output=True, text=True)
        if pub.returncode == 0:
            print(f"[OK] {ok}/{len(files)} modelos publicados no release {tag}")
            return 0
        print(f"[AVISO] uploads OK, mas falha ao publicar: {pub.stderr[:200]}")
        return 1
    print(f"[ERRO] apenas {ok}/{len(files)} modelos enviados; release permanece DRAFT.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Publica modelos como CDN (GitHub Releases + manifest)")
    ap.add_argument("--tf", default=None, help="filtra por timeframe (ex.: M5)")
    ap.add_argument("--symbols", default=None, help="filtra por simbolos (ex.: XAUUSD,EURUSD)")
    ap.add_argument("--dry-run", action="store_true", help="mostra o plano sem publicar")
    ap.add_argument("--upload", action="store_true", help="faz upload dos .pkl no release via gh CLI")
    args = ap.parse_args()

    if not MODELS_DIR.exists():
        print(f"[ERRO] pasta de modelos nao encontrada: {MODELS_DIR}")
        return 2

    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    files = collect(MODELS_DIR, args.tf, symbols)
    if not files:
        print("[ERRO] nenhum modelo corresponde aos filtros")
        return 1

    manifest = build_manifest(files)
    total_mb = manifest["total_bytes"] / 1e6
    print(f"Selecionados {len(files)} modelo(s) | total {total_mb:.1f} MB")
    for m in manifest["models"]:
        print(f"  {m['name']:22} {m['size']/1e6:8.1f} MB  sha256={m['sha256'][:12]}...")

    if args.dry_run:
        print("\n[DRY-RUN] Manifest seria gravado em:", OUT_MANIFEST)
        print("[DRY-RUN] Manifest URL publica seria:", RAW_MANIFEST_URL)
        if args.upload:
            print("[DRY-RUN] Upload seria feito no release:", RELEASE_URL_BASE)
        return 0

    # grava manifest local (para commit no repo)
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n[OK] manifest gravado: {OUT_MANIFEST}")
    print(f"     publique com: git add Models/manifest.json && git commit && git push")
    print(f"     URL publica do manifest: {RAW_MANIFEST_URL}")

    if args.upload:
        return gh_upload(files, RELEASE_TAG)

    print("\n[AVISO] --upload nao informado: os .pkl ainda NAO foram publicados.")
    print("        Rode: python publish_models.py --tf M5 --upload")
    return 0


if __name__ == "__main__":
    sys.exit(main())