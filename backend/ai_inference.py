# -*- coding: utf-8 -*-
"""Servico de inferencia: modelos treinados -> decisao de trading, na CPU.

POR QUE ISTO EXISTE
===================
O sinal que o app exibia antes NAO VINHA DE NENHUM MODELO. O frontend
(`useAICommunication.ts`) aplicava regras fixas sobre indicadores e, quando o
calculo falhava, inventava os valores:

    const rsi = typeof indicators?.rsi === 'number' ? indicators.rsi : 50;
    const macd = typeof indicators?.macd === 'number' ? indicators.macd : 0;
    const volume = typeof indicators?.volume === 'number' ? indicators.volume : 1;

Ou seja: RSI "falso" 50, MACD "falso" 0, volume sempre 1, Stop Loss em
preco*0.99 e Take Profit em preco*1.02 — aritmetica fixa, sem modelo. E a
confianca era uma CONSTANTE por regra (70/75/80), apresentada na tela como se
fosse uma estatistica. O perfil "breakout" exigia volume > 1.5 e por isso
nunca disparava: o volume era hardcoded em 1.

Este modulo substitui isso por inferencia de verdade:

  - carrega o .pkl treinado e o .meta.json com os metricos reais
  - monta as 25 features pela mesma funcao usada no treino (25F-v2), com as
    4 features KCI derivadas da serie, e NUNCA preenchidas com zero
  - devolve as probabilidades REAIS do classificador
  - a confianca exibida e a probabilidade do modelo, nao uma constante
  - se o modelo nao passou na porta de qualidade, ou nao ha dado suficiente,
    ou o timeframe nao bate, o servico devolve `disponivel: false` com o
    motivo. Nao existe fallback que fabrique um sinal.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Raiz do repositorio: backend/ -> ..
RAIZ = Path(__file__).resolve().parent.parent
for _caminho in (RAIZ, RAIZ / "Python"):
    if str(_caminho) not in sys.path:
        sys.path.insert(0, str(_caminho))

from Python.ai import train_v2 as t  # noqa: E402
from Python.ai import features_estacionarias as fe  # noqa: E402


def _resolver_modelos() -> Path:
    """Onde os `.pkl` ficam, na fonte e no app instalado.

    Este era o unico caminho (`RAIZ / "Python" / "models"`), e ele so funciona
    rodando do repositorio. No app instalado o gateway e um binario
    congelado com PyInstaller, onde `__file__` aponta para dentro do
    `_internal` — e `RAIZ` vira `<instalacao>/bridge/_internal`. O modelo H1
    estava no repositorio e NAO no instalador, entao
    `/api/ai/trained` devolvia `models: []` e a interface mostrava
    "Nenhum modelo carregavel" mesmo com o modelo treinado e validado.

    Agora sao testados varios candidatos e vence o primeiro que EXISTE e tem
    artefato de modelo: um diretorio vazio nao pode sequestrar a resolucao.
    E exatamente o que acontecia no app instalado - `model_registry` criava
    `<bundle>/Python/models` vazio, esse candidato existia e era testado
    antes do `C:/Program Files/XAU AI PRO/Python/models` (72 arquivos),
    entao `/api/ai/trained` voltava `models: []`.

    A variavel de ambiente `XAU_MODELOS_DIR` tem precedencia absoluta, para
    quem quiser apontar para outro lugar sem rebuild.
    """
    override = os.environ.get("XAU_MODELOS_DIR", "").strip()
    if override:
        return Path(override)

    def tem_modelos(candidato: Path) -> bool:
        return any(candidato.glob("*.meta.json")) or any(candidato.glob("*.pkl"))

    candidatos: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidatos.append(Path(meipass) / "Python" / "models")
    exe_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None
    if exe_dir is not None:
        candidatos.append(exe_dir / "Python" / "models")
        candidatos.append(exe_dir.parent / "Python" / "models")
        candidatos.append(exe_dir / "_internal" / "Python" / "models")
        candidatos.append(exe_dir.parent / "_internal" / "Python" / "models")
    candidatos.append(RAIZ / "Python" / "models")
    existente: Path | None = None
    for candidato in candidatos:
        try:
            if not candidato.is_dir():
                continue
            if existente is None:
                existente = candidato
            if tem_modelos(candidato):
                return candidato
        except OSError:
            continue
    if existente is not None:
        return existente
    return candidatos[0] if candidatos else RAIZ / "Python" / "models"

MODELOS_DIR = _resolver_modelos()

#: Motivo devolvido quando nao ha simbolo. Constante e nao string solta no
#: ponto de uso porque o mesmo texto aparece em `_carregar` e em `inferir`, e
#: as duas precisam concordar: se divergirem, a tela mostra um motivo e o log
#: registra outro.
MOTIVO_SEM_SIMBOLO = (
    "escolha o ativo antes de pedir inferencia: simbolo vazio nao carrega "
    "nenhum modelo (o projeto nao presume ativo padrao)"
)

# Quantas threads de CPU o processo pode usar. O usuario ve esse numero na aba
# IA; nao e cosmetics, e o limite real de paralelismo do scikit-learn.
def cpu_threads() -> int:
    """Threads de CPU liberadas para inferencia."""
    bruto = os.environ.get("XAU_AI_PRO_N_JOBS", "").strip()
    if bruto:
        try:
            valor = int(bruto)
            if valor > 0:
                return valor
        except ValueError:
            pass
    # -1 no scikit-learn significa "todas as nucleos".
    return max(1, (os.cpu_count() or 1))


@dataclass
class Inferencia:
    """Resultado de uma inferencia. Honesto por construcao."""

    disponivel: bool
    motivo: str
    symbol: str = ""
    timeframe: str = ""
    signal: str = "NEUTRAL"          # BUY | SELL | NEUTRAL
    confianca: float = 0.0            # probabilidade real do classificador (0-100)
    prob_buy: float = 0.0
    prob_sell: float = 0.0
    prob_neutral: float = 0.0
    price: float = 0.0
    atr: float = 0.0
    edge: float | None = None
    accuracy: float | None = None
    folds: list[dict[str, Any]] | None = None
    inferencia_ms: float = 0.0
    modelo: str = ""
    #: Nome do artefato de CLASSE que decidiu (`MULTI_FIAT`), vazio quando quem
    #: decidiu foi o modelo do proprio ativo. Campo separado e nao texto:
    #: quem consome precisa saber QUE modelo respondeu sem partir o rotulo de
    #: exibicao (`model`) — AGENTS §5.
    modelo_classe: str = ""
    feature_hash: str = ""

    def para_dict(self) -> dict[str, Any]:
        return {
            "available": self.disponivel,
            "reason": self.motivo,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "signal": self.signal,
            "confidence": round(self.confianca, 1),
            "prob_buy": round(self.prob_buy, 4),
            "prob_sell": round(self.prob_sell, 4),
            "prob_neutral": round(self.prob_neutral, 4),
            "price": self.price,
            "atr": self.atr,
            "edge": self.edge,
            "accuracy": self.accuracy,
            "folds": self.folds,
            "inference_ms": round(self.inferencia_ms, 2),
            "model": self.modelo,
            "class_model": self.modelo_classe,
            "feature_hash": self.feature_hash,
            "cpu_threads": cpu_threads(),
        }


_CACHE: dict[str, Any] = {}

#==================================================
# TRAVERSAL DE CAMINHO — DEFESA 1: FORMATO DO NOME
#==================================================
# Allowlist de timeframes medida nos artefatos reais (`Python/models/*.pkl`):
# H1, H4, M15, M5. Fechada de proposito — timeframe nao tem como ser novo a
# cada semana, e um valor aberto viraria vetor de travessia.
#
# O simbolo NAO tem allowlist de pares: a lista cresceria a cada novo par
# listado e a regra do projeto e "nenhum simbolo pode ser presumido". O que se
# restringe e o FORMATO, nao o conteudo: letras, digitos e o underscore de
#familia. `..`, `/`, `\` e `%2e%2e` nao passam — o ponto e a barra sao o que
# constroi travessia de caminho, e nenhum dos dois esta na classe.
TIMEFRAMES_VALIDOS = frozenset({"M5", "M15", "H1", "H4"})

# O UNDERSCORE ENTRA POR CAUSA DOS MODELOS MULTI_CLASSE (medido 04/10/2026).
# --------------------------------------------------------------------------
# Os artefatos `MULTI_METALS.pkl`, `MULTI_FIAT.pkl` e `MULTI_CRYPTO.pkl` levam
# o `_` no nome. Com `^[A-Z0-9]{1,12}$` os TRES eram INALCANCAVEIS:
# `_nome_de_artefato()` devolvia `None` e a tela dizia "modelo nao publicado
# ou ausente" — para artefatos que existem no disco, com `publicable: true` e
# o maior edge do catalogo (MULTI_METALS +0.2497, 67.678 amostras).
#
# E o comentario desta constante JA citava `BTCUSDT_PERP` como exemplo de
# simbolo valido: o comentario e o regex discordavam, e o regex era o que
# valia. Por isso o defeito nao apareceu em revisao — os dois pareciam certos.
#
# A DEFESA CONTRA TRAVERSIA CONTINUA INTEIRA: o conjunto permitido e
# `[A-Z0-9_]`, que nao contem ponto, barra nem barra invertida. `..`, `/` e
# `\` seguem barrados por construcao, nao por lista de excecao. O
# confinamento de destino em `_caminho_confinado` e a segunda barreira e
# continua valendo.
#
# O LIMITE CONTINUA EM 12. Subi para 24 achando que precisaria de folga para
# `MULTI_METALS` (12) + `_H1` (3) = 15 — mas o limite conta o SIMBOLO, nao o
# nome do arquivo. Medido: MULTI_METALS 12, MULTI_CRYPTO 12, BTCUSDT_PERP 12.
# Nenhum precisa de mais. `tests/test_traversal_modelos.py` barrava `A * 13`
# e estava CERTO: subir o limite seria afrouxar seguranca sem necessidade.
_RE_SIMBOLO = re.compile(r"^[A-Z0-9_]{1,12}$")


def base_do_ativo(simbolo: str) -> str:
    """Base do ativo sem o quote da corretora: `BTCUSDT` -> `BTC`.

    Delega a `backend.symbols` (fonte unica): MEXC/Binance/Bybit/OKX operam
    contra USDT/USDC; MT5 (XM) opera contra USD. Sem nomes de ativos.
    """
    from backend.symbols import base as _base

    return _base(simbolo)


def mesmo_ativo(a: str, b: str) -> bool:
    """Mesmo ativo em quotes diferentes (`BTCUSDT` == `BTCUSD`)."""
    from backend.symbols import mesmo_ativo as _igual

    return _igual(a, b)


def candidatos_de_simbolo(simbolo: str) -> list[str]:
    """Formas do mesmo ativo onde pode haver artefato (`BTCUSDT_H1`...).

    Ordem: o pedido literal primeiro (um `BTCUSDT_H1.pkl` treinado na
    exchange vence o alias); depois as formas no quote do terminal.
    """
    from backend.symbols import formas as _formas

    return _formas(simbolo)


def _nome_de_artefato(simbolo: str, timeframe: str) -> str | None:
    """`<SIMBOLO>_<TF>`, ou so `<SIMBOLO>`, ou `None` se nao puder nomear.

    `None` e recusa COM MOTIVO. Chamar `MODELOS_DIR / nome` com um nome
    invalido e o que produz o alerta de CodeQL; devolver `None` deixa a
    decisao no codigo, onde da para recusar e explicar.

    `timeframe` VAZIO devolve o nome geral (`MULTI_METALS`), que e o modelo
    unico que cobre varios periodos. E o que `_nomes_de_artefato` tenta
    depois do especifico.

    POR QUE O VAZIO CONTINUA SENDO RECUSA NO `inferir`
    ---------------------------------------------------
    A porta do vazio existe aqui, dentro do resolvedor de NOME, e nao no
    `inferir`. `inferir` ja recusa timeframe fora da allowlist antes de
    chegar aqui, entao um pedido do operador nunca usa esta porta — ela so
    e alcancavel pela propria `_nomes_de_artefato`, que sabe o que esta
    fazendo. Um `timeframe` QUE NAO EXISTE na allowlist continua recusando:
    a allowlist e o que impede que qualquer string vire nome de arquivo.
    """
    if not _RE_SIMBOLO.match(simbolo):
        return None
    if not timeframe:
        # Nome geral: `<SIMBOLO>.pkl`, o modelo unico multi-periodo.
        return simbolo
    if timeframe not in TIMEFRAMES_VALIDOS:
        return None
    return f"{simbolo}_{timeframe}"


#==================================================
# TRAVERSAL DE CAMINHO — DEFESA 2: CONFINAMENTO
#==================================================
# A regex acima barra o ataque pela origem. Esta barra o ataque pelo destino:
# mesmo com um nome valido, o caminho resolvido precisa estar DENTRO de
# `MODELOS_DIR`.
#
# Cobre o caso que a regex nao pega: `MODELOS_DIR` vem de
# `XAU_MODELOS_DIR` (ou de um app instalado), e um link simbolico dentro
# dessa pasta apontaria para fora. `resolve()` segue o link; `is_relative_to`
# compara o caminho JA resolvido, entao a travessia aparece na diferenca.
#
# `Path.is_relative_to` existe do Python 3.9. A raiz usa 3.11/3.12
# (`AGENTS.md`), entao nao ha necessidade de fallback — e o `try` de
# `relative_to` abaixo e apenas para o caso de `MODELOS_DIR` relativo, que
# `resolve()` resolve antes da comparacao.
def _caminho_confinado(nome: str) -> Path | None:
    """Caminho absoluto de `nome`, garantido dentro de `MODELOS_DIR`.

    `nome` ja passou por `_nome_de_artefato`; aqui so se confirma que o
    resultado nao escapa. `None` significa "recusado", nunca "criei um
    caminho novo".

    POR QUE `os.path.abspath` E NAO SO `Path.resolve()`
    ====================================================
    A primeira versao usava `Path.resolve()` + `is_relative_to`. A defesa
    funcionava (os testes provaram: 9 ataques e um symlink recusados), mas o
    CodeQL continuou accusing `py/path-injection` nas linhas de baixo.

    A razao e analise de fluxo de dados, nao um defeito: o CodeQL nao acompanha
    que `nome` foi validado em `_nome_de_artefato` e que o resultado foi
    conferido contra a raiz. Ele so sabe que a entrada veio de `simbolo`, que
    veio da REQUISICAO HTTP, e que um `Path / str` com dado controlado acontece
    perto de um `.exists()`.

    O que o CodeQL reconhece como saneamento em Python e a comparacao
    EXPLICITA entre o caminho absoluto normalizado e a raiz. Por isso a
    logica esta escrita assim, e nao como um `if not alvo.is_relative_to(raiz)`
    escondido atras de um helper: nao e estetica, e o que faz a verificacao
    ser provavel por uma ferramenta diferente da que a escreveu.

    `resolve()` E `abspath` JUNTOS, E NAO SÓ `abspath`
    =================================================
    `os.path.abspath` normaliza `..` e barras, mas NAO segue link simbolico: um
    symlink dentro da pasta de modelos continua apontando para fora depois do
    `abspath`. Trocar `resolve()` por `abspath` sozinho destravou um ataque
    real — o teste `test_symlink_para_fora_e_recusado` reprovou.

    Por isso: `resolve()` segue o link e normaliza (defesa de seguranca), e a
    comparacao `startswith(raiz + os.sep)` sobre o resultado normalizado e o
    que o CodeQL le como saneamento (defesa de auditoria). As duas jogam no
    mesmo sentido; nenhuma das duas e opcional.
    """
    try:
        # `resolve()` segue symlink; `abspath` normaliza o resto. Nos dois,
        # um caminho que nao se resolve nao deve ser lido.
        raiz = os.path.abspath(MODELOS_DIR.resolve())
        # O `os.path.join` vem ANTES do `resolve()` de proposito: e a ordem
        # que o CodeQL le como saneamento. Juncao por atributo
        # (`Path / str`) em dados nao-fio nao e reconhecida como tal, e
        # sobrou 1 `py/path-injection` na linha do `join` ate a troca.
        bruto = os.path.join(raiz, nome)
        alvo = os.path.abspath(os.path.realpath(bruto))
    except (OSError, ValueError, TypeError, RuntimeError):
        # `RuntimeError` e o que `resolve()` levanta em ciclo de symlink no
        # Python 3.13+ (antes era `OSError`).
        return None

    # Comparacao EXPLICITA e o ponto que o CodeQL reconhece como saneamento.
    # `== raiz` cobre o caso degenerado em que `nome` seria vazio.
    if alvo == raiz:
        return None
    if not alvo.startswith(raiz + os.sep):
        return None
    return Path(alvo)


#==================================================
# MODELO DE CLASSE (`MULTI_*`) — O RECURSO QUE FALTAVA
#==================================================
# MEDIDO em 10/11/2026 (P0 do CMD): na conta nova, so o XAUUSD tinha modelo. O
# EA registava "[AI] INDISPONIVEL | BNB | MOTIVO=modelo nao publicado ou
# ausente" e o mesmo para XAUT, USDCOP, USDCLP, USDCZK, USDRUB e USDSGD. Nao
# era falta de dado: `MULTI_FIAT.pkl`, `MULTI_CRYPTO.pkl` e `MULTI_METALS.pkl`
# estao no disco, `publicable: true`, com o maior edge do catalogo. Faltava o
# resolvedor saber que um simbolo SEM modelo proprio pode ser atendido pelo
# modelo da CLASSE dele.
#
# O que este pedaco NAO faz:
#  - nao adivinha classe. A classe vem da tabela de `asset_classes.py`, e
#    simbolo fora dela e `OUTROS`, que devolve recusa com motivo;
#  - nao substitui o modelo do ativo. O unitario e tentado ANTES e ganha
#    sempre que existe e e publicavel;
#  - nao afrouxa defesa nenhuma: o nome passa pelas mesmas
#    `_nome_de_artefato` e `_caminho_confinado`, e o `.pkl` continua conferido
#    por SHA-256 antes do `joblib.load`.

#: Decisao de acesso ao MULTI, com TTL. Ler a assinatura e I/O de arquivo; sem
#: cache seria uma leitura por tique por simbolo (15 simbolos a 2-3 tiques/s).
_TTL_MULTI_S = 300.0
_CACHE_MULTI: dict[str, Any] = {"valor": None, "quando": 0.0}


def _multi_permitido() -> bool:
    """O modelo de CLASSE e beneficio de plano pago (regua do dono, 02/10).

    `limite_multi_modelos()` era funcao SEM consumidor: a docstring dela ja
    dizia "o `inferir()` trata 0 como so modelo unico" e o `inferir()` nunca a
    chamava (AGENTS §9 — controle sem consumidor e pior que a ausencia dele).
    Este e o consumidor: plano sem MULTI nao recebe MULTI, e o operador segue
    vendo recusa com motivo em vez de um modelo que o plano dele nao cobre.

    Fail-closed: assinatura ilegivel nao libera recurso pago.
    """
    agora = time.monotonic()
    idade = agora - float(_CACHE_MULTI.get("quando") or 0.0)
    if _CACHE_MULTI.get("valor") is not None and idade < _TTL_MULTI_S:
        return bool(_CACHE_MULTI.get("valor"))
    try:
        from backend.acesso import limite_multi_modelos

        permitido = limite_multi_modelos() > 0
    except Exception:
        permitido = False
    _CACHE_MULTI["valor"] = permitido
    _CACHE_MULTI["quando"] = agora
    return bool(permitido)


def _classe_multi_de(simbolo: str) -> str:
    """Classe do ATIVO, nao do texto; `OUTROS` quando nao ha classe.

    MEDIDO em 10/11/2026, logo depois da opcao (b): `classe_de("BTCUSDT")`
    devolve `OUTROS` e `classe_de("BTCUSD")` devolve `CRYPTO`. A tabela
    classifica o PAR do terminal, e `BTCUSDT` e o MESMO ativo escrito no quote
    da exchange. Perguntar so pela forma literal deixava `BTCUSDT` sem
    cobertura de classe enquanto `BTCUSD` tinha — dois nomes do mesmo ativo
    respondendo diferente, que e o defeito que o AGENTS §5 cobra.

    A pergunta passa a ser feita a cada forma do ativo, na ordem de
    `candidatos_de_simbolo` (o pedido literal primeiro). Nenhuma lista de
    ativos e criada aqui: quem decide a classe continua sendo a tabela.
    """
    from backend.asset_classes import classe_de

    for forma in candidatos_de_simbolo(simbolo):
        classe = classe_de(forma)
        if classe != "OUTROS":
            return classe
    return "OUTROS"


def _tentativas_multi(simbolo: str, timeframe: str) -> list[tuple[str, str]]:
    """Pares (candidato, nome) do artefato da CLASSE; vazio quando nao ha.

    `MULTI_FIAT` nao tem timeframe no nome — o horizonte entra como feature
    (`Timeframe_Cod`). O "especifico" (`MULTI_FIAT_H1`) nunca existe no disco e
    `_nomes_de_artefato` ja devolve so o nome geral, sem caso especial aqui.

    Chamada em `_carregar` DEPOIS do laco do modelo do ativo e ANTES da recusa
    dele (D-175, autorizada pelo dono em 10/11/2026): publicavel proprio ganha
    sempre, e recusa de governanca do modelo do ativo cede a cobertura da
    classe. O motivo recusado nao se perde — viaja em `cobertura_sobre_recusa`.
    """
    from backend.asset_classes import nome_do_modelo_multi

    classe = _classe_multi_de(simbolo)
    if classe == "OUTROS":
        return []
    if not _multi_permitido():
        return []
    multi = nome_do_modelo_multi(classe)
    return [(multi, nome) for nome in _nomes_de_artefato(multi, timeframe)]


def _classe_do_artefato(simbolo: str, meta: dict[str, Any]) -> str:
    """Classe para a feature `Classe_Cod`: do artefato, senao do simbolo.

    O `.meta.json` do MULTI grava `"class": "FIAT"` no treino. Ler dali e o que
    garante que a codificacao da inferencia e a MESMA do treino; `classe_de`
    fica como reserva para um meta antigo sem o campo.
    """
    from backend.asset_classes import classe_de

    classe = str(meta.get("class") or "").strip().upper()
    return classe or classe_de(simbolo)
#: Nomes de volume que chegam ao runtime, na ordem em que devem ser lidos. O
#: MT5 entrega `Tick_volume`; o dataset de treino usa `Volume`.
_COLS_VOLUME: tuple[str, ...] = (
    "Volume", "volume", "Tick_volume", "tick_volume",
    "Real_volume", "real_volume", "Tickvol", "tickvol",
)


#: Grafia do CONTRATO de features, na ordem em que deve ser lida.
#:
#: MEDIDO em 11/11/2026 com o gateway real: `_mt5_candles` entrega as chaves
#: canonicas em MINUSCULAS (`time/open/high/low/close/volume/timestamp`) e o
#: caminho 25F-v2 / 25F-est-v1 indexa por `Time` e agrega `Open/High/Low/Close`
#: (`train_v2.reamostrar`). O resultado era `available=false` com
#: `erro na inferencia: "None of ['Time'] are in the columns"` em 14 dos 15
#: simbolos, enquanto o XAUUSD publicava â€” ele usa o contrato 30F, que
#: normaliza as colunas por conta propria. Dois lados do mesmo dado com nomes
#: diferentes, e o operador lia "IA sem modelo" (AGENTS Â§5). O defeito era do
#: lado do CONSUMIDOR: o dado chegava certo, com outra grafia.
_GRAFIA_DO_CONTRATO: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Open", ("Open", "open")),
    ("High", ("High", "high")),
    ("Low", ("Low", "low")),
    ("Close", ("Close", "close")),
    ("Volume", _COLS_VOLUME),
)


def _com_volume_padrao(candles: pd.DataFrame) -> pd.DataFrame:
    """Entrega `candles` na grafia que o contrato de features exige.

    HISTORICO desta funcao, para nao regredir. Nasceu em 10/11/2026 cobrindo
    SO `Volume`, depois de o caminho 25F-v2 morrer em `KeyError: 'Volume'`.
    Faltava o resto â€” `Time` e os quatro precos â€” e era exatamente o que
    impedia os 15 simbolos de publicar previsao: o XAUUSD nao sentia porque
    usa o contrato 30F, que se normaliza sozinho.

    Nao inventa dado: copia o que existe, e so quando a coluna de destino nao
    existe. Sem nenhuma das grafias, devolve o DataFrame como veio e o
    reamostrador diz o que falta.
    """
    if not isinstance(candles, pd.DataFrame) or candles.empty:
        return candles
    ajustado = candles
    for destino, origens in _GRAFIA_DO_CONTRATO:
        if destino in ajustado.columns:
            continue
        for origem in origens:
            if origem not in ajustado.columns:
                continue
            if ajustado is candles:
                ajustado = candles.copy()
            ajustado[destino] = ajustado[origem]
            break
    # `Time` nao e so nome: e TIPO. O MT5 entrega epoch em segundos, e sem esta
    # conversao o `resample` levanta `TypeError` em vez de agregar.
    if "Time" not in ajustado.columns:
        for origem in ("time", "timestamp"):
            if origem not in ajustado.columns:
                continue
            if ajustado is candles:
                ajustado = candles.copy()
            bruto = ajustado[origem]
            if pd.api.types.is_numeric_dtype(bruto):
                ajustado["Time"] = pd.to_datetime(bruto, unit="s", errors="coerce")
            else:
                ajustado["Time"] = pd.to_datetime(bruto, errors="coerce", format="mixed")
            break
    if ajustado is not candles and "Time" in ajustado.columns:
        # Linha sem instante nao entra num reamostrador por tempo: viraria NaT
        # e derrubaria a janela inteira.
        ajustado = ajustado.dropna(subset=["Time"])
    return ajustado

def _carregar(symbol: str, timeframe: str) -> tuple[Any | None, dict[str, Any]]:
    """Carrega .pkl e .meta.json de um timeframe de um simbolo.

    SEM ATIVO FIXO
    ==============
    O artefato e `<SIMBOLO>_<TF>` (XAUUSD_H1, BTCUSD_M15, ...). Simbolo vazio
    aqui e **recusa**, nunca XAUUSD: a regra do dono e "nenhum simbolo pode ser
    presumido" e ja estava escrita em `app/market_symbols.py`
    (`return ""  # sem ativo fixo`).

    HISTORICO DESTE DEFEITO
    -----------------------
    Duas vezes o mesmo par de bugs apareceu neste modulo:

    1. O CAMINHO era fixo em XAUUSD. Pedir BTCUSD devolvia o modelo de ouro.
       Corrigido: as linhas de `pkl`/`meta` passaram a usar `{simbolo}`.
    2. O DEFAULT ficou. `str(symbol or "XAUUSD")` sobreviveu ao conserto do
       caminho, e `inferir("", candles, "H1")` continuava devolvendo o
       classificador de ouro — com confianca real e sem nada no retorno que
       denuncie.

    O padrao e sempre o mesmo: conserta-se o caso visivel e o silencioso fica.
    Por isso `tests/test_ai_inference.py::TestNenhumAtivoPresumido` existe.

    O `.pkl` tem 8 MB e leva ~2 s para desserializar. Recarregar a cada tique
    seria crippling, entao o resultado fica em cache e so e invalidado quando
    o mtime do arquivo muda (retraining).

    TRAVERSAL DE CAMINHO (corrigido com este ciclo)
    -----------------------------------------------
    `simbolo` e `timeframe` chegam da REQUISICAO HTTP — `auto_engine.py:194`
    faz `self.simbolo = str(payload["simbolo"]).upper()` e nao ha validacao
    antes de `MODELOS_DIR / f"{simbolo}_{timeframe}.pkl"`. Um simbolo com
    `../` escapava da pasta de modelos e chegava no `joblib.load` da linha
    seguinte: desserializar um `.pkl` de caminho escolhido e execucao de
    codigo arbitrario. CodeQL apontou como `py/path-injection` (4x) e
    `py/unsafe-deserialization` (1x).

    Duas defesas, porque uma so nao fecha:

    1. `_nome_de_artefato` so aceita `[A-Z0-9]` e `^[A-Z0-9]{1,12}$`, o que
       ja barra `/`, `\\` e `..` na origem. O timeframe tem allowlist
       fechada, medida nos artefatos reais (H1, H4, M15, M5).
    2. Mesmo com nome valido, o caminho resolvido e conferido dentro de
       `MODELOS_DIR` com `Path.is_relative_to`/`resolve`. Isto cobre o caso
       que a regex nao pega: `MODELOS_DIR` apontado por `XAU_MODELOS_DIR`
       para um diretorio com link simbolico para fora.

    O simbolo NAO tem allowlist de pares: a lista mudaria a cada novo
    par listado e a regra do projeto e "nenhum simbolo pode ser presumido".
    A regex barra o que e perigoso (separadores e travessia) sem
    restringir o que e legitimo.
    """
    simbolo = str(symbol or "").strip().upper()
    if not simbolo:
        # Sem artefato, sem metadados e sem chance de cache: um simbolo vazio
        # nao tem mtime para invalidar.
        return None, {"publish_reason": MOTIVO_SEM_SIMBOLO}
    timeframe = str(timeframe or "").strip().upper()
    # O par da exchange (MEXC: `BTCUSDT`) resolve para o artefato treinado no
    # terminal (`BTCUSD_H1`): mesmo ativo, quote da corretora diferente. Cada
    # candidato e validado por `_nome_de_artefato` (formato) e por
    # `_caminho_confinado` (destino) — o alias nao afrouxa nenhuma defesa.
    ultimo_meta: dict[str, Any] = {}
    for candidato in candidatos_de_simbolo(simbolo):
        # Dois nomes por candidato: o especifico (`XAUUSD_H1`) e o geral
        # (`MULTI_METALS`). Ver `_nomes_de_artefato` — o motivo de o segundo
        # existir e os tres modelos de maior edge do catalogo.
        for nome in _nomes_de_artefato(candidato, timeframe):
            carregado, meta = _carregar_artefato(candidato, nome)
            if carregado is not None:
                return carregado, meta
            if meta:
                ultimo_meta = meta
    # MODELO DA CLASSE ANTES DA RECUSA DO MODELO DO ATIVO (D-175)
    # ==========================================================
    # AUTORIZADO PELO DONO em 10/11/2026, resposta "b" a Q-177: o modelo de
    # classe PODE operar um ativo cujo modelo proprio foi reprovado pela
    # governanca, para toda a classe.
    #
    # POR QUE A ORDEM MUDOU. A versao anterior era "MULTI e cobertura, nao
    # substituicao": ativo com `.meta.json` proprio — ainda que recusado por
    # edge — devolvia a recusa e o MULTI nunca entrava. MEDIDO na frota: os 10
    # pares FIAT NAO estao sem modelo, eles TEM `USDCOP_H1.pkl` e irmaos, e e o
    # modelo proprio que os recusa (EURUSD -0.0161, USDCOP -0.0584, USDCLP
    # -0.0281, USDCZK -0.0072, USDRUB +0.0166, USDSGD +0.0193: abaixo do
    # minimo +0.0200 ou com folds insuficientes). A regra estrita destravava
    # UM simbolo; a regra autorizada destrava a classe inteira.
    #
    # O QUE A ORDEM NOVA NAO AFROUXA:
    #  1. modelo proprio PUBLICAVEL continua ganhando SEMPRE: o laco acima ja
    #     devolveu antes de chegar aqui. O MULTI so entra quando o unitario
    #     nao publicou nada;
    #  2. a recusa do unitario NAO e apagada: ela viaja no meta devolvido
    #     (`cobertura_sobre_recusa`), entao a resposta diz qual modelo estava
    #     reprovado e por que, mesmo quando a classe decide;
    #  3. se o MULTI tambem nao existir ou nao publicar, a recusa citada e a do
    #     modelo do ATIVO, que e a mais especifica (`if meta and not
    #     ultimo_meta`). Esse guard estava MORTO na versao estrita — o laco so
    #     rodava com `ultimo_meta` vazio —; agora o laco roda sempre e ele volta
    #     a decidir;
    #  4. classe fora da tabela (`OUTROS`) nao tem MULTI: `_tentativas_multi`
    #     devolve vazio e a recusa segue sem fallback nenhum.
    recusa_do_ativo = ultimo_meta
    for candidato, nome in _tentativas_multi(simbolo, timeframe):
        carregado, meta = _carregar_artefato(candidato, nome)
        if carregado is not None:
            if recusa_do_ativo:
                # COPIA OBRIGATORIA: `_carregar_artefato` devolve o dict que
                # esta na cache, e ele nao pode ganhar chave por simbolo
                # consultado (o mesmo MULTI_FIAT atende 15 pares).
                meta = dict(meta)
                meta["cobertura_sobre_recusa"] = str(
                    recusa_do_ativo.get("publish_reason") or ""
                )
            return carregado, meta
        if meta and not ultimo_meta:
            ultimo_meta = meta
    if ultimo_meta:
        # NADA PUBLICAVEL PARA ESTE ATIVO NESTE PERIODO. A recusa citada e a
        # mais especifica que existe: a do modelo do ativo, quando ha uma.
        _CACHE[f"modelo:{simbolo}:{timeframe}"] = (None, ultimo_meta)
        return None, ultimo_meta
    # Nome fora do formato aceito: e recusao COM MOTIVO, nao ausencia de
    # artefato. A distincao importa — "sem modelo" parece um problema de
    # treino; "simbolo invalido" e entrada do cliente.
    _CACHE[f"modelo:{simbolo}:{timeframe}"] = (None, {})
    return _CACHE[f"modelo:{simbolo}:{timeframe}"]


def _nomes_de_artefato(candidato: str, timeframe: str) -> list[str]:
    """Nomes a tentar, do mais especifico ao mais geral.

    POR QUE EXISTE (medido em 04/10/2026)
    ======================================
    Os artefatos tem dois formatos, porque foram treinados por dois motivos
    diferentes:

    1. `<SIMBOLO>_<TF>.pkl` — um modelo por ativo e por periodo:
       `XAUUSD_H1.pkl`, `EURUSD_H4.pkl`.

    2. `<SIMBOLO>.pkl` — um modelo UNICO que cobre varios periodos. E o caso
       dos `MULTI_*`: `MULTI_METALS.pkl`, treinado sobre a uniao de metais,
       vale para H1, H4 e M15.

    O codigo so procurava o formato 1. Resultado medido: os tres `MULTI_*`
    respondiam "modelo nao publicado ou ausente" — sendo que existem no
    disco, tem `publicable: true` e o MAIOR edge do catalogo (MULTI_METALS
    +0,2497, 58,3% de acerto, 67.678 amostras).

    A ORDEM IMPORTA: o nome COM timeframe e o mais especifico e precisa
    ganhar. Um `XAUUSD_H1` especifico tem sempre preferencia sobre um
    `XAUUSD` geral — caso contrario, pedir H1 cairia no modelo de H4.

    NENHUM ARQUIVO E RENOMEADO. O artefato continua como o treino o gravou;
    o que muda e que o codigo passa a saber PROCURAR-lo.
    """
    # PERIODO FORA DA ALLOWLIST NAO TEM NOME — NEM O GERAL (10/11/2026)
    # -----------------------------------------------------------------
    # O nome GERAL (`<SIMBOLO>.pkl`) significa "um modelo que cobre VARIOS
    # periodos", e a lista deles esta no `.meta.json` do proprio artefato. Ele
    # so pode ser pedido para um periodo VALIDO: com `M1` ou `H1/../..` a
    # degradacao para o geral fazia o `MULTI_METALS` — treinado em M5/M15/H1/H4
    # — responder a um pedido de M1, e o motivo da recusa virava erro de
    # reamostragem. Antes da opcao (b) isso ficava escondido porque o caminho
    # do ativo nao tem `.pkl` geral; o MULTI e, por construcao, geral.
    if timeframe not in TIMEFRAMES_VALIDOS:
        return []
    especifico = _nome_de_artefato(candidato, timeframe)
    geral = _nome_de_artefato(candidato, "")
    saida: list[str] = []
    for nome in (especifico, geral):
        if nome and nome not in saida:
            saida.append(nome)
    return saida


def _carregar_artefato(candidato: str, nome: str) -> tuple[Any | None, dict[str, Any]]:
    """Carrega UM artefato ja validado. Extraido de `_carregar` sem mudar nada."""
    chave = f"modelo:{candidato}:{nome.split('_')[-1]}"
    pkl = _caminho_confinado(f"{nome}.pkl")
    meta = _caminho_confinado(f"{nome}.meta.json")
    if pkl is None or meta is None:
        _CACHE[chave] = (None, {}, None)
        return _CACHE[chave][0], _CACHE[chave][1]
    if not (pkl.exists() and meta.exists()):
        _CACHE[chave] = (None, {}, None)
        return _CACHE[chave][0], _CACHE[chave][1]
    # A CHAVE DE CACHE tem de ver O `.meta.json` TAMBEM.
    #
    # MEDIDO em 10/11/2026 (D-159): a chave usava so o mtime do `.pkl`. Uma
    # correccao de GOVERNANCA (`publicable`, `min_edge`, `publish_reason`) vive
    # no `.meta.json` - e nao toca o `.pkl` - logo o gateway continuava a servir
    # a metadada antiga enquanto o ficheiro no disco ja dizia outra coisa. O
    # sintoma era o gateway "nao reiniciado": o `/api/ai/predict` respondia
    # `available=true` para um modelo que ja estava recusado em disco, e as
    # recusas continuavam a citar o piso antigo (+0.0500) depois da politica
    # mudar para +0.0200. A chave passa a ser o par (mtime do .pkl, mtime do
    # .meta.json): qualquer mudanca num dos dois invalida a cache.
    mtime = (pkl.stat().st_mtime, meta.stat().st_mtime)
    # A entrada do cache e (modelo, meta, mtime). O mtime decide se o arquivo
    # em disco mudou desde a leitura: sem ele, retreinar o modelo no mesmo
    # processo continuaria servindo o artefato antigo, e o operador veria o
    # nome do modelo novo com a previsao antiga.
    em_cache = _CACHE.get(chave)
    if em_cache is not None and len(em_cache) == 3 and em_cache[2] == mtime:
        return em_cache[0], em_cache[1]
    try:
        import joblib

        with meta.open(encoding="utf-8") as f:
            m = json.load(f)
        # INTEGRIDADE ANTES DE DESSERIALIZAR
        # --------------------------------------
        # `joblib.load` executa codigo (pickle). O caminho ja e confinado, mas
        # isso nao diz nada sobre o CONTEUDO do arquivo: quem escreve um `.pkl`
        # na pasta de modelos ganha execucao de codigo. O SHA-256 gravado no
        # `.meta.json` no treino e conferido ANTES do load — divergencia recusa
        # com motivo e o arquivo nao e desserializado. Ver
        # `Python/integridade_modelo.py`.
        #
        # A conferencia vem antes da checagem de `publicable` de proposito: um
        # arquivo adulterado nao passa nem quando o modelo nem e publicavel,
        # porque "nao vou usar" ainda e "executar o que estiver dentro" quando
        # alguem troca o arquivo por um publicavel.
        from Python.integridade_modelo import conferir as _conferir

        integro, motivo_integridade = _conferir(pkl, m)
        if not integro:
            _CACHE[chave] = (None, {**m, "publish_reason": motivo_integridade}, mtime)
            return _CACHE[chave][0], _CACHE[chave][1]
        # Treino so e aceito se passou na porta de qualidade.
        #
        # codeql[py/unsafe-deserialization] acesso ao modelo ja e verificado
        #
        # POR QUE A SUPressAO E JUSTA, E NAO UM ESCONDERDOR
        # ================================================
        # O CodeQL acusa por ANALISE DE FLUXO: `simbolo` chega do pedido HTTP e
        # alcanca `joblib.load(pkl)`, entao conclui "dado nao-confiavel vira
        # desserializacao". E isso esta certo sobre o QUE a regra ve, e errado
        # sobre o que o codigo faz — a regra nao raciocina sobre helper nenhum.
        #
        # TRES DEFESAS, todas ANTES do load:
        #  1. `_nome_de_artefato` barra na ORIGEM: regex `^[A-Z0-9]{1,12}$`
        #     mais allowlist fechada de timeframe. `..`, `/` e `\` nao passam.
        #  2. `_caminho_confinado` barra no DESTINO: o caminho resolvido
        #     precisa estar dentro de MODELOS_DIR (resolve + is_relative_to,
        #     com `resolve` seguindo link simbolico).
        #  3. `conferir(pkl, m)` barra no CONTEUDO: SHA-256 do `.pkl` gravado
        #     no `.meta.json` no treino e conferido antes do load. Divergencia
        #     recusa com motivo e o arquivo nao e desserializado.
        #     Ver `Python/integridade_modelo.py`.
        #
        # A 1 e a 2 existem desde o commit e0dbf0a e NUNCA resolveram o alerta.
        # A regra `py/path-injection` ja foi reescrita na forma que o CodeQL
        # reconhece justamente porque ele nao segue o helper — e mesmo assim o
        # `py/unsafe-deserialization` continuou accusing. E o mesmo motivo.
        #
        # O QUE A SUPressAO NAO COBRE (e por que e aceitavel aqui)
        # =========================================================
        # Nao ha assinatura digital: um atacante com escrita na pasta de
        # modelos E no `.meta.json` passaria. O modelo e treinado nesta
        # maquina e versionado no git; a defesa e contra troca de arquivo, erro
        # de copia e artefato vindo de outra maquina — nao contra um atacante
        # com escrita no disco. Assinatura exigiria chave privada fora do
        # repositorio e assinatura por build, desproporcional aqui.
        modelo = None if not m.get("publicable") else joblib.load(pkl)  # codeql[py/unsafe-deserialization] tres defesas acima; ver justificativa
        _CACHE[chave] = (modelo, m, mtime)
    except Exception:
        _CACHE[chave] = (None, {}, mtime)
    return _CACHE[chave][0], _CACHE[chave][1]


def limpar_cache() -> None:
    _CACHE.clear()
    _CACHE_MULTI["valor"] = None
    _CACHE_MULTI["quando"] = 0.0


def timeframes_capazes(symbol: str) -> list[str]:
    """Timeframes com modelo publicavel para este ativo, na ordem H1/H4/M15/M5.

    Cada ativo tem sua habilidade e seu periodo: em vez de o operador
    descobrir tentando, a recusa do `inferir` diz onde aquele ativo opera.
    Le so os `.meta.json` (sem desserializar `.pkl`), e aceita o par no
    quote de qualquer corretora (mesma regra generica de `_carregar`).
    """
    s = str(symbol or "").strip().upper()
    if not s:
        return []
    formas = set(candidatos_de_simbolo(s))
    achados: dict[str, bool] = {}
    try:
        for meta_path in MODELOS_DIR.glob("*.meta.json"):
            # `stem` de `BTCUSD_H1.meta.json` e `BTCUSD_H1.meta`: corta o
            # sufixo duplo pelo nome, nao pelo stem.
            nome_arquivo = meta_path.name
            nome = nome_arquivo[: -len(".meta.json")] if nome_arquivo.endswith(".meta.json") else ""
            if "_" not in nome:
                continue
            base_tf = nome.rsplit("_", 1)
            if len(base_tf) != 2:
                continue
            forma, tf = base_tf
            if forma not in formas or tf not in TIMEFRAMES_VALIDOS:
                continue
            try:
                with meta_path.open(encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                continue
            if m.get("publicable"):
                achados[tf] = True
    except OSError:
        return []
    # MODELO DE CLASSE COBRE O ATIVO MESMO SEM MODELO PROPRIO (D-175)
    # --------------------------------------------------------------
    # Depois de (b), "onde este ativo opera" inclui os periodos que o
    # `MULTI_<CLASSE>` cobre — o gateway responde por eles. Manter a lista so
    # com o artefato do proprio ativo diria ao operador que ele nao opera onde
    # ele opera: dois lados do mesmo dado discordando (AGENTS §5).
    try:
        classe = _classe_multi_de(s)
        if classe != "OUTROS" and _multi_permitido():
            from backend.asset_classes import nome_do_modelo_multi

            nome_classe = nome_do_modelo_multi(classe)
            caminho = _caminho_confinado(f"{nome_classe}.meta.json")
            if caminho is not None and caminho.exists():
                with caminho.open(encoding="utf-8") as f:
                    m_classe = json.load(f)
                if m_classe.get("publicable"):
                    for tf_classe in m_classe.get("timeframes") or []:
                        tf_up = str(tf_classe).strip().upper()
                        if tf_up in TIMEFRAMES_VALIDOS:
                            achados[tf_up] = True
    except (OSError, ValueError):
        # Catalogo ilegivel nao inventa capacidade: a lista fica a do ativo.
        pass
    return [tf for tf in ("H1", "H4", "M15", "M5") if achados.get(tf)]


def _nome_do_modelo(symbol: str, timeframe: str, meta: dict[str, Any]) -> str:
    """Nome do modelo QUE DECIDIU, lido do proprio metadado.

    POR QUE ISTO EXISTE
    ===================
    A inferencia usava `f"random_forest_{symbol}_{timeframe}"` — um nome
    FABRICADO em tempo de execucao. tres problemas, todos reais:

    1. **O nome da tela era falso.** O operador lia `random_forest_XAUUSD_H1`
       no app e acreditava que aquele era o artefato rodando. O `.meta.json`
       ja gravava `"algorithm"` desde o treino (train_v2.py:508) e a
       inferencia simplesmente o ignorava.
    2. **Nao sobrevivia a troca de algoritmo.** Se o treino passasse a usar
       GradientBoosting, a tela continuaria dizendo "random forest" — o
       oposto do principio de `Docs/LEVANTAMENTO_20260930.md`: *"afirmacao
       sem verificacao e marketing"*.
    3. **O frontend fabricava de novo.** `UniversalLiveTerminal.tsx:177`
       montava o mesmo nome a partir de `auto.simbolo`/`auto.timeframe`,
       ou seja, o terminal mostrava um modelo que talvez nem fosse o do ciclo.

    O nome agora vem do artefato. `Fallback: sem metadado, mostra o par — que
    e verdadeiro — em vez de inventar um algoritmo.
    """
    algoritmo = str(meta.get("algorithm") or "").strip()
    par = rotulo_modelo(symbol, timeframe)
    if not algoritmo:
        return par
    # O NOME E O ATIVO E O PERIODO. O ALGORITMO FICA NO CAMPO `algorithm`.
    #
    # MEDIDO na captura de 20:17 (09/10/2026), pedido do dono: o terminal
    # mostrava `MODELO Floresta · BTCUSD 1H`, e a tabela de modelos treinados
    # mostrava o mesmo nome na coluna MODELO **e** na coluna PAR — o mesmo par
    # duas vezes na mesma linha.
    #
    # "Floresta" e a traducao de `RandomForestClassifier` que existe para quem
    # precisa do nome tecnico. O operador nao precisa: ele precisa saber QUAL
    # ativo e QUAL periodo, porque e isso que ele compara com a ordem que esta
    # montando. Um algoritmo nao diz se o stop cai no lugar certo.
    #
    # O `algorithm` continua no payload, entao nada se perde — quem precisar do
    # nome tecnico le o campo, e nao o rotulo.
    #
    # Este e o AGENTS.md §9: formatação de numero e nome e configuração, nao
    # enfeite. E a forma como o nome aparecia era ruido entre o operador e o
    # dado que ele precisa.
    #
    # MODELO DE CLASSE: O NOME DO ARTEFATO E A RESPOSTA (D-175)
    # ========================================================
    # Pedido do dono ao autorizar a opcao "b" da Q-177: o rotulo do modelo de
    # classe tem de aparecer. Sem isto a tela diria `USDCOP 1H` e o operador
    # compararia a ordem com um modelo que NAO foi o que decidiu — o
    # `MULTI_FIAT` e UM artefato para os 15 pares da classe, e o par entra so
    # como amostra. Dois lados do mesmo dado com nomes diferentes e o defeito
    # do AGENTS §5.
    #
    # Artefato primeiro, alvo depois: `MULTI_FIAT · USDCOP 1H` responde as duas
    # perguntas de quem vai montar a ordem — QUE modelo decidiu e PARA QUE ativo.
    artefato = str(meta.get("symbol") or "").strip().upper()
    if str(meta.get("model_type") or "").strip().lower() == "multi" and artefato:
        alvo = rotulo_modelo(symbol, timeframe, comPrefixo=False)
        return f"{artefato} · {alvo}".strip() if alvo else artefato
    return rotulo_modelo(symbol, timeframe, comPrefixo=False)


#: Rotulo legivel por algoritmo. Sem esta tabela, a tela mostraria
#: `RandomForestClassifier_XAUUSD_H1` — correto e inutil para quem opera.
_ROTULO_ALGORITMO: dict[str, str] = {
    "RandomForestClassifier": "Floresta",
    "GradientBoostingClassifier": "Boosting",
    "ExtraTreesClassifier": "ExtraTrees",
    "HistGradientBoostingClassifier": "HistBoost",
    "LogisticRegression": "Logistica",
    "SVC": "SVM",
    "XGBClassifier": "XGBoost",
    "LGBMClassifier": "LightGBM",
}


def _n_jobs_inferencia() -> int:
    """Threads para inferencia de UMA amostra.

    predict_proba de uma unica linha nao paraleliza: o joblib ainda paga o
    custo de spawn (medido: metade dos 68 ms era time.sleep de worker). Como
    a inferencia pode rodar em paralelo por modelo (aba IA ativa varios
    modelos ao vivo), deixamos o paralelismo para FORA e usamos 1 thread aqui.
    """
    return 1


def _predict_proba(modelo: Any, amostra: pd.DataFrame) -> np.ndarray:
    """predict_proba de uma linha com 1 thread.

    Sem isso, o joblib paga o custo de criar 4 workers para processar UMA
    amostra: metade dos 68 ms medidos era time.sleep esperando worker ocioso.
    """
    try:
        modelo.n_jobs = _n_jobs_inferencia()
    except Exception:
        pass
    return modelo.predict_proba(amostra)[0]


# ============================================================
# CONTRATO XAU-30F-v4 (30 features, alvo binario)
# ============================================================
# MEDIDO 2026-11-04 nos 87 `Python/models/*.meta.json`: 80 falam 25F-v2, 3
# falam 25F-est-v1 e 4 falam XAU-30F-v4. Dos 4 publicaveis, o UNICO XAUUSD e o
# H1 - e ele e XAU-30F-v4. O runtime construia 25 features e o unico modelo que
# o gateway podia publicar exigia 30: por isso a resposta era `available=false`
# e o EA ficava em IA=SEM PRECO.
#
# A lista abaixo e uma COPIA VERBATICA de `xau_model_tools.FEATURES` e existe
# aqui para nao importar o modulo no caminho quente. `_features_30f` confere o
# tamanho contra o modulo antes de prever: divergencia vira recusa, nunca uma
# previsao com a coluna trocada.
_VERSAO_30F = "XAU-30F-v4"

#: Versao ESTACIONARIA: 22 features, escala normalizada por ATR, e o horizonte
#: e a classe entram como feature (`Timeframe_Cod`, `Classe_Cod`). E o contrato
#: dos tres `MULTI_*` — ver `Python/ai/features_estacionarias.py`.
#:
#: Sem esta constante o `inferir` caia no construtor de 25 features para um
#: artefato de 22: o `predict_proba` levantava e o operador lia "erro na
#: inferencia". O sintoma parecia falta de modelo; era contrato trocado.
_VERSAO_EST = "25F-est-v1"

_COLS_30F: tuple[str, ...] = (
    "ret1", "ret3", "ret5", "ret10", "ret20",
    "ema20_rel", "ema50_rel", "ema200_rel", "ema20_slope", "ema50_slope",
    "rsi14", "rsi_slope",
    "atr_pct", "atr_z",
    "adx14", "pdi_minus_mdi",
    "bbw", "close_z20",
    "stoch14",
    "body_ratio", "upper_wick", "lower_wick", "range_pct",
    "vol_z", "vol_ratio",
    "ret5_std", "gap_pct",
    "hour_sin", "hour_cos", "dow",
)


def _features_30f(candles: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Monta as 30 features do XAU-30F-v4 e o ATR absoluto da ultima barra.

    O construtor do 30F trabalha em MINUSCULAS (`time/open/high/low/close/
    tickvol`) porque le o CSV do dataset, enquanto o gateway entrega as colunas
    capitalizadas. O mapa abaixo aceita as duas grafias e as duas fontes de
    volume, para o caminho nao depender do nome exato que o MT5 devolveu.

    O ATR devolvido e o ABSOLUTO, e nao `atr_pct`: `atr_pct` e uma razao
    (ATR/preco) e devolve-la como ATR daria um numero ~4000x menor ao EA.
    """
    from Python import xau_model_tools as x30

    d = candles.copy()
    mapa: dict[str, str] = {}
    for destino, origens in (
        ("time", ("Time", "time")),
        ("open", ("Open", "open")),
        ("high", ("High", "high")),
        ("low", ("Low", "low")),
        ("close", ("Close", "close")),
        ("tickvol", ("Tick_volume", "Tickvol", "tick_volume", "tickvol",
                     "Volume", "volume")),
    ):
        for origem in origens:
            if origem in d.columns:
                mapa[origem] = destino
                break

    d = d.rename(columns=mapa)
    faltando = [c for c in ("time", "open", "high", "low", "close", "tickvol")
                if c not in d.columns]
    if faltando:
        raise ValueError(f"candles sem coluna para o contrato 30F: {faltando}")

    if tuple(x30.FEATURES) != _COLS_30F:
        raise ValueError(
            "contrato 30F divergente do xau_model_tools: "
            f"{len(x30.FEATURES)} features no modulo x {len(_COLS_30F)} aqui"
        )

    d = d.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time")
    feats = x30.build_features(d)
    atr_abs = float(x30.atr(d, 14).iloc[-1]) if len(d) else 0.0
    return feats, atr_abs


def _decodifica(probs: Any, classes: Any) -> tuple[float, float, float, str]:
    """Traduz a saida do classificador em (p_sell, p_neutral, p_buy, rotulo).

    BINARIO x TRICLASSE - O DEFEITO QUE SO APARECE A OPERAR
    ======================================================
    O alvo do XAU-30F-v4 e 0/1 com "0 = desce, 1 = sobe" e NAO tem classe
    NEUTRO (era a v3 de 3 classes; ver `build_target` em xau_model_tools). Ler
    `probs[2]` como compra num modelo binario devolve 0.0 sempre, e `probs[1]`
    (a probabilidade de SUBIR) iria para o campo NEUTRO: a compra viraria
    neutro em silencio - exactamente o que o proprio treinador avisa que nao se
    deve fazer.

    A traducao usa `classes_` do artefato, nunca um indice fixo. Para um modelo
    de 3 classes o resultado e identico ao anterior (0=SELL, 1=NEUTRAL,
    2=BUY), para nao mudar o comportamento dos 80 artefatos 25F-v2.
    """
    p = np.asarray(probs, dtype=np.float64).ravel()
    cl = list(range(len(p))) if classes is None else [int(c) for c in classes]
    if len(p) < 2 or len(cl) != len(p):
        return 0.0, 0.0, 0.0, "NEUTRAL"

    triclasse = 2 in cl
    p_sell = float(p[cl.index(0)]) if 0 in cl else 0.0
    if triclasse:
        p_neu = float(p[cl.index(1)]) if 1 in cl else 0.0
        p_buy = float(p[cl.index(2)]) if 2 in cl else 0.0
    else:
        p_neu = 0.0
        p_buy = float(p[cl.index(1)]) if 1 in cl else 0.0

    codigo = cl[int(np.argmax(p))]
    if triclasse:
        rotulo = {0: "SELL", 1: "NEUTRAL", 2: "BUY"}.get(codigo, "NEUTRAL")
    else:
        rotulo = "BUY" if codigo == 1 else "SELL"
    return p_sell, p_neu, p_buy, rotulo

def inferir(symbol: str, candles: pd.DataFrame, timeframe: str = "H1") -> Inferencia:
    """Roda o modelo do timeframe e devolve a decisao, ou diz por que nao pode.

    `candles` deve conter Time/Open/High/Low/Close/Volume/ATR/ADX/RSI no
    timeframe pedido. Nao ha padrao e nao ha fallback: se faltar, devolvemos
    indisponivel com o motivo.

    SIMBOLO VAZIO E RECUSA
    =====================
    Verificado ANTES de qualquer trabalho pesado (reamostrar, construir as 25
    features). Sem simbolo nao existe artefato, e sem artefato nao existe
    decisao. Devolver qualquer coisa aqui seria inventar o ativo.
    """
    inicio = time.perf_counter()
    threads = cpu_threads()
    os.environ.setdefault("XAU_AI_PRO_N_JOBS", str(threads))

    if not str(symbol or "").strip():
        return Inferencia(False, MOTIVO_SEM_SIMBOLO, "", timeframe)

    if timeframe not in t.MINUTOS_TIMEFRAME:
        return Inferencia(False, f"timeframe nao suportado: {timeframe}", symbol, timeframe)
    if candles is None or candles.empty:
        return Inferencia(False, "sem candles recebidos", symbol, timeframe)

    modelo, meta = _carregar(symbol, timeframe)
    if modelo is None:
        motivo = meta.get("publish_reason") or "modelo nao publicado ou ausente"
        capazes = timeframes_capazes(symbol)
        if capazes:
            motivo = f"{motivo} (este ativo opera em: {', '.join(capazes)})"
        return Inferencia(False, motivo, symbol, timeframe)

    try:
        # O contrato de features vem do ARTEFATO, nao do codigo: 80 dos 87
        # `.meta.json` falam 25F-v2 e os unicos publicaveis falam
        # XAU-30F-v4 (30 features, alvo binario). Despachar pelo
        # `feature_version` mantem os dois caminhos vivos sem que um quebre o
        # outro - trocar o construtor para todo mundo quebraria 80 modelos.
        versao = str(meta.get("feature_version") or "")
        if versao == _VERSAO_30F:
            base, atr_abs = _features_30f(candles)
            colunas = _COLS_30F
            col_preco = "close"
        else:
            # So a ultima linha e usada. Cortar ANTES de reamostrar evita
            # resamplear 46 mil candles a cada tique (eram ~2,4 s por inferencia).
            # 600 candles M5 dao 200 de H1, mais que o suficiente para as
            # features rolling/ewm ficarem identicas ao treino.
            janela = t.reamostrar(_com_volume_padrao(candles.tail(1200)), timeframe)
            if versao == _VERSAO_EST:
                # 22 features estacionarias, com o horizonte e a classe dentro.
                # A janela reamostrada e a mesma do caminho 25F-v2: o MULTI ve
                # o timeframe PEDIDO, e `Timeframe_Cod` diz qual e.
                base = fe.construir_features_estacionarias(
                    janela, timeframe, _classe_do_artefato(symbol, meta)
                )
                colunas = tuple(fe.FEATURES_ESTACIONARIAS)
            else:
                base = t.construir_features(janela)
                colunas = t.FEATURES
            col_preco = "Close"
            atr_abs = 0.0

        base = base.replace([np.inf, -np.inf], np.nan).dropna(subset=list(colunas))
        if base.empty:
            return Inferencia(False, "features incompletas apos derivacao", symbol, timeframe)
        ultima = base.iloc[[-1]][list(colunas)]
        if ultima.isna().any(axis=None):
            return Inferencia(False, "ultima linha com feature faltando", symbol, timeframe)

        # O 30F foi treinado com `to_numpy` (sem nomes de coluna): passar um
        # DataFrame aqui e aceito, mas gera aviso do sklearn a cada tique.
        amostra = ultima.to_numpy(dtype=np.float64) if versao == _VERSAO_30F else ultima
        probs = _predict_proba(modelo, amostra)
        p_sell, p_neu, p_buy, rotulo = _decodifica(probs, getattr(modelo, "classes_", None))
        metricas = meta.get("metrics", {})
        linha = base.iloc[-1]
        ms = (time.perf_counter() - inicio) * 1000.0
        if versao != _VERSAO_30F:
            atr_abs = float(linha.get("ATR", 0.0))
        return Inferencia(
            disponivel=True,
            motivo=(
                "inferencia real do modelo de classe publicado"
                + (
                    f" (modelo do ativo reprovado: {meta['cobertura_sobre_recusa']})"
                    if meta.get("cobertura_sobre_recusa")
                    else ""
                )
                if str(meta.get("model_type") or "") == "multi"
                else "inferencia real do modelo publicado"
            ),
            symbol=symbol,
            timeframe=timeframe,
            signal=rotulo,
            # Confianca = probabilidade real que o modelo atribui a decisao.
            confianca=float(max(probs)) * 100.0,
            prob_buy=p_buy,
            prob_sell=p_sell,
            prob_neutral=p_neu,
            price=float(linha[col_preco]),
            atr=float(atr_abs),
            edge=metricas.get("edge"),
            accuracy=metricas.get("accuracy"),
            folds=metricas.get("folds"),
            inferencia_ms=ms,
            modelo=_nome_do_modelo(symbol, timeframe, meta),
            modelo_classe=(
                str(meta.get("symbol") or "").strip().upper()
                if str(meta.get("model_type") or "").strip().lower() == "multi"
                else ""
            ),
            feature_hash=(str(meta.get("feature_hash") or "")
                          if versao in (_VERSAO_30F, _VERSAO_EST)
                          else t.feature_hash()),
        )
    except Exception as exc:  # pragma: no cover
        return Inferencia(False, f"erro na inferencia: {exc}", symbol, timeframe)


# Rotulo legivel do timeframe. O `id` do modelo e o nome do arquivo
# (`XAUUSD_H1`) e precisa continuar assim: o `.pkl` e o `.meta.json` sao
# gravados por esse nome, e trocar a convencao deixaria os 72 artefatos
# ja treinados orfaos. O que muda e o texto que a tela mostra.
#
# Antes a interface exibia o id cru. O operador lia "XAUUSD_H1" e tinha que
# saber que H1 = 1 hora. Agora a tela mostra "MODELO XAUUSD 1H".
_ROTULO_TF: dict[str, str] = {
    "M1": "1M", "M5": "5M", "M15": "15M", "M30": "30M",
    "H1": "1H", "H4": "4H", "D1": "1D", "W1": "1S",
}


def rotulo_modelo(symbol: str, timeframe: str, comPrefixo: bool = True) -> str:
    """Nome de exibicao de um modelo: `MODELO XAUUSD 1H`.

    Funcao pura e sem I/O — pode ser chamada de qualquer tela que liste
    modelo, sem depender do arquivo existir.

    `comPrefixo=False` devolve so `XAUUSD 1H`. A palavra MODELO e um
    cabecalho de coluna, nao parte do nome: entrelaçar com o algoritmo
    produzia `Floresta MODELO XAUUSD 1H`, que e ruido para quem opera.
    """
    simbolo = str(symbol or "").strip().upper()
    tf = str(timeframe or "").strip().upper()
    prefixo = "MODELO " if comPrefixo else ""
    if not simbolo and not tf:
        return prefixo.strip() or "MODELO"
    if not tf:
        return f"{prefixo}{simbolo}"
    return f"{prefixo}{simbolo} {_ROTULO_TF.get(tf, tf)}"


def listar_modelos() -> list[dict[str, Any]]:
    """Inventario real dos artefatos, com os metricos do treino.

    Percorre TODOS os `<SIMBOLO>_<TF>.meta.json` do diretorio. Antes o glob
    era `XAUUSD_*`, e os 9 simbolos treinados (BTCUSD, EURUSD, GBPUSD, ...)
    ficavam invisiveis para a interface mesmo com o .pkl no disco.
    """
    saida: list[dict[str, Any]] = []
    if not MODELOS_DIR.exists():
        return saida
    for meta_path in sorted(MODELOS_DIR.glob("*.meta.json")):
        nome = meta_path.name[: -len(".meta.json")]
        try:
            with meta_path.open(encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            continue

        # O NOME DO ARQUIVO NAO E `SIMBOLO_TF` NOS MULTI (09/10/2026)
        # =============================================================
        # MEDIDO: os tres artefatos de classe se chamam `MULTI_METALS`,
        # `MULTI_FIAT`, `MULTI_CRYPTO` — SEM underscore. Eles treinam sobre a
        # uniao de varios pares e valem para varios periodos (o
        # `MULTI_METALS.meta.json` tem `"timeframes": ["M5","M15","H1","H4"]`).
        #
        # Este laco os DESCARTAVA: `if "_" not in nome: continue`. O resultado
        # apareceu na captura de 20:28 do dono como "28 de 28 modelos" e uma
        # lista sem os tres de maior edge do catalogo — o `MULTI_METALS` tem
        # edge 0.2497 e 67.678 amostras, o maior de todos. Tres modelos SOMEM
        # da tela sem erro nenhum, e o contador repete o numero que a lista
        # devolveu.
        #
        # Agora o nome e lido do proprio `symbol`, que e o que o modelo GRAVOU
        # no treino, e o periodo tambem. Sem `_`, o modelo e de CLASSE, e os
        # periodos dele sao os que o meta disser.
        simbolo = str(m.get("symbol") or "").strip().upper()
        if not simbolo:
            continue
        timeframes_do_modelo = m.get("timeframes")
        if isinstance(timeframes_do_modelo, list) and timeframes_do_modelo:
            # Modelo de classe: UMA linha por periodo que ele cobre, para a
            # tabela nao mentir sobre "um nome, um periodo". O `id` continua
            # sendo o nome do arquivo — e ele que localiza o `.pkl` no disco.
            for tf_do_meta in [str(t).upper() for t in timeframes_do_modelo]:
                saida.append(_linha_do_modelo(m, nome, simbolo, tf_do_meta))
            continue

        tf = str(m.get("timeframe") or "").strip().upper()
        if not tf and "_" in nome:
            # Formato antigo, `SIMBOLO_TF`: o nome do arquivo ainda decide.
            _, tf = nome.rsplit("_", 1)
            tf = tf.upper()
        saida.append(_linha_do_modelo(m, nome, simbolo, tf))
    return saida


def _linha_do_modelo(
    m: dict[str, Any],
    nome: str,
    simbolo: str,
    tf: str,
) -> dict[str, Any]:
    """Uma linha da lista de modelos, do que o `.meta.json` GRAVOU.

    Separada do laco porque o mesmo artefato agora pode virar VARIAS linhas (o
    modelo de classe cobre varios periodos), e repetir os 20 campos dentro do
    laco seria copiar o mesmo bloco tres vezes.
    """
    metricas = m.get("metrics", {})
    folds = metricas.get("folds") or []
    edges = [fo["edge"] for fo in folds if isinstance(fo, dict) and "edge" in fo]
    return {
        "id": nome,
        "label": rotulo_modelo(simbolo, tf),
        "symbol": simbolo,
        "timeframe": tf,
        "publicable": bool(m.get("publicable")),
        "reason": m.get("publish_reason", ""),
        "accuracy": metricas.get("accuracy"),
        "f1": metricas.get("f1_score"),
        "baseline": metricas.get("baseline"),
        "edge": metricas.get("edge"),
        "edge_min": m.get("min_edge"),
        "edge_folds": edges,
        "edge_mean": float(np.mean(edges)) if edges else None,
        "edge_std": float(np.std(edges)) if edges else None,
        "train_samples": metricas.get("train_samples"),
        "test_samples": metricas.get("test_samples"),
        "purged": metricas.get("purged"),
        "train_date": m.get("train_date"),
        "feature_version": m.get("feature_version"),
        "feature_hash": m.get("feature_hash"),
        "algorithm": m.get("algorithm"),
        "pkl_present": (MODELOS_DIR / f"{nome}.pkl").exists(),
        "cpu_threads": cpu_threads(),
    }
