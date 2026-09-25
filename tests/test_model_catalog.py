"""O catálogo informa metadados sem declarar integridade ou execução do modelo."""
import json

from Python import model_registry


def test_catalogo_exibe_ativo_e_timeframe_apenas_com_metadados_compativeis(tmp_path, monkeypatch):
    monkeypatch.setattr(model_registry, "MODELS_DIR", tmp_path)
    (tmp_path / "XAUUSD_M5.pkl").write_bytes(b"arquivo de teste")
    assert model_registry.model_catalog()[0]["trained_symbol"] is None
    assert model_registry.model_catalog()[0]["training_metadata_status"] == "missing"

    metadata = tmp_path / "XAUUSD_M5.meta.json"
    metadata.write_text(json.dumps({"symbol": "BTCUSD", "timeframe": "M5"}), encoding="utf-8")
    assert model_registry.model_catalog()[0]["training_metadata_status"] == "mismatch"
    assert model_registry.model_catalog()[0]["trained_symbol"] is None

    metadata.write_text(json.dumps({"symbol": "XAUUSD", "timeframe": "M5", "train_date": "2026-08-31T00:00:00Z", "algorithm": "RandomForest", "model_version": "1.2.0"}), encoding="utf-8")
    model = model_registry.model_catalog()[0]
    assert (model["trained_symbol"], model["trained_timeframe"]) == ("XAUUSD", "M5")
    assert model["training_metadata_status"] == "present"
    assert model["training_verified"] is False


def test_catalogo_rejeita_metadados_invalidos(tmp_path, monkeypatch):
    monkeypatch.setattr(model_registry, "MODELS_DIR", tmp_path)
    (tmp_path / "XAUUSD_M5.pkl").write_bytes(b"arquivo de teste")
    (tmp_path / "XAUUSD_M5.meta.json").write_text("{", encoding="utf-8")
    assert model_registry.model_catalog()[0]["training_metadata_status"] == "invalid"