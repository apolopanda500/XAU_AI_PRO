from pathlib import Path


def test_mql_data_path_matches_installed_mt5_layout() -> None:
    from app.utils.paths import get_base_dir, get_mql_data_path

    base = get_base_dir()
    data_path = get_mql_data_path()
    if base.parent.name.lower() == "files" and base.parent.parent.name.lower() == "mql5":
        assert data_path == base.parent / "Data"


def test_pipeline_uses_resolved_mt5_dataset() -> None:
    import sys

    project_root = Path(__file__).resolve().parent.parent
    python_dir = project_root / "Python"
    sys.path.insert(0, str(python_dir))
    try:
        from pipeline import Pipeline
        from mt5_bridge import get_mt5_data_path

        assert Pipeline().dataset_path == get_mt5_data_path() / "dataset.csv"
    finally:
        sys.path.remove(str(python_dir))
