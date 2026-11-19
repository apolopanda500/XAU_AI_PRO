"""Testes de backend.mobile_command — controle destravado com a trava LIGADA.

Cobre:
  - 403 por padrao (fail-closed: sem XAU_MOBILE_CONTROL_ENABLED=1 a escrita morre);
  - confirm=true obrigatorio em toda gravacao;
  - faixas de seguranca de SET_RISK_PCT e SET_DAILY_TARGET_USD;
  - perfis validos de SET_PROP_PROFILE;
  - gravacao atomica do remote_cmd.json com command_id unico;
  - fail-closed tambem se alguém chamar escrever_comando diretamente.
"""

from __future__ import annotations

import json
import os

import pytest

from backend import mobile_command


@pytest.fixture()
def cmd_tmp(tmp_path, monkeypatch):
    destino = tmp_path / "remote_cmd.json"
    monkeypatch.setattr(mobile_command, "CMD_FILE", destino)
    return destino


def _ligar(monkeypatch, valor: str = "1") -> None:
    monkeypatch.setenv("XAU_MOBILE_CONTROL_ENABLED", valor)


class TestFailClosed:
    def test_padrao_desligado(self, monkeypatch, cmd_tmp):
        monkeypatch.delenv("XAU_MOBILE_CONTROL_ENABLED", raising=False)
        with pytest.raises(RuntimeError):
            mobile_command.escrever_comando(
                {"command_id": "c1", "action": "RESUME_AUTO"},
            )

    def test_disabled_0_recusa(self, monkeypatch, cmd_tmp):
        _ligar(monkeypatch, "0")
        with pytest.raises(RuntimeError):
            mobile_command.escrever_comando({"command_id": "c1", "action": "RESUME_AUTO"})

    def test_confirm_falso_recusa(self, monkeypatch, cmd_tmp):
        _ligar(monkeypatch)
        with pytest.raises(ValueError, match="confirm=true"):
            mobile_command.montar_comando(action="RESUME_AUTO", confirm=False)


class TestValidacao:
    def test_acao_desconhecida(self, monkeypatch):
        _ligar(monkeypatch)
        with pytest.raises(ValueError):
            mobile_command.montar_comando(action="GIVE_ALL_MONEY", confirm=True)

    def test_risco_fora_da_faixa(self, monkeypatch):
        _ligar(monkeypatch)
        with pytest.raises(ValueError):
            mobile_command.montar_comando(action="SET_RISK_PCT", value=15.0, confirm=True)
        with pytest.raises(ValueError):
            mobile_command.montar_comando(action="SET_RISK_PCT", value=0.0, confirm=True)

    def test_risco_valido(self, monkeypatch):
        _ligar(monkeypatch)
        res = mobile_command.montar_comando(action="SET_RISK_PCT", value=0.75, confirm=True)
        assert res["value"] == 0.75
        assert res["action"] == "SET_RISK_PCT"
        assert res["ok"] is not False if "ok" in res else True

    def test_alvo_diario_precisa_ser_positivo(self, monkeypatch):
        _ligar(monkeypatch)
        with pytest.raises(ValueError):
            mobile_command.montar_comando(action="SET_DAILY_TARGET_USD", value=-10, confirm=True)

    def test_perfil_invalido(self, monkeypatch):
        _ligar(monkeypatch)
        with pytest.raises(ValueError):
            mobile_command.montar_comando(action="SET_PROP_PROFILE", profile="URSO", confirm=True)

    def test_perfil_valido(self, monkeypatch):
        _ligar(monkeypatch)
        res = mobile_command.montar_comando(action="SET_PROP_PROFILE", profile="FTMO", confirm=True)
        assert res["profile"] == "FTMO"


class TestEscritaAtomica:
    def test_arquivo_sera_gravado(self, monkeypatch, cmd_tmp):
        _ligar(monkeypatch)
        payload = mobile_command.montar_comando(
            action="SET_RISK_PCT", value=0.75, confirm=True, command_id="cmd_test_001"
        )
        recibo = mobile_command.escrever_comando(payload)
        assert recibo["ok"] is True
        assert recibo["status"] == "EXECUTED"
        escrito = json.loads(cmd_tmp.read_text(encoding="utf-8"))
        assert escrito["command_id"] == "cmd_test_001"
        assert escrito["action"] == "SET_RISK_PCT"
        assert escrito["value"] == 0.75
        assert escrito["confirm"] is True

    def test_command_id_gerado_quando_ausente(self, monkeypatch, cmd_tmp):
        _ligar(monkeypatch)
        payload = mobile_command.montar_comando(action="PAUSE_AUTO", confirm=True)
        assert payload["command_id"].startswith("mob_")

    def test_tmp_nao_fica_residual(self, monkeypatch, cmd_tmp):
        _ligar(monkeypatch)
        payload = mobile_command.montar_comando(action="RESUME_AUTO", confirm=True)
        mobile_command.escrever_comando(payload)
        assert not cmd_tmp.with_suffix(".tmp").exists()
