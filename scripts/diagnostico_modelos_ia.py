"""Mede a qualidade real de cada modelo, contra o palpite da sua propria arvore.

Correcao importante: comparar com 0,50 so faz sentido para problema binario.
O pipeline treina 3 classes (SELL/NEUTRAL/BUY) ou 5, entao o palpite aleatorio e
1/n_classes. Um modelo de 3 classes com accuracy 0,378 e melhor que o palpite
(0,333), mas nao o suficiente para virar decisao.

Este script calcula:
  - accuracy
  - accuracy contra o palpite (1/n_classes)
  - f1 ponderado
  - edge = accuracy - palpite
  - disposicao: só "util" com edge minimo configuravel
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Edge minimo sobre o palpite para o modelo ser considerado utilizavel.
# Abaixo disso a IA nao agrega: e preciso lavar a mao, com o preco de operar.
EDGE_MINIMO = 0.05

RAIZES = [
    Path("Python/models"),
    Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    / "D0E8209F77C8CF37AD8BF550E51FF075" / "MQL5" / "Files" / "Data",
]

# O pipeline treina 3 classes por padrao (ver CATEGORY_CONFIG em Python/pipeline.py).
CLASSES_PADRAO = 3


def n_classes_do_model(dados: dict) -> int:
    for chave in ("n_classes", "classes"):
        valor = dados.get(chave)
        if isinstance(valor, int) and valor > 1:
            return valor
    return CLASSES_PADRAO


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    vistos: dict[str, dict] = {}
    for raiz in RAIZES:
        if not raiz.exists():
            continue
        for meta in raiz.glob("*.meta.json"):
            try:
                dados = json.loads(meta.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            nome = meta.stem.replace(".meta", "")
            if dados.get("model_version") or nome not in vistos:
                vistos[nome] = dados

    print(f"{'modelo':<20} {'acc':>7} {'palpite':>8} {'edge':>8} {'f1':>7}  disposicao")
    print("-" * 74)
    utilizaveis: list[str] = []
    for nome in sorted(vistos):
        dados = vistos[nome]
        metricas = dados.get("metrics")
        if isinstance(metricas, str):
            try:
                metricas = json.loads(metricas)
            except json.JSONDecodeError:
                metricas = {}
        if not isinstance(metricas, dict):
            continue
        acc = metricas.get("accuracy")
        f1 = metricas.get("f1_score")
        if not isinstance(acc, (int, float)):
            continue
        classes = n_classes_do_model(dados)
        palpite = 1.0 / classes
        edge = acc - palpite
        if edge >= EDGE_MINIMO:
            situacao = "UTIL"
            utilizaveis.append(nome)
        elif edge > 0:
            situacao = "acima do palpite, insuficiente"
        else:
            situacao = "PIOR QUE PALPITE"
        print(
            f"{nome:<20} {acc:>7.4f} {palpite:>8.3f} {edge:>+8.4f} "
            f"{(f1 if isinstance(f1, (int, float)) else 0):>7.4f}  {situacao}"
        )

    print("-" * 74)
    print(f"edge minimo exigido: {EDGE_MINIMO:+.2f} sobre o palpite")
    print(f"modelos utilizaveis: {len(utilizaveis)} de {len(vistos)}")
    if not utilizaveis:
        print(
            "\nNenhum modelo tem poder preditivo suficiente. Publicar sinal com eles\n"
            "seria pior do que a decisao sem IA. A trava de staleness do EA esta\n"
            "mantendo a IA inerte de proposito, e isso esta correto."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
