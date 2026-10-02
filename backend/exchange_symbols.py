# -*- coding: utf-8 -*-
"""Normalizacao de par para as exchanges cripto.

POR QUE ESTE MODULO EXISTE (2026-10-02)
========================================
O dono reportou: *"os ativos sao negociados em USDT"* e *"o robo e os
modelos nao conseguem operar em outras corretoras"*.

Medido: `BTC/USD`, `BTC-USDT`, `XAUUSD` e `BTCUSDT` iam todos para a
exchange **como o operador digitou**. Cada uma delas:

- `BTCUSDT` — funciona
- `BTC/USD`  — **HTTP 400** (separador nao existe no campo `symbol`)
- `XAUUSD`   — **HTTP 400** (spot cripto nao tem par em USD)
- `EURUSD`   — **HTTP 400** (forex nao existe na exchange)

A tabela oficial do endpoint de ordem da MEXC usa `BTCUSDT` e `MXUSDT` como
exemplos: **em cripto o par e sempre contra um quote conhecido**, concatenado
sem separador.

A REGRA, E POR QUE ELA E DECLARATIVA
====================================
Nao ha lista de pares. A regra e: **tirar os separadores, reconhecer o quote
no fim, e recusar o que nao for par de cripto.**

| Entrada | Saida | Por que |
|---|---|---|
| `BTCUSDT` | `BTCUSDT` | ja no formato |
| `BTC/USD` | `BTCUSDT` | separador removido |
| `BTC-USDT` | `BTCUSDT` | separador removido |
| `BTCUSD` | `BTCUSDT` | sufixo `USD` e o quote do par MT5/forex |
| `XAUUSDT` | `XAUUSDT` | spot de metais existe (XAUUSDT, XAGUSDT) |
| `ETHBTC` | `ETHBTC` | quote em BTC e valido nas exchanges |
| `EURUSD` | **recusa** | forex nao opera em exchange cripto |
| `EURUSDT` | **recusa** | `EURUSDT` nao existe na exchange |

A ultima linha importa tanto quanto a primeira: sem ela, `EURUSD` viraria
`EURUSDT` e o sistema enviaria um par inventado. **Recusar com motivo e
melhor que enviar lixo** — e a exchange rejeitaria do mesmo jeito, so sem
nosso explicar por que.

TAMBEM PRESERVA A REGRA DO PROJETO
==================================
Nenhum par fixo e assumido. `BtcUsdt` funciona (vira caixa alta) e um simbolo
vazio recusa — nunca vira BTC.
"""
from __future__ import annotations

#: Quotes aceitos em spot pelas exchanges cripto.
#:
#: A ORDEM IMPORTA: `USDT` PRECISA SER TESTADO ANTES DE `USD`
#: ==============================================================
#: O casamento e por sufixo. Em `BTCUSD` o sufixo `USD` casa primeiro e o
#: resultado seria `BTCUSDT` com o `USDT` colado duas vezes. Por isso a lista
#: e ordenada do mais LONGO para o mais curto. Nao e estetica: e a condicao
#: para a regra funcionar.
QUOTES_ORDENADOS: tuple[str, ...] = tuple(
    sorted(
        {"USDT", "USDC", "USD", "BTC", "ETH", "EUR", "FDUSD", "TUSD"},
        key=len, reverse=True,
    )
)

#: Quote do par MT5/forex que, trazido para exchange cripto, vira USDT.
#:
#: O operador ve `BTCUSD` porque é assim que o par aparece no terminal e nos
#: modelos. Em exchange cripto esse par **nao existe**: o quote e USDT. Sem
#: esta conversao, `BTCUSD` passaria adiante e a MEXC responderia HTTP 400.
#: Este e o pedido literal do dono: *"os ativos sao negociados em USDT"*.
QUOTE_DE_FX_PARA_CRIPTO: str = "USDT"

#: Separadores aceitos na entrada. A entrada do operador vem de tela, de
#: arquivo e de sinal do broker — nao ha garantia de formato unico.
SEPARADORES: str = "/-_ "

#: Quotes que so existem em forex/CFD e NUNCA devem virar par de exchange.
#: `EURUSDT` e `GBPUSDT` nao existem em exchange cripto; produzi-los seria
#: fabricar um par. `JPY` entra aqui porque `USDJPY` precisa ser reconhecido
#: como forex para RECUSAR — sem isso ele nem casa em `QUOTES_ORDENADOS` e a
#: recusa sairia com o motivo errado ("quote desconhecido").
QUOTES_DE_FX: frozenset[str] = frozenset({
    "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "SEK", "NOK", "MXN", "ZAR", "TRY",
})


