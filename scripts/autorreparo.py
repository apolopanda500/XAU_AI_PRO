# -*- coding: utf-8 -*-
"""Auto-reparo do XAU AI PRO: corrige o que e seguro corrigir sozinho.

Por que existe ao lado do `preflight`
--------------------------------------
O `preflight.py` diagnostica e NAO altera nada — por desenho, porque um
diagnostico que muda o ambiente mente sobre o estado que encontrou. Este
script e o outro lado: ele age. Mas so no que tem reparo inequivoco, e
declara o que fez.

A divisao que vale
-----------------
O que este script faz e sempre a MESMA COISA que o dono faria a mao, com o
mesmo resultado, sem perguntar. O que exige escolha humana ele **nao** faz e
nao pode fingir que faz.

| Repara sozinho | Nao toca, e diz por quê |
|---|---|
| Cache e artefato de build | `cmd_remover_elevado.txt` — preso pelo Controlador de Arquivos |
| `__pycache__` e `.pyc` | `cmd.exe` na raiz — precisa de shell elevado |
| `.pytest_cache` | `Temp\\cargo-target` sem `--build`: rebuild custa 3 min |
| Resumo do preflight depois | Qualquer coisa que envolva dinheiro, chave ou conta |

Regra que NAO muda
------------------
Nada aqui habilita saque, transferencia ou ordem. Ver `AGENTS.md`.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DISCO_MINIMO_GB = 4.0


@dataclass
class Acao:
    nome: str
    feito: bool
    detalhe: str


def _tamanho(p: Path) -> int:
    """Bytes do alvo. Devolve 0 se nao existir ou nao der para ler."""
    if not p.exists():
        return 0
    if p.is_file():
        try:
            return p.stat().st_size
        except OSError:
            return 0
    total = 0
    for item in p.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _remover(p: Path) -> tuple[bool, str]:
    """Remove um alvo, devolvendo o motivo quando falha.

    ACL corrompida e o caso real desta maquina: `Remove-Item` falha com
    "acesso negado" e o lote inteiro pararia. Por isso cada remocao e
    independente — a que falha vira aviso, e as outras continuam.
    """
    if not p.exists():
        return True, "nao existia"
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return True, "removido"
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


def limpar_cache_build(aplicar: bool) -> list[Acao]:
    """Artefatos regeneraveis por comando, nunca codigo nem dado do usuario.

    A lista e a mesma allowlist de `scripts/limpeza_segura.ps1`. O motivo de
    os dois existirem: o PowerShell e o que roda na limpeza manual, e este
    e o que roda dentro do app. Ter as duas listas em um lugar so e o que
    evita o esquecimento.
    """
    alvos = [
        ROOT / ".pytest_cache",
        ROOT / "frontend" / "dist",
        ROOT / "frontend" / "src-tauri" / "NONE",
    ]
    acoes: list[Acao] = []
    for alvo in alvos:
        if not alvo.exists():
            continue
        tamanho = _tamanho(alvo)
        if not aplicar:
            acoes.append(Acao(f"cache: {alvo.name}", False, f"existe, {_mb(tamanho)} (use --apply)"))
            continue
        ok, detalhe = _remover(alvo)
        acoes.append(Acao(f"cache: {alvo.name}", ok, detalhe))
    return acoes


def limpar_pycache(aplicar: bool) -> list[Acao]:
    """`__pycache__` e `.pyc`: o Python recria sozinho na proxima importacao."""
    if not aplicar:
        return []
    total, falhas = 0, 0
    for pasta in (ROOT / "app", ROOT / "backend", ROOT / "scripts", ROOT / "tests"):
        if not pasta.exists():
            continue
        for cache in pasta.rglob("__pycache__"):
            ok, _ = _remover(cache)
            total += 1
            if not ok:
                falhas += 1
    if not total:
        return []
    detalhe = f"{total} pasta(s)"
    if falhas:
        detalhe += f" · {falhas} sem permissao"
    return [Acao("cache: __pycache__", falhas < total, detalhe)]


def disco() -> tuple[str, str]:
    livre = shutil.disk_usage(ROOT).free / (1024 ** 3)
    if livre < DISCO_MINIMO_GB:
        estado = "CRITICO"
    elif livre < DISCO_MINIMO_GB * 2:
        estado = "ATENCAO"
    else:
        estado = "OK"
    return estado, f"{livre:.2f} GB livres"


def rodar_preflight() -> Acao:
    """Roda o preflight e traduz o codigo de saida em frase.

    Nao e um reparo: e o diagnostico de verdade, que o dono precisa ver antes
    de operar. Roda depois das limpezas para que o resultado reflita o estado
    ja corrigido.
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "preflight.py")],
            capture_output=True, text=True, timeout=180, cwd=str(ROOT),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Acao("preflight", False, f"nao rodou: {type(exc).__name__}")
    if proc.returncode == 0:
        return Acao("preflight", True, "0 bloqueantes")
    linhas = [l.strip() for l in (proc.stdout or "").splitlines() if l.strip()]
    return Acao("preflight", False, linhas[-1] if linhas else "falhou sem resumo")



def main() -> int:
    ap = argparse.ArgumentParser(description="Repara o que e seguro reparar e diz o que nao e.")
    ap.add_argument("--apply", action="store_true",
                    help="Executa as remocoes. Sem esta flag nada e apagado.")
    args = ap.parse_args()

    print("=" * 70)
    print("XAU AI PRO - AUTO-REPARO")
    print("=" * 70)
    if not args.apply:
        print("Modo: DRY-RUN. Nada sera removido. Use --apply para corrigir.\n")

    antes_estado, antes_texto = disco()
    print(f"disco antes: {antes_texto}  [{antes_estado}]\n")

    acoes: list[Acao] = []
    acoes.extend(limpar_cache_build(args.apply))
    acoes.extend(limpar_pycache(args.apply))

    if not acoes:
        print("nenhum cache conhecido para limpar.")

    print()
    for acao in acoes:
        marca = "ok  " if acao.feito else "aviso"
        print(f"[{marca}] {acao.nome}: {acao.detalhe}")

    acoes.append(rodar_preflight())
    marca = "ok  " if acoes[-1].feito else "aviso"
    print(f"[{marca}] {acoes[-1].nome}: {acoes[-1].detalhe}")

    depois_estado, depois_texto = disco()
    print(f"\ndisco depois: {depois_texto}  [{depois_estado}]")

    print("\n" + "-" * 70)
    print("NAO REPARADO (exige decisao ou privilegio humano)")
    print("-" * 70)
    print("  cmd_remover_elevado.txt na raiz - o Controlador de Arquivos segura")
    print("    o binario e recusa a delecao. O rename resolve o nome; o sumicio")
    print("    precisa de um shell elevado, uma vez.")
    print("  cmd.exe na raiz - mesma classe de problema; nao ha reparo sem admin.")
    print("  Temp\\cargo-target - removivel, mas o rebuild custa ~3 min e ~4 GB.")
    print("    Use: .\\scripts\\limpeza_segura.ps1 -BuildArtifacts -Apply")
    print("  Token do GitLab, chaves de exchange, conta real - sao credencial.")
    print("  Qualquer dinheiro real - regra do AGENTS.md, nao ha atalho.")

    falhas = [a for a in acoes if not a.feito]
    print("\n" + "=" * 70)
    if falhas:
        print(f"{len(falhas)} item(ns) continuam abertos - veja a lista acima.")
    else:
        print("Ambiente reparado.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
