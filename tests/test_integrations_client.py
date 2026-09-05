import json
import subprocess

from app.integrations_client import github_push_test, github_test


def test_github_test_prefers_authenticated_cli(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        payload = {"nameWithOwner": "owner/repo", "viewerPermission": "ADMIN"}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = github_test("https://github.com/owner/repo.git", "stale-token")

    assert result == {"ok": True, "message": "Conectado via GitHub CLI: owner/repo (ADMIN)"}
    assert calls[0][0][:3] == ["gh", "repo", "view"]
    assert "stale-token" not in calls[0][0]


def test_github_test_falls_back_to_git_without_cli(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[0] == "gh":
            raise FileNotFoundError
        return subprocess.CompletedProcess(command, 0, stdout="hash refs/heads/main\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = github_test("https://github.com/owner/repo.git", "token-value")

    assert result["ok"] is True
    assert calls[1][0] == ["git", "ls-remote", "--heads", "https://github.com/owner/repo.git"]
    assert "token-value" not in calls[1][0]
    assert calls[1][1]["env"]["GIT_CONFIG_VALUE_0"] == "Authorization: Bearer token-value"


def test_github_push_status_accepts_cli_auth(monkeypatch):
    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = github_push_test("", "stale-token")

    assert result["ok"] is True
    assert "nenhum envio" in result["message"]
