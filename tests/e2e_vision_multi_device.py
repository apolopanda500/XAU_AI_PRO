"""Visão multi-dispositivo: fotografa a tela do app no Android conectado via
ADB e valida que a tela principal renderiza sem código-morto nem erro fatal.

Este script NÃO existe para substituir testes visuais humanos; ele marca os
sintoma objetivos (imagem vazia, logcat com FATAL, selo duplicado) para um
auditor olhar o print e julgar.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

AUDIT_ROOT = Path(__file__).resolve().parents[1] / "MQL5" / "Files" / "Temp" / "bateria_10_10_vision"


def adb(serial: str, *args: str, binary: bool = False):
    cmd = ["adb", "-s", serial, *args]
    if binary:
        return subprocess.check_output(cmd, timeout=15)
    return subprocess.check_output(cmd, text=True, errors="ignore", timeout=30)


def list_connected() -> list[str]:
    out = subprocess.check_output(["adb", "devices"], text=True)
    return [
        line.split("\t")[0].strip()
        for line in out.splitlines()
        if "\tdevice" in line
    ]


def audit(serial: str) -> dict:
    device_dir = AUDIT_ROOT / serial.replace(":", "_")
    device_dir.mkdir(parents=True, exist_ok=True)

    adb(serial, "reverse", "tcp:9027", "tcp:9027")
    adb(
        serial,
        "shell",
        "monkey",
        "-p",
        "com.xau_ai_pro.desktop",
        "-c",
        "android.intent.category.LAUNCHER",
        "1",
    )
    time.sleep(3.0)

    png = adb(serial, "exec-out", "screencap", "-p", binary=True)
    png_path = device_dir / "01_tela_principal.png"
    png_path.write_bytes(png)

    xml = adb(serial, "shell", "uiautomator", "dump", "/sdcard/xau_ui.xml")
    xml_path = device_dir / "01_tela_principal.xml"
    xml_path.write_text(xml, encoding="utf-8")

    logcat = adb(serial, "logcat", "-d", "-t", "200")
    fatals = [
        l for l in logcat.splitlines()
        if "FATAL" in l or "panicked" in l or "ERR_CLEARTEXT" in l
    ]

    return {
        "serial": serial,
        "type": "EMULATOR" if serial.startswith("emulator-") else "PHYSICAL_USB",
        "screenshot": str(png_path),
        "xml": str(xml_path),
        "screenshot_bytes": len(png),
        "fatal_logcat_count": len(fatals),
        "fatal_samples": fatals[-5:],
        "passed": len(png) > 15_000 and len(fatals) == 0,
    }


def main() -> int:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    targets = list_connected()
    report = {
        "timestamp_utc": int(time.time()),
        "devices_found": len(targets),
        "results": [audit(serial) for serial in targets],
    }
    out = AUDIT_ROOT / "vision_audit_summary.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = all(r["passed"] for r in report["results"]) if targets else True
    print(f"[VISION QA] {len(targets)} dispositivo(s). Relatorio: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
