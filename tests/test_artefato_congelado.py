# -*- coding: utf-8 -*-
"""Bateria do ARTEFATO congelado — o `.exe` que o instalador entrega.

A regra do ciclo é medir o artefato, não o código (AGENTS.md). Toda a suíte do
gateway sobe `backend/mt5_gateway.py` pelo fonte; o que o operador executa é o
`dist/mt5-gateway/mt5-gateway.exe` do PyInstaller, e é esse binário que já
saiu do ar com o entry point trocado (`fastapi_gateway` em vez de
`mt5_gateway`) e sem `Docs/version.json` (tela branca no bootstrap).

A medição fica em `scripts/medir_artefato_gateway.py` e é IMPORTADA aqui — um
teste que repete o código prova que o código está certo mesmo quando está
errado (AGENTS.md §6).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ESPECIFICACAO = ROOT / "scripts" / "medir_artefato_gateway.py"
_spec = importlib.util.spec_from_file_location("medir_artefato_gateway", ESPECIFICACAO)
medir = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(medir)

EXE = Path(medir.EXE_PADRAO)

#: Uma unica medicao por sessao: o binario demora a subir.
@pytest.fixture(scope="module")
def medicao():
    if not EXE.is_dir() and not EXE.is_file():
        pytest.skip("bundle ainda nao construido (rode scripts/build_app.bat)")
    resultado = medir.medir_artefato(str(EXE), token="bateria-artefato-pytest")
    if not resultado.get("respondeu"):
        pytest.fail(f"o binario nao respondeu: {resultado}")
    return resultado


class TestArtefatoCongelado:
    def test_sem_token_e_401_em_tudo(self, medicao):
        """Fail-closed no binario, não só no fonte (decisao em mt5_gateway:3131)."""
        abertas = {r: c for r, c in medicao["sem_token"].items() if c != 401}
        assert not abertas, abertas

    def test_token_errado_e_401(self, medicao):
        """Prova negativa: se 401 viesse de qualquer string, o teste passaria."""
        assert medicao["token_errado"] == 401

    def test_com_token_as_rotas_respondem(self, medicao):
        rejeitadas = {r: c for r, c in medicao["com_token"].items() if c != 200}
        assert not rejeitadas, rejeitadas

    def test_gateway_build_bate_com_a_fonte(self, medicao):
        """Identidade lida de Docs/version.json DENTRO do pacote."""
        import backend.mt5_gateway as gw

        assert medicao["gateway_build"] == gw.GATEWAY_BUILD, (
            f"artefato={medicao['gateway_build']} fonte={gw.GATEWAY_BUILD} "
            "— o pacote le um version.json diferente do repositorio"
        )

    def test_nenhum_saque_nenhuma_transferencia(self, medicao):
        """§2: a proibição vale no binário entregue, não só no código."""
        assert medicao["withdrawals_enabled"] is False
        assert medicao["transfers_enabled"] is False

    def test_ordem_dry_run_valida_sem_executar(self, medicao):
        assert medicao["codigo_ordem"] == 200, medicao
        assert medicao["ordem"].get("accepted") is True, medicao
        assert medicao["ordem"].get("stage") == "validated", medicao


def test_medicao_e_importada_do_script():
    """Se o import quebrar, o resto da bateria pularia em silêncio (§6)."""
    assert callable(medir.medir_artefato)
    assert EXE.name == "mt5-gateway.exe"
    assert EXE.parent.name == "mt5-gateway"


def test_estado_ausente_e_dito_quando_nao_ha_bundle():
    """Quando o bundle não existe, a medição diz por quê — não finge sucesso."""
    resultado = medir.medir_artefato(os.path.join(str(ROOT), "inexistente", "x.exe"))
    assert resultado["disponivel"] is False
    assert "bundle nao construido" in resultado["motivo"]
