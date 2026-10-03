# -*- coding: utf-8 -*-
"""Varredura de segredos e de artefatos suspeitos antes de commit.

POR QUE ESTE SCRIPT EXISTE
=========================
Antes de mandar qualquer alteracao para o GitHub, e preciso provar tres coisas,
por comando e nao por impressao:

1. nenhum segredo (chave, token, senha, DSN, chave privada) vai no diff;
2. nenhum `.env` esta versionado;
3. nenhum binario, instalador ou script de inicializacao silenciosa entrou.

O item 3 responde a preocupação com virus/PUP: `.exe`, `.vbs`, `.cmd` de
inicializacao automatica e instalador silencioso sao vetores classicos. O projeto
JA bloqueia varios deles no `.gitignore` e no `validate_release.ps1`; aqui a
verificacao e local e roda antes do `git add`.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\auditar_segredos.py
    .\\.venv\\Scripts\\python.exe scripts\\auditar_segredos.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# (rotulo, regex). Os padroes exigem valor com tamanho minimo para nao acusar
# um placeholder, um nome de variavel ou um comentario.
PADROES_SEGREDO: list[tuple[str, re.Pattern[str]]] = [
    ("chave privada", re.compile(r"BEGIN\s+(?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY")),
    ("openai", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("dsn com senha", re.compile(r"https?://[^\s:@/]+:[^\s:@/]+@[^\s/]+")),
    ("api key atribuida", re.compile(
        r"(?i)\b(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|"
        r"bearer[_-]?token|client[_-]?secret)\b\s*[=:]\s*[\"'][^\"'\s]{12,}[\"']"
    )),
    ("senha atribuida", re.compile(
        r"(?i)\b(?:password|passwd|senha)\b\s*[=:]\s*[\"'][^\"'\s]{8,}[\"']"
    )),
]

# Extensao -> (motivo). Binario nunca entra no git; script de inicializacao
# silenciosa e instalador silencioso sao vetor classico de PUP.
ARQUIVOS_PROIBIDOS: dict[str, str] = {
    ".exe": "binario executavel",
    ".dll": "biblioteca compilada",
    ".scr": "screen saver executavel",
    ".sys": "driver de kernel",
    ".vbs": "script de inicializacao silenciosa (padrao PUP)",
    ".msi": "instalador compilado",
    ".apk": "pacote Android",
    ".aab": "bundle Android",
    ".keystore": "chave de assinatura Android",
    ".jks": "chave de assinatura Java",
    ".p12": "certificado com senha",
    ".pfx": "certificado com senha",
    ".pem": "certificado/chave",
    ".env": "configuracao com segredo",
}

# Extensao liberada, com o motivo: precisa de leitura humana.
PERMITIDOS_COM_AUDITORIA = {".bat", ".cmd", ".ps1"}


def _git(*args: str) -> str:
    try:
        r = subprocess.run(
            ["git", *args], cwd=str(RAIZ), capture_output=True,
            text=True, timeout=120, errors="replace",
        )
        return r.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def arquivos_alterados() -> list[Path]:
    """Arquivos modificados e nao rastreados; o git e a fonte da lista."""
    nomes = _git("status", "--porcelain", "--untracked-files=all")
    achados: list[Path] = []
    for linha in nomes.splitlines():
        if len(linha) < 4:
            continue
        bruto = linha[3:].strip()
        if " -> " in bruto:  # renomeado
            bruto = bruto.split(" -> ", 1)[1]
        caminho = RAIZ / bruto.strip('"')
        if caminho.is_file():
            achados.append(caminho)
    return achados


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria de segredos antes do commit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    problemas: list[dict[str, str]] = []
    avisos: list[dict[str, str]] = []
    auditados = arquivos_alterados()

    # 1) Segredo no conteudo do que vai entrar no commit.
    for caminho in auditados:
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Os proprios auditores contem os padroes que procuram. Sem esta
        # exclusao, `auditar_segredos.py` acusa o proprio codigo de
        # "dsn com senha" e o `listar_dsn_historico.py` acusa o que ele
        # deveria listar — o utilitario de auditoria trava o commit.
        if caminho.resolve() in {Path(__file__).resolve(), Path(__file__).with_name("listar_dsn_historico.py").resolve()}:
            continue
        for rotulo, padrao in PADROES_SEGREDO:
            achado = padrao.search(texto)
            if achado:
                problemas.append({
                    "tipo": "segredo",
                    "arquivo": str(caminho.relative_to(RAIZ)),
                    "detalhe": f"{rotulo} (mascara {achado.group(0)[:6]}…)",
                })
                break

    # 2) Extensao proibida entre os que vao entrar.
    for caminho in auditados:
        ext = caminho.suffix.lower()
        if ext in ARQUIVOS_PROIBIDOS:
            problemas.append({
                "tipo": "arquivo-proibido",
                "arquivo": str(caminho.relative_to(RAIZ)),
                "detalhe": ARQUIVOS_PROIBIDOS[ext],
            })
        elif ext in PERMITIDOS_COM_AUDITORIA:
            avisos.append({
                "tipo": "auditar-manualmente",
                "arquivo": str(caminho.relative_to(RAIZ)),
                "detalhe": f"{ext} pode ser instalador/inicializador silencioso",
            })

    # 3) O que JAH esta versionado. O diff nao ve historico antigo.
    for nome in _git("ls-files").splitlines():
        nome = nome.strip()
        if not nome:
            continue
        if nome.startswith(".env") and nome != ".env.example":
            problemas.append({
                "tipo": "env-versionado", "arquivo": nome,
                "detalhe": "arquivo .env no indice do git",
            })
        ext = Path(nome).suffix.lower()
        if ext in ARQUIVOS_PROIBIDOS:
            problemas.append({
                "tipo": "arquivo-proibido", "arquivo": nome,
                "detalhe": f"{ARQUIVOS_PROIBIDOS[ext]} versionado",
            })

    if args.json:
        print(json.dumps({
            "auditados": len(auditados),
            "problemas": problemas,
            "avisos": avisos,
            "aprovado": not problemas,
        }, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("AUDITORIA DE SEGREDOS E ARQUIVOS SUSPEITOS")
        print("=" * 70)
        print(f"arquivos auditados: {len(auditados)}")
        if problemas:
            print(f"\nBLOQUEIOS ({len(problemas)}):")
            for p in problemas:
                print(f"  [{p['tipo']}] {p['arquivo']}\n        {p['detalhe']}")
        else:
            print("\n0 bloqueios: nenhum segredo e nenhum arquivo proibido.")
        if avisos:
            print(f"\nAVISOS ({len(avisos)}) — revise antes de commit:")
            for a in avisos:
                print(f"  {a['arquivo']}: {a['detalhe']}")
        print("\nATENCAO: audita o que vai ENTRAR. Para o historico completo, "
              "use gitleaks ou trufflehog.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())