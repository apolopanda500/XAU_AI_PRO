# -*- coding: utf-8 -*-
"""AI Memory + Pensamentos (raciocinio em camadas) para o XAU_AI_PRO.

Memoria persistente em SQLite (chats, pensamentos, fatos aprendidos) e
motor local de "pensamentos" (chain-of-thought) usado quando a IA externa
esta offline. Tambem expoe o keep-alive do assistente.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_APP_ROOT = Path(__file__).resolve().parent.parent
_DB = _APP_ROOT / "database" / "ai_memory.db"
_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  kind TEXT NOT NULL,            -- chat | thought | fact | alert
  content TEXT NOT NULL,
  meta TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_mem_kind ON memories(kind);
CREATE INDEX IF NOT EXISTS idx_mem_ts ON memories(ts);
"""

FACTS_DEFAULT = [
    "XAUUSD e negociado em USD por onca troy; liquidez alta em Londres e NY.",
    "O EA usa predicoes do pipeline Python (XGBoost) salvas em MQL5/Files/Data.",
    "Aporte de risco controlado por RiskPercent, MaxDailyLossPercent e MaxDrawdownPercent.",
    "Regioes de alta liquidez do ouro: 03:00-05:00 e 09:00-12:00 (horario de Brasilia).",
    "Fatos de mercado: ouro tende a subir com juros reais caindo e stress global.",
]


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        c = sqlite3.connect(str(_DB), check_same_thread=False)
        c.executescript(_SCHEMA)
        c.commit()
        return c


def remember(kind: str, content: str, meta: dict[str, Any] | None = None) -> int:
    """Grava uma memoria (chat, thought, fact, alert) e retorna o id."""
    c = _conn()
    try:
        cur = c.execute(
            "INSERT INTO memories (ts, kind, content, meta) VALUES (?,?,?,?)",
            (datetime.utcnow().isoformat(timespec="seconds"), kind, content,
             json.dumps(meta or {}, ensure_ascii=False)),
        )
        c.commit()
        return int(cur.lastrowid)
    finally:
        c.close()


def recall(kind: str | None = None, limit: int = 50, query: str = "") -> list[dict[str, Any]]:
    """Retorna memorias recentes, opcionalmente filtrando por tipo e texto."""
    c = _conn()
    try:
        sql = "SELECT id, ts, kind, content, meta FROM memories"
        args: list[Any] = []
        conds = []
        if kind:
            conds.append("kind=?")
            args.append(kind)
        if query:
            conds.append("content LIKE ?")
            args.append(f"%{query}%")
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        rows = c.execute(sql, args).fetchall()
        return [
            {"id": r[0], "ts": r[1], "kind": r[2], "content": r[3],
             "meta": json.loads(r[4] or "{}")}
            for r in rows
        ]
    finally:
        c.close()


def seed_facts() -> int:
    """Garante os fatos base na memoria (nao duplica)."""
    c = _conn()
    try:
        n = c.execute("SELECT COUNT(*) FROM memories WHERE kind='fact'").fetchone()[0]
        if n > 0:
            return n
        for f in FACTS_DEFAULT:
            c.execute(
                "INSERT INTO memories (ts, kind, content, meta) VALUES (?,?,?,?)",
                (datetime.utcnow().isoformat(timespec="seconds"), "fact", f, "{}"),
            )
        c.commit()
        return len(FACTS_DEFAULT)
    finally:
        c.close()


# ---------------------------------------------------------------------------
# Motor de "pensamentos" (chain-of-thought local, camada por camada)
# ---------------------------------------------------------------------------

def think(query: str, layers: int = 4) -> dict[str, Any]:
    """Gera um raciocinio estruturado em camadas sobre a pergunta do usuario.

    Cada camada aborda um aspecto (contexto, dados, risco, acao). Retorna a
    arvore de pensamentos + conclusao. Usado pelo chat quando a IA externa
    esta offline, e tambem alimenta a memoria.
    """
    q = (query or "").strip().lower()
    if not q:
        return {"thoughts": [], "conclusion": "", "ok": False, "error": "pergunta vazia"}

    thoughts: list[dict[str, str]] = [
        {
            "layer": 1,
            "title": "Contexto",
            "question": f"O que o usuario esta pedindo sobre '{query[:90]}'?",
            "answer": _ctx_answer(q),
        },
        {
            "layer": 2,
            "title": "Dados",
            "question": "Que dados do XAU AI PRO ajudam a responder?",
            "answer": _data_answer(q),
        },
        {
            "layer": 3,
            "title": "Risco",
            "question": "Quais riscos devem ser considerados?",
            "answer": _risk_answer(q),
        },
        {
            "layer": 4,
            "title": "Acao",
            "question": "Qual acao pratica recomendo?",
            "answer": _action_answer(q),
        },
    ][:layers]

    conclusion = f"Analise em {len(thoughts)} camada(s). " + thoughts[-1]["answer"]

    # alimenta a memoria com o pensamento
    try:
        remember("thought", query, {"layers": len(thoughts), "conclusion": conclusion[:200]})
    except Exception:
        pass

    return {
        "thoughts": thoughts,
        "conclusion": conclusion,
        "ok": True,
        "layers": len(thoughts),
    }


