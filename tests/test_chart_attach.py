# -*- coding: utf-8 -*-
"""Testes do anexador de EAs a graficos (backend/chart_attach.py).

O formato do MT5 e "XML de contorno": dentro de <expert> e <inputs> o conteudo
sao LINHAS `chave=valor` no text node, nao elementos nem atributos. Ler com
findtext() devolve vazio — foi exatamente o bug que estes testes cobrem.

Nenhum teste escreve em grafico real do terminal: todos usam tmp_path e um
terminal simulado. A regra do projeto (MQL5/Experts intocavel) tambem e
verificada aqui.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend import chart_attach as ca

# Trecho real do chart01.chr deste terminal, preservado para os testes.
# expertmode=5 = ExpertEnable DESLIGADO; AutoTrade=true e a flag do proprio EA.
CHR_REAL = (
    "?<chart>\r\n"
    "id=22884787070177\r\n"
    "symbol=XAUUSD\r\n"
    "description=Gold vs US Dollar\r\n"
    "period_size=5\r\n"
    "<expert>\r\n"
    "name=XAU_AI_PRO\r\n"
    "path=Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5\r\n"
    "expertmode=5\r\n"
    "<inputs>\r\n"
    "AutoTrade=true\r\n"
    "MagicNumber=2026001\r\n"
    "LotSize=0.01\r\n"
    "MaxSpread=50.0\r\n"
    "</inputs>\r\n"
    "</expert>\r\n"
    "<window>\r\n"
    "type=0\r\n"
    "</window>\r\n"
    "</chart>\r\n"
)


@pytest.fixture()
def terminal_fake(tmp_path: Path, monkeypatch) -> Path:
    """Terminal MT5 simulado com um grafico real e um EA compilado."""
    root = tmp_path / "TERMINAL"
    experts = root / "MQL5" / "Experts" / "XAU_AI_PRO"
    experts.mkdir(parents=True)
    (experts / "XAU_AI_PRO.ex5").write_bytes(b"\x00" * 256)
    charts = root / "MQL5" / "Profiles" / "Charts" / "Default"
    charts.mkdir(parents=True)
    grafico = charts / "chart01.chr"
    grafico.write_bytes(CHR_REAL.encode("utf-16"))
    monkeypatch.setattr(ca, "_terminal_root", lambda: root)
    monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
    return grafico


# ------------------------------------------------------------------- leitura


class TestParse:
    def test_parse_linhas_chave_valor(self):
        r = ca._parse_linhas_chave_valor("\nname=Bot\npath=a\\b.ex5\nexpertmode=4\n")
        assert r == {"name": "Bot", "path": "a\\b.ex5", "expertmode": "4"}

    def test_ignora_linha_sem_igual(self):
        r = ca._parse_linhas_chave_valor("nome=Bot\n\nsem_igual\nx=1")
        assert r == {"nome": "Bot", "x": "1"}

    def test_valor_com_igual_e_preservado(self):
        r = ca._parse_linhas_chave_valor("formula=a=b=c")
        assert r["formula"] == "a=b=c"


class TestLeitura:
    def test_le_grafico_real(self, terminal_fake):
        g = ca.ler_grafico(terminal_fake)
        assert g["ok"] is True
        assert g["symbol"] == "XAUUSD"
        assert g["period_size"] == "5"

    def test_le_ea_que_esta_como_texto(self, terminal_fake):
        """O bug coberto aqui: findtext() devolveria vazio neste formato."""
        g = ca.ler_grafico(terminal_fake)
        assert g["expert"]["name"] == "XAU_AI_PRO"
        assert g["expert"]["expertmode"] == "5"
        assert g["expert"]["path"] == "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5"

    def test_le_inputs_do_ea(self, terminal_fake):
        g = ca.ler_grafico(terminal_fake)
        assert g["inputs"]["AutoTrade"] == "true"
        assert g["inputs"]["MagicNumber"] == "2026001"
        assert g["inputs"]["MaxSpread"] == "50.0"

    def test_listar_encontra_o_grafico(self, terminal_fake):
        r = ca.listar_graficos()
        assert r["ok"] is True
        assert r["count"] == 1
        assert r["graficos"][0]["expert"]["name"] == "XAU_AI_PRO"


# ------------------------------------------------------------------ escrita


class TestEscritaExigePermissao:
    def test_sem_variavel_recusa(self, terminal_fake, monkeypatch):
        monkeypatch.delenv(ca.VARIAVEL_PERMITE_ESCRITA, raising=False)
        antes = terminal_fake.read_bytes()
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {"AutoTrade": "true"})
        assert r["ok"] is False
        assert r["read_only"] is True
        assert terminal_fake.read_bytes() == antes, "recusou mas alterou o arquivo"

    def test_variavel_presente_permite(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {"AutoTrade": "true"}, autotrade=True)
        assert r["ok"] is True
        assert r["expertmode"] == ca.EXPERTMODE_AUTOTRADE


class TestTerminalAbertoRecusa:
    def test_terminal_aberto_nao_altera_arquivo(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: True)
        antes = terminal_fake.read_bytes()
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        assert r["ok"] is False
        assert r["terminal_aberto"] is True
        assert terminal_fake.read_bytes() == antes, "escreveu com terminal aberto"


class TestEscrita:
    def test_troca_mode_5_por_4_liga_autotrade(self, terminal_fake, monkeypatch):
        """O achado real: os 13 graficos estavam com mode=5, AutoTrade desligado."""
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5",
                         {"AutoTrade": "true", "MagicNumber": "2026001"}, autotrade=True)
        assert r["ok"] is True
        g = ca.ler_grafico(terminal_fake)
        assert g["expert"]["expertmode"] == "4"

    def test_autotrade_false_mantem_mode_5(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {}, autotrade=False)
        assert ca.ler_grafico(terminal_fake)["expert"]["expertmode"] == "5"

    def test_preserva_simbolo_e_timeframe(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        g = ca.ler_grafico(terminal_fake)
        assert g["symbol"] == "XAUUSD"
        assert g["period_size"] == "5"

    def test_gera_backup(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        assert Path(r["backup"]).exists()
        # O backup tem de ser o conteudo ORIGINAL (mode=5).
        assert ca.ler_grafico(Path(r["backup"]))["expert"]["expertmode"] == "5"

    def test_preserva_codificacao_utf16(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        bruto = terminal_fake.read_bytes()
        assert bruto[:2] in (b"\xff\xfe", b"\xfe\xff"), "perdeu o BOM UTF-16"

    def test_nao_deixa_arquivo_temporario(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        assert not list(terminal_fake.parent.glob("*.tmp"))

    def test_ea_inexistente_recusa(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        antes = terminal_fake.read_bytes()
        r = ca.anexar_ea(terminal_fake, "Fantasma", "Experts\\NaoExiste\\Fantasma.ex5", {})
        assert r["ok"] is False
        assert "nao encontrado" in r["error"]
        assert terminal_fake.read_bytes() == antes


class TestNaoDuplicaExpert:
    def test_reescrever_substitui_em_vez_de_empilhar(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        for _ in range(3):
            ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5",
                         {"AutoTrade": "true"}, autotrade=True)
        bruto = terminal_fake.read_bytes().decode("utf-16")
        assert bruto.count("<expert>") == 1, "duplicou o bloco expert"
        assert ca.ler_grafico(terminal_fake)["expert"]["expertmode"] == "4"

    def test_trocar_de_ea_substitui(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        # chart01.chr -> Default -> Charts -> Profiles -> MQL5. Sao 4 niveis.
        experts = terminal_fake.parents[3] / "Experts" / "OutroBot"
        experts.mkdir(parents=True, exist_ok=True)
        (experts / "OutroBot.ex5").write_bytes(b"\x00" * 64)
        r = ca.anexar_ea(terminal_fake, "OutroBot", "Experts\\OutroBot\\OutroBot.ex5", {})
        assert r["ok"] is True, r.get("error")
        assert ca.ler_grafico(terminal_fake)["expert"]["name"] == "OutroBot"


# ------------------------------------------------ compatibilidade do projeto


class TestRegraDoProjeto:
    def test_nunca_escreve_em_mql5_experts(self, terminal_fake, monkeypatch):
        """A regra do projeto: MQL5/Experts e somente leitura."""
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        experts = terminal_fake.parents[3] / "MQL5" / "Experts"
        antes = {p: p.read_bytes() for p in experts.rglob("*") if p.is_file()}
        ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        depois = {p: p.read_bytes() for p in experts.rglob("*") if p.is_file()}
        assert antes == depois, "o modulo alterou MQL5/Experts"

    def test_gravar_sempre_cria_backup(self, terminal_fake, monkeypatch):
        """Nenhuma escrita de perfil pode ocorrer sem backup correspondente."""
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        assert r.get("backup"), "escrita sem backup"
        assert Path(r["backup"]).exists()

    def test_recusa_ou_avisa_antes_de_sobrescrever(self, terminal_fake, monkeypatch):
        """Se nao ha backup (grafo inexistente), nao escreve."""
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        r = ca.anexar_ea(Path(str(terminal_fake) + "x.chr"), "X", "a\\b.ex5", {})
        assert r["ok"] is False
        assert not list(terminal_fake.parent.glob("*.x.chr"))


class TestAnexarPorNome:
    def test_resolve_perfil_e_grafico(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        r = ca.anexar_ea_por_nome("Default", "chart01.chr", "XAU_AI_PRO",
                                  "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {"AutoTrade": "true"})
        assert r["ok"] is True

    def test_grafico_inexistente_lista_disponiveis(self, terminal_fake, monkeypatch):
        r = ca.anexar_ea_por_nome("Default", "chart99.chr", "X", "a\\b.ex5", {})
        assert r["ok"] is False
        assert "chart01.chr" in r["disponiveis"]
