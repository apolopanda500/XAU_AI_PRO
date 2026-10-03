# -*- coding: utf-8 -*-
"""Persistencia local e leve de cotações recebidas pelo desk.

PROCEDENCIA (lacuna C1, fechada em 2026-09-26)
----------------------------------------------
Toda linha gravada carrega `provenance`:

- ``live``: a cotacao chegou de uma fonte conectada neste processo;
- ``unverified``: gravada sem origem confirmada (inclui as 23.820 linhas
  preexistentes, que o usuario confirmou em 2026-09-25 serem DADOS DE TESTE);
- ``stored``: apenas lida de volta do banco.

`last_ticks` e usado como fallback do grafico quando o MT5 nao fornece candles.
Sem a coluna, um tick de teste era desenhado com a mesma aparencia de preco ao
vivo. `last_ticks` agora devolve a procedencia junto dos candles, e
`fallback_provenance` diz se a tela pode apresentar o dado como mercado real.
A regra do `AGENTS.md` continua valendo: dado de teste nao vira dado real.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from app.utils.paths import get_data_dir

# Valores aceitos na coluna `provenance`.
PROVENIENCE_LIVE = "live"
PROVENIENCE_UNVERIFIED = "unverified"
PROVENIENCE_STORED = "stored"
PROVENIENCES_VALIDOS = (PROVENIENCE_LIVE, PROVENIENCE_UNVERIFIED)

# Acima disto o fallback deixa de ser "mercado" e passa a ser historico antigo.
IDADE_MAXIMA_SEGUNDOS = 300


def get_market_db_path() -> Path:
    return get_data_dir() / "marketdata.db"


def _garantir_esquema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS market_ticks (
            ts_ms INTEGER NOT NULL, symbol TEXT NOT NULL, source TEXT NOT NULL,
            price REAL NOT NULL, bid REAL NOT NULL, ask REAL NOT NULL,
            change_value REAL NOT NULL, change_pct REAL NOT NULL, spread REAL NOT NULL,
            PRIMARY KEY (ts_ms, symbol, source)
        )"""
    )
    # Banco criado antes da lacuna C1: a coluna e adicionada sem perder dados.
    colunas = {row[1] for row in connection.execute("PRAGMA table_info(market_ticks)")}
    if "provenance" not in colunas:
        connection.execute(
            "ALTER TABLE market_ticks ADD COLUMN provenance TEXT NOT NULL DEFAULT 'unverified'"
        )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol_ts ON market_ticks(symbol, ts_ms DESC)"
    )


