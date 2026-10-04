# -*- coding: utf-8 -*-
"""Testes da inferencia real (backend/ai_inference.py).

O ponto central destes testes e a AUSENCIA DE FALLBACK. O sinal antigo
usava `rsi ?? 50`, `macd ?? 0`, `volume ?? 1` e confianca constante. Aqui a
exigencia e o contrario: quando nao ha dado, o servico tem de dizer que nao
tem, e nunca fabricar numero para preencher a tela.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend import ai_inference as ai
from backend.ai_inference import _RE_SIMBOLO, _nome_de_artefato


def _candles(n: int = 1200, seed: int = 11) -> pd.DataFrame:
    """Serie M5 com vol coerente com o ATR (ver train_v2 para o porque)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    preco = 2000.0 * np.exp(np.cumsum(rng.normal(0, 0.0006, n)))
    wiggle = np.abs(rng.normal(0, 0.0004, n)) * preco
    return pd.DataFrame({
        "Time": idx, "Open": preco, "High": preco + wiggle, "Low": preco - wiggle,
        "Close": preco * (1 + rng.normal(0, 0.0002, n)),
        "Volume": rng.integers(50, 500, n).astype(float),
        "ATR": np.abs(rng.normal(0, 1.2, n)).clip(0.3, None),
        "ADX": rng.uniform(10, 40, n), "RSI": rng.uniform(20, 80, n),
    })


# ------------------------------------------------------------- sem fallback


def test_sem_candles_nao_inventa_sinal():
    r = ai.inferir("XAUUSD", pd.DataFrame(), "H1")
    assert r.disponivel is False
    assert r.signal == "NEUTRAL"
    assert r.confianca == 0.0
    assert "candles" in r.motivo


def test_timeframe_sem_modelo_publicado_e_recusado():
    # M5 tem edge negativo: o servico tem de recusar, nao estimar.
    r = ai.inferir("XAUUSD", _candles(), "M5")
    assert r.disponivel is False
    assert r.confianca == 0.0
    assert r.motivo


def test_timeframe_invalido_e_recusado():
    r = ai.inferir("XAUUSD", _candles(), "M2")
    assert r.disponivel is False
    assert "nao suportado" in r.motivo


def test_resultado_indisponivel_nao_tem_probabilidade():
    """A tela nao pode exibir 50%/'vazio' como se fosse leitura do modelo."""
    r = ai.inferir("XAUUSD", pd.DataFrame(), "H1")
    d = r.para_dict()
    assert d["available"] is False
    assert d["confidence"] == 0.0
    assert d["prob_buy"] == 0.0 and d["prob_sell"] == 0.0
    assert d["reason"], "sempre haver um motivo legivel"


# ------------------------------------------------------------- inventario


@pytest.mark.skipif(
    not ai.MODELOS_DIR.exists() or not any(ai.MODELOS_DIR.glob("*.meta.json")),
    reason=(
        "sem catalogo de modelos neste checkout: os .pkl e .meta.json sao "
        "artefatos de treino e nao vao no git (.gitignore). O CI roda o "
        "checkout limpo e nao tem o catalogo; o inventario real e verificado "
        "por scripts/auditar_governanca_modelos.py na maquina de operacao."
    ),
)
def test_listar_modelos_traz_metricos_reais():
    modelos = ai.listar_modelos()
    assert modelos, "deveria haver metadados de modelo no repositorio"
    simbolos = set()
    for m in modelos:
        # O catalogo cobre todos os simbolos treinados (9), nao so XAUUSD.
        # O que nao pode e vazio ou sem simbolo: a interface precisa saber
        # qual ativo cada artefato decide.
        assert m["symbol"], m
        simbolos.add(m["symbol"])
        assert "_" in m["id"] and m["id"].startswith(m["symbol"]), m
        assert "accuracy" in m and "edge" in m
        assert m["edge_min"] is not None
        assert isinstance(m["publicable"], bool)
    assert len(simbolos) >= 2, f"catalogo deveria cobrir varios simbolos: {simbolos}"


