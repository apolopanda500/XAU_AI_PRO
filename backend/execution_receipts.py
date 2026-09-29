# -*- coding: utf-8 -*-
"""Idempotencia de envio real por request_id.

Um pedido reenviado por timeout, reconnect ou clique repetido nao pode virar
duas ordens na corretora. O request_id e o identificador do operador: a
primeira tentativa grava o recibo aqui e qualquer repeticao devolve o recibo
em vez de abrir outra posicao.

Recibo em memoria (mesmo processo do gateway). E deliberadamente simples: nao
ha fallback em disco porque um recibo persistido entre reinicios sem resposta
da corretora seria tratado como sucesso sem prova.
"""
from __future__ import annotations

import hashlib
import threading
from typing import Any

_LOCK = threading.Lock()
_RECEIPTS: dict[str, dict[str, Any]] = {}
_MAX = 4096


def client_order_id(request_id: str) -> str:
    """Identificador aceito pelas quatro corretoras.

    As APIs aceitam so [a-zA-Z0-9-_] com limite de 36 caracteres. O request_id
    original continua sendo a chave de idempotencia; aqui apenas geramos a
    forma enviada, preservando o sufixo hash para nao colidir apos truncar.
    """
    raw = str(request_id or "").strip()
    if not raw:
        raise ValueError("request_id obrigatorio")
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in {"-", "_", "."})
    if len(cleaned) <= 36:
        return cleaned
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned[:27]}-{digest}"


def remember(request_id: str, receipt: dict[str, Any]) -> None:
    key = str(request_id or "").strip()
    if not key:
        return
    with _LOCK:
        if len(_RECEIPTS) >= _MAX:
            _RECEIPTS.clear()
        _RECEIPTS[key] = dict(receipt)


def recall(request_id: str) -> dict[str, Any] | None:
    key = str(request_id or "").strip()
    if not key:
        return None
    with _LOCK:
        receipt = _RECEIPTS.get(key)
        return dict(receipt) if isinstance(receipt, dict) else None


def reset() -> None:
    with _LOCK:
        _RECEIPTS.clear()
