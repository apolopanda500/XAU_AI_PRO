# -*- coding: utf-8 -*-
"""Simbolo canonico para todas as corretoras e todos os formatos.

POR QUE UMA FONTE SO
=====================
O mesmo ativo chega em cada corretora com uma roupagem diferente:

- MT5/XM: `EURUSD`, `BTCUSD`, `XAUUSD`, com sufixos da corretora
  (`XAUUSD.pro`, `EURUSD_M`, `EURUSDc`) e contratos fracionarios (`MICRO`)
- MEXC/Binance/Bybit: concatenado contra USDT (`BTCUSDT`, `ETHUSDT`)
- OKX: com hifen (`BTC-USDT`)
- Futuros linear: mesmo par, categoria a parte (`BTCUSDT` linear)
- Operador digitando: `BTC/USD`, `btc usdt`, `XAU-USD`

Antes cada modulo normalizava do seu jeito (`app/market_symbols`,
`backend/exchange_symbols`, `backend/ai_inference`): tres lugares onde
"o mesmo ativo" significava tres coisas diferentes. Este modulo e o
vocabulario unico. Os outros delegam — nao duplicam.

REGRA DO DONO
=============
Nenhum nome de ativo no codigo. So sufixo de quote (`USDT`, `USD`, ...),
sufixo de corretora (`.PRO`, `_M`, `MICRO`, ...) e separador. `BTC` nunca
vira outro ativo por estar numa lista: a comparacao e pela base extraida,
nao por catalogo.
"""
from __future__ import annotations

#: Sufixos de quote, do mais longo ao mais curto. A ordem importa: em
#: `BTCUSDT` o `USDT` precisa casar antes do `T`/`DT` inexistente — e em
#: `BTCUSD` o `USD` e o quote do terminal (vira USDT na exchange).
QUOTES: tuple[str, ...] = tuple(sorted(
    {"USDT", "USDC", "USD", "EUR", "BTC", "ETH", "BUSD", "FDUSD", "TUSD",
     "JPY", "GBP", "AUD", "NZD", "CAD", "CHF"},
    key=len, reverse=True,
))

#: Sufixos que a corretora pendura no par e que nao mudam o ativo para
#: leitura (`XAUUSD.pro` continua ouro). `MICRO`/`MINI` mudam o CONTRATO,
#: nao o nome: a base extraida e a mesma, e quem decide se opera o contrato
#: fracionario e o catalogo da corretora, nao este modulo.
#:
#: `.M`/`.C` entram porque a XM Global usa essa grafia nos pares de forex
#: (`EURUSD.m`, `GBPUSD.c`) e em metais (`XAUUSD.m`). Sem eles, o `canonico`
#: devolvia `EURUSD.` — com o ponto grudado no nome — e o par nao casava com
#: nenhum modelo do catalogo: a tela nao encontrava artefato para um ativo que
#: existe. Medido em 04/10/2026.
SUFIXOS_CORRETORA: tuple[str, ...] = (
    ".PRO", "_M", "_C", "MICRO", "MINI", ".M", ".C", ".ECN", ".RAW",
)

#: Separadores que o operador digita e as venues nao aceitam.
#:
#: O ponto NAO entra aqui de proposito: ele e parte do nome do contrato na XM
#: (`EURUSD.m`), e remove-lo antes de tirar o sufixo apagaria o proprio sufixo.
#:
#: O UNDERSCORE TAMBEM NAO ENTRA MAIS (medido em 04/10/2026). Ele separava
#: `XAU_USD` de `XAUUSD` na digitacao — util — mas tambem APAGAVA o
#: underscore dos nomes de classe: `MULTI_METALS` virava `MULTIMETALS`, que
#: nao existe em disco. Os tres modelos de maior edge do catalogo
#: (MULTI_METALS +0,2497) ficavam inacessiveis por causa de um caractere que
#: o operador nunca digitaria.
#:
#: A troca e QUASE DEZRADA, com uma excecao que o teste mede: `BTC_USDT`
#: continua virando `BTCUSDT`. O `canonico` remove o underscore SO ENTRE
#: LETRAS, quando ele separa as duas metades do par; o `_` de `MULTI_METALS`
#: fica porque o prefixo `MULTI_` e um marcador de nome de classe, nao um
#: separador de par. Ver `_e_separador_de_par`.
SEPARADORES: str = "/- "