def test_modelo_publicado_tem_edge_acima_do_minimo():
    for m in ai.listar_modelos():
        if m["publicable"]:
            assert m["edge"] is not None
            assert m["edge"] >= m["edge_min"], (
                f"{m['id']} marcado publicavel com edge {m['edge']} < {m['edge_min']}"
            )


def test_modelo_reprovado_expoe_o_motivo():
    for m in ai.listar_modelos():
        if not m["publicable"]:
            assert m["reason"], f"{m['id']} reprovado sem motivo registrado"


def test_inventario_informa_threads_de_cpu():
    modelos = ai.listar_modelos()
    assert all(m["cpu_threads"] >= 1 for m in modelos)
    assert ai.cpu_threads() >= 1


# ----------------------------------------------------------------- cache


def test_limpar_cache_nao_quebra():
    ai.limpar_cache()
    r = ai.inferir("XAUUSD", _candles(), "H1")
    # Pode estar disponivel ou nao (depende do .pkl publicado no ambiente),
    # mas nunca pode quebrar nem inventar.
    assert isinstance(r.disponivel, bool)
    assert r.confianca >= 0.0


# ------------------------------------------- coerencia com o treino


def test_inferencia_usa_as_mesmas_features_do_treino():
    """Se a ordem das features divergir do treino, o modelo ve outra coisa."""
    from Python.ai import train_v2 as t
    r = ai.inferir("XAUUSD", _candles(), "H1")
    if not r.disponivel:
        pytest.skip("modelo H1 nao publicado neste ambiente")
    # O hash sai do mesmo modulo usado no treino.
    assert r.feature_hash == t.feature_hash()
    # O nome na tela e limpo e legivel: `Floresta · XAUUSD 1H`.
    # Nao usa mais `_H1`: o operador pediu nome sem sublinhado, e o timeframe
    # ja vem traduzido por `_ROTULO_TF`. O artefato em disco continua
    # `XAUUSD_H1.pkl` — renomear o arquivo deixaria os 36 modelos orfaos.
    assert r.modelo.endswith("XAUUSD 1H"), r.modelo
    assert "_" not in r.modelo, r.modelo


def test_rotulo_modelo_nao_tem_sublinhado():
    """Nome exibido e sempre `SIMBOLO TF`, sem `_` nem prefixo no meio."""
    assert ai.rotulo_modelo("XAUUSD", "H1") == "MODELO XAUUSD 1H"
    assert ai.rotulo_modelo("BTCUSDT", "M5") == "MODELO BTCUSDT 5M"
    assert ai.rotulo_modelo("XAUUSD", "H1", comPrefixo=False) == "XAUUSD 1H"
    # O prefixo MODELO e cabecalho de coluna: nunca aparece entre o algoritmo
    # e o par, que era o que a tela mostrava ("Floresta MODELO XAUUSD 1H").
    meta = {"algorithm": "RandomForestClassifier"}
    assert ai._nome_do_modelo("XAUUSD", "H1", meta).endswith("XAUUSD 1H")
    assert "MODELO" not in ai._nome_do_modelo("XAUUSD", "H1", meta)


def test_confianca_e_probabilidade_do_classificador():
    """Confianca nao pode ser constante: tem que bater com as probabilidades."""
    r = ai.inferir("XAUUSD", _candles(), "H1")
    if not r.disponivel:
        pytest.skip("modelo H1 nao publicado neste ambiente")
    probs = [r.prob_buy, r.prob_sell, r.prob_neutral]
    assert abs(sum(probs) - 1.0) < 0.01, "probabilidades devem somar 1"
    assert r.confianca == pytest.approx(max(probs) * 100.0, rel=1e-3)
    # E nao pode ser uma das constantes do gerador antigo (50/60/70/75/80).
    assert r.confianca not in (50.0, 60.0, 70.0, 75.0, 80.0)


def test_decisao_corresponde_a_probabilidade_maior():
    r = ai.inferir("XAUUSD", _candles(), "H1")
    if not r.disponivel:
        pytest.skip("modelo H1 nao publicado neste ambiente")
    probs = {0: r.prob_sell, 1: r.prob_neutral, 2: r.prob_buy}
    esperado = {0: "SELL", 1: "NEUTRAL", 2: "BUY"}[max(probs, key=lambda k: probs[k])]
    assert r.signal == esperado
