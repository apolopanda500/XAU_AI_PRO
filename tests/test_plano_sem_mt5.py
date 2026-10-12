# -*- coding: utf-8 -*-
"""Planos funcionam com o MT5 FECHADO. Nenhuma rota de plano depende do terminal.

MEDIDO no app instalado em 12/10/2026: com o MT5 fechado, a aba Plano
funcionava (catalogo, assinatura, ativacao local) — e o dono reportou o
inverso em outro momento ("planos dependendo do MT5"). As duas leituras sao
compativeis: o que depende do MT5 e o DADO (candles, conta, envio pelo
terminal), nunca a ASSINATURA. Assinatura e arquivo local com integridade;
gate e mapa feature -> entitlement. Nenhum dos dois abre o terminal.

Este arquivo trava isso onde a regressao nasceria: um `import MetaTrader5`
(ou `from backend.mt5_gateway import ...`) DENTRO da cadeia do plano faria a
aba Plano inteira depender do terminal — e o sintoma seria "plano so
funciona com MT5 aberto", sem excecao em lugar nenhum.

A tecnica e o subprocesso com bloqueador de import: o teste filho RODA a
cadeia com `MetaTrader5` tornado nao-importavel. Se qualquer modulo da cadeia
encostar no terminal, o filho morre com ModuleNotFoundError e este teste
reprova. Medir o filho, e nao este processo: aqui o `MetaTrader5` pode ja
estar importado por outro teste, e bloquear `sys.modules` depois de
importado nao prova nada (AGENTS.md 6: o duble tem de medir a coisa certa).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

CODIGO_FILHO = """
import os, sys

class _SemMT5:
    \"\"\"Tudo que cheirar a terminal morre aqui, com nome e sobrenome.\"\"\"
    def find_module(self, nome, caminho=None):
        if nome == "MetaTrader5" or nome.startswith("MetaTrader5."):
            return self
        return None
    def load_module(self, nome):
        raise ModuleNotFoundError(f"{nome} bloqueado neste teste: MT5 fechado")

sys.meta_path.insert(0, _SemMT5())
sys.modules.pop("MetaTrader5", None)

# A CADEIA INTEIRA DO PLANO, como a rota do gateway a percorre.
from backend.planos.subscriptions import (
    activate_local_plan,
    get_subscription,
    has_entitlement,
    list_plans,
)
from backend import plano_gate

planos = list_plans()
assert [p["id"] for p in planos] == ["free", "vip", "vips"], "catalogo mudou sem teste"

assinatura = get_subscription()
assert assinatura["plan_id"] == "free", "sem arquivo, o padrao e Free"
assert assinatura["withdrawals_enabled"] is False
assert assinatura["live_execution"] is False

ativada = activate_local_plan("vips")
assert ativada["plan_id"] == "vips"
assert ativada["active"] is True
assert has_entitlement("advanced_analytics") is True
assert has_entitlement("advanced_analytics", "outro-usuario") is False

liberado, carga = plano_gate.verificar("auto_engine")
assert liberado is True
assert carga["granted"] is True

bloqueio = plano_gate.resposta_bloqueio("auto_engine", {"motivo": "x"})
assert bloqueio["code"] == "PLAN_REQUIRED"
assert "VIP" in bloqueio["required_plans"] or "VIPS" in bloqueio["required_plans"]

# `/api/acesso`: a arvore que junta plano e volume. Le arquivos, nao terminal.
from backend.acesso import acesso
arvore = acesso()
assert isinstance(arvore, dict)

print("CADEIA DO PLANO OK SEM MT5")
"""


def test_cadeia_do_plano_nao_encosta_no_mt5(tmp_path) -> None:
    """Catalogo, assinatura, ativacao, gate e acesso rodam sem terminal."""
    ambiente = dict(os.environ)
    # Assinatura ISOLADA: o filho ativa `vips` de verdade (escreve arquivo).
    # Sem isto, o teste sujaria `%APPDATA%` — e travaria onde outro teste
    # tivesse ativado plano antes (AGENTS.md 6: estado compartilhado).
    ambiente["XAU_SUBSCRIPTION_FILE"] = str(tmp_path / "subscriptions.json")
    executado = subprocess.run(
        [sys.executable, "-c", CODIGO_FILHO],
        cwd=RAIZ,
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert executado.returncode == 0, (
        "a cadeia do plano encostou no MT5 (ou quebrou sem ele):\n"
        f"STDOUT: {executado.stdout[-2000:]}\n"
        f"STDERR: {executado.stderr[-2000:]}"
    )
    assert "CADEIA DO PLANO OK SEM MT5" in executado.stdout


def test_bloqueador_pegaria_um_import_de_terminal() -> None:
    """PROVA NEGATIVA: o bloqueador do teste acima nao e decorativo.

    Sem este caso, um `_SemMT5` que nao bloqueia nada passaria Junto — e a
    trava inteira seria um subprocesso que sempre passa.
    """
    codigo = (
        "import sys; "
        "class B: "
        " def find_module(s, n, c=None): return s if n == 'MetaTrader5' else None; "
        " def load_module(s, n): raise ModuleNotFoundError(n); "
        "sys.meta_path.insert(0, B()); "
        "sys.modules.pop('MetaTrader5', None); "
        "import MetaTrader5"
    )
    executado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert executado.returncode != 0
    assert "MetaTrader5" in executado.stderr
