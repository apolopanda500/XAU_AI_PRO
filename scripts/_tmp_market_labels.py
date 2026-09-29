# -*- coding: utf-8 -*-
"""Ajusta os rotulos da aba Mercado para o app desbloqueado.

A aba continua sendo leitura (nenhum botao de ordem mora aqui), mas o texto
nao pode mais sugerir que o app inteiro e somente-leitura: a ordem sai em
Robo -> Mesa. Script de uso unico, apagado logo em seguida.
"""
from __future__ import annotations

import pathlib

ARQUIVO = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "tabs" / "MarketTab.tsx"

SUBSTITUICOES = [
    ("em tempo real, sem execu\u00e7\u00e3o.",
     "em tempo real. A ordem sai em Rob\u00f4 \u2192 Mesa."),
    ("<strong>Somente leitura</strong>",
     "<strong>Esta aba \u00e9 leitura</strong>"),
    ("Nenhuma a\u00e7\u00e3o de trading est\u00e1 dispon\u00edvel nesta aba.",
     "A ordem sai em Rob\u00f4 \u2192 Mesa, nas corretoras MT5, MEXC, Binance, Bybit e OKX."),
    ("{selectedStale ? 'Leitura vencida' : 'Somente leitura'}",
     "{selectedStale ? 'Leitura vencida' : 'Leitura do mercado'}"),
    ("{visibleDepth ? 'somente leitura' : 'indispon\u00edvel'}",
     "{visibleDepth ? 'leitura' : 'indispon\u00edvel'}"),
    ("{visibleTrades ? 'somente leitura' : 'indispon\u00edvel'}",
     "{visibleTrades ? 'leitura' : 'indispon\u00edvel'}"),
]


def main() -> int:
    texto = ARQUIVO.read_text(encoding="utf-8")
    for antigo, novo in SUBSTITUICOES:
        if antigo not in texto:
            print(f"FALTA: {antigo[:60]!r}")
            return 1
        if novo in texto:
            print(f"ja estava: {novo[:60]!r}")
            continue
        texto = texto.replace(antigo, novo)
        print(f"ok: {antigo[:60]!r}")
    ARQUIVO.write_text(texto, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
