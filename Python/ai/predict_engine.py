"""Signal builder for XAU_AI_PRO predictions."""

from __future__ import annotations


def build_result(prediction, probability, last_row):
    if len(probability) >= 2:
        sell = float(probability[0])
        buy = float(probability[1])
    else:
        sell = float(probability[0])
        buy = float(probability[0])

    signal = "BUY" if prediction == 1 else "SELL"
    score = max(buy, sell) * 100

    result = {
        "symbol": str(last_row.get("Symbol", "")),
        "signal": signal,
        "price": float(last_row.get("Close", 0)),
        "buy": round(buy * 100, 2),
        "sell": round(sell * 100, 2),
        "score": round(score, 2),
    }
    return result
