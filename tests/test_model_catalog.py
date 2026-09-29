"""O catálogo informa metadados sem declarar integridade ou execução do modelo."""
import json
import sys

from Python import model_registry


def test_resolver_modelos_ignora_dir_vazio_do_bundle(tmp_path, monkeypatch):
    """O dir `Python/models` do bundle nao pode sequestrar a resolucao.

    No app instalado o `model_registry` (importado por `mt5_gateway`) criava
    `<bundle>/Python/models` vazio. Esse candidato e testado ANTES do
    `C:/Program Files/XAU AI PRO/Python/models` (72 arquivos), entao o
    gateway devolvia `models: []` e a UI mostrava "Nenhum modelo carregavel".
    """
    from backend import ai_inference

    bundle = tmp_path / "bridge" / "_internal"
    sombra = bundle / "Python" / "models"
    sombra.mkdir(parents=True)

    raiz = tmp_path / "XAU AI PRO"
    real = raiz / "Python" / "models"
    real.mkdir(parents=True)
    (real / "XAUUSD_H1.meta.json").write_text(json.dumps({"symbol": "XAUUSD"}), encoding="utf-8")

    monkeypatch.delenv("XAU_MODELOS_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(sys, "executable", str(raiz / "bridge" / "mt5-gateway.exe"), raising=False)
    monkeypatch.setattr(ai_inference, "RAIZ", bundle, raising=False)

    assert ai_inference._resolver_modelos() == real


def test_model_registry_nao_cria_diretorio_dentro_do_bundle(tmp_path, monkeypatch):
    """Congelado, `__file__` fica em Program Files: nao gravamos la."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("XAU_AI_PRO_MODELS", raising=False)
    destino = tmp_path / "_internal" / "Python"
    monkeypatch.setattr(
        model_registry, "__file__", str(destino / "model_registry.pyc"), raising=False
    )

    assert model_registry._resolve_models_dir() == destino / "models"
    assert not (destino / "models").exists()


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