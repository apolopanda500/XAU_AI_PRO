# -*- coding: utf-8 -*-
"""Classes de ativo e deteccao de simbolo valido.

A REGUA QUE O DONO FIXOU (2026-10-02)
====================================
> *"Modelos UNICOS serao separados por periodos; MULTI precisam operar todos os
> horarios"* — e, antes: *"reconstruir totalmente os modelos: FOREX, INDICE,
> CRYPTO, FIAT... separados, e tambem MULTI de cada um"*

Entao a taxonomia e por CLASSE, e dentro de cada classe existem dois tipos de
artefato:

| Tipo | O que e | Granularidade |
|---|---|---|
| **unitario** | um modelo por simbolo | um por timeframe |
| **MULTI** | um modelo que opera a classe inteira | **um so, com o timeframe como entrada** |

Por que o MULTI e um so: o log de treino de 28/09 mostra que o edge depende
do **horizonte**, nao do ativo. Todo M5 reprova e todo H4 publica, em todos
os ativos. Um modelo que recebe o timeframe como feature captura esse efeito;
separar por timeframe desperdicaria o dado sem ganhar nada.

POR QUE A CLASSIFICACAO IMPORTA
================================
`FEATURES` hoje comeca com preco ABSOLUTO (`Open`, `High`, `Low`, `Close`).
XAUUSD ~2000 e EURUSD ~1,08 sao escalas incomparaveis, e um unico modelo
treinado em ambos nao tem o que aprender. E por isso que o MULTI so faz
sentido com **features estacionarias** (`Close/ATR`, `Volume/Volume_MA`).
Ver `Python/ai/train_v2.py` e o plano em `docs/PLANO_MESTRE_20261002.md`.

O QUE ESTE MODULO FAZ
=====================
1. Detecta simbolo VALIDO. O dataset tem 193 nomes no campo `Symbol` e a
   maioria e **lixo**: `0.0`, `69`, `35.981`, `HF`, `2026.09.16 05:15`. Sao
   linhas corrompidas de escrita concorrente. Sem filtrar, o modelo aprende
   lixo — que e o que o `auditar_dataset.py` ja avisava.
2. Classifica o simbolo valido numa das classes pedidas.
3. Declara as classes que **nao tem dado**, para o plano nao prometer o que
   nao existe: INDICE tem zero linhas neste dataset.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------
# 1. Simbolo valido
# --------------------------------------------------------------------------

#: Simbolo de ativo: 3 a 12 letras, iniciado em letra. `0.0`, `69`, `35.981`
#: e `HF` nao passam. `2026.09.16 05:15` tambem nao (espaco e ponto).
PADRAO_SIMBOLO = re.compile(r"^[A-Z][A-Z0-9]{2,11}$")

#: Sufixos de derivativa/indice que aparecem em broker e nao sao ativo proprio
#: para treino. Ficam de fora em vez de entrar como ruido.
SUFIXOS_NAO_TREINAVEIS = ("#", "m", "c", ".a", "_i")

#: Prefixos de conta/indice/proxy do MT5.
PREFIXOS_NAO_TREINAVEIS = (
    "US500", "US30", "NAS100", "SPX500", "DE500", "UK100", "JP225",
    "GER30", "GER40", "FRA40", "ESP35", "AUS200", "HKG50", "CHI50",
)


def simbolo_valido(nome: str) -> bool:
    """True quando o campo `Symbol` e um ativo, e nao lixo de escrita."""
    bruto = str(nome or "").strip().upper()
    if not PADRAO_SIMBOLO.match(bruto):
        return False
    if bruto.endswith(SUFIXOS_NAO_TREINAVEIS):
        return False
    return True


# --------------------------------------------------------------------------
# 2. Classes de ativo
# --------------------------------------------------------------------------

#: Cripto observado no dataset. Os 5 tem 64.862 linhas M5 cada.
CRIPTO: frozenset[str] = frozenset({
    "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD",
})

#: Metais. XAGUSD tem so 946 linhas — entra, mas com volume muito menor que
#: o XAU (46.463). Ver `volume_por_simbolo()` antes de treinar.
METAIS: frozenset[str] = frozenset({"XAUUSD", "XAGUSD"})

#: Forex — o conjunto inteiro do dataset. Sao pares de moeda contra USD, que e
#: o que o dono chama de "FIAT": a moeda individualmente e fiat; o que se
#: treina e o par. Isso precisa ficar escrito porque "FIAT" ambiguo sugere
#: treinar a moeda isolada, e isso nao existe em dataset de cambio.
FIAT: frozenset[str] = frozenset({
    # majors
    "EURUSD", "GBPUSD", "USDJPY",
    # crosses
    "AUDUSD", "USDCAD", "NZDUSD", "USDCHF",
    # exoticos
    "USDSEK", "USDCNH", "USDBRL",
})

#: Classes para as quais **existe** dado neste dataset.
CLASSES_COM_DADO: tuple[str, ...] = ("CRYPTO", "FIAT", "METALS")

#: Classes pedidas que **nao tem** dado. Declarar aqui e melhor que descobrir
#: na hora do treino: o plano mostra o buraco antes de prometer o modelo.
CLASSES_SEM_DADO: tuple[str, ...] = ("INDICES",)


def classe_de(simbolo: str) -> str:
    """Classe do simbolo, ou `OUTROS` quando nao pertence a nenhuma.

    Nao adivinha: um par novo (EURPLN) cai em `OUTROS` e o chamador decide o
    que fazer. Classificar por palpite seria o mesmo defeito de assumir ativo.
    """
    bruto = str(simbolo or "").strip().upper()
    if bruto in CRIPTO:
        return "CRYPTO"
    if bruto in METAIS:
        return "METALS"
    if bruto in FIAT:
        return "FIAT"
    return "OUTROS"


def simbolos_da_classe(classe: str) -> list[str]:
    """Os simbolos conhecidos de uma classe, em ordem alfabetica."""
    mapa = {"CRYPTO": CRIPTO, "METALS": METAIS, "FIAT": FIAT}
    return sorted(mapa.get(str(classe).strip().upper(), frozenset()))


def nome_do_modelo_multi(classe: str) -> str:
    """Nome do artefato MULTI de uma classe.

    **Sem timeframe no nome**, e a diferenca em relacao ao unitario. O dono
    definiu que o MULTI opera todos os horarios, entao `MULTI_CRYPTO_H1` seria
    enganoso: existe um so artefato, e o timeframe entra como feature.
    """
    return f"MULTI_{str(classe).strip().upper()}"


def nome_do_modelo_unitario(simbolo: str, timeframe: str) -> str:
    """Nome do artefato unitario: `BTCUSDT_H1`."""
    return f"{str(simbolo).strip().upper()}_{str(timeframe).strip().upper()}"