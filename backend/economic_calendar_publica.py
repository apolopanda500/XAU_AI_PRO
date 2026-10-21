# -*- coding: utf-8 -*-
"""Adaptador do calendario publico de divulgacoes, sem chave de API.

POR QUE ISTO EXISTE (05/10/2026)
===============================
A aba Calendario mostrava Anterior / Previsao / Real em tres colunas, e as
tres eram permanentemente `--`. A causa esta em
`backend/planos/economic_calendar.py`: `_BASE_EVENTS` e uma TABELA LOCAL de
horarios recorrentes. Ela sabe QUANDO o evento acontece e nada mais. Nao ha
valor anterior, nem consenso, nem numero divulgado — porque nao existe tal
informacao na fonte.

Ou seja: tres colunas que nunca podiam ter dado. Isso e pior que coluna
ausente, porque o operador passa a desconfiar das outras.

A fonte publica
===============
`https://nfs.faireconomy.media/ff_calendar_thisweek.json` e um feed publico,
sem chave e sem registro, que entrega a semana corrente com `country`,
`impact`, `title`, `previous`, `forecast` e `actual`. Foi medido em 05/10/2026:
79 eventos na semana, 4 de alto impacto, 39 com previsao e 57 com anterior.

LIMITE DECLARADO, NAO ESCONDIDO
===============================
O feed cobre SO a semana corrente. `ff_calendar_nextweek.json` e
`ff_calendar_lastweek.json` respondem 404. Entao:

- a semana corrente vem do feed, com numero de verdade;
- as semanas seguintes continuam vindo de `_BASE_EVENTS`, que sao ESTIMATIVAS.

As duas nunca sao misturadas sem avisar: cada evento carrega `fonte` e
`estimado`, e a tela mostra isso. O dono pediu para nao usar dado simulado como
se fosse dado de mercado real — a regra vale em duas direcoes: um horario
estimado tambem nao pode parecer um horario confirmado.

FALHA DE REDE
=============
Levanta `CalendarUnavailable`. O chamador decide o que fazer; o adaptador nunca
devolve lista vazia fingindo que nao ha evento nenhum — lista vazia e "nao
consegui perguntar" sao respostas diferentes.

CACHE EM DISCO E POR QUE
=======================
O feed responde 429 (medido em 05/10/2026, depois de duas consultas seguidas).
Uma agenda economica nao muda no mesmo segundo, entao perguntar a cada 5 minutos
era desperdicio que acabava barrado.

O cache dura 30 minutos e fica em `%APPDATA%\\XAU_AI_PRO\\cache_calendar.json`.
E o cache serve DUAS coisas:

1. nao hammering no feed;
2. quando o feed esta limitando, o operador ainda ve a agenda da ultima
   consulta, marcada com `idade_minutos` — em vez de uma agenda de estimativas
   que parece igual a uma falha.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

#: Feed publico, sem chave. Medido 200 em 05/10/2026.
FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

#: User-Agent honesto: o app se identifica em vez de parecer navegador.
USER_AGENT = "XAU_AI_PRO/1.2 (calendario; contato local)"

#: A agenda economica nao pode travar a tela. 6 s e o teto; um feed lento
#: devolve "nao foi possivel consultar", nunca um numero inventado.
TIMEOUT_S = 6

#: Cache: 30 min. A agenda muda no dia, no minuto — nao no segundo.
CACHE_TTL_MIN = 30

#: Impacto do feed -> os tres niveis que a tela conhece.
IMPACTO = {
    "high": "alto",
    "medium": "medio",
    "medium-low": "medio",
    "low": "baixo",
    "holiday": "baixo",
}

#: O feed manda codigo de moeda em `country`. Moeda que o app conhece e
#: precious metal ou fiat relevante; o resto entra como o codigo, sem nome
#: inventado. NENHUM nome de ativo e fixado aqui.
BANDEIRA = {
    "USD": "\U0001F1FA\U0001F1F8",
    "EUR": "\U0001F1EA\U0001F1FA",
    "GBP": "\U0001F1EC\U0001F1E7",
    "JPY": "\U0001F1EF\U0001F1F5",
    "AUD": "\U0001F1E6\U0001F1FA",
    "CAD": "\U0001F1E8\U0001F1E6",
    "CHF": "\U0001F1E8\U0001F1ED",
    "NZD": "\U0001F1F3\U0001F1FF",
    "CNY": "\U0001F1E8\U0001F1F3",
    "BRL": "\U0001F1E7\U0001F1F7",
    "MXN": "\U0001F1F2\U0001F1FD",
    "ZAR": "\U0001F1FF\U0001F1E6",
    "INR": "\U0001F1EE\U0001F1F3",
    "KRW": "\U0001F1F0\U0001F1F7",
    "SGD": "\U0001F1F8\U0001F1EC",
    "HKD": "\U0001F1ED\U0001F1F0",
}


class CalendarUnavailable(RuntimeError):
    """O feed publico nao respondeu. Nao e lista vazia."""


def _cache_path() -> Path:
    base = Path(os.getenv("APPDATA", str(Path.home()))) / "XAU_AI_PRO"
    return base / "cache_calendar.json"


def ler_cache() -> tuple[list[dict[str, Any]], int] | None:
    """Cache ainda valido: os eventos e a idade em minutos.

    Devolve `None` quando nao ha cache, ele expirou, ou o arquivo esta
    corrompido. Cache corrompido e descartado sem erro: ele e otimizacao, nao
    fonte — e uma fonte corrompida que derrubasse a agenda seria o pior
    resultado possivel.
    """
    caminho = _cache_path()
    if not caminho.exists():
        return None
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(str(bruto["ts"]))
        eventos = bruto["events"]
        if not isinstance(eventos, list):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if datetime.now(timezone.utc) - ts > timedelta(minutes=CACHE_TTL_MIN):
        return None
    idade = max(0, int((datetime.now(timezone.utc) - ts).total_seconds() // 60))
    return eventos, idade


def gravar_cache(eventos: list[dict[str, Any]]) -> None:
    """Grava o cache. Falha aqui e silenciosa de proposito: sem cache funciona
    igual, so que consulta mais vezes."""
    try:
        caminho = _cache_path()
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "events": eventos}),
            encoding="utf-8",
        )
    except OSError:
        return


def _bandeira(moeda: str) -> str:
    return BANDEIRA.get(moeda, "\U0001F3F3")


def _texto(valor: Any) -> str | None:
    """Normaliza campo do feed: string vazia e espaco viram ausente.

    O feed manda `""` para campo nao publicado. Deixar `""` na tela produz
    celula vazia ao lado de celula com "--", e o operador nao sabe qual das
    duas e ausencia de verdade.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _quando(valor: Any) -> datetime | None:
    """`date` do feed vem em ISO com deslocamento (-04:00)."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        momento = datetime.fromisoformat(valor.strip())
    except ValueError:
        return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def buscar_semana(atual: datetime | None = None) -> list[dict[str, Any]]:
    """Eventos da semana corrente, como o feed publica.

    Cache primeiro: agenda economica nao muda no segundo, e o feed responde 429
    quando consulta demais. Com o cache valido, nao ha rede nenhuma.

    Levanta `CalendarUnavailable` quando nao ha cache E o feed nao responde.
    Devolver `[]` seria dizer "esta semana nao tem evento" — e mentira.
    """
    guardado = ler_cache()
    if guardado is not None:
        return guardado[0]

    requisicao = urllib.request.Request(
        FEED_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=TIMEOUT_S) as resposta:
            corpo = resposta.read()
    except urllib.error.HTTPError as exc:
        # 429 e o caso medido: o feed barra taxa. A mensagem diz isso, porque
        # "indisponivel" generico leva o operador a culpar o gateway local.
        raise CalendarUnavailable(f"feed publico recusou a consulta (HTTP {exc.code})") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise CalendarUnavailable(f"feed publico nao respondeu: {exc}") from exc

    try:
        dados = json.loads(corpo.decode("utf-8", errors="replace"))
    except ValueError as exc:
        raise CalendarUnavailable("feed publico devolveu corpo ilegivel") from exc
    if not isinstance(dados, list):
        raise CalendarUnavailable("feed publico devolveu algo que nao e lista")

    agora = (atual or datetime.now(timezone.utc)).astimezone(timezone.utc)
    eventos: list[dict[str, Any]] = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        evento = _normaliza(item, agora)
        if evento is not None:
            eventos.append(evento)
    eventos.sort(key=lambda evento: evento["when_utc"])
    gravar_cache(eventos)
    return eventos


def _normaliza(item: dict, agora: datetime) -> dict[str, Any] | None:
    """Um item do feed vira evento, ou `None` se faltar o que identifica um.

    Fica separado de `buscar_semana` para poder ser testado sem rede — e
    testar sem rede é a única forma de cobrir `previous`/`forecast`/`actual`
    com o formato MEDIDO, e não com o formato que a gente imagina.
    """
    momento = _quando(item.get("date"))
    titulo = _texto(item.get("title"))
    moeda = (_texto(item.get("country")) or "").upper()
    if momento is None or not titulo or not moeda:
        return None
    return {
        "title": titulo,
        "currency": moeda,
        "impact": IMPACTO.get((_texto(item.get("impact")) or "").lower(), "medio"),
        "note": _texto(item.get("note")) or "",
        "when_utc": momento.isoformat(timespec="minutes"),
        "bandeira": _bandeira(moeda),
        # Os tres campos que a tabela local nao tinha.
        "previous": _texto(item.get("previous")),
        "forecast": _texto(item.get("forecast")),
        "actual": _texto(item.get("actual")),
        "divulgado": momento <= agora,
        # Rótulo de procedencia. A tela mostra, e o teste exige.
        "fonte": "feed-publico",
        "estimado": False,
    }


def suplementar(estimados: list[dict[str, Any]]) -> dict[str, Any]:
    """Junta o feed real com as estimativas das semanas seguintes.

    A semana corrente e real; o que passa dela e estimativa. Nenhum evento
    reescreve outro, e a resposta diz as duas coisas para a tela nao misturar.

    `fontes.erro` carrega o motivo quando o feed nao respondeu. Sem ele, o
    operador veria uma agenda so de estimativas e nenhum aviso — que e
    exatamente o defeito que este arquivo veio corrigir.
    """
    agora = datetime.now(timezone.utc)
    fimDaSemana = agora + timedelta(days=7)
    erro = ""
    try:
        reais = buscar_semana(agora)
    except CalendarUnavailable as exc:
        reais = []
        erro = str(exc)

    def rotulo(evento: dict[str, Any]) -> dict[str, Any]:
        copia = dict(evento)
        copia.setdefault("previous", None)
        copia.setdefault("forecast", None)
        copia.setdefault("actual", None)
        if "estimado" not in copia:
            # Vem de `_BASE_EVENTS`: horario RECORRENTE estimado, sem valor.
            copia["estimado"] = True
            copia["fonte"] = "estimativa-local"
        copia.setdefault("bandeira", _bandeira(str(evento.get("currency", "")).upper()))
        return copia

    estimativas = [
        rotulo(evento)
        for evento in estimados
        if (_quando(evento.get("when_utc")) or agora) >= fimDaSemana
    ]
    return {
        "events": reais + estimativas,
        "fontes": {
            "reais": len(reais),
            "estimados": len(estimativas),
            "feed_disponivel": bool(reais),
            "erro": erro,
            "idade_cache_min": (ler_cache() or (None, 0))[1] if not erro else 0,
        },
    }