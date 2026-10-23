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

    if path.name == "version.ts":
        m = re.search(r"APP_VERSION\s*=\s*'([^']+)'", text)
        if m:
            return m.group(1)
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
    if new == text:  # ja estava certo: nao reporta "atualizado" mentindo
        return False
    path.write_text(new, encoding="utf-8")
    return True


def _patch_toml(path: Path, version: str) -> bool:
    # Todas as ocorrencias, nao so a primeira: pyproject.toml declara a versao
    # em [tool.poetry] E em [project], e atualizar so uma deixa as duas
    # divergentes — exatamente o bug que existia na 1.2.4.
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
        text,
        flags=re.MULTILINE,
    )
    if n == 0:
        return False
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def _patch_app_version(path: Path, version: str) -> bool:
    """frontend/src/version.ts: a versao mostrada na interface."""
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(
        r"export const APP_VERSION = '[^']*'",
        f"export const APP_VERSION = '{version}'",
        text,
        count=1,
    )
    if n == 0:
        return False
    if new == text:  # ja estava certo
        return False
    path.write_text(new, encoding="utf-8")
    return True


def build_esperado(version: str) -> str:
    """A MESMA string que `backend/mt5_gateway.py::_gateway_build()` produz.

    MEDIDO 22/10/2026: main.rs e main.tsx traziam `xau-ai-pro-1.2.4-...`
    escrito a mao. Na 1.2.5 o gateway passou a responder
    `xau-ai-pro-1.2.5-universal-20261022`, os dois clientes compararam com a
    string velha, recusaram a identidade e o app abriu com a tela preta
    "Falha ao inicializar o ambiente local seguro". Uma fonte, tres leitores:
    quem deriva e o gateway, e os clientes recebem o valor daqui.
    """
    data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    suffix = str(data.get("gateway_build_suffix", "universal")).strip() or "universal"
    updated = str(data.get("updated_at", "")).strip().replace("-", "")
    stamp = updated if len(updated) == 8 and updated.isdigit() else "20260928"
    return f"xau-ai-pro-{version}-{suffix}-{stamp}"


def _patch_gateway_build(path: Path, build: str) -> bool:
    """version.ts: a identidade que o frontend exige do gateway."""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    linha = f"export const GATEWAY_BUILD = '{build}';"
    if "export const GATEWAY_BUILD" in text:
        new, n = re.subn(
            r"export const GATEWAY_BUILD = '[^']*'", linha, text, count=1
        )
        if n == 0 or new == text:
            return False
        path.write_text(new, encoding="utf-8")
        return True
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(
        text
        + "\n/** Build do gateway exigido pelo bootstrap; gerado por sync_version.py. */\n"
        + linha
        + "\n",
        encoding="utf-8",
    )
    return True


def _patch_version(path: Path, version: str) -> bool:
    new = version + "\n"
    current = path.read_text(encoding="utf-8").strip()
    if current == version:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def patch(path: Path, version: str) -> bool:
    if path.name == "VERSION":
        return _patch_version(path, version)
    if path.name == "version.ts":
        return _patch_app_version(path, version)
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
    ("frontend/src/version.ts", ROOT / "frontend" / "src" / "version.ts"),
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

    # A identidade do gateway sai da MESMA fonte. O Rust le via build.rs e o
    # frontend via `version.ts`; nenhum dos dois pode escrever a string a mao.
    build = build_esperado(version)
    alvo_ts = ROOT / "frontend" / "src" / "version.ts"
    if args.check:
        texto = alvo_ts.read_text(encoding="utf-8") if alvo_ts.exists() else ""
        ok = f"GATEWAY_BUILD = '{build}'" in texto
        print(f"{'frontend/src/version.ts (build)':<40} {'OK' if ok else 'DIVERGENTE'}")
        if not ok:
            divergences.append("frontend/src/version.ts (build)")
    else:
        mudou = _patch_gateway_build(alvo_ts, build)
        print(f"{'frontend/src/version.ts (build)':<40} {'atualizado' if mudou else 'ja correto'} -> {build}")

    if args.check and divergences:
        print(f"\n{len(divergences)} divergencia(s) encontrada(s).")
        print("Rode sem --check para corrigir.")
        return 1

    if args.check:
        print("\nTodos alinhados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())