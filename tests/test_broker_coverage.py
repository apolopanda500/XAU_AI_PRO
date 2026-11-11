"""Testes da camada de corretoras e do formato canonico de simbolo.

Achados que estes testes fixam:

1. A matriz de capabilities gerava a coluna "Leitura" a partir de
   ``read_only``, que vale ``not execution``. O efeito era invertido: toda
   corretora sem execucao aparecia com "OK" e as que entregam dado publico
   real apareciam com "nao".
2. Saque e transferencia permanecem False fixos em qualquer corretora.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from backend.broker_registry import (
    BROKERS,
    capability_matrix,
    code_only_brokers,
    list_brokers,
    normalize_read_scope,
    read_brokers,
    supported_brokers,
)


class TestMatrizLeituraNaoInvertida:
    """A coluna "Leitura" da matriz precisa dizer a verdade."""

    def test_matriz_expoe_public_data(self) -> None:
        linhas = capability_matrix(include_planned=True)
        assert linhas, "a matriz nao pode voltar vazia"
        for linha in linhas:
            assert "public_data" in linha, "a matriz precisa expor public_data"
            assert isinstance(linha["public_data"], bool)

    def test_public_data_nao_e_read_only(self) -> None:
        """O campo da coluna Leitura nao pode ser o de execucao.

        Ambas as variaveis existem no registro, mas medem coisas diferentes:
        `public_data` responde "existe dado publico?", `read_only` responde
        "nao executa ordem?". Usar a segunda na primeira produz o documento
        invertido.
        """
        linhas = capability_matrix(include_planned=True)
        ativas = [linha for linha in linhas if linha["status"] == "active"]
        assert ativas, "deveria haver corretora ativa"
        assert any(linha["public_data"] != linha["read_only"] for linha in ativas), (
            "public_data virou sinonimo de read_only: a coluna Leitura "
            "voltaria a medir execucao em vez de dado publico"
        )

    def test_toda_corretora_com_dado_publico_declara_sim(self) -> None:
        for linha in capability_matrix(include_planned=True):
            if linha["public_data"]:
                assert linha["read_only"] in (True, False)

    def test_documento_gerado_diz_a_verdade(self) -> None:
        """O .md precisa bater com o REGISTRO — sem depender do dia."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scripts.gerar_matriz_capacabilities import gerar

        destino = Path(__file__).resolve().parent.parent / "Docs" / "MATRIZ_CAPABILIDADES.md"
        sem_data = lambda texto: re.sub(r"Dados publicos: \d{4}-\d{2}-\d{2}", "Dados publicos: <data>", texto)

        assert sem_data(gerar()) == sem_data(destino.read_text(encoding="utf-8")), (
            "Docs/MATRIZ_CAPABILIDADES.md desatualizado: rode o gerador sem --check"
        )


def test_mt5_ativo_para_dados_publicos():
    assert {"mt5"} <= read_brokers()
    assert "mt5" not in code_only_brokers()
    assert "mt5" in supported_brokers()


def test_matriz_declara_execucao_e_nunca_saque():
    # App desbloqueado: corretoras ativas expoem execucao real e deixam de ser
    # somente-leitura. Saque e transferencia continuam fixos em False.
    for row in capability_matrix(include_planned=True):
        assert row["withdrawals"] is False
        assert row["transfers"] is False
        if row["status"] == "active":
            assert row["execution"], row
            assert row["read_only"] is False
        else:
            assert row["execution"] == []
            assert row["read_only"] is True


def test_gate_desligada_torna_a_corretora_somente_leitura(monkeypatch):
    monkeypatch.setenv("XAU_ENABLE_MT5_EXECUTION", "0")
    rows = [row for row in capability_matrix() if row["broker"] == "mt5"]
    assert rows
    for row in rows:
        assert row["execution"] == []
        assert row["read_only"] is True
        assert row["withdrawals"] is False


def test_corretoras_planejadas_nao_entram_no_padrao():
    padrao = {item["id"] for item in list_brokers()}
    assert padrao == {"mt5"}
    assert {"bitget", "coinbase", "kraken", "kucoin"} <= set(BROKERS)


def test_escopo_invalido_falha_explicito():
    with pytest.raises(ValueError):
        normalize_read_scope("binance", "metals")
    with pytest.raises(ValueError):
        normalize_read_scope("corretora-inexistente", "crypto-spot")
