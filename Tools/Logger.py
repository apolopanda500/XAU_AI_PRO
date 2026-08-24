"""
Logger profissional - FASE 8.1
Espelho Python do Logger.mqh para uso no pipeline (train/predict/replay).

API:
    from Tools.Logger import get_logger
    log = get_logger("predict")
    log.info("Carregando modelo")
    log.warn("Feature X ausente")
    log.error("Falha ao carregar")
    log.trade("BUY EURUSD")
    log.ai("Predicao gerada")
    log.system("Pipeline iniciado")
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def _ensure_root_logger(
    log_dir: str = "Logs",
    filename: str = "python.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    level: int = logging.INFO,
) -> None:
    """Configura o logger raiz uma unica vez por processo."""
    global _initialized
    if _initialized:
        return

    root = logging.getLogger("xau_ai_pro")
    root.setLevel(level)
    root.propagate = False

    # limpa handlers antigos (em caso de reload)
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # arquivo com rotacao por tamanho
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            os.path.join(log_dir, filename),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        root.addHandler(fh)
    except Exception as exc:
        # se falhar ao criar arquivo, segue so com console
        sys.stderr.write(f"[Logger] Falha ao abrir arquivo de log: {exc}\n")

    _initialized = True


def get_logger(name: str, level: int | None = None) -> "XauLogger":
    """Retorna um logger nomeado."""
    if not _initialized:
        _ensure_root_logger()
    inner = logging.getLogger(f"xau_ai_pro.{name}")
    if level is not None:
        inner.setLevel(level)
    return XauLogger(inner)


class XauLogger:
    """Wrapper com atalhos semanticos (ai/trade/system)."""

    def __init__(self, inner: logging.Logger):
        self._log = inner

    def debug(self, msg: str) -> None:
        self._log.debug(msg)

    def info(self, msg: str) -> None:
        self._log.info(msg)

    def warn(self, msg: str) -> None:
        self._log.warning(msg)

    def warning(self, msg: str) -> None:
        self._log.warning(msg)

    def error(self, msg: str) -> None:
        self._log.error(msg)

    def critical(self, msg: str) -> None:
        self._log.critical(msg)

    def ai(self, msg: str) -> None:
        self._log.info("[AI] " + msg)

    def trade(self, msg: str) -> None:
        self._log.info("[TRADE] " + msg)

    def system(self, msg: str) -> None:
        self._log.info("[SYSTEM] " + msg)


def shutdown() -> None:
    """Fecha handlers (chamar ao final do processo)."""
    global _initialized
    logging.getLogger("xau_ai_pro").handlers.clear()
    _initialized = False
