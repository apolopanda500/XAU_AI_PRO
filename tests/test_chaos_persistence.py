"""Caos & Persistencia — comandos moveis sob falha de rede/arquivo.

Testa o caminho real (`backend.mobile_command`), nao a API de outro modulo:
  - rajada concorrente com o mesmo `command_id` nunca corrompe o arquivo;
  - a pasta de destino se auto-recria quando ausente;
  - `confirm=true` e obrigatorio; o clique sem confirmacao morre;
  - sem `XAU_MOBILE_CONTROL_ENABLED=1` o caminho inteiro nao escreve nada;
  - arquivo .tmp nunca sobrevive ao fim da escrita atomica.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from backend import mobile_command


@pytest.fixture()
def cmd_dir(tmp_path, monkeypatch):
    destino = tmp_path / "subpasta" / "remote_cmd.json"
    monkeypatch.setattr(mobile_command, "CMD_FILE", destino)
    return destino


def _liga(monkeypatch, valor: str = "1") -> None:
    monkeypatch.setenv("XAU_MOBILE_CONTROL_ENABLED", valor)


class TestPersistencia:
    def test_pasta_ausente_e_recriada(self, monkeypatch, cmd_dir):
        _liga(monkeypatch)
        payload = mobile_command.montar_comando(
            action="RESUME_AUTO", command_id="chaos_create_dir", confirm=True,
        )
        r = mobile_command.escrever_comando(payload)
        assert r["ok"] is True
        assert cmd_dir.exists()
        assert not cmd_dir.with_suffix(".tmp").exists()

    def test_rajada_com_mesmo_command_id_nao_corrompe(self, monkeypatch, cmd_dir):
        _liga(monkeypatch)
        payload = mobile_command.montar_comando(
            action="PAUSE_AUTO", command_id="chaos_burst_999", confirm=True,
        )
        resultados: list[object] = []
        lock = threading.Lock()

        def disparar():
            try:
                mobile_command.escrever_comando(payload)
                with lock:
                    resultados.append(0)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    # Mantem o tipo do erro para diagnostico ao invés de somar 1.
                    resultados.append(exc)

        threads = [threading.Thread(target=disparar) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert resultados == [0] * 20, f"Erros ao lancar rajada: {resultados}"
        dados = json.loads(cmd_dir.read_text(encoding="utf-8"))
        assert dados["command_id"] == "chaos_burst_999"
        assert not cmd_dir.with_suffix(".tmp").exists()

    def test_sem_flag_nada_e_escrito(self, monkeypatch, cmd_dir):
        monkeypatch.delenv("XAU_MOBILE_CONTROL_ENABLED", raising=False)
        payload = mobile_command.montar_comando(
            action="PAUSE_AUTO", command_id="chaos_blocked", confirm=True,
        )
        with pytest.raises(RuntimeError):
            mobile_command.escrever_comando(payload)
        assert not cmd_dir.exists()

    def test_confirm_obrigatorio(self, monkeypatch, cmd_dir):
        _liga(monkeypatch)
        with pytest.raises(ValueError):
            mobile_command.montar_comando(action="PAUSE_AUTO", confirm=False)

    def test_arquivo_tem_so_o_payload(self, monkeypatch, cmd_dir):
        _liga(monkeypatch)
        payload = mobile_command.montar_comando(
            action="SET_RISK_PCT", value=0.75, confirm=True,
        )
        mobile_command.escrever_comando(payload)
        bruto = cmd_dir.read_text(encoding="utf-8")
        # Nunca pode conter tokens/segredos (o modulo nao aceita esses campos).
        for proibido in ("token", "senha", "secret", "api_key", "authorization"):
            assert proibido not in bruto.lower()
        dados = json.loads(bruto)
        assert dados["command_id"].startswith("mob_")
        assert dados["confirm"] is True
        assert dados["action"] == "SET_RISK_PCT"
        assert dados["value"] == 0.75
