# -*- coding: utf-8 -*-
"""Serializa o acesso a API nativa do MetaTrader5.

A extensao MetaTrader5 (IPC com o terminal64) NAO e thread-safe: chamadas
simultaneas de threads diferentes (MarketData, MT5Robot, graficos, busca)
podem travar em deadlock na camada IPC e congelar o app.

Regras do app:
1. TODA chamada nativa (initialize, symbol_info, copy_rates, order_send...)
   deve rodar dentro de `with mt5_lock:`.
2. NUNCA chame mt5.shutdown() em workers de fundo: a conexao IPC e
   compartilhada por todo o processo e o shutdown a derruba para todos.
"""
from __future__ import annotations

import threading

# RLock: reentrante para a mesma thread (metodos que chamam metodos).
mt5_lock = threading.RLock()
