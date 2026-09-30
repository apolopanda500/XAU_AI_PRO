# -*- coding: utf-8 -*-
"""Mede qual padrao esta caro na varredura do historico.

O primeiro `auditar_historico_git.py` nao terminava: 1,8 GB com 8 regex e
`read_text` inteiro. A segunda versao, em blocos, ficava com CPU em 0 e RAM em
4 MB — sinal de bloqueio, nao de lentidao. Este script isola o gargalo: le UM
bloco e mede cada padrao separadamente.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\benchmark_historico.py
"""
from __future__ import annotations

import re
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOG = RAIZ / "Temp" / "hist.log"
JANELA = 4 * 1024 * 1024

PADROES: list[tuple[str, str]] = [
    ("chave privada", r"BEGIN\s+(?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY"),
    ("openai", r"\bsk-[A-Za-z0-9]{20,}"),
    ("github token", r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    ("aws", r"\bAKIA[0-9A-Z]{16}\b"),
    ("google", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("slack", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("dsn", r"https?://[^\s:@/]+:[^\s:@/]+@[^\s/]+"),
    ("api key atribuida", (
        r"(?i)\b(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|"
        r"bearer[_-]?token|client[_-]?secret)\b\s*[=:]\s*[\"'][^\"'\s]{16,}[\"']"
    )),
]


def main() -> int:
    if not LOG.is_file():
        print(f"sem {LOG.name}; rode: git log --all -p > Temp/hist.log")
        return 2

    inicio = time.perf_counter()
    with LOG.open("rb") as fluxo:
        bruto = fluxo.read(JANELA)
    leitura = time.perf_counter() - inicio
    texto = bruto.decode("utf-8", errors="replace")
    print(f"bloco lido: {len(bruto) / 1e6:.1f} MB em {leitura:.1f}s")
    print(f"caracteres:  {len(texto):,}\n")

    total = 0.0
    for nome, padrao in PADROES:
        t0 = time.perf_counter()
        achados = len(re.findall(padrao, texto))
        decorrido = time.perf_counter() - t0
        total += decorrido
        alerta = "  <-- CARO" if decorrido > 1.0 else ""
        print(f"  {nome:20} {decorrido:7.2f}s  {achados:5} ocorrencia(s){alerta}")

    print(f"\ntotal das regex: {total:.1f}s por bloco de {len(bruto) / 1e6:.1f} MB")
    if LOG.stat().st_size:
        blocos = LOG.stat().st_size / len(bruto)
        print(f"estimativa para o arquivo inteiro: {total * blocos / 60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())