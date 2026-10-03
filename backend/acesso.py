# -*- coding: utf-8 -*-
"""Fonte unica de acesso: junta PLANO e VOLUME numa arvore so.

POR QUE ESTE MODULO EXISTE
==========================
Ate 2026-10-02 o projeto tinha DOIS sistemas de plano que nao se falavam:

1. `app/subscriptions.py` — planos COMPRADOS (Free / VIP / VIPS)
2. `backend/vip_progress.py` — escada por VOLUME executado (VIP 1..VIP 5)

Cada um destravava um conjunto diferente de coisas. A tela mostrava as duas,
e o resultado foi o que o dono reportou: **"duplicatas"** e **"VIP nao
funciona"**.

O motivo e estrutural, nao de interface. `plano_gate.py:34` mapeia
`auto_engine -> advanced_analytics`, e `advanced_analytics` so existe no
catalogo de planos. A progressao por volume (`vip_progress.progresso()`)
devolve escada, percentuais e nivel — mas **nunca escreve em `entitlements`**.
Subir de VIP por volume desenhava uma escada bonita e nao abria nada. Era o
mesmo padrao que o comentario do proprio `plano_gate.py` descreve: *"a tela
prometia plano pago e o produto nao mudava"*.

A REGRA DESTE MODULO
====================
**Uma feature e liberada por PLANO. O VOLUME da PROFUNDIDADE dentro do plano
liberado — nunca abre feature que o plano nao tem.**

E deliberado, e e o que resolve a duplicata:

| Caminho            | Resultado                   |
|--------------------|-----------------------------|
| VIP1 por volume    | Entra no escopo do VIP      |
| VIP pago, sem vol  | Entra no escopo do VIP      |
| VIP + VIP3 volume  | VIP com profundidade maior  |
| VIP3 sem VIP pago  | **Nada** — volume nao compra |

A ultima linha e a importante: sem ela existiriam DOIS jeitos de destravar a
mesma coisa (comprar OU operar), que e exatamente a duplicata. Aqui o volume
so adiciona DENTRO do plano.

O QUE NAO PASSA POR AQUI
========================
Dinheiro real, saque e transferencia. `live_execution` e
`withdrawals_enabled` seguem `False` em todos os planos. Ver `AGENTS.md`.
"""
from __future__ import annotations

from typing import Any

#: Feature que abre os modelos `MULTI_<GRUPO>_<TF>` de `backend/ai_inference.py`.
ENTITLEMENT_MULTI_MODEL = "multi_model"

#: Plano que NAO pode usar multi, em nenhuma hipotese.
PLANO_SEM_MULTI = "free"


def plano_atual(user_id: str | None = None) -> dict[str, Any]:
    """Assinatura local, ou o Free quando nao ha nada valido.

    Nunca levanta: assinatura ilegivel nao pode derrubar a tela, mas tambem
    nao pode liberar recurso pago. Fail-closed.
    """
    try:
        from app.subscriptions import get_subscription

        assinatura = get_subscription(user_id)
    except Exception:  # noqa: BLE001 - assinatura e acessoria, e fail-closed
        return {"plan_id": PLANO_SEM_MULTI, "active": True, "entitlements": {}, "limits": {}, "degraded": True}

    if not assinatura.get("active"):
        return {"plan_id": PLANO_SEM_MULTI, "active": True, "entitlements": {}, "limits": {}, "degraded": False}

    return {
        "plan_id": str(assinatura.get("plan_id") or PLANO_SEM_MULTI),
        "active": True,
        "entitlements": dict(assinatura.get("entitlements") or {}),
        "limits": dict(assinatura.get("limits") or {}),
        "degraded": bool(assinatura.get("integrity_status") not in {"verified", "default", ""}),
    }


def pode_usar_multi_modelo(user_id: str | None = None) -> bool:
    """True somente para plano pago COM o entitlement ligado.

    Duas condicoes, e as duas sao necessarias:

    1. `plan_id != "free"` — o dono definiu: Free nunca usa multi.
    2. `entitlements["multi_model"]` verdadeiro.

    A 1 e redundante enquanto o catalogo estiver correto (o Free ja tem
    `multi_model: False`). Ela existe para o caso de o `subscriptions.json`
    da maquina ter sido editado a mao: o arquivo pode dizer `vips` enquanto o
    catalogo em memoria mantem o Free. Conferir as duas impede que o arquivo
    sozinho decida.
    """
    assinatura = plano_atual(user_id)
    if assinatura["plan_id"] == PLANO_SEM_MULTI:
        return False
    return bool(assinatura["entitlements"].get(ENTITLEMENT_MULTI_MODEL, False))


def limite_multi_modelos(user_id: str | None = None) -> int:
    """Quantos modelos multi o plano permite usar ao mesmo tempo.

    Free devolve 0 — e nao "todos", nem -1, nem o limite do proximo plano.
    O `inferir()` trata 0 como "so modelo unico", que e o comportamento
    correto: no Free `MULTI_*` nao existe e o operador ve o motivo.
    """
    assinatura = plano_atual(user_id)
    if assinatura["plan_id"] == PLANO_SEM_MULTI:
        return 0
    try:
        return max(0, int(assinatura["limits"].get("multi_models", 0)))
    except (TypeError, ValueError):
        return 0


def nivel_por_volume(user_id: str | None = None) -> dict[str, Any]:
    """Progressao por volume, ou um estado neutro se nao houver dados.

    Nunca levanta: o `audit.jsonl` pode nao existir ainda, e um app que nao
    abre por causa disso esta quebrado. Ausencia de dados NAO e promessa de
    nivel — o resultado neutro deixa isso explicito.
    """
    try:
        from backend.vip_progress import progresso

        return progresso()
    except Exception:  # noqa: BLE001 - tela de progresso nao pode derrubar o app
        return {
            "ok": False,
            "nivel": {"id": "regular", "nome": "Regular"},
            "escada": [],
            "total_degraus": 0,
            "volume_por_grupo": {},
            "janela_dias": 30,
            "indisponivel": True,
            "motivo": "sem dados de volume para calcular a progressao",
        }


def acesso(user_id: str | None = None) -> dict[str, Any]:
    """Arvore completa: plano, volume e o que cada um destrava.

    Esta e a unica funcao que a tela e a API devem chamar. Ela junta o que
    antes vinha de dois lugares sem se falar — a origem da duplicata.

    `features` diz o que o PLANO abre. `volume` diz a profundidade. E
    `multi_model` e True so quando as duas condicoes de
    `pode_usar_multi_modelo` passam.
    """
    assinatura = plano_atual(user_id)
    volume = nivel_por_volume(user_id)
    return {
        "plano": assinatura["plan_id"],
        "plano_ativo": assinatura["active"],
        "degraded": assinatura["degraded"],
        "features": assinatura["entitlements"],
        "limits": assinatura["limits"],
        "multi_model": pode_usar_multi_modelo(user_id),
        "multi_models": limite_multi_modelos(user_id),
        "volume": {
            "nivel": volume.get("nivel", {}),
            "escada": volume.get("escada", []),
            "total_degraus": volume.get("total_degraus", 0),
            "por_grupo": volume.get("volume_por_grupo", {}),
            "janela_dias": volume.get("janela_dias", 30),
            "dias_ate_promocao": volume.get("dias_ate_promocao", 1),
            "disponivel": not volume.get("indisponivel", False),
            "motivo": volume.get("motivo", ""),
        },
        # Declarado aqui tambem: nenhum destes dois destrava dinheiro real.
        "live_execution": False,
        "withdrawals_enabled": False,
    }