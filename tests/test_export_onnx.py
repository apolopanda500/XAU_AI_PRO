# -*- coding: utf-8 -*-
"""Testes da exportacao ONNX.

As dependencias de exportacao (skl2onnx, onnx, onnxruntime) sao opcionais e NAO
estao instaladas no ambiente de producao - so este script precisa delas. Por
isso o teste que depende delas e condicional: quando faltam, o que se prova e
que o script avisa com clareza em vez de falhar com um traceback de import.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys

import pytest

from scripts.export_onnx_model import export_to_mt5_onnx, main

TEM_SKL2ONNX = importlib.util.find_spec("skl2onnx") is not None


def test_recusa_features_invalidas_sem_precisar_de_dependencia():
    with pytest.raises(ValueError):
        export_to_mt5_onnx(sklearn_model=None, n_features=0, output_path="x.onnx")


@pytest.mark.skipif(TEM_SKL2ONNX, reason="dependencias instaladas: o caminho de erro nao se aplica")
def test_sem_dependencia_o_erro_diz_o_que_instalar():
    with pytest.raises(RuntimeError) as erro:
        export_to_mt5_onnx(sklearn_model=None, n_features=30, output_path="x.onnx")
    assert "skl2onnx" in str(erro.value)
    assert "pip install" in str(erro.value)


def test_cli_exige_os_tres_argumentos():
    with pytest.raises(SystemExit):
        main(["--model", "m.pkl"])


def test_cli_responde_ao_help_sem_importar_dependencia():
    concluido = subprocess.run(
        [sys.executable, "-m", "scripts.export_onnx_model", "--help"],
        capture_output=True,
        text=True,
    )
    assert concluido.returncode == 0
    assert "--features" in concluido.stdout
