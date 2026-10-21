# -*- coding: utf-8 -*-
"""Alias modelo -> simbolo da corretora, por configuracao do operador.

POR QUE EXISTE (medido em 04/10/2026)
=====================================
Na XM STANDARD o ouro spot chama `GOLD`; o modelo foi treinado como
`XAUUSD`. Sem alias, o motor pede `XAUUSD` a XM e recebe "simbolo
inexistente" — ou pior, alguem mapeia no codigo e o proximo broker com
nome diferente quebra de novo.

POR QUE CONFIG, E NAO CODIGO
=============================
A regra do dono proibe nomes de ativos no codigo. Este modulo nao tem
nenhum: ele LE o mapa que o operador gravou
(`symbol_aliases.json` ao lado do config) e aplica. Sem mapa, o simbolo
passa intacto — nenhuma presuncao.

Formato do arquivo (tudo maiusculo, por corretora):
    {"mt5": {"XAUUSD": "GOLD"}, "mexc": {}}
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def caminho_arquivo() -> Path:
    base = os.getenv("XAU_APP_CONFIG", "")
    if base:
        return Path(base).parent / "symbol_aliases.json"
    return Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "symbol_aliases.json"


def carregar() -> dict[str, dict[str, str]]:
    try:
        dados = json.loads(caminho_arquivo().read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(dados, dict):
        return {}
    mapa: dict[str, dict[str, str]] = {}
    for corretora, pares in dados.items():
        if not isinstance(pares, dict):
            continue
        mapa[str(corretora).strip().lower()] = {
            str(modelo).strip().upper(): str(real).strip().upper()
            for modelo, real in pares.items()
            if str(modelo).strip() and str(real).strip()
        }
    return mapa


def gravar(mapa: dict[str, dict[str, str]]) -> Path:
    destino = caminho_arquivo()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(mapa, indent=2, sort_keys=True), encoding="utf-8")
    return destino


def para_corretora(broker: str, symbol: str, mapa: dict[str, Any] | None = None) -> str:
    """Simbolo do modelo -> simbolo que a corretora entende."""
    pedido = str(symbol or "").strip().upper()
    if not pedido:
        return ""
    tabela = (mapa if mapa is not None else carregar()).get(str(broker or "").strip().lower(), {})
    return str(tabela.get(pedido, pedido)).upper()


def para_modelo(broker: str, symbol: str, mapa: dict[str, Any] | None = None) -> str:
    """Simbolo da corretora -> simbolo do modelo (reverso do alias)."""
    real = str(symbol or "").strip().upper()
    if not real:
        return ""
    tabela = (mapa if mapa is not None else carregar()).get(str(broker or "").strip().lower(), {})
    for modelo, destino in tabela.items():
        if str(destino).upper() == real:
            return str(modelo).upper()
    return real
