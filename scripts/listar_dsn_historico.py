# -*- coding: utf-8 -*-
"""Mostra as ocorrencias de DSN com senha, sem expor o valor inteiro.

`auditar_historico_git.py` achou 9 ocorrencias de `https://user:senha@host`.
Antes deagerar, e preciso saber se sao segredo de verdade ou placeholder de
documentacao (`postgres://user:pass@localhost`) — que e o caso comum em README
e exemplo de `.env.example`. Por isso este script mostra o arquivo, o commit e
a senha Mascara, nunca o valor completo.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\listar_dsn_historico.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOG = RAIZ / "Temp" / "hist.log"
JANELA = 4 * 1024 * 1024
SOBREPOSTA = 512

PADRAO = re.compile(r"https?://[^\s:@/]+:([^\s:@/]+)@[^\s/]+")
# Host que so aparece em exemplo/documentacao, nunca em segredo de producao.
HOSTS_DE_EXEMPLO = ("localhost", "127.0.0.1", "exemplo", "example", "SEU_USUARIO", "user", "senha", "pass", "password", "trocar", "CHANGEME")


def mascara(segredo: str) -> str:
    if len(segredo) <= 4:
        return "*" * len(segredo)
    return f"{segredo[:2]}{'*' * (len(segredo) - 4)}{segredo[-2:]}"


def main() -> int:
    if not LOG.is_file():
        print(f"sem {LOG.name}")
        return 2

    offset = 0
    achados: list[tuple[int, str, str, str]] = []
    with LOG.open("rb") as fluxo:
        while True:
            bloco = fluxo.read(JANELA)
            if not bloco:
                break
            texto = bloco.decode("utf-8", errors="replace")
            for m in PADRAO.finditer(texto):
                senha = m.group(1)
                linha = texto[max(0, m.start() - 200):m.start() + 60]
                arquivo = "?"
                for candidato in linha.splitlines()[::-1]:
                    if candidato.startswith("+++ b/") or candidato.startswith("--- a/"):
                        arquivo = candidato.split(" b/")[-1].split(" a/")[-1]
                        break
                achados.append((offset + m.start(), arquivo, senha, m.group(0)))
            if len(bloco) < JANELA:
                break
            offset += len(bloco) - SOBREPOSTA
            fluxo.seek(offset)

    print(f"ocorrencias: {len(achados)}\n")
    reais, exemplos = [], []
    for pos, arquivo, senha, completo in achados:
        alvo = exemplos if any(h in completo.lower() for h in HOSTS_DE_EXEMPLO) else reais
        alvo.append((pos, arquivo, senha, completo))

    print("--- PROVAVELMENTE PLACEHOLDER (host/credencial de exemplo) ---")
    for pos, arquivo, senha, completo in exemplos:
        print(f"  pos {pos:,} | {arquivo} | senha={mascara(senha)}")
    print("\n--- REQUEREM VERIFICACAO (host nao e local) ---")
    for pos, arquivo, senha, completo in reais:
        print(f"  pos {pos:,} | {arquivo} | senha={mascara(senha)} | host={completo.rsplit('@', 1)[-1]}")
    if not reais:
        print("  nenhum: todo host e local/exemplo")
    return 0


if __name__ == "__main__":
    sys.exit(main())