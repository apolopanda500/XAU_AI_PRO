"""Painel do AI Trade Engine."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI

import sys as _sys

_APP_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_APP_ROOT) in _sys.path:
    _sys.path.remove(str(_APP_ROOT))
_sys.path.insert(0, str(_APP_ROOT))
from app.utils.paths import get_config_path, get_mql_data_path  # noqa: E402

# Sentry: ID de conversa por chat (agrupa spans em Conversas).
try:
    from sentry_config import set_ai_conversation_id, set_current_user
except Exception:
    def set_ai_conversation_id(_conv_id):  # noqa: E305
        pass

    def set_current_user(_user_id, username=None):  # noqa: E305
        pass

# Motor MCP local (Sequential Thinking etc.)
try:
    from app.mcp_tools import call_tool, enabled_tools  # noqa: E402

    MCP_TOOLS_AVAILABLE = True
except Exception:
    call_tool = None  # type: ignore[assignment]
    enabled_tools = lambda: []  # type: ignore[assignment]
    MCP_TOOLS_AVAILABLE = False


# Camadas adicionais: busca global, memoria, calendario e sync MT5.
try:
    from app.search_hub import search_all, quick_summary
    from app.ai_memory import think, recall, remember, start_keepalive
    from app.economic_calendar import event_summary, upcoming_events
    from app.mt5_sync import to_export
    EXTRA_LAYERS = True
except Exception:
    search_all = quick_summary = think = recall = remember = None  # type: ignore[assignment]
    event_summary = upcoming_events = None  # type: ignore[assignment]
    to_export = None  # type: ignore[assignment]
    EXTRA_LAYERS = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PREDICTIONS_DIR = get_mql_data_path()
DATASET_PATH = PREDICTIONS_DIR / "dataset.csv"
DB_PATH = PROJECT_ROOT / "database" / "trading.db"
CONFIG_PATH = get_config_path()


def load_ai_config() -> dict:
    """Le a config do app (api.ai_*) usada pelo chat."""
    cfg = {}
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cfg = (raw.get("api") or {})
    except Exception:
        pass
    return {
        "enabled": bool(cfg.get("ai_enabled", False)),
        "base_url": str(cfg.get("ai_base_url", "") or "").strip().rstrip("/"),
        "api_key": str(cfg.get("ai_api_key", "") or "").strip(),
        "model": str(cfg.get("ai_model", "ollama/deepseek-v4-flash:cloud") or ""),
    }


def make_client(cfg: dict) -> OpenAI | None:
    """Cria o cliente OpenAI-compatible a partir da config (None se desativado)."""
    if not cfg["enabled"]:
        return None
    base = cfg["base_url"] or "http://localhost:4000"
    # Garante sufixo /v1 (LiteLLM local e gateways OpenAI-compatible)
    if not base.endswith("/chat/completions"):
        if not base.endswith("/v1"):
            base = base + "/v1"
    return OpenAI(api_key=cfg["api_key"] or "anything", base_url=base)


@st.cache_data
def load_dataset() -> pd.DataFrame | None:
    if not DATASET_PATH.exists():
        return None
    try:
        python_dir = PROJECT_ROOT / "Python"
        if str(python_dir) not in _sys.path:
            _sys.path.insert(0, str(python_dir))
        from data.data_engine_xau import DataEngineXAU

        return DataEngineXAU(DATASET_PATH).load()
    except Exception:
        return None


@st.cache_data
def load_predictions() -> pd.DataFrame | None:
    files = sorted(PREDICTIONS_DIR.glob("prediction_*.json"))
    records = []
    for path in files:
        try:
            data = pd.read_json(path, typ="series")
            data["file"] = path.name
            records.append(data)
        except Exception:
            continue
    if not records:
        return None
    return pd.DataFrame(records)


@st.cache_data
def load_feedback() -> pd.DataFrame | None:
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        return pd.read_sql_query(
            "SELECT * FROM prediction_feedback ORDER BY id DESC LIMIT 500", conn
        )
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


@st.cache_data
def load_retrain_log() -> pd.DataFrame | None:
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        return pd.read_sql_query(
            "SELECT * FROM retrain_log ORDER BY id DESC LIMIT 500", conn
        )
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> None:
    st.set_page_config(page_title="AI Trade Engine", layout="wide")
    st.title("AI Trade Engine Pro")
    st.caption("Painel de status da IA multi-ativo")

    ai_cfg = load_ai_config()
    client = make_client(ai_cfg)

    tab1, tab2, tab3 = st.tabs(["Dashboard", "Chat IA", "Pesquisa Global"])

    # Barra lateral: calendario economico + sync MT5
    if EXTRA_LAYERS:
        with st.sidebar:
            st.subheader("📅 Calendário Econômico (BRT)")
            try:
                for line in (event_summary(tz="BRT") or []):
                    st.write(line)
            except Exception:
                st.write("Calendário indisponível")
            st.divider()
            st.subheader("🔄 Sync MT5")
            try:
                s = to_export() or {}
                st.metric("MT5", "Conectado" if s.get("conectado") else "Offline")
                st.metric("Posições", s.get("positions_count", 0))
                st.metric("Histórico", s.get("history_count", 0))
            except Exception:
                st.write("Sync indisponível")
            st.divider()
            st.subheader("🔍 Resumo")
            try:
                qs = quick_summary() or {}
                st.write(f"MCP: {qs.get('mcp', 0)} | Agentes: {qs.get('agentes', 0)}")
                st.write(f"Ativos: {qs.get('ativos', 0)} | Chats: {qs.get('chats', 0)}")
            except Exception:
                pass

    with tab1:
        dataset = load_dataset()
        predictions = load_predictions()
        feedback = load_feedback()
        retrain_log = load_retrain_log()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Registros no dataset", len(dataset) if dataset is not None else 0)
        with col2:
            st.metric(
                "Predições geradas", len(predictions) if predictions is not None else 0
            )
        with col3:
            st.metric("Feedbacks registrados", len(feedback) if feedback is not None else 0)
        with col4:
            st.metric(
                "Logs de retreino", len(retrain_log) if retrain_log is not None else 0
            )

        if predictions is not None and not predictions.empty:
            st.subheader("Últimas predições")
            st.dataframe(predictions.head(50), use_container_width=True)

        if feedback is not None and not feedback.empty:
            st.subheader("Feedbacks recentes")
            st.dataframe(feedback.head(50), use_container_width=True)

        if retrain_log is not None and not retrain_log.empty:
            st.subheader("Retreinos recentes")
            st.dataframe(retrain_log.head(50), use_container_width=True)

    with tab2:
        st.subheader("Converse com o XAU AI PRO")

        if client is None:
            st.info(
                "IA desativada no aplicativo. Abra XAU AI PRO > Configuracoes > "
                "Assistente IA, marque 'Habilitar IA real', preencha URL base / chave / "
                "modelo e clique em Salvar. Depois recarregue esta pagina."
            )
        else:
            st.caption(f"Modelo: {ai_cfg['model']} @ {ai_cfg['base_url'] or 'localhost:4000'}")

        # Modo raciocinio estruturado (MCP Sequential Thinking)
        usar_sequencial = st.checkbox(
            "🧠 Raciocínio sequencial (MCP)",
            value=st.session_state.get("usar_sequencial", False),
            help="Encadeia passos de análise (Sequential Thinking) antes de responder solo.",
        )
        st.session_state.usar_sequencial = usar_sequencial
        if usar_sequencial and MCP_TOOLS_AVAILABLE:
            st.caption("Ferramentas MCP: " + ", ".join(enabled_tools() or []))

        # Sentry: identifica o usuario (coluna User em Conversas) e cria ID de conversa.
        if "sentry_user_id" not in st.session_state:
            st.session_state.sentry_user_id = "chat:" + uuid.uuid4().hex[:12]
            set_current_user(st.session_state.sentry_user_id, username="dashboard")
        if "sentry_conv_id" not in st.session_state:
            st.session_state.sentry_conv_id = uuid.uuid4().hex[:12]

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Pergunte algo sobre o mercado..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                if usar_sequencial and MCP_TOOLS_AVAILABLE and call_tool is not None:
                    try:
                        r = call_tool(
                            "sequential_thinking",
                            thought=prompt,
                            thoughtNumber=1,
                            totalThoughts=5,
                        )
                        if r.get("ok"):
                            res = r.get("result") or {}
                            linhas = [f"**Pensamento {i + 1}:** {p.get('question', '')}"
                                      for i, p in enumerate(res.get("steps", []))]
                            full_response = "🧠 **Raciocínio sequencial (MCP)**\n\n" + "\n\n".join(linhas)
                            if res.get("branches"):
                                full_response += "\n\n**Ramos:** " + ", ".join(res["branches"])
                        else:
                            full_response = "MCP Sequential Thinking: erro → " + str(r.get("error", ""))
                    except Exception as mcp_exc:
                        full_response = f"MCP Sequential Thinking falhou: {mcp_exc}"
                    st.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                elif client is None:
                    st.warning("IA desativada - configure no aplicativo (Configuracoes > Assistente IA).")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": "[IA desativada no aplicativo]"}
                    )
                else:
                    try:
                        # Sentry: agrupa spans desta conversa (gen_ai.conversation.id).
                        set_ai_conversation_id(
                            f"chat:{st.session_state.get('sentry_conv_id', 'default')}"
                        )
                        response = client.chat.completions.create(
                            model=ai_cfg["model"],
                            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                        )
                        full_response = response.choices[0].message.content
                        st.markdown(full_response)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    except Exception as e:
                        msg = str(e)
                        hint = ""
                        if "localhost" in msg or "Connection" in msg or "No connection" in msg:
                            hint = " - o servico de IA (LiteLLM/gateway) nao esta respondendo na URL configurada"
                        st.error(f"Erro ao conectar com a IA: {msg}{hint}")

    with tab3:
        st.subheader("🔍 Pesquisa Global no Aplicativo")
        q = st.text_input("Buscar", placeholder="ex.: xau, mercado, posicao, FOMC, MCP")
        if q and EXTRA_LAYERS and search_all is not None:
            r = search_all(q)
            st.caption(f"{r.get('total', 0)} resultado(s) para '{q}'")
            secs = [("🛠️ MCP", r.get("mcp", [])),
                    ("🤖 Agentes", r.get("agentes", [])),
                    ("💬 Chats/Memória", r.get("chats", [])),
                    ("📈 Ativos", r.get("ativos", [])),
                    ("📅 Calendário", r.get("calendario", []))]
            for titulo, items in secs:
                with st.expander(f"{titulo} ({len(items)})", expanded=len(items) > 0):
                    if not items:
                        st.write("Nenhum resultado")
                    for it in items:
                        st.markdown(f"**{it.get('nome','')}** — {it.get('descricao','')}")
        elif not EXTRA_LAYERS:
            st.info("Camadas extras indisponíveis.")


if __name__ == "__main__":
    main()
