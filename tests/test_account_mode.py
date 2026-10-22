"""Modo da conta MT5: DEMO=0, CONTEST=1, REAL=2.

MEDIDO em 21/10/2026 na conta demo `113568614` (servidor `MetaQuotes-Demo`):
`account_info().trade_mode` devolveu `0` e o codigo rotulava isso `REAL`.
O mapa antigo era `{0: "REAL", 1: "DEMO", 2: "CONTEST"}` — invertido.

Estes testes existem para o numero nao voltar a ser escrito a mao.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.account_mode import (
    MODO_NUMERO_PARA_ROTULO,
    TRADE_MODE_CONTEST,
    TRADE_MODE_DEMO,
    TRADE_MODE_REAL,
    conta_e_demo,
    modo_da_conta,
    modo_numero_para_rotulo,
    modo_para_rotulo,
)

ROOT = Path(__file__).resolve().parent.parent


class TestConstantesOficiais:
    def test_valores_padrao_sao_os_do_terminal(self) -> None:
        """Documentacao do terminal: DEMO=0, CONTEST=1, REAL=2."""
        assert (TRADE_MODE_DEMO, TRADE_MODE_CONTEST, TRADE_MODE_REAL) == (0, 1, 2)

    def test_terminal_instalado_confirma(self) -> None:
        """Se o terminal esta aqui, ele e a fonte — e ele concorda."""
        mt5 = pytest.importorskip("MetaTrader5")
        assert mt5.ACCOUNT_TRADE_MODE_DEMO == TRADE_MODE_DEMO
        assert mt5.ACCOUNT_TRADE_MODE_CONTEST == TRADE_MODE_CONTEST
        assert mt5.ACCOUNT_TRADE_MODE_REAL == TRADE_MODE_REAL


class TestTraducao:
    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [(0, "DEMO"), (1, "CONTEST"), (2, "REAL")],
    )
    def test_mapa_numerico(self, valor: int, esperado: str) -> None:
        assert modo_da_conta(valor) == esperado

    def test_conta_demo_medida_nao_vira_real(self) -> None:
        """A prova do defeito: `trade_mode == 0` na conta demo real."""
        conta = SimpleNamespace(login=113568614, server="MetaQuotes-Demo", trade_mode=0)
        assert modo_da_conta(conta.trade_mode) == "DEMO"
        assert conta_e_demo(conta.trade_mode) is True

    def test_conta_real_nao_vira_demo(self) -> None:
        """O inverso do mesmo defeito: `trade_mode == 2` e REAL."""
        assert modo_da_conta(2) == "REAL"
        assert conta_e_demo(2) is False

    def test_contest_nao_e_demo(self) -> None:
        """CONTEST opera dinheiro de verdade em premiacoes."""
        assert modo_da_conta(1) == "CONTEST"
        assert conta_e_demo(1) is False

    def test_ausencia_e_unknown_e_nao_demo(self) -> None:
        assert modo_da_conta(None) == "UNKNOWN"
        assert conta_e_demo(None) is False

    def test_valor_fora_da_faixa_e_unknown(self) -> None:
        assert modo_da_conta(9) == "UNKNOWN"
        assert modo_da_conta(-1) == "UNKNOWN"

    def test_rotulo_em_texto_e_aceito(self) -> None:
        assert modo_da_conta("demo") == "DEMO"
        assert modo_da_conta("REAL") == "REAL"
        assert modo_da_conta("lixo") == "UNKNOWN"

    def test_booleano_nao_e_modo(self) -> None:
        """`True == 1` em Python: sem esta guarda, demo viraria contest."""
        assert modo_da_conta(True) == "UNKNOWN"
        assert modo_da_conta(False) == "UNKNOWN"

    def test_texto_nao_numerico_nao_levanta(self) -> None:
        assert modo_da_conta("xau") == "UNKNOWN"
        assert modo_da_conta(object()) == "UNKNOWN"


class TestMapaDoTerminal:
    def test_mapa_numero_para_rotulo_e_inverso(self) -> None:
        para_rotulo = modo_para_rotulo()
        assert modo_numero_para_rotulo() == {v: k for k, v in para_rotulo.items()}

    def test_mapa_conservador(self) -> None:
        """Um mapa de ida e volta perde informacao quando o terminal muda."""
        for numero, rotulo in modo_numero_para_rotulo().items():
            assert modo_da_conta(numero) == rotulo

    def test_constante_de_import_e_conservadora(self) -> None:
        """O mapa de import tem os tres rotulos, com os tres numeros."""
        assert set(MODO_NUMERO_PARA_ROTULO.values()) == {"DEMO", "CONTEST", "REAL"}
        assert len(MODO_NUMERO_PARA_ROTULO) == 3


class TestDubleDeTerminalInjetado:
    """O terminal pode ser injetado DEPOIS do import do modulo.

    E o que os testes do gateway fazem (`sys.modules["MetaTrader5"]`). Um mapa
    fixado no import congelaria o valor antigo e passaria a mentir.
    """

    def test_terminal_injetado_muda_o_mapa(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import types

        fake = types.ModuleType("MetaTrader5")
        fake.ACCOUNT_TRADE_MODE_DEMO = 7
        fake.ACCOUNT_TRADE_MODE_CONTEST = 8
        fake.ACCOUNT_TRADE_MODE_REAL = 9
        monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
        assert modo_da_conta(7) == "DEMO"
        assert modo_da_conta(9) == "REAL"
        assert modo_da_conta(0) == "UNKNOWN"

    def test_terminal_ausente_usa_o_padrao_documentado(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "MetaTrader5", None)
        assert modo_da_conta(0) == "DEMO"
        assert modo_da_conta(2) == "REAL"



class TestSnapshotDoTerceiroEAPublicaOModoCerto:
    """O snapshot do EA de terceiro e o que a tela mostra: ele tem de dizer DEMO."""

    def _mt5_demo(self):
        class _Conta:
            login = 113568614
            server = "MetaQuotes-Demo"
            currency = "USD"
            trade_mode = 0

        return SimpleNamespace(
            account_info=lambda: _Conta(),
            positions_get=lambda: [],
            orders_get=lambda: [],
            history_deals_get=lambda *a, **k: [],
        )

    def test_snapshot_demo_preserva_o_numero(self) -> None:
        from backend.third_party_ea import read_mt5_snapshot

        snap = read_mt5_snapshot(self._mt5_demo())
        assert snap["account"]["trade_mode"] == 0

    def test_avaliacao_publica_account_mode_demo(self) -> None:
        from datetime import datetime, timezone

        from backend.third_party_ea import evaluate_adapter, read_mt5_snapshot

        manifest = {
            "adapter_id": "acme-gold-v3",
            "vendor": "ACME",
            "name": "Gold Observer",
            "version": "3.2.1",
            "build": "2026.09",
            "login": 113568614,
            "server": "MetaQuotes-Demo",
            "terminal_id_hash": None,
            "issued_at": "2026-10-21T11:59:30Z",
            "sequence": 42,
            "ttl_seconds": 120,
            "read_only": True,
            "commands_enabled": False,
            "capabilities": ["account", "positions", "orders", "history"],
            "magics": [7001],
            "symbols": ["XAUUSD"],
        }
        agora = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
        resultado = evaluate_adapter(manifest, read_mt5_snapshot(self._mt5_demo()), agora)
        assert resultado["account_mode"] == "DEMO"


class TestNenhumMapaDeModoEscritoAMaoNoCodigo:
    """Trava de REGRESSAO: ninguem escreve o mapa de trade_mode de novo.

    A REGRA e "o rotulo do modo da conta vem de backend.account_mode". A
    trava casa a REGRA - procura um dicionario literal, no codigo, que mapeie
    NUMEROS para os rotulos de modo - e nao a palavra "REAL". Por isso um
    comentario ou docstring que DOCUMENTE o problema nao reprova: o teste le
    a AST, nao o texto bruto.
    """

    ROTULOS = {"DEMO", "CONTEST", "REAL"}

    @staticmethod
    def _e_mapa_de_modo(no) -> bool:
        if not isinstance(no, ast.Dict):
            return False
        chaves = [k.value for k in no.keys if isinstance(k, ast.Constant)]
        valores = [v.value for v in no.values if isinstance(v, ast.Constant)]
        if len(chaves) != len(no.keys) or len(valores) != len(no.values):
            return False
        if not chaves:
            return False
        if not all(isinstance(c, int) and not isinstance(c, bool) for c in chaves):
            return False
        return bool(set(valores) & TestNenhumMapaDeModoEscritoAMaoNoCodigo.ROTULOS)

    def _dicionarios_de_modo(self) -> list[str]:
        achados: list[str] = []
        for arquivo in sorted((ROOT / "backend").rglob("*.py")):
            if arquivo.name == "account_mode.py":
                continue  # a fonte da verdade; ela tem o mapa de proposito
            try:
                arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for no in ast.walk(arvore):
                if self._e_mapa_de_modo(no):
                    achados.append(f"{arquivo.relative_to(ROOT)}:{no.lineno}")
        return achados

    def test_nenhum_mapa_numerico_de_modo_fora_da_fonte(self) -> None:
        achados = self._dicionarios_de_modo()
        assert achados == [], (
            "mapa de modo da conta escrito a mao fora de backend/account_mode.py: "
            + ", ".join(achados)
        )

    def test_a_trava_reprova_quando_o_mapa_volta(self) -> None:
        """PROVA NEGATIVA: a trava precisa reprovar, nao so passar."""
        fonte = "MODO = {0: 'REAL', 1: 'DEMO', 2: 'CONTEST'}"
        arvore = ast.parse(fonte)
        achados = [no.lineno for no in ast.walk(arvore) if self._e_mapa_de_modo(no)]
        assert achados, "a trava deixou de reprovar o mapa invertido"

    def test_nenhum_account_mode_fixo_no_codigo(self) -> None:
        """`"account_mode": "DEMO"` escrito a mao e a mesma divergencia.

        MEDIDO: `mt5_gateway._status()` e `mt5_gateway._ea_command()` devolviam
        `"account_mode": "DEMO"` literal. Numa conta REAL, o gateway
        responderia "DEMO" — e o operador leria que a conta e de teste.

        A trava le a AST e procura o PAR chave `account_mode` com valor
        textual fixo, entao um comentario ou docstring que cite o problema
        nao reprova. E `backend/account_mode.py` fica de fora: la o rotulo
        vem do terminal.
        """
        achados: list[str] = []
        for arquivo in sorted((ROOT / "backend").rglob("*.py")):
            if arquivo.name == "account_mode.py":
                continue
            try:
                arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for no in ast.walk(arvore):
                if not isinstance(no, ast.Dict):
                    continue
                for chave, valor in zip(no.keys, no.values):
                    if not isinstance(chave, ast.Constant) or chave.value != "account_mode":
                        continue
                    if isinstance(valor, ast.Constant) and valor.value in self.ROTULOS:
                        achados.append(f"{arquivo.relative_to(ROOT)}:{valor.lineno}")
        assert achados == [], (
            "account_mode escrito a mao fora de backend/account_mode.py: "
            + ", ".join(achados)
        )

    def test_a_trava_do_account_mode_fixo_reprova(self) -> None:
        """PROVA NEGATIVA da trava acima."""
        fonte = "d = {'account_mode': 'DEMO'}"
        achados = [
            no.lineno
            for no in ast.walk(ast.parse(fonte))
            if isinstance(no, ast.Dict)
            for chave, valor in zip(no.keys, no.values)
            if isinstance(chave, ast.Constant)
            and chave.value == "account_mode"
            and isinstance(valor, ast.Constant)
            and valor.value in self.ROTULOS
        ]
        assert achados, "a trava deixou de reprovar o account_mode fixo"
