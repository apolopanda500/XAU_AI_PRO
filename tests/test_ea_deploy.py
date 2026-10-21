# -*- coding: utf-8 -*-
"""Testes do deploy do `.ex5` (backend/ea_deploy.py).

O defeito que estes testes existem para pegar: compilar o EA no MetaEditor gera
o `.ex5` AO LADO, no REPO, e o grafico so carrega EA de `MQL5/Experts` do
TERMINAL. Nada copiava um para o outro — MEDIDO em 11/10/2026, um EA defasado
operando a conta real 391773676 (1132 vendas de EURUSD no journal de domingo).
Reanexar o EA NAO resolve: reanexar recarrega o `.ex5` velho que ja estava la.

Duas coisas que estes testes provam, e que a medicao sozinha nao prova:

  1. que `sincronizar_ex5` realmente copia (prova POSITIVA) e so copia o `.ex5`;
  2. que, SEM `XAU_ALLOW_EA_DEPLOY=1`, ele NAO copia (prova NEGATIVA — regra
     §6: uma trava que so passa nao prova que a guarda funciona).

Nada aqui toca no terminal real: origem e destino sao `tmp_path`, e
`_terminal_root` e monkeypatchado. Nenhuma conta, nenhuma ordem.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend import ea_deploy as dep


@pytest.fixture()
def repo_e_terminal(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    """Cria um `.ex5` de origem (repo) e um destino (terminal) defasado.

    Sao dois arquivos com conteudo diferente, de proposito: e a situacao medida
    em 11/10 (repo fresco, terminal 2 dias atras).
    """
    monkeypatch.delenv(dep.VARIAVEL_PERMITE_DEPLOY, raising=False)

    origem = tmp_path / "repo" / "XAU_AI_PRO.ex5"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"BINARIO-NOVO-DO-REPO" * 100)

    terminal_root = tmp_path / "terminal"
    destino = terminal_root / "MQL5" / "Experts" / "XAU_AI_PRO" / "XAU_AI_PRO.ex5"
    destino.parent.mkdir(parents=True)
    destino.write_bytes(b"BINARIO-VELHO-DO-TERMINAL" * 100)

    monkeypatch.setattr(dep, "_repo_ex5", lambda: origem)
    monkeypatch.setattr(dep, "_terminal_ex5", lambda: destino)
    return origem, destino


class TestEstadoDeploy:
    def test_detecta_defasado_por_hash_nao_por_data(self, repo_e_terminal):
        """Dois binarios diferentes => defasado, mesmo com datas proximas."""
        est = dep.estado_deploy()
        assert est["situacao"] == "defasado"
        assert est["defasado"] is True
        assert est["origem"]["hash"] != est["destino"]["hash"]

    def test_atualizado_quando_os_hashes_batem(self, tmp_path, monkeypatch):
        origem = tmp_path / "o.ex5"
        destino = tmp_path / "d.ex5"
        origem.write_bytes(b"MESMO-CONTEUDO" * 50)
        destino.write_bytes(b"MESMO-CONTEUDO" * 50)
        est = dep.estado_deploy(origem, destino)
        assert est["situacao"] == "atualizado"
        assert est["defasado"] is False

    def test_terminal_sem_binario_conta_como_defasado(self, tmp_path):
        origem = tmp_path / "o.ex5"
        origem.write_bytes(b"CONTEUDO")
        falta = tmp_path / "nao-existe" / "d.ex5"
        est = dep.estado_deploy(origem, falta)
        assert est["situacao"] == "terminal_sem_binario"
        assert est["defasado"] is True

    def test_sem_binario_no_repo_nao_e_defasado_e_avisa(self, tmp_path):
        falta = tmp_path / "sem-repo" / "o.ex5"
        destino = tmp_path / "d.ex5"
        destino.write_bytes(b"algo")
        est = dep.estado_deploy(falta, destino)
        assert est["ok"] is False
        assert est["situacao"] == "sem_binario_no_repo"
        assert est["defasado"] is False

    def test_o_aviso_de_reanexar_esta_presente(self, repo_e_terminal):
        """O modulo nao pode fingir que copiar basta — tem de avisar do reanexar."""
        est = dep.estado_deploy()
        assert "REANEXAR" in est["aviso"].upper()


class TestProvaNegativa:
    """Regra §6: a trava tem de reprovar quando DEVE reprovar."""

    def test_sem_a_variavel_nao_copia(self, repo_e_terminal, monkeypatch):
        monkeypatch.delenv(dep.VARIAVEL_PERMITE_DEPLOY, raising=False)
        _, destino = repo_e_terminal
        antes = destino.read_bytes()
        r = dep.sincronizar_ex5(aplicar=True)
        assert r["acao"] == "sem_autorizacao"
        # O destino NAO mudou: sem a variavel, e leitura.
        assert destino.read_bytes() == antes

    def test_com_a_variavel_em_outro_valor_nao_copia(self, repo_e_terminal, monkeypatch):
        monkeypatch.setenv(dep.VARIAVEL_PERMITE_DEPLOY, "0")
        _, destino = repo_e_terminal
        antes = destino.read_bytes()
        r = dep.sincronizar_ex5(aplicar=True)
        assert r["acao"] == "sem_autorizacao"
        assert destino.read_bytes() == antes

    def test_dry_run_nao_copia_mesmo_com_a_variavel(self, repo_e_terminal, monkeypatch):
        monkeypatch.setenv(dep.VARIAVEL_PERMITE_DEPLOY, "1")
        _, destino = repo_e_terminal
        antes = destino.read_bytes()
        r = dep.sincronizar_ex5(aplicar=False)
        assert r["acao"] == "dry_run"
        assert destino.read_bytes() == antes


class TestProvaPositiva:
    """Com a variavel, copia de verdade — e so o .ex5."""

    def test_copia_e_o_hash_passa_a_bater(self, repo_e_terminal, monkeypatch, tmp_path):
        monkeypatch.setenv(dep.VARIAVEL_PERMITE_DEPLOY, "1")
        origem, destino = repo_e_terminal
        r = dep.sincronizar_ex5(aplicar=True, backup_dir=tmp_path / "bkp")
        assert r["acao"] == "copiado"
        assert r["hash_confere"] is True
        assert destino.read_bytes() == origem.read_bytes()
        assert dep.estado_deploy()["situacao"] == "atualizado"

    def test_grava_backup_do_destino_antes_de_sobrescrever(
        self, repo_e_terminal, monkeypatch, tmp_path
    ):
        monkeypatch.setenv(dep.VARIAVEL_PERMITE_DEPLOY, "1")
        _, destino = repo_e_terminal
        conteudo_velho = destino.read_bytes()
        bkp = tmp_path / "bkp"
        r = dep.sincronizar_ex5(aplicar=True, backup_dir=bkp)
        assert r["acao"] == "copiado"
        assert r["backup"] is not None
        # O backup guardou o binario VELHO do terminal, nao o novo.
        assert Path(r["backup"]).read_bytes() == conteudo_velho

    def test_idempotente_nao_copia_de_novo(self, repo_e_terminal, monkeypatch, tmp_path):
        monkeypatch.setenv(dep.VARIAVEL_PERMITE_DEPLOY, "1")
        dep.sincronizar_ex5(aplicar=True, backup_dir=tmp_path / "bkp")
        segunda = dep.sincronizar_ex5(aplicar=True, backup_dir=tmp_path / "bkp")
        assert segunda["acao"] == "ja_atualizado"

    def test_nunca_escreve_no_repo(self, repo_e_terminal, monkeypatch, tmp_path):
        """A origem e intocavel: so o destino muda."""
        monkeypatch.setenv(dep.VARIAVEL_PERMITE_DEPLOY, "1")
        origem, _ = repo_e_terminal
        mtime_origem = origem.stat().st_mtime
        dep.sincronizar_ex5(aplicar=True, backup_dir=tmp_path / "bkp")
        assert origem.stat().st_mtime == mtime_origem
