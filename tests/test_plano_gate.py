"""Prova que o plano local realmente trava e destrava o produto.

Por que este arquivo existe
----------------------------
`app/subscriptions.py` expunha `require_entitlement` desde o começo, mas
nenhuma rota do gateway o chamava. O painel de planos mostrava Free/Pro/
Business, o botão "Ativar" respondia 200 — e nada mudava no produto. Um
usuário pagaria por um desbloqueio que não existia.

Estes testes existem para impedir que isso volte. Cada um falha se o gate for
removido, se a feature for trocada de plano, ou se a trava de saque for
afetada por engano.
"""

from __future__ import annotations

import pytest

from backend.planos import subscriptions
from backend import plano_gate
from backend.mt5_gateway import _ROTAS_GET, _ROTAS_POST


@pytest.fixture(autouse=True)
def assinatura_isolada(tmp_path, monkeypatch):
    """Cada teste roda contra um arquivo de assinatura proprio.

    Sem isto os testes escreveriam em %APPDATA% e o estado vazaria entre
    execucoes — um teste que passa por acidente e outro que falha sozinho.
    """
    monkeypatch.setattr(subscriptions, "_path", lambda: tmp_path / "assinaturas.json")
    return tmp_path


# --------------------------------------------------------------------------
# Catalogo
# --------------------------------------------------------------------------

def test_catalogo_tem_os_tres_planos():
    ids = {p["id"] for p in subscriptions.list_plans()}
    assert ids == {"free", "vip", "vips"}


def test_planos_vip_e_vips_tem_os_nomes_do_catalogo():
    """O nome exibido e o que a tela mostra: VIP e VIPS, nao Pro e Business."""
    nomes = {p["id"]: p["name"] for p in subscriptions.list_plans()}
    assert nomes["vip"] == "VIP"
    assert nomes["vips"] == "VIPS"


def test_planos_subem_de_preco():
    precos = [p["reference_price_monthly"] for p in subscriptions.list_plans()]
    assert precos == sorted(precos), "planos devem crescer em preco na ordem do catalogo"


def test_plano_gratuito_nao_paga_nada():
    free = next(p for p in subscriptions.list_plans() if p["id"] == "free")
    assert free["reference_price_monthly"] == 0
    assert free["billing_mode"] == "local_only"


# --------------------------------------------------------------------------
# Divisao de features entre os planos
# --------------------------------------------------------------------------

def test_free_opera_na_mao_mas_nao_automatiza():
    """Free = comandos manuais. O motor automatico e Pro."""
    assert subscriptions.has_entitlement("paper_execution") is True
    assert subscriptions.has_entitlement("advanced_analytics") is False
    assert subscriptions.has_entitlement("economic_calendar") is False


def test_vip_libera_modelo_automatico_e_calendario():
    subscriptions.activate_local_plan("vip")
    for feature in ("ai_signals", "advanced_analytics", "economic_calendar", "social_paper"):
        assert subscriptions.has_entitlement(feature) is True, f"VIP deveria liberar {feature}"


def test_vips_libera_auditoria_avancada():
    subscriptions.activate_local_plan("vips")
    assert subscriptions.has_entitlement("advanced_audit") is True
    assert subscriptions.has_entitlement("priority_support") is True


def test_plano_antigo_pro_ainda_e_aceito():
    """Regressao do renome: quem tinha `pro` gravado nao pode perder o plano.

    Sem a migracao em `_normalized_record`, o registro deixaria de casar com
    o catalogo e o usuario cairia para Free sem aviso.
    """
    resultado = subscriptions.activate_local_plan("pro")
    assert resultado["effective_plan_id"] == "vip"


def test_plano_antigo_business_ainda_e_aceito():
    resultado = subscriptions.activate_local_plan("business")
    assert resultado["effective_plan_id"] == "vips"


def test_motor_automatico_exige_ia():
    """O motor automatico nao pode cair no Free.

    Regressao real: `auto_engine` mapeava para `ai_signals`, que o Free ja
    inclui. O plano basico terminava com o motor ligado, que e o preco do Pro.
    """
    assert plano_gate.entitlement_de("auto_engine") == "advanced_analytics"
    subscriptions.activate_local_plan("free")
    liberado, payload = plano_gate.verificar("auto_engine")
    assert liberado is False
    assert payload["feature"] == "auto_engine"


# --------------------------------------------------------------------------
# O gate realmente bloqueia (o ponto que estava quebrado)
# --------------------------------------------------------------------------

def test_gate_bloqueia_no_free_e_libera_no_vip():
    subscriptions.activate_local_plan("free")
    assert plano_gate.verificar("auto_engine")[0] is False
    subscriptions.activate_local_plan("vip")
    assert plano_gate.verificar("auto_engine")[0] is True


def test_resposta_bloqueio_diz_qual_plano_libera():
    subscriptions.activate_local_plan("free")
    payload = plano_gate.resposta_bloqueio("auto_engine", plano_gate.verificar("auto_engine")[1])
    assert payload["ok"] is False
    assert payload["code"] == "PLAN_REQUIRED"
    assert "VIP" in payload["required_plans"], "a UI precisa saber o que destrava"


def test_gate_nao_derruba_a_leitura_do_catalogo():
    """Sem isto a tela inteira quebraria no Free em vez de mostrar as travas."""
    for rota in ("/api/subscriptions/plans", "/api/subscriptions/me", "/api/auto/state"):
        assert rota not in _ROTAS_GET
        assert rota not in _ROTAS_POST


def test_ordem_manual_e_liberada_no_free():
    """O plano Free precisa servir para alguma coisa: operar na mao."""
    subscriptions.activate_local_plan("free")
    assert _ROTAS_POST["/api/order"] == "manual_order"
    assert plano_gate.verificar("manual_order")[0] is True


def test_rotas_gravadas_tem_feature_conhecida():
    conhecidas = set(plano_gate.FEATURE_PARA_ENTITLEMENT)
    for rota, feature in {**_ROTAS_GET, **_ROTAS_POST}.items():
        assert feature in conhecidas, f"rota {rota} usa feature sem entitlement mapeado: {feature}"


# --------------------------------------------------------------------------
# A unica proibicao do projeto
# --------------------------------------------------------------------------

def test_nenhum_plano_liberaria_saque():
    """Nenhuma feature pode virar saque/transferencia.

    `withdrawals_enabled` e False fixo por AGENTS.md. Falha se alguem mapear
    "withdrawal" ou "transfer" para uma feature de plano.
    """
    proibidas = {"withdrawal", "withdrawals", "transfer", "transferencia", "saque", "resgate"}
    assert not (set(plano_gate.FEATURE_PARA_ENTITLEMENT) & proibidas)
    for plano in subscriptions.list_plans():
        for chave in plano["entitlements"]:
            assert chave not in proibidas, f"plano {plano['id']} expoe entitlement proibido: {chave}"


def test_gate_de_plano_nao_altera_dinheiro_real():
    """Liberar plano nao pode virar execucao real."""
    subscriptions.activate_local_plan("vips")
    assinatura = subscriptions.get_subscription()
    assert assinatura["live_execution"] is False
    assert assinatura["withdrawals_enabled"] is False
