# -*- coding: utf-8 -*-
"""A allowlist de CORS nao tem via aberta.

POR QUE ESTE TESTE EXISTE
==========================
`_cors_origin` devolveu `"*"` quando o pedido NAO trazia cabecalho `Origin`.
Isso nao apareceu em nenhum alerta: o CodeQL apontou as linhas do
`send_header`, e a `*` estava duas funcoes acima.

Medido depois da correcao, os seis casos que importam — inclusive a
tentativa de injecao por CRLF, que e o ataque que a regra
`py/http-response-splitting` descreve.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from backend.mt5_gateway import _cors_origin  # noqa: E402


class TestCorsAllowlist:
    def test_sem_origem_nao_devolve_wildcard(self):
        """O defeito: sem `Origin` a resposta saia com `*`.

        Nao havia teste nenhum cobrindo isto.
        """
        assert _cors_origin(None) is None
        assert _cors_origin("") is None

    def test_origem_permitida_passa(self):
        assert _cors_origin("http://127.0.0.1:1420") == "http://127.0.0.1:1420"
        assert _cors_origin("http://tauri.localhost") == "http://tauri.localhost"

    def test_origem_desconhecida_e_bloqueada(self):
        assert _cors_origin("http://evil.com") is None

    def test_injecao_crlf_nao_passa(self):
        """O ataque da regra `py/http-response-splitting`.

        Uma origem com CRLF nao esta na allowlist e por isso nao chega ao
        cabecalho. O teste fixa isso para que uma futura mudanca que troque a
        allowlist por `startswith` nao reabra o buraco em silencio.
        """
        malicioso = "http://127.0.0.1:1420\r\nX-Injetado: 1"
        assert _cors_origin(malicioso) is None

    def test_prefixo_similar_e_bloqueado(self):
        """`http://127.0.0.1:1420.evil.com` COMECA com uma origem permitida.

        E o caso que quebra um `startswith` usado no lugar da igualdade.
        """
        assert _cors_origin("http://127.0.0.1:1420.evil.com") is None