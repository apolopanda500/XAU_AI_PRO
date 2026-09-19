# -*- coding: utf-8 -*-
"""Fonte unica de verdade da versao do XAU AI PRO.

Le Docs/version.json e propaga a versao para todos os arquivos que a declaram.

Uso:
    python scripts/sync_version.py            # aplica a versao
    python scripts/sync_version.py --check    # apenas verifica (exit 1 se divergir)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "Docs" / "version.json"


def load_version() -> str:
    data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    version = str(data.get("version", "")).strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"versao invalida em {VERSION_FILE}: {version!r}")
    return version


def current_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")

    if path.name == "VERSION":
        stripped = text.strip()
        if re.fullmatch(r"\d+\.\d+\.\d+", stripped):
            return stripped
        return "?"

    if path.suffix == ".json":
        m = re.search(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', text)
        if m:
            return m.group(1)
        return "?"

    if path.suffix == ".toml":
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m and re.fullmatch(r"\d+\.\d+\.\d+", m.group(1)):
            return m.group(1)
        return "?"

    return "?"


def _patch_json(path: Path, version: str) -> bool:
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(r'"version"\s*:\s*"[^"]+"', f'"version": "{version}"', text, count=1)
    if n == 0:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def _patch_toml(path: Path, version: str) -> bool:
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(r'^version\s*=\s*"[^"]+"', f'version = "{version}"', text, count=1, flags=re.MULTILINE)
    if n == 0:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def _patch_version(path: Path, version: str) -> bool:
    new = version + "\n"
    current = path.read_text(encoding="utf-8").rstrip("\n")
    if current == version:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def patch(path: Path, version: str) -> bool:
    if path.name == "VERSION":
        return _patch_version(path, version)
    if path.suffix == ".json":
        return _patch_json(path, version)
    if path.suffix == ".toml":
        return _patch_toml(path, version)
    return False


TARGETS: list[tuple[str, Path]] = [
    ("VERSION", ROOT / "VERSION"),
    ("pyproject.toml", ROOT / "pyproject.toml"),
    ("backend/package.json", ROOT / "backend" / "package.json"),
    ("frontend/package.json", ROOT / "frontend" / "package.json"),
    ("frontend/src-tauri/Cargo.toml", ROOT / "frontend" / "src-tauri" / "Cargo.toml"),
    ("frontend/src-tauri/tauri.conf.json", ROOT / "frontend" / "src-tauri" / "tauri.conf.json"),
    ("core/Cargo.toml", ROOT / "core" / "Cargo.toml"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza a versao do projeto")
    parser.add_argument("--check", action="store_true", help="apenas verifica (exit 1 se divergir)")
    args = parser.parse_args()
    version = load_version()
    divergences: list[str] = []

    for label, path in TARGETS:
        if not path.exists():
            print(f"{label:<40} AUSENTE")
            divergences.append(label)
            continue
        found = current_version(path)
        if args.check:
            status = "OK" if found == version else f"DIVERGENTE ({found})"
            print(f"{label:<40} {status}")
            if found != version:
                divergences.append(label)
            continue
        changed = patch(path, version)
        print(f"{label:<40} {'atualizado' if changed else 'ja correto'} -> {version}")

    if args.check and divergences:
        print(f"\n{len(divergences)} divergencia(s) encontrada(s).")
        print("Rode sem --check para corrigir.")
        return 1

    if args.check:
        print("\nTodos alinhados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())