# -------------------------------------------- nenhum ativo pode ser presumido
#
# POR QUE ESTES TESTES EXISTEM
# ===========================
# O dono definiu: *"nao deixei xauusd em codigos como comandos ou exclusivo.
# manter codigos limpos e livres"*. A regra ja esta escrita no projeto
# (`app/market_symbols.py:32` → `return ""  # sem ativo fixo`).
#
# A docstring de `_carregar`, DUAS LINHAS ACIMA do defeito, descreve este
# bug como ja corrigido: *"Antes o caminho era fixo em XAUUSD, entao pedir
# BTCUSD devolvia o modelo de ouro"*. O caminho foi corrigido; o
# `or "XAUUSD"` da linha 184 ficou.
#
# Efeito hoje, verificavel:
#     ai.inferir("", candles, "H1")  ->  carrega XAUUSD_H1.pkl  ->  sinal de OURO
#
# E a segunda vez que este par exato reaparece no mesmo modulo:
# `ESTADO_E_PENDENCIAS.md` linha 36 registra *"Inferencia usava coluna
# `time`, features esperavam `Time`"*. O padrao e corrigir o caso visivel e
# deixar o silencioso.


class TestNenhumAtivoPresumido:
    def test_simbolo_vazio_nao_carrega_o_modelo_de_ouro(self):
        """`_carregar` com simbolo vazio NAO pode devolver um modelo.

        Este e o teste mais importante do arquivo. Sem ele, qualquer chamador
        que passe simbolo vazio recebe decisao de trading do ativo errado com
        confianca real — e nada no retorno denuncia isso.
        """
        ai.limpar_cache()
        modelo, meta = ai._carregar("", "H1")
        assert modelo is None, (
            "simbolo vazio carregou um modelo. A regra do projeto e "
            "'sem ativo fixo': nenhum .pkl pode ser escolhido por omissao."
        )
        assert not meta.get("modelo") or meta.get("modelo") != "XAUUSD_H1"

    def test_simbolo_ausente_e_recusado_com_motivo(self):
        """`inferir` com simbolo vazio tem de dizer que nao pode decidir.

        Nao pode devolver `disponivel=False` com motivo generico nem, pior,
        `disponivel=True` carregando ouro.
        """
        ai.limpar_cache()
        r = ai.inferir("", _candles(), "H1")
        assert r.disponivel is False
        assert r.motivo, "recusa de simbolo ausente sempre tem motivo"
        assert "XAUUSD" not in (r.modelo or ""), (
            f"recusou mas declarou o modelo {r.modelo!r}"
        )

    def test_simbolo_desconhecido_nao_troca_por_outro(self):
        """`INEXISTENTE_QUALQUER` nao pode virar o modelo de ouro.

        Este e o caso que a docstring descreve: pedir BTCUSD e receber ouro.
        """
        ai.limpar_cache()
        r = ai.inferir("INEXISTENTE_QUALQUER", _candles(), "H1")
        assert r.disponivel is False
        assert "INEXISTENTE_QUALQUER" not in str(r.modelo or "")

    def test_simbolo_e_preservado_ao_carregar(self):
        """`_carregar` normaliza caixa, mas nao troca o ativo.

        `btcusd` e `BTCUSD` sao o mesmo ativo — isso e normalizacao legitima.
        O que nao pode e virar em outro ativo.
        """
        ai.limpar_cache()
        _, meta = ai._carregar("btcusd", "H1")
        declarado = str(meta.get("symbol") or meta.get("modelo") or "")
        if declarado:
            assert "BTCUSD" in declarado.upper(), (
                f"pediu BTCUSD e recebeu {declarado!r}"
            )


