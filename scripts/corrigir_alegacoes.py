"""Corrige as afirmacoes de CONVERSAHOJE.txt que nao tem lastro.

Verificado em disco antes de cada troca:
  - release/1.2.3 contem 8 artefatos (.exe/.msi/.apk), nao 7
  - release/1.2.3/release-manifest.json NAO existe
  - o scan do Defender cobriu os artefatos, nao um full scan offline
  - o smoke test foi em diretorio isolado, nao em VM/maquina limpa
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ARQUIVO = Path("CONVERSAHOJE.txt")
CHECK = "\u2713"  # [check]
WING = "\u2717"  # [x]
MEIO = "~"


def trocar(texto: str, ancora: str, novo: str) -> tuple[str, bool]:
    """Substitui a linha inteira que contem `ancora` por `novo` (multilinha)."""
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        if ancora in linha:
            linhas[i] = novo
            return "\n".join(linhas) + "\n", True
    return texto, False


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    texto = ARQUIVO.read_text(encoding="utf-8")

    trocas = [
        (
            "release-manifest.json gerado com hashes",
            f"[{WING}] release/1.2.3/release-manifest.json NAO EXISTE.\n"
            "     Afirmacao de 25/09 sem artefato em disco. Ha 8 artefatos em release/1.2.3;\n"
            "     falta gerar e publicar o manifesto com os hashes SHA-256.",
        ),
        (
            "artefatos assinados com Authenticode SHA256",
            f"[{MEIO}] 8 artefatos assinados com Authenticode SHA256 + timestamp RFC3161, com certificado\n"
            "     AUTOASSINADO de teste (Status=UnknownError por definicao, reputacao zero). Nao e\n"
            "     assinatura publica. O conflito A1 (assinatura) vs B3 (Windows gratis) segue\n"
            "     sem decisao do dono.",
        ),
        (
            'Defender: "found no threats"',
            f"[{MEIO}] Defender: \"found no threats\", exit 0, no escopo dos artefatos de release/1.2.3.\n"
            "     Isso NAO equivale ao \"full scan offline com 0 deteccoes\" exigido por\n"
            "     RELATORIO_AUDITORIA_SEGURANCA.md:196.",
        ),
        (
            "Validar bundles/EXEs em instala",
            f"[{MEIO}] Validar bundles/EXEs: executado em DIRETORIO ISOLADO, nao em VM ou maquina\n"
            "     Windows limpa. O Gate D de ACOMPANHAMENTO_OFICIAL_PC_20260921.md:247 pede VM:\n"
            "     ainda NAO cumprido.",
        ),
        (
            "Reconstruir e assinar os artefatos Windows finais ap",
            f"[{MEIO}] Reconstruir e assinar os artefatos Windows finais apos a limpeza\n"
            "     [PARCIAL 25/09 - artefatos gerados, assinatura e de teste]",
        ),
    ]

    for ancora, novo in trocas:
        texto, ok = trocar(texto, ancora, novo)
        print(("OK   " if ok else "SKIP ") + ancora[:52])

    ARQUIVO.write_text(texto, encoding="utf-8")
    restantes = texto.count(f"[{CHECK}] release-manifest")
    return 0 if restantes == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
