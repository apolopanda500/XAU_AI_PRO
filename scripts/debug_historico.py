# -*- coding: utf-8 -*-
"""Passos isolados da varredura, para descobrir onde ela trava.

Executa um passo por vez, medindo o tempo de cada um. `auditar_historico_git.py`
ficava com CPU em 0 s e RAM em 4 MB, sem terminar: e este script que diz em
qual passo o processo para. Cada passo imprime ANTES e DEPOIS, entao o ultimo
"antes" sem o "depois" seguinte e o culpado.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\debug_historico.py [n_passos]
"""
from __future__ import annotations

import re
import sys
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


def passo(nome: str):
    """Envolve cada etapa para provar que ela rodou."""
    def deco(funcao):
        def envolvida(*args, **kwargs):
            inicio = time.perf_counter()
            print(f"[+] {nome} ...", flush=True)
            resultado = funcao(*args, **kwargs)
            print(f"[ok] {nome} em {time.perf_counter() - inicio:.2f}s", flush=True)
            return resultado
        return envolvida
    return deco


def main() -> int:
    print(f"log: {LOG} existe={LOG.is_file()}", flush=True)
    if not LOG.is_file():
        return 2
    print(f"tamanho: {LOG.stat().st_size / 1e6:.1f} MB", flush=True)

    with LOG.open("rb") as fluxo:
        bruto = fluxo.read(JANELA)
    texto = bruto.decode("utf-8", errors="replace")
    print(f"bloco: {len(bruto) / 1e6:.1f} MB / {len(texto):,} chars\n", flush=True)

    for nome, padrao in PADROES:
        print(f"[+] regex '{nome}' ...", flush=True)
        inicio = time.perf_counter()
        achados = len(re.findall(padrao, texto))
        print(f"[ok] {nome}: {achados} em {time.perf_counter() - inicio:.2f}s", flush=True)

    # O gargalo real: o LOOP com seek. Três blocos em binario, medindo cada
    # iteracao. Se o `seek` estivesse errado, o offset nao avancaria e o
    # processo leria sempre o mesmo trecho para sempre.
    print("\n--- loop com seek (3 blocos) ---", flush=True)
    with LOG.open("rb") as fluxo:
        offset = 0
        for volta in range(3):
            inicio = time.perf_counter()
            fluxo.seek(offset)
            bloco = fluxo.read(JANELA)
            decodificado = bloco.decode("utf-8", errors="replace")
            total = sum(
                len(re.findall(p, decodificado)) for _, p in PADROES
            )
            print(
                f"    volta {volta}: offset={offset:,} bytes "
                f"liu={len(bloco):,} achados={total} "
                f"em {time.perf_counter() - inicio:.2f}s",
                flush=True,
            )
            offset += len(bloco) - 512
    print(f"offset final: {offset:,} (de {LOG.stat().st_size:,})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())