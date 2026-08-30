"""
Configuracao do Sentry para XAU AI Pro
Monitoramento de erros e performance para sistema de trading de XAUUSD
"""

import os
import sys
from pathlib import Path
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

# Caminhos do projeto
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Carrega variaveis de ambiente do arquivo .env
def load_env_file():
    """Carrega variaveis de ambiente do arquivo .env"""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Carrega .env antes de qualquer coisa
load_env_file()

def get_project_version():
    """Obtém versão do projeto (lê a primeira versão '## [x.y]' do CHANGELOG)."""
    try:
        import re

        # Tenta ler versão do CHANGELOG (busca o primeiro heading de versão)
        changelog = PROJECT_ROOT / "CHANGELOG.md"
        if changelog.exists():
            with open(changelog, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"##\s*\[([^\]]+)\]", content)
            if match:
                version = match.group(1).strip()
                return f"xau-ai-pro@{version}"

        # Fallback para data
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d")
        return f"xau-ai-pro@{timestamp}"
    except Exception:
        return "xau-ai-pro@unknown"

def init_sentry():
    """Inicializa Sentry com configuracao para XAU AI Pro"""
    
    environment = os.getenv("ENVIRONMENT", "development")
    sentry_dsn = os.getenv("SENTRY_DSN")
    
    # Nao inicializa em development a menos que explicitamente configurado
    if environment == "development" and not sentry_dsn:
        print("[SENTRY] Modo desenvolvimento - monitoramento desativado")
        return
    
    if not sentry_dsn:
        print("[SENTRY] SENTRY_DSN nao configurado")
        return
    
    # Configuracao de logging
    logging_integration = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        release=get_project_version(),
        environment=environment,
        
        traces_sample_rate=1.0,
        # Add data like inputs and responses to/from LLMs and tools;
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        stream_gen_ai_spans=True,
        send_default_pii=True,
        attach_stacktrace=True,
        
        # Debug apenas em staging
        debug=(environment == "staging"),
        
        # Integracoes
        integrations=[logging_integration],
        
        # Filtros customizados para XAU AI Pro
        before_send=before_send_filter,
    )
    
    # Contexto global do projeto
    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("project", "xau_ai_pro")
        scope.set_tag("asset", "XAUUSD")
        scope.set_tag("environment", environment)
        scope.set_context("project_info", {
            "name": "XAU AI Pro",
            "version": get_project_version(),
            "asset": "XAUUSD (Gold)",
            "type": "trading_ai_system"
        })
    
    print(f"[SENTRY] Inicializado: {get_project_version()}")
    print(f"[SENTRY] Environment: {environment}")
    print(f"[SENTRY] Asset: XAUUSD")

def set_ai_conversation_id(conversation_id: str) -> None:
    """Define o ID de conversa para o Sentry Conversas (gen_ai.conversation.id).

    Usa a API oficial sentry_sdk.ai (SDK >= 2.64) com fallback manual.
    """
    try:
        try:
            from sentry_sdk import ai as _sai
            _sai.set_conversation_id(str(conversation_id))
            return
        except Exception:
            pass
        import sentry_sdk
        sentry_sdk.get_current_scope().set_attribute(
            "gen_ai.conversation.id", str(conversation_id)
        )
    except Exception:
        pass


def set_current_user(user_id: str, **fields) -> None:
    """Atribui o usuario corrente (preenche a coluna User do Sentry Conversas)."""
    try:
        import sentry_sdk
        user = {"id": str(user_id)}
        user.update(fields)
        sentry_sdk.set_user(user)
    except Exception:
        pass


def before_send_filter(event, hint):
    """Filtra eventos sensiveis antes de enviar"""
    
    # Remove dados de API keys
    if 'request' in event:
        event['request'].pop('api_key', None)
        event['request'].pop('secret', None)
        event['request'].pop('password', None)
    
    # Ignora erros esperados em rede
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if 'TimeoutError' in str(exc_type):
            return None
        if 'ConnectionError' in str(exc_type):
            return None
    
    # Adiciona tag do projeto
    event.setdefault('tags', {})['project'] = 'xau_ai_pro'
    
    return event

# Funcoes auxiliares para XAU AI Pro

def capture_training_error(epoch, loss, error_msg):
    """Captura erros durante treinamento do modelo"""
    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("component", "training")
        scope.set_tag("asset", "XAUUSD")
        scope.set_context("training", {
            "epoch": epoch,
            "loss": str(loss),
            "error": error_msg,
        })
        sentry_sdk.capture_message(
            f"Training error at epoch {epoch}: {error_msg}",
            level="error"
        )

def capture_prediction_error(symbol, prediction_type, error_msg):
    """Captura erros durante predicao"""
    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("component", "prediction")
        scope.set_tag("symbol", symbol)
        scope.set_context("prediction", {
            "symbol": symbol,
            "prediction_type": prediction_type,
            "error": error_msg,
        })
        sentry_sdk.capture_message(
            f"Prediction error for {symbol}: {error_msg}",
            level="error"
        )

def capture_backtest_results(strategy_name, total_trades, win_rate, profit):
    """Captura resultados de backtest"""
    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("component", "backtest")
        scope.set_tag("strategy", strategy_name)
        scope.set_context("backtest_results", {
            "strategy_name": strategy_name,
            "total_trades": total_trades,
            "win_rate": f"{win_rate:.2f}%",
            "profit": f"{profit:.2f}",
        })
        sentry_sdk.capture_message(
            f"Backtest completed: {strategy_name} - Win Rate: {win_rate:.2f}%",
            level="info"
        )

def capture_model_performance(model_metrics):
    """Captura metricas de performance do modelo"""
    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("component", "model_performance")
        scope.set_context("metrics", model_metrics)
        sentry_sdk.capture_message(
            f"Model performance: {model_metrics}",
            level="info"
        )

# Inicializa automaticamente ao importar
init_sentry()




