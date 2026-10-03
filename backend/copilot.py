# -*- coding: utf-8 -*-
"""Copiloto do XAU AI PRO: conversa sobre o EA, o mercado e o codigo.

CONTEXTO QUE ESTE COPILOTO DEVE CONHECER
=========================================
Desde o build 6060 (23/07/2026) o MetaTrader 5 tem IA nativa: um AI Assistant
no terminal (mercado, posicoes, historico) e outro no MetaEditor (gerar e
analisar MQL5). O build 6180 deu acesso a Strategy Tester, otimizacao e logs; o
6230 (24/09) deu controle de EAs, parametros, lancamento em grafico e calendario
economico. Alem disso o terminal fala MCP, entao agentes externos como Codex e
Claude Code se conectam a ele.

Isso muda o que este copiloto DEVE e NAO DEVE ser:

  - NAO e um "copiloto de mercado" para competir com o AI nativo do MT5. O
    dele tem leitura direta do terminal; o nosso teria que passar pelo gateway.
  - NAO e gerador de MQL5: o AI do MetaEditor faz isso melhor, com o arquivo
    aberto no editor.
  - E o copiloto que conhece O SEU EA. O do terminal nao le o codigo do seu
    projeto: ele nao sabe que o seu OrderRetry tem retry inoperante, nem que o
    seu log de auditoria tem ATR e RSI trocados. Este modulo sabe, porque ha um
    mapa verificado em `backend/ea_map.py`.

PRINCIPIO: RESPONDER O QUE SEI, ADMITIR O QUE NAO SEI
=====================================================
Toda resposta sobre o EA sai de `ea_map`, que foi construido por leitura do
codigo e dos artefatos de runtime. Nada e inventado. Se a pergunta exige algo
que o mapa nao cobre, o copiloto diz isso e sugere o que precisaria ler.

O copiloto NAOprediz mercado. Com edge medido de +0,11 e confianca media de
41,7%, qualquer promessa de direcao seria mentira. Ele relata o que os dados
reais dizem e aponta a leitura, nao a previsao.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from backend import ea_map

# Limite de caracteres por resposta, para a UI nao virar um texto sem fim.
LIMITE_RESPOSTA = 6000


# ------------------------------------------------------------------ intents

# A ordem das entradas importa: o primeiro padrao que casa vence. Por isso
# "codigo" vem antes de "copiloto" e "mercado" antes de "geral" — senao
# "quem e voce" casaria em \bcodigo\b e "onde OrderSend e chamado" nao
# encontraria a intencao de codigo, porque "chamado" nao estava no padrao.
INTENTS = [
    # `achado` com digito e intencao exata: tem precedencia sobre "achados".
    # Sem \\b depois, "achado 4" casaria "achados" pela lista generica.
    ("achado", r"achado\s*\d+"),
    # 'conta de' saiu daqui: em "minha conta demo" o `de` casa o 'e' de
    # "demo" e a pergunta ia para a intencao errada. Quem fala de "conta de
    # operacoes" tambem toca "operacoes", coberto por `risco`/dados.
    #
    # `ambiente` NAO fica aqui: e a intencao mais ampla ("como esta tudo?"), e
    # `agora`/`status`/`resumo` sao palavras genericas que roubavam a intencao
    # `mercado` — "qual o preco do ouro agora" ia para ambiente. Ver o fim da
    # lista, depois de `copiloto`.
    ("achados", r"achado|problema|\berro\b|\bbug\b|defeito|erros"),
    # 'demo' nao pode casar \\berro\\b: em "minha conta demo" a letra 'e' de
    # "demo" casa a alternancia parcial. \\berro\\ ja exige fronteira, mas
    # "contas" tambem era capturado por `conta de`. Mantem aqui.
    ("criticos", r"critic|grave|pior|perig|serio"),
    ("risco", r"risco|protecao|limite|trava|drawdown|exposicao|margem|lote"),
    ("fluxo", r"fluxo|ontick|pipeline|como funciona|passo|ordem de|sequencia"),
    ("ia", r"\bia\b|inteligencia|modelo|predic|signal|sinal"),
    ("dados", r"dados|dataset|csv|\blog\b|auditoria|registro|grava"),
    ("controles", r"controle|tabela|resumo|panorama|quantos|mapa"),
    # "chamad|usad|definid|onde .*chamad|onde .*usad|ordersend" fazem uma
    # busca por simbolo de codigo cair em responder_codigo, e nao em "geral".
    ("codigo", r"codigo|fonte|mq5|mqh|include|funcao|variavel|grep|busca|procure"
               r"|chamad|usad|definid|ordersend"),
    ("agenda", r"agenda|calendario|evento|macro|noticia|noticias|cpi|ipc"
               r"|juros|banco central|fed"),
    # Sem pipe duplicado: "suporte||tendencia" criava uma alternativa vazia,
    # que casa em qualquer texto e fazia `mercado` capturar TODAS as perguntas.
    ("mercado", r"mercado|preco|cotacao|ativo|\bxau\b|ouro|eurusd|usdjpy|trend|suporte"
                r"|tendencia|vela|candle"),
    ("posicao", r"posicao|posicoes|aberta|lucro|p&l|pnl"),
    ("copiloto", r"copiloto|quem e voce|quem voce|o que voce faz|o que e voce"
                 r"|ajuda|como funciona voce|seu nome"),
    # `ambiente` e a intencao mais aberta, entao fica DEPOIS das especificas.
    # Exige um substantivo: "como esta" sozinho e comum demais e capturava
    # perguntas de mercado e de conta.
    ("ambiente", r"como esta (minha |o |a )?(conta|dia|sistema|rob|terminal|mercado|carteira)"
                 r"|como ta (minha |o |a )?(conta|dia|sistema|rob|terminal|carteira)"
                 r"|como foi (o |meu |hoje)"
                 r"|meu status|status da (conta|sistema)|panorama do dia"
                 r"|resumo do (dia|conta|sistema)"),
    # 'conta' so no fim e com frases especificas: e palavra muito comum e
    # capturaria quase tudo.
    ("conta", r"minha conta|o saldo|o equity|o patrimonio|em demo|em real|minha banca"),
]


def detectar_intent(pergunta: str) -> str:
    t = pergunta.lower()
    for nome, padrao in INTENTS:
        if re.search(padrao, t):
            return nome
    return "geral"


# ----------------------------------------------------------------- contexto


@dataclass
class Contexto:
    """Fontes de dado que o copiloto pode consultar.

    `mapa` e o modulo `backend.ea_map`. Pode ser substituido por um duble nos
    testes, mas o padrao e o modulo real — e por isso `Any`, e nao uma classe.
    """

    mapa: Any = field(default=ea_map)
    agora: Callable[[], dict[str, Any]] | None = None
    _cache: dict[str, Any] = field(default_factory=dict)

    def runtime(self) -> dict[str, Any]:
        if "runtime" not in self._cache:
            self._cache["runtime"] = self.mapa.estado_runtime()
        return self._cache["runtime"]

    def cotacoes(self) -> dict[str, Any]:
        """Cotacoes do store do gateway, se houver. Ausente nao e erro."""
        if "cotacoes" not in self._cache and self.agora is not None:
            try:
                self._cache["cotacoes"] = self.agora() or {}
            except Exception:
                self._cache["cotacoes"] = {"erro": "gateway indisponivel"}
        return self._cache.get("cotacoes", {})


# ------------------------------------------------------------- formatadores


def _achado_texto(a: ea_map.Achado) -> str:
    return (
        f"**#{a.id} [{a.gravidade}] {a.titulo}**\n"
        f"`{a.referencia()}`\n"
        f"{a.descricao}\n"
        f"Por que importa: {a.por_que_importa}"
    )


def _top(limite: int = 5) -> list[ea_map.Achado]:
    ordenados = sorted(
        ea_map.TODOS_ACHADOS,
        key=lambda a: (ea_map.PESO_GRAVIDADE.get(a.gravidade, 9), a.id),
    )
    return ordenados[:limite]


def _rodape() -> str:
    grav = ea_map.contar_gravidade()
    return (
        f"\n---\n_{len(ea_map.TODOS_ACHADOS)} achados verificados no codigo: "
        f"{grav.get('CRITICO', 0)} criticos, {grav.get('ALTO', 0)} altos, "
        f"{grav.get('MEDIO', 0)} medios, {grav.get('BAIXO', 0)} baixos._"
    )


# --------------------------------------------------------------- respostas


def responder_achados(ctx: Contexto, pergunta: str) -> str:
    # Stopwords em portugues: Filtrar这些 evita que "qual o PIOR problema"
    # devolva achados que so tem a palavra "pior" no texto. Sem isso a busca
    # por adjectivo devolve resultado irrelevante em vez da lista ordenada.
    stop = {
        "problema", "problemas", "erro", "erros", "quais", "qual", "pior",
        "melhor", "grave", "graves", "defeito", "defeitos", "projeto",
        "mostra", "mostrar", "queria", "quero", "sobre", "codigo", "meu",
        "esta", "estao", "existe", "tem", "fala",
    }
    termos = [p for p in re.findall(r"[\wÀ-ÿ]{4,}", pergunta.lower()) if p not in stop]
    for termo in termos:
        achados = ctx.mapa.buscar(termo)
        # Um unico achado bate fraco; com 1+ achados e a resposta util.
        if len(achados) >= 2:
            linhas = [f"Achei {len(achados)} achado(s) para '{termo}':\n"]
            for d in achados[:4]:
                linhas.append(
                    f"**#{d['id']} [{d['gravidade']}] {d['titulo']}**\n"
                    f"`{d['arquivo']}:{d['linha']}`\n"
                    f"{d['por_que_importa']}\n"
                )
            return "\n".join(linhas) + _rodape()
    return _resumo_por_gravidade(ctx)


def _resumo_por_gravidade(ctx: Contexto) -> str:
    linhas = ["Mapa de problemas do EA, do mais grave para o menos:\n"]
    for a in _top(10):
        linhas.append(f"**#{a.id} [{a.gravidade}] {a.titulo}** — `{a.referencia()}`")
        linhas.append(f"  {a.por_que_importa}\n")
    linhas.append("Peça por número (`" + str(_top(1)[0].id) + "`), por gravidade "
                  "(`críticos`), por área (`risco`, `IA`, `dados`) ou por "
                  "termo (`retry`, `lote`, `auditoria`).")
    return "\n".join(linhas) + _rodape()


def responder_criticos(ctx: Contexto, _pergunta: str) -> str:
    achados = [a for a in ctx.mapa.TODOS_ACHADOS if a.gravidade == "CRITICO"]
    linhas = [
        "Os problemas mais graves do seu EA. Todos verificados por leitura do "
        "codigo e dos arquivos de runtime — nao sao suposicoes:\n",
    ]
    for a in achados:
        linhas.append(f"\n**#{a.id} {a.titulo}**\n`{a.referencia()}`")
        linhas.append(f"{a.descricao}\n")
        linhas.append(f"*Consequencia:* {a.por_que_importa}\n")
    linhas.append(
        "\nO que isso significa na pratica: o EA tem protecoes de risco "
        "declaradas que nao estao no caminho de entrada, e os logs de auditoria "
        "que deveriam provar o comportamento tem ATR e RSI trocados. Qualquer "
        "forward test feito sobre esses logs mede numeros corrompidos."
    )
    return "\n".join(linhas) + _rodape()


def responder_risco(ctx: Contexto, _pergunta: str) -> str:
    controles = ctx.mapa.controles_risco()
    contagem: dict[str, int] = {}
    for c in controles:
        contagem[c["situacao"]] = contagem.get(c["situacao"], 0) + 1
    linhas = [
        f"Controles de risco do EA: **{len(controles)}** no total.\n",
        f"- {contagem.get('ATIVO', 0)} ativos",
        f"- {contagem.get('PARCIAL', 0)} parciais (funcionam com ressalva)",
        f"- {contagem.get('INOPERANTE', 0)} inoperantes (estao no codigo mas nao protegem)",
        f"- {contagem.get('STUB', 0)} sao stub (`return true`)\n",
        "**Os que nao funcionam de verdade:**\n",
    ]
    for c in controles:
        if c["situacao"] in {"INOPERANTE", "STUB"}:
            linhas.append(f"- **{c['nome']}** (`{c['arquivo']}:{c['linha']}`) — {c['detalhe']}")
    linhas.append("\n**Verde, mas com ressalva:**\n")
    for c in controles:
        if c["situacao"] == "PARCIAL":
            linhas.append(f"- **{c['nome']}** (`{c['arquivo']}:{c['linha']}`) — {c['detalhe']}")
    return "\n".join(linhas) + _rodape()


def responder_fluxo(ctx: Contexto, _pergunta: str) -> str:
    linhas = [
        "Fluxo do `OnTick`, na ordem real do codigo "
        "(`XAU_AI_PRO.mq5:763-1004`):\n",
    ]
    for p in ctx.mapa.FLUXO_ON_TICK:
        marca = " **BLOQUEIA**" if p.get("bloqueia") else ""
        nota = f"  \n  _{p['nota']}_" if p.get("nota") else ""
        linhas.append(f"{p['passo']:>2}. `{p['linha']}` {p['acao']}{marca}{nota}")
    linhas.append("\n**Cadeia de abertura de posicao:**\n")
    for c in ctx.mapa.CADEIA_DE_ENTRADA:
        linhas.append(f"{c['passo']}. `{c['local']}` — {c['acao']}")
    linhas.append(
        "\nRepare no passo 21: `ManagePositions()` roda **fora** de todos os "
        "early-returns. O fechamento por stop, trailing e breakeven acontece "
        "mesmo com o pipeline de entrada bloqueado — e sem passar por "
        "`OrderCheck`, retry ou lock, porque usa `CTrade` direto."
    )
    return "\n".join(linhas)


def responder_ia(ctx: Contexto, _pergunta: str) -> str:
    runtime = ctx.runtime()
    linhas = [
        "**Como a IA entra no EA:**\n",
        "1. O EA le `Data/prediction_<SIMBOLO>.json` por polling de arquivo "
        "(`AIConnector.mqh:137-608`). Nao ha socket nem chamada ao backend Python.",
        "2. `AIEngine.mqh:203` so gera sinal se `AI_Score >= MinAIConfidence` "
        "e `|buy - sell| > 10`.",
        "3. Se o tecnico e a IA divergem, `GetCombinedSignal` retorna 0 — aborta.",
        "4. A IA **nunca cria sinal**: ela so veta (`AIEngine.mqh:287-375`).",
        "5. Sem predicao, o EA **opera 100%** com score local de indicadores.\n",
        "**Problemas verificados:**\n",
    ]
    for a in ctx.mapa.TODOS_ACHADOS:
        if a.categoria == "ia" and a.gravidade in {"CRITICO", "ALTO"}:
            linhas.append(f"- **#{a.id} {a.titulo}** (`{a.referencia()}`) — {a.por_que_importa}")
    linhas.append("\n**Predicoes que o terminal tem agora:**\n")
    preds = runtime.get("predicoes") or []
    if not preds:
        linhas.append("Nenhum arquivo `prediction*.json` encontrado em "
                      f"`{runtime.get('data_dir')}`.")
    else:
        for p in preds[:8]:
            linhas.append(
                f"- `{p['arquivo']}` → {p['symbol']} **{p['signal']}** "
                f"confianca {p['confidence']}"
            )
        linhas.append(
            "\nRepare no `prediction.json` (M5): confianca 0.0. O modelo M5 foi "
            "reprovado na porta de qualidade — edge negativo sobre o palpite. O "
            "H1 tem edge +0,11 e o H4 +0,13."
        )
    return "\n".join(linhas) + _rodape()


def responder_dados(ctx: Contexto, _pergunta: str) -> str:
    runtime = ctx.runtime()
    linhas = [
        "**O que o EA grava e onde:**\n",
        "| Arquivo | Codificacao | Delimitador | Escritor |",
        "|---|---|---|---|",
        "| `Data/dataset.csv` | UTF-16 | `,` | `AI/DataLogger.mqh:166-176` |",
        "| `Data/full_audit.csv` | ANSI | **`;`** | `Monitoring/AuditLog.mqh:566-575` |",
        "| `Data/ai_feedback.csv` | ANSI | `,` | `AI/AIEngine.mqh:390-428` |",
        "| `Data/forward_test_events.csv` | UTF-16 | `,` | `Monitoring/EventEmitter.mqh:73` |",
        "| `Data/system_status.json` | ANSI | JSON | `Monitoring/SystemStatus.mqh:210-223` |",
        "\nTres codificacoes no mesmo diretorio e dois delimitadores. Qualquer "
        "consumidor precisa ramificar por arquivo.\n",
        "**Problemas verificados:**\n",
    ]
    for a in ctx.mapa.TODOS_ACHADOS:
        if a.categoria in {"dados", "auditoria"} and a.gravidade in {"CRITICO", "ALTO", "MEDIO"}:
            linhas.append(f"- **#{a.id} {a.titulo}** (`{a.referencia()}`)")
    linhas.append(
        f"\nDiretorio de runtime: `{runtime.get('data_dir')}` "
        f"(existe: {runtime.get('existe')})"
    )
    return "\n".join(linhas) + _rodape()


def responder_controles(ctx: Contexto, _pergunta: str) -> str:
    inv = ctx.mapa.inventario()
    if not inv.get("ok"):
        return inv.get("error", "arvore do EA nao encontrada")
    principal = inv.get("arquivo_principal") or {}
    ex5 = inv.get("ex5") or {}
    return "\n".join([
        "**XAU AI PRO — mapa do codigo:**\n",
        f"- {inv['total_arquivos']} arquivos `.mq5/.mqh` vivos, "
        f"{inv['total_linhas']:,} linhas",
        f"- principal: `{principal.get('arquivo')}`, {principal.get('linhas')} linhas",
        f"- compilado: `{ex5.get('caminho', '?').split(chr(92))[-1]}` "
        f"({(ex5.get('bytes') or 0):,} bytes)",
        f"- achados: {ea_map.contar_gravidade()}",
        f"- por area: {ea_map.contar_categoria()}",
        "\n**Controles de risco:** "
        + ", ".join(
            f"{k} {v}" for k, v in sorted(
                {s: len(ctx.mapa.controles_risco(s))
                 for s in ("ATIVO", "PARCIAL", "INOPERANTE", "STUB")}.items()
            )
        ),
        "\nPergunte sobre uma area: `risco`, `IA`, `dados`, `fluxo`, "
        "ou um achado pelo numero.",
    ]) + _rodape()


def responder_codigo(ctx: Contexto, pergunta: str) -> str:
    """Busca textual nos arquivos do EA. Leitura apenas."""
    termos = re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", pergunta)
    termos = [t for t in termos if t.lower() not in {"codigo", "fonte", "arquivo", "funcao", "variavel"}]
    if not termos:
        return (
            "Diga o que procurar. Exemplo: `onde OrderSend e chamado` ou "
            "`o que faz CircuitBreaker`.\n\n"
            f"A arvore tem {ctx.mapa.inventario().get('total_arquivos', 0)} arquivos "
            "e eu leio, mas nao escrevo — a regra do projeto mantem MQL5 intocavel."
        )
    termo = termos[0]
    achados = ctx.mapa.buscar(termo)
    arv = ctx.mapa._arvore()  # noqa: SLF001 - uso interno deliberado
    correspondentes = [
        a["arquivo"] for a in arv.get("arquivos_vivos", [])
        if termo.lower() in a["arquivo"].lower()
    ]
    linhas = [f"Busca por `{termo}`:\n"]
    if correspondentes:
        linhas.append("Arquivos com esse nome:\n")
        for c in correspondentes[:6]:
            linhas.append(f"- `{c}`")
        linhas.append("")
    if achados:
        linhas.append(f"Achados relacionados ({len(achados)}):\n")
        for d in achados[:3]:
            linhas.append(f"- **#{d['id']} {d['titulo']}** — `{d['arquivo']}:{d['linha']}`")
    else:
        linhas.append(
            "Nenhum achado conhecido menciona esse termo. Posso dizer que **nao "
            "sei**: meu mapa cobre os problemas verificados, nao a arvore inteira. "
            "Para responder com precisao eu precisaria ler os arquivos correspondentes."
        )
    linhas.append(
        "\n_Limite meu: eu leio e explico o MQL5, mas nao compilo. "
        "Para gerar ou corrigir codigo MQL5, o AI Assistant do proprio MetaEditor "
        "faz isso com o arquivo aberto — ele esta no terminal desde o build 6060._"
    )
    return "\n".join(linhas)


def responder_mercado(ctx: Contexto, pergunta: str) -> str:
    dados = ctx.cotacoes()
    runtime = ctx.runtime()
    linhas = ["**Mercado — o que os dados reais dizem:**\n"]
    quotes = dados.get("quotes") or {}
    if quotes:
        linhas.append(f"Cotacoes ({dados.get('atualizado_em', 'sem hora')}):\n")
        itens = quotes.items() if isinstance(quotes, dict) else [
            (q.get("symbol"), q) for q in quotes
        ]
        for simbolo, q in list(itens)[:10]:
            if isinstance(q, dict):
                linhas.append(
                    f"- **{simbolo}** {q.get('bid', '?')} / {q.get('ask', '?')} "
                    f"({q.get('source', '?')})"
                )
    else:
        linhas.append(
            "Sem cotacoes no store do gateway agora. Motivo: "
            f"{dados.get('erro', 'gateway nao consultado ou sem simbolo selecionado')}."
        )
    linhas.append(
        "\n**O que eu nao faco:** nao prevejo direcao. O modelo H1 tem edge "
        "medido de +0,11 sobre o palpite e confianca media de 41,7% — ou seja, "
        "quase empate entre compra e venda. Qualquer Previsao minha seria teatro.\n"
        "Para leitura de mercado com dado vivo, o AI Assistant nativo do MT5 "
        "acessa os graficos direto. Para decisao baseada no seu modelo, use a "
        "aba Inteligencia Artificial do app."
    )
    preds = runtime.get("predicoes") or []
    if preds:
        linhas.append(f"\nPredicoes geradas: {len(preds)} arquivo(s).")
    return "\n".join(linhas)


def responder_posicao(ctx: Contexto, _pergunta: str) -> str:
    dados = ctx.cotacoes()
    pos = dados.get("positions") or []
    linhas = ["**Posicoes abertas:**\n"]
    if not pos:
        linhas.append(
            "Nenhuma posicao informada pelo gateway agora.\n"
            "\nPara ver as posicoes, abra a aba Robo do app: o "
            "`UniversalLiveTerminal` le `/api/universal/positions` direto do MT5."
        )
    else:
        for p in pos[:10]:
            linhas.append(
                f"- ticket {p.get('ticket')} {p.get('symbol')} {p.get('side')} "
                f"vol {p.get('volume')} P/L {p.get('profit')}"
            )
    linhas.append(
        "\nLembre do achado #1: o retry de ordem esta inoperante em producao, "
        "mas **nao** no Strategy Tester. Entao o que voce ve em backtest nao e "
        "o que acontece com o EA real rodando."
    )
    return "\n".join(linhas)


def responder_conta(ctx: Contexto, _pergunta: str) -> str:
    dados = ctx.cotacoes()
    conta = dados.get("account") or {}
    linhas = ["**Conta:**\n"]
    if conta:
        linhas.append(
            f"- login {conta.get('login', '?')} · servidor {conta.get('server', '?')}\n"
            f"- modo: {conta.get('trade_mode', '?')} "
            f"({'DEMO' if conta.get('trade_mode') == 1 else 'REAL' if conta.get('trade_mode') == 0 else 'desconhecido'})\n"
            f"- moeda {conta.get('currency', '?')}"
        )
    else:
        linhas.append("Sem dados de conta no gateway agora (MT5 desconectado ou sem sessao).")
    linhas.append(
        "\nA aba de patrimonio mostra saldo, disponivel e posicoes por corretora. "
        "Dupliquei essa leitura de proposito: e o unico lugar onde ela aparece."
    )
    return "\n".join(linhas)


def responder_copiloto(_ctx: Contexto, _pergunta: str) -> str:
    return "\n".join([
        "Sou o copiloto do XAU AI PRO. O que eu faco de diferente:",
        "",
        "**Conheco o SEU codigo.**Li os 90 arquivos `.mq5/.mqh` vivos "
        "(32.202 linhas) e os artefatos de runtime. Sei que o seu retry nao roda, "
        "que o log de auditoria tem ATR e RSI trocados, que `AutoTrade=false` nao "
        "impede operacao e que 670 linhas de metricas estao mortas por um guard "
        "de include duplicado.",
        "",
        "**O que eu nao faco:**",
        "- Nao prevejo preco. O edge do seu modelo e +0,11 e a confianca media e "
        "41,7%. Prever direcao aqui seria mentira.",
        "- Nao escrevo MQL5. A regra do projeto mantem `.mq5/.mqh` intocaveis. "
        "Leio e explico; para gerar codigo, use o AI Assistant do MetaEditor.",
        "- Nao invento. Se eu nao sei, eu digo que nao sei — e digo o que "
        "precisaria ler para saber.",
        "",
        "**Sobre o MT5:** seu terminal ja tem IA nativa desde o build 6060 "
        "(23/07/2026), e o 6230 (24/09) adicionou controle de EAs, Strategy "
        "Tester e calendario economico. Ele le o terminal direto; eu le o seu "
        "projeto. Sao coisas diferentes.",
        "",
        "Pergunte sobre um achado (`achado 4`), por area (`risco`, `IA`, `dados`), "
        "pelo fluxo (`como funciona o OnTick`) ou por codigo "
        "(`onde OrderSend e chamado`).",
    ])


def responder_geral(ctx: Contexto, pergunta: str) -> str:
    """Sem intent claro: mostra o mapa e pergunta o que quer olhar."""
    # Recusa explicita de previsao. Precisa de linguagem propia: cair no
    # "nao sei, o que eu consigo responder" e fraco quando o usuario pediu
    # justamente a coisa que um copiloto de trading nao pode prometer.
    if re.search(r"prev|acert|ganhar|render|va subir|va cair|comprar|vender"
                 r"|sera .*?(alta|baixa)|dire[cç][aã]o", pergunta.lower()):
        return "\n".join([
            "**Isso eu nao faco, e nao e limitacao tecnica: e questao de honestidade.**\n",
            "O edge medido do seu modelo H1 e de **+0,11** sobre o palpite, com "
            "confianca media de **41,7%** — ou seja, praticamente empate entre "
            "compra e venda. O M5 foi reprovado na porta de qualidade (edge "
            "negativo). Com esses numeros, qualquer previsao de direcao minha "
            "seria teatro com nota de rodape.\n",
            "O que eu faco com o modelo:\n",
            "- **Relato** as probabilidades reais (`/api/ai/trained`)\n",
            "- **Explico** o que a inferencia mediu e com que edge\n",
            "- **Aponto** que M5 nao tem edge e H1/H4 tem\n",
            "\nPara decidir com dado, use a aba **Inteligencia Artificial** do app: "
            "ela mostra a distribuicao de probabilidade (compra / venda / neutro) "
            "do modelo, que e a informacao real. A decisao e sua.\n",
            "E para leitura de grafico com dado vivo, o **AI Assistant nativo do "
            "MT5** (build 6060+) acessa os graficos direto — mais rapido e mais "
            "preciso que eu.",
        ])
    achados = ctx.mapa.buscar(pergunta)
    if achados:
        linhas = [f"Encontrei {len(achados)} achado(s) relacionado(s):\n"]
        for d in achados[:3]:
            linhas.append(f"**#{d['id']} [{d['gravidade']}] {d['titulo']}**")
            linhas.append(f"`{d['arquivo']}:{d['linha']}` — {d['titulo']}\n")
        return "\n".join(linhas) + _rodape()
    return "\n".join([
        "Nao sei responder isso com precisao — e prefiro dizer isso a inventar.\n",
        "O que eu consigo responder:\n",
        "- **Achados do seu EA** — os 10 mais graves, por area, por numero",
        "- **Controles de risco** — quais funcionam, quais estao inoperantes",
        "- **Fluxo do OnTick** e a cadeia de abertura de posicao, passo a passo",
        "- **Integracao da IA** — como o sinal entra e o que acontece sem ele",
        "- **Dados** — o que o EA grava, onde, e em que formato",
        "- **Codigo** — onde uma funcao e usada (leio, nao escrevo)",
        "\nExemplos: `qual o pior problema`, `me mostra os controles de risco`, "
        "`como funciona o OnTick`, `o que acontece sem sinal de IA`.",
    ]) + _rodape()


def responder_ambiente(_ctx: Contexto, _pergunta: str) -> str:
    """Estado ao vivo. Leitura, nao opiniao."""
    from backend import copilot_data

    return copilot_data.relatorio_ambiente()


def responder_agenda(_ctx: Contexto, pergunta: str) -> str:
    from backend import copilot_data

    m = re.search(r"(\d+)", pergunta)
    limite = min(20, max(3, int(m.group(1)))) if m else 10
    return copilot_data.relatorio_agenda(limite)


def _por_achado(ctx: Contexto, pergunta: str) -> str:
    """Responde por numero de achado. Cai no geral se o numero nao existir."""
    m = re.search(r"\bachado\s*(\d+)\b", pergunta.lower())
    alvo = next(
        (a for a in ctx.mapa.TODOS_ACHADOS if m and a.id == int(m.group(1))),
        None,
    )
    if alvo is None:
        return responder_geral(ctx, pergunta)
    return _achado_texto(alvo) + _rodape()


MANIPULADORES: dict[str, Callable[[Contexto, str], str]] = {
    "achado": lambda ctx, p: _por_achado(ctx, p),
    "ambiente": responder_ambiente,
    "agenda": responder_agenda,
    "achados": responder_achados,
    "criticos": responder_criticos,
    "risco": responder_risco,
    "fluxo": responder_fluxo,
    "ia": responder_ia,
    "dados": responder_dados,
    "controles": responder_controles,
    "codigo": responder_codigo,
    "mercado": responder_mercado,
    "posicao": responder_posicao,
    "conta": responder_conta,
    "copiloto": responder_copiloto,
    "geral": responder_geral,
}


# ------------------------------------------------------------------ publico


def perguntar(pergunta: str, ctx: Contexto | None = None) -> dict[str, Any]:
    """Ponto de entrada. Devolve resposta, intent e o que foi consultado."""
    ctx = ctx or Contexto()
    texto = (pergunta or "").strip()
    if not texto:
        return {
            "ok": False,
            "resposta": "Pergunta vazia.",
            "intent": "geral",
            "perguntado_em": datetime.now(timezone.utc).isoformat(),
        }
    intent = detectar_intent(texto)
    # Numero de achado tem precedencia: "achado 4" e mais preciso que a area.
    m = re.search(r"\bachado\s*(\d+)\b", texto.lower())
    if m:
        alvo = next((a for a in ctx.mapa.TODOS_ACHADOS if a.id == int(m.group(1))), None)
        if alvo is not None:
            return {
                "ok": True,
                "resposta": _achado_texto(alvo) + _rodape(),
                "intent": "achado",
                "achado": alvo.para_dict(),
                "perguntado_em": datetime.now(timezone.utc).isoformat(),
            }
    resposta = MANIPULADORES.get(intent, responder_geral)(ctx, texto)
    if len(resposta) > LIMITE_RESPOSTA:
        resposta = resposta[:LIMITE_RESPOSTA] + "\n\n_(resposta truncada)_"
    return {
        "ok": True,
        "resposta": resposta,
        "intent": intent,
        "perguntado_em": datetime.now(timezone.utc).isoformat(),
    }


def contexto() -> dict[str, Any]:
    """O que o copiloto sabe, para a UI mostrar sem perguntar."""
    inv = ea_map.inventario()
    return {
        "ok": inv.get("ok", False),
        "mapa": inv,
        "achados_total": len(ea_map.TODOS_ACHADOS),
        "controles": {
            "total": len(ea_map.CONTROLES_DE_RISCO),
            "ativos": len(ea_map.controles_risco("ATIVO")),
            "parciais": len(ea_map.controles_risco("PARCIAL")),
            "inoperantes": len(ea_map.controles_risco("INOPERANTE")),
            "stubs": len(ea_map.controles_risco("STUB")),
        },
        "intents": [nome for nome, _ in INTENTS] + ["geral"],
        "escreve_codigo": False,
        "previsao_mercado": False,
        "nota": (
            "Copiloto de leitura e diagnostico. Le o codigo do projeto e os "
            "artefatos de runtime; nao compila, nao escreve MQL5 e nao preve "
            "preco. O terminal MT5 tem AI Assistant nativo (build 6060+) para "
            "leitura de graficos e geracao de codigo."
        ),
    }
