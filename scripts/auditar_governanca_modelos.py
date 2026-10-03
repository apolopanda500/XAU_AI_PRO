# -*- coding: utf-8 -*-
"""Confere quais metadados perderam a porta de qualidade do `train_v2`.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\auditar_governanca_modelos.py

O `auto_retrain` legado (Python/pipeline.py) escrevia um `.meta.json` sem
`min_edge`, `publicable` e `publish_reason` por cima dos metadados do
`train_v2`. Este script lista o catalogo inteiro e diz o que precisa ser
regenerado com `scripts/treinar_ia.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODELOS = RAIZ / "Python" / "models"
CAMPOS = ("min_edge", "publicable", "publish_reason", "feature_hash")


def main() -> int:
    # O console do Windows usa cp1252 por padrao e quebra em caractere nao-ASCII.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if not MODELOS.is_dir():
        print(f"catalogo ausente: {MODELOS}")
        return 1
    metas = sorted(MODELOS.glob("*.meta.json"))
    if not metas:
        print(f"nenhum .meta.json em {MODELOS}")
        return 1

    sem_governanca: list[str] = []
    publicaveis: list[str] = []
    reprovados: list[str] = []

    for caminho in metas:
        try:
            meta = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            sem_governanca.append(f"{caminho.name} (ilegivel: {exc})")
            continue
        if not isinstance(meta, dict) or not set(CAMPOS) <= set(meta):
            faltando = sorted(set(CAMPOS) - set(meta if isinstance(meta, dict) else {}))
            sem_governanca.append(f"{caminho.name} (sem {', '.join(faltando)})")
            continue
        (publicaveis if meta.get("publicable") else reprovados).append(caminho.stem)

    print(f"catalogo: {len(metas)} metadados")
    print(f"  com governanca: {len(publicaveis) + len(reprovados)}")
    print(f"  publicaveis   : {len(publicaveis)}")
    print(f"  reprovados     : {len(reprovados)}")
    if sem_governanca:
        print(f"  SEM GOVERNANCA: {len(sem_governanca)}")
        for item in sem_governanca:
            print(f"    - {item}")
        print()
        print("Para corrigir, regenere com o pipeline que passa pela porta:")
        print("  .\\.venv\\Scripts\\python.exe scripts\\treinar_ia.py --todos")
        return 2
    print("\nCatalogo integro: todo metadado tem a porta de qualidade.")
    return 0


if __name__ == "__main__":
    sys.exit(main())