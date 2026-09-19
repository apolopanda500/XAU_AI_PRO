"""Reconciliação determinística entre ordem enviada e estado observado."""
from __future__ import annotations
from typing import Any

def reconcile_order(request: dict[str, Any], response: dict[str, Any], position: dict[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    if not response.get("ticket") and not response.get("orderId"):
        errors.append("ticket ausente")
    expected = str(request.get("request_id", "")); returned = str(response.get("request_id", response.get("clientOrderId", response.get("externalOid", expected))))
    if expected and returned != expected:
        errors.append("request_id divergente")
    if position is not None:
        if str(position.get("symbol", "")).upper() != str(request.get("symbol", "")).upper(): errors.append("símbolo da posição divergente")
        if float(position.get("quantity", position.get("vol", 0)) or 0) <= 0: errors.append("posição sem quantidade válida")
    return {"ok": not errors, "status": "reconciled" if not errors else "mismatch", "request_id": expected, "ticket": response.get("ticket", response.get("orderId")), "errors": errors}
