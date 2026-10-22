# -*- coding: utf-8 -*-
"""Dublô de `MetaTrader5` no estado de um terminal SEM sessão.

Não é conveniência: é a diferença entre simular o produto e simular um bug.
Um `ModuleType("MetaTrader5")` vazio faz `backend/asset_registry.py:177`
levantar `AttributeError: module 'MetaTrader5' has no attribute 'symbols_get'`,
que o handler genérico devolve como **500** — medido no CI de 22/10/2026, onde
duas baterias falhavam nesse ponto. O estado real de um terminal sem
`initialize()` é devolver `None`, e é esse estado que o código já trata
(`if symbols is None: return rows`).

Compartilhado por todas as baterias para que o mesmo dublô valha em qualquer
arquivo de teste: três dublôs diferentes são três produtos diferentes.
"""
from __future__ import annotations

from types import ModuleType

#: Atributos que o terminal real expõe e que o backend chama.
CHAMADAS_QUE_DEVOLVEM_NONE = (
    "shutdown", "account_info", "terminal_info", "symbols_get", "symbol_info",
    "symbol_info_tick", "copy_rates_from_pos", "copy_rates_range",
    "history_deals_get", "history_orders_get", "positions_get", "orders_get",
    "order_send", "order_check", "market_book_get", "version",
)

#: Atributos que no terminal real devolvem `False` (fracassou / não conectou).
CHAMADAS_QUE_DEVOLVEM_FALSE = ("initialize", "login", "symbol_select")


def terminal_desconectado() -> ModuleType:
    terminal = ModuleType("MetaTrader5")

    def _none(*_args, **_kwargs):
        return None

    def _false(*_args, **_kwargs):
        return False

    for nome in CHAMADAS_QUE_DEVOLVEM_NONE:
        setattr(terminal, nome, _none)
    for nome in CHAMADAS_QUE_DEVOLVEM_FALSE:
        setattr(terminal, nome, _false)
    return terminal
