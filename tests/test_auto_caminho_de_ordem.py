"""
  O CAMINHO DE ORDEM DO MOTOR (06/10/2026)
  ========================================

  MEDIDO no log de intents de PRODUCAO, conta 391773676: 158 intents, sendo 77
  `exchange_order` pending e 77 `exchange_order` **failed**, e **zero** intents
  com ticket de ordem. Toda tentativa morria com `EXECUTION_VIA_MT5_GATEWAY`.

  A causa: o envio do MT5 foi trocado do `mt5_gateway` para o `UniversalRouter`,
  mas `MT5ExecutionAdapter.execute` recusa MT5 DE PROPÓSITO (o `risk_gate` e o
  `order_check` so existem em `_trade_order`). O MT5 ficou com um caminho que,
  por desenho, nunca envia.

  Estes testes medem a TRADUCAO e nao o envio. O envio real depende do MetaTrader
  e de money real; o que se trava aqui e o desacamento de nome entre o que o
  motor produz e o que `_trade_order` le — que e onde a ordem se perdia.
"""

from __future__ import annotations

import pytest

from backend.auto_engine import mercado_do_ativo, pedido_para_mt5, pedido_para_router


# O payload que `ciclo_unico` monta, nas chaves REAIS.
PAYLOAD = {
    "symbol": "btcusd",
    "side": "sell",
    "quantity": 0.01,
    "stop_loss": 85664.55,
    "take_profit": 85361.80,
    "confirm": True,
    "request_id": "auto-mt5:BTCUSD:H1:5971026",
    "origin": "motor_auto",
}


class TestTraducaoParaMt5:
    def test_usa_as_chaves_que_o_trade_order_le(self):
        """
        `_trade_order` le `volume`, `sl` e `tp`. O motor produz `quantity`,
        `stop_loss` e `take_profit`. Sem esta traducao a ordem morre em
        "symbol, side, volume <= 0.10, sl e tp validos sao obrigatorios" — que
        e a recusa que NAO diz qual dos cinco campos faltou (AGENTS.md 5).
        """
        pedido = pedido_para_mt5(PAYLOAD)
        assert pedido["volume"] == 0.01
        assert pedido["sl"] == 85664.55
        assert pedido["tp"] == 85361.80

    def test_side_em_caixa_alta(self):
        # `_trade_order` compara `side not in {"BUY", "SELL"}`. Minuscula seria
        # recusado com o motivo generico de cinco campos.
        assert pedido_para_mt5(PAYLOAD)["side"] == "SELL"
        assert pedido_para_mt5({**PAYLOAD, "side": "buy"})["side"] == "BUY"

    def test_confirm_e_request_id_sobram(self):
        """Toda escrita exige os dois (AGENTS.md 4). Sem eles e recusa."""
        pedido = pedido_para_mt5(PAYLOAD)
        assert pedido["confirm"] is True
        assert pedido["request_id"] == PAYLOAD["request_id"]

    def test_o_request_id_sobja_intacto(self):
        """
        `request_id` e a idempotencia. Reescrever o formato faria o gateway
        tratar cada ciclo como uma ordem nova, e o mesmo ciclo reexecutado
        viraria ordem duplicada.
        """
        bruto = "auto-mt5:BTCUSD:H1:5971026"
        assert pedido_para_mt5({**PAYLOAD, "request_id": bruto})["request_id"] == bruto

    def test_PROVA_NEGATIVA_nao_inventa_sl_nem_tp(self):
        """
        `sl: 0` e `tp: 0` sao recusados pelo gateway, mas a recusa chega como
        motivo generico. O que a traducao nao pode fazer e substituir um nivel
        ausente por um numero: o painel e que decide o nivel, e ele ja recusou
        sem `contract_size`.
        """
        pedido = pedido_para_mt5({**PAYLOAD, "stop_loss": 0, "take_profit": 0})
        assert pedido["sl"] == 0
        assert pedido["tp"] == 0
        # E nao virou preco, volume, nem distancia calculada.
        assert pedido["volume"] == 0.01

    def test_PROVA_NEGATIVA_sem_symbol_levanta(self):
        """Sem simbolo a ordem nao pode sair; a recusa tem de ser no envio."""
        with pytest.raises(KeyError):
            pedido_para_mt5({k: v for k, v in PAYLOAD.items() if k != "symbol"})


