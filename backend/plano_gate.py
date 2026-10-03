"""Gate de plano: traducao entre feature e entitlement do catalogo.

Motivo
------
`app/subscriptions.py` ja expunha `require_entitlement`, mas NENHUMA rota do
gateway o chamava. Os planos apareciam na tela e o botao "Ativar" respondia,
mas nao desbloqueiava nada: o `entitlements` era apenas exibicao. Isso e o
caso mais grave de "rotulo sem lastro" do projeto — a tela prometia plano
pago e o produto nao mudava.

Este modulo centraliza o mapa feature -> entitlement e devolve a resposta
padronizada de recusa, para que a UI possa mostrar a trava com o plano que a
libera em vez de "erro generico".

Regra que NAO muda: nenhuma trava aqui habilita dinheiro real. Saque e
transferencia seguem bloqueados em todos os planos; ver AGENTS.md.
"""

from __future__ import annotations

from typing import Any

# feature pedida pela rota -> chave em plan["entitlements"]
FEATURE_PARA_ENTITLEMENT: dict[str, str] = {
    # Free: leitura de mercado, ordens manuais, sinais basicos.
    "manual_order": "paper_execution",
    "core_market_data": "core_market_data",
    "price_alerts": "price_alerts",
    "ai_signals": "ai_signals",
    # Pro: automacao por modelo e analise avancada.
    # `auto_engine` NAO pode mapear para `ai_signals`: o Free ja tem esse
    # entitlement, e o motor automatico e exatamente o que o Free nao paga.
    # Ele exige `advanced_analytics`, que so entra no Pro.
    "auto_engine": "advanced_analytics",
    "model_backtest": "advanced_analytics",
    "economic_calendar": "economic_calendar",
    "multi_account": "multi_account",
    "social_paper": "social_paper",
    # Business: auditoria e suporte.
    "advanced_audit": "advanced_audit",
    "priority_support": "priority_support",
}

# Rotas GET que so exibem dados. Devolver 403 aqui derrubaria a tela inteira
# para quem esta no Free; a UI precisa LER o catalogo para saber o que existe.
ROTAS_SOMENTE_LEITURA: frozenset[str] = frozenset({
    "/api/subscriptions/plans",
    "/api/subscriptions/me",
    "/api/auto/state",
})


def entitlement_de(feature: str) -> str:
    """Chave de entitlement correspondente a uma feature."""
    return FEATURE_PARA_ENTITLEMENT.get(feature, feature)


def planos_que_liberam(feature: str) -> list[str]:
    """Nomes dos planos que liberam a feature, na ordem de ascending.

    Usado pela UI para dizer "libera no Pro" em vez de "erro".
    """
    from app.subscriptions import list_plans

    alvo = entitlement_de(feature)
    return [
        str(p.get("name", p.get("id")))
        for p in list_plans()
        if bool(p.get("entitlements", {}).get(alvo, False))
    ]


def verificar(feature: str, user_id: str | None = None) -> tuple[bool, dict[str, Any]]:
    """Verifica a feature e devolve (liberado, payload).

    Nunca levanta excecao: a rota decide o codigo HTTP. Em caso de falha
    inesperada ao ler a assinatura, libera (fail-open de plano) e registra o
    motivo — travar o usuario por erro de disco seria pior que o inverso.
    A trava de dinheiro real nao passa por aqui.
    """
    from app.subscriptions import has_entitlement

    try:
        liberado = has_entitlement(entitlement_de(feature), user_id)
    except Exception as exc:  # noqa: BLE001 - assinatura local e acessoria
        return True, {
            "feature": feature,
            "granted": True,
            "degraded": True,
            "motivo": f"assinatura local ilegivel ({type(exc).__name__}); liberado por fallback",
        }
    return liberado, {
        "feature": feature,
        "granted": liberado,
        "degraded": False,
        "motivo": "" if liberado else f"plano local atual não inclui: {feature}",
    }


def resposta_bloqueio(feature: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Corpo padronizado de 403 para feature travada pelo plano."""
    return {
        "ok": False,
        "error": payload.get("motivo") or f"recurso nao liberado no plano atual: {feature}",
        "code": "PLAN_REQUIRED",
        "feature": feature,
        "required_plans": planos_que_liberam(feature),
    }