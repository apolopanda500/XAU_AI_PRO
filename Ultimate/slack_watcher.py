# -*- coding: utf-8 -*-
"""XAU AI PRO - Slack Watcher

Monitora o forward_test_events.csv (gerado pelo EventEmitter MQL5) e
envia notificações para o Slack em tempo real.

Fluxo:
    MQL5 EA --> EventEmitter --> forward_test_events.csv --> slack_watcher.py --> Slack

Uso:
    # Modo contínuo (thread daemon)
    python slack_watcher.py

    # Ou importado no app:
    import slack_watcher
    slack_watcher.start_watcher(interval=10)

O watcher roda em background thread, tolera falhas e nunca levanta exceções.
"""
from __future__ import annotations

import csv
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from app.utils.paths import get_mql_data_path

TERMINAL_DATA = get_mql_data_path()
LOCAL_DATA = Path(__file__).resolve().parent.parent / "MQL5" / "Files" / "Data"

_EVENTS_FILE = "forward_test_events.csv"

# Eventos que queremos notificar no Slack
_EVENT_MAP: dict[str, dict[str, Any]] = {
    "TRADE_OPEN":   {"handler": "trade_open",  "severity": "info"},
    "TRADE_CLOSE":  {"handler": "trade_close", "severity": "info"},
    "CIRCUIT_BREAKER": {"handler": "circuit_breaker", "severity": "critical"},
    "SAFE_MODE":       {"handler": "safe_mode",        "severity": "warn"},
    "RISK_BLOCK":      {"handler": "risk_block",       "severity": "warn"},
    "NEWS_BLOCK":      {"handler": "news_block",       "severity": "warn"},
    "AI_ERROR":        {"handler": "ai_error",         "severity": "error"},
    "AI_BLOCK":        {"handler": "ai_block",         "severity": "warn"},
    "SYSTEM_ERROR":    {"handler": "system_error",     "severity": "critical"},
    "PYTHON_ERROR":    {"handler": "python_error",     "severity": "error"},
    "DATABASE_ERROR":  {"handler": "database_error",   "severity": "error"},
    "BROKER_ERROR":    {"handler": "broker_error",     "severity": "error"},
    "HEALTH_FAILURE":  {"handler": "health_failure",   "severity": "critical"},
}


def _events_file() -> Path | None:
    """Resolve o caminho do arquivo de eventos."""
    p1 = TERMINAL_DATA / _EVENTS_FILE
    if p1.exists():
        return p1
    p2 = LOCAL_DATA / _EVENTS_FILE
    if p2.exists():
        return p2
    return None


