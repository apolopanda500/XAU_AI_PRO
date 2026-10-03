# -*- coding: utf-8 -*-
"""METAS e TRAVAS do VIP: o que destrava, o que trava e ate quando.

O PROBLEMA QUE ESTE MODULO RESOLVE
==================================
Ate 02/10/2026 o VIP era decorativo. `vip_progress.progresso()` desenhava
a escada com percentual, mas nunca escrevia em `entitlements` — subir de
nivel por volume nao abria nada. E o dono reportou **duplicatas**: dois
sistemas de plano (comprado + volume) que nao se falavam.

Este modulo e a unica fonte de verdade da TRAVA. `backend/acesso.py` le
aqui; a tela le aqui; a API le aqui. Nenhum outro lugar decide o que esta
liberado.

AS DUAS METAS — E POR QUE SAO DUAS
===================================
O dono pediu: *"usuario operou x volume OU comprou 100$ do vips pro"*.

| Meta | Como se cumpre | Para quem |
|---|---|---|
| `volume` | opera e atinge o limiar no ciclo | quem opera muito |
| `compra` | paga o plano | quem quer o recurso sem operar ainda |

OR vs E
------
Sao **OU**, nunca E. Se fosse E, quem comprou e ainda nao operou ficaria
travado sem poder usar o que pagou — e ninguem paga por um recurso que
nao abre. Se fosse so OU de volume, quem nunca operaria nao teria caminho
para o PRO.

A consequencia de serem OU e que **as duas podem这一个 destravar a mesma
feature**, e isso nao e duplicata: e o mesmo beneficio alcancado por dois
caminhos declarados. Duplicata seria o mesmo beneficio aparecer **duas
vezes na tela** com nomes diferentes — que e o que `SettingsCore` deixou
de fazer ao remover a aba Planos.

A REGRA QUE RESOLVE A DUPLICATA
===============================
**O PLANO E O COMERCIAL. O VOLUME E O MERITO. Nenhum dos dois, sozinho,
promete o que o outro nao cobre:**

| Caminho | Resultado |
|---|---|
| VIP1 por volume | Entra no escopo do VIP |
| VIP pago, sem volume | Entra no escopo do VIP |
| VIP + VIP3 volume | VIP com profundidade maior |
| **VIP3 sem VIP pago** | **Nada** — volume nao compra plano |

A 4a linha e a que importa. Sem ela existiriam dois jeitos de destravar a
mesma coisa e o sistema nao saberia qual cobrar.

TRAVAS DECLARADAS (2026-10-02)
==============================
`multi_model` — o unico caminho para `MULTI_<GRUPO>_<TF>`. **Free nunca**,
por decisao do dono, com reforco duplo em `acesso.py`.

O QUE NAO PASSA POR AQUI
========================
Dinheiro real, saque e transferencia. `live_execution` e
`withdrawals_enabled` sao `False` em toda meta e em todo plano, sem excecao.
Ver `AGENTS.md`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Plano que nunca usa multi, em nenhuma hipotese.
PLANO_SEM_MULTI = "free"

#: Preco de referencia do PRO, em USD. O dono definiu "comprou 100$".
PRECO_PRO_USD = 100.0

#: Feature que abre os modelos `MULTI_<GRUPO>_<TF>`.
ENTITLEMENT_MULTI_MODEL = "multi_model"


@dataclass(frozen=True)
class Meta:
    """Uma meta, e a regra de como ela se cumpre.

    `caminho` documenta QUAL dos dois jeitos abre a meta. Os dois sao
    aceitos: `ou_compra` OU `ou_volume`. Ver a secao "OR vs E" acima para
    por que nunca exigimos os dois juntos.
    """

    id: str
    nome: str
    #: Volume em USD por grupo de instrumento. Vazio = meta nao depende de volume.
    minimo_por_grupo: dict[str, float] = field(default_factory=dict)
    #: Plano que cumpre a meta por compra.
    plano_por_compra: str = ""
    #: Preco de referencia em USD quando a meta e por compra.
    preco_usd: float = 0.0
    #: Feature liberada quando a meta e atingida.
    libera: str = ""
    beneficios: list[str] = field(default_factory=list)
    descricao: str = ""


#: As metas, em ordem de escada. `livre` e o degrau zero e sempre vale.
METAS: tuple[Meta, ...] = (
    Meta(
        id="livre",
        nome="Livre",
        minimo_por_grupo={},
        plano_por_compra="free",
        preco_usd=0.0,
        libera="paper_execution",
        beneficios=["Paper/demo", "IA basica", "Alertas de preco"],
        descricao="Entrada no produto. Modelo unico por ativo.",
    ),
    Meta(
        id="pro",
        nome="PRO",
        minimo_por_grupo={"cripto": 10_000.0, "forex_cfd": 100_000.0},
        plano_por_compra="vip",
        preco_usd=PRECO_PRO_USD,
        libera=ENTITLEMENT_MULTI_MODEL,
        beneficios=[
            "Motor automatico",
            "Calendario economico",
            "Multiplas contas",
            "Social paper",
            "2 modelos multi",
        ],
        descricao=(
            "Destrava o modelo MULTI (PRO). Cumpre por compra do plano VIP "
            "ou por volume — os dois valem, um basta."
        ),
    ),
    Meta(
        id="vip",
        nome="VIP",
        minimo_por_grupo={"cripto": 100_000.0, "forex_cfd": 1_000_000.0},
        plano_por_compra="vips",
        preco_usd=PRECO_PRO_USD * 3,
        libera="advanced_audit",
        beneficios=[
            "Tudo do PRO",
            "8 modelos multi",
            "Auditoria avancada",
            "Suporte prioritario",
        ],
        descricao="Escada ampliada. Volume maior ou plano VIPS.",
    ),
)


#: Ordem de planos que contam como "comprou". O `plan_id` gravado e comparado
#: por esta ordem, e nao por igualdade: quem tem `vips` tambem passageou por
#: `vip`. Sem isso, o VIPS naoabria a meta PRO que ele contem.
ORDEM_PLANOS: tuple[str, ...] = ("free", "vip", "vips")


def _indice_do_plano(plan_id: str) -> int:
    """Posicao do plano na escada. Plano desconhecido vale como `free`.

    Fail-closed: um `plan_id` adulterado no `subscriptions.json` nao pode
    virar o topo da escada. `-1` e menor que `free`, entao so o menor vence.
    """
    try:
        return ORDEM_PLANOS.index(str(plan_id or "").strip().lower())
    except ValueError:
        return -1


def _grupos() -> tuple[str, ...]:
    """Grupos que aparecem em alguma meta, sem repetir."""
    vistos: list[str] = []
    for meta in METAS:
        for grupo in meta.minimo_por_grupo:
            if grupo not in vistos:
                vistos.append(grupo)
    return tuple(vistos)


def _cumpre_por_volume(meta: Meta, volumes: dict[str, float]) -> tuple[bool, dict[str, float]]:
    """True quando TODOS os grupos da meta passam do limiar.

    Todos, e nao o melhor grupo: quem tem 500.000 em cripto e 20.000 em forex
    nao cumpriu a meta, porque no forex ainda falta. Escolher o grupo mais
    adiantado mostraria a meta cumprida quando nao esta.
    """
    if not meta.minimo_por_grupo:
        return True, {}
    falta = {
        grupo: max(0.0, minimo - float(volumes.get(grupo, 0.0) or 0.0))
        for grupo, minimo in meta.minimo_por_grupo.items()
    }
    cumprida = all(valor <= 0.0 for valor in falta.values())
    return cumprida, falta


def _cumpre_por_compra(meta: Meta, plano_id: str) -> bool:
    """True quando o plano comprado alcanca o plano exigido pela meta."""
    if not meta.plano_por_compra:
        return False
    return _indice_do_plano(plano_id) >= _indice_do_plano(meta.plano_por_compra)


def _caminhos_da_meta(meta: Meta) -> list[str]:
    """Como a meta pode ser cumprida, em texto curto para a tela."""
    caminhos: list[str] = []
    if meta.plano_por_compra:
        caminhos.append(f"comprar {meta.plano_por_compra}")
    if meta.minimo_por_grupo:
        caminhos.append("operar o volume do ciclo")
    return caminhos


def multi_model_liberado(plan_id: str, volumes: dict[str, float] | None = None) -> bool:
    """Regra do dono: *"FREE nao pode usar multi"*.

    Duas condicoes, e as duas sao necessarias:

    1. `plan_id != "free"` — o plano nunca e o Free.
    2. A meta `pro` esta cumprida, por **compra ou volume**.

    A 1 e o reforco: mesmo que o `subscriptions.json` da maquina seja editado
    a mao, o Free nao libera.

    Sem volume informado, so o caminho de compra e avaliado. Quem tem VIP1
    por volume e esta no Free nao entra aqui — e o resultado correto: sem
    plano, o volume nao compra acesso.
    """
    if _indice_do_plano(plan_id) <= _indice_do_plano(PLANO_SEM_MULTI):
        return False
    meta_pro = next((m for m in METAS if m.libera == ENTITLEMENT_MULTI_MODEL), None)
    if meta_pro is None:
        return False
    if _cumpre_por_compra(meta_pro, plan_id):
        return True
    ok_volume, _ = _cumpre_por_volume(meta_pro, volumes or {})
    return ok_volume


def avaliar(plan_id: str, volumes: dict[str, float] | None = None) -> dict[str, Any]:
    """Estado completo das metas: o que cumpriu, por que e o que falta.

    Este e o unico lugar que decide o que esta destravado. A tela, a API e
    `acesso.py` leem daqui; nenhum deles recalcula.

    Retorna as metas **todas**, alcancadas ou nao. Um degrau futuro mostra o
    limiar, nunca um desconto: o sistema nao promete o que ainda nao cumpriu.
    """
    volumes = dict(volumes or {})
    indice_plano = _indice_do_plano(plan_id)
    escada: list[dict[str, Any]] = []
    alcancadas: list[dict[str, Any]] = []
    passou = False
    proximo: dict[str, Any] | None = None

    for meta in METAS:
        ok_volume, falta = _cumpre_por_volume(meta, volumes)
        ok_compra = _cumpre_por_compra(meta, plan_id)
        cumprida = ok_volume or ok_compra
        if meta.id == "livre":
            cumprida = True  # degrau zero: sempre verdadeiro

        # Caminhos que chegaram nesta meta, para a tela mostrar o PORQUE.
        caminhos: list[str] = []
        if meta.plano_por_compra and indice_plano >= _indice_do_plano(meta.plano_por_compra):
            caminhos.append("compra")
        if ok_volume:
            caminhos.append("volume")

        if cumprida:
            passou = True
            estado = "alcancado"
            # `proxima` NAO e preenchida aqui. A meta alcancada e o ONDE o
            # operador ESTA, nao o alvo dele. Preencher aqui fazia `proxima`
            # devolver a primeira meta alcancada em vez da proxima meta a
            # perseguir — em "VIP zero" voltava `pro`, que ja era alcancada,
            # e o operador via "faltam 100k no forex" para algo que ja tinha.
            # O alvo e sempre a primeira meta NAO cumprida, tratado no ramo
            # "atual" abaixo.
        elif not passou:
            estado = "futuro"  # abaixo do alcancado: inatingivel nesta ordem
        else:
            # Exatamente UMA meta pode ser `atual`: a primeira nao cumprida
            # acima da alcancada. Marcar as demais tambem como `atual` diz ao
            # operador que ele persegue tres metas ao mesmo tempo, que e falso.
            # `vip_progress.escada_completa` ja faz essa distincao ("so um
            # degrau e atual"); aqui e a mesma regra, no mesmo lugar.
            if proximo is None:
                estado = "atual"
                proximo = {
                    "id": meta.id, "nome": meta.nome, "libera": meta.libera,
                    "preco_usd": meta.preco_usd, "falta_por_grupo": falta,
                    "caminhos_aceitos": _caminhos_da_meta(meta),
                    "beneficios": list(meta.beneficios),
                }
            else:
                estado = "futuro"

        percentuais = [
            min(100.0, (float(volumes.get(g, 0.0) or 0.0) / m * 100.0) if m > 0 else 100.0)
            for g, m in meta.minimo_por_grupo.items()
        ]
        escada.append({
            "id": meta.id,
            "nome": meta.nome,
            "estado": estado,
            "percentual": round(min(percentuais) if percentuais else 100.0, 1),
            "minimo_por_grupo": {g: float(m) for g, m in meta.minimo_por_grupo.items()},
            "preco_usd": meta.preco_usd,
            "libera": meta.libera,
            "caminhos_aceitos": _caminhos_da_meta(meta),
            "beneficios": list(meta.beneficios),
            "descricao": meta.descricao,
        })
        if cumprida and meta.id != "livre":
            alcancadas.append({"id": meta.id, "nome": meta.nome, "caminhos": caminhos})

    return {
        "ok": True,
        "plano": str(plan_id or "free"),
        "metas_alcancadas": alcancadas,
        "proxima": proximo,
        "escada": escada,
        "total_degraus": len(METAS),
        "volume_por_grupo": {g: float(volumes.get(g, 0.0) or 0.0) for g in _grupos()},
        "multi_model": multi_model_liberado(plan_id, volumes),
        # Declarado aqui: nenhuma meta destrava dinheiro real.
        "live_execution": False,
        "withdrawals_enabled": False,
    }


def estado_do_usuario(plan_id: str, volumes: dict[str, float] | None = None) -> dict[str, Any]:
    """Wrapper com o nome que a tela e a API entendem.

    Separado de `avaliar` para que o nome clique na rota: `avaliar` responde
    "como esta o catalogo de metas", `estado_do_usuario` responde "o que este
    usuario destravou".
    """
    return avaliar(plan_id, volumes)