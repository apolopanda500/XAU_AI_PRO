from pathlib import Path
import backend.mt5_gateway as gateway

def test_emergency_stop_file_blocks_state(monkeypatch, tmp_path: Path):
    marker = tmp_path / "STOP"
    monkeypatch.setattr(gateway, "REAL_EMERGENCY_STOP", marker)
    assert not marker.exists()
    marker.write_text("test", encoding="utf-8")
    assert marker.exists()
    marker.unlink(missing_ok=True)
    assert not marker.exists()
