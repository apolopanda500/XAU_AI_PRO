"""Painel XAU_AI_PRO - versao Streamlit in Snowflake (SiS).

Adaptacao do dashboard local (Python/dashboard/app.py) para rodar
dentro do Snowflake. Diferencas em relacao a versao local:

  - Sem acesso a arquivos do disco (dataset.csv, prediction_*.json,
    trading.db) e sem MetaTrader5: as metricas sao lidas de tabelas
    Snowflake (XAU_AI_PRO.*) quando existem; caso contrario mostram 0.
  - Sem LiteLLM em localhost:4000: o chat usa o Snowflake Cortex
    (snowflake.cortex.Complete) quando disponivel na conta.
"""
from __future__ import annotations

import uuid

import pandas as pd
import streamlit as st

# Snowpark: conexao gerenciada automaticamente pelo ambiente do SiS.
try:
    from snowflake.snowpark.context import get_active_session
except Exception:  # pragma: no cover
    get_active_session = None


def _safe_query(session, sql: str) -> pd.DataFrame | None:
    """Executa uma consulta Snowpark e devolve DataFrame; None em erro."""
    try:
        return session.sql(sql).to_pandas()
    except Exception:
        return None


@st.cache_resource
def _get_session():
    if get_active_session is None:
        return None
    try:
        return get_active_session()
    except Exception:
        return None


@st.cache_data(ttl=60)
def load_dataset() -> pd.DataFrame | None:
    session = _get_session()
    if session is None:
        return None
    return _safe_query(session, "SELECT * FROM XAU_AI_PRO.DATASET LIMIT 1000")


@st.cache_data(ttl=60)
def load_predictions() -> pd.DataFrame | None:
    session = _get_session()
    if session is None:
        return None
    return _safe_query(session, "SELECT * FROM XAU_AI_PRO.PREDICTIONS ORDER BY CREATED_AT DESC LIMIT 500")


@st.cache_data(ttl=60)
def load_feedback() -> pd.DataFrame | None:
    session = _get_session()
    if session is None:
        return None
    return _safe_query(session, "SELECT * FROM XAU_AI_PRO.FEEDBACK ORDER BY CREATED_AT DESC LIMIT 500")


@st.cache_data(ttl=60)
def load_retrain_log() -> pd.DataFrame | None:
    session = _get_session()
    if session is None:
        return None
    return _safe_query(session, "SELECT * FROM XAU_AI_PRO.RETRAIN_LOG ORDER BY CREATED_AT DESC LIMIT 500")


def _ask_cortex(prompt: str) -> str | None:
    """Chama o Snowflake Cortex se disponivel; caso contrario None."""
    session = _get_session()
    if session is None:
        return None
    try:
        import snowflake.cortex as cortex  # type: ignore

        reply = cortex.Complete(
            model="snowflake-arctic",
            prompt=f"Voce e o assistente de trading de ouro (XAU). Responda de forma objetiva.\nPergunta: {prompt}",
            session=session,
        )
        return str(reply)
    except Exception:
        return None


def main() -> None:
    st.set_page_config(page_title="AI Trade Engine Pro (Snowflake)", layout="wide")
    st.title("AI Trade Engine Pro")
    st.caption("Painel de status da IA multi-ativo - Streamlit in Snowflake")

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

        st.info(
            "Fonte de dados: tabelas XAU_AI_PRO.DATASET / PREDICTIONS / FEEDBACK / "
            "RETRAIN_LOG. Execute o setup.sql para cria-las e carregar dados."
        )

    with tab2:
        st.subheader("Converse com o XAU AI PRO (Snowflake Cortex)")

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
                    reply = _ask_cortex(prompt)
                    if reply:
                        st.markdown(reply)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": reply}
                        )
                    else:
                        st.warning(
                            "Cortex nao disponivel nesta conta/regiao. "
                            "O chat requer o Snowflake Cortex habilitado."
                        )
                except Exception as e:  # pragma: no cover
                    st.error(f"Erro ao conectar com a IA: {e}")


if __name__ == "__main__":
    main()