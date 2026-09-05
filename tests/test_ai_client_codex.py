from pathlib import Path
from unittest.mock import patch


def test_ask_codex_reads_last_message(tmp_path: Path) -> None:
    from app.ai_client import _ask_codex

    def fake_run(command, **kwargs):
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("Resposta real", encoding="utf-8")
        return type("Completed", (), {"returncode": 0})()

    with patch("app.ai_client._codex_executable", return_value="codex.exe"), patch(
        "app.ai_client.subprocess.run", side_effect=fake_run
    ):
        result = _ask_codex([{"role": "user", "content": "Ola"}], 1)

    assert result == {"ok": True, "reply": "Resposta real", "error": "", "provider": "codex"}


def test_ask_ai_falls_back_to_codex_on_http_error() -> None:
    from app.ai_client import ask_ai

    with patch("app.ai_client._effective_settings", return_value={
        "enabled": True,
        "base_url": "https://api.openai.com/v1",
        "api_key": "redacted",
        "model": "gpt-test",
    }), patch("app.ai_client.urllib.request.urlopen", side_effect=OSError("offline")), patch(
        "app.ai_client._ask_codex",
        return_value={"ok": True, "reply": "Fallback ativo", "error": "", "provider": "codex"},
    ):
        result = ask_ai([{"role": "user", "content": "Teste"}])

    assert result["ok"] is True
    assert result["provider"] == "codex"
