# -*- coding: utf-8 -*-
"""XAU AI PRO - Teste rápido da integração Slack.

Uso:
    python test_slack.py <WEBHOOK_URL>

Exemplo:
    python test_slack.py https://hooks.slack.com/services/T000/B000/XXX

Este script:
  1. Envia uma mensagem de teste ao Slack
  2. Envia notificações de trade (abertura e fechamento) formatadas
  3. Envia um alerta de risco
  4. Verifica se o arquivo forward_test_events.csv existe (se sim, simula leitura)
"""
from __future__ import annotations

import sys

def main() -> None:
    if len(sys.argv) < 2:
        print("❌  Uso: python test_slack.py <WEBHOOK_URL>")
        print("Exemplo: python test_slack.py https://hooks.slack.com/services/T000/B000/XXX")
        return

    webhook = sys.argv[1].strip()

    try:
        import slack_notifier as sn
    except Exception:
        # Adiciona Ultimate/ ao path
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import slack_notifier as sn

    notifier = sn.SlackNotifier()
    notifier.configure(
        webhook_url=webhook,
        enabled=True,
        notify_trades=True,
        notify_errors=True,
        notify_risk=True,
    )

    # 1. Teste básico
    print("Enviando mensagem de teste...")
    ok = notifier.test()
    print("✅  Teste OK!" if ok else "❌  Falha no teste")
    if not ok:
        print("Verifique a URL do webhook e sua conexão.")
        return

    # 2. Trade aberto
    print("\nEnviando notificação de abertura de posição...")
    ok = notifier.send_trade_open("XAUUSD", 0.01, 2345.67, "BUY")
    print("✅  Trade aberto enviado!" if ok else "⏳  (debounce ativo, aguarde 2s)")

    import time
    time.sleep(2.5)

    # 3. Trade fechado (lucro)
    print("Enviando notificação de fechamento (lucro)...")
    ok = notifier.send_trade_close("XAUUSD", 45.30, "TP atingido")
    print("✅  Trade fechado (lucro) enviado!" if ok else "⏳  (debounce ativo)")

    time.sleep(2.5)

    # 4. Trade fechado (prejuízo)
    print("Enviando notificação de fechamento (prejuízo)...")
    ok = notifier.send_trade_close("XAUUSD", -12.40, "SL atingido")
    print("✅  Trade fechado (prejuízo) enviado!" if ok else "⏳  (debounce ativo)")

    time.sleep(2.5)

    # 5. Alerta de risco
    print("Enviando alerta de risco...")
    ok = notifier.send_risk_alert("Drawdown", "5.2% abaixo do balance")
    print("✅  Alerta de risco enviado!" if ok else "⏳  (debounce ativo)")

    time.sleep(2.5)

    # 6. Erro
    print("Enviando notificação de erro...")
    ok = notifier.send_error("MT5", "Conexão perdida - reconectando")
    print("✅  Erro enviado!" if ok else "⏳  (debounce ativo)")

    # 7. Verifica evento stream
    print("\nVerificando forward_test_events.csv...")
    try:
        import slack_watcher as sw
        f = sw._events_file()
        if f:
            print(f"✅  Arquivo de eventos encontrado: {f}")
            print(f"    Monitorando eventos do EA em tempo real.")
        else:
            print("ℹ️   Arquivo forward_test_events.csv ainda não existe.")
            print("    (Será criado quando o EA MT5 rodar com EventEmitter ativo)")
    except Exception as e:
        print(f"ℹ️   Não foi possível verificar watcher: {e}")

    print("\n" + "=" * 50)
    print("✅  TESTE CONCLUÍDO! Verifique seu canal Slack.")
    print("=" * 50)

if __name__ == "__main__":
    main()