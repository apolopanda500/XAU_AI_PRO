"""
SL E TP EM DINHEIRO — O MOTOR QUE MANTEM O VALOR (05/10/2026)
=============================================================

O QUE O DONO PEDIU
------------------
"antes abrir operacao configurar tp e sl ao vivo, mantendo seguindo o preco
ambos mantendo o valor pre determinado pelo usuario"

Isto e: o operador determina um VALOR em dinheiro, e o preco se move, e o nivel
acompanha o preco para que o dinheiro continue sendo o mesmo numero.

POR QUE AQUI, E NAO NA TELA
--------------------------
MEDIDO: o painel do ticket NAO sabe o lado da operacao — o proprio botao diz
"A direcao e do modelo" — e o preco que chega e um so (`price ?? last ?? bid ??
ask`), sem o lado.  Um nivel so exigiria inventar compra ou venda na tela.

O motor sabe os tres: o LADO (do modelo), o PRECO DE ENTRADA (da execucao) e o
VOLUME. E o lugar onde o valor pode ser recomputado enquanto a posicao vive,
que e o que "ao vivo" significa.

A CONTA
-------
    dinheiro = |entrada - nivel| * volume * contract_size
    nivel    = entrada +/- dinheiro / (volume * contract_size)

`contract_size` e o que separa crypto de forex: 1 em BTCUSD, 100.000 em EURUSD.
Sem ele, "lote" nao significa dinheiro, e o erro cresce com o preco — o defeito
medido na tela, onde `preco * volume * distancia` exagerava 85.865x.

SEM CONTRATO, NAO HA NIVEL
--------------------------
A corretora pode nao devolver `contract_size`. Aqui isso e `None`, e quem chama
recusa com motivo.  Numero de risco inventado e o pior defeito possivel numa
tela de operacao: o operador dimensiona a posicao por ele.
"""

from __future__ import annotations

from typing import Literal

Lado = Literal["buy", "sell"]
Papel = Literal["stop", "alvo"]

#: Motivo da recusa, para o gateway responder em vez de servir numero.
SEM_CONTRATO = "a corretora nao devolveu o tamanho do contrato deste ativo"
SEM_VOLUME = "volume invalido: nao ha conversao de dinheiro para preco"
VALOR_INVALIDO = "valor em dinheiro precisa ser maior que zero"


class RiscoInvalido(ValueError):
    """O dinheiro nao pode virar preco. `str(exc)` e o motivo, ja pronto."""


def contrato_de(ficha: dict | None) -> float | None:
    """O `contract_size` da ficha do ativo, ou None."""
    if not ficha:
        return None
    for chave in ("contract_size", "contractSize", "trade_contract_size"):
        valor = ficha.get(chave)
        if isinstance(valor, (int, float)) and valor > 0:
            return float(valor)
    return None


def valor_do_nivel(entrada: float, nivel: float, volume: float, contrato: float) -> float:
    """Dinheiro em jogo entre a entrada e o nivel."""
    return abs(entrada - nivel) * volume * contrato


#: Para que lado do preco o nivel vai, por papel e por lado da posicao.
#
# MEDIDO (05/10/2026): a primeira versao usava SO o lado, e devolvia o stop
# ACIMA da entrada numa compra — 105 em vez de 95. Um stop acima do preco de uma
# compra e executado no primeiro tick: o operador perde antes de a posicao
# respirar. O dado que faltava nao era o LADO, era o PAPEL: o mesmo valor e stop
# numa direcao e alvo na outra.
#:                `buy`      `sell`
_DIRECAO = {
    ("stop", "buy"): -1,
    ("stop", "sell"): +1,
    ("alvo", "buy"): +1,
    ("alvo", "sell"): -1,
}


def nivel_do_valor(
    entrada: float,
    valor: float,
    volume: float,
    lado: Lado,
    contrato: float | None,
    papel: Papel = "stop",
) -> float:
    """
    O nivel que produz o dinheiro pedido, para o PAPEL pedido.

    `papel` decide o sinal do deslocamento; `lado` decide o sentido. Os dois sao
    necessarios: `stop` de compra fica abaixo, `alvo` de compra fica acima, e o
    mesmo para a venda invertido.

    Levanta `RiscoInvalido` com motivo, em vez de devolver numero inventado:
    nivel de stop que sai errado manda a ordem errada.
    """
    if contrato is None:
        raise RiscoInvalido(SEM_CONTRATO)
    if not isinstance(volume, (int, float)) or volume <= 0:
        raise RiscoInvalido(SEM_VOLUME)
    if not isinstance(valor, (int, float)) or valor <= 0:
        raise RiscoInvalido(VALOR_INVALIDO)
    if not isinstance(entrada, (int, float)) or entrada <= 0:
        raise RiscoInvalido("preco de entrada invalido")
    try:
        sentido = _DIRECAO[(papel, lado)]
    except KeyError:
        raise RiscoInvalido(f"papel invalido: {papel!r}") from None
    distancia = valor / (volume * contrato)
    return entrada + sentido * distancia


def niveis_do_valor(
    entrada: float,
    sl_valor: float | None,
    tp_valor: float | None,
    volume: float,
    lado: Lado,
    contrato: float | None,
) -> dict[str, float | None]:
    """
    SL e TP em preco, derivados do dinheiro do operador.

    O LADO decide para onde cada um vai:

        `sell` -> o stop fica ACIMA da entrada e o alvo ABAIXO
        `buy`  -> o stop fica ABAIXO da entrada e o alvo ACIMA

    Isso e geometria de posicao, nao preferencia: um stop acima do preco em uma
    compra e imediatamente executado, e o operador perde no primeiro tick.

    Devolve `None` no que nao foi pedido.  Nao inventa nivel para campo vazio.
    """
    sl = (
        None
        if sl_valor is None
        else nivel_do_valor(entrada, sl_valor, volume, lado, contrato, papel="stop")
    )
    tp = (
        None
        if tp_valor is None
        else nivel_do_valor(entrada, tp_valor, volume, lado, contrato, papel="alvo")
    )
    return {"sl_preco": sl, "tp_preco": tp}


def risco_real(
    entrada: float,
    nivel: float | None,
    volume: float,
    contrato: float | None,
) -> float | None:
    """Dinheiro em jogo, ou None se nao ha nivel/contrato."""
    if nivel is None or contrato is None:
        return None
    return valor_do_nivel(entrada, nivel, volume, contrato)