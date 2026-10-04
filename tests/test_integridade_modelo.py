# -*- coding: utf-8 -*-
"""O artefato `.pkl` e conferido ANTES de ser desserializado.

POR QUE ESTE TESTE EXISTE
=========================
`joblib.load` desserializa com `pickle`, que EXECUTA codigo. O CodeQL classifica
como `py/unsafe-deserialization` (critical) — e com razao. O caminho do arquivo
ja era confinado em dois niveis, mas isso nao diz nada sobre o CONTEUDO: quem
consegue gravar um `.pkl` na pasta de modelos ganha execucao de codigo.

Estes testes usam um arquivo de TEXTO como `.pkl` de mentira. Nao importa: a
conferencia e sobre o digest do arquivo, e happens antes de qualquer desserializacao.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from Python.integridade_modelo import (  # noqa: E402
    CAMPO,
    conferir,
    registrar,
    sha256_do_artefato,
)


def _pkl(tmp: Path, conteudo: bytes = b"modelo original") -> Path:
    caminho = tmp / "XAUUSD_H1.pkl"
    caminho.write_bytes(conteudo)
    return caminho


class TestHashDoArtefato:
    def test_hash_muda_quando_o_arquivo_muda(self, tmp_path):
        a = _pkl(tmp_path, b"um")
        h1 = sha256_do_artefato(a)
        a.write_bytes(b"dois")
        assert sha256_do_artefato(a) != h1

    def test_hash_e_estavel_para_o_mesmo_arquivo(self, tmp_path):
        a = _pkl(tmp_path)
        assert sha256_do_artefato(a) == sha256_do_artefato(a)

    def test_arquivo_grande_e_lido_em_blocos(self, tmp_path):
        """> 1 MB passa pelo caminho de blocos; nao pode estourar memoria."""
        a = tmp_path / "grande.pkl"
        a.write_bytes(b"x" * (3 * 1024 * 1024))
        assert len(sha256_do_artefato(a)) == 64


class TestConferencia:
    def test_artefato_intacto_passa(self, tmp_path):
        pkl = _pkl(tmp_path)
        meta = registrar(pkl, {"symbol": "XAUUSD"})
        ok, motivo = conferir(pkl, meta)
        assert ok is True, motivo

    def test_artefato_adulterado_e_recusado_com_motivo(self, tmp_path):
        """O ataque: o `.pkl` foi trocado depois do treino."""
        pkl = _pkl(tmp_path)
        meta = registrar(pkl, {"symbol": "XAUUSD"})
        pkl.write_bytes(b"payload malicioso")
        ok, motivo = conferir(pkl, meta)
        assert ok is False
        assert "adulterado" in motivo

    def test_modelo_antigo_sem_hash_ainda_carrega(self, tmp_path):
        """Os 36 modelos ja treinados nao tem `model_sha256`.

        Bloquear aqui derrubaria a operacao sem ganho de seguranca: ausencia de
        hash e ausencia de verificacao.
        """
        pkl = _pkl(tmp_path)
        ok, motivo = conferir(pkl, {"symbol": "XAUUSD"})
        assert ok is True, motivo

    def test_arquivo_inexistente(self, tmp_path):
        ok, motivo = conferir(tmp_path / "nao_existe.pkl", {})
        assert ok is False
        assert "nao existe" in motivo

    def test_registrar_grava_o_hash_no_meta(self, tmp_path):
        pkl = _pkl(tmp_path)
        meta = registrar(pkl, {"symbol": "XAUUSD"})
        assert CAMPO in meta
        assert meta[CAMPO] == sha256_do_artefato(pkl)