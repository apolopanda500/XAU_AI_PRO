# -*- coding: utf-8 -*-
"""XAU AI PRO - Slack Notifier

Envia notificações formatadas para canais Slack via Incoming Webhooks.
Tolerante a falhas: nunca levanta exceções — apenas registra e segue.

Uso:
    from slack_notifier import SlackNotifier
    sn = SlackNotifier.get()
    sn.send_trade_open("XAUUSD", 0.01, 2345.67, "BUY")
    sn.send_trade_close("XAUUSD", 45.30)
    sn.send_error("MT5", "Conexão perdida")
    sn.send_info("Sistema", "Auto-approve aprovado")
"""
from __future__ import annotations

import threading
import time
from typing import Any

try:
    import requests
except Exception:  # noqa: BLE001
    requests = None  # type: ignore[assignment]


# Debounce simples para evitar flood de mensagens
_last_send: float = 0.0
_debounce_lock = threading.Lock()
_DEBOUNCE_SEC = 2.0


class SlackNotifier:
    """Cliente Slack com formatação de blocos e cores por tipo de evento."""

    _instance: "SlackNotifier | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> SlackNotifier:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._webhook_url: str = ""
        self._enabled: bool = True
        self._notify_trades: bool = True
        self._notify_errors: bool = True
        self._notify_risk: bool = True

    # ── Configuração ──
    def configure(self, webhook_url: str, **kwargs: Any) -> None:
        """Configura o webhook e opções de notificação."""
        self._webhook_url = (webhook_url or "").strip()
        self._enabled = kwargs.get("enabled", True)
        self._notify_trades = kwargs.get("notify_trades", True)
        self._notify_errors = kwargs.get("notify_errors", True)
        self._notify_risk = kwargs.get("notify_risk", True)

    @property
    def is_configured(self) -> bool:
        """Retorna True se o webhook URL está definido."""
        return bool(self._webhook_url) and self._webhook_url.startswith(
            "https://hooks.slack.com/services/"
        )

    @staticmethod
    def get() -> "SlackNotifier":
        """Retorna a instância singleton (cria e carrega config se disponível)."""
        inst = SlackNotifier()
        try:
            import config_store as cs

            api_cfg = cs.get_api_config()
            inst.configure(
                webhook_url=api_cfg.get("slack_webhook_url", ""),
                enabled=api_cfg.get("slack_enabled", True),
                notify_trades=api_cfg.get("slack_notify_trades", True),
                notify_errors=api_cfg.get("slack_notify_errors", True),
                notify_risk=api_cfg.get("slack_notify_risk", True),
            )
        except Exception:
            pass
        return inst

    # ── Métodos públicos ──
    def test(self) -> bool:
        """Envia uma mensagem de teste. Retorna True se sucesso."""
        return self._send_raw(
            text=":white_check_mark: XAU AI PRO — conexão Slack OK!",
            color="#36a64f",
        )

    def send_trade_open(
        self, symbol: str, volume: float, price: float, direction: str
    ) -> bool:
        """Notifica abertura de posição (verde)."""
        if not self._notify_trades:
            return False
        arrow = ":arrow_up:" if direction.upper().startswith("BUY") else ":arrow_down:"
        text = (
            f"{arrow} *ABERTURA DE POSIÇÃO*\n"
            f"*Símbolo:* `{symbol}`\n"
            f"*Direção:* `{direction}`\n"
            f"*Volume:* `{volume}` | *Preço:* `{price}`"
        )
        return self._send_raw(text, "#2eb872")

    def send_trade_close(
        self, symbol: str, profit: float, comment: str = ""
    ) -> bool:
        """Notifica fechamento de posição (verde se lucro, vermelho se prejuízo)."""
        if not self._notify_trades:
            return False
        is_profit = profit >= 0
        emoji = ":chart_with_upwards_trend:" if is_profit else ":chart_with_downwards_trend:"
        color = "#2eb872" if is_profit else "#e01e5a"
        sign = "+" if is_profit else ""
        detail = f" | _{comment}_" if comment else ""
        text = (
            f"{emoji} *FECHAMENTO DE POSIÇÃO*\n"
            f"*Símbolo:* `{symbol}`\n"
            f"*Resultado:* `{sign}{profit:.2f}`{detail}"
        )
        return self._send_raw(text, color)

    def send_error(self, module: str, error: str) -> bool:
        """Notifica erro crítico (vermelho)."""
        if not self._notify_errors:
            return False
        text = (
            f":warning: *ERRO NO SISTEMA*\n"
            f"*Módulo:* `{module}`\n"
            f"*Erro:* `{error}`"
        )
        return self._send_raw(text, "#e01e5a")

    def send_risk_alert(self, alert_type: str, detail: str) -> bool:
        """Notifica alerta de risco (laranja)."""
        if not self._notify_risk:
            return False
        text = (
            f":rotating_light: *ALERTA DE RISCO*\n"
            f"*{alert_type}:* `{detail}`"
        )
        return self._send_raw(text, "#ff9900")

    def send_info(self, module: str, message: str) -> bool:
        """Notifica informação geral (azul)."""
        text = f":information_source: *{module}:* {message}"
        return self._send_raw(text, "#4a6784")

    def send_approval(self, approved: bool, details: str = "") -> bool:
        """Notifica resultado do auto-approve."""
        emoji = ":white_check_mark:" if approved else ":x:"
        status = "APROVADO" if approved else "NÃO APROVADO"
        color = "#2eb872" if approved else "#e01e5a"
        text = f"{emoji} *AUTO-APPROVE: {status}*\n{details}" if details else f"{emoji} *AUTO-APPROVE: {status}*"


    # ── Métodos internos ──
    def _send_raw(self, text: str, color: str = "#4a6784") -> bool:
        """Envia mensagem com formatação básica. Retorna True se sucesso."""
        if not self._enabled or not self.is_configured:
            return False

        # Debounce global
        with _debounce_lock:
            global _last_send
            now = time.time()
            if now - _last_send < _DEBOUNCE_SEC:
                return False
            _last_send = now

        if requests is None:
            return False

        payload: dict[str, Any] = {
            "text": text,
            "mrkdwn": True,
            "attachments": [
                {
                    "color": color,
                    "text": text,
                    "mrkdwn_in": ["text"],
                }
            ],
        }

        try:
            resp = requests.post(
                self._webhook_url,
                json=payload,
                timeout=8,
            )
            return resp.status_code == 200
        except Exception:
            return False


