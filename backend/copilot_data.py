# -*- coding: utf-8 -*-
"""Leitura de dados vivos para o copiloto.

POR QUE LER AO VIVO EM VEZ DE TER UM LLM
=========================================
Um LLM tem data de corte: ele responde com o que sabia na treino e nunca sabe
o que aconteceu no seu terminal agora. Aqui e o oposto — cada pergunta busca o
estado real no gateway, entao a resposta nunca fica velha.

Esta camada chama os MESMOS endpoints que a interface usa. Nao ha fonte
paralela, nem cache com TTL, nem numero de fallback. Se o gateway nao
responde, o copiloto diz "nao respondeu" — que e a informacao verdadeira.

SEM CUSTO, SEM RAM
==================
Nenhum modelo, nenhuma inferencia: apenas leitura de JSON. Resposta em
milissegundos, consumo de memoria desprezivel.

O QUE ESTE MODULO LE
====================
- Mercado:   cotações, 24h, depth, trades, candles
- Conta:     saldo, moeda, modo da conta, servidor
- Posições:  abertas com P/L
- Risco:     o estado do risk_gate (limites efetivos)
- Execução:  ordens, histórico, fila
- Sistema:   saúde do core, watchdog, boot
- Calendário: eventos econômicos que podem mexer no vol
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

# 3s e suficiente para leitura local e evita travar a UI se o gateway estiver
# ocupado com inferencia. Nao ha retry: repetir so pioraria a espera.
TIMEOUT = 3.0
BASE_PADRAO = "http://127.0.0.1:9001"

# Token do gateway. O Tauri gera um token aleatorio POR SESSAO e o passa aos
# filhos por variavel de ambiente (main.rs:431). Sem ele o gateway responde 401
# — e o motivo pelo qual uma leitura externa daria "HTTP 401" em tudo.
# Esta funcao le a mesma fonte; se nao houver token, a leitura degrada para
# "precisa de sessao" em vez de fingir que o gateway esta fora.
def token_gateway() -> str:
    return (os.getenv("XAU_GATEWAY_TOKEN") or "").strip()


def _base() -> str:
    """Base do gateway. Vem da config do app quando houver."""
    try:
        from backend.mt5_gateway import _mt5_data_path  # type: ignore

        _ = _mt5_data_path()  # so para garantir que o modulo carrega
    except Exception:
        pass
    return BASE_PADRAO


def buscar(caminho: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET no gateway. Devolve dict; nunca levanta excecao.

    Em falha devolve `{"erro": ...}`. O chamador decide como mostrar — mas
    nunca substitui por valor inventado.
    """
    url = _base() + caminho
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    cabecalhos: dict[str, str] = {"Accept": "application/json"}
    token = token_gateway()
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=cabecalhos)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
            corpo = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {
                "erro": "HTTP 401",
                "motivo": "Leitura exige o token da sessão. Reabra o app: o Tauri "
                          "gera o token e o injeta nos filhos.",
            }
        return {"erro": f"HTTP {e.code}", "detalhe": e.read().decode("utf-8", errors="replace")[:200]}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {"erro": "gateway indisponível", "detalhe": str(e)[:200]}
    try:
        return json.loads(corpo)
    except json.JSONDecodeError:
        return {"erro": "resposta não é JSON"}


# ------------------------------------------------------------------ mercado


def _motivo_503(d: dict[str, Any]) -> str | None:
    """Traduz o 503 do gateway em causa legivel.

    Descobri empiricamente que /api/universal/* devolve 503 com
    `ok: false` quando o MT5 nao esta logado — nao e "gateway caiu". Sem esta
    traducao o copiloto diria "sem dados" e o usuario culparia o app em vez de
    notar que falta conectar a conta.
    """
    if not isinstance(d, dict):
        return None
    status = d.get("status")
    if status == 503 or d.get("ok") is False:
        erro = str(d.get("error") or d.get("detalhe") or "").lower()
        prov = d.get("provenance") or {}
        fonte = str((prov.get("fonte") if isinstance(prov, dict) else "") or "").lower()
        if "login" in erro or "conta" in erro or "account" in erro or "mt5" in fonte:
            return "MT5 não está logado em conta nenhuma. Conecte a conta no terminal."
        if erro:
            return erro[:160]
        return f"fonte {d.get('broker')}/{d.get('market')} indisponível ({fonte or 'sem origem'})"
    return None


