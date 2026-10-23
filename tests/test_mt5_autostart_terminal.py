"""AUTO-START DO TERMINAL MT5 (medido 22/10/2026)

O gateway recusava conectar quando o `terminal64.exe` nao estava aberto, e o
app ficava `offline` ate o dono abrir o terminal na mao. O dono pediu que o
app abrisse o terminal que ele ja configurou.

O que este teste trava:

1. terminal aberto -> nao abre uma segunda janela;
2. terminal fechado e caminho confirmado -> abre UMA vez e chama
   `initialize(path=...)` com esse caminho;
3. terminal fechado e caminho ausente -> RECUSA, sem `Popen` e sem
   `initialize` (nada de caminho presumido);
4. `XAU_MT5_AUTOSTART=0` -> nao abre nada;
5. a trava de 45 s impede uma janela por requisicao.

Prova negativa: os casos 2 e 3 rodam o mesmo `_ensure_mt5`; o que muda e a
existencia do caminho. Se o codigo presumisse um caminho padrao, o caso 3
passaria a abrir terminal e o teste reprovaria.
"""
from __future__ import annotations

import importlib
import sys

import pytest

_gateway = importlib.import_module("backend.mt5_gateway")


class Conta:
    def __init__(self, login: int = 113568614, server: str = "MetaQuotes-Demo") -> None:
        self.login = login
        self.server = server


class FakeMT5:
    def __init__(self, ok: bool = True, conta: Conta | None = None) -> None:
        self.ok = ok
        self.conta = conta
        self.initialize_calls: list[dict] = []
        self.shutdown_calls = 0

    def initialize(self, **kwargs):
        self.initialize_calls.append(dict(kwargs))
        if not self.ok:
            return False
        if "login" in kwargs and self.conta is None:
            self.conta = Conta(kwargs["login"], kwargs.get("server", ""))
        return True

    def account_info(self):
        return self.conta

    def shutdown(self):
        self.shutdown_calls += 1

    def terminal_info(self):
        return None


@pytest.fixture(autouse=True)
def _sem_efeito_colateral(monkeypatch):
    monkeypatch.setattr(_gateway, "_TERMINAL_LAST_START", 0.0)
    monkeypatch.setattr(_gateway, "_TERMINAL_START_TIMEOUT", 0.01)
    monkeypatch.setattr(_gateway.intent_log, "reconcile", lambda _m: {})
    monkeypatch.setattr(_gateway.watchdog, "record", lambda *_a, **_k: None)
    monkeypatch.setattr(_gateway.watchdog, "snapshot_metrics", lambda *_a, **_k: {})
    monkeypatch.delenv("XAU_MT5_AUTOSTART", raising=False)
    monkeypatch.delenv("XAU_MT5_TERMINAL", raising=False)


class TestTerminalJaAberto:
    def test_nao_abre_outra_janela(self, monkeypatch):
        fake = FakeMT5()
        popen: list[list[str]] = []
        monkeypatch.setattr(_gateway, "_mt5", lambda: fake)
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: True)
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: r"C:\MT5\terminal64.exe")
        monkeypatch.setattr(_gateway.subprocess, "Popen", lambda *a, **k: popen.append(a[0]))

        assert _gateway._ensure_mt5() is True
        assert popen == []
        assert fake.initialize_calls == [{"path": r"C:\MT5\terminal64.exe"}]


class TestTerminalFechado:
    def test_abre_uma_vez_e_conecta(self, monkeypatch):
        fake = FakeMT5()
        vivo = {"valor": False}
        popen: list[list[str]] = []
        caminho = r"C:\Program Files\MetaTrader 5\terminal64.exe"

        def abrir(argv, **_kwargs):
            popen.append(argv)
            vivo["valor"] = True

        monkeypatch.setattr(_gateway, "_mt5", lambda: fake)
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: vivo["valor"])
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: caminho)
        monkeypatch.setattr(_gateway.subprocess, "Popen", abrir)

        assert _gateway._ensure_mt5() is True
        assert popen == [[caminho]]
        assert fake.initialize_calls == [{"path": caminho}]

    def test_sem_caminho_recusa_sem_presumir(self, monkeypatch):
        fake = FakeMT5()
        popen: list[list[str]] = []
        monkeypatch.setattr(_gateway, "_mt5", lambda: fake)
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: False)
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: None)
        monkeypatch.setattr(_gateway.subprocess, "Popen", lambda *a, **k: popen.append(a[0]))

        assert _gateway._ensure_mt5() is False
        assert popen == []
        assert fake.initialize_calls == []


class TestDesligado:
    def test_autostart_desligado_nao_abre(self, monkeypatch):
        fake = FakeMT5()
        popen: list[list[str]] = []
        monkeypatch.setenv("XAU_MT5_AUTOSTART", "0")
        monkeypatch.setattr(_gateway, "_mt5", lambda: fake)
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: False)
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: r"C:\MT5\terminal64.exe")
        monkeypatch.setattr(_gateway.subprocess, "Popen", lambda *a, **k: popen.append(a[0]))

        assert _gateway._ensure_mt5() is False
        assert popen == []
        assert fake.initialize_calls == []


