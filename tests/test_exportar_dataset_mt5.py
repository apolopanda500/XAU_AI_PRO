# -*- coding: utf-8 -*-
"""O exportador grava no MESMO layout que o DataEngineXAU le.

MEDIDO 22/10/2026: o dataset de treino terminava em 15/08/2026, e o terminal
tinha M5 real ate hoje. O exportador existe para fechar essa lacuna, e o
layout de 15 colunas e o contrato com o leitor (`DataEngineXAU.load`) e com o
treino (`train_v2`, que deriva ATR/ADX/RSI/KCI quando recebe zero).

A prova negativa aqui e o caso da barra com campo faltando: se o layout deixar
de ser 15 colunas, `escrever` tem de reprovar em vez de gravar linha torta.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.exportar_dataset_mt5 import COLUNAS, escrever, linhas_de  # noqa: E402


def barra(ts: int, preco: float = 2000.0) -> list[float]:
    return [ts, preco, preco + 1, preco - 1, preco + 0.5, 10.0, 3.0, 0]


class TestLayout:
    def test_15_colunas_na_ordem_do_leitor(self) -> None:
        linha = linhas_de(barra(1_700_000_000), "XAUUSD")
        assert len(linha) == COLUNAS == 15
        assert linha[1] == "XAUUSD"
        assert linha[0] == "2023-11-14 22:13:20"
        assert linha[8:15] == [0.0] * 7, "indicadores vao zerados: o treino deriva"

    def test_tempo_e_utc_sem_fuso_no_texto(self) -> None:
        carimbo = 1_700_000_000
        esperado = datetime.fromtimestamp(carimbo, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        assert linhas_de(barra(carimbo), "EURUSD")[0] == esperado


class TestEscrita:
    def test_deduplica_por_tempo_e_simbolo_ficando_com_o_novo(self, tmp_path: Path) -> None:
        antigo = linhas_de(barra(1_700_000_000, 2000.0), "XAUUSD")
        novo = linhas_de(barra(1_700_000_000, 2050.0), "XAUUSD")
        outro = linhas_de(barra(1_700_000_000, 1.1), "EURUSD")
        destino = tmp_path / "dataset.csv"
        total = escrever(destino, [antigo, novo, outro])
        assert total == 2
        conteudo = destino.read_text(encoding="utf-8").splitlines()
        assert len(conteudo) == 2
        assert any(",2050.0," in linha for linha in conteudo)
        assert not any(",2000.0," in linha for linha in conteudo)

    def test_layout_errado_reprova_em_vez_de_gravar(self, tmp_path: Path) -> None:
        destroco = linhas_de(barra(1_700_000_000), "XAUUSD")[:10]
        with pytest.raises(ValueError):
            escrever(tmp_path / "dataset.csv", [destroco])