def _traduzir_erro_gateway(mensagem: str | None, status: Any = None) -> str:
    """Traduz a mensagem do gateway em causa util para o usuario.

    O gateway ja da mensagens precisas ("conta MT5 indisponivel para validar
    risco", "simbolo indisponivel no MT5: XAUUSD"). Reutilizar essas frases e
    melhor que inventar uma: o usuario sabe exatamente o que corrigir. O que
    falta e so acrescentar o que fazer.
    """
    if not mensagem:
        return f"fonte indisponível (HTTP {status})" if status else "fonte indisponível"
    m = str(mensagem).lower()
    if "conta mt5 indisponivel" in m or "conta" in m and "indisponivel" in m:
        return "**Conta MT5 não logada.** Abra o terminal e logue numa conta. " \
               f"({mensagem})"
    if "simbolo indisponivel" in m:
        return f"**Símbolo não existe no Market Watch deste terminal.** {mensagem}"
    if "login" in m or "conect" in m:
        return f"**Terminal desconectado.** {mensagem}"
    return f"`{mensagem}`"


def _erro_de(d: dict[str, Any], padrao: str) -> str:
    """Extrai e traduz o erro de uma resposta do gateway."""
    if not isinstance(d, dict):
        return padrao
    if "erro" in d:
        return _traduzir_erro_gateway(d.get("erro"), d.get("status"))
    m = _motivo_503(d)
    if m:
        return m
    if d.get("ok") is False:
        return _traduzir_erro_gateway(d.get("error"), d.get("status"))
    return padrao


def cotacoes(broker: str = "mt5", market: str = "other",
             simbolos: str = "XAUUSD") -> dict[str, Any]:
    r = buscar("/api/universal/quotes", {"broker": broker, "market": market, "symbols": simbolos})
    if r.get("erro") or r.get("ok") is False or r.get("status") == 503:
        r = {**r, "motivo": _erro_de(r, "sem retorno")}
    return r


def stats24h(symbol: str, broker: str = "mt5", market: str = "other") -> dict[str, Any]:
    return buscar("/api/universal/stats24h", {"symbol": symbol, "broker": broker, "market": market})


def candles(symbol: str, timeframe: str = "H1", limite: int = 200,
            broker: str = "mt5", market: str = "other") -> dict[str, Any]:
    r = buscar("/api/universal/candles", {
        "symbol": symbol, "timeframe": timeframe, "limit": limite,
        "broker": broker, "market": market,
    })
    if r.get("erro") or r.get("ok") is False or r.get("status") == 503:
        r = {**r, "motivo": _erro_de(r, "sem candles")}
    return r


def profundidade(symbol: str, limite: int = 10, broker: str = "mt5", market: str = "other") -> dict[str, Any]:
    return buscar("/api/universal/depth", {
        "symbol": symbol, "limit": limite, "broker": broker, "market": market,
    })


# ------------------------------------------------------------------- conta


def conta(broker: str = "mt5", market: str = "other") -> dict[str, Any]:
    r = buscar("/api/universal/account", {"broker": broker, "market": market})
    if r.get("erro") or r.get("ok") is False or r.get("status") == 503:
        r = {**r, "motivo": _erro_de(r, "sem conta")}
    return r


def posicoes(broker: str = "mt5", market: str = "other") -> dict[str, Any]:
    return buscar("/api/universal/positions", {"broker": broker, "market": market})