def _ctx_answer(q: str) -> str:
    if any(w in q for w in ("posicao", "lucro", "preju", "trade", "ordem", "lote")):
        return "O usuario pergunta sobre posicoes/operacoes. Devo consultar o estado real da conta MT5."
    if any(w in q for w in ("trein", "modelo", "ia", "predic")):
        return "O usuario pergunta sobre o modelo/pipeline IA. Refiro-me ao pipeline Python (XGBoost)."
    if any(w in q for w in ("mercado", "cotacao", "preco", "ouro", "xau")):
        return "O usuario pergunta sobre mercado/cotacoes. Busco o simbolo em MarketData/MT5."
    return "Pergunta generica de apoio ao trading; respondo com regras do sistema e posicao geral."


def _data_answer(q: str) -> str:
    if any(w in q for w in ("mercado", "cotacao", "preco", "ouro")):
        return "Dados disponiveis: cotacoes XAUUSD via MT5/MarketData, predicoes em Files/Data, calendario economico."
    if any(w in q for w in ("posicao", "trade", "lucro")):
        return "Dados: posicoes abertas, historico de deals e saldo disponiveis via MT5Robot/MT5 sync."
    return "Dados disponiveis: dashboard com predicao, dataset, feedbacks, sala e historico do robo."


def _risk_answer(q: str) -> str:
    return ("Riscos: alavancagem, noticias de alto impacto, variacao de spread e "
            "limites diarios (MaxDailyLoss, MaxDrawdown). Nunca sugerir tamanho de "
            "posicao sem conferir o RiskPercent configurado.")


def _action_answer(q: str) -> str:
    if any(w in q for w in ("trein", "modelo")):
        return "Sugiro abrir a aba IA/Treino e executar 'Treinar + Predizer' apos conferir dataset."
    if any(w in q for w in ("posicao", "trade")):
        return "Sugiro abrir a aba Posicoes para ver a carteira real e, se preciso, encerrar via app."
    if any(w in q for w in ("mercado", "cotacao", "preco")):
        return "Sugiro consultar a aba Mercado (cotacoes em tempo real) e o dashboard de predicoes."
    return "Sugiro revisar o dashboard e as abas de monitoramento; estou acompanhando em tempo real."


# ---------------------------------------------------------------------------
# Keep-alive do assistente (IA viva enquanto o app estiver aberto)
# ---------------------------------------------------------------------------

class AIKeepAlive(threading.Thread):
    """Thread daemon que mantem o assistente 'vivo': pulsa a cada N segundos,
    grava pensamento periodico de monitoramento e atualiza o health."""

    def __init__(self, interval: float = 300.0) -> None:  # 5 min padrao
        super().__init__(daemon=True, name="ai-keepalive")
        self.interval = interval
        self._stop_flag = threading.Event()
        self.last_beat: float = 0.0
        self.last_beat_text = "inicio"
        self.started_at = time.time()

    def stop(self) -> None:
        self._stop_flag.set()

    def run(self) -> None:
        seed_facts()
        while not self._stop_flag.is_set():
            self.last_beat = time.time()
            self.last_beat_text = _brief_status()
            try:
                remember("alert", "keepalive", {"uptime_s": int(time.time() - self.started_at)})
            except Exception:
                pass
            self._stop_flag.wait(self.interval)

    def health(self) -> dict[str, Any]:
        return {
            "alive": not self._stop_flag.is_set(),
            "last_beat_ts": self.last_beat,
            "last_beat_text": self.last_beat_text,
            "uptime_s": int(time.time() - self.started_at),
            "memory_db": str(_DB),
        }


def _brief_status() -> str:
    try:
        from app.mcp_tools import enabled_tools
        tools = enabled_tools()
        return f"Monitorando. MCPs ativas: {', '.join(tools) or 'nenhuma'}"
    except Exception:
        return "Monitorando sistema."


_keepalive: AIKeepAlive | None = None


def start_keepalive(interval: float = 300.0) -> AIKeepAlive:
    """Inicia a thread de keep-alive (unica). Retorna a instancia."""
    global _keepalive
    if _keepalive is None or not _keepalive.is_alive():
        _keepalive = AIKeepAlive(interval)
        _keepalive.start()
    return _keepalive


def stop_keepalive() -> None:
    global _keepalive
    if _keepalive is not None:
        _keepalive.stop()
        _keepalive = None