class TestQuoteDaCorretora:
    """O par da exchange resolve para o modelo do terminal, sem trocar de ativo.

    MEXC/Binance operam `BTCUSDT`; o modelo foi treinado como `BTCUSD`.
    A regra e generica (sufixo de quote), sem nenhum nome de ativo no codigo:
    BTC nunca vira outro ativo, e desconhecido continua recusado.
    """

    def test_usdt_carrega_modelo_usd(self):
        ai.limpar_cache()
        modelo, meta = ai._carregar("BTCUSDT", "H1")
        assert modelo is not None, (
            "BTCUSDT deveria resolver para o artefato BTCUSD_H1"
        )
        assert ai.mesmo_ativo(meta.get("symbol", ""), "BTCUSDT")

    def test_usdt_nao_troca_de_ativo(self):
        ai.limpar_cache()
        modelo, meta = ai._carregar("BTCUSDT", "H1")
        if modelo is not None:
            assert not ai.mesmo_ativo(meta.get("symbol", ""), "EURUSD")

    def test_desconhecido_em_usdt_continua_recusado(self):
        ai.limpar_cache()
        modelo, _ = ai._carregar("ZZZQUSDT", "H1")
        assert modelo is None

    def test_recusa_diz_onde_o_ativo_opera(self):
        ai.limpar_cache()
        r = ai.inferir("XAUUSD", _candles(), "M5")
        assert r.disponivel is False
        assert "H1" in r.motivo or "H4" in r.motivo, (
            f"a recusa deveria dizer os timeframes capazes: {r.motivo!r}"
        )

    def test_timeframes_capazes_por_ativo(self):
        ai.limpar_cache()
        assert ai.timeframes_capazes("BTCUSDT") == ["H1", "H4", "M15"]
        assert "M5" not in ai.timeframes_capazes("XAUUSD")
        assert ai.timeframes_capazes("") == []


class TestModelosMultiClasseAcessiveis:
    """Os artefatos `MULTI_*` precisam ser alcancaveis, e a travessia barrada.

    MEDIDO EM 04/10/2026
    =====================
    `MULTI_METALS.pkl`, `MULTI_FIAT.pkl` e `MULTI_CRYPTO.pkl` existem no
    disco, tem `publicable: true` e o maior edge do catalogo — MULTI_METALS
    +0,2497 com 58,3% de acerto em 67.678 amostras. Nenhum dos tres era
    alcanzavel: `_RE_SIMBOLO` era `^[A-Z0-9]{1,12}$`, o `_` do nome nao
    passava, `_nome_de_artefato()` devolvia `None` e a tela dizia "modelo nao
    publicado ou ausente".

    O comentario da propria constante citava `BTCUSDT_PERP` como simbolo
    valido: comentario e regex discordavam, e o regex era o que valia. Por
    isso o defeito passou em revisao — os dois pareciam certos.

    A DEFESA CONTINUA: o conjunto `[A-Z0-9_]` nao contem ponto nem barra, que
    sao o que constroi travessia. Estes testes medem os dois lados — sem o
    segundo, "corrigir" o primeiro seria abrir um buraco.
    """

    @pytest.mark.parametrize("simbolo", ["MULTI_METALS", "MULTI_FIAT", "MULTI_CRYPTO"])
    def test_o_nome_do_artefato_e_gerado(self, simbolo):
        assert _nome_de_artefato(simbolo, "H1") == f"{simbolo}_H1"

    @pytest.mark.parametrize("simbolo", ["MULTI_METALS", "MULTI_FIAT", "MULTI_CRYPTO"])
    def test_o_artefato_do_multi_existe_no_disco(self, simbolo):
        """Nao basta gerar o nome: o `.meta.json` tem de estar la. Sem esta
        checagem o teste passaria com o nome certo e o arquivo errado."""
        pasta = ai._resolver_modelos()
        artefato = pasta / f"{simbolo}.meta.json"
        if not artefato.exists():
            pytest.skip(f"{simbolo} nao foi treinado nesta maquina")
        assert _nome_de_artefato(simbolo, "H1") is not None

    @pytest.mark.parametrize("simbolo", [
        "BTCUSDT_PERP",   # citado no comentario da constante
        "XAUUSD", "BTCUSD", "EURUSD", "MULTI_METALS",
    ])
    def test_simbolo_valido_aceito(self, simbolo):
        assert _RE_SIMBOLO.match(simbolo), simbolo

    @pytest.mark.parametrize("ataque", [
        "../secret", "..%2f..%2fetc", "XAU/USD", "XAU\\\\USD", "..",
        "..\\\\..\\\\win", "XAUUSD;rm", "XAUUSD\x00.txt", "a" * 25,
        "XAU USD", "XAU-USD", "~/XAU", "XAUUSD.", ".XAUUSD",
    ])
    def test_travessia_continua_barrada(self, ataque):
        """O ponto e a barra NAO estao na classe permitida, entao `..` e `/`
        falham por construcao — nao por lista de excecao que alguem possa
        esquecer de atualizar."""
        assert not _RE_SIMBOLO.match(ataque), ataque
        assert _nome_de_artefato(ataque, "H1") is None

    def test_o_underscore_nao_abre_caminho(self):
        """`_` nao e separador de caminho. Um nome com `_` continua sendo um
        nome de arquivo dentro da pasta, nunca uma instrucao de subir de
        nivel."""
        assert _nome_de_artefato("MULTI_METALS", "H1") == "MULTI_METALS_H1"
        assert ".." not in "MULTI_METALS_H1"
        assert "/" not in "MULTI_METALS_H1"

    def test_o_limite_comporta_o_nome_completo(self):
        """`MULTI_METALS` + `_H4` tem 15 caracteres. Com o limite antigo de 12
        no simbolo, o nome completo estourava."""
        assert len(_nome_de_artefato("MULTI_METALS", "H4")) == 15



