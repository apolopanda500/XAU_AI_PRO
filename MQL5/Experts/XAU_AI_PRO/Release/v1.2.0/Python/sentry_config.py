"""
Configuracao do Sentry para XAU AI Pro
Monitoramento de erros e performance para sistema de trading de XAUUSD
"""

import os
import sys
from pathlib import Path
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# OpenAI SDK e opcional: registra a integracao se o pacote estiver instalado.
try:
    from sentry_sdk.integrations.openai import OpenAIIntegration
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False
    OpenAIIntegration = None  # type: ignore[assignment]
import logging

# ============================================================
# Logging estruturado para o produto Logs do Sentry (Explore > Logs)
# Regras:
#  - use get_logger(__name__) nos modulos
#  - debug/info/warning sao enviados como LOGS (com atributos via extra={})
#  - error/critical sao enviados como ISSUES (event_level=ERROR)
# ============================================================

_LOGGER_NAME = os.getenv("SENTRY_LOGGER_NAME", "xau_ai_pro")
logger = logging.getLogger(_LOGGER_NAME)


def get_logger(name: str | None = None) -> logging.Logger:
    """Retorna um logger filho do logger XAU AI Pro (herda a config do Sentry).

    Uso:  log = get_logger(__name__)
          log.info("sinal validado", extra={"sinal": "BUY", "conf": 0.72})
          log.error("falha na predicao", exc_info=True)
    """
    base = name or "xau_ai_pro"
    return logging.getLogger(base)


def capture_log(level: str, message: str, **attrs) -> None:
    """Envia um log estruturado ao Sentry (Logs) com atributos adicionais.

    wrapper conveniente sobre o logger; so chama se o Sentry estiver ativo.
    """
    if not os.getenv("SENTRY_DSN"):
        return
    lvl = getattr(logging, str(level).upper(), logging.INFO)
    logger.log(lvl, message, extra=attrs)


# Bandeira de depuracao: checkpoints/diagnosticos so saem do processo
# quando DEBUG_SENTRY=1. Em producao nunca geram ruido no Sentry.
_DEBUG_SENTRY = os.getenv("DEBUG_SENTRY", "").strip().lower() in ("1", "true", "yes")

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
    
    # Configuracao de logging -> envia LOGS ao Sentry (Explore > Logs)
    # level: a partir de que nivel registra como log
    # event_level: a partir de que nivel cria ISSUE
    logging_integration = LoggingIntegration(
        level=logging.DEBUG,
        event_level=logging.ERROR,
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        release=get_project_version(),
        environment=environment,
        
        # Performance monitoring para IA/Trading
        traces_sample_rate=0.2 if environment == "production" else 0.0,
        profiles_sample_rate=0.1 if environment == "production" else 0.0,
        # Adiciona dados de inputs/respostas das LLMs e ferramentas (Conversas/Agentes)
        stream_gen_ai_spans=True,
        
        # Seguranca
        send_default_pii=False,
        attach_stacktrace=True,
        
        # Debug apenas em staging
        debug=(environment == "staging"),
        
        # Integracoes
        integrations=[
            logging_integration,
            *([OpenAIIntegration(include_prompts=True)] if _OPENAI_OK else []),
        ],
        
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
    """Define o ID de conversa para o Sentry Conversas (gen_ai.conversation.id)."""
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


def capture_checkpoint(message: str, level: str = "info", **tags) -> None:
    """Checkpoint de verificacao/diagnostico.

    So envia ao Sentry quando DEBUG_SENTRY=1. Em producao e um no-op
    (nunca cria 'non-error issues'). Use para telemetria/diagnostico.
    """
    if not _DEBUG_SENTRY:
        return
    try:
        with sentry_sdk.isolation_scope() as scope:
            for k, v in tags.items():
                scope.set_tag(str(k), str(v))
            scope.set_tag("diagnostic", "true")
            sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


def _register_openai() -> bool:
    """Registra a integracao OpenAI (register-first).

    Garante que o client Sentry esteja inicializado antes de registrar a
    OpenAIIntegration. Retorna True se a integracao ficou ativa.
    """
    if not _OPENAI_OK:
        return False  # pacote openai / integracao indisponivel
    try:
        client = sentry_sdk.get_client()
        if not getattr(client, "dsn", None):
            init_sentry()  # garante bootstrap antes de registrar
            client = sentry_sdk.get_client()
        integrations = getattr(client, "integrations", {}) or {}
        return "openai" in integrations
    except Exception as exc:
        logging.error("[SENTRY] Falha ao registrar OpenAI: %s", exc)
        return False


def ensure_openai_registered() -> None:
    """Fail-fast (padrao Seer): registra OpenAI e valida logo em seguida.

    Se a OpenAIIntegration nao estiver registrada apos o registro, registra
    um erro estruturado (log + evento level=error, sem ruido info) e levanta
    RuntimeError descritivo - acionavel, sem assert silencioso.
    """
    ok = _register_openai()
    if ok:
        logging.info("[SENTRY] OpenAIIntegration registrada.")
        return
    try:
        client = sentry_sdk.get_client()
        integrations = getattr(client, "integrations", {}) or {}
        names = list(integrations.keys())
    except Exception:
        names = []
    logging.error(
        "[SENTRY] OpenAIIntegration NAO registrada. Integracoes ativas: %s", names
    )
    try:
        with sentry_sdk.isolation_scope() as scope:
            scope.set_tag("component", "sentry_bootstrap")
            scope.set_context("integrations", {"active": names})
            sentry_sdk.capture_message(
                f"[SENTRY] OpenAIIntegration nao registrada apos init_sentry() "
                f"(ativas: {names})",
                level="error",
            )
    except Exception:
        pass
    raise RuntimeError(
        "OpenAI provider not registered. Check your API key and provider initialization."
    )


def verify_openai_integration() -> bool:
    """Versao fail-open de ensure_openai_registered(): retorna bool sem levantar.

    Use em caminhos nao-criticos onde um RuntimeError nao deve derrubar o
    processo; para bootstrap critico use ensure_openai_registered().
    """
    return _register_openai()


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

    # Defesa em camadas: checkpoints de verificacao/diagnostico (level=info)
    # nunca viram issue no Sentry, a menos que DEBUG_SENTRY=1 (double-gate).
    if not _DEBUG_SENTRY:
        _lev = str(event.get('level', '') or '').lower()
        _msg_obj = event.get('message') or ''
        _msg = _msg_obj.get('formatted', '') if isinstance(_msg_obj, dict) else str(_msg_obj)
        _markers = ('[VERIFY', '[VERIFY-FINAL', '[CHECKPOINT', '[DEBUG', '[DIAG')
        if _lev == 'info' and any(m in _msg.upper() for m in _markers):
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
        capture_checkpoint(
            f"Backtest completed: {strategy_name} - Win Rate: {win_rate:.2f}%",
            level="info", component="backtest", strategy=strategy_name,
        )

def capture_model_performance(model_metrics):
    """Captura metricas de performance do modelo"""
    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("component", "model_performance")
        scope.set_context("metrics", model_metrics)
        capture_checkpoint(
            f"Model performance: {model_metrics}",
            level="info", component="model_performance",
        )

# Inicializa automaticamente ao importar
init_sentry()
# Padrao Seer: registra o provedor OpenAI ANTES de qualquer validacao.
# Fail-fast em producao (levanta RuntimeError descritivo se ausente).
_register_openai()
