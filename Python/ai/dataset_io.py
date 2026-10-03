"""Leitura do dataset: encoding, colunas e inventario.

POR QUE ESTE MODULO EXISTE SEPARADO (2026-10-02)
==================================================
`_carregar`, em `Python/ai/train_multi.py`, travava sem produzir erro: o
processo ficava em 4 MB com CPU em zero e sumia. A causa era o import
**dentro** da funcao:

    from scripts.limpar_dataset import _detectar_encoding

`scripts/` **nao tem `__init__.py`** (medido). O Python trata um diretorio
sem `__init__.py` como *namespace package*, e o import de um submodule dele
dispara o *auto-loader*, que varre o diretorio inteiro — 36 arquivos — e
recursivamente os que importam. O processo travava ali.

A prova de que era isso: o mesmo parseo, executado **antes** de importar
`train_multi`, levava 2,2 s;via `_carregar`, nao terminava. A diferenca era
apenas esse import.

Aqui a funcao mora num modulo com import normal, e `train_multi.py`
importa este modulo **no topo**. Sem `__init__.py` e sem import aninhado.
"""
from __future__ import annotations

import os
from pathlib import Path

#: Colunas do dataset, na ordem em que aparecem no CSV. **Nao tem cabecalho.**
#:
#: MEDIDO: as linhas tem **11 campos**. Zipar com `train_v2.COLUNAS_DATASET`
#: (15 campos) dava `KDI_MINUS = None` em toda linha, e um filtro de largura
#: errado descartava o arquivo inteiro.
COLUNAS: tuple[str, ...] = (
    "Time", "Symbol", "Open", "High", "Low", "Close", "Volume",
    "Spread", "ATR", "ADX", "RSI",
)

#: Colunas numericas, na ordem em que aparecem depois de Time e Symbol.
NUMERICAS: tuple[str, ...] = COLUNAS[2:]

#: Onde o dataset vive. `%APPDATA%` e o dono da maquina; o id do terminal e o
#: mesmo que o app instalado usa.
DATA_DIR = (
    Path(os.environ.get("APPDATA", str(Path.home())))
    / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075"
    / "MQL5" / "Files" / "Data"
)

DATASET_LIMPO = DATA_DIR / "dataset_limpo.csv"

ORIGINAIS = ("dataset_legacy_20260910_1730.csv", "dataset.csv")


def detectar_encoding(caminho: Path) -> str:
    """UTF-16 LE ou UTF-8, medido pelo BOM e pelos primeiros bytes.

    MEDIDO (2026-10-02): `dataset_legacy_20260910_1730.csv` e **UTF-16 LE**.
    Lido como UTF-8, cada caractere vem precedido de `\\x00` e `AUDUSD` vira
    ` A U D U S D `. Foi por isso que a primeira limpeza mediu *"677.011
    lidas, 0 mantidas"* e listou `BTCUSD` entre os DESCARTADOS — e por isso que
    a auditoria anterior acusava "193 simbolos" cheios de lixo (`0.0`, `69`,
    `35.981`, `HF`): nao era sujeira no CSV, era leitura errada.

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


def ler_simbolos(caminho: Path, alvo: set[str]) -> list[dict[str, object]]:
    """Le as linhas cujo `Symbol` esta em `alvo`, ja como registros.

    Monta **colunas em listas**, nao um dict por linha: 324 mil linhas de
    cripto viravam 324 mil dicionarios Python, e o processo morria de
    memoria antes de chegar no `DataFrame`. Medido: 2,4 s assim.
    """
    colunas: dict[str, list] = {c: [] for c in COLUNAS}
    encoding = detectar_encoding(caminho)
    with caminho.open("r", encoding=encoding, errors="replace", newline="") as fh:
        for bruta in fh:
            partes = bruta.rstrip("\r\n").split(",")
            if len(partes) < 7:
                continue
            simbolo = partes[1].strip().upper()
            if simbolo not in alvo:
                continue
            colunas["Time"].append(partes[0].strip())
            colunas["Symbol"].append(simbolo)
            for i, nome in enumerate(NUMERICAS, start=2):
                try:
                    colunas[nome].append(float(partes[i]))
                except (ValueError, IndexError):
                    colunas[nome].append(float("nan"))
    if not colunas["Time"]:
        return []
    return [dict(zip(COLUNAS, valores)) for valores in zip(*(colunas[c] for c in COLUNAS))]