# -*- coding: utf-8 -*-
"""Repara texto gravado com encoding dobrado (mojibake).

Falha real e versionada: `MarketTab.tsx` mostra "CatÃ¡logo", "CotaÃ§Ãµes" e
"Atualizandoâ€¦" na tela, porque os bytes UTF-8 foram relidos como cp1252 e
gravados de novo como UTF-8.

A reparacao e por trecho: pega o maximo de caracteres nao-ASCII seguidos,
tenta `cp1252 -> utf-8` e so troca quando (a) o trecho decodifica, (b) o
resultado nao traz marcador de mojibake e (c) havia marcador antes. Texto que
ja esta certo (acento correto) nao decodifica como UTF-8 e permanece intacto.
"""
from __future__ import annotations

import pathlib
import re
import sys

MARCADOR = re.compile(
    # Byte de continuacao vindo de UTF-8 de 2 bytes: Â/Ã + 0x80..0xBF.
    # 'Ã' seguido de letra (OPERACAO, PAINÉIS) nao conta.
    r"[\u00c2\u00c3][\u0080-\u00bf]"
    # UTF-8 de 3 bytes (â€¦ â€”) relido como cp1252.
    r"|â[\u20ac\u2018\u2019\u201a\u201c\u201d\u2013\u2014\u2026\u0152\u0153\u0160\u0161"
    r"\u0178\u017d\u017e\u02c6\u02dc]"
)

ALVOS = [
    "frontend/src/components/tabs/MarketTab.tsx",
]


def marcadores(texto: str) -> int:
    return len(MARCADOR.findall(texto))


def reparar_trecho(trecho: str) -> str:
    if marcadores(trecho) <= 0:
        return trecho
    try:
        consertado = trecho.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return trecho
    if marcadores(consertado) > 0:
        return trecho
    return consertado


def reparar_texto(texto: str) -> tuple[str, int]:
    saida: list[str] = []
    trecho: list[str] = []
    trocas = 0

    def despejar() -> None:
        nonlocal trocas
        if not trecho:
            return
        bloco = "".join(trecho)
        consertado = reparar_trecho(bloco)
        if consertado != bloco:
            trocas += 1
        saida.append(consertado)
        trecho.clear()

    for caractere in texto:
        if ord(caractere) >= 0x80:
            trecho.append(caractere)
            continue
        despejar()
        saida.append(caractere)
    despejar()
    return "".join(saida), trocas


def main(argv: list[str]) -> int:
    alvos = argv[1:] or ALVOS
    falhou = False
    for alvo in alvos:
        caminho = pathlib.Path(alvo)
        bruto = caminho.read_bytes()
        com_bom = bruto.startswith(b"\xef\xbb\xbf")
        texto = bruto.decode("utf-8-sig")
        antes = marcadores(texto)
        novo, trocas = reparar_texto(texto)
        depois = marcadores(novo)
        caminho.write_bytes((("\ufeff" + novo) if com_bom else novo).encode("utf-8"))
        print(f"{alvo}: trechos_trocados={trocas} marcadores {antes} -> {depois}")
        if depois:
            print(f"  AINDA SUJO em {alvo}", file=sys.stderr)
            falhou = True
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