#: Prefixos que indicam CLASSE DE ATIVO, e nao par. O underscore depois deles
#: faz parte do nome e nunca e separador.
PREFIXOS_DE_CLASSE: tuple[str, ...] = ("MULTI_",)


def _e_separador_de_par(s: str) -> bool:
    """O underscore em `s` separa as metades de um par, ou faz parte do nome?

    `BTC_USDT` -> sim, e o par `BTCUSDT`. `MULTI_METALS` -> nao: `MULTI_` e
    marcador de classe de ativo, e o nome em disco tem o underscore.

    Sem esta distincao, uma das duas grafias funciona e a outra nao — e o
    operador descobre qual so quando o modelo nao carrega.
    """
    for prefixo in PREFIXOS_DE_CLASSE:
        if s.startswith(prefixo):
            return False
    return "_" in s

#: Marcador de contrato perpetuo em algumas venues.
SUFIXO_PERP: str = "_PERP"


def canonico(symbol: str) -> str:
    """Forma canonica: maiuscula, sem separador, sem sufixo de corretora.

    `btc/usdt` -> `BTCUSDT`. `XAUUSD.pro` -> `XAUUSD`. Vazio -> vazio
    (recusa com motivo no chamador, nunca ativo presumido).
    """
    s = str(symbol or "").strip().upper()
    # Sufixos ANTES dos separadores: `_M` precisa casar com `_` ainda
    # presente (`EURUSD_M` -> `EURUSD`). Tirar o separador primeiro colaria
    # o `M` no par (`EURUSDM`) e o sufixo nunca mais casaria.
    if s.endswith(SUFIXO_PERP):
        s = s[: -len(SUFIXO_PERP)]
    for sufixo in SUFIXOS_CORRETORA:
        if s.endswith(sufixo) and len(s) > len(sufixo):
            s = s[: -len(sufixo)]
            break
    # Sufixo de 1 letra da corretora (`EURUSDc`, `XAUUSDm`): so quando sobra
    # par valido (mais de 6). `BTC` (3) nunca e tocado — cortar ali seria
    # fabricar outro ativo a partir do nome certo.
    if len(s) > 6 and s[-1:] in ("C", "M"):
        s = s[:-1]
    for sep in SEPARADORES:
        s = s.replace(sep, "")
    # O underscore entre letras separa as metades do par (`BTC_USDT`), e some.
    # O underscore de nome de CLASSE fica (`MULTI_METALS`). Ver
    # `_e_separador_de_par`.
    if _e_separador_de_par(s):
        s = s.replace("_", "")
    return s


def base(symbol: str) -> str:
    """Ativo base sem o quote: `BTCUSDT` -> `BTC`, `EURUSD` -> `EUR`."""
    s = canonico(symbol)
    for quote in QUOTES:
        if len(s) > len(quote) and s.endswith(quote):
            return s[: -len(quote)]
    return s


def quote(symbol: str) -> str:
    """Quote do par: `BTCUSDT` -> `USDT`. Vazio quando nao ha quote conhecido."""
    s = canonico(symbol)
    for q in QUOTES:
        if len(s) > len(q) and s.endswith(q):
            return q
    return ""


def mesmo_ativo(a: str, b: str) -> bool:
    """Mesmo ativo em venues diferentes (`BTCUSDT` == `BTCUSD`).

    Compara pela base extraida. `BTCUSDT` e `EURUSD` nunca sao iguais;
    vazio nunca e igual a nada.
    """
    sa, sb = canonico(a), canonico(b)
    if not sa or not sb or sa == sb:
        return sa == sb and bool(sa)
    ba, bb = base(a), base(b)
    return bool(ba) and ba == bb


def formas(symbol: str) -> list[str]:
    """Formas do mesmo ativo onde pode haver artefato ou par negociavel.

    Ordem: o canonico primeiro (um `BTCUSDT_H1.pkl` treinado na exchange
    vence o alias); depois as formas no quote do terminal e da exchange.
    Sem duplicar e sem inventar quote de forex.
    """
    s = canonico(symbol)
    if not s:
        return []
    b = base(symbol)
    candidatos = [s]
    for forma in (f"{b}USD", f"{b}USDT", f"{b}USDC"):
        if len(forma) > 3 and forma != s and forma not in candidatos:
            candidatos.append(forma)
    return candidatos