def historico(dias: int = 90, symbol: str | None = None, broker: str = "mt5") -> dict[str, Any]:
    params: dict[str, Any] = {"broker": broker, "market": "other", "days": dias}
    if symbol:
        params["symbol"] = symbol
    return buscar("/api/universal/history", params)


# ------------------------------------------------------------------- risco


def risco() -> dict[str, Any]:
    """Estado do risk_gate. Este e o estado que REALMENTE bloqueia ordem."""
    r = buscar("/api/risk/state")
    if r.get("ok") is False or r.get("erro"):
        r = {**r, "motivo": _erro_de(r, "risk_gate sem estado")}
    return r


def demos() -> dict[str, Any]:
    return buscar("/api/trade/orders")


# ------------------------------------------------------------------ sistema


def saude() -> dict[str, Any]:
    return buscar("/api/health")


def watchdog() -> dict[str, Any]:
    return buscar("/api/watchdog")


def boot() -> dict[str, Any]:
    return buscar("/api/boot")


def fila() -> dict[str, Any]:
    return buscar("/api/queue/status")


def calendario(limite: int = 20) -> dict[str, Any]:
    return buscar("/api/economic/calendar", {"limit": limite, "days": 7, "tz": "BRT"})


def journal(limite: int = 40) -> dict[str, Any]:
    return buscar("/api/journal", {"limit": limite})


# ------------------------------------------------------------------ leitura


