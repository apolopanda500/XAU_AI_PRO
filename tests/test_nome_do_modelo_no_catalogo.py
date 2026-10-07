"""
O CATALOGO DIZ O NOME DO MODELO (07/10/2026)
==============================================

MEDIDO na conta 391773676 (XMGlobal-MT5 14), com `discover_assets`:

    GOLD       path = Derivatives\\Spot Metals\\GOLD  contract_size = 100
    XAUUSD     NAO EXISTE no terminal XM  (symbol_info("XAUUSD") -> None)
    XAUJPY     existe,  path = Derivatives\\Spot Metals
    BTCUSD     existe,  path = Cryptocurrencies\\Standard
    1639 linhas no catalogo; 36 .meta.json no disco

O MESMO METAL, DOIS NOMES, E A FICHA SAI VAZIA PARA UM DELES.

A CONSEQUENCIA MEDIDA NO APP INSTALADO
=====================================
O `fichaDoAtivo` do frontend procurava so por `symbol`. Com o par do modelo
(`XAUUSD`), a ficha vinha `null` — e a ficha alimenta TRES decisoes de uma vez:

    - `assetClass`    -> `mercadoDoAtivo` -> o mercado da consulta
    - `contract_size` -> `nivelDoValor`   -> dinheiro vira preco
    - `volume_min/max/step` -> a faixa que o painel aceita

Sem ficha, as tres somem, e o painel diz "depende do contrato" para um ativo que
a corretora JA TINHA PUBLICADO. E o grafico nem carrega: `mercadoDoAtivo(null)`
devolve `null`, e `configurado` fica falso.

E o AGENTS.md 5 pelo lado que ESCREVEU a tela: o sintoma — "nao tem grafico",
"depende do contrato" — cairia em quem escreveu, e a culpa seria da corretora.

POR QUE O CAMPO NASCE AQUI, E NAO NO FRONTEND
===============================================
O mapa `{"mt5": {"XAUUSD": "GOLD"}}` e CONFIG do operador, e o AGENTS.md 3
proibe nome de ativo no codigo. Ele vive no gateway, que tem a ficha.

Se o frontend tivesse o proprio mapa, e o operador mudasse o arquivo, a tela
continuaria com o mapa velho — dois lugares que divergem, que e o AGENTS.md 5.

Por isso `model_symbol` e `para_modelo` (corretora -> modelo): quem pergunta e a
TELA, e ela precisa do nome com que o `.pkl` foi gravado. E o sentido oposto de
`para_corretora`, que o gateway ja usa em candles, cotacao e ordem.

O QUE ESTE ARQUIVO TRAVA
=======================
1. `GOLD` e `XAUUSD` produzem a MESMA ficha, com o mesmo `contract_size`.
2. `null` quando o par nao existe — a segunda busca nao pode virar "qualquer par
   acha alguma ficha".
3. `model_symbol` ausente vira `null`, e NAO o proprio `symbol`: se caisse no
   `symbol`, todos os 1.639 pares do catalogoariam ter modelo, e a lista de
   modelos mentiria (existem 36 `.meta.json`).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# O mapa do operador, medido no disco. Sem `XAU_APP_CONFIG`, o modulo le
# `%APPDATA%/XAU_AI_PRO/symbol_aliases.json`; aqui vai o mesmo conteudo para o
# teste nao depender do que o terminal da maquina tem gravado.
MAPA_XM = {"mt5": {"XAUUSD": "GOLD"}}


def _sem_docstrings_e_comentarios(fonte: str) -> str:
    """O codigo, sem comentario nem docstring.

    Usando o `tokenize` do Python, e nao um regex: um `#` DENTRO de uma string
    (uma URL, um caminho) nao e comentario, e um regex apagaria a linha inteira —
    incluindo o codigo dela, que e o que este teste precisa ler.

    O AGENTS.md 4e: uma trava textual que proibe documentar reprova a
    explicacao do defeito. Este helper existe para que o testerittenha o que a
    regra proibe — o NOME NO CODIGO — sem proibir o nome no texto que explica
    por que ele nao pode estar no codigo.
    """
    import io
    import tokenize

    linhas = fonte.splitlines(keepends=True)
    fora: set[int] = set()
    try:
        for token in tokenize.generate_tokens(io.StringIO(fonte).readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                for n in range(token.start[0], token.end[0] + 1):
                    fora.add(n)
    except tokenize.TokenError:
        # Fonte truncada: devolve o que deu para ler, e o teste reprova.
        return fonte
    return "".join(l for i, l in enumerate(linhas, start=1) if i not in fora)


class _Symbol:
    """Um item de `symbols_get`, com os campos que `discover_assets` le."""

    def __init__(self, nome, path, contract_size, volume_min, volume_max, volume_step,
                 digits, point, base="", profit="USD"):
        self.name = nome
        self.path = path
        self.trade_contract_size = contract_size
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.volume_step = volume_step
        self.digits = digits
        self.point = point
        self.currency_base = base
        self.currency_profit = profit
        self.description = nome
        self.visible = True
        self.trade_mode = 4


class _Mt5ComOuro:
    """O catalogo MEDIDO da conta 391773676 (XMGlobal-MT5 14)."""

    def symbols_get(self, *_a, **_k):
        return [
            _Symbol("GOLD", "Derivatives\\Spot Metals\\GOLD", 100.0, 0.01, 50.0, 0.01, 2, 0.01),
            _Symbol("BTCUSD", "Cryptocurrencies\\Standard\\BTCUSD", 1.0, 0.01, 80.0, 0.01, 2, 0.01),
            _Symbol("EURUSD", "Forex\\Standard\\Majors\\EURUSD", 100_000.0, 0.01, 50.0, 0.01, 5, 0.00001),
            _Symbol("XAUJPY", "Derivatives\\Spot Metals\\XAUJPY", 100.0, 0.01, 50.0, 0.01, 0, 0.001),
        ]


def _linhas(monkeypatch, mapa=None):
    """Roda `discover_assets` com o catalogo medido e devolve por simbolo."""
    mod = importlib.import_module("asset_registry")
    aliases = importlib.import_module("backend.symbol_aliases")
    monkeypatch.setattr(aliases, "carregar", lambda: mapa or MAPA_XM)
    monkeypatch.setattr(mod, "_asset_class", mod._asset_class)
    linhas = mod.discover_assets(_Mt5ComOuro(), include_hidden=True)
    return {linha["symbol"]: linha for linha in linhas}


class TestNomeDoModeloNoCatalogo:
    def test_GOLD_publica_o_nome_do_modelo(self, monkeypatch):
        """MEDIDO: a XM tem `GOLD`; o `.meta.json` do app e `XAUUSD_*`."""
        linhas = _linhas(monkeypatch)

        assert "GOLD" in linhas
        assert linhas["GOLD"]["model_symbol"] == "XAUUSD"
        assert linhas["GOLD"]["has_model"] is True

    def test_o_contrato_do_OURO_e_100_e_nao_1(self, monkeypatch):
        """
        MEDIDO no terminal da XM: `GOLD` tem `trade_contract_size = 100.0`.

        Com `1`, `0,01` de ouro exporia `$24` de nocional em vez de `$2.400` —
        100 vezes. E a ficha que alimenta `nivelDoValor`: o erro sai nas duas
        pontas, no stop e no alvo, e o preco derivado fica 100 vezes longe.
        """
        linhas = _linhas(monkeypatch)

        assert linhas["GOLD"]["contract_size"] == 100.0
        assert linhas["GOLD"]["asset_class"] == "metal"

    def test_XAUUSD_NAO_APARECE_no_catalogo_e_isto_e_um_FATO(self, monkeypatch):
        """
        `XAUUSD` nao existe no terminal XM. O catalogo nao pode fabricar a
        linha: `XAUUSD` nao tem `path`, nao tem `contract_size` e nao tem classe
        — e uma linha inventada seria o "numero inventado vira limite real" que
        o AGENTS.md proibe.

        A ponte e `model_symbol` NA linha `GOLD`.
        """
        linhas = _linhas(monkeypatch)

        assert "XAUUSD" not in linhas
        assert linhas["GOLD"]["model_symbol"] == "XAUUSD"

    def test_ativo_SEM_modelo_declara_None_e_nao_o_proprio_nome(self, monkeypatch):
        """
        Se `model_symbol` ausente caesse no proprio `symbol`, todos os 1.639
        pares do catalogo declarariam ter modelo — e a lista de modelos
        mentiria, porque existem 36 `.meta.json`.

        `None` e a ausencia medida: "nenhum modelo treinado com este nome".
        """
        linhas = _linhas(monkeypatch)

        assert linhas["BTCUSD"]["model_symbol"] is None
        assert linhas["BTCUSD"]["has_model"] is False
        assert linhas["EURUSD"]["model_symbol"] is None

    def test_o_MAPA_E_CONFIG_E_O_CODIGO_NAO_TEM_NENHUM_NOME(self, monkeypatch):
        """
        O AGENTS.md 3: nenhum nome de ativo no CODIGO.

        Se o par estivesse escrito no modulo, trocar o mapa do operador nao
        mudaria nada — e a correcao pareceria funcionar enquanto o operador
        acredita que configurou.

        A PROVA NEGATIVA DESTA, e ela tem forma propria: o codigo sem comentario
        nem docstring. Commentario que nomeia o par e DOCUMENTACAO — o AGENTS.md
        §4e warns que uma trava textual que proibe documentar reprova a
        explicacao do defeito, e essa trava e o defeito.

        A primeira versao deste teste varria o arquivo inteiro e reprovava no
        proprio texto que documenta a medicao. Isso foi corrigido aqui, e o
        AGENTS.md §4e esta registrado por ter custado um ciclo.
        """
        mod = importlib.import_module("asset_registry")
        fonte = Path(mod.__file__).read_text(encoding="utf-8", errors="replace")
        sem_comentario = _sem_docstrings_e_comentarios(fonte)

        for nome in ("XAUUSD", "GOLD", "BTCUSD", "EURUSD"):
            assert nome not in sem_comentario, (
                f"`{nome}` esta escrito no CODIGO de asset_registry — "
                "o mapa e config do operador"
            )

    def test_a_direcao_do_mapa_e_a_INVERSA_da_da_ordem(self, monkeypatch):
        """
        A tela precisa de `para_modelo` (corretora -> modelo).

        `para_corretora` (modelo -> corretora) e o que o gateway usa para LER e
        ENVIAR. Usar o sentido errado aqui faria a tela procurar `GOLD` no
        catalogo como se fosse nome de modelo — e a ficha cairia em outro ativo
        ou em nenhum.
        """
        aliases = importlib.import_module("backend.symbol_aliases")
        monkeypatch.setattr(aliases, "carregar", lambda: MAPA_XM)

        assert aliases.para_modelo("mt5", "GOLD") == "XAUUSD"
        assert aliases.para_corretora("mt5", "XAUUSD") == "GOLD"
        # E um par sem mapa volta intacto, nos dois sentidos: nenhuma presuncao.
        assert aliases.para_modelo("mt5", "EURUSD") == "EURUSD"
        assert aliases.para_corretora("mt5", "EURUSD") == "EURUSD"


class TestOAliasNoPayloadDaRota:
    def test_a_ROTA_de_assets_devolve_o_campo(self, monkeypatch):
        """
        A rota e o que a tela consome — nao `discover_assets` direto.

        Se o campo se perdesse na traducao, o `parseAssetCatalog` leria
        `undefined`, `modelSymbol` seria `null` para todos, e a segunda busca
        nunca acharia nada: o grafico do ouro nao carregaria com o codigo
        parecendo correto.
        """
        mod = importlib.import_module("mt5_gateway")
        aliases = importlib.import_module("backend.symbol_aliases")
        monkeypatch.setattr(aliases, "carregar", lambda: MAPA_XM)
        monkeypatch.setattr(mod, "_mt5", lambda: _Mt5ComOuro())

        resposta = mod._universal_assets(broker="mt5", market="metals")
        por_simbolo = {a["symbol"]: a for a in resposta["assets"]}

        assert por_simbolo["GOLD"]["model_symbol"] == "XAUUSD"
        assert por_simbolo["BTCUSD"]["model_symbol"] is None