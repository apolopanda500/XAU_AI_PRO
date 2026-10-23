r"""A CLASSIFICACAO DO CATALOGO VEM DA HIERARQUIA (23/10/2026)

DEFEITO MEDIDO no app instalado 1.2.7 (conta 113568614, MetaQuotes-Demo):

    symbol_info("XAUUSD").path == "Metals\\XAUUSD"
    /api/universal/assets?broker=mt5  ->  asset_class == "other"

Com `asset_class="other"`, `mercadoDoAtivo("other")` e `null`: o painel ficava
sem mercado e o grafico caia para `/api/publico/ohlc`. A tela mostrava o ouro
do Yahoo (~4.025,00) enquanto o MT5 servia 4.016,46 no mesmo minuto — e o
motor ligava com o mercado do ESCOPO (`forex`), que nao e o mercado do ativo.

DUAS CAUSAS, as duas medidas:

1. `Metals` nao existia no mapa de raizes (so `Derivatives\\Spot Metals\\...`).
2. `raiz` era comparada em minusculo contra raizes escritas como a corretora
   publica (`Metals`, `Forex`). NUNCA casava: toda classificacao vinha do
   palpite por palavra, e o mapa era codigo morto. `XAUUSD` nao tem a palavra
   METAL no texto do palpite, entao virava `other`.

Estes casos usam os `path` REAIS medidos no terminal, nao inventados.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.asset_registry import _asset_class  # noqa: E402


class TestHierarquiaDaCorretora:
    def test_metals_vira_metal(self):
        # MEDIDO: symbol_info("XAUUSD").path == "Metals\\XAUUSD"
        assert _asset_class("XAUUSD", "Metals\\XAUUSD", "XAU", "USD", "Gold vs US Dollar") == "metal"

    def test_forex_continua_forex(self):
        assert _asset_class("EURUSD", "Forex\\EURUSD", "EUR", "USD", "Euro vs US Dollar") == "forex"

    def test_derivatives_spot_metals_vira_metal(self):
        # MEDIDO na XM (conta 391773676): `GOLD` sob `Derivatives\\Spot Metals`.
        assert _asset_class("GOLD", "Derivatives\\Spot Metals\\GOLD", "", "", "Gold") == "metal"

    def test_derivatives_cash_indices_vira_index(self):
        assert (
            _asset_class("AUS200Cash", "Derivatives\\Cash\\Cash Indices\\AUS200Cash", "", "", "")
            == "index"
        )

    def test_crypto_e_stocks(self):
        assert _asset_class("BTCUSD", "Cryptocurrencies\\BTCUSD", "BTC", "USD", "Bitcoin") == "crypto"
        assert (
            _asset_class(
                "AalbertsIndustries",
                "Stocks\\EU\\Netherlands\\AalbertsIndustries",
                "",
                "",
                "Aalberts Industries",
            )
            == "equity"
        )

    def test_prova_negativa_a_raiz_em_minusculo_casa(self):
        """O defeito de verdade: `metals` (minusculo) contra `Metals` (mapa).

        Sem a comparacao sem caixa, ESTE caso devolve `other` e o ouro perde o
        mercado — foi o que a tela mostrou. O caso nao depende da palavra
        GOLD na descricao: ele prova o mapa, nao o palpite.
        """
        assert _asset_class("XAUUSD", "Metals\\XAUUSD", "", "") == "metal"

    def test_prova_negativa_sem_hierarquia_nao_inventa_classe(self):
        assert _asset_class("XYZ123", "", "", "", "") == "other"

    def test_prova_negativa_palavra_solta_nao_casa_dentro_de_outra(self):
        """`SOL` dentro de "Solvar" nao e cripto (trava do AGENTS 3)."""
        assert _asset_class("Solvar", "Stocks\\EU\\Solvar", "", "", "Solvar SA") == "equity"


@pytest.mark.parametrize(
    ("path", "esperado"),
    [
        ("Metals\\XAUUSD", "metal"),
        ("Forex\\USDJPY", "forex"),
        ("Cryptocurrencies\\ETHUSD", "crypto"),
        ("Indices\\US500", "index"),
    ],
)
def test_catalogo_real_do_demo(path: str, esperado: str):
    nome = path.split("\\")[-1]
    assert _asset_class(nome, path, "", "") == esperado
