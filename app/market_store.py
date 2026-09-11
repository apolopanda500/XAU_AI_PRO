# -*- coding: utf-8 -*-
"""Persistencia local e leve de cotações recebidas pelo desk."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from app.utils.paths import get_data_dir


def get_market_db_path() -> Path:
    return get_data_dir() / "marketdata.db"


def store_quotes(quotes: list[dict[str, Any]], db_path: Path | None = None) -> int:
    if not quotes:
        return 0
    path = db_path or get_market_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp_ms = int(time.time() * 1000)
    rows = [
        (
            timestamp_ms, str(quote.get("symbol") or ""), str(quote.get("source") or ""),
            float(quote.get("price") or 0), float(quote.get("bid") or 0),
            float(quote.get("ask") or 0), float(quote.get("change") or 0),
            float(quote.get("change_pct") or 0), float(quote.get("spread") or 0),
        )
        for quote in quotes
        if quote.get("symbol")
    ]
    if not rows:
        return 0
    with sqlite3.connect(path, timeout=2) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS market_ticks (
                ts_ms INTEGER NOT NULL, symbol TEXT NOT NULL, source TEXT NOT NULL,
                price REAL NOT NULL, bid REAL NOT NULL, ask REAL NOT NULL,
                change_value REAL NOT NULL, change_pct REAL NOT NULL, spread REAL NOT NULL,
                PRIMARY KEY (ts_ms, symbol, source)
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol_ts ON market_ticks(symbol, ts_ms DESC)"
        )
        connection.executemany(
            """INSERT OR REPLACE INTO market_ticks
               (ts_ms, symbol, source, price, bid, ask, change_value, change_pct, spread)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        connection.execute("DELETE FROM market_ticks WHERE ts_ms < ?", (timestamp_ms - 7 * 86_400_000,))
    return len(rows)
