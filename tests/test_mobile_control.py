"""Trava da central de comando movel (somente leitura).

O QUE ESTES TESTES PROVAM
=========================
1. O mapeamento do payload REAL do gateway (`gw._payload()` +
   `gw._status_snapshot()` + `gw._risk_state()`) produz o retrato que a tela
   consome - importando `montar_de_leitura`, nao repetindo o codigo.
2. Nenhuma recusa vira zero silencioso: `positions_available=False` (terminal
   mudo) NAO pode aparecer como "nenhuma posicao".
3. Simbolo vazio e recusado com motivo, nunca substituido por ativo padrao.
4. O modulo nao tem caminho de escrita: os nomes de funcao publicos nao criam,
   fecham, alteram, cancelam nem sacam nada.
"""
from __future__ import annotations

import inspect

import pytest

from backend import mobile_control


# ---------------------------------------------------------------------------
# Payloads no formato em que o gateway realmente responde. Os nomes foram
# lidos de `mt5_gateway._payload()` e `_status_snapshot()`.
# ---------------------------------------------------------------------------
def payload_conta_ok() -> dict:
    return {
        "terminal_connected": True,
        "account": {
            "login": 55512,
            "server": "XM-DEMO",
            "broker": "XM",
            "currency": "USD",
            "balance": 1500.5,
            "equity": 1520.25,
            "margin_free": 1400.0,
            "leverage": 500,
        },
        "positions": [
            {
                "ticket": 90210,
                "symbol": "EURUSD",
                "type": 1,
                "volume": 0.25,
                "price_open": 1.08412,
                "price_current": 1.0835,
                "sl": 1.089,
                "tp": 1.075,
                "profit": 12.4,
                "comment": "mcc",
            }
        ],
        "positions_available": True,
        "pending_orders": [],
        "pending_orders_available": True,
        "exposure": {"total": 0.25},
        "ts": "2026-11-17T12:00:00Z",
    }


def saude_ok(conectado: bool = True) -> dict:
    return {
        "ok": True,
        "gateway": "online",
        "terminal_connected": conectado,
        "positions_available": True,
        "source": "mt5_gateway",
    }


def risco_ok() -> dict:
    return {
        "ok": True,
        "withdrawals_enabled": False,
        "daily_loss_pct": 1.2,
        "max_daily_loss_pct": 3.0,
        "drawdown_pct": 4.5,
        "max_drawdown_pct": 10.0,
        "risk_percent": 0.5,
    }


