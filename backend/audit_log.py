"""Auditoria operacional sem segredos.

POR QUE O VOLUME ENTROU AQUI
===========================
O evento gravava um conjunto fixo de campos:

    at, action, request_id, account_id, broker, market, symbol, status

Volume nao estava entre eles. Mas `vip_progress.volume_por_grupo()` le
exatamente `evento.get("volume") or evento.get("quantity")` para somar o
volume realizado por grupo e subir a escada de nivel.

O resultado medido em 05/10/2026: TODO evento de ordem real no audit.jsonl
tinha `volume` ausente. O `float(None)` caia no `continue` e a escada ficava
sempre no degrau 1 — nao por falta de operacao, mas porque o dado nunca foi
gravado. A tela mostrava 0 como se o cliente nao tivesse operado.

A licao: os testes de `test_vip_progress.py` fabricavam eventos COM `volume`
e por isso passavam, enquanto o produtor real nunca emitia esse campo. O
teste media um formato que o codigo de producao nao gerava.

Por isso `record()` copia agora os campos de quantidade do payload. Nao e
para a tela: e para que exista prova do volume executado.

O QUE NUNCA ENTRA
=================
`SENSITIVE` segue valendo e e aplicado a qualquer coisa que venha do payload.
Credencial em log e o defeito que a auditoria existe para pegar.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

#: Campos que NUNCA entram no log, nem quando vierem no payload.
SENSITIVE = frozenset(
    {
        "api_key",
        "api_secret",
        "secret",
        "password",
        "token",
        "signature",
        "passphrase",
        "api_passphrase",
        "authorization",
        "login",
        "account_password",
        "private_key",
    }
)

#: Campos de quantidade e preco. Um deles basta: os adaptadores nomeiam
#: volume de jeitos diferentes (`volume`, `quantity`, `qty`, `sz`, `lots`).
_QUANTIDADE = ("volume", "quantity", "qty", "sz", "lots", "amount")
_NOTIONAL = ("notional", "notional_value", "value")


def _primeiro(payload: dict, chaves: tuple[str, ...]):
    for chave in chaves:
        if chave in payload:
            return payload[chave]
    return None


def record(path: Path, *, action: str, payload: dict, status: str) -> dict:
    """Grava um evento de auditoria sem nenhum segredo.

    O payload entra por allowlist, nao por negacao: um campo novo no payload
    nao vaza por acidente, porque so os nomes listados sao lidos.
    """
    event = {
        "at": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "request_id": payload.get("request_id"),
        "account_id": payload.get("account_id"),
        "broker": payload.get("broker"),
        "market": payload.get("market"),
        "symbol": payload.get("symbol"),
        "status": status,
        # Quantidade e preco: o que prova o volume executado. Sem estes dois
        # campos a progressao por volume nao tem de onde ler.
        "volume": _primeiro(payload, _QUANTIDADE),
        "notional": _primeiro(payload, _NOTIONAL),
        "side": payload.get("side"),
    }
    # Allowlist ja garante nada sensivel entrou; a checagem final e a rede de
    # seguranca contra um nome novo entrar na lista por engano.
    for campo in SENSITIVE:
        event.pop(campo, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event