class TestMercadoDoAtivo:
    """BTCUSD gravado como `forex` por 14 intents na conta real."""

    def test_cripto_vira_crypto_spot(self, monkeypatch):
        monkeypatch.setattr(
            "backend.asset_registry.discover_assets",
            lambda *_a, **_k: [{"symbol": "BTCUSD", "asset_class": "crypto"}],
        )
        monkeypatch.setattr("backend.mt5_gateway._mt5", lambda: object())
        assert mercado_do_ativo("mt5", "forex", "BTCUSD") == "crypto-spot"

    def test_metal_vira_metals(self, monkeypatch):
        monkeypatch.setattr(
            "backend.asset_registry.discover_assets",
            lambda *_a, **_k: [{"symbol": "XAUUSD", "asset_class": "metal"}],
        )
        monkeypatch.setattr("backend.mt5_gateway._mt5", lambda: object())
        assert mercado_do_ativo("mt5", "forex", "XAUUSD") == "metals"

    def test_a_classe_da_corretora_manda(self, monkeypatch):
        """
        Um par cujo NOME parece cripto, publicado pela corretora como
        `forex`, tem que ficar forex. A classe e a HIERARQUIA da corretora, e
        nao palavra no nome (AGENTS.md 3).
        """
        monkeypatch.setattr(
            "backend.asset_registry.discover_assets",
            lambda *_a, **_k: [{"symbol": "SOLUSD", "asset_class": "forex"}],
        )
        monkeypatch.setattr("backend.mt5_gateway._mt5", lambda: object())
        assert mercado_do_ativo("mt5", "crypto-spot", "SOLUSD") == "forex"

    def test_PROVA_NEGATIVA_sem_catalogo_devolve_o_que_vier(self, monkeypatch):
        """
        Sem catalogo nao ha como saber, e `forex` para BTCUSD seria palpite.
        Trocar um palpite por outro seria adivinhar com mais confianca.
        """
        monkeypatch.setattr(
            "backend.asset_registry.discover_assets",
            lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("sem MT5")),
        )
        assert mercado_do_ativo("mt5", "forex", "BTCUSD") == "forex"

    def test_PROVA_NEGATIVA_ativo_inexistente_nao_muda_o_mercado(self, monkeypatch):
        monkeypatch.setattr(
            "backend.asset_registry.discover_assets",
            lambda *_a, **_k: [{"symbol": "EURUSD", "asset_class": "forex"}],
        )
        monkeypatch.setattr("backend.mt5_gateway._mt5", lambda: object())
        assert mercado_do_ativo("mt5", "metals", "BTCUSD") == "metals"

    def test_PROVA_NEGATIVA_outra_corretora_nao_e_consultada(self, monkeypatch):
        """
        Exchange nao tem `discover_assets` de MT5. Consultar seria presumir que
        toda corretora e MT5 — o oposto do que a troca de 30/09 queria.
        """

        def _explodir(*_a, **_k):  # pragma: no cover - so aparece se bugar
            raise AssertionError("catalogo de MT5 nao pode ser consultado para exchange")

        monkeypatch.setattr("backend.asset_registry.discover_assets", _explodir)
        assert mercado_do_ativo("binance", "crypto-spot", "BTCUSDT") == "crypto-spot"


class TestRoteadorNaoMuda:
    def test_a_traducao_das_exchanges_continua_no_roteador(self):
        """
        A correcao e do MT5, nao do roteador: as exchanges seguem com o
        `UniversalRouter`, que tem o adaptador de cada uma e o gate
        `XAU_ENABLE_<BROKER>_EXECUTION`. O pedido leva `quantity` e
        `account_id`, que e o que `UniversalOrderRequest` le.
        """
        pedido = pedido_para_router(PAYLOAD, "binance", "crypto-spot", "binance:crypto")
        assert pedido["quantity"] == 0.01
        assert pedido["side"] == "sell"
        assert pedido["account_id"] == "binance:crypto"
        # E nao ganhou `volume`/`sl`/`tp`, que sao do MT5.
        assert "volume" not in pedido