def _num(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # descarta NaN


def _fmt(v: Any, casas: int = 2) -> str:
    n = _num(v)
    return "--" if n is None else f"{n:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def resumo_do_ambiente() -> dict[str, Any]:
    """Uma leitura de tudo. Usado pela aba 'como esta agora'."""
    saida: dict[str, Any] = {"colhido_em": datetime.now(timezone.utc).isoformat()}

    c = conta()
    saida["conta"] = {
        "disponivel": "erro" not in c and c.get("ok") is not False and c.get("status") != 503,
        "erro": c.get("erro"),
        "motivo": c.get("motivo"),
        "login": (c.get("account") or {}).get("login") if "account" in c else None,
        "servidor": (c.get("account") or {}).get("server") if "account" in c else None,
        "moeda": (c.get("account") or {}).get("currency") if "account" in c else None,
        "saldo": _num(c.get("balance")),
        "patrimonio": _num(c.get("equity")),
        "disponivel_margem": _num(c.get("margin_free")),
        "modo": "DEMO" if c.get("trade_mode") == 1 else "REAL" if c.get("trade_mode") == 0 else "desconhecido",
    }

    p = posicoes()
    lista = p.get("positions") if isinstance(p, dict) else None
    saida["posicoes"] = {
        "disponivel": isinstance(lista, list),
        "erro": p.get("erro") if isinstance(p, dict) else None,
        "quantidade": len(lista) if isinstance(lista, list) else None,
        "pnl_flutuante": sum(x for x in ((_num(q.get("profit")) or 0) for q in (lista or []))),
        "detalhe": [
            {
                "ticket": q.get("ticket"), "symbol": q.get("symbol"),
                "side": q.get("side") or q.get("type"),
                "volume": _num(q.get("volume")),
                "abertura": _num(q.get("price_open") or q.get("entry")),
                "atual": _num(q.get("price_current")),
                "pnl": _num(q.get("profit")),
            }
            for q in (lista or [])[:20]
        ],
    }

    r = risco()
    estado = r.get("estado") or r.get("state") or r
    tem_estado = (
        isinstance(estado, dict)
        and "erro" not in estado
        and r.get("ok") is not False
        and any(k in estado for k in ("daily_loss_pct", "exposure_pct", "drawdown_pct"))
    )
    saida["risco"] = {
        "disponivel": tem_estado,
        "erro": r.get("erro"),
        "motivo": r.get("motivo"),
        "perda_diaria_pct": _num(estado.get("daily_loss_pct")) if isinstance(estado, dict) else None,
        "exposicao_pct": _num(estado.get("exposure_pct")) if isinstance(estado, dict) else None,
        "drawdown_pct": _num(estado.get("drawdown_pct")) if isinstance(estado, dict) else None,
        "posicoes_abertas": estado.get("open_positions") if isinstance(estado, dict) else None,
        "operacoes_dia": estado.get("daily_trades") if isinstance(estado, dict) else None,
        "deve_parar": estado.get("should_stop") if isinstance(estado, dict) else None,
    }

    s = saude()
    saida["sistema"] = {
        "disponivel": "erro" not in s,
        "erro": s.get("erro"),
        "core_online": s.get("core_online", s.get("ok")),
        "gateway": s.get("gateway"),
    }

    return saida


def leitura_do_mercado(symbol: str = "XAUUSD", timeframe: str = "H1") -> dict[str, Any]:
    """Cotacao + 24h + leitura de tendencia dos candles. Sem previsao."""
    saida: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "colhido_em": datetime.now(timezone.utc).isoformat(),
    }

    q = cotacoes(simbolos=symbol)
    items = q.get("quotes") or q.get("data") if isinstance(q, dict) else None
    if isinstance(items, list) and items:
        saida["cotacao"] = {
            "symbol": items[0].get("symbol"),
            "bid": _num(items[0].get("bid")),
            "ask": _num(items[0].get("ask")),
            "last": _num(items[0].get("last")),
            "spread": _num(items[0].get("spread")),
            "fonte": items[0].get("source") or items[0].get("provedor"),
            "recebido": items[0].get("received_at") or items[0].get("timestamp"),
        }
    else:
        saida["cotacao"] = {"erro": q.get("erro") if isinstance(q, dict) else "sem retorno"}

    st = stats24h(symbol)
    std = st.get("stats") or st.get("data") if isinstance(st, dict) else None
    if isinstance(std, dict):
        saida["24h"] = {
            "maxima": _num(std.get("high") or std.get("high_24h")),
            "minima": _num(std.get("low") or std.get("low_24h")),
            "variacao_pct": _num(std.get("change_pct") or std.get("price_change_pct")),
            "volume": _num(std.get("volume")),
            "fonte": std.get("source"),
        }
    else:
        saida["24h"] = {"erro": st.get("erro") if isinstance(st, dict) else "MT5 não expõe 24h"}

    # Tendencia e um FATO sobre os candles, nao uma previsao: OnTick classifica
    # o ultimo fechamento contra a media da janela. Digo qual e o criterio.
    cd = candles(symbol, timeframe, 200)
    cs = cd.get("candles") if isinstance(cd, dict) else None
    if isinstance(cs, list) and len(cs) >= 21:
        fech = [_num(c.get("close")) for c in cs if _num(c.get("close")) is not None]
        if len(fech) >= 21:
            media20 = sum(fech[-20:]) / 20
            ultimo = fech[-1]
            highs = [_num(c.get("high")) for c in cs[-20:] if _num(c.get("high")) is not None]
            lows = [_num(c.get("low")) for c in cs[-20:] if _num(c.get("low")) is not None]
            saida["leitura_tecnica"] = {
                "criterio": "último fechamento contra a média dos 20 anteriores",
                "fechamento": ultimo,
                "media_20": media20,
                "distancia_pct": ((ultimo - media20) / media20 * 100.0) if media20 else None,
                "acima_da_media": ultimo > media20,
                "maxima_janela": max(highs) if highs else None,
                "minima_janela": min(lows) if lows else None,
                "velas": len(fech),
                "aviso": "Leitura descritiva do que já aconteceu. Não é direção futura.",
            }
    else:
        saida["leitura_tecnica"] = {
            "erro": cd.get("erro") if isinstance(cd, dict) else "sem candles suficientes",
        }

    return saida


