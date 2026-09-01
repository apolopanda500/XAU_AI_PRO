# -*- coding: utf-8 -*-
"""bump_version.py - Ciclo de versoes mensais do XAU_AI_PRO (fonte unica: VERSION).

Atualiza VERSION + installer.iss (MyAppVersion) + Python/launcher.py (VERSION).

Uso:
  python Tools/bump_version.py --patch   # 1.3.2 -> 1.3.3
  python Tools/bump_version.py --minor   # 1.3.2 -> 1.4.0 (novo ciclo mensal)
  python Tools/bump_version.py --major   # 1.3.2 -> 2.0.0
  python Tools/bump_version.py --set 1.4.0
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
ISS_FILE = ROOT / "installer" / "installer.iss"
LAUNCHER_FILE = ROOT / "Python" / "launcher.py"


def read_current() -> tuple[int, int, int]:
    v = VERSION_FILE.read_text(encoding="utf-8").strip().lstrip("vV")
    parts = (v.split("-")[0]).split(".")
    nums = [int(p) for p in parts[:3]]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)  # type: ignore[return-value]


def write_everywhere(v: str) -> None:
    VERSION_FILE.write_text(v + "\n", encoding="utf-8")

    # installer.iss: #define MyAppVersion "X.Y.Z"
    iss = ISS_FILE.read_text(encoding="utf-8")
    iss_new = re.sub(r'#define MyAppVersion "[^"]+"',
                     f'#define MyAppVersion "{v}"', iss, count=1)
    ISS_FILE.write_text(iss_new, encoding="utf-8")

    # launcher.py: VERSION = "X.Y.Z"
    ln = LAUNCHER_FILE.read_text(encoding="utf-8")
    ln_new = re.sub(r'^VERSION\s*=\s*"[^"]+"',
                    f'VERSION = "{v}"', ln, count=1, flags=re.M)
    LAUNCHER_FILE.write_text(ln_new, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Bump da versao do XAU_AI_PRO")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--patch", action="store_true")
    g.add_argument("--minor", action="store_true")
    g.add_argument("--major", action="store_true")
    g.add_argument("--set", dest="set_v", metavar="X.Y.Z")
    args = ap.parse_args()

    major, minor, patch = read_current()
    if args.set_v:
        if not re.match(r"^\d+\.\d+\.\d+$", args.set_v):
            print("[ERRO] formato esperado X.Y.Z")
            return 1
        v = args.set_v
    elif args.patch:
        patch += 1
        v = f"{major}.{minor}.{patch}"
    elif args.minor:
        minor += 1
        v = f"{major}.{minor}.0"
    else:
        major += 1
        v = f"{major}.0.0"

    write_everywhere(v)
    print(f"[OK] versao atualizada para {v}")
    print("     VERSION / installer.iss / launcher.py sincronizados")
    print()
    print("Proximos passos para o ciclo mensal:")
    print(f'  git commit -am "chore(release): v{v}" && git push')
    print(f'  git tag v{v} && git push --tags   # dispara o CI (build-installer.yml)')
    return 0


if __name__ == "__main__":
    sys.exit(main())