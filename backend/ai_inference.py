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
# restringe e o FORMATO, nao o conteudo: letras e digitos, sem separadores.
# `..`, `/`, `\` e `%2e%2e` nao passam.
TIMEFRAMES_VALIDOS = frozenset({"M5", "M15", "H1", "H4"})

# 12 e o maior comprimento de simbolo em Forex/Cripto/metal (ex.: `XAUUSD`,
# `BTCUSDT_PERP`). Acima disso ou ja e abuso, ou nao e simbolo.
_RE_SIMBOLO = re.compile(r"^[A-Z0-9]{1,12}$")


def _nome_de_artefato(simbolo: str, timeframe: str) -> str | None:
    """`<SIMBOLO>_<TF>` ou `None` se o par nao puder gerar nome de arquivo.

    `None` e recusa COM MOTIVO. Chamar `MODELOS_DIR / nome` com um nome
    invalido e o que produz o alerta de CodeQL; devolver `None` deixa a
    decisao no codigo, onde da para recusar e explicar.
    """
    if timeframe not in TIMEFRAMES_VALIDOS:
        return None
    if not _RE_SIMBOLO.match(simbolo):
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
       ja barra `/`, `\` e `..` na origem. O timeframe tem allowlist
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
    nome = _nome_de_artefato(simbolo, timeframe)
    if nome is None:
        # Nome fora do formato aceito: e recusao COM MOTIVO, nao ausencia de
        # artefato. A distincao importa — "sem modelo" parece um problema de
        # treino; "simbolo invalido" e entrada do cliente.
        _CACHE[f"modelo:{simbolo}:{timeframe}"] = (None, {})
        return _CACHE[f"modelo:{simbolo}:{timeframe}"]
    chave = f"modelo:{simbolo}:{timeframe}"
    pkl = _caminho_confinado(f"{nome}.pkl")
    meta = _caminho_confinado(f"{nome}.meta.json")
    if pkl is None or meta is None:
        _CACHE[chave] = (None, {})
        return _CACHE[chave]
    if not (pkl.exists() and meta.exists()):
        _CACHE[chave] = (None, {})
        return _CACHE[chave]
    mtime = pkl.stat().st_mtime
    em_cache = _CACHE.get(chave)
    if em_cache is not None and em_cache[2] == mtime:
        return em_cache[0], em_cache[1]
    try:
        import joblib

        with meta.open(encoding="utf-8") as f:
            m = json.load(f)
        # Treino so e aceito se passou na porta de qualidade.
        modelo = None if not m.get("publicable") else joblib.load(pkl)
        _CACHE[chave] = (modelo, m, mtime)
    except Exception:
        _CACHE[chave] = (None, {}, mtime)
    return _CACHE[chave][0], _CACHE[chave][1]


def limpar_cache() -> None:
    _CACHE.clear()


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
    # `RandomForestClassifier` -> "Floresta" fica ilegivel para o operador;
    # `random_forest` e o nome tecnico curto que ele reconhece.
    #
    # `rotulo_modelo()` ja devolve "MODELO XAUUSD 1H". Com o prefixo do algoritmo
    # antes, a tela mostrava "Floresta MODELO XAUUSD 1H" - a palavra MODELO no
    # meio, entre o nome e o timeframe. O operador pediu nome limpo e curto, sem
    # sublinhado: o timeframe ja vem legivel de `rotulo_modelo`, e o algoritmo
    # continua disponivel em `algorithm` no payload, entao nada se perde.
    return f"{_ROTULO_ALGORITMO.get(algoritmo, algoritmo)} · {rotulo_modelo(symbol, timeframe, comPrefixo=False)}"


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
        return Inferencia(False, motivo, symbol, timeframe)

    try:
        # So a ultima linha e usada. Cortar ANTES de reamostrar evita
        # resamplear 46 mil candles a cada tique (eram ~2,4 s por inferencia).
        # 600 candles M5 dao 200 de H1, mais que o suficiente para as features
        # rolling/ewm ficarem identicas ao treino.
        janela = t.reamostrar(candles.tail(1200), timeframe)
        base = t.construir_features(janela)
        base = base.replace([np.inf, -np.inf], np.nan).dropna(subset=t.FEATURES)
        if base.empty:
            return Inferencia(False, "features incompletas apos derivacao", symbol, timeframe)
        ultima = base.iloc[[-1]][t.FEATURES]
        if ultima.isna().any(axis=None):
            return Inferencia(False, "ultima linha com feature faltando", symbol, timeframe)

        probs = _predict_proba(modelo, ultima)
        decisao = int(np.argmax(probs))
        metricas = meta.get("metrics", {})
        linha = base.iloc[-1]
        ms = (time.perf_counter() - inicio) * 1000.0

        p_buy = float(probs[2]) if len(probs) > 2 else 0.0
        p_sell = float(probs[0]) if len(probs) > 0 else 0.0
        p_neu = float(probs[1]) if len(probs) > 1 else 0.0
        return Inferencia(
            disponivel=True,
            motivo="inferencia real do modelo publicado",
            symbol=symbol,
            timeframe=timeframe,
            signal={0: "SELL", 1: "NEUTRAL", 2: "BUY"}.get(decisao, "NEUTRAL"),
            # Confianca = probabilidade real que o modelo atribui a decisao.
            confianca=float(max(probs)) * 100.0,
            prob_buy=p_buy,
            prob_sell=p_sell,
            prob_neutral=p_neu,
            price=float(linha["Close"]),
            atr=float(linha.get("ATR", 0.0)),
            edge=metricas.get("edge"),
            accuracy=metricas.get("accuracy"),
            folds=metricas.get("folds"),
            inferencia_ms=ms,
            modelo=_nome_do_modelo(symbol, timeframe, meta),
            feature_hash=t.feature_hash(),
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
        if "_" not in nome:
            continue
        simbolo, tf = nome.rsplit("_", 1)
        try:
            with meta_path.open(encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            continue
        metricas = m.get("metrics", {})
        folds = metricas.get("folds") or []
        edges = [fo["edge"] for fo in folds if isinstance(fo, dict) and "edge" in fo]
        rotulo_simbolo = str(m.get("symbol") or simbolo).upper()
        rotulo_tf = str(m.get("timeframe") or tf).upper()
        saida.append({
            "id": nome,
            # `label` e o texto para a tela. `id` continua sendo o nome do
            # arquivo, porque e ele que localiza o `.pkl` no disco.
            "label": rotulo_modelo(rotulo_simbolo, rotulo_tf),
            "symbol": rotulo_simbolo,
            "timeframe": rotulo_tf,
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
        })
    return saida