class ParInvalido(ValueError):
    """Par que nao pode virar um par de exchange cripto.

    Herda de `ValueError` de proposito: o resto do codigo ja trata
    `ValueError` como recusa de entrada (ver `_universal_run`, que mapeia
    `ValueError` para resposta `rejected`). Uma excecao nova aqui exigiria
    mudar os tratadores, e o ganho seria so de nome.
    """


def normalizar_par(symbol: str, *, contexto: str = "exchange") -> str:
    """Devolve o par concatenado no formato da exchange, ou recusa.

    `contexto` entra na mensagem de recusa para dizer qual exchange recusou:
    sem isso o operador ve o mesmo texto para quatro corretoras diferentes e
    nao sabe onde corrigir.
    """
    bruto = str(symbol or "").strip().upper()
    for separador in SEPARADORES:
        bruto = bruto.replace(separador, "")
    if not bruto:
        raise ParInvalido(f"par obrigatorio para {contexto}")

    for quote in QUOTES_ORDENADOS:
        if bruto.endswith(quote) and len(bruto) > len(quote):
            base = bruto[: -len(quote)]
            if not base:
                raise ParInvalido(f"par invalido para {contexto}: {bruto!r} sem ativo base")
            if base in QUOTES_DE_FX:
                raise ParInvalido(
                    f"{bruto!r} nao e par de {contexto}: {base} e moeda de forex/CFD e "
                    f"nao existe em exchange cripto. Forex opera no gateway MT5, nao aqui."
                )
            # `BTCUSD` e como o par aparece no terminal e nos modelos, mas em
            # exchange cripto o quote e USDT. Sem isto a MEXC responde HTTP 400.
            final = QUOTE_DE_FX_PARA_CRIPTO if quote == "USD" else quote
            return f"{base}{final}"

    # Um par de forex e reconhecido pelos DOIS lados: base em fiat
    # (`EURUSD`) ou quote em fiat (`USDJPY`, `EURJPY`). Checar so a base
    # deixaria `USDJPY` passar como se fosse cripto, e `USDEUR` virar um par
    # que ninguem pediu. A base em fiat e o caso comum; o quote em fiat e o
    # que fecha o buraco.
    if any(bruto.endswith(fx) and len(bruto) > len(fx) for fx in QUOTES_DE_FX):
        raise ParInvalido(
            f"{bruto!r} nao e par de {contexto}: e um par de forex/CFD e nao existe "
            f"em exchange cripto. Forex opera no gateway MT5, nao aqui."
        )

    raise ParInvalido(
        f"par invalido para {contexto}: {bruto!r}. O quote precisa ser um de "
        f"{', '.join(QUOTES_ORDENADOS)} — em cripto o par e sempre contra USDT ou equivalente."
    )


def par_exchange(symbol: str, contexto: str = "exchange") -> str:
    """Alias com nome curto, para o call-site dos clientes ficar legivel."""
    return normalizar_par(symbol, contexto=contexto)


def e_forex(symbol: str) -> bool:
    """True quando o par e de forex/CFD — nao opera em exchange cripto.

   Forex e reconhecido pela BASE sendo uma moeda de fiat e o QUOTE sendo
    USD ou uma moeda do proprio grupo. `BTCUSDT` e cripto (base `BTC`, quote
    `USDT`); `USDJPY` e forex; `EURUSDT` e forex mesmo tendo `USDT` no fim —
    porque o que decide e a BASE, nao o quote.
    """
    bruto = str(symbol or "").strip().upper()
    for separador in SEPARADORES:
        bruto = bruto.replace(separador, "")

    # Casa o quote mais longo primeiro, pelo mesmo motivo de
    # `QUOTES_ORDENADOS`: em `BTCUSD` o `USD` curto casaria antes.
    for quote in QUOTES_ORDENADOS:
        if bruto.endswith(quote) and len(bruto) > len(quote):
            base = bruto[: -len(quote)]
            if base in QUOTES_DE_FX:
                return True
            break
    # Quote de forex que nao esta em `QUOTES_ORDENADOS`: `USDJPY`, `EURJPY`.
    # Sem esta checagem `USDJPY` cairia no `return False` e seria classificado
    # como cripto — que e o oposto do que ele e.
    for fx in QUOTES_DE_FX:
        if bruto.endswith(fx) and len(bruto) > len(fx):
            return True
    return False