# -*- coding: utf-8 -*-
"""Prontidao para operar com dinheiro real. Le, nao altera.

Este script nao liga nada. Ele responde a uma unica pergunta: "se eu definir
`XAU_ENABLE_REAL_ORDERS=1` agora, o que acontece?". Cada item mostra o que foi
verificado e por comando, sem confiar em documento.

O `AGENTS.md` exige, para execucao real: validacao completa em DEMO, forward
test aprovado, endurance test e autorizacao do proprietario. Este script mede
se esses pre-requisitos tem evidencia. Aprovacao final e do proprietario.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\validar_prontidao_real.py
    .\\.venv\\Scripts\\python.exe scripts\\validar_prontidao_real.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Arquivo de eventos do forward test, gravado pelo EA.
FORWARD = (
    Path(r"C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal")
    / "D0E8209F77C8CF37AD8BF550E51FF075" / "MQL5" / "Files" / "Data"
    / "forward_test_events.csv"
)


def _flag(nome: str) -> str:
    return os.environ.get(nome, "<nao definida>")


def _verificar_gate_real() -> tuple[bool, str]:
    """A flag nao pode vir de codigo compilado nem ter padrao ligado."""
    main_rs = RAIZ / "frontend" / "src-tauri" / "src" / "main.rs"
    if not main_rs.is_file():
        return False, "main.rs nao encontrado"
    # Comentarios de documentacao mencionam o valor antigo para explicar a
    # mudanca. O que conta e o codigo executavel, entao as linhas de
    # comentario sao removidas antes de procurar.
    codigo = "\n".join(
        linha for linha in main_rs.read_text(encoding="utf-8", errors="replace").splitlines()
        if not linha.lstrip().startswith("//")
    )
    if '"XAU_ENABLE_REAL_ORDERS", "1"' in codigo:
        return False, "main.rs ainda fixa XAU_ENABLE_REAL_ORDERS em 1 no codigo"
    if 'flag("XAU_ENABLE_REAL_ORDERS", "0")' not in codigo:
        return False, "main.rs nao le a flag do ambiente com padrao 0"
    return True, "flag lida do ambiente, padrao 0 (fail-closed)"


def _verificar_catalogo() -> tuple[bool, str]:
    """Todo metadado precisa da porta de qualidade do train_v2."""
    sys.path.insert(0, str(RAIZ))
    sys.path.insert(0, str(RAIZ / "Python"))
    try:
        from backend import ai_inference
    except ImportError as exc:
        return False, f"nao consegui importar ai_inference: {exc}"
    try:
        modelos = ai_inference.listar_modelos()
    except Exception as exc:  # pragma: no cover
        return False, f"erro ao listar modelos: {exc}"
    if not modelos:
        return False, "catalogo vazio"
    sem = [
        m["id"] for m in modelos
        if m.get("edge_min") is None or (not m.get("publicable") and not m.get("reason"))
    ]
    if sem:
        return False, f"metadados sem governanca: {sem}"
    publicaveis = sum(1 for m in modelos if m["publicable"])
    return True, f"{len(modelos)} modelos, {publicaveis} publicaveis, 0 sem governanca"


def _verificar_backtest() -> tuple[bool, str]:
    """O backtest precisa medir o modelo, nunca uma heuristica."""
    backtest = RAIZ / "backend" / "backtest.py"
    if not backtest.is_file():
        return False, "backtest.py nao encontrado"
    texto = backtest.read_text(encoding="utf-8", errors="replace")
    if "_decisao_do_modelo" not in texto:
        return False, "backtest.py nao chama o modelo publicado"
    for marca in ("rsi[index] < 35", "crossover_up"):
        if marca in texto:
            return False, f"heuristica {marca!r} ainda presente no backtester"
    return True, "decisao vem do .pkl publicado, heuristica removida"


def _verificar_saque() -> tuple[bool, str]:
    """A trava permanente: saque e transferencia bloqueados."""
    try:
        resultado = subprocess.run(
            ["git", "grep", "-l", "withdrawals_enabled"],
            cwd=str(RAIZ), capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"nao consegui varrer: {exc}"
    arquivos = [a for a in resultado.stdout.split() if a.endswith(".py")]
    if not arquivos:
        return False, "nenhuma ocorrencia de withdrawals_enabled — trava ausente"
    ligados = subprocess.run(
        ["git", "grep", "-n", "-E", r"withdrawals_enabled[\"']?\s*[:=]\s*True"],
        cwd=str(RAIZ), capture_output=True, text=True, timeout=60,
    )
    if ligados.stdout.strip():
        return False, f"encontrei saque habilitado: {ligados.stdout.strip()[:200]}"
    return True, f"{len(arquivos)} arquivos, nenhuma ligacao de saque"


def _verificar_forward_test() -> tuple[bool, str]:
    if not FORWARD.is_file():
        return False, f"sem registro de forward test ({FORWARD.name} nao existe)"
    try:
        linhas = len(FORWARD.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError as exc:
        return False, f"erro ao ler: {exc}"
    if linhas < 2:
        return False, "registro de forward test vazio"
    return True, (
        f"{linhas - 1} eventos registrados (a janela minima de dias ainda e "
        "decisao do proprietario)"
    )


def _verificar_conta_real() -> tuple[bool, str]:
    """Conta de teste nao pode ser aprovada para dinheiro real."""
    provedor = os.environ.get("XAU_ACCOUNT_KIND", "").strip().lower()
    if not provedor:
        return False, (
            "credencial real nao configurada. Defina XAU_ACCOUNT_KIND=real "
            "apenas com conta CORRETORA real; hoje a conta e MetaQuotes-DEMO"
        )
    if provedor == "demo":
        return False, "conta e DEMO: dinheiro real exige credencial real separada"
    return True, f"conta declarada como {provedor}"


def main() -> int:
    # O console do Windows usa cp1252 por padrao e quebra em caractere nao-ASCII.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Prontidao para mercado real (leitura)")
    parser.add_argument("--json", action="store_true", help="saida em JSON")
    args = parser.parse_args()

    checagens = [
        ("gate de dinheiro real", _verificar_gate_real),
        ("catalogo de modelos", _verificar_catalogo),
        ("backtester fiel ao modelo", _verificar_backtest),
        ("trava de saque", _verificar_saque),
        ("forward test em DEMO", _verificar_forward_test),
        ("credencial de conta real", _verificar_conta_real),
    ]

    linhas: list[str] = []
    resultados = []
    for nome, funcao in checagens:
        try:
            ok, detalhe = funcao()
        except Exception as exc:  # pragma: no cover
            ok, detalhe = False, f"erro na verificacao: {exc}"
        resultados.append({"nome": nome, "ok": ok, "detalhe": detalhe})
        marca = "OK    " if ok else "FALHA "
        linhas.append(f"[{marca}] {nome}\n          {detalhe}")

    prontidao = all(r["ok"] for r in resultados)
    linhas.append("")
    linhas.append(f"XAU_ENABLE_REAL_ORDERS no ambiente : {_flag('XAU_ENABLE_REAL_ORDERS')}")
    linhas.append(f"XAU_MCP_TRADING no ambiente        : {_flag('XAU_MCP_TRADING')}")
    linhas.append("")
    linhas.append(
        "PRONTIDAO: " + ("completa" if prontidao else "INCOMPLETA — nao operar com dinheiro real")
    )
    if not prontidao:
        linhas.append("")
        linhas.append("Este script nao altera nada. Cada item pendente esta descrito acima.")

    if args.json:
        print(json.dumps({
            "prontidao": prontidao,
            "checagens": resultados,
            "env": {n: _flag(n) for n in (
                "XAU_ENABLE_REAL_ORDERS", "XAU_MCP_TRADING", "XAU_ENABLE_DEMO_ORDERS"
            )},
        }, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("XAU AI PRO - PRONTIDAO PARA MERCADO REAL (somente leitura)")
        print("=" * 70)
        print("\n".join(linhas))
    return 0 if prontidao else 1


if __name__ == "__main__":
    sys.exit(main())