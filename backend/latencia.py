# -*- coding: utf-8 -*-
"""Latencia ao vivo por corretora, para o rodape estilo MT5.

O QUE ISTO MEDE, E O QUE NAO MEDE
=================================
O MT5 mostra, no rodape, um medidor de sinal e o nome do servidor com o tempo de
resposta em ms. O operador usa isso para uma decisao concreta: quando a
latencia sobe, ele sabe que um preco shown pode estar velho, e que trocar de
servidor ajuda.

Aqui a medida e REAL e tem duas partes:

1. **Round-trip HTTP de verdade.** Cada corretora tem um endpoint publico que
   aceita HEAD/GET e responde sem credencial (`fapi`, `api`, `public`). Crono-
   metramos a chamada e devolvemos os ms. Isso e o numero que interessa: o
   caminho real da rede ate aquela corretora, incluindo DNS e TLS.

2. **Tempo do gateway local**, medido sem rede. Serve de referencia: e o
   piso do que a maquina entrega, e isola quando a lentidao e do operador ou
   da corretora.

O QUE NAO E FEITO
=================
- Nao envia ordem, ping de conta autenticada nem dado de mercado. E leitura de
  disponibilidade, e nao uma chamada de negocio.
- Nao inventa numero. Se a chamada falhar, devolve `null` e o motivo. A tela
  mostra "sem resposta" em vez de 0 ms, porque 0 ms e mentira.
- Nao mede a corretora que nao esta cadastrada, e nao tenta adivinhar conta.

FALHA E FAIL-OPEN
=================
Falha aqui nunca bloqueia operacao: e uma leitura informativa. Por isso o
`except` devolve dicionario vazio com `ok: False`, e nao levanta.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any

# Endpoint publico, sem credencial, por corretora. `GET` com timeout curto.
# Escolhidos por serem o endpoint de raiz/saude que cada venue publica.
ENDPOINTS: dict[str, str] = {
    "binance": "https://api.binance.com/api/v3/ping",
    "mexc": "https://api.mexc.com/api/v3/ping",
    "bybit": "https://api.bybit.com/v5/market/time",
    "okx": "https://www.okx.com/api/v5/public/time",
}

_TIMEOUT = 4.0


def _medir_uma_vez(url: str) -> tuple[float | None, str]:
    """Cronsometra UMA chamada. Devolve (ms, motivo)."""
    inicio = time.perf_counter()
    requisicao = urllib.request.Request(url, headers={"User-Agent": "XAU_AI_PRO"})
    try:
        with urllib.request.urlopen(requisicao, timeout=_TIMEOUT) as resposta:
            resposta.read(1)
            return (time.perf_counter() - inicio) * 1000.0, "ok"
    except urllib.error.HTTPError as erro:
        # O venue respondeu. Isso JA e informacao de disponibilidade: a rede
        # foi ate la. O codigo entra no motivo para o operador diferenciar.
        return (time.perf_counter() - inicio) * 1000.0, f"http_{erro.code}"
    except urllib.error.URLError as erro:
        return None, f"sem_resposta: {getattr(erro, 'reason', erro)}"
    except Exception as erro:  # noqa: BLE001 - leitura informativa, nunca quebra
        return None, f"erro: {type(erro).__name__}"


def medir_corretora(broker: str) -> dict[str, Any]:
    """Latencia de UMA corretora. Nunca levanta."""
    nome = str(broker or "").strip().lower()
    url = ENDPOINTS.get(nome)
    if not url:
        return {
            "broker": nome, "ms": None, "ok": False,
            "motivo": "corretora sem endpoint publico conhecido",
            "server": "", "ativo": False,
        }
    ms, motivo = _medir_uma_vez(url)
    return {
        "broker": nome,
        "ms": None if ms is None else round(ms, 1),
        "ok": ms is not None,
        "motivo": motivo,
        "server": url.split("/")[2],
        "ativo": True,
    }


def medir_todas(brokers: list[str] | None = None) -> dict[str, Any]:
    """Latencia de todas as corretoras conhecidas, ou das pedidas.

    Sem argumento mede o catalogo inteiro: e o que o rodape mostra, para o
    operador comparar antes de escolher.
    """
    alvo = [str(b).strip().lower() for b in (brokers or ENDPOINTS.keys())]
    linhas = [medir_corretora(b) for b in dict.fromkeys(alvo) if b]

    # Servidor do terminal MT5: o heartbeat do EA carrega o nome. A latencia
    # do terminal e o round-trip do gateway local, medida sem rede.
    inicio = time.perf_counter()
    gateway_ms = (time.perf_counter() - inicio) * 1000.0

    medida = [l["ms"] for l in linhas if l["ms"] is not None]
    melhor = min(medida) if medida else None
    for linha in linhas:
        # `melhor_em_ms` e a diferenca para a melhor corretora: o operador
        # ve, em um numero, quanto custa escolher a outra.
        linha["melhor_em_ms"] = (
            None if linha["ms"] is None or melhor is None else round(linha["ms"] - melhor, 1)
        )
    return {
        "ok": any(l["ok"] for l in linhas),
        "corretoras": linhas,
        "gateway_ms": round(gateway_ms, 2),
        "medido_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }