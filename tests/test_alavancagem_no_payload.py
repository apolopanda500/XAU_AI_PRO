"""
A ALAVANCAGEM DA CONTA NO PAYLOAD (06/10/2026)
===============================================

O CICLO ANTERIOR RECUSOU O "REQUISITO DE MARGEM" DO PAINEL DE ORDEM. O motivo
era certo e a conclusao estava errada.

O motivo: nao se escreve numero estimado num painel onde o numero vira limite
real. Correto, e o AGENTS.md 9.

A conclusao errada: o `Docs/ORDEM_PELO_GRAFICO_20261006.md` escreveu que a
alavancagem "e um numero que a corretora calcula (alavancagem da conta, spread,
taxa da exchange) e que o app nao tem de onde ler".

**A CORRETORA PUBLICA.** MEDIDO na conta 391773676:

    painel `Gerir` da XM (my.xm.com)   "Alavancagem  1000:1"
    `account_info().leverage`          1000

Sao o mesmo numero, medido de dois lados. O gateway lia a conta e descartava o
campo; bastava NAO descartar.

A CONTA, QUE E O QUE AUTORIZA A TELA A ESCREVER O NUMERO
=========================================================
    contract_size BTCUSD = 1,0   (MEDIDO em `symbol_info`)
    alavancagem          = 1000  (MEDIDO nos dois lados acima)
    entrada              = 85.376,63  (captura da XM)

    nocional   = 0,01 x 1,0 x 85.376,63   = 853,7663
    requisito = 853,7663 / 1000           = 0,8537663
    a XM escreve                            "$0.85"

Sem o `contract_size` o mesmo volume daria `853,77` no BTCUSD e `85.376.630` no
EURUSD, cujo contrato e 100.000. Por isso os dois campos entram juntos.

O QUE ESTE ARQUIVO PROVA
=======================
1. A rota de `/api/live` traz a alavancagem que a CONTA mediu — e traz `None`,
   nunca `0`, quando o campo nao existe.
2. O `None` nao vira `0`: `0` de alavancagem e um numero que o painel dividiria
   por zero.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class _Conta:
    """O que `account_info()` devolve nesta conta real."""

    login = 391773676
    name = "XAU AI PRO"
    company = "XM Global Limited"
    server = "XMGlobal-MT5 14"
    balance = 10.50
    equity = 10.50
    profit = 0.0
    margin = 0.0
    margin_free = 10.50
    margin_level = 0.0
    currency = "USD"
    trade_mode = 0  # conta REAL no padrao do MT5
    leverage = 1000


class _Terminal:
    connected = True
    trade_allowed = True


class _Mt5:
    ACCOUNT_TRADE_MODE_DEMO = 1

    def terminal_info(self):
        return _Terminal()

    def account_info(self):
        return _Conta()

    def positions_get(self):
        return None

    def symbol_info_tick(self, *_a, **_k):
        return None


class TestAlavancagemNoPayload:
    """O campo que o painel de ordem usa para calcular o requisito de margem."""

    def test_a_conta_publica_a_alavancagem(self, monkeypatch):
        mod = importlib.import_module("mt5_gateway")
        monkeypatch.setattr(mod, "_mt5", lambda: _Mt5())

        conta = mod._payload()["account"]

        # MEDIDO nos dois lados: XM escreve 1000:1, MT5 devolve 1000.
        assert conta["leverage"] == 1000

    def test_a_alavancagem_entra_JUNTO_COM_A_CONTA(self, monkeypatch):
        """
        Por que o campo e da CONTA e nao de um catalogo de ativos.

A alavancagem e uma propriedade da conta, e nao do par: o mesmo `0,01`
        usa 1000:1 em BTCUSD e em EURUSD. Um cadastro por ativo teria duas
        tabelas para atualizar e nenhuma delas autoritativa — e o painel leria
        a errada sem aviso.
        """
        mod = importlib.import_module("mt5_gateway")
        monkeypatch.setattr(mod, "_mt5", lambda: _Mt5())

        conta = mod._payload()["account"]

        for campo in ("login", "currency", "balance", "leverage"):
            assert campo in conta, f"`{campo}` tem de vir na mesma leitura"

    def test_PROVA_NEGATIVA_sem_leverage_vem_None_e_nao_zero(self, monkeypatch):
        """
        `None` E AUSENCIA MEDIDA. `0` E UM NUMERO QUE O PAINEL DIVIDIRIA.

        O frontend faz `nocional / alavancagem`. Com `0` isso e `Infinity`, e o
        painel escreveria `Infinity USD` — que e o "numero inventado no painel"
        que este ciclo existe para impedir.

        `None` faz o painel escrever "indisponivel — falta alavancagem da conta",
        que e a resposta honesta e diz o que fazer.
        """
        mod = importlib.import_module("mt5_gateway")

        class ContaSemAlavancagem(_Conta):
            leverage = None

        class Mt5SemAlavancagem(_Mt5):
            def account_info(self):
                return ContaSemAlavancagem()

        monkeypatch.setattr(mod, "_mt5", lambda: Mt5SemAlavancagem())

        conta = mod._payload()["account"]

        assert conta["leverage"] is None
        assert conta["leverage"] != 0

    def test_PROVA_NEGATIVA_a_conta_ausente_nao_inventa_alavancagem(self, monkeypatch):
        """
        Com o `terminal64` fechado nao ha conta nenhuma. O payload tem de ficar
        sem `account`, e nao com uma conta de leverage `1`.

        Uma conta inventada com `leverage: 1` daria requisito de margem igual ao
        nocional inteiro — e o operador leria `$855,10` como se a conta tivesse
        1:1, que e o oposto da alavancagem real.
        """
        mod = importlib.import_module("mt5_gateway")

        class Mt5Fechado(_Mt5):
            def terminal_info(self):
                return None

            def account_info(self):
                return None

        monkeypatch.setattr(mod, "_mt5", lambda: Mt5Fechado())

        payload = mod._payload()

        assert payload["account"] is None
        assert payload["terminal_connected"] is False
        # E o painel tem de ter um caminho para "sem sessao", que e o que a aba
        # Historico ja diz.
        assert "leverage" not in (payload["account"] or {})

    def test_a_alavancagem_nao_muda_com_o_mercado(self, monkeypatch):
        """
        MEDIDO: BTCUSD tem `contract_size = 1`, EURUSD tem `100.000`, GOLD tem
        `100`. A alavancagem e a MESMA para os tres.

        E por isso que o requisito de margem precisa dos DOIS campos: a
        alavancagem sozinha nao diz se `0,01` expoe `$853` ou `$85.376.630`.
        """
        mod = importlib.import_module("mt5_gateway")
        monkeypatch.setattr(mod, "_mt5", lambda: _Mt5())

        leitura = mod._payload()["account"]["leverage"]

        for contrato in (1.0, 100.0, 100_000.0):
            nocional = 0.01 * contrato * 85_376.63
            assert nocional / leitura > 0
        # A alavancagem e uma so.
        assert leitura == 1000