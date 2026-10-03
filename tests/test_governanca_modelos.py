# -*- coding: utf-8 -*-
"""A porta de qualidade do `train_v2` nao pode ser apagada pelo pipeline legado.

Regressao real de 2026-09-29: `Python/auto_retrain.py` chama `Pipeline`, que
gravava um `.meta.json` sem `min_edge`, `publicable` e `publish_reason` por
cima dos metadados governados. O resultado foi um catalogo de 36 modelos com 6
arquivos sem governanca, e `tests/test_ai_inference.py` passou a falhar.

Estes testes travam o comportamento: o pipeline legado pode acrescentar os
seus campos (`dataset_version`, `model_version`), mas nunca remover os do
`train_v2`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PY_DIR = RAIZ / "Python"
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))

from pipeline import preservar_governanca  # noqa: E402


_GOVERNADO = {
    "symbol": "AUDUSD",
    "timeframe": "M5",
    "feature_version": "25F-v2",
    "feature_hash": "27727ee00bc30b7f",
    "feature_count": 25,
    "algorithm": "RandomForestClassifier",
    "metrics": {
        "accuracy": 0.44,
        "baseline": 0.333,
        "edge": 0.108,
        "folds": [{"fold": 1, "edge": 0.12}],
        "edge_estavel": True,
    },
    "publicable": False,
    "publish_reason": "edge +0.0210 abaixo do minimo +0.0500",
    "min_edge": 0.05,
    "train_date": "2026-09-28T03:33:20+00:00",
}

# O que `pipeline.py` legado tentava gravar por cima.
_LEGADO = {
    "algorithm": "CalibratedClassifierCV",
    "train_date": "2026-09-29T12:00:29+00:00",
    "dataset_version": "2b5178d118bae147",
    "metrics": {"accuracy": 0.328, "f1_score": 0.336},
    "feature_count": 25,
    "symbol": "AUDUSD",
    "timeframe": "M5",
    "model_version": "1.2.0",
}


def _escrever(tmp_path: Path, conteudo: dict) -> Path:
    caminho = tmp_path / "AUDUSD_M5.meta.json"
    caminho.write_text(json.dumps(conteudo, indent=2), encoding="utf-8")
    return caminho


def test_legado_nao_apaga_a_porta_de_qualidade(tmp_path):
    caminho = _escrever(tmp_path, _GOVERNADO)
    resultado = preservar_governanca(caminho, _LEGADO)

    assert resultado["min_edge"] == 0.05
    assert resultado["publicable"] is False
    assert resultado["publish_reason"] == _GOVERNADO["publish_reason"]
    assert resultado["feature_hash"] == _GOVERNADO["feature_hash"]


def test_legado_nao_apaga_a_razao_da_reprovacao(tmp_path):
    """O caso real: AUDUSD_M5 reprovado ficava com `reason` vazio."""
    caminho = _escrever(tmp_path, _GOVERNADO)
    resultado = preservar_governanca(caminho, _LEGADO)
    assert resultado["publish_reason"], "a razao da reprovacao precisa sobreviver"


def test_legado_preserva_as_metricas_de_walk_forward(tmp_path):
    caminho = _escrever(tmp_path, _GOVERNADO)
    resultado = preservar_governanca(caminho, _LEGADO)
    assert "folds" in resultado["metrics"]
    assert resultado["metrics"]["edge"] == 0.108


def test_legado_pode_acrescentar_seus_campos(tmp_path):
    """Preservar nao pode virar apagar: o MQL5 le `dataset_version`."""
    caminho = _escrever(tmp_path, _GOVERNADO)
    resultado = preservar_governanca(caminho, _LEGADO)
    assert resultado["dataset_version"] == "2b5178d118bae147"
    assert resultado["model_version"] == "1.2.0"


def test_meta_inexistente_e_criado_normalmente(tmp_path):
    resultado = preservar_governanca(tmp_path / "NOVO_M5.meta.json", _LEGADO)
    assert resultado == _LEGADO
    assert "min_edge" not in resultado


def test_meta_legado_continua_sendo_substituivel(tmp_path):
    """Sem governanca anterior, nao ha o que preservar."""
    caminho = _escrever(tmp_path, _LEGADO)
    resultado = preservar_governanca(caminho, dict(_LEGADO, model_version="1.2.1"))
    assert resultado["model_version"] == "1.2.1"
    assert "governado_por" not in resultado


def test_meta_corrompido_nao_derruba_o_treino(tmp_path):
    caminho = tmp_path / "AUDUSD_M5.meta.json"
    caminho.write_text("{ nao e json", encoding="utf-8")
    resultado = preservar_governanca(caminho, _LEGADO)
    assert resultado == _LEGADO


def test_catalogo_real_do_repositorio_tem_governanca():
    """Trava de regressao no catalogo que o app realmente carrega.

    Foi aqui que a falha apareceu: 6 dos 36 `.meta.json` estavam sem `min_edge`
    e sem `publish_reason` por causa do auto-retrain.
    """
    modelos = RAIZ / "Python" / "models"
    if not modelos.is_dir():
        pytest.skip("catalogo de modelos ausente neste ambiente")
    metas = sorted(modelos.glob("*.meta.json"))
    if not metas:
        pytest.skip("nenhum modelo neste ambiente")

    sem_governanca = [
        m.name for m in metas
        if not {"min_edge", "publicable", "publish_reason"} <= set(json.loads(
            m.read_text(encoding="utf-8")
        ))
    ]
    assert not sem_governanca, (
        f"metadados sem a porta de qualidade do train_v2: {sem_governanca}"
    )