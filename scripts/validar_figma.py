# -*- coding: utf-8 -*-
"""Valida a FIGMA_TOKEN do `.env` chamando a API real. NUNCA imprime o token.

POR QUE UM SCRIPT E NAO SO O BOTAO "TESTAR" DA TELA
===================================================
O botao existe e funciona, mas depende do app estar com pe. Este script roda
sem o app e responde a pergunta antes de gastar um build de 20 minutos:
"a chave que colei esta certa?"

REGRA QUE ELE NAO QUEBRA
========================
Nenhuma linha imprime, registra ou devolve o valor do token — nem em caso de
erro. A Figma devolve `403` quando o escopo esta errado, e a mensagem aqui
diz QUAL escopo falta, sem repetir a credencial.

O que ele mostra:
  - se a chave foi encontrada no `.env`
  - quantos caracteres tem (serve para pegar `FIGMA_TOKEN=` colado inteiro,
    com o sinal de igual, que e o erro de digitacao mais comum)
  - o que a API respondeu sobre identidade, arquivo e variaveis

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\validar_figma.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENV = RAIZ / ".env"
OK, FALHA, AVISO = "[ ok  ]", "[FALHA ]", "[AVISO ]"


def ler_do_env(nome: str) -> str:
    """Le uma variavel do .env sem ecoar o valor."""
    if not ENV.exists():
        return ""
    prefixo = nome + "="
    for linha in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        if linha.startswith(prefixo):
            return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def chamar(url: str, token: str) -> tuple[int, dict]:
    requisicao = urllib.request.Request(
        url, headers={"X-Figma-Token": token, "User-Agent": "XAU_AI_PRO"}
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            return resposta.status, json.loads(resposta.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", "replace")
        try:
            return erro.code, json.loads(corpo)
        except ValueError:
            return erro.code, {"err": corpo[:120]}


def explicar_escopo(status: int) -> None:
    if status == 403:
        print("        escopo insuficiente. Gere o token com leitura de")
        print("        arquivos e variaveis: figma.com > Settings > Security")
    elif status == 401:
        print("        token invalido ou expirado.")
    else:
        print("        a Figma nao respondeu como esperado; tente de novo.")


def main() -> int:
    token = ler_do_env("FIGMA_TOKEN")
    if not token:
        print(f"{FALHA} FIGMA_TOKEN nao encontrada no .env")
        print(f"        arquivo: {ENV}")
        print("        cole o valor DEPOIS do '=' na linha FIGMA_TOKEN=")
        return 1

    print(f"{OK} chave encontrada: {len(token)} caracteres")

    status, dados = chamar("https://api.figma.com/v1/me", token)
    if status != 200:
        print(f"{FALHA} a Figma respondeu HTTP {status}")
        explicar_escopo(status)
        return 1

    handle = dados.get("handle") or dados.get("email") or "(sem handle)"
    print(f"{OK} identidade: {handle}")

    file_key = ler_do_env("FIGMA_FILE_KEY")
    if not file_key:
        print(f"{AVISO} FIGMA_FILE_KEY vazio: a chave funciona, mas nao ha")
        print("        arquivo ligado para ler.")
        return 0

    status, dados = chamar("https://api.figma.com/v1/files/" + file_key, token)
    if status == 404:
        print(f"{FALHA} arquivo {file_key} nao encontrado ou sem acesso")
        return 1
    if status != 200:
        print(f"{FALHA} arquivo: HTTP {status}")
        explicar_escopo(status)
        return 1
    print(f"{OK} arquivo: {dados.get('name', file_key)}")

    # COMPONENTES E ESTILOS: o que ja da para ler HOJE.
    # Estes endpoints aceitam `file_read`, que e o escopo minimo de qualquer
    # token com acesso ao arquivo. E o que alimenta abas, paineis e tabelas.
    status, dados = chamar(f"https://api.figma.com/v1/files/{file_key}/components", token)
    componentes = dados.get("meta", {}).get("components", []) or []
    print(f"{OK} componentes publicados: {len(componentes)}")
    if componentes:
        nomes = sorted({str(c.get("name", "?")) for c in componentes[:12]})
        print(f"        {', '.join(nomes)}")

    status, dados = chamar(f"https://api.figma.com/v1/files/{file_key}/styles", token)
    estilos = dados.get("meta", {}).get("styles", []) or []
    print(f"{OK} estilos publicados: {len(estilos)}")

    # VARIAVEIS: e o que vira token no CSS, mas exige `file_variables:read`.
    status, dados = chamar(
        f"https://api.figma.com/v1/files/{file_key}/variables/local", token
    )
    if status == 200:
        variaveis = dados.get("meta", {}).get("variables", {}) or {}
        print(f"{OK} variaveis: {len(variaveis)}  <- viram token no CSS")
        return 0

    # A propria Figma devolve a lista de escopos que faltam. Mostramos ela,
    # porque ela e o passo exato a seguir e nao ha como adivinhar.
    print(f"{AVISO} variaveis: HTTP {status} — faltam escopos no token")
    mensagem = str(dados.get("message") or dados.get("err") or "")
    if "requires" in mensagem:
        print(f"        escopo necessario: {mensagem.rsplit('requires', 1)[-1].strip()}")
    if "Invalid scope" in mensagem:
        print("        o token atual tambem recusou:")
        for escopo in mensagem.split(":", 1)[-1].split(",")[:6]:
            print(f"          - {escopo.strip()}")
    print()
    print("        COMO RESOLVER (1 min):")
    print("        1. figma.com > Settings > Security > Personal access tokens")
    print("        2. Edite o token, ou gere um novo")
    print("        3. Em 'Permissions', marque:")
    print("             File content    (file_content:read)")
    print("             File metadata   (file_metadata:read)")
    print("             Variables       (file_variables:read)")
    print("             Library content (library_content:read)")
    print("        4. Cole o valor novo em FIGMA_TOKEN no .env e rode este script")
    return 0


if __name__ == "__main__":
    sys.exit(main())