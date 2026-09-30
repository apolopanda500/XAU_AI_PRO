# -*- coding: utf-8 -*-
"""Varredura de segredos no HISTORICO completo do git.

`auditar_segredos.py` ve o que vai ENTRAR. Este ve o que JA ENTROU: um token
commitado e depois removido continua no historico e continua valido para quem
leia o repositorio. E a razao de `git rm` nao resolver vazamento.

Le `Temp/hist.log`, gerado por `git log --all -p`, e conta ocorrencias de cada
padrao. Nao imprime o segredo: so a contagem e o primeiro offset.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\auditar_historico_git.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOG = RAIZ / "Temp" / "hist.log"

PADROES: list[tuple[str, str]] = [
    ("chave privada", r"BEGIN\s+(?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY"),
    ("openai", r"\bsk-[A-Za-z0-9]{20,}"),
    ("github token", r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    ("aws access key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("google api key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("slack", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("dsn com senha", r"https?://[^\s:@/]+:[^\s:@/]+@[^\s/]+"),
    ("api key atribuida", (
        r"(?i)\b(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|"
        r"bearer[_-]?token|client[_-]?secret)\b\s*[=:]\s*[\"'][^\"'\s]{16,}[\"']"
    )),
]


def gerar_log(forcar: bool = False) -> bool:
    """`git log --all -p` e grande (1,8 GB aqui); vai para arquivo.

    O arquivo EXISTENTE E REUSADO. Sem essa guarda, cada execucao relia o
    historico inteiro antes de auditar: o script nao terminava nunca, e o
    `LastWriteTime` do log mudava a cada tentativa — sinal de que passava o
    tempo todo no `git log`, nao na auditoria.
    """
    if not forcar and LOG.is_file() and LOG.stat().st_size > 0:
        return True
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("wb") as saida:
        subprocess.run(
            ["git", "log", "--all", "-p"], cwd=str(RAIZ),
            stdout=saida, stderr=subprocess.DEVNULL, timeout=1800,
        )
    return LOG.is_file() and LOG.stat().st_size > 0


def main() -> int:
    if not gerar_log():
        print("nao consegui gerar o log do historico")
        return 2
    tamanho_mb = LOG.stat().st_size / 1e6
    print(f"historico analisado: {LOG.name} ({tamanho_mb:.1f} MB)\n")

    # LEITURA EM BLOCOS, EM MODO BINARIO. O historico deste repo passa de
    # 1,8 GB: ler o arquivo inteiro de uma vez estoura a memoria e o processo
    # morre sem imprimir nada.
    #
    # E PRECISA SER BINARIO. Em modo texto, `seek(posicao)` e relativo a um
    # cookie de decodificacao, nao a um byte: um offset obtido de `tell()` nao
    # pode voltar a ser usado no `seek()`, e a chamada trava o processo com
    # CPU em 0. Foi o que aconteceu na segunda execucao. Em binario o offset
    # e o byte, e o `seek` e exato.
    JANELA = 4 * 1024 * 1024
    SOBREPOSTA = 512  # cobre um token cortado na fronteira do bloco
    contadores = {nome: 0 for nome, _ in PADROES}
    primeira: dict[str, int] = {}
    offset = 0
    with LOG.open("rb") as fluxo:
        while True:
            bloco = fluxo.read(JANELA)
            if not bloco:
                break
            texto = bloco.decode("utf-8", errors="replace")
            for nome, padrao in PADROES:
                for achado in re.finditer(padrao, texto):
                    contadores[nome] += 1
                    primeira.setdefault(nome, offset + achado.start())
            if len(bloco) < JANELA:
                break
            offset += len(bloco) - SOBREPOSTA
            fluxo.seek(offset)
    encontrados = [(nome, contadores[nome], primeira[nome])
                   for nome, _ in PADROES if contadores[nome]]

    if not encontrados:
        print("HISTORICO LIMPO: nenhuma chave privada, token, senha ou DSN "
              "em nenhum commit.")
        return 0

    print("ACHADOS NO HISTORICO — estes valores continuam validos para quem "
          "leia o repositorio:\n")
    for nome, total, offset in encontrados:
        print(f"  {nome}: {total} ocorrencia(s), primeira na posicao {offset}")
    print("\nSe algum for real: o arquivo tem de ser revogado NA FONTE "
          "(token da plataforma, chave do broker), e so depois reescrever o "
          "historico com git-filter-repo/BFG. Apagar o arquivo nao basta.")
    return 1


if __name__ == "__main__":
    sys.exit(main())