class TestTravaDeIntervalo:
    def test_duas_chamadas_seguidas_abrem_uma_janela(self, monkeypatch):
        popen: list[list[str]] = []
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: False)
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: r"C:\MT5\terminal64.exe")
        monkeypatch.setattr(_gateway.subprocess, "Popen", lambda *a, **k: popen.append(a[0]))

        assert _gateway._start_terminal() is False
        assert _gateway._start_terminal() is False
        assert len(popen) == 1


class TestCaminhoConfigurado:
    def test_env_so_vale_se_o_arquivo_existe(self, monkeypatch, tmp_path):
        alvo = tmp_path / "terminal64.exe"
        monkeypatch.setenv("XAU_MT5_TERMINAL", str(alvo))
        assert _gateway._terminal_path() is None

        alvo.write_bytes(b"")
        assert _gateway._terminal_path() == str(alvo)

    def test_padrao_ligado_e_desligado_por_env(self, monkeypatch):
        assert _gateway._terminal_autostart_enabled() is True
        monkeypatch.setenv("XAU_MT5_AUTOSTART", "nao")
        assert _gateway._terminal_autostart_enabled() is False


class TestLoginAutomatico:
    def test_credencial_do_ambiente_faz_login(self, monkeypatch, capsys):
        fake = FakeMT5(conta=None)
        monkeypatch.setattr(_gateway, "_mt5", lambda: fake)
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: True)
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: r"C:\MT5\terminal64.exe")
        monkeypatch.setenv("XAU_MT5_LOGIN", "123456")
        monkeypatch.setenv("XAU_MT5_PASSWORD", "segredo-de-teste")
        monkeypatch.setenv("XAU_MT5_SERVER", "Broker-Demo")

        assert _gateway._ensure_mt5() is True
        assert fake.initialize_calls == [
            {"path": r"C:\MT5\terminal64.exe"},
            {
                "login": 123456,
                "password": "segredo-de-teste",
                "server": "Broker-Demo",
                "path": r"C:\MT5\terminal64.exe",
            },
        ]
        assert fake.shutdown_calls == 1
        assert "segredo-de-teste" not in capsys.readouterr().out

    def test_sessao_certa_nao_reloga(self, monkeypatch):
        fake = FakeMT5(conta=Conta(123456, "Broker-Demo"))
        monkeypatch.setattr(_gateway, "_mt5", lambda: fake)
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: True)
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: r"C:\MT5\terminal64.exe")
        monkeypatch.setenv("XAU_MT5_LOGIN", "123456")
        monkeypatch.setenv("XAU_MT5_PASSWORD", "segredo")
        monkeypatch.setenv("XAU_MT5_SERVER", "Broker-Demo")

        assert _gateway._ensure_mt5() is True
        assert fake.initialize_calls == [{"path": r"C:\MT5\terminal64.exe"}]
        assert fake.shutdown_calls == 0

    def test_credencial_incompleta_nao_reloga(self, monkeypatch):
        fake = FakeMT5(conta=Conta(999, "Outro-Server"))
        monkeypatch.setattr(_gateway, "_mt5", lambda: fake)
        monkeypatch.setattr(_gateway, "_terminal_running", lambda: True)
        monkeypatch.setattr(_gateway, "_terminal_path", lambda: r"C:\MT5\terminal64.exe")
        monkeypatch.setenv("XAU_MT5_LOGIN", "123456")
        monkeypatch.delenv("XAU_MT5_PASSWORD", raising=False)
        monkeypatch.setenv("XAU_MT5_SERVER", "Broker-Demo")

        assert _gateway._ensure_mt5() is True
        assert fake.initialize_calls == [{"path": r"C:\MT5\terminal64.exe"}]
        assert fake.shutdown_calls == 0

    def test_status_nunca_devolve_senha(self, monkeypatch):
        monkeypatch.setenv("XAU_MT5_LOGIN", "123456")
        monkeypatch.setenv("XAU_MT5_PASSWORD", "segredo")
        monkeypatch.setenv("XAU_MT5_SERVER", "Broker-Demo")
        status = _gateway._auto_login_status()
        assert status["configured"] is True
        assert status["login"] == 123456
        assert "password" not in status


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI e API do Windows")
class TestArquivoDpapi:
    def test_grava_cifrado_e_le_de_volta(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        status = _gateway._save_auto_login(
            {"login": "123456", "password": "segredo-de-teste", "server": "Broker-Demo"}
        )
        assert status["configured"] is True
        assert status["source"] == "file"
        bruto = _gateway._auto_login_file().read_text(encoding="utf-8")
        assert "segredo-de-teste" not in bruto
        assert _gateway._auto_login_credentials() == {
            "login": 123456,
            "password": "segredo-de-teste",
            "server": "Broker-Demo",
        }

    def test_clear_remove_o_arquivo(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        _gateway._save_auto_login(
            {"login": "1", "password": "x", "server": "S"}
        )
        status = _gateway._save_auto_login({"clear": True})
        assert status["configured"] is False
        assert not _gateway._auto_login_file().exists()
