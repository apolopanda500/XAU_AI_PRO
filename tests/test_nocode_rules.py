# -*- coding: utf-8 -*-
"""Testes G1/G2 — no-code parser generico (sem ativo fixo)."""
from app.nocode_rules import build_bot, parse_rule


def test_buy_rsi_pt():
    r = parse_rule("comprar quando rsi < 30 com sl 50 e tp 100", symbol="EURUSD")
    assert r["ok"] and r["rule"]["action"] == "buy"
    assert r["rule"]["conditions"][0]["indicator"] == "rsi"
    bot = build_bot(r)
    assert bot["ok"] and bot["bot"]["enabled"] is False  # comeca pausado


def test_sell_macd_en():
    r = parse_rule("sell if macd crosses up, risk 1%", symbol="GBPUSD")
    assert r["ok"] and r["rule"]["action"] == "sell"


def test_empty_and_unknown():
    assert parse_rule("")["ok"] is False
    assert parse_rule("ola mundo", symbol="EURUSD")["ok"] is False
    assert build_bot(parse_rule("", symbol="EURUSD"))["ok"] is False


def test_no_symbol_needs_selection():
    r = parse_rule("comprar quando atr > 20", symbol="")
    bot = build_bot(r)
    # sem simbolo no contexto: pode pedir selecao (ok=False) ou usar fallback config
    assert "symbol" in (r.get("rule") or {}) or bot["ok"] is False
