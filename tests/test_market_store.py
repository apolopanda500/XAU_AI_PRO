from pathlib import Path

from app.market_store import store_quotes


def test_store_quotes_creates_local_market_history(tmp_path: Path) -> None:
    database = tmp_path / "marketdata.db"
    written = store_quotes([
        {"symbol": "BTCUSD", "source": "Binance", "price": 1, "bid": 1,
         "ask": 1, "change": 0, "change_pct": 0, "spread": 0}
    ], database)
    assert written == 1
    assert database.exists()
