# -*- coding: utf-8 -*-
"""Toda rota que o frontend chama tem que existir NO GATEWAY LOCAL (9001).

O QUE ACONTECEU (2026-10-02)
===========================
A aba VIP mostrava erro porque `GET /api/vip/progress -> 404`, mesmo com
token valido. Medido no app instalado:

    9001/api/vip/progress -> 404   (gateway local, ONDE o frontend fala)
    9003/api/vip/progress -> 404   (core Rust, NAO tem a rota)

A causa: a rota vivia SO em `backend/fastapi_gateway.py`, que sobe no
servidor HOSPEDADO (Vercel/Nitro). Quem sobe a 9001 e o `main()` de
`backend/mt5_gateway.py` (ThreadingHTTPServer), e ele nao conhecia o caminho.

O mesmo ja tinha acontecido com as rotas de plano — o comentario em
`mt5_gateway.py:2604` registra: *"a tela de Planos recebia 404 em todas as
cinco chamadas e aparecia vazia"*. Corrigido la, o defeito reincidiu aqui.

POR QUE NINGUEM VIU
===================
Nenhum teste ligava "rota que o frontend chama" com "rota que o gateway local
serve". O `test_spec_gateway.py` cobre o empacotamento; este cobre o ROTAS.

A REGRA DESTE TESTE
==================
Toda rota `apiBase()` + caminho, usada por um componente do frontend, tem
que estar em `mt5_gateway.py`. Sem isso a tela mostra 404 silenciosamente —
nao ha excecao, nao ha log, e o build inteiro passa.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
GATEWAY = RAIZ / "backend" / "mt5_gateway.py"
FRONTEND = RAIZ / "frontend" / "src"

#: Rotas que o frontend chama e que precisam existir no gateway local.
#: Descobertas por varredura do `frontend/src` (ver `test_rota_do_frontend_`
#: abaixo, que reprova se alguem usar uma fora desta lista).
ROTAS_DO_APP: tuple[str, ...] = (
    "/api/vip/progress",
    "/api/acesso",
    "/api/subscriptions/plans",
    "/api/subscriptions/me",
    "/api/auto/state",
)


def _servidas_pelo_gateway_local() -> set[str]:
    """Caminhos que o `mt5_gateway.py` atende por `parsed.path == ...`."""
    texto = GATEWAY.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r'parsed\.path\s*==\s*"([^"]+)"', texto))


def test_gateway_local_existe():
    assert GATEWAY.exists(), f"gateway ausente: {GATEWAY}"


@pytest.mark.parametrize("rota", ROTAS_DO_APP)
def test_rota_existe_no_gateway_local(rota: str):
    """O teste que teria pegado o 404 da aba VIP.

    Sem isto o build passa, o instalador instala, o app sobe e a aba
    simplesmente mostra erro — que foi exatamente o relato do dono.
    """
    servidas = _servidas_pelo_gateway_local()
    assert rota in servidas, (
        f"{rota} e chamada pelo frontend (apiBase() -> gateway local 9001) "
        f"mas nao existe em backend/mt5_gateway.py. A tela vai receber 404.\n"
        f"Rotas servidas hoje: {len(servidas)}"
    )


def test_nenhuma_rota_do_app_esta_ausente():
    """Mesma regra, com a lista inteira de uma vez — mostra o que falta."""
    faltando = [r for r in ROTAS_DO_APP if r not in _servidas_pelo_gateway_local()]
    assert not faltando, "rotas ausentes no gateway local:\n  " + "\n  ".join(faltando)


def test_front_end_usa_essas_rotas():
    """Confirma que as rotas acima sao de fato consumidas pelo frontend.

    Sem isto a lista could virar um documento morto: alguem remove a tela e o
    teste continua exigindo a rota.
    """
    pasta = FRONTEND / "components"
    if not pasta.exists():
        pytest.skip("frontend/components ausente neste ambiente")
    textos = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in pasta.rglob("*.tsx")
    )
    assert "/api/vip/progress" in textos, "a aba VIP parou de usar a rota"
    assert "/api/acesso" in textos, "nenhuma tela consome a arvore de acesso"