def _read_events(offset: int) -> tuple[list[list[str]], int]:
    """Lê novas linhas do CSV a partir do offset.

    Retorna (linhas_novas, novo_offset_byte).
    O offset é baseado em bytes para suportar UTF-16.
    """
    f = _events_file()
    if f is None:
        return [], 0

    try:
        # O offset persistido é de bytes. Não usar seek() em TextIOWrapper:
        # em UTF-16 ele é um offset de caracteres/opaco e pode iniciar no
        # meio de um code unit, produzindo linhas corrompidas ou eventos
        # silenciosamente perdidos.
        with open(f, "rb") as fh:
            size = fh.seek(0, os.SEEK_END)
            if offset < 0 or offset > size:
                offset = 0
            fh.seek(offset)
            raw = fh.read()
            new_offset = fh.tell()
        content = raw.decode("utf-16", errors="replace")
    except Exception:
        return [], offset

    if not content:
        return [], offset

    lines = [ln.replace("\r", "").strip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        return [], new_offset

    rows = []
    for line in lines:
        try:
            parts = next(csv.reader([line]))
        except (csv.Error, StopIteration):
            continue
        if len(parts) >= 10 and parts[1].strip() != "Event":
            rows.append(parts[:10])

    return rows, new_offset


class _OffsetStore:
    """Armazena o offset de leitura em disco (persistência simples)."""

    _path: Path | None = None

    @classmethod
    def get_path(cls) -> Path:
        if cls._path is None:
            cls._path = Path(__file__).resolve().parent / ".slack_watcher_offset"
        return cls._path

    @classmethod
    def load(cls) -> int:
        try:
            p = cls.get_path()
            if p.exists():
                return int(p.read_text(encoding="utf-8").strip() or 0)
        except Exception:
            pass
        return 0

    @classmethod
    def save(cls, offset: int) -> None:
        try:
            p = cls.get_path()
            p.write_text(str(offset), encoding="utf-8")
        except Exception:
            pass



# ── Processamento de eventos ──
def _process_event(row: list[str]) -> None:
    """Processa uma linha de evento e envia notificação se aplicável."""
    try:
        event_name = row[1].strip()
        symbol = row[2].strip()
        severity = row[5].strip()
        module = row[6].strip()
        message = row[7].strip()
        value = row[8].strip()
        status = row[9].strip()

        mapping = _EVENT_MAP.get(event_name)
        if mapping is None:
            return

        try:
            import slack_notifier as sn
        except Exception:
            return

        handler = mapping["handler"]

        if handler == "trade_open":
            sn.send_info("TRADE", f"Posição aberta: {symbol} {message} ({value})")
        elif handler == "trade_close":
            profit = float(value) if value else 0.0
            sn.send_trade_close(symbol, profit, message)
        elif handler == "circuit_breaker":
            sn.send_risk_alert("Circuit Breaker", message)
        elif handler == "safe_mode":
            sn.send_risk_alert("Modo Seguro", message)
        elif handler == "risk_block":
            sn.send_risk_alert("Risco Bloqueado", f"{symbol}: {message}")
        elif handler == "news_block":
            sn.send_risk_alert("Notícia Bloqueada", f"{symbol}: {message}")
        elif handler == "ai_error":
            sn.send_error("IA", f"{symbol}: {message}")
        elif handler == "ai_block":
            sn.send_info("IA", f"IA bloqueada: {symbol} - {message}")
        elif handler in ("system_error", "python_error", "database_error", "broker_error"):
            sn.send_error(module or handler, message)
        elif handler == "health_failure":
                        sn.send_risk_alert("Falha de Saúde", message)
    except Exception:
        pass


# ── Watcher principal ──
class SlackWatcher:
    """Monitora forward_test_events.csv e envia notificações para Slack."""

    def __init__(self, interval: float = 10.0) -> None:
        self._interval = interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._offset: int = 0
        self._file_path: Path | None = None

    def start(self) -> None:
        """Inicia o watcher em thread background."""
        if self._running:
            return
        self._running = True
        self._offset = _OffsetStore.load()
        self._file_path = _events_file()
        # Offset pertence ao arquivo. Se o arquivo foi recriado/truncado,
        # reinicia do início para não perder o cabeçalho/eventos novos.
        if self._file_path is not None:
            try:
                if self._offset > self._file_path.stat().st_size:
                    self._offset = 0
            except OSError:
                self._offset = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Para o watcher."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self) -> None:
        """Loop principal: lê eventos e envia notificações."""
        while self._running:
            try:
                rows, new_offset = _read_events(self._offset)
                if rows:
                    self._offset = new_offset
                    _OffsetStore.save(new_offset)
                    for row in rows:
                        _process_event(row)
            except Exception:
                pass
            time.sleep(self._interval)

    def run_once(self) -> int:
        """Processa eventos uma vez (modo não-daemon). Útil para testes."""
        rows, new_offset = _read_events(self._offset)
        count = 0
        if rows:
            self._offset = new_offset
            _OffsetStore.save(new_offset)
            for row in rows:
                _process_event(row)
                count += 1
        return count


# ── Instância global ──
_watcher: SlackWatcher | None = None


def start_watcher(interval: float = 10.0) -> SlackWatcher:
    """Inicia o watcher global."""
    global _watcher
    if _watcher is None:
        _watcher = SlackWatcher(interval=interval)
        _watcher.start()
    return _watcher


def stop_watcher() -> None:
    """Para o watcher global."""
    global _watcher
    if _watcher is not None:
        _watcher.stop()
        _watcher = None


if __name__ == "__main__":
    print("=== XAU AI PRO — Slack Watcher ===")
    print(f"Arquivo de eventos: {_events_file() or 'NÃO ENCONTRADO'}")
    print("Monitorando eventos... (Ctrl+C para parar)\n")

    w = start_watcher(interval=10.0)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nParando watcher...")
        stop_watcher()
        print("Watcher parado. Offset salvo em .slack_watcher_offset")