def agenda_economica(limite: int = 12) -> dict[str, Any]:
    cal = calendario(limite)
    eventos = cal.get("events") if isinstance(cal, dict) else None
    if not isinstance(eventos, list):
        return {"erro": cal.get("erro") if isinstance(cal, dict) else "sem retorno"}
    agora = datetime.now(timezone.utc)
    linhas = []
    for e in eventos[:limite]:
        quando = str(e.get("when") or e.get("time") or e.get("date") or "")
        impacto = str(e.get("impact") or "").lower()
        linhas.append({
            "quando": quando,
            "pais": e.get("country") or e.get("currency"),
            "evento": e.get("title") or e.get("event") or e.get("name"),
            "impacto": impacto,
            "anterior": e.get("previous"),
            "consenso": e.get("forecast") or e.get("consensus"),
            "real": e.get("actual"),
        })
    return {
        "colhido_em": agora.isoformat(),
        "quantidade": len(eventos),
        "eventos": linhas,
        "alto_impacto": [e for e in linhas if e["impacto"] in {"high", "alto", "3"}],
    }


# ----------------------------------------------------------------- formatação

AVISO_SEM_MT5 = (
    "**O MT5 não está logado em conta nenhuma.** Por isso cotação, saldo e "
    "posições não têm o que mostrar. Isso não é o copiloto falhando — é a "
    "conta. Conecte no terminal e pergunte de novo."
)


def relatorio_ambiente() -> str:
    """Como esta o ambiente agora. Texto pronto para a tela."""
    a = resumo_do_ambiente()
    l: list[str] = ["**Como está agora** _(leitura ao vivo)_\n"]

    c = a["conta"]
    if c.get("disponivel"):
        modo = c.get("modo", "?")
        l.append(f"**Conta** — {c.get('moeda') or '?'} · {c.get('servidor') or '?'} · {modo}\n")
        l.append(f"- Saldo: {_fmt(c.get('saldo'))} {c.get('moeda') or ''}")
        l.append(f"- Patrimônio: {_fmt(c.get('patrimonio'))}")
        l.append(f"- Livre para operar: {_fmt(c.get('disponivel_margem'))}\n")
    else:
        l.append(f"**Conta** — {c.get('motivo') or c.get('erro') or 'indisponível'}\n")

    p = a["posicoes"]
    if p.get("disponivel"):
        n = p.get("quantidade") or 0
        l.append(f"**Posições** — {n} aberta(s), P/L flutuante {_fmt(p.get('pnl_flutuante'))}\n")
        for d in (p.get("detalhe") or [])[:8]:
            l.append(
                f"- {d['symbol']} {d['side']} {d['volume']} · "
                f"abertura {_fmt(d['abertura'])} · atual {_fmt(d['atual'])} · "
                f"P/L {_fmt(d['pnl'])}"
            )
        if n:
            l.append("")
    else:
        l.append(f"**Posições** — {p.get('erro') or 'indisponível'}\n")

    r = a["risco"]
    if r.get("disponivel"):
        l.append("**Risco (risk_gate — o que realmente bloqueia ordem)**\n")
        l.append(f"- Perda diária: {_fmt(r.get('perda_diaria_pct'))}% (limite 2%)")
        l.append(f"- Exposição: {_fmt(r.get('exposicao_pct'))}% (limite 5%)")
        l.append(f"- Drawdown: {_fmt(r.get('drawdown_pct'))}% (limite 15%)")
        l.append(
            f"- Posições: {r.get('posicoes_abertas') or 0} (limite 5) · "
            f"operações hoje: {r.get('operacoes_dia') or 0} (limite 20)"
        )
        if r.get("deve_parar"):
            l.append(f"\n**O gateway deve PARAR.** Motivo registrado: {r.get('deve_parar')}")
        l.append("")
    else:
        l.append(
            f"**Risco** — {r.get('motivo') or 'o risk_gate não respondeu'}. "
            "Sem esse estado o motor de operação automática não abre posição "
            "nenhuma (falha fechada).\n"
        )

    s = a["sistema"]
    l.append("**Sistema** — core {}".format(
        "online" if s.get("core_online") else f"indisponível ({s.get('erro') or 'sem resposta'})"
    ))
    return "\n".join(l)


