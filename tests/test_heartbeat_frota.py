# -*- coding: utf-8 -*-
"""Trava do heartbeat de frota (25/11/2026).

MEDIDO: varias instancias LIVE escrevem o mesmo `XAU_AI_PRO_heartbeat.json`
em FILE_COMMON. O gateway le o ultimo gravador; `symbol` e `timeframe` do
grafico oscilavam no /api/status e no TopNav (`no grafico · EURUSD 5` / `no
grafico · GOLD 5`). O heartbeat e da FROTA da conta, nao de um grafico.

Este teste NAO repete o codigo: ele le o `.mqh` embedido, extrai a chamada
`StringFormat` de verdade e confere a que argumento cada placeholder esta
ligado. A prova negativa usa o formato antigo e exige reprovação.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
EMBUTIDA = RAIZ / "MQL5" / "Experts" / "XAU_AI_PRO" / "Integration" / "EAHeartbeat.mqh"
CANONICA = RAIZ.parents[1] / "Experts" / "XAU_AI_PRO" / "Integration" / "EAHeartbeat.mqh"

# Placeholders na ordem em que aparecem no literal de formato.
PLACEHOLDER = re.compile(r"%I64d|%\.[0-9]+f|%[0-9]*[sd]")


def _argumentos(texto: str) -> list[str]:
    """Separa argumentos de uma chamada por virgulas de primeiro nivel."""
    texto = texto.strip()
    if texto.startswith(","):
        texto = texto[1:].strip()
    partes: list[str] = []
    atual: list[str] = []
    nivel = 0
    em_string = False
    escapado = False
    for ch in texto:
        if em_string:
            atual.append(ch)
            if escapado:
                escapado = False
            elif ch == "\\":
                escapado = True
            elif ch == '"':
                em_string = False
            continue
        if ch == '"':
            em_string = True
            atual.append(ch)
            continue
        if ch in "([":
            nivel += 1
        elif ch in ")]":
            nivel -= 1
        if ch == "," and nivel == 0:
            partes.append("".join(atual).strip())
            atual = []
        else:
            atual.append(ch)
    if "".join(atual).strip():
        partes.append("".join(atual).strip())
    return partes


def _extrair(fonte: str) -> tuple[str, list[tuple[str, str]]]:
    """Devolve (literal de formato, [(placeholder, expressao), ...])."""
    achado = re.search(r"StringFormat\s*\(", fonte)
    assert achado, "chamada StringFormat do heartbeat nao encontrada"
    inicio = achado.end()
    nivel = 1
    i = inicio
    while i < len(fonte) and nivel:
        if fonte[i] == "(":
            nivel += 1
        elif fonte[i] == ")":
            nivel -= 1
        i += 1
    assert nivel == 0, "parenteses da StringFormat nao fecham"
    bloco = fonte[inicio:i - 1]

    literal = re.match(r'\s*("(?:[^"\\]|\\.)*")', bloco, re.S)
    assert literal, "literal de formato da StringFormat nao encontrado"
    args = _argumentos(bloco[literal.end():])
    pares = list(zip(PLACEHOLDER.findall(literal.group(1)), args))
    assert len(pares) == len(args), (
        f"placeholders ({len(pares)}) divergem dos argumentos ({len(args)})"
    )
    return literal.group(1), pares


def _validar(fonte: str) -> None:
    _, pares = _extrair(fonte)
    assert len(pares) >= 8, f"formato incompleto: {len(pares)} campos"

    # Indices 4..7: symbol, writer_symbol, timeframe, writer_timeframe.
    assert pares[4] == ("%s", "heartbeat_symbol"), pares[4]
    assert pares[5] == ("%s", "_Symbol"), pares[5]
    assert pares[6] == ("%d", "heartbeat_timeframe"), pares[6]
    assert pares[7] == ("%d", "Period()"), pares[7]

    assert re.search(r'const\s+string\s+heartbeat_symbol\s*=\s*"[^"]+"\s*;', fonte), (
        "rotulo estavel de symbol nao declarado"
    )
    assert re.search(r"const\s+int\s+heartbeat_timeframe\s*=\s*0\s*;", fonte), (
        "timeframe estavel da frota nao declarado"
    )
    # Separacao do backtest nao pode ser perdita com a correcao do live.
    assert "XAU_AI_PRO_heartbeat_tester.json" in fonte
    assert "MQL_TESTER" in fonte


def test_heartbeat_da_frota_nao_segue_o_ultimo_grafico() -> None:
    _validar(EMBUTIDA.read_text(encoding="utf-8"))


def test_prova_negativa_formato_antigo_e_reprovado() -> None:
    """O formato que alimentava `symbol` com `_Symbol` TEM de falhar."""
    antigo = r'''
    const string json = StringFormat(
       "{\"schema\":\"ea-heartbeat.v1\",\"symbol\":\"%s\",\"timeframe\":%d}",
       _Symbol,
       Period());
    '''
    with pytest.raises(AssertionError):
        _validar(antigo)


def test_copia_canonica_usa_o_mesmo_formato() -> None:
    """A copia que o MT5 executa nao pode divergir da copia que o teste le."""
    if not CANONICA.exists():
        pytest.skip("copia canonica do EA nao existe neste ambiente")
    embutida, _ = _extrair(EMBUTIDA.read_text(encoding="utf-8"))
    canonica, _ = _extrair(CANONICA.read_text(encoding="utf-8"))
    assert canonica == embutida
