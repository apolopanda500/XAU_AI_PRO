"""O carregamento de modelos nao aceita caminho de fora da pasta.

O QUE HOUVE
===========
`simbolo` e `timeframe` chegam da REQUISICAO HTTP:
`backend/auto_engine.py:194` faz `self.simbolo = str(payload["simbolo"]).upper()`
e nao havia validacao antes de

    pkl = MODELOS_DIR / f"{simbolo}_{timeframe}.pkl"

Um simbolo com `../` escapava da pasta de modelos e chegava no `joblib.load`
seguinte. Desserializar um `.pkl` de caminho escolhido e EXECUCAO DE CODIGO
ARBITRARIO — o `pickle` carrega e executa.

CodeQL apontou como `py/path-injection` (4x) e `py/unsafe-deserialization` (1x)
em `backend/ai_inference.py`.

O PORQUE DE DUAS DEFESAS
========================
1. `_nome_de_artefato` barra o ataque na ORIGEM: so `[A-Z0-9]{1,12}` e
   timeframe de allowlist fechada. `..`, `/`, `\\` e `%2e%2e` nao passam.
2. `_caminho_confinado` barra o ataque no DESTINO: mesmo com nome valido, o
   caminho resolvido precisa estar dentro de `MODELOS_DIR`.

So a primeira nao fecha: `MODELOS_DIR` vem de `XAU_MODELOS_DIR` (ou de um app
instalado), e um link simbolico dentro da pasta apontaria para fora. Os testes
abaixo cobrem as duas, e o do symlink e o unico jeito de provar a segunda.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend import ai_inference as ai  # noqa: E402


class TestNomeDeArtefatoRecusa:
    """Defesa 1: o formato do nome e recusado."""

    @pytest.mark.parametrize(
        "simbolo",
        [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "XAUUSD/../../../etc",
            "%2e%2e%2fetc",
            "XAUUSD_H1.pkl",
            "A" * 13,
            "XAU USD",
            "XAUUSD;rm",
            "..",
            ".",
        ],
    )
    def test_simbolo_fora_do_formato(self, simbolo: str):
        assert ai._nome_de_artefato(simbolo.upper(), "H1") is None, (
            f"{simbolo!r} passou na validacao de nome e viraria caminho de arquivo"
        )

    @pytest.mark.parametrize("timeframe", ["H1/../../etc", "ZZZ9", "", "h1 ", "M1"])
    def test_timeframe_fora_da_allowlist(self, timeframe: str):
        # `M1` nao esta em TIMEFRAMES_VALIDOS: medido nos artefatos reais
        # (M5, M15, H1, H4), `M1` seria um timeframe novo e nao um existente.
        #
        # POR QUE ESTE TESTE MEDE `inferir`, E NAO `_nome_de_artefato`
        # ===========================================================
        # Em 04/10/2026 a resolucao de nome ganhou uma porta nova: o timeframe
        # VAZIO devolve o nome geral (`MULTI_METALS`), para o modelo unico que
        # cobre varios periodos. Isso fez este teste reprovar — mas o
        # comportamento estava CORRETO: `inferir` ja recusa timeframe fora da
        # allowlist ANTES de chegar no resolvedor de nome, entao um pedido do
        # operador nunca usa a porta do vazio.
        #
        # O teste antigo verificava a camada errada. A propriedade que importa
        # e "um pedido com timeframe invalido nao vira nome de arquivo", e
        # essa e medida aqui no caminho real, com `inferir`.
        import pandas as pd

        candles = pd.DataFrame({
            "Time": pd.date_range("2026-01-01", periods=300, freq="h"),
            "Open": range(300), "High": range(300), "Low": range(300),
            "Close": range(300), "Volume": range(300),
            "ATR": 12.0, "ADX": 30.0, "RSI": 50.0,
        })
        inf = ai.inferir("XAUUSD", candles, timeframe)
        assert inf.disponivel is False, (
            f"timeframe {timeframe!r} foi aceito e produziu decisao"
        )
        assert "timeframe" in inf.motivo or "nao publicado" in inf.motivo, inf.motivo

    @pytest.mark.parametrize(
        "simbolo,timeframe",
        [
            ("XAUUSD", "H1"),
            ("BTCUSD", "M15"),
            ("EURUSD", "H4"),
            ("US500", "M5"),
            ("XAGUSD", "M5"),
        ],
    )
    def test_par_legitimo_gera_nome(self, simbolo: str, timeframe: str):
        """A trava nao pode fechar o que e legitimo."""
        assert ai._nome_de_artefato(simbolo, timeframe) == f"{simbolo}_{timeframe}"


class TestCaminhoConfinado:
    """Defesa 2: o caminho resolvido nao pode escapar de `MODELOS_DIR`."""

    def test_nome_valido_fica_dentro(self):
        caminho = ai._caminho_confinado("XAUUSD_H1.pkl")
        assert caminho is not None
        assert caminho.name == "XAUUSD_H1.pkl"
        assert caminho.is_relative_to(ai.MODELOS_DIR.resolve())

    def test_symlink_para_fora_e_recusado(self, monkeypatch, tmp_path):
        """O caso que a regex NAO pega: nome valido apontando para fora.

        Sem este teste, apagar a defesa 2 nao quebraria nada visivel — a regex
        continua barrando os ataques por origem, e o symlink so apareceria em
        producao.
        """
        raiz = tmp_path / "models"
        fora = tmp_path / "fora"
        raiz.mkdir()
        fora.mkdir()
        (fora / "XAUUSD_H1.pkl").write_bytes(b"PK\x03\x04 malicioso")

        link = raiz / "XAUUSD_H1.pkl"
        try:
            os.symlink(fora / "XAUUSD_H1.pkl", link)
        except OSError as e:  # pragma: no cover - depende de privilegio do SO
            pytest.skip(f"symlink nao permitido nesta maquina: {e}")

        monkeypatch.setattr(ai, "MODELOS_DIR", raiz)

        # O nome passa a regex — e por isso que a defesa 2 e necessaria.
        assert ai._nome_de_artefato("XAUUSD", "H1") == "XAUUSD_H1"
        assert ai._caminho_confinado("XAUUSD_H1.pkl") is None, (
            "symlink para fora de MODELOS_DIR nao foi recusado: o joblib.load "
            "seguiria o link e leria o arquivo de fora"
        )


class TestCarregarRecusaSemEscapar:
    """O ponto de entrada: `_carregar` nao pode tocar arquivo de fora."""

    @pytest.mark.parametrize(
        "simbolo,timeframe",
        [
            ("../../../etc/passwd", "H1"),
            ("..\\..\\secret", "H1"),
            ("XAUUSD/../../x", "H1"),
            ("XAUUSD", "H1/../.."),
        ],
    )
    def test_carregar_nao_le_arquivo_de_fora(self, simbolo: str, timeframe: str):
        modelo, meta = ai._carregar(simbolo, timeframe)
        assert modelo is None, "um caminho de fora da pasta foi desserializado"
        assert meta == {} or not meta.get("model"), (
            f"o carregamento devolveu metadados para entrada invalida: {meta}"
        )

    def test_simbolo_vazio_continua_recusado(self):
        """A regra do dono: simbolo vazio e recusa, nunca um ativo padrao."""
        modelo, meta = ai._carregar("", "H1")
        assert modelo is None
        assert meta.get("publish_reason") == ai.MOTIVO_SEM_SIMBOLO