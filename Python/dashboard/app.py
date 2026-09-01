"""Painel do AI Trade Engine."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI

# Sentry: ID de conversa por chat (agrupa spans em Conversas).
try:
    from sentry_config import set_ai_conversation_id, set_current_user
except Exception:
    def set_ai_conversation_id(_conv_id):  # noqa: E305
        pass

    def set_current_user(_user_id, username=None):  # noqa: E305
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "MQL5" / "Files" / "Data" / "dataset.csv"
PREDICTIONS_DIR = PROJECT_ROOT / "MQL5" / "Files" / "Data"
DB_PATH = PROJECT_ROOT / "database" / "trading.db"

# Cliente IA (LiteLLM)
client = OpenAI(api_key="anything", base_url="http://localhost:4000")


@st.cache_data
def load_dataset() -> pd.DataFrame | None:
    if not DATASET_PATH.exists():
        return None
    try:
        return pd.read_csv(DATASET_PATH)
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

    tab1, tab2 = st.tabs(["Dashboard", "Chat IA"])

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
                try:
                    # Sentry: agrupa spans desta conversa (gen_ai.conversation.id).
                    set_ai_conversation_id(
                        f"chat:{st.session_state.get('sentry_conv_id', 'default')}"
                    )
                    response = client.chat.completions.create(
                        model="ollama/deepseek-v4-flash:cloud",
                        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    )
                    full_response = response.choices[0].message.content
                    st.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    st.error(f"Erro ao conectar com a IA: {e}")


if __name__ == "__main__":
    main()
