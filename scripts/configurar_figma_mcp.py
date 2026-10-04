# -*- coding: utf-8 -*-
"""Insere o servidor MCP remoto do Figma no `opencode.json`.

POR QUE ESTE SCRIPT EXISTE
==========================
O Figma MCP remoto usa autenticacao OAUTH: o token e gerado pela Figma no
navegador, nunca colado no arquivo. Por isso a entrada e so `type` + `url` —
sem `environment`, ao contrario dos outros servidores locais deste arquivo.

Feito por script e nao a mao porque o JSON precisa continuar valido: uma
virada de virgula errada quebra o OpenCode inteiro, e o sintoma seria
"o OpenCode nao abre", que nao aponta para a causa.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\configurar_figma_mcp.py
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ALVO = RAIZ / "opencode.json"
URL = "https://mcp.figma.com/mcp"

ENTRADA = {
    "type": "remote",
    "url": URL,
    "enabled": True,
    # 60 s: a primeira chamada faz o handshake OAuth e pode demorar. Os outros
    # servidores ficam em 30 s porque sao locais e respondem na hora.
    "timeout": 60000,
}


def inserir() -> int:
    dados = json.loads(ALVO.read_text(encoding="utf-8"))
    mcp = dados.setdefault("mcp", {})
    if "figma" in mcp:
        print("figma ja estava configurado; nada mudou")
    else:
        mcp["figma"] = ENTRADA
        ALVO.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        # Relê do disco: so voltar a ler prova que o JSON é válido.
        json.loads(ALVO.read_text(encoding="utf-8"))
        print(f"figma adicionado -> mcp: {sorted(mcp)}")
    return 0


def main() -> int:
    if not ALVO.exists():
        print(f"FALHA: {ALVO} nao existe")
        return 1
    return inserir()


if __name__ == "__main__":
    sys.exit(main())