# -*- coding: utf-8 -*-
"""A trava de saque do script de prontidao nao pode reprovar quem proibe.

MEDIDO em 22/10/2026: `scripts/validar_prontidao_real.py` fazia

    git grep -E withdrawals_enabled[\"']?\\s*[:=]\\s*True

e reprovava `tests/test_metas_vip.py:146`, que e

    assert '"withdrawals_enabled": True' not in fonte

Ou seja: a checagem de prontidao acusava um teste que PROIBE o saque como se
fosse saque habilitado — o falso positivo do §6, onde a trava erra em cima de
quem estava certo. Aqui a correcao tem prova nos DOIS sentidos: o assert que
deve passar passa, e o dicionario ligado, que deve reprovar, reprova.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.validar_prontidao_real import (  # noqa: E402
    _arquivos_com_saque,
    _linhas_com_saque_ligado,
    _verificar_saque,
)

#: O fonte EXATO que reprovava antes. Se voltar a reprovar, a correcao regrediu.
FONTE_QUE_PROIBE = '''\
def test_catalogo_nao_declara_saque_em_nenhuma_meta():
    fonte = Path("backend/metas_vip.py").read_text(encoding="utf-8")
    assert '"withdrawals_enabled": True' not in fonte
    assert "'withdrawals_enabled': True" not in fonte
'''


class TestProvaNegativa:
    def test_assert_que_proibe_nao_conta_como_saque_ligado(self):
        assert _linhas_com_saque_ligado(FONTE_QUE_PROIBE) == []

    def test_dicionario_ligado_e_detectado(self):
        fonte = 'CAP = {"withdrawals_enabled": True}\n'
        assert _linhas_com_saque_ligado(fonte) == [1]

    def test_kwarg_ligado_e_detectado(self):
        fonte = 'resposta = json.dumps(withdrawals_enabled=True)\n'
        assert _linhas_com_saque_ligado(fonte) == [1]

    def test_desligado_nao_conta(self):
        fonte = '{"withdrawals_enabled": False, "transfers_enabled": False}\n'
        assert _linhas_com_saque_ligado(fonte) == []

    def test_comentario_contando_nao_conta(self):
        fonte = "# era withdrawals_enabled=True, agora nao\n"
        assert _linhas_com_saque_ligado(fonte) == []

    def test_variavel_de_nome_parecido_nao_conta(self):
        fonte = "outro_withdrawals_enabled = True\n"
        assert _linhas_com_saque_ligado(fonte) == []


class TestCaminhoInteiro:
    def test_arquivos_com_saque_e_trilha_ate_o_repositorio(self):
        arquivos = _arquivos_com_saque()
        assert arquivos, "nenhum arquivo menciona withdrawals_enabled — trava ausente"
        assert all(a.suffix == ".py" for a in arquivos)

    def test_repositorio_real_passa(self, capsys):
        ok, detalhe = _verificar_saque()
        assert ok is True, detalhe
        assert "tokenize" in detalhe

    def test_verificar_reprova_quando_o_saque_aparece_ligado(self, monkeypatch, tmp_path):
        """Prova negativa do caminho inteiro: checagem com saque ligado reprova."""
        forjado = tmp_path / "backend"
        forjado.mkdir()
        (forjado / "adaptador.py").write_text(
            'def capabilities():\n    return {"withdrawals_enabled": True}\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "scripts.validar_prontidao_real._arquivos_com_saque",
            lambda: [forjado / "adaptador.py"],
        )
        ok, detalhe = _verificar_saque()
        assert ok is False
        assert "adaptador.py:2" in detalhe

    def test_verificar_reprova_quando_nao_consegue_ler(self, monkeypatch, tmp_path):
        quebrado = tmp_path / "quebrado.py"
        quebrado.write_text("withdrawals_enabled\n   (sem fechar\n", encoding="utf-8")
        monkeypatch.setattr(
            "scripts.validar_prontidao_real._arquivos_com_saque",
            lambda: [quebrado],
        )
        ok, detalhe = _verificar_saque()
        assert ok is False
        assert "nao consegui ler" in detalhe