class TestNenhumAtivoRealFicaPreso:
    """A regra do projeto: o que o operador PRECISA usar nao pode ser barrado.

    "Nenhum simbolo pode ser presumido" vale para o CONTEUDO: a lista nao e
    allowlist de pares, porque cresceria a cada par novo. O FORMATO, esse sim,
    e restrito — e e ai que um nome valido ja foi barrado por accidento (os
    `MULTI_*`, medido em 04/10/2026).

    Estes testes listam os nomes que as corretoras do catalogo usam de verdade.
    Se um dia um deles for barrado, o defeito aparece aqui e nao na tela do
    operador, como "modelo nao publicado ou ausente" para um artefato que
    existe no disco.

    O limite de 24 caracteres nao e apertado: o maior nome real medido tem 12.
    A folga existe para o sufixo `_PERP` e contratos nomeados, e nao para
    nomes que so existam para estourar o limite.
    """

    #: Forex, metais, energias, cripto e as tres classes multi. Todos estes
    #: nomes aparecem em corretora real e TODOS precisam gerar artefato.
    ATIVOS_REAIS = (
        "XAUUSD", "XAGUSD",
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF",
        "EURJPY", "GBPJPY", "EURAUD", "EURCAD",
        "USOIL", "UKOIL", "WTI", "NGAS",
        "BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD", "XRPUSD", "DOGEUSD",
        "BTCUSDT", "ETHUSDT", "BTCUSDT_PERP",
        "MULTI_METALS", "MULTI_FIAT", "MULTI_CRYPTO",
    )

    @pytest.mark.parametrize("simbolo", ATIVOS_REAIS)
    def test_gera_nome_de_artefato(self, simbolo):
        assert _nome_de_artefato(simbolo, "H1") == f"{simbolo}_H1"

        """O limite tem que COBRIR todo nome real, e NAO sobra folga sem motivo.

        Subi o limite de 12 para 24 achando que `MULTI_METALS` (12) + `_H1`
        precisaria de espaco. O limite conta o SIMBOLO, nao o nome do arquivo,
        e `MULTI_METALS` tem 12. A folga seria afrouxar seguranca sem
        necessidade: `tests/test_traversal_modelos.py` barrava `A * 13` e
        estava certo.

        Aqui a propriedade e o COBRIMENTO — todo nome real passa. A propriedade
        de nao sobrar folga esta no teste de travessia, que barra `A * 13`.
        """
        maior = max(len(s) for s in self.ATIVOS_REAIS)
        assert _RE_SIMBOLO.match("A" * maior), f"nome real de {maior} chars nao cabe"
        # E o nome completo do artefato, que e o que vira arquivo.
        assert _nome_de_artefato("MULTI_METALS", "H1") == "MULTI_METALS_H1"
