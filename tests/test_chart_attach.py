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

# Capturada no import, antes de qualquer fixture trocar o atributo por duble.
# Ver o comentario de test_anexar_recusa_com_terminal_vivo_detectado.
TERMINAL_ABERTO_REAL = ca.terminal_aberto

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


# -------------------------------------------------------------------cirurgico


class TestDefinirInputPreservaTodoOMais:
    """MEDIDO 08/10/2026: 11 graficos com `expertmode=37` e 13 com `5`.

    `anexar_ea` so escreve 4 ou 5, entao usá-lo nesses graficos reescreveria 37
    como 5. `definir_input_ea` troca SO a linha do input.
    """

    def _com_expertmode(self, grafico, modo):
        bruto = grafico.read_bytes().decode("utf-16")
        bruto = bruto.replace("expertmode=5", f"expertmode={modo}")
        grafico.write_bytes(bruto.encode("utf-16"))

    def test_troca_o_valor(self, terminal_fake, monkeypatch):
        # O fixture tem MaxSpread, nao MinFreeMargin: usar uma chave que existe
        # e exercitar a substituicao de verdade.
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        r = ca.definir_input_ea(terminal_fake, "MaxSpread", "10.0")
        assert r["ok"] is True
        assert r["antes"] == "MaxSpread=50.0"
        assert r["depois"] == "10.0"
        assert r["acao"] == "substituido"
        entradas = ca.ler_grafico(terminal_fake)["inputs"]
        assert entradas["MaxSpread"] == "10.0"

    def test_preserva_expertmode_37(self, terminal_fake, monkeypatch):
        """O caso que motivou a funcao: 37 nao pode virar 5."""
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        self._com_expertmode(terminal_fake, 37)
        r = ca.definir_input_ea(terminal_fake, "MinFreeMargin", "10.0")
        assert r["ok"] is True
        assert ca.ler_grafico(terminal_fake)["expert"]["expertmode"] == "37"

    def test_preserva_os_outros_inputs(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        antes = ca.ler_grafico(terminal_fake)["inputs"]
        ca.definir_input_ea(terminal_fake, "MaxSpread", "10.0")
        depois = ca.ler_grafico(terminal_fake)["inputs"]
        assert depois["MagicNumber"] == antes["MagicNumber"], "perdeu o magic"
        assert depois["AutoTrade"] == antes["AutoTrade"], "perdeu o AutoTrade"
        assert depois["LotSize"] == antes["LotSize"], "perdeu o lote"
        assert len(depois) == len(antes), "criou ou removeu input"

    def test_preserva_simbolo_e_timeframe(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        antes = ca.ler_grafico(terminal_fake)
        ca.definir_input_ea(terminal_fake, "MinFreeMargin", "10.0")
        depois = ca.ler_grafico(terminal_fake)
        assert depois["symbol"] == antes["symbol"] == "XAUUSD"
        assert depois["period_size"] == antes["period_size"]

    def test_chave_ausente_e_incluida(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        r = ca.definir_input_ea(terminal_fake, "ChaveNova", "7")
        assert r["acao"] == "incluido"
        assert ca.ler_grafico(terminal_fake)["inputs"]["ChaveNova"] == "7"

    def test_valor_com_barra_invertida_nao_vira_escape(self, terminal_fake, monkeypatch):
        """`re.sub` com string trataria `\\1` como backreference e comeria o resto."""
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        r = ca.definir_input_ea(terminal_fake, "Caminho", r"Experts\XAU_AI_PRO\a.ex5")
        assert r["ok"] is True
        assert ca.ler_grafico(terminal_fake)["inputs"]["Caminho"] == r"Experts\XAU_AI_PRO\a.ex5"

    def test_sem_permissao_recusa(self, terminal_fake, monkeypatch):
        monkeypatch.delenv(ca.VARIAVEL_PERMITE_ESCRITA, raising=False)
        antes = terminal_fake.read_bytes()
        r = ca.definir_input_ea(terminal_fake, "MinFreeMargin", "10.0")
        assert r["ok"] is False
        assert r["read_only"] is True
        assert terminal_fake.read_bytes() == antes

    def test_com_terminal_aberto_recusa(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: True)
        antes = terminal_fake.read_bytes()
        r = ca.definir_input_ea(terminal_fake, "MinFreeMargin", "10.0")
        assert r["ok"] is False
        assert r["terminal_aberto"] is True
        assert terminal_fake.read_bytes() == antes

    def test_grafico_sem_ea_recusa(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        vazio = tmp_path / "vazio.chr"
        vazio.write_bytes(b"\xff\xfe" + "?<chart>\r\nsymbol=XAUUSD\r\n</chart>\r\n".encode("utf-16"))
        r = ca.definir_input_ea(vazio, "MinFreeMargin", "10.0")
        assert r["ok"] is False

    def test_cria_backup(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: False)
        antes = terminal_fake.read_bytes()
        r = ca.definir_input_ea(terminal_fake, "MinFreeMargin", "10.0")
        assert Path(r["backup"]).exists()
        assert Path(r["backup"]).read_bytes() == antes


class TestTerminalAbertoRecusa:
    def test_terminal_aberto_nao_altera_arquivo(self, terminal_fake, monkeypatch):
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", lambda: True)
        antes = terminal_fake.read_bytes()
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        assert r["ok"] is False
        assert r["terminal_aberto"] is True
        assert terminal_fake.read_bytes() == antes, "escreveu com terminal aberto"


# ------------------------------------------------------------------ deteccao
#
# MEDIDO em 08/10/2026: `terminal64.exe` PID 12860 rodando desde 13:59 e
# ZERO arquivos `lock*` na pasta de dados. A guarda so de `lock*` devolvia
# `False` com o terminal ABERTO, e `anexar_ea` gravava num terminal que
# descarta o `.chr` ao sair. Os testes abaixo exercitam a DETECCAO de verdade;
# os de cima fazem `monkeypatch` dela e por isso nunca pegariam esse defeito.


class TestDeteccaoDeTerminalAberto:
    def test_lock_detecta(self, tmp_path, monkeypatch):
        root = tmp_path / "TERMINAL"
        # O glob de producao e `root.glob("*/lock*")`: UM nivel de diretorio.
        (root / "sub").mkdir(parents=True)
        (root / "sub" / "lock").write_text("x")
        assert list(root.glob("*/lock*")), "pre-condicao do teste furada"
        monkeypatch.setattr(ca, "_terminal_root", lambda: root)
        monkeypatch.setattr(ca, "_processo_rodando", lambda nome: False)
        assert ca.terminal_aberto() is True

    def test_processo_detecta_mesmo_sem_lock(self, tmp_path, monkeypatch):
        """O caso que quebrava: terminal vivo e ZERO `lock*`."""
        root = tmp_path / "TERMINAL"
        (root / "MQL5").mkdir(parents=True)
        assert list(root.glob("*/lock*")) == [], "pre-condicao do teste furada"
        monkeypatch.setattr(ca, "_terminal_root", lambda: root)
        monkeypatch.setattr(ca, "_processo_rodando", lambda nome: nome == "terminal64.exe")
        assert ca.terminal_aberto() is True, "terminal vivo nao detectado sem lock"

    def test_sem_lock_e_sem_processo_da_fechado(self, tmp_path, monkeypatch):
        root = tmp_path / "TERMINAL"
        (root / "MQL5").mkdir(parents=True)
        monkeypatch.setattr(ca, "_terminal_root", lambda: root)
        monkeypatch.setattr(ca, "_processo_rodando", lambda nome: False)
        assert ca.terminal_aberto() is False

    def test_sem_raiz_ainda_assim_olha_o_processo(self, monkeypatch):
        """Falhar aberto e o pior jeito de falhar: sem raiz, `False` na corrida."""
        monkeypatch.setattr(ca, "_terminal_root", lambda: None)
        monkeypatch.setattr(ca, "_processo_rodando", lambda nome: True)
        assert ca.terminal_aberto() is True

    def test_anexar_recusa_com_terminal_vivo_detectado(self, terminal_fake, monkeypatch):
        """Prova negativa: o caminho inteiro tem de recusar e NAO tocar o .chr.

        Cuidado que custou um teste vermelho: o fixture ja trocou
        `ca.terminal_aberto` por `lambda: False`, entao `ca.terminal_aberto`
        aqui seria o DUBLE e nao a funcao real — instalar isso seria o teste
        validando a si mesmo. Por isso a funcao real e capturada no import.
        """
        monkeypatch.setenv(ca.VARIAVEL_PERMITE_ESCRITA, "1")
        monkeypatch.setattr(ca, "terminal_aberto", TERMINAL_ABERTO_REAL)
        monkeypatch.setattr(ca, "_processo_rodando", lambda nome: True)
        antes = terminal_fake.read_bytes()
        r = ca.anexar_ea(terminal_fake, "XAU_AI_PRO", "Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5", {})
        assert r["ok"] is False
        assert r["terminal_aberto"] is True
        assert terminal_fake.read_bytes() == antes, "gravar com terminal vivo"


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
