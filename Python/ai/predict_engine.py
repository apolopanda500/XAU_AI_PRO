"""Signal builder for XAU_AI_PRO predictions."""

from __future__ import annotations

from typing import Any


def build_result(prediction: Any, probability: Any, last_row: Any) -> dict[str, Any]:
    """Build the prediction result dictionary.

    Args:
        prediction: Predicted class label (0 or 1).
        probability: Array-like of class probabilities.
        last_row: Last row of the dataset with market data.

    Returns:
        Dictionary with prediction signal, price, buy/sell percentages, and score.
    """
    probabilities = list(probability)

    if len(probabilities) >= 2:
        sell = float(probabilities[0])
        buy = float(probabilities[1])
    else:
        sell = float(probabilities[0])
        buy = float(probabilities[0])

    signal = "BUY" if prediction == 1 else "SELL"
    score = max(buy, sell) * 100

    return {
        "symbol": str(last_row.get("Symbol", "")),
        "signal": signal,
        "price": float(last_row.get("Close", 0)),
        "buy": round(buy * 100, 2),
        "sell": round(sell * 100, 2),
        "score": round(score, 2),
    }
