# -*- coding: utf-8 -*-
"""Testes da gestao de Expert Advisors (backend/ea_manager.py).

O ponto nao e so listar arquivos: e NAO prometer que o app roda EAs, porque o
MT5 nao executa EA via API Python. Se um dia alguem reintroduzir "start EA"
aqui, estes testes falham.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend import ea_manager as em


class _ArquivoFake:
    """Substituto de Path.stat() para os testes de inventario."""

    def __init__(self, tamanho: int = 1024, mtime: int = 1_700_000_000):
        self.st_size = tamanho
        self.st_mtime = mtime


class _FakeWatchdog:
    """Dublê do modulo backend.watchdog.

    `_heartbeat` usa `from backend import watchdog` e chama `watchdog.ea_state()`.
    Injetar um objeto assim no atributo do pacote substitui o modulo inteiro,
    independente de qual watcher real ja foi importado antes neste processo.
    """

    def __init__(self, ea_state):
        self.ea_state = ea_state


@pytest.fixture()
def experts_fake(tmp_path: Path, monkeypatch) -> Path:
    """Cria uma pasta MQL5/Experts com .ex5 e .mq5/.mqh reais."""
    experts = tmp_path / "MQL5" / "Experts"
    (experts / "Advisors").mkdir(parents=True)
    (experts / "Advisors" / "MeuBot.ex5").write_bytes(b"\x00" * 512)
    (experts / "Advisors" / "MeuBot.mq5").write_text("// fonte", encoding="utf-8")
    (experts / "SoFonte.mq4").write_text("// legado", encoding="utf-8")
    (experts / "Include.mqh").write_text("// header", encoding="utf-8")
    (experts / "leia-me.txt").write_text("nao e EA", encoding="utf-8")
    (experts / "Outro.ex5").write_bytes(b"\x01" * 256)
    monkeypatch.setattr(em, "_terminal_data_dir", lambda: tmp_path)
    return experts


class TestExtensoes:
    def test_somente_ex5_e_executavel(self):
        """Fonte (.mq5/.mq4) exige compilacao no MetaEditor, que o app nao faz."""
        assert em.EXTENSOES_EXECUTAVEIS == {".ex5"}

    def test_fonte_nao_e_marcada_como_executavel(self, experts_fake):
        r = em.listar_eas_instalados()
        por_nome = {e["arquivo"]: e for e in r["experts"]}
        assert por_nome["Advisors/MeuBot.ex5"]["executavel"] is True
        assert por_nome["Advisors/MeuBot.mq5"]["executavel"] is False
        assert por_nome["SoFonte.mq4"]["executavel"] is False
        assert por_nome["Include.mqh"]["executavel"] is False


class TestInventario:
    def test_ignora_arquivo_nao_related(self, experts_fake):
        r = em.listar_eas_instalados()
        assert not any("leia-me" in e["arquivo"] for e in r["experts"])

    def test_conta_executaveis_e_fontes(self, experts_fake):
        r = em.listar_eas_instalados()
        assert r["ok"] is True
        # MeuBot.ex5 e Outro.ex5 = 2 executaveis
        assert r["executaveis"] == 2
        # MeuBot.mq5, SoFonte.mq4, Include.mqh = 3 so fonte
        assert r["apenas_fonte"] == 3
        assert r["count"] == 5

    def test_registra_hash_e_data_reais(self, experts_fake):
        r = em.listar_eas_instalados()
        bot = next(e for e in r["experts"] if e["arquivo"] == "Advisors/MeuBot.ex5")
        assert bot["bytes"] == 512
        assert len(bot["hash_sha256_16"]) == 16
        assert bot["modificado_em"].startswith("20")

    def test_detecta_codigo_fonte_irmao(self, experts_fake):
        r = em.listar_eas_instalados()
        bot = next(e for e in r["experts"] if e["arquivo"] == "Advisors/MeuBot.ex5")
        assert bot["tem_codigo_fonte"] is True, "o .mq5 irmao do .ex5 existe"

    def test_pasta_inexistente_nao_explode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(em, "_terminal_data_dir", lambda: tmp_path)
        r = em.listar_eas_instalados()
        assert r["ok"] is False
        assert r["status"] == "pasta_inexistente"
        assert r["experts"] == []

    def test_terminal_nao_localizado_e_honesto(self, monkeypatch):
        monkeypatch.setattr(em, "_terminal_data_dir", lambda: None)
        r = em.listar_eas_instalados()
        assert r["ok"] is False
        assert r["status"] == "terminal_nao_localizado"
        assert r["count"] == 0


class TestSomenteLeitura:
    def test_nunca_anuncia_comando_ou_execucao(self, experts_fake):
        r = em.listar_eas_instalados()
        assert r["read_only"] is True
        assert r["commands_enabled"] is False
        assert r["control_supported"] is False

    def test_nao_expoe_funcao_de_execucao_de_ea(self):
        """MT5 nao roda EA via API. Se alguem adicionar start/stop, falha aqui."""
        proibidos = [n for n in dir(em) if any(
            n.lower().startswith(p) for p in
            ("start_ea", "run_ea", "exec_ea", "attach_", "compile_ea", "stop_ea")
        )]
        assert proibidos == [], f"modulo expoe controle de EA: {proibidos}"

    def test_status_explica_que_instalado_nao_e_executando(self, experts_fake, monkeypatch):
        monkeypatch.setattr(em, "_heartbeat", lambda: {"state": "alive"})
        monkeypatch.setattr(em, "_ea_no_journal", lambda nome, limite=400: {
            "presente": False, "ocorrencias": 0, "ultima": None})
        r = em.status_eas(com_journal=False)
        assert "anexado a um grafico" in r["nota"]


class TestEstadoHonesto:
    def test_heartbeat_alive_sem_identificar_nao_diz_vivo(self, experts_fake, monkeypatch):
        """Sem sinal proprio do EA, o estado e desconhecido — nunca 'vivo'."""
        monkeypatch.setattr(em, "_heartbeat", lambda: {"state": "alive"})
        monkeypatch.setattr(em, "_ea_no_journal", lambda nome, limite=400: {
            "presente": False, "ocorrencias": 0, "ultima": None})
        r = em.status_eas(com_journal=False)
        estados = {e["estado"] for e in r["detalhado"]}
        assert "vivo" not in estados
        assert "heartbeat_sem_identificar" in estados

    def test_sinal_proprio_diz_vivo(self, experts_fake, monkeypatch):
        # com_journal=True para que o sinal injetado em _ea_no_journal seja
        # realmente consultado. Com com_journal=False o status e
        # deliberadamente "sem_sinal" — nao ha leitura de journal.
        monkeypatch.setattr(em, "_heartbeat", lambda: {"state": "alive"})
        monkeypatch.setattr(em, "_ea_no_journal", lambda nome, limite=400: {
            "presente": True, "ocorrencias": 3, "ultima": "MeuBot started"})
        r = em.status_eas(com_journal=True)
        assert all(e["estado"] == "vivo" for e in r["detalhado"])

    def test_heartbeat_stale_marca_sem_sinal(self, experts_fake, monkeypatch):
        monkeypatch.setattr(em, "_heartbeat", lambda: {"state": "stale"})
        monkeypatch.setattr(em, "_ea_no_journal", lambda nome, limite=400: {
            "presente": False, "ocorrencias": 0, "ultima": None})
        r = em.status_eas(com_journal=True)
        assert all(e["estado"] == "sem_sinal" for e in r["detalhado"])

    def test_apenas_executaveis_entram_no_detalhado(self, experts_fake, monkeypatch):
        monkeypatch.setattr(em, "_heartbeat", lambda: {"state": "stale"})
        monkeypatch.setattr(em, "_ea_no_journal", lambda nome, limite=400: {
            "presente": False, "ocorrencias": 0, "ultima": None})
        r = em.status_eas(com_journal=True)
        assert all(e["extensao"] == ".ex5" for e in r["detalhado"])
        assert len(r["detalhado"]) == 2

    def test_sem_leitura_de_journal_nao_declara_vivo(self, experts_fake, monkeypatch):
        """com_journal=False nao pode afirmar que um EA esta vivo."""
        monkeypatch.setattr(em, "_heartbeat", lambda: {"state": "alive"})
        r = em.status_eas(com_journal=False)
        assert all(e["estado"] != "vivo" for e in r["detalhado"])


class TestJournal:
    def test_heartbeat_que_lanca_nao_quebra(self, monkeypatch):
        """watchdog indisponivel -> dicionario vazio, nunca excecao.

        `_heartbeat` faz `from backend import watchdog`, que resolve o ATRIBUTO
        do pacote `backend` antes do sys.modules. Por isso o patch precisa ir
        em `backend.watchdog` (setattr), e nao so em sys.modules.
        """
        import backend

        def _ea_state_que_lança():
            raise RuntimeError("sem MT5")

        monkeypatch.setattr(backend, "watchdog", _FakeWatchdog(_ea_state_que_lança), raising=False)
        assert em._heartbeat() == {}

    def test_heartbeat_que_nao_e_dict_vira_vazio(self, monkeypatch):
        import backend

        monkeypatch.setattr(backend, "watchdog", _FakeWatchdog(lambda: None), raising=False)
        assert em._heartbeat() == {}

    def test_heartbeat_valido_passa_atraves(self, monkeypatch):
        import backend

        monkeypatch.setattr(backend, "watchdog", _FakeWatchdog(lambda: {"state": "alive"}), raising=False)
        assert em._heartbeat() == {"state": "alive"}

    def test_journal_indisponivel_nao_quebra(self, monkeypatch):
        def _lança(limite: int = 400):
            raise RuntimeError("sem journal")
        monkeypatch.setattr(em, "_journal_lines", _lança, raising=False)
        r = em._ea_no_journal("MeuBot")
        assert r["presente"] is False
        assert r["ocorrencias"] == 0
