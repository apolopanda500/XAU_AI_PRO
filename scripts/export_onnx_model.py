# -*- coding: utf-8 -*-
"""Exporta o modelo treinado em Python para .onnx pronto para o MetaTrader 5.

O MT5 (build 2360 em diante) executa ONNX nativamente, o que tira a inferencia
do processo Python e a traz para dentro do EA. O shape de entrada e fixo em
[1, n_features] de proposito: shape dinamico depende de optimizacao em tempo de
execucao e o MT5 e mais estavel com o formato congelado.

As dependencias (skl2onnx, onnx, onnxruntime) sao importadas dentro da funcao.
Nao estao no `requirements.txt` de producao porque o gateway nao precisa delas
- so este script e o teste de validacao precisam. Importar no topo faria o
gateway inteiro depender de um pacote que so serve na hora de treinar.

Uso como script:
    python scripts/export_onnx_model.py --model Models/meu_modelo.pkl \
        --features 30 --out Models/xau_modelo.onnx --opset 15
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path
from typing import Any

INSTALACAO = "pip install skl2onnx onnx onnxruntime"


def _importar_skl2onnx():
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError as exc:  # dependencia opcional, so necessaria aqui
        raise RuntimeError(
            f"skl2onnx/onnx nao instalados. Instale antes de exportar: {INSTALACAO}"
        ) from exc
    return convert_sklearn, FloatTensorType


def export_to_mt5_onnx(
    sklearn_model: Any,
    n_features: int,
    output_path: str,
    input_name: str = "float_input",
    opset: int = 15,
) -> Path:
    """Converte e grava o modelo, validando o artefato antes de devolver.

    Levanta RuntimeError quando as dependencias faltam e quando o ONNX Runtime
    nao consegue abrir o artefato gerado. Nao devolve um caminho de arquivo que
    nao passa pelo runtime: o MT5 recusaria o arquivo e o erro so apareceria no
    grafico, longe de quem treinou.
    """
    if n_features < 1:
        raise ValueError("n_features tem de ser >= 1")

    convert_sklearn, FloatTensorType = _importar_skl2onnx()

    initial_types = [(input_name, FloatTensorType([1, int(n_features)]))]
    onnx_model = convert_sklearn(sklearn_model, initial_types=initial_types, target_opset=opset)

    destino = Path(output_path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(onnx_model.SerializeToString())

    _validar_artefato(destino, input_name, n_features)
    return destino


def _validar_artefato(caminho: Path, input_name: str, n_features: int) -> None:
    """Abre o arquivo com o ONNX Runtime e roda uma inferencia de mentira."""
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError(
            f"onnxruntime nao instalado; nao foi possivel validar {caminho}. "
            f"Instale antes de entregar ao MT5: {INSTALACAO}"
        ) from exc

    sessao = ort.InferenceSession(str(caminho), providers=["CPUExecutionProvider"])
    entrada = np.zeros((1, int(n_features)), dtype=np.float32)
    resultado = sessao.run(None, {input_name: entrada})
    if not resultado:
        raise RuntimeError(f"modelo {caminho} nao devolveu saida na validacao")


def _carregar_modelo(caminho: str) -> Any:
    with open(caminho, "rb") as handle:
        return pickle.load(handle)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exporta um modelo sklearn para .onnx do MT5")
    parser.add_argument("--model", required=True, help="caminho do .pkl com o modelo treinado")
    parser.add_argument("--features", required=True, type=int, help="numero de features de entrada")
    parser.add_argument("--out", required=True, help="caminho do .onnx de saida")
    parser.add_argument("--opset", default=15, type=int, help="opset do ONNX (padrao 15)")
    args = parser.parse_args(argv)

    modelo = _carregar_modelo(args.model)
    destino = export_to_mt5_onnx(modelo, args.features, args.out, opset=args.opset)
    print(f"[ONNX OK] {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
