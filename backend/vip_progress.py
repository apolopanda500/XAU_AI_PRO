# -*- coding: utf-8 -*-
"""Progressao VIP medida pelo volume real de operacao.

POR QUE ISTE EXISTE
===================
O projeto tinha tres nomes de plano (Free / VIP / VIPS) e nenhuma relacao
entre operar e subir de nivel. Nas corretoras reais e o oposto: o nivel e
conquistado por VOLUME, e a corretora mostra quanto falta.

AS DUAS REFERENCIAS USADAS
==========================

**PrimeXBT** ("How VIP Tiers Work") — cinco niveis alem do Regular. O que
muda por nivel e taxa taker, desconto de spread, desconto na exchange e
cashback; o maker fica igual em todos. O status e recalculado por volume de
30 dias e, ao ser alcancado, **trava por 30 dias**: o cliente nao cai de
nivel no meio do ciclo. Detalhe que importa: o volume e contado por **grupo
de instrumento** — cripto e forex tem limiares diferentes (10.000 USD em
cripto sobe para VIP1; 100.000 USD em forex).

**IC Markets** ("Raw Spread Account") — o outro extremo: nao ha nivel, ha um
unico tipo de conta com spread 0,0 e comissao de US$ 3,50 por lote por lado.
A mesma logica vista pelo outro lado: o custo total (spread + comissao) e a
unica coisa negociada, e a conta existe para quem opera volume alto.

O QUE FAZ
=========
Le o `audit.jsonl` real, soma o volume executado na janela de 30 dias e diz
em que nivel o operador esta e quanto falta para o proximo.

O QUE NAO FAZ
==============
Nao libera dinheiro real, nao altera plano, nao promete spread. Os limiares
aqui sao de ESTRUTURA, nao promessa comercial. A trava de saque continua
em `AGENTS.md` e `plano_gate.py`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Janela de recalculo. O PrimeXBT trava o nivel alcancado por 30 dias: sem
# isso um mes fraco tiraria o cliente do nivel no meio do ciclo, e ele
# perderia desconto que ja pagou para entrar.
JANELA_DIAS = 30

# Grupo de instrumento -> corretoras. O volume e contado separado porque o
# limiar muda por grupo: cripto e mais liquido e sobe com volume menor.
GRUPOS_INSTRUMENTO: dict[str, set[str]] = {
    "cripto": {"binance", "bybit", "okx", "mexc"},
    "forex_cfd": {"mt5", "pepperstone", "icmarkets", "xm", "fxcm"},
}


# Estrutura dos niveis, com limiares de volume em USD.
#
# Duas fontes, e por que a segunda entra aqui:
#
# PRIME.XBT — cinco niveis alem do Regular. Limiar por grupo de
# instrumento: 10.000 USD em cripto sobe para VIP1, mas em forex sao
# 100.000 USD (cripto e 10x mais liquido). O nivel trava 30 dias ao ser
# alcancado, para o cliente nao perder no meio do ciclo um desconto pelo
# qual ja pagou.
#
# INTERACTIVE BROKERS — a mesma ideia com nomes e muito mais degraus. A
# comissao cai em degraus conforme o volume mensal cresce (0,05% ->
# 0,03% -> 0,02% -> 0,015% do valor negociado). Duas regras dela valem
# aqui e NAO valem no PrimeXBT:
#
# 1. "Calculated once daily, not at the time of the trade. The execution
#    reduction starts the NEXT TRADING DAY after the threshold is
#    exceeded." — o nivel NAO e imediato. Quem cruza o limiar as 23h50
#    descobre amanha. Isso evita a corrida de última hora em que todo
#    mundo infla o volume para fechar o mes.
#
# 2. "Only shares traded while under the Tiered pricing structure will
#    count towards the monthly volume." — o volume que conta e o do mes
#    corrente, nao acumulado vitalicio. Ja e o que JANELA_DIAS faz, mas a
#    frase deixa o motivo explicito.
#
# O que NAO esta aqui: o desconto em si. IBKR e PrimeXBT tem acordos
# diferentes, e o preco do produto deste projeto depende de decisao
# comercial. A tela mostra o nivel e a distancia ate o proximo — nunca um
# numero que o sistema nao pode cumprir.
NIVEIS: list[dict[str, Any]] = [
    {"id": "regular", "nome": "Regular",
     "minimo_por_grupo": {"cripto": 0.0, "forex_cfd": 0.0},
     "beneficios": ["Spread padrao", "Execucao pelo caminho do terminal"]},
    {"id": "vip1", "nome": "VIP 1",
     "minimo_por_grupo": {"cripto": 10_000.0, "forex_cfd": 100_000.0},
     "beneficios": ["Spread reduzido", "Prioridade na fila de execucao"]},
    {"id": "vip2", "nome": "VIP 2",
     "minimo_por_grupo": {"cripto": 100_000.0, "forex_cfd": 1_000_000.0},
     "beneficios": ["Spread reduzido 2o degrau", "Analise ampliada"]},
    {"id": "vip3", "nome": "VIP 3",
     "minimo_por_grupo": {"cripto": 1_000_000.0, "forex_cfd": 10_000_000.0},
     "beneficios": ["Spread reduzido 3o degrau", "Auditoria completa"]},
    {"id": "vip4", "nome": "VIP 4",
     "minimo_por_grupo": {"cripto": 5_000_000.0, "forex_cfd": 45_000_000.0},
     "beneficios": ["Spread reduzido 4o degrau", "Suporte prioritario"]},
    {"id": "vip5", "nome": "VIP 5",
     "minimo_por_grupo": {"cripto": 25_000_000.0, "forex_cfd": 90_000_000.0},
     "beneficios": ["Spread minimo do catalogo", "Suporte dedicado"]},
]

# O nivel nao sobe no mesmo instante em que o limiar e cruzado. A IBKR e
# explicita: o calculo e diario e a reducao comeca no dia seguinte. O
# motivo e o contrapeso da corrida de fim de mes — sem ele, todo mundo
# operaria no ultimo minuto so para fechar o numero.
DIAS_ATE_PROMOCAO = 1


# Atos que contam como volume realizado. `order` sozinho nao prova fill — o
# cancelamento logo depois nao movimenta nada.
ATOS_DE_VOLUME = {"trade/universal/order", "trade/universal/execute"}


def _audit_path() -> Path:
    return Path(os.getenv("APPDATA", str(Path.home()))) / "XAU_AI_PRO" / "audit.jsonl"


def _grupo_do_corretora(broker: str) -> str:
    chave = str(broker or "").strip().lower()
    for grupo, corretoras in GRUPOS_INSTRUMENTO.items():
        if chave in corretoras:
            return grupo
    return "forex_cfd"


def _parse_iso(valor: Any) -> datetime | None:
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def volume_por_grupo(dias: int = JANELA_DIAS) -> dict[str, float]:
    """Volume executado por grupo na janela.

    A fonte e o `audit.jsonl` gravado pelo proprio produto. Se o arquivo nao
    existe, o resultado e zero — e zero e a resposta honesta, nao um chute.
    """
    caminho = _audit_path()
    vazio = {grupo: 0.0 for grupo in GRUPOS_INSTRUMENTO}
    if not caminho.exists():
        return vazio
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    total = dict(vazio)
    try:
        linhas = caminho.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return vazio
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        try:
            evento = json.loads(linha)
        except ValueError:
            continue  # linha truncada por queda de energia: nao e dado valido
        if not isinstance(evento, dict) or evento.get("action") not in ATOS_DE_VOLUME:
            continue
        if str(evento.get("status", "")).lower() != "executed":
            continue
        quando = _parse_iso(evento.get("at"))
        if quando is None or quando < corte:
            continue
        try:
            quantidade = abs(float(evento.get("volume") or evento.get("quantity")))
        except (TypeError, ValueError):
            continue
        if quantidade > 0:
            total[_grupo_do_corretora(evento.get("broker"))] += quantidade
    return total


def nivel_por_volume(volumes: dict[str, float]) -> dict[str, Any]:
    """Nivel alcancado e quanto falta para o proximo.

    O nivel e o MAIOR em que TODOS os grupos passam. Sem isso, quem tivesse
    500.000 em cripto e 20.000 em forex subiria olhando so para o cripto, e
    perderia o desconto do grupo que nao atingiu.
    """
    alcancado = NIVEIS[0]
    for nivel in NIVEIS:
        if all(volumes.get(g, 0.0) >= m for g, m in nivel["minimo_por_grupo"].items()):
            alcancado = nivel
        else:
            break
    proximo = None
    # O proximo e o primeiro nivel NAO alcancado. Pular direto para o primeiro
    # da lista daria "falta 0" quando o operador ja passou por ele — o
    # cliente veria a barra cheia e nenhuma meta pela frente.
    for nivel in NIVEIS:
        if all(volumes.get(g, 0.0) >= m for g, m in nivel["minimo_por_grupo"].items()):
            continue
        proximo = {
            "id": nivel["id"],
            "nome": nivel["nome"],
            "falta_por_grupo": {
                grupo: max(0.0, minimo - volumes.get(grupo, 0.0))
                for grupo, minimo in nivel["minimo_por_grupo"].items()
            },
        }
        break
    return {
        "nivel": alcancado["id"],
        "nivel_nome": alcancado["nome"],
        "beneficios": list(alcancado["beneficios"]),
        "proximo": proximo,
    }


def escada_completa(volumes: dict[str, float], alcancado_id: str) -> list[dict[str, Any]]:
    """A escada inteira, na ordem, com o estado de cada degrau.

    POR QUE A TELA PRECISA DA ESCADA E NAO SO DO PROXIMO
    ====================================================
    Antes esta funcao nao existia: a tela recebia o nivel alcancado e o
    proximo, e nada mais. O operador via "falta US$ 10.000" sem enxergar a
    escada — quantos degraus existem, qual dele ele esta alcancando, e o que
    vem DEPOIS. Um nivel isolado nao diz se a meta esta longe ou perto.

    `percentual` responde a pergunta que o operador realmente faz ("quanto
    eu ja fiz deste degrau?"). Ele usa o grupo mais atrasado: o nivel so
    conta quando TODOS passam, e mostrar o melhor grupo daria um numero
    maior do que a reality.

    `estado` e um de `alcancado`, `atual` ou `futuro`. A tela usa isso para
    marcar a linha — e nao para prometer: um degrau `futuro` mostra o
    limiar, nunca um desconto.
    """
    escada: list[dict[str, Any]] = []
    passou_atual = False
    # Marca se o proximo degrau ALCANÇAVEL ainda nao recebeu o rotulo
    # `atual`. Comeca ligada: logo apos o alcancado, o primeiro degrau e o
    # proximo alvo.
    estado_atual_pendente = True
    for nivel in NIVEIS:
        minimos = nivel["minimo_por_grupo"]
        # Groupo mais atrasado: o que decide a subida. Teto de 100 para o
        # primeiro degrau (limiar zero nao produce divisao por zero).
        percentuais = [
            min(100.0, (volumes.get(g, 0.0) / m * 100.0) if m > 0 else 100.0)
            for g, m in minimos.items()
        ]
        percentual = min(percentuais) if percentuais else 0.0
        # `alcancado` e o unico degrau confirmado. `atual` e o proximo a
        # perseguir — exatamente UM. Marcar todos os posteriores como
        # `atual` diria ao operador que ele precisa trabalhar em cinco
        # degraus ao mesmo tempo, o que e falso: so o proximo conta.
        if nivel["id"] == alcancado_id:
            estado = "alcancado"
            passou_atual = True
        elif not passou_atual:
            estado = "futuro"  # abaixo do alcancado: inatingivel nesta ordem
        else:
            estado = "atual" if estado_atual_pendente else "futuro"
            estado_atual_pendente = False
        escada.append({
            "id": nivel["id"],
            "nome": nivel["nome"],
            "estado": estado,
            "percentual": round(percentual, 1),
            "minimo_por_grupo": {g: float(m) for g, m in minimos.items()},
            "beneficios": list(nivel["beneficios"]),
        })
    return escada


def progresso() -> dict[str, Any]:
    """Estado completo da progressao, para a tela e para a API."""
    volumes = volume_por_grupo()
    resultado = nivel_por_volume(volumes)
    resultado["volume_por_grupo"] = volumes
    resultado["janela_dias"] = JANELA_DIAS
    resultado["trava_dias"] = JANELA_DIAS
    # Regra da IBKR: o nivel nao promove no mesmo instante. Quem cruza o
    # limiar as 23h50 descobre o novo nivel no dia seguinte. A tela mostra
    # isso para o operador nao operar no ultimo minuto achando que o
    # desconto ja esta valendo.
    resultado["dias_ate_promocao"] = DIAS_ATE_PROMOCAO
    resultado["fonte"] = "audit.jsonl"
    # A escada inteira, para o operador enxergar onde esta e o que vem
    # depois. Sem isto a tela mostrava um degrau solto.
    resultado["escada"] = escada_completa(volumes, resultado["nivel"])
    resultado["total_degraus"] = len(NIVEIS)
    # A trava de dinheiro real e declarada aqui tambem: a progressao nao
    # habilita saque, transferencia nem execucao real.
    resultado["live_execution"] = False
    resultado["withdrawals_enabled"] = False
    return resultado