def relatorio_mercado(symbol: str = "XAUUSD", timeframe: str = "H1") -> str:
    """Leitura de mercado. Descritiva, nunca previsao."""
    m = leitura_do_mercado(symbol, timeframe)
    l: list[str] = [f"**{symbol} {timeframe}** _(leitura ao vivo)_\n"]

    q = m.get("cotacao") or {}
    if "erro" in q:
        l.append(f"**Cotação** — indisponível. {q.get('erro')}\n")
    else:
        l.append("**Cotação**")
        l.append(f"- Bid/ask: {_fmt(q.get('bid'))} / {_fmt(q.get('ask'))}")
        l.append(f"- Último: {_fmt(q.get('last'))} · spread: {_fmt(q.get('spread'))}")
        l.append(f"- Fonte: {q.get('fonte') or '?'} · recebido: {q.get('recebido') or '?'}\n")

    d = m.get("24h") or {}
    if "erro" not in d:
        l.append("**Últimas 24h**")
        l.append(f"- Máxima {_fmt(d.get('maxima'))} · mínima {_fmt(d.get('minima'))}")
        l.append(f"- Variação: {_fmt(d.get('variacao_pct'))}%\n")
    else:
        l.append(f"**24h** — {d.get('erro')}\n")

    t = m.get("leitura_tecnica") or {}
    if "erro" in t:
        l.append(f"**Leitura técnica** — {t.get('erro')}")
    else:
        l.append(f"**Leitura técnica** — critério: {t.get('criterio')}")
        l.append(
            f"- Fechamento {_fmt(t.get('fechamento'))} contra média de 20 "
            f"em {_fmt(t.get('media_20'))} "
            f"({'acima' if t.get('acima_da_media') else 'abaixo'}, "
            f"{_fmt(t.get('distancia_pct'))}%)"
        )
        l.append(
            f"- Janela de 20: mínima {_fmt(t.get('minima_janela'))} · "
            f"máxima {_fmt(t.get('maxima_janela'))}\n"
        )

    l.append(
        "_Isso descreve o que já aconteceu nos candles. Não é previsão de "
        "direção — o edge medido do modelo é +0,11 e a confiança média 41,7%._"
    )
    return "\n".join(l)


def relatorio_agenda(limite: int = 10) -> str:
    a = agenda_economica(limite)
    if "erro" in a:
        return f"**Agenda econômica** — indisponível: {a.get('erro')}"
    l = [f"**Agenda econômica** — {a.get('quantidade')} evento(s) nos próximos 7 dias\n"]
    altos = a.get("alto_impacto") or []
    if altos:
        l.append("**Alto impacto** (os que mexem em volatilidade):\n")
        for e in altos[:6]:
            l.append(f"- **{e['quando']}** · {e.get('pais') or '?'} — {e.get('evento') or '?'}")
        l.append("")
    l.append("**Todos**\n")
    for e in (a.get("eventos") or [])[:limite]:
        prev = e.get("anterior")
        cons = e.get("consenso")
        real = e.get("real")
        extra = ""
        if cons not in (None, "-", ""):
            extra = f" · consenso {cons}"
            if prev not in (None, "-", ""):
                extra += f" (anterior {prev})"
            if real not in (None, "-", ""):
                extra += f" · realizado {real}"
        l.append(f"- {e['quando']} · {e.get('pais') or '?'} · {e.get('evento') or '?'}{extra}")
    l.append(
        "\n_Antes de operar perto de um evento de alto impacto, considere o risco "
        "de spread e de slippage._"
    )
    return "\n".join(l)
