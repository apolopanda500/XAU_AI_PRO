# -*- coding: utf-8 -*-
"""Contrato rígido do modelo universal — 18 features + integridade SHA-256."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from Python import train_universal_onnx as t  # noqa: E402


def _rows(n=60):
    return [{"close": 100.0 + i * 0.1, "high": 100.0 + i * 0.1 + 0.5,
             "low": 100.0 + i * 0.1 - 0.5, "time": 1_700_000_000 + i * 60,
             "tick_volume": 100 + (i % 5), "spread": 2} for i in range(n)]


def test_contrato_exatamente_18_features():
    assert len(t.FEATURE_COLUMNS) == 18
    assert len(set(t.FEATURE_COLUMNS)) == 18


def test_extracao_pura_devolve_as_18_features_em_ordem():
    feats = t.build_agnostic_features_pure(_rows())
    assert len(feats) == 60
    assert all(tuple(f.keys()) == t.FEATURE_COLUMNS for f in feats)
    assert all(all(isinstance(v, float) for v in f.values()) for f in feats)


def test_zero_ativo_fixo_no_codigo_do_pipeline():
    fonte = (ROOT / "Python" / "train_universal_onnx.py").read_text(encoding="utf-8")
    import io, tokenize
    codigo = [tok.string for tok in tokenize.generate_tokens(io.StringIO(fonte).readline)
              if tok.type not in (tokenize.STRING, tokenize.COMMENT)]
    txt = " ".join(codigo).upper()
    for proibido in ("XAUUSD", "EURUSD", "BTCUSD", "FTMO", "BINANCE", "MEXC", "OANDA"):
        assert proibido not in txt, f"símbolo/marca presumido no código: {proibido}"


def test_manifesto_com_hash_divergente_e_reprovado(tmp_path):
    artefato = tmp_path / "modelo.joblib"
    artefato.write_bytes(b"modelo-falso")
    manifesto = {"model_id": "modelo_teste", "feature_columns": list(t.FEATURE_COLUMNS),
                 "feature_count": 18, "artifact": artefato.name, "sha256": "hash-errado"}
    manifest = tmp_path / "model_manifest.json"
    manifest.write_text(json.dumps(manifesto), encoding="utf-8")
    ok, motivo = t.verify_manifest_integrity(manifest)
    assert ok is False and "SHA" in motivo


def test_manifesto_integro_e_aprovado(tmp_path):
    artefato = tmp_path / "modelo.joblib"
    artefato.write_bytes(b"modelo-real")
    manifesto = {"model_id": "modelo_teste", "feature_columns": list(t.FEATURE_COLUMNS),
                 "feature_count": 18, "artifact": artefato.name,
                 "sha256": hashlib.sha256(artefato.read_bytes()).hexdigest()}
    manifest = tmp_path / "model_manifest.json"
    manifest.write_text(json.dumps(manifesto), encoding="utf-8")
    ok, motivo = t.verify_manifest_integrity(manifest)
    assert ok is True, motivo
