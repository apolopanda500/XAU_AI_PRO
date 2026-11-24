# -*- coding: utf-8 -*-
"""Noticias de mercado GRATUITAS: RSS publico do Google News + news.dat local.

REFINE 23/11/2026 - extraido da biblioteca/terminal MT5 e do app Android
(MarketData.kt: fetchNoticias / fetchCalendario), ambos gratis e sem chave.

Nao negocia, nao decide, nao altera risco/lote/alvo/stop. E apenas contexto
que o operador e o EA podem ler. Fail-closed: sem rede e sem arquivo devolve
lista vazia com motivo, nunca manchete inventada.
"""
from __future__ import annotations

import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

TERMINAL = Path(
    os.environ.get(
        "XAU_TERMINAL_PATH",
        r"C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal"
        r"\D0E8209F77C8CF37AD8BF550E51FF075",
    )
)
RSS = (
    "https://news.google.com/rss/search?"
    "q=mercado+financeiro+OR+ouro+OR+bitcoin+OR+forex+OR+dolar"
    "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)
_cache: tuple[float, list[dict[str, Any]], str] | None = None
TTL = 900          # 15 min, igual ao gateway / refresh
MAX = 12


def _rss() -> tuple[list[dict[str, Any]], str]:
    req = urllib.request.Request(RSS, headers={"User-Agent": "XAU_AI_PRO/1.2"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    itens: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        titulo = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        fonte = (item.findtext("source") or "").strip()
        if not titulo:
            continue
        if " - " in titulo and not fonte:
            titulo, fonte = titulo.rsplit(" - ", 1)
        itens.append({"title": titulo, "source": fonte, "link": link, "pubDate": pub})
        if len(itens) >= MAX:
            break
    return itens, "Google News RSS (publico, sem chave)"


def _news_dat() -> tuple[list[dict[str, Any]], str]:
    """Le manchetes do news.dat (UTF-16LE). Formato MetaQuotes: texto corrido
    com cabecalho; extrai linhas com comprimento minimo e removes duplicatas."""
    pasta = TERMINAL / "bases"
    candidatos = sorted(
        pasta.glob("*/news/news.dat"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    for p in candidatos[:3]:
        try:
            if p.stat().st_size < 1000:
                continue
            txt = p.read_bytes().decode("utf-16-le", errors="ignore")
            partes = re.split(r"[\r\n\x00]+", txt)
            vistos: set[str] = set()
            itens: list[dict[str, Any]] = []
            for parte in partes:
                s = parte.strip()
                if len(s) < 40 or len(s) > 300:
                    continue
                if s in vistos:
                    continue
                if not any(c.isalpha() for c in s):
                    continue
                vistos.add(s)
                itens.append({
                    "title": s,
                    "source": f"MT5 news.dat ({p.parent.parent.name})",
                    "link": "",
                    "pubDate": "",
                })
                if len(itens) >= MAX:
                    break
            if itens:
                return itens, f"MT5 local: {p.name} ({p.stat().st_size} bytes)"
        except Exception:
            continue
    return [], "sem news.dat com manchetes"


def noticias(force: bool = False) -> dict[str, Any]:
    global _cache
    agora = time.time()
    if _cache and not force and (agora - _cache[0]) < TTL:
        itens, fonte = _cache[1], _cache[2]
    else:
        try:
            itens, fonte = _rss()
        except Exception:
            itens, fonte = _news_dat()
        _cache = (agora, itens, fonte)
    return {
        "ok": True,
        "count": len(itens),
        "source": fonte,
        "items": itens,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