def store_quotes(
    quotes: list[dict[str, Any]],
    db_path: Path | None = None,
    provenance: str = PROVENIENCE_UNVERIFIED,
) -> int:
    """Grava cotacoes com a procedencia declarada.

    `provenance` so aceita `live` ou `unverified`. `live` e responsabilidade de
    quem chama: passar `live` sem uma fonte conectada e affirmar que o dado e ao
    vivo, que e exatamente o que a regra do AGENTS.md proibe.
    """
    if not quotes:
        return 0
    if provenance not in PROVENIENCES_VALIDOS:
        raise ValueError(f"provenance invalida: {provenance!r}")
    path = db_path or get_market_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp_ms = int(time.time() * 1000)
    rows = [
        (
            timestamp_ms, str(quote.get("symbol") or ""), str(quote.get("source") or ""),
            float(quote.get("price") or 0), float(quote.get("bid") or 0),
            float(quote.get("ask") or 0), float(quote.get("change") or 0),
            float(quote.get("change_pct") or 0), float(quote.get("spread") or 0),
            provenance,
        )
        for quote in quotes
        if quote.get("symbol")
    ]
    if not rows:
        return 0
    with sqlite3.connect(path, timeout=2) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        _garantir_esquema(connection)
        connection.executemany(
            """INSERT OR REPLACE INTO market_ticks
               (ts_ms, symbol, source, price, bid, ask, change_value, change_pct, spread, provenance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        connection.execute("DELETE FROM market_ticks WHERE ts_ms < ?", (timestamp_ms - 7 * 86_400_000,))
    return len(rows)


def fallback_provenance(symbol: str, db_path: Path | None = None) -> dict[str, Any]:
    """Descreve a origem do fallback de um simbolo, para a tela rotular.

    `live` so e True quando todos os ticks do simbolo foram gravados como `live`
    e o mais recente tem menos de IDADE_MAXIMA_SEGUNDOS. Qualquer mistura com
    `unverified` rebaixa o conjunto inteiro: um unico tick sem origem confirmada
    impede afirmar que a linha toda e ao vivo.
    """
    agora_ms = int(time.time() * 1000)
    vazio: dict[str, Any] = {
        "symbol": str(symbol), "live": False, "provenance": None, "count": 0,
        "age_seconds": None, "sources": [], "label": "sem historico local",
    }
    path = db_path or get_market_db_path()
    if not path.exists():
        return vazio
    try:
        with sqlite3.connect(path, timeout=2) as connection:
            _garantir_esquema(connection)
            rows = connection.execute(
                """SELECT provenance, source, MAX(ts_ms) AS ts
                   FROM market_ticks WHERE symbol = ? GROUP BY provenance, source""",
                (str(symbol),),
            ).fetchall()
    except sqlite3.Error:
        return vazio
    if not rows:
        return vazio
    proveniencias = {str(row[0] or PROVENIENCE_UNVERIFIED) for row in rows}
    fontes = sorted({str(row[1]) for row in rows if row[1]})
    mais_recente = max(int(row[2] or 0) for row in rows)
    idade = max(0, (agora_ms - mais_recente) // 1000)
    somente_live = proveniencias == {PROVENIENCE_LIVE}
    live = somente_live and idade <= IDADE_MAXIMA_SEGUNDOS
    if live:
        label = f"ao vivo · {', '.join(fontes)}"
    elif somente_live:
        label = f"historico local de {idade}s atras · {', '.join(fontes)}"
    else:
        label = f"DADOS NAO VERIFICADOS · {idade}s atras · {', '.join(fontes)}"
    return {
        "symbol": str(symbol), "live": live,
        "provenance": PROVENIENCE_LIVE if somente_live else "mixed" if len(proveniencias) > 1 else next(iter(proveniencias)),
        "count": sum(1 for _ in rows), "age_seconds": idade,
        "sources": fontes, "label": label,
    }


def last_ticks(symbol: str, limit: int = 80, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Le os ultimos ticks persistidos de um simbolo (mais antigos -> recentes).

    Usado como fallback do grafico quando o MT5 nao fornece candles: cada tick
    vira um ponto OHLC degenerado (open=high=low=close=price). Cada ponto carrega
    `provenance` e `source` para que a tela distinga dado ao vivo de dado
    armazenado — quem desenha e responsavel por mostrar essa distincao.
    """
    path = db_path or get_market_db_path()
    if not path.exists():
        return []
    try:
        with sqlite3.connect(path, timeout=2) as connection:
            _garantir_esquema(connection)
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """SELECT ts_ms, price, source, provenance FROM market_ticks
                   WHERE symbol = ? ORDER BY ts_ms DESC LIMIT ?""",
                (str(symbol), int(limit)),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in reversed(rows):
            price = float(r["price"])
            when = time.strftime("%H:%M:%S", time.localtime(int(r["ts_ms"]) / 1000.0))
            out.append({
                "symbol": str(symbol), "time": when,
                "open": price, "high": price, "low": price, "close": price,
                "volume": 0.0,
                "source": str(r["source"] or ""),
                "provenance": PROVENIENCE_STORED,
                "origin_provenance": str(r["provenance"] or PROVENIENCE_UNVERIFIED),
            })
        return out
    except sqlite3.Error:
        return []
