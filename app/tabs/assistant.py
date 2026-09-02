"""
Aba Assistente IA (chat) - usa IA real quando configurada, com fallback local.
"""
from __future__ import annotations

import json
import threading
import tkinter as tk
from typing import Callable

from app.ai_client import ask_ai
from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class AssistantTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._busy = False
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Assistente IA", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.status_lbl = tk.Label(header, text="", bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                                   font=(Theme.FONT_FAMILY, 9))
        self.status_lbl.pack(side="left", padx=12)

        card = Card(self.frame, title="Conversa")
        card.pack(fill="both", expand=True, padx=24, pady=10)
        self.chat = tk.Text(card.body, bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 10),
                            relief="flat", wrap="word", state="disabled", height=20)
        self.chat.pack(fill="both", expand=True, padx=8, pady=8)
        input_frame = tk.Frame(card.body, bg=Theme.CARD)
        input_frame.pack(fill="x", padx=8, pady=8)
        self.entry = tk.Entry(input_frame, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                              relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1,
                              font=(Theme.FONT_FAMILY, 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        self.entry.bind("<Return>", lambda e: self.send())
        PrimaryButton(input_frame, text="Enviar", command=self.send, width=10).pack(side="left", padx=4)
        SecondaryButton(input_frame, text="Limpar", command=self.clear, width=10).pack(side="left", padx=4)

        self.add_message("Assistente", "Ola! Sou o assistente do XAU AI PRO. Pergunte sobre o mercado, o robo ou o treinamento.")
        self._update_status()

    def _update_status(self) -> None:
        try:
            from app.ai_client import health_text
            self.status_lbl.configure(text=health_text())
        except Exception:
            pass

    def add_message(self, sender: str, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{sender}: {text}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.add_message("Voce", text)
        self.entry.delete(0, "end")
        if self._busy:
            self.add_message("Assistente", "Aguarde, ainda estou respondendo...")
            return
        self._busy = True
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text: str) -> None:
        try:
            # 0) Grava a pergunta do usuario na memoria
            try:
                from app.ai_memory import remember
                remember("chat", text, {"sender": "user"})
            except Exception:
                pass
            # 1) Tenta ferramentas MCP habilitadas para dados reais (se houver)
            mcp_note = self._try_mcp_tools(text)
            # 2) IA real configurada
            result = ask_ai([{"role": "user", "content": text}])
            if result.get("ok"):
                reply = result["reply"]
                try:
                    remember("chat", reply, {"sender": "assistant"})
                except Exception:
                    pass
            else:
                # 3) IA offline -> raciocinio em camadas (pensamentos) + memoria
                reply = self._layered_reply(text)
                err = result.get("error") or ""
                if err:
                    reply = f"(IA offline: {err})\n\n{reply}"
            if mcp_note:
                reply = mcp_note + "\n\n" + reply
            self.frame.after(0, lambda: self._done(reply))
        except Exception as e:  # noqa: BLE001
            self.frame.after(0, lambda: self._done(self._layered_reply(text) + f"\n\n(erro local: {e})"))

    def _layered_reply(self, text: str) -> str:
        """Resposta em camadas usando o motor de pensamentos + memorias recentes."""
        try:
            from app.ai_memory import think, recall
            t = think(text, layers=4)
            parts = []
            for th in t.get("thoughts", []):
                parts.append(f"🧠 [{th['title']}] {th['answer']}")
            # complementa com memorias relevantes
            mems = recall(query=text, limit=3)
            if mems:
                parts.append("📚 **Memorias relevantes:**")
                for m in mems[:3]:
                    parts.append(f"  • {m['content'][:120]}")
            if t.get("conclusion"):
                parts.append(f"✅ **Conclusao:** {t['conclusion']}")
            return "\n\n".join(parts) if parts else self._local_reply(text)
        except Exception:
            return self._local_reply(text)

    def _try_mcp_tools(self, text: str) -> str:
        """Usa as MCP habilitadas para enriquecer a resposta com dados reais.

        Retorna uma nota (string) com os dados obtidos, ou '' se nada aplicavel.
        """
        from app.mcp_tools import call_tool, enabled_tools
        t = text.lower()
        enabled = enabled_tools()
        if not enabled:
            return ""
        notes = []

        # Cotacao de simbolo (TradingView / Alpha Vantage habilitados)
        import re
        m = re.search(r"\b(XAUUSD|XAUUSDc|BTCUSD|ETHUSD|EURUSD|GBPUSD|USDJPY|AUDUSD|NZDUSD|USDCAD)\b", text.upper())
        if m and ("tradingview" in enabled or "alpha_vantage" in enabled or "alpaca" in enabled):
            sym = m.group(1)
            if "tradingview" in enabled:
                r = call_tool("tradingview", "quote", symbol=sym)
                if r.get("ok"):
                    items = r["result"].get("items", [])
                    if items:
                        it = items[0]
                        notes.append(f"📊 TradingView {sym}: {it.get('price')} ({it.get('change_pct')})%")
            if not notes and "alpha_vantage" in enabled:
                r = call_tool("alpha_vantage", "quote", symbol=sym)
                if r.get("ok"):
                    g = r["result"]
                    notes.append(f"📈 AlphaVantage {g.get('symbol')}: {g.get('price')} ({g.get('change_pct')})")

        # Status MT5 via gateway
        if "mt5_gateway" in enabled and ("conectar" in t or "mt5" in t or "gateway" in t):
            r = call_tool("mt5_gateway", "health")
            if r.get("ok"):
                res = r["result"]
                txt = json.dumps(res, ensure_ascii=False)[:120] if not isinstance(res, str) else res
                notes.append(f"🔌 MT5 Gateway: {txt}")

        # Banco: consultar trades recentes quando perguntar sobre historico/posicoes
        if "postgres_sqlite" in enabled and ("historico" in t or "posico" in t or "trades" in t or "sql" in t):
            r = call_tool("postgres_sqlite", "query",
                          query="SELECT name FROM sqlite_master WHERE type='table' LIMIT 15")
            if r.get("ok"):
                tables = ", ".join(str(x[0]) for x in r["result"].get("rows", []))
                notes.append(f"🗄️ SQLite tabelas: {tables or 'nenhuma'}")

        return "\n".join(notes)

    def _done(self, reply: str) -> None:
        self._busy = False
        self.add_message("Assistente", reply)
        self.on_status("Mensagem enviada ao assistente")
        self._update_status()

    def clear(self) -> None:
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")

    def _local_reply(self, text: str) -> str:
        t = text.lower()
        if "conectar" in t or "mt5" in t:
            return "Va em 'Robo MT5' e clique em 'Conectar MT5'. Certifique-se de que o MetaTrader 5 esta aberto."
        if "trein" in t:
            return "Na aba 'IA / Treino', clique em 'Treinar + Predizer' para atualizar o modelo. O agendador automatico tambem esta disponivel."
        if "lote" in t or "risco" in t:
            return "Use a aba 'Configuracoes' para ajustar lote, risco percentual, SL e TP."
        if "pre" in t or "mercado" in t:
            return "A aba 'Mercado' mostra cotacoes em tempo real de spot e futuros."
        return "Entendido. Estou monitorando os mercados. Use as abas para acessar dashboard, mercado, carteira e robo."