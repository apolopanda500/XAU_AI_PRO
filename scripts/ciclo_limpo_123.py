# -*- coding: utf-8 -*-
"""Ciclo novo, limpo e completo v1.2.3 — executa em segundo plano com log.

EA intocavel: este script nunca toca em MQL5/Experts.
Uso: .\\.venv\\Scripts\\python.exe scripts\\ciclo_limpo_123.py
Acompanhe: Get-Content Logs\\ciclo_limpo_123.log -Wait -Tail 30
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "Logs"
LOG_FILE = LOG_DIR / "ciclo_limpo_123.log"
VERSION = "1.2.3"


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(cmd: list[str], cwd: Path | None = None) -> None:
    log(f"$ {' '.join(cmd)} (cwd={cwd or ROOT})")
    proc = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True)
    if proc.stdout.strip():
        for line in proc.stdout.strip().splitlines()[-8:]:
            log(f"  out: {line}")
    if proc.returncode != 0:
        if proc.stderr.strip():
            for line in proc.stderr.strip().splitlines()[-15:]:
                log(f"  err: {line}")
        raise SystemExit(f"falhou ({proc.returncode}): {' '.join(cmd)}")
    log("  OK")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def etapa_higiene() -> None:
    log("--- [1/8] Higiene ---")
    for target in (ROOT / "build", ROOT / "dist" / "frontend"):
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            log(f"removido: {target}")
    for pycache in ROOT.rglob("__pycache__"):
        if ".venv" not in pycache.parts:
            shutil.rmtree(pycache, ignore_errors=True)
    for pyc in ROOT.rglob("*.pyc"):
        if ".venv" not in pyc.parts:
            pyc.unlink(missing_ok=True)
    for name in ("build_log.txt", "build_log2.txt", "versao_log.txt"):
        (ROOT / name).unlink(missing_ok=True)
    for tmp in ROOT.glob(".pytest-tmp-*"):
        shutil.rmtree(tmp, ignore_errors=True)
    old_setup = ROOT / "installer" / "XAU_AI_PRO_Setup_1.2.0.exe"
    if old_setup.exists():
        old_setup.unlink()
        log("instalador 1.2.0 antigo removido")
    log("higiene concluida")

def etapa_versao_testes(py: Path) -> None:
    log("--- [2/8] Versao unica ---")
    run([str(py), "scripts/sync_version.py", "--check"])
    log("--- [3/8] Testes em 3 lotes ---")
    run([str(py), "-m", "pytest", "-q",
         "tests/test_universal_router_dispatch.py", "tests/test_universal_execution.py",
         "tests/test_execution_adapters.py", "tests/test_risk_gate.py",
         "tests/test_reconciliation_controlled.py", "tests/test_connection_contract.py",
         "tests/test_audit_log.py", "tests/test_emergency_stop.py",
         "tests/test_universal_account.py", "--disable-warnings"])
    run([str(py), "-m", "pytest", "-q", "tests/test_gateway_endpoints.py", "--disable-warnings"])
    run([str(py), "-m", "pytest", "-q", "tests/test_app_core.py", "tests/test_chart_indicators.py",
         "tests/test_market_store.py", "tests/test_mcp_status.py", "tests/test_mt5_sync_status.py",
         "tests/test_tools_alerts.py", "tests/test_topnav.py", "tests/test_table_diff.py",
         "tests/test_sidebar_compact.py", "tests/test_scrollable_preserve.py",
         "tests/test_runtime_paths.py", "tests/test_financial_subgraph.py",
         "tests/test_ai_client_codex.py", "tests/test_integrations_client.py", "--disable-warnings"])


def etapa_frontend_gateway(py: Path) -> None:
    log("--- [4/8] Frontend (tsc + vite) ---")
    npx = shutil.which("npx") or str(ROOT / "frontend" / "node_modules" / ".bin" / "npx.cmd")
    run([npx, "tsc", "--noEmit"], cwd=ROOT / "frontend")
    npm = shutil.which("npm") or r"C:\Program Files\nodejs\npm.cmd"
    run([npm, "run", "build"], cwd=ROOT / "frontend")
    log("--- [5/8] Gateway PyInstaller + bridge ---")
    run([str(py), "-m", "PyInstaller", "--noconfirm", "mt5-gateway.spec"])
    # Launcher GUI (XAU_AI_PRO.exe em dist/) exigido pelo installer.iss na etapa 8.
    run([str(py), "-m", "PyInstaller", "--noconfirm", "launcher.spec"])
    dist_exe = ROOT / "dist" / "mt5-gateway" / "mt5-gateway.exe"
    bridge = ROOT / "frontend" / "src-tauri" / "bridge"
    if bridge.exists():
        shutil.rmtree(bridge)
    shutil.copytree(ROOT / "dist" / "mt5-gateway", bridge)
    dist_hash = sha256(dist_exe)
    bridge_hash = sha256(bridge / "mt5-gateway.exe")
    log(f"gateway dist SHA256:   {dist_hash}")
    log(f"gateway bridge SHA256: {bridge_hash}")
    if dist_hash != bridge_hash:
        raise SystemExit("drift: bridge diferente do dist")
    log("bridge sincronizado, sem drift")


def etapa_core_bundle() -> None:
    log("--- [6/8] Core Rust + src-tauri/core ---")
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo.exe")
    run([cargo, "build", "--release"], cwd=ROOT / "core")
    core_exe = ROOT / "core" / "target" / "release" / "xau-ai-pro-core.exe"
    dest_dir = ROOT / "frontend" / "src-tauri" / "core"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(core_exe, dest_dir / "xau-ai-pro-core.exe")
    core_hash = sha256(core_exe)
    dest_hash = sha256(dest_dir / "xau-ai-pro-core.exe")
    log(f"core target SHA256: {core_hash}")
    log(f"core bundle SHA256: {dest_hash}")
    if core_hash != dest_hash:
        raise SystemExit("drift: core do bundle diferente do target")
    log("--- [7/8] Bundle Tauri (msi + nsis) ---")
    npm_tauri = shutil.which("npm") or r"C:\Program Files\nodejs\npm.cmd"
    run([npm_tauri, "run", "tauri", "build"], cwd=ROOT / "frontend")
    nsis = ROOT / "frontend" / "src-tauri" / "target" / "release" / "bundle" / "nsis" / f"XAU AI PRO_{VERSION}_x64-setup.exe"
    msi = ROOT / "frontend" / "src-tauri" / "target" / "release" / "bundle" / "msi" / f"XAU AI PRO_{VERSION}_x64_en-US.msi"
    if not nsis.exists() or not msi.exists():
        raise SystemExit("bundle Tauri 1.2.3 nao gerado")
    log(f"NSIS: {nsis.stat().st_size} bytes SHA256={sha256(nsis)}")
    log(f"MSI:  {msi.stat().st_size} bytes SHA256={sha256(msi)}")
    log("--- [8/8] Instalador Inno Setup ---")
    iscc = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
    if not iscc.exists():
        raise SystemExit("ISCC.exe nao encontrado")
    run([str(iscc), str(ROOT / "installer" / "installer.iss")])
    setup = ROOT / "dist" / f"XAU_AI_PRO_Setup_{VERSION}.exe"
    if setup.exists():
        log(f"Setup final: {setup.stat().st_size} bytes SHA256={sha256(setup)}")
    else:
        log("aviso: Setup Inno nao localizado em dist/; verifique OutputDir do installer.iss")


def main() -> int:
    py = ROOT / ".venv" / "Scripts" / "python.exe"
    log("=== CICLO NOVO LIMPO E COMPLETO v1.2.3 ===")
    etapa_higiene()
    etapa_versao_testes(py)
    etapa_frontend_gateway(py)
    etapa_core_bundle()
    log("=== CICLO 1.2.3 CONCLUIDO: tudo atualizado, nada para tras ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

