# -*- coding: utf-8 -*-
"""Limpa o dataset e mede a qualidade real por simbolo.

O QUE ESTE SCRIPT FAZ, E POR QUE ANTES DE TREINAR
=================================================
O dataset tem **1.354.289 linhas** e **249 nomes distintos** no campo
`Symbol`. A maioria desses nomes e lixo de escrita concorrente: `0.0`, `69`,
`35.981`, `HF`, `2026.09.16 05:15`. Treinar com isso produz modelo que
aprende lixo — o que `scripts/auditar_dataset.py` ja apontava no cabecalho
dele: *"indicadores do comeco do arquivo parecem nao inicializados (ADX=0,
RSI=50). Treinar com isso produz modelo que aprende lixo."*

Entao este script **nao treina**: filtra, conta e mede. Sem isso, decidir qual
modelo treinar e especulacao.

A SAIDA
=======
Um CSV limpo (`dataset_limpo.csv`) com so simbolos validos, mais o relatorio
de volume por simbolo e por classe. O relatorio e o que decide se a classe
tem volume suficiente para MULTI.

USO
====
    .\.venv\Scripts\python.exe scripts\limpar_dataset.py --simular
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from backend.asset_classes import CLASSES_COM_DADO, classe_de, simbolo_valido  # noqa: E402

DATA = Path(
    os.environ.get("APPDATA", str(Path.home()))
) / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075" / "MQL5" / "Files" / "Data"

ORIGINAIS = ("dataset_legacy_20260910_1730.csv", "dataset.csv")

#: Quantas linhas minimas um simbolo precisa ter para gerar um modelo. Abaixo
#: disso o treino produz fold instavel e o modelo nao generaliza — e a
#: governanca de 28/09 ja exigia `min_amostras=800`.
MINIMO_POR_SIMBOLO = 5_000


ENCODING = "utf-16-le"  # medido: cada caractere vem precedido de \x00


def _detectar_encoding(caminho: Path) -> str:
    """UTF-16 LE ou UTF-8, medido pelo BOM e pelos primeiros bytes.

    O legacy e UTF-16 LE e `dataset.csv` e UTF-8: dois arquivos, duas
    codificacoes, no mesmo dataset. Fixar uma so produz 0 linhas mantidas
    num deles — que e o que aconteceu na primeira execucao.

    O BOM UTF-16 LE e `FF FE`. Sem BOM, decide pelos NUL intercalados: em
    UTF-16 todo caractere ASCII vem com o byte alto zerado.
    """
    with caminho.open("rb") as fh:
        amostra = fh.read(64)
    if amostra[:2] == b"\xff\xfe":
        return "utf-16-le"
    if amostra[:2] == b"\xfe\xff":
        return "utf-16-be"
    # Sem BOM: UTF-16 tem um NUL em toda posicao impar.
    nulos_impares = sum(1 for i in range(1, min(len(amostra), 40), 2) if amostra[i] == 0)
    return "utf-16-le" if nulos_impares > 8 else "utf-8"


def _iterar_linhas(caminho: Path):
    """Le o CSV linha a linha, na codificacao REAL do arquivo.

    MEDIDO (2026-10-02): `dataset_legacy_20260910_1730.csv` e **UTF-16 LE** —
    lido como UTF-8 cada caractere vem com `\\x00` antes, e `AUDUSD` vira
    ` A U D U S D `. Foi por isso que a primeira execucao do limpador
    mediu "677.011 lidas, 0 mantidas, 0 simbolos validos" e(listou BTCUSD
    entre os DESCARTADOS: o filtro estava certo e a LEITURA estava errada.

    Isso tambem explica os "193 simbolos" cheios de lixo da auditoria
    anterior (`0.0`, `69`, `35.981`, `HF`): o parser leu bytes pares de um
    arquivo de bytes impares.

    Nao ha cabecalho: a primeira linha ja e dado.
    """
    with caminho.open("r", encoding=_detectar_encoding(caminho), errors="replace", newline="") as fh:
        for bruta in fh:
            partes = bruta.rstrip("\r\n").split(",")
            if len(partes) >= 7:
                yield partes


def _numero(texto: str) -> float | None:
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=str(DATA / "dataset_limpo.csv"))
    ap.add_argument("--so", default="")
    ap.add_argument("--simular", action="store_true")
    args = ap.parse_args()

    filtro = args.so.strip().upper()
    if filtro and filtro not in {"CRYPTO", "FIAT", "METALS", "OUTROS"}:
        print(f"classe invalida: {filtro!r}. Use {CLASSES_COM_DADO} ou OUTROS.")
        return 2

    if not DATA.exists():
        print(f"DATASET AUSENTE: {DATA}")
        return 1

    contagem: Counter = Counter()
    por_classe: defaultdict[str, Counter] = defaultdict(Counter)
    tempo: dict[str, list[str]] = defaultdict(list)
    descartados: Counter = Counter()
    total = mantidas = 0

    destino = Path(args.saida)
    saida = None if args.simular else destino.open("w", encoding="utf-8", newline="")
    try:
        for nome in ORIGINAIS:
            caminho = DATA / nome
            if not caminho.exists():
                print(f"  ausente: {nome}")
                continue
            for partes in _iterar_linhas(caminho):
                total += 1
                simbolo = partes[1].strip().upper()
                classe = classe_de(simbolo)
                descarta = (
                    not simbolo_valido(simbolo)
                    or close_invalida(partes)
                    or (filtro and (classe != filtro or classe == "OUTROS"))
                )
                if descarta:
                    descartados[simbolo or "(vazio)"] += 1
                    continue
                mantidas += 1
                contagem[simbolo] += 1
                por_classe[classe][simbolo] += 1
                if len(tempo[simbolo]) < 2:
                    tempo[simbolo].append(partes[0].strip())
                if saida is not None:
                    saida.write(",".join(partes) + "\n")
    finally:
        if saida is not None:
            saida.close()

    print("\n=== LIMPEZA ===")
    print(f"lidas:      {total:,}")
    print(f"mantidas:   {mantidas:,}  ({mantidas / max(total, 1) * 100:.1f}%)")
    print(f"descartadas:{total - mantidas:,}")
    print(f"simbolos validos: {len(contagem)}")

    for classe in sorted(por_classe):
        print(f"\n--- {classe} ---")
        for simbolo, qtd in por_classe[classe].most_common():
            janela = tempo.get(simbolo, [])
            marca = f"  {janela[0]} -> {janela[-1]}" if janela else ""
            sinal = "OK   " if qtd >= MINIMO_POR_SIMBOLO else "POUCO"
            print(f"  [{sinal}] {simbolo:12} {qtd:>8,}{marca}")

    print("\n=== DESCARTADOS (top 12) ===")
    for simbolo, qtd in descartados.most_common(12):
        print(f"  {simbolo[:28]:30} {qtd:>8,}")

    print("\n=== CLASSE SEM DADO ===")
    print("  INDICES: nenhum indice (SPX500, US30, NAS100...) neste dataset.")

    if not args.simular:
        print(f"\nCSV limpo em: {destino}")
    return 0


def close_invalida(partes: list[str]) -> bool:
    """Linha sem preco utilizavel. `Close` e o campo 5."""
    close = _numero(partes[5])
    return close is None or close <= 0


if __name__ == "__main__":
    sys.exit(main())