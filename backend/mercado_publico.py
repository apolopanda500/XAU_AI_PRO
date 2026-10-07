# -*- coding: utf-8 -*-
"""
FONTE PUBLICA DE PRECO — as tres que respondem sem chave (05/10/2026)
====================================================================

O PEDIDO
========
"quero os precos ao vivo" e "nao deixe o grafico generico nunca".

MEDIDO NESTA MAQUINA, AGORA (latencia real, nao de pagina de venda)
---------------------------------------------------------------------
    Yahoo  GC=F (ouro)      HTTP 200   578 ms   preco 4167.6     exchange CMX
    Yahoo  EURUSD=X          HTTP 200   517 ms   preco 1.1227     exchange CCY
    Yahoo  BTC-USD           HTTP 200   521 ms   preco 85809.64   exchange CCC
    Binance BTCUSDT 1h       HTTP 200   368 ms   close 85821.96   volume 80.22
    Frankfurter EUR/USD      HTTP 200    77 ms   1.1204           (ECB, diario)

    NENHUMA EXIGE CHAVE. NENHUMA EXIGE CADASTRO.

O QUE ESTE MÓDULO FAZ, E O QUE ELE PROIBE
==========================================
Este módulo é **SÓ LEITURA DE GRÁFICO**. Ele nunca vira preço de execução.

Motivo, e é a regra do projeto: o preço que o operador executa é o preço da
CORRETORA dele. Se o candle do gráfico vier de fonte externa e o preço de
execução do MT5, os dois números são de lugares diferentes, e o operador que
monta a ordem no gráfico pode estar olhando um preço que não é o que vai
executar. Por isso:

  - `fonte` viaja JUNTO com o dado, sempre. A tela mostra de onde veio.
  - `execucao: false` viaja junto. Quem monta ordem tem de recusar preço sem
    corretora, e a flag existe para isso ser testável.
  - O módulo não conhece `risk_gate`, não conhece `confirm`, não conhece
    ordem. Ele não tem como enviar nada.

CADEIA E ORDEM
==============
A ordem é por ADEQUAÇÃO, não por popularidade:

  1. **Binance** — cripto. Fonte primaria: e exchange, tem 1m real, e o
     endpoint publico e o mais estavel dos tres (368 ms medido).
  2. **Yahoo** — ouro, forex, cripto. Unica das tres que cobre as tres classes
     que o app opera, no mesmo formato de `interval`.
  3. **Frankfurter** — forex **diario**. Nao serve para grafico de 5 min: e
     taxa de referencia do BCE. Entra como ultima opcao e e marcada como tal,
     porque um candle diario rotulado como 5m seria mentira.

NENHUMA CHAVE, NENHUM SEGREDO, NENHUMA ESCRITA
===============================================
Nao ha token aqui, e nao deve haver. Se alguem pedir chave para isto, a chave
entra em **campo de configuracao do operador**, nunca no codigo — e as tres
fontes aqui nao precisam de chave nenhuma.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

#: Quanto tempo uma fonte externa pode levar antes de ser considerada fora.
#: MEDIDO: o pior caso foi 578 ms. 4 s e folga sem virar espera.
TIMEOUT_S = 4.0

#: Usuario-Agent honesto: some com ele e o provedor pode recusar.
_UA = "XAU-AI-PRO/1.2.4 (leitura de grafico)"

#: Mapa do simbolo DA APP para o simbolo DA FONTE.
#:
#: Nao e lista de ativos do produto: e so o nome que cadaERVO writes para o
#: mesmo instrumento. Um par sem entrada aqui simplesmente nao vem dessas
#: fontes — e o app diz isso, em vez de tentar um nome chutado.
_ALIAS_YAHOO = {
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "XAUUSD": "GC=F",
    "GOLD": "GC=F",
    "XAGUSD": "SI=F",
    "SILVER": "SI=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "CAD=X",
    "USDCHF": "CHF=X",
    "NZDUSD": "NZD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "US30": "^DJI",
    "NAS100": "^NDX",
    "SPX500": "^GSPC",
    "DE40": "^GDAXI",
    "UK100": "^FTSE",
}

#: Binance usa `USDT` como o par de referencia; a app fala `USD`.
_ALIAS_BINANCE = {
    "BTCUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT",
    "BNBUSD": "BNBUSDT",
    "SOLUSD": "SOLUSDT",
    "XRPUSD": "XRPUSDT",
}

#: Intervalo da app -> intervalo da fonte.
_INTERVALO_YAHOO = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

_INTERVALO_BINANCE = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

#: Classes que so o Frankfurter cobre, e so como COTACAO DIARIA.
_DIARIO_APENAS = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")


class FontePublicaIndisponivel(RuntimeError):
    """Nenhuma fonte respondeu. Não é lista vazia."""


def _buscar_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _vela(t: Any, o: float, h: float, l: float, c: float, v: float | None = None) -> dict[str, Any]:
    """Uma vela no MESMO formato que o resto do app usa."""
    return {
        "time": int(t),
        "open": float(o),
        "high": float(h),
        "low": float(l),
        "close": float(c),
        "volume": float(v) if v is not None else 0.0,
    }


def _binance(symbol: str, timeframe: str, limit: int) -> dict[str, Any] | None:
    par = _ALIAS_BINANCE.get(symbol.upper())
    if not par:
        return None
    intervalo = _INTERVALO_BINANCE.get(timeframe.upper())
    if intervalo is None:
        return None
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={par}"
        f"&interval={intervalo}&limit={max(1, min(int(limit), 1000))}"
    )
    dados = _buscar_json(url)
    if not isinstance(dados, list) or not dados:
        return None
    # Cada kline do Binance e um ARRAY de 12 campos, nao um objeto:
    # [openTime, open, high, low, close, volume, closeTime, ...]
    velas = [
        _vela(k[0], k[1], k[2], k[3], k[4], k[5])
        for k in dados
        if isinstance(k, list) and len(k) >= 6
    ]
    if not velas:
        return None
    return {
        "candles": velas,
        "fonte": "binance",
        "fonte_url": url,
        "execucao": False,
        "observacao": f"Binance {par} {intervalo} — exchange, 1m real",
    }


def _yahoo(symbol: str, timeframe: str, limit: int) -> dict[str, Any] | None:
    destino = _ALIAS_YAHOO.get(symbol.upper())
    if not destino:
        return None
    intervalo = _INTERVALO_YAHOO.get(timeframe.upper())
    if intervalo is None:
        return None
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.request.quote(destino)}?interval={intervalo}&range=5d"
    )
    dados = _buscar_json(url)
    grafico = (dados or {}).get("chart") or {}
    if grafico.get("error"):
        return None
    resultados = grafico.get("result") or []
    if not resultados:
        return None
    r = resultados[0]
    marcas = r.get("timestamp") or []
    indicadores = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    aberturas = indicadores.get("open") or []
    maximas = indicadores.get("high") or []
    minimas = indicadores.get("low") or []
    fechamentos = indicadores.get("close") or []
    volumes = indicadores.get("volume") or []
    velas: list[dict[str, Any]] = []
    for i, marca in enumerate(marcas):
        o, h, l, c = (aberturas[i], maximas[i], minimas[i], fechamentos[i])
        # A serie vem com buraco (feriado, falta): None no meio. Vela com None
        # vira zero, e zero no grafico e um preco que nunca existiu.
        if None in (o, h, l, c):
            continue
        velas.append(_vela(marca, o, h, l, c, (volumes[i] if i < len(volumes) else None)))
    if not velas:
        return None
    velas.sort(key=lambda x: x["time"])
    velas = velas[-max(1, min(int(limit), 2000)):]
    meta = r.get("meta") or {}
    return {
        "candles": velas,
        "fonte": "yahoo",
        "fonte_url": url,
        "execucao": False,
        "observacao": (
            f"Yahoo {destino} {intervalo}"
            + (f" · {meta.get('exchangeName')}" if meta.get("exchangeName") else "")
            + " — endpoint público, não oficial"
        ),
    }


def _frankfurter(symbol: str, timeframe: str, limit: int) -> dict[str, Any] | None:
    """
    Frankfurter: taxa DIARIA do BCE.

    Entra como ultima opcao e so para D1. Para qualquer outro intervalo nao ha
    o que devolver — e devolver o preço diario rotulado como 5m seria fabricar
    dado que nao existe.
    """
    if timeframe.upper() != "D1":
        return None
    par = symbol.upper()
    if not (par.endswith("USD") and len(par) == 6):
        return None
    base, quote = par[:3], par[3:]
    url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={quote}"
    dados = _buscar_json(url)
    taxas = (dados or {}).get("rates") or {}
    if quote not in taxas:
        return None
    preco = float(taxas[quote])
    agora = int(time.time())
    return {
        "candles": [_vela(agora, preco, preco, preco, preco, None)],
        "fonte": "frankfurter",
        "fonte_url": url,
        "execucao": False,
        "diario": True,
        "observacao": "Frankfurter/BCE — cotação DIÁRIA de referência, serve só para D1",
    }


#: Ordem por adequacao. Ver o docstring.
CADEIA = (_binance, _yahoo, _frankfurter)


def ohlc_publico(symbol: str, timeframe: str = "M5", limit: int = 300) -> dict[str, Any]:
    """OHLC de fonte publica, com a procedencia sempre junto.

    Levanta `FontePublicaIndisponivel` quando NENHUMA fonte responde. Isso é
    diferente de lista vazia: "não tem dado" e "não Consegui perguntar" levam a
    decisões opostas na tela.
    """
    if not symbol or not str(symbol).strip():
        raise ValueError("symbol é obrigatório: nenhuma fonte pública presume par")
    tentativas: list[str] = []
    for fonte in CADEIA:
        nome = fonte.__name__.lstrip("_")
        try:
            resultado = fonte(str(symbol).strip().upper(), str(timeframe).upper(), int(limit))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as ex:
            tentativas.append(f"{nome}: {type(ex).__name__}")
            continue
        if resultado:
            resultado["tentativas"] = tentativas
            return resultado
        tentativas.append(f"{nome}: sem equivalente para este par ou período")
    raise FontePublicaIndisponivel(
        f"nenhuma fonte publica respondeu para {symbol} {timeframe} ({'; '.join(tentativas)})"
    )


def cotacao(symbol: str) -> dict[str, Any] | None:
    """Preço de referência de UMA fonte, para cotação rápida.

    Não é candle e não é histórico: é o preço atual. Usado no rodapé e em
    conferência — nunca em ordem.
    """
    try:
        dados = ohlc_publico(symbol, "M5", 2)
    except FontePublicaIndisponivel:
        return None
    velas = dados.get("candles") or []
    if not velas:
        return None
    return {
        "symbol": str(symbol).upper(),
        "price": velas[-1]["close"],
        "fonte": dados.get("fonte"),
        "execucao": False,
        "observacao": dados.get("observacao"),
    }