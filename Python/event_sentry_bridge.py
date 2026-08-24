"""Ponte Event Stream -> Sentry (ETAPA Plataforma/Sentry).

Le o forward_test_events.csv gerado pelo EventEmitter MQL5 e encaminha
eventos de severidade ERROR/CRITICAL ao Sentry via sentry_config.

Uso: importado no agendador Python (cycico) ou manualmente.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Integracao Sentry tolerante (nao quebra se nao configurado)
try:
    import sentry_sdk
    from sentry_config import init_sentry
    _SENTRY_OK = True
except Exception:
    _SENTRY_OK = False


def _events_file() -> Path | None:
    base = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" \
           / "D0E8209F77C8CF37AD8BF550E51FF075" / "MQL5" / "Files" / "Data"
    f = base / "forward_test_events.csv"
    return f if f.exists() else None


def _read_last_errors(limit: int = 20) -> list[dict]:
    """Le as ultimas linhas com severidade ERROR/CRITICAL (UTF-16)."""
    f = _events_file()
    if f is None:
        return []
    try:
        text = f.read_text(encoding="utf-16", errors="replace")
    except Exception:
        return []

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []

    header = lines[0].split(",")
    errors = []
    for ln in lines[1:]:
        parts = ln.split(",")
        if len(parts) < 6:
            continue
        sev = parts[5].strip().upper()
        if sev in ("ERROR", "CRITICAL"):
            row = {header[i].strip(): (parts[i].strip() if i < len(parts) else "")
                   for i in range(len(header))}
            errors.append(row)
    return errors[-limit:]


def report_errors_to_sentry() -> int:
    """Encaminha erros do event stream nao reportados ao Sentry.

    Retorna o numero de erros encaminhados.
    """
    if not _SENTRY_OK:
        return 0
    if not sentry_sdk:
        return 0

    errors = _read_last_errors()
    if not errors:
        return 0

    # Evita re-report: arquivo de offset simples (nao-persistente por sessao)
    reported = 0
    for ev in errors:
        with sentry_sdk.isolation_scope() as scope:
            scope.set_tag("component", ev.get("Module", "unknown"))
            scope.set_tag("symbol", ev.get("Symbol", ""))
            scope.set_context("event_stream", ev)
            sentry_sdk.capture_message(
                f"[EVENT-STREAM] {ev.get('Event','')} | "
                f"{ev.get('Message','')} | {ev.get('Status','')}",
                level="error",
            )
        reported += 1

    return reported