"""Testes de procedencia do armazenamento local de cotacoes (lacuna C1).

O `marketdata.db` continha 23.820 ticks confirmados pelo usuario como DADOS DE
TESTE, sem nenhuma coluna que distinguisse origem. `last_ticks` alimenta o
fallback do grafico quando o MT5 nao devolve candles, entao esses ticks
apareciam com a mesma aparencia de preco ao vivo — o que a regra do `AGENTS.md`
proibe explicitamente.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from app.market_store import (
    IDADE_MAXIMA_SEGUNDOS,
    PROVENIENCE_LIVE,
    PROVENIENCE_STORED,
    PROVENIENCE_UNVERIFIED,
    fallback_provenance,
    last_ticks,
    store_quotes,
)


def _cotacao(symbol: str = "XAUUSD", price: float = 3000.0, source: str = "MT5") -> dict:
    return {"symbol": symbol, "price": price, "bid": price - 1, "ask": price + 1,
            "change": 0.0, "change_pct": 0.0, "spread": 2.0, "source": source}


def test_grava_com_proveniencia(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    assert store_quotes([_cotacao()], db, provenance=PROVENIENCE_LIVE) == 1

    with sqlite3.connect(db) as connection:
        coluna = [row[1] for row in connection.execute("PRAGMA table_info(market_ticks)")]
        valor = connection.execute("SELECT provenance FROM market_ticks").fetchone()[0]
    assert "provenance" in coluna
    assert valor == PROVENIENCE_LIVE


def test_proveniencia_invalida_e_recusada(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    with pytest.raises(ValueError):
        store_quotes([_cotacao()], db, provenance="ao_vivo_achado")


def test_padrao_e_unverified(tmp_path: Path) -> None:
    # Sem origem confirmada, o padrao e nao-verificado, nunca "live".
    db = tmp_path / "m.db"
    store_quotes([_cotacao()], db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT provenance FROM market_ticks").fetchone()[0] == PROVENIENCE_UNVERIFIED


def test_migra_banco_antigo_sem_perder_dados(tmp_path: Path) -> None:
    # Banco no formato anterior a lacuna C1, sem a coluna.
    db = tmp_path / "antigo.db"
    with sqlite3.connect(db) as connection:
        connection.execute(
            """CREATE TABLE market_ticks (
                ts_ms INTEGER NOT NULL, symbol TEXT NOT NULL, source TEXT NOT NULL,
                price REAL NOT NULL, bid REAL NOT NULL, ask REAL NOT NULL,
                change_value REAL NOT NULL, change_pct REAL NOT NULL, spread REAL NOT NULL,
                PRIMARY KEY (ts_ms, symbol, source))"""
        )
        connection.execute(
            "INSERT INTO market_ticks VALUES (?,?,?,?,?,?,?,?,?)",
            (int(time.time() * 1000), "XAUUSD", "MT5", 3000.0, 2999.0, 3001.0, 0.0, 0.0, 2.0),
        )
    meta = fallback_provenance("XAUUSD", db)
    assert meta["count"] == 1
    # Dado herdado do formato antigo e tratado como nao verificado.
    assert meta["live"] is False
    assert meta["provenance"] == PROVENIENCE_UNVERIFIED
    assert "NAO VERIFICADOS" in meta["label"]


def test_fallback_live_exige_idade_recente(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    store_quotes([_cotacao()], db, provenance=PROVENIENCE_LIVE)
    meta = fallback_provenance("XAUUSD", db)
    assert meta["live"] is True
    assert meta["provenance"] == PROVENIENCE_LIVE
    assert "ao vivo" in meta["label"]


def test_fallback_live_antigo_vira_historico(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    store_quotes([_cotacao()], db, provenance=PROVENIENCE_LIVE)
    # Envelhece o tick alem do limite aceito como "ao vivo".
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE market_ticks SET ts_ms = ?",
            (int(time.time() * 1000) - (IDADE_MAXIMA_SEGUNDOS + 120) * 1000,),
        )
    meta = fallback_provenance("XAUUSD", db)
    assert meta["live"] is False
    assert "historico local" in meta["label"]


def test_mistura_de_proveniencia_rebaixa_o_conjunto(tmp_path: Path) -> None:
    # Um unico tick sem origem confirmada impede afirmar que a linha toda e ao vivo.
    db = tmp_path / "m.db"
    agora = int(time.time() * 1000)
    with sqlite3.connect(db) as connection:
        connection.execute(
            """CREATE TABLE market_ticks (
                ts_ms INTEGER NOT NULL, symbol TEXT NOT NULL, source TEXT NOT NULL,
                price REAL NOT NULL, bid REAL NOT NULL, ask REAL NOT NULL,
                change_value REAL NOT NULL, change_pct REAL NOT NULL, spread REAL NOT NULL,
                provenance TEXT NOT NULL DEFAULT 'unverified',
                PRIMARY KEY (ts_ms, symbol, source))"""
        )
        connection.executemany(
            "INSERT INTO market_ticks (ts_ms, symbol, source, price, bid, ask, change_value, change_pct, spread, provenance)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (agora, "XAUUSD", "MT5", 3000.0, 2999.0, 3001.0, 0.0, 0.0, 2.0, "live"),
                (agora - 1000, "XAUUSD", "HTTP", 3001.0, 3000.0, 3002.0, 0.0, 0.0, 2.0, "unverified"),
            ],
        )
    meta = fallback_provenance("XAUUSD", db)
    assert meta["live"] is False
    assert meta["provenance"] == "mixed"


def test_simbolo_sem_historico_nao_inventa_origem(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    store_quotes([_cotacao("XAUUSD")], db, provenance=PROVENIENCE_LIVE)
    meta = fallback_provenance("EURUSD", db)
    assert meta["count"] == 0
    assert meta["live"] is False
    assert meta["label"] == "sem historico local"


def test_last_ticks_carrega_a_origem(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    store_quotes([_cotacao(source="MT5")], db, provenance=PROVENIENCE_LIVE)
    pontos = last_ticks("XAUUSD", 10, db)
    assert len(pontos) == 1
    assert pontos[0]["source"] == "MT5"
    # O ponto lido do banco e 'stored'; a origem gravada vem em origin_provenance.
    assert pontos[0]["provenance"] == PROVENIENCE_STORED
    assert pontos[0]["origin_provenance"] == PROVENIENCE_LIVE


def test_last_ticks_em_banco_inexistente(tmp_path: Path) -> None:
    assert last_ticks("XAUUSD", 10, tmp_path / "nao-existe.db") == []
