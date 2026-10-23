# -*- coding: utf-8 -*-
"""A identidade do gateway tem UMA fonte e tres leitores.

MEDIDO 22/10/2026 na versao 1.2.5: `main.rs` e `main.tsx` tinham
`xau-ai-pro-1.2.4-universal-20260928` escrito a mao. O gateway, que deriva a
string de `Docs/version.json`, respondia `xau-ai-pro-1.2.5-universal-20261022`.
Os dois clientes recusaram a identidade e o app instalado abriu com a tela
preta "Falha ao inicializar o ambiente local seguro".

Esta bateria mede os tres lados contra a mesma fonte e tem prova negativa: o
leitor de literal REPROVA um arquivo que escreve o build a mao.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LITERAL = re.compile(r"xau-ai-pro-\d+\.\d+\.\d+-[a-z0-9-]+")


def _build_da_fonte() -> str:
    data = json.loads((RAIZ / "Docs" / "version.json").read_text(encoding="utf-8"))
    stamp = str(data.get("updated_at", "")).replace("-", "")
    if len(stamp) != 8 or not stamp.isdigit():
        stamp = "20260928"
    suffix = str(data.get("gateway_build_suffix", "universal")).strip() or "universal"
    return f"xau-ai-pro-{data['version']}-{suffix}-{stamp}"


def _literais(texto: str) -> list[str]:
    return LITERAL.findall(texto)


def _sem_comentarios(texto: str) -> str:
    """Remove comentario de linha e de bloco antes de medir o codigo."""
    texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    return re.sub(r"//[^\n]*", "", texto)


def test_gateway_deriva_a_mesma_string_da_fonte():
    from backend import mt5_gateway as gw

    assert gw.GATEWAY_BUILD == _build_da_fonte()


def test_frontend_recebe_o_build_gerado_pelo_sync():
    texto = (RAIZ / "frontend" / "src" / "version.ts").read_text(encoding="utf-8")
    assert f"export const GATEWAY_BUILD = '{_build_da_fonte()}'" in texto


def test_rust_le_do_build_e_nao_tem_literal():
    texto = (RAIZ / "frontend" / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    assert 'env!("XAU_GATEWAY_BUILD")' in texto
    assert _literais(_sem_comentarios(texto)) == [], "main.rs nao pode escrever o build a mao"


def test_frontend_importa_a_constante_e_nao_tem_literal():
    texto = (RAIZ / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "GATEWAY_BUILD" in texto
    assert _literais(_sem_comentarios(texto)) == [], "main.tsx nao pode escrever o build a mao"


def test_prova_negativa_o_leitor_reprova_literal():
    # O leitor existe para reprovar. Se ele nao reprova a string velha que
    # causou a tela preta, a bateria acima e decorativa.
    velho = 'payload.gateway_build === "xau-ai-pro-1.2.4-universal-20260928"'
    assert _literais(_sem_comentarios(velho))
