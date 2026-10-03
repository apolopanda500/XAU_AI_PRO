# -*- coding: utf-8 -*-
"""Inventario do dataset de treino: simbolos, linhas e janela temporal.

POR QUE ESTE SCRIPT EXISTE (2026-10-02)
========================================
O dono pediu reconstruir os modelos. Antes de treinar qualquer coisa, este
script responde a pergunta que decide todo o plano: **o que existe no disco**.

O log de treino de 28/09 fala em "454.649 linhas unicas", mas o CSV **nao
esta no repositorio** — vive em
`%APPDATA%/MetaQuotes/Terminal/<id>/MQL5/Files/Data`. Por isso um `grep` no
projeto nao acha nada.

Este script **nao treina nada**: mede e imprime. Sem dado, decidir qual modelo
treinar e especulacao.

LEITURA LINHA A LINHA, E NAO COM PANDAS
========================================
`auditar_dataset.py` le o arquivo inteiro em memoria e estoura o stack do
pandas (`overflow encountered in square`) — 170 MB com 15 colunas. Aqui so
interessa `Time` e `Symbol`, entao o arquivo e percorrido como texto: memoria
constante, e o unico jeito de auditar esse arquivo nesta maquina.
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from pathlib import Path

# `Path(...)` envolve so o primeiro segmento: sem os parenteses, o `/` de
# `Path(x) / "a" / "b"` fica `x / ("a" / "b")` e o `str` nao tem `/`. Por isso
# o `Path` inteiro tem de ser montado primeiro.
DATA = Path(
    os.getenv("APPDATA", str(Path.home()))
) / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075" / "MQL5" / "Files" / "Data"

ARQUIVOS = ("dataset_legacy_20260910_1730.csv", "dataset.csv")

#: Os CSVs **nao tem linha de cabecalho**. Medido: a primeira linha do legacy e
#: `2026-01-02 09:05:00,AUDUSD,0.66934,...` — ja um dado, nao o nome das
#: colunas. Ler `cabecalho` como coluna fez a primeira auditoria devolver
#: "1.354.287 linhas | 0 simbolos": contava linhas e nao achava `Symbol` por
#: causa disso.
#:
#: A ordem vem de `Python/ai/train_v2.py::COLUNAS_DATASET`, que e a mesma
#: ordem que `treinar_ia.py` ja assumia ao ler o arquivo. Nao e adivinhacao: o
#: time vem primeiro, e `Symbol` e a coluna 1.
INDICE_SYMBOL = 1
INDICE_TIME = 0
COLUNAS = (
    "Time", "Symbol", "Open", "High", "Low", "Close", "Volume",
    "Spread", "ATR", "ADX", "RSI", "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",
)


def _detectar_encoding(caminho: Path) -> str:
    """UTF-16 LE ou UTF-8, medido pelo BOM e pelos primeiros bytes.

    MEDIDO (2026-10-02): o legacy e **UTF-16 LE**. Lido como UTF-8, cada
    caractere vem precedido de `\\x00`, e `AUDUSD` vira ` A U D U S D `. E o
    que produziu a primeira auditoria com "193 simbolos", quase todos lixo
    (`0.0`, `69`, `35.981`, `HF`): nao era sujeira no CSV, era leitura
    errada de arquivo UTF-16 como bytes emparelhados.

    O legacy tem BOM `FF FE`; `dataset.csv` e UTF-8 sem BOM.
    """
    with caminho.open("rb") as fh:
        amostra = fh.read(64)
    if amostra[:2] == b"\xff\xfe":
        return "utf-16-le"
    if amostra[:2] == b"\xfe\xff":
        return "utf-16-be"
    nulos_impares = sum(1 for i in range(1, min(len(amostra), 40), 2) if amostra[i] == 0)
    return "utf-16-le" if nulos_impares > 8 else "utf-8"


def _inventaria(caminho: Path) -> tuple[Counter, str, str, int]:
    """Conta simbolos e marca inicio/fim do tempo, sem carregar o arquivo.

    `csv.reader` em 1,34 milhao de linhas de 15 campos leva minutos e segura
    memoria. Aqui so interessa o campo 1 (`Symbol`), entao o arquivo e lido
    linha a linha e o campo e recortado com `split`: bem mais rapido, e o
    resultado e o mesmo porque `Symbol` nunca contem virgula.

    Nao ha cabecalho: a primeira linha ja e dado.
    """
    contagem: Counter = Counter()
    primeiro = ultimo = ""
    linhas = 0
    with caminho.open("r", encoding=_detectar_encoding(caminho), errors="replace") as fh:
        for bruta in fh:
            linhas += 1
            partes = bruta.split(",")
            if len(partes) > INDICE_SYMBOL:
                simbolo = partes[INDICE_SYMBOL].strip()
                if simbolo:
                    contagem[simbolo] += 1
            if len(partes) > INDICE_TIME:
                marca = partes[INDICE_TIME].strip()
                if marca:
                    primeiro = primeiro or marca
                    ultimo = marca
    return contagem, primeiro, ultimo, linhas


def main() -> int:
    # O console do Windows e cp1252 e os timestamps do dataset sao UTF-8. Sem
    # isto o script morre com `UnicodeEncodeError` **depois** de varrer o
    # arquivo inteiro — dois minutos de trabalho perdidos numa linha de print.
    # O proprio `auditar_dataset.py` ja usa `reconfigure` pelo mesmo motivo.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if not DATA.exists():
        print(f"DATASET AUSENTE: {DATA}")
        print("Sem dado nao ha modelo novo. Ver docs/PLANO_MESTRE_20261002.md, secao 5.")
        return 1

    total = 0
    geral: Counter = Counter()
    for nome in ARQUIVOS:
        caminho = DATA / nome
        if not caminho.exists():
            print(f"  ausente: {nome}")
            continue
        contagem, primeiro, ultimo, linhas = _inventaria(caminho)
        total += linhas
        geral.update(contagem)
        print(f"\n=== {nome} ===")
        print(f"  {linhas:,} linhas | {len(contagem)} simbolos")
        print(f"  janela: {primeiro} -> {ultimo}")
        for simbolo, qtd in contagem.most_common():
            print(f"    {simbolo:14} {qtd:>9,}")

    print(f"\nTOTAL: {total:,} linhas | {len(geral)} simbolos distintos")
    return 0


if __name__ == "__main__":
    sys.exit(main())