# ── Interface global para compatibilidade ──
def send_notification(message: str) -> bool:
    """Função de conveniência: envia mensagem de texto simples."""
    return SlackNotifier.get()._send_raw(message)


def send_trade_open(symbol: str, volume: float, price: float, direction: str) -> bool:
    return SlackNotifier.get().send_trade_open(symbol, volume, price, direction)


def send_trade_close(symbol: str, profit: float, comment: str = "") -> bool:
    return SlackNotifier.get().send_trade_close(symbol, profit, comment)


def send_error(module: str, error: str) -> bool:
    return SlackNotifier.get().send_error(module, error)


def send_risk_alert(alert_type: str, detail: str) -> bool:
    return SlackNotifier.get().send_risk_alert(alert_type, detail)


def send_info(module: str, message: str) -> bool:
    return SlackNotifier.get().send_info(module, message)


def send_approval(approved: bool, details: str = "") -> bool:
    return SlackNotifier.get().send_approval(approved, details)


if __name__ == "__main__":
    sn = SlackNotifier.get()
    if sn.is_configured:
        print("Webhook configurado:", sn._webhook_url[:50] + "...")
        if sn.test():
            print("✅ Mensagem de teste enviada!")
        else:
            print("❌ Falha ao enviar mensagem de teste")
    else:
        print("❌ Slack webhook não configurado.")
        print("Configure em: Configurações → API → slack_webhook_url")