class TestMapeamentoDoGateway:
    def test_conta_e_posicao_atravessam_o_mapeamento(self):
        retrato = mobile_control.montar_de_leitura(payload_conta_ok(), saude_ok(), risco_ok())
        assert retrato["conta"]["ok"] is True
        assert retrato["conta"]["login"] == 55512
        assert retrato["conta"]["servidor"] == "XM-DEMO"
        assert retrato["posicoes"]["total"] == 1
        item = retrato["posicoes"]["itens"][0]
        assert item["simbolo"] == "EURUSD"
        assert item["lado"] == "venda", "type=1 do MT5 precisa virar venda"
        assert item["volume"] == 0.25
        assert retrato["risco"]["bloqueios"] == []

    def test_terminal_mudo_nao_vira_conta_zerada(self):
        payload = payload_conta_ok()
        payload["positions"] = []
        payload["positions_available"] = False
        payload["account"] = None

        retrato = mobile_control.montar_de_leitura(payload, saude_ok(False), {})
        assert retrato["posicoes"]["ok"] is False
        assert retrato["posicoes"]["disponivel"] is False
        assert "indisponiveis" in retrato["posicoes"]["motivo"]
        assert retrato["conta"]["ok"] is False
        assert retrato["conta"]["saldo"] is None, "saldo ausente nao pode virar 0"
        assert any("posicoes" in a for a in retrato["avisos"])
        assert any("conta" in a for a in retrato["avisos"])

    def test_simbolo_vazio_e_recusa_com_motivo(self):
        payload = payload_conta_ok()
        payload["positions"] = [
            {"ticket": 1, "symbol": "", "type": 0, "volume": 0.1},
            {"ticket": 2, "symbol": "EURUSD", "type": 0, "volume": 0.1},
        ]
        retrato = mobile_control.montar_de_leitura(payload, saude_ok(), risco_ok())
        assert retrato["posicoes"]["total"] == 1
        assert retrato["posicoes"]["recusadas"] == 1
        assert "sem simbolo" in retrato["posicoes"]["motivo"]
        # Prova negativa: nenhum simbolo inventado entrou no lugar do vazio.
        assert [p["simbolo"] for p in retrato["posicoes"]["itens"]] == ["EURUSD"]

    def test_posicoes_em_formato_inesperado_nao_e_silencio(self):
        payload = payload_conta_ok()
        payload["positions"] = {"nao": "e lista"}
        retrato = mobile_control.montar_de_leitura(payload, saude_ok(), risco_ok())
        assert retrato["posicoes"]["ok"] is False
        assert any("formato inesperado" in a for a in retrato["avisos"])

    def test_erros_de_leitura_viram_aviso(self):
        retrato = mobile_control.montar_de_leitura({}, {}, {}, ["terminal: timeout"])
        assert "terminal: timeout" in retrato["avisos"]

    def test_limite_de_risco_aparece_sem_bloquear_nada(self):
        risco = risco_ok()
        risco["drawdown_pct"] = 10.0
        retrato = mobile_control.montar_de_leitura(payload_conta_ok(), saude_ok(), risco)
        assert retrato["risco"]["bloqueios"] == ["drawdown atingiu o limite configurado"]
        # Leitura NAO muda o estado de execucao do modulo.
        assert retrato["execution_enabled"] is False

    @pytest.mark.parametrize(
        "tipo, lado",
        [(2, "compra"), (4, "compra"), (6, "compra"), (3, "venda"), (5, "venda"), (7, "venda")],
    )
    def test_ordem_pendente_tem_lado_pelo_tipo_do_mt5(self, tipo: int, lado: str):
        # Medido no telefone (17/11/2026): com o mapa so de 0/1 a ordem pendente
        # aparecia como "lado nao informado" mesmo tendo lado no terminal.
        payload = payload_conta_ok()
        payload["pending_orders"] = [
            {"ticket": 7001, "symbol": "XAUUSD", "type": tipo, "volume": 0.05}
        ]
        payload["pending_orders_available"] = True
        retrato = mobile_control.montar_de_leitura(payload, saude_ok(), risco_ok())
        assert retrato["ordens"]["itens"][0]["lado"] == lado


class TestNadaDeEscrita:
    """A guarda principal: o modulo movel nao tem caminho de escrita."""

    def test_constantes_sao_falsas(self):
        assert mobile_control.READ_ONLY is True
        assert mobile_control.COMMANDS_ENABLED is False
        assert mobile_control.EXECUTION_ENABLED is False
        assert mobile_control.WITHDRAWALS_ENABLED is False

    def test_payload_declara_somente_leitura(self):
        retrato = mobile_control.montar_de_leitura(payload_conta_ok(), saude_ok(), risco_ok())
        assert retrato["read_only"] is True
        assert retrato["commands_enabled"] is False
        assert retrato["execution_enabled"] is False
        assert retrato["withdrawals_enabled"] is False
        assert retrato["comandos_recusados"], "a tela precisa saber o que NAO faz"

    @pytest.mark.parametrize(
        "verbo",
        ["order", "trade", "close", "cancel", "withdraw", "transfer", "send"],
    )
    def test_nenhuma_funcao_publica_de_escrita(self, verbo: str):
        publicas = [
            nome
            for nome, _ in inspect.getmembers(mobile_control, inspect.isfunction)
            if not nome.startswith("_")
        ]
        ofensoras = [nome for nome in publicas if verbo in nome.lower()]
        # Prova negativa do proprio teste: `resumo_ordens` LE ordens e nada mais.
        if verbo == "order":
            assert ofensoras in ([], ["resumo_ordens"]), ofensoras
        else:
            assert ofensoras == [], f"funcao publica de escrita: {ofensoras}"

    def test_autoteste_do_modulo_passa(self):
        assert mobile_control.autoteste() == []
