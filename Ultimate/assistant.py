"""
XAU AI PRO - AI Assistant com memoria
Chat interno do app com historico persistente no SQLite.
Integracao com LiteLLM Proxy (porta 4000) quando disponivel,
com fallback para respostas locais inteligentes.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from config_store import DB_PATH

# Sentry AI telemetry (Python/ no path)
import sys as _sys
_PY = Path(__file__).resolve().parent.parent / "Python"
if str(_PY) not in _sys.path:
    _sys.path.insert(0, str(_PY))


class MemoryStore:
    """Armazena conversas, pensamentos e notas no SQLite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _ensure_tables(self) -> None:
        conn = self._connect()
        c = conn.cursor()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                model TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS thoughts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                tags TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                content TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """
        )
        conn.commit()
        conn.close()

    def add_message(self, role: str, content: str, model: str = "local") -> None:
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_history(role, content, model, created_at) VALUES(?,?,?,?)",
            (role, content, model, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "SELECT role, content, model, created_at FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = [{"role": r[0], "content": r[1], "model": r[2], "created_at": r[3]} for r in c.fetchall()]
        conn.close()
        rows.reverse()
        return rows

    def clear_history(self) -> None:
        conn = self._connect()
        c = conn.cursor()
        c.execute("DELETE FROM chat_history")
        conn.commit()
        conn.close()

    def add_thought(self, title: str, content: str, tags: str = "") -> None:
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO thoughts(title, content, tags, created_at) VALUES(?,?,?,?)",
            (title, content, tags, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_thoughts(self, limit: int = 100) -> list[dict[str, Any]]:
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "SELECT id, title, content, tags, created_at FROM thoughts ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = [{"id": r[0], "title": r[1], "content": r[2], "tags": r[3], "created_at": r[4]} for r in c.fetchall()]
        conn.close()
        return rows

    def delete_thought(self, thought_id: int) -> None:
        conn = self._connect()
        c = conn.cursor()
        c.execute("DELETE FROM thoughts WHERE id=?", (thought_id,))
        conn.commit()
        conn.close()

    def save_daily_note(self, date: str, content: str) -> None:
        now = datetime.now().isoformat()
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            """INSERT INTO daily_notes(date, content, created_at, updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at""",
            (date, content, now, now),
        )
        conn.commit()
        conn.close()

    def get_daily_note(self, date: str) -> str:
        """Retorna o conteudo da nota diaria (ou string vazia)."""
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT content FROM daily_notes WHERE date=?", (date,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else ""



class AIAssistant:
    """Assistente de conversa com memoria e fallback local."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.memory = MemoryStore(db_path)
        self.system_prompt = (
            "Voce e o assistente do XAU AI PRO, uma plataforma de trading quantitativo. "
            "Responda de forma objetiva, profissional e em portugues do Brasil. "
            "Ajude com analise de mercado, configuracao do robo, codigo MQL5/Python e produtividade."
        )

    def _call_litellm(self, messages: list[dict[str, str]]) -> str | None:
        try:
            import requests
            from config_store import get_api_config

            cfg = get_api_config()
            port = cfg.get("litellm_port", 4000)
            url = f"http://127.0.0.1:{port}/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.7,
            }
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                data = r.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            pass
        return None

    def _local_reply(self, user_msg: str) -> str:
        """Fallback local quando nao ha proxy LLM disponivel."""
        msg = user_msg.lower()
        if any(w in msg for w in ["ola", "oi", "eae"]):
            return "Ola! Sou o assistente do XAU AI PRO. Como posso ajudar com seu trading hoje?"
        if any(w in msg for w in ["robo", "ea", "mt5", "nao abre"]):
            return "Se o robo nao abre operacoes, verifique: 1) margem livre no SafetyManager, 2) spread maximo, 3) sinais no log. Posso ajudar a ajustar o codigo."
        if any(w in msg for w in ["treinar", "modelo", "ia"]):
            return "Para treinar o modelo, use a aba 'Treinamento' e clique em 'Treinar modelos'. O dataset precisa estar em MQL5/Files/Data/dataset.csv."
        if any(w in msg for w in ["configur", "tema", "cor"]):
            return "Voce pode personalizar tema, wallpaper e atalhos na aba 'Configuracoes'. Temos temas dark, light, cyberpunk, crypto e midnight."
        if any(w in msg for w in ["lot", "risco", "tamanho"]):
            return "O calculo de lote segue RiskPercent * Balance / (StopLoss * tickValue). Use a calculadora na aba 'Ferramentas' para simular."
        return "Entendido. Estou aprendendo com essa conversa. Pode detalhar mais o que voce precisa?"

    def _conversation_id(self) -> str:
        """ID de conversa para o Sentry Conversas (gen_ai.conversation.id)."""
        return "chat-%s" % datetime.now().strftime("%Y%m%d")

    def chat(self, user_msg: str) -> str:
        self.memory.add_message("user", user_msg)

        messages = [{"role": "system", "content": self.system_prompt}]
        for h in self.memory.get_history(limit=10):
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_msg})

        # --- Sentry AI Agent Monitoring (gen_ai.* spans) ---
        try:
            import json
            import sentry_sdk
            from sentry_config import set_ai_conversation_id

            conv_id = self._conversation_id()
            set_ai_conversation_id(conv_id)

            with sentry_sdk.start_span(
                op="gen_ai.invoke_agent", name="invoke_agent XAU AI Assistant"
            ) as agent_span:
                agent_span.set_data("gen_ai.request.model", "gpt-4o-mini")
                agent_span.set_data("gen_ai.agent.name", "XAU AI Assistant")
                agent_span.set_data("gen_ai.conversation.id", conv_id)

                with sentry_sdk.start_span(
                    op="gen_ai.request", name="chat gpt-4o-mini"
                ) as req_span:
                    req_span.set_data("gen_ai.request.model", "gpt-4o-mini")
                    req_span.set_data("gen_ai.request.messages", json.dumps(messages))
                    req_span.set_data("gen_ai.request.temperature", 0.7)
                    req_span.set_data("gen_ai.conversation.id", conv_id)

                    reply = self._call_litellm(messages)
                    model = "litellm"

                    req_span.set_data(
                        "gen_ai.response.text",
                        json.dumps([reply]) if reply else "[]",
                    )
                    # Tokens (se o LiteLLM retornar usage na resposta)
                    try:
                        import requests as _r
                        from config_store import get_api_config
                        _cfg = get_api_config()
                        _port = _cfg.get("litellm_port", 4000)
                        _url = f"http://127.0.0.1:{_port}/v1/chat/completions"
                        _pr = {"model": "gpt-4o-mini", "messages": messages, "temperature": 0.7}
                        _rr = _r.post(_url, json=_pr, timeout=15)
                        if _rr.status_code == 200:
                            _u = _rr.json().get("usage", {})
                            if _u.get("prompt_tokens"):
                                req_span.set_data("gen_ai.usage.input_tokens", _u["prompt_tokens"])
                            if _u.get("completion_tokens"):
                                req_span.set_data("gen_ai.usage.output_tokens", _u["completion_tokens"])
                            if _u.get("total_tokens"):
                                req_span.set_data("gen_ai.usage.total_tokens", _u["total_tokens"])
                    except Exception:
                        pass

                agent_span.set_data("gen_ai.response.text", str(reply))
        except Exception:
            # Fallback: sem telemetry, mantem funcionamento
            reply = self._call_litellm(messages)
            model = "litellm"
        if reply is None:
            reply = self._local_reply(user_msg)
            model = "local"

        self.memory.add_message("assistant", reply, model)
        return reply

    def quick_tip(self) -> str:
        tips = [
            "Dica: mantenha o Stop Loss sempre dentro do limite de risco configurado.",
            "Dica: monitore o drawdown diario na aba MT5 / Robo.",
            "Dica: antes de operar em real, valide 1 semana em conta demo.",
            "Dica: sincronize as predicoes do Python com MQL5/Files/Data a cada treinamento.",
            "Dica: use o tema Crypto ou Cyberpunk para uma experiencia mais imersiva.",
        ]
        idx = int(time.time()) % len(tips)
        return tips[idx]

    def get_daily_note(self, date: str) -> str:
        """Delega para o MemoryStore (que possui a conexao do banco)."""
        return self.memory.get_daily_note(date)
