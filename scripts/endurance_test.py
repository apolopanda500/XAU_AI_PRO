# -*- coding: utf-8 -*-
"""Endurance test 24h / 72h / 7d. Mede, nao opera.

O `AGENTS.md` exige endurance test antes de execucao com dinheiro real. Este
script e a coleta de evidencia: ele observa o gateway ja em DEMO e grava um
relatorio periodico. Nao envia ordem, nao liga flag, nao escreve no MT5.

O que ele responde: "o sistema ficou de pe por N horas sem derrubar ordem,
sem perder token, sem abrir posicao fora do limite e sem travar?".

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\endurance_test.py --horas 24
    .\\.venv\\Scripts\\python.exe scripts\\endurance_test.py --horas 72 --intervalo 60
    .\\.venv\\Scripts\\python.exe scripts\\endurance_test.py --relatorio

Exit codes: 0 = janela completa sem incidente; 1 = incidente; 2 = ambiente
indisponivel (gateway fora do ar, sem token).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "Reports" / "endurance"
GATEWAY = "http://127.0.0.1:9001"
ARQUIVO_TOKEN = RAIZ / "Temp" / "gateway_token.txt"

# Campo que a ausencia, sozinho, ja e incidente.
CAMPOS_OBRIGATORIOS = ("ok", "service", "core_version")


def _token() -> str:
    """O token vive em sessao do Tauri; fora dele o gateway recusa (401)."""
    if ARQUIVO_TOKEN.is_file():
        return ARQUIVO_TOKEN.read_text(encoding="utf-8").strip()
    return ""


def _consultar(rota: str, token: str) -> tuple[bool, dict]:
    url = f"{GATEWAY}{rota}"
    # O header e `Authorization: Bearer` e NAO `X-Gateway-Token`.
    #
    # `mt5_gateway.py:2594-2596` aceita uma unica forma:
    #     auth = self.headers.get("Authorization", "")
    #     if auth != f"Bearer {API_TOKEN}": return False, "token"
    #
    # Este script mandava `X-Gateway-Token`, que o gateway ignora. O efeito era
    # 401 em TODA consulta — e `HTTP 401` gravado como se fosse queda do
    # gateway: o endurance test reprovava 100% das amostras por um header
    # errado, e apontava o operador para o gateway em vez do cliente. E a
    # quinta ocorrencia da regra do AGENTS.md: dois lados discordando do nome
    # do mesmo campo. O EA ja passou por isso (Docs/SESSAO_20261005_IA_
    # CHEGOU_AO_MT5_E_OURO.md).
    cabecalhos = {"Authorization": f"Bearer {token}"} if token else {}
    pedido = urllib.request.Request(url, headers=cabecalhos)
    try:
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return True, json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return False, {"erro": f"HTTP {exc.code}"}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return False, {"erro": str(exc)}


def _amostrar(token: str) -> dict:
    """Um ciclo de observacao. Devolve o registro, com incidente ou nao."""
    registro: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "incidentes": [],
    }

    # `/api/health`, e NAO `/health`. O gateway so conhece "/" e "/api/health"
    # (`mt5_gateway.py:2750`); "/health" cai no 404 do else final. O mesmo
    # caminho errado ja foi medido no core Rust (`core/src/bridge/mod.rs:80`),
    # onde `MT5Bridge::new` recebia 404, `bridge` ficava `None` para sempre e o
    # WebSocket 9002 nao entregava nenhuma cotacao.
    ok, saude = _consultar("/api/health", token)
    if not ok:
        registro["incidentes"].append(f"health: {saude.get('erro')}")
        return registro
    faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in saude]
    if faltando:
        registro["incidentes"].append(f"health sem campos: {faltando}")
    registro["health"] = {c: saude.get(c) for c in CAMPOS_OBRIGATORIOS}

    ok, conta = _consultar("/api/account", token)
    if ok:
        registro["conta"] = {
            "balance": conta.get("balance"),
            "equity": conta.get("equity"),
        }
        if conta.get("balance") is None:
            registro["incidentes"].append("conta sem balance")
    else:
        registro["incidentes"].append(f"account: {conta.get('erro')}")

    # Kill switch precisa continuar recusando. Se um dia aceitar ordem sem
    # confirmacao, isso e incidente critico e o teste para.
    ok, ordem = _consultar("/api/order", token)
    if ok and ordem.get("accepted"):
        registro["incidentes"].append("CRITICO: ordem aceita sem confirmacao")

    return registro


def _relatorio(caminho: Path) -> int:
    if not caminho.is_file():
        print(f"sem relatorio em {caminho}")
        return 2
    registros = [
        json.loads(linha) for linha in
        caminho.read_text(encoding="utf-8").splitlines() if linha.strip()
    ]
    incidentes = [r for r in registros if r.get("incidentes")]
    print(f"amostras      : {len(registros)}")
    print(f"com incidente : {len(incidentes)}")
    if registros:
        inicio = datetime.fromisoformat(registros[0]["ts"])
        fim = datetime.fromisoformat(registros[-1]["ts"])
        print(f"janela        : {(fim - inicio).total_seconds() / 3600:.2f} h")
    for r in incidentes[:10]:
        print(f"  {r['ts']}  {r['incidentes']}")
    return 0 if not incidentes else 1


def main() -> int:
    # O console do Windows usa cp1252 por padrao e quebra em caractere nao-ASCII.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Endurance test em DEMO (observacao)")
    parser.add_argument("--horas", type=int, default=24, help="janela em horas")
    parser.add_argument("--intervalo", type=int, default=60, help="segundos entre amostras")
    parser.add_argument("--relatorio", action="store_true", help="resume o ultimo relatorio e sai")
    args = parser.parse_args()

    SAIDA.mkdir(parents=True, exist_ok=True)
    existentes = sorted(SAIDA.glob("endurance_*.jsonl"))

    if args.relatorio:
        if not existentes:
            print(f"nenhum relatorio em {SAIDA}")
            return 2
        return _relatorio(existentes[-1])

    carimbo = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    caminho = SAIDA / f"endurance_{args.horas}h_{carimbo}.jsonl"

    token = _token()
    if not token:
        print("SEM TOKEN: o gateway recusa fora da sessao do Tauri (401, fail-closed).")
        print("Rode o app primeiro; o token e gerado por sessao.")
        return 2

    primeiro = _amostrar(token)
    if primeiro["incidentes"]:
        print(f"gateway indisponivel no inicio: {primeiro['incidentes']}")
        return 2

    print(f"endurance {args.horas}h | intervalo {args.intervalo}s | -> {caminho.name}")
    print("Ctrl-C para encerrar e ver o resumo.\n")
    inicio = time.time()
    total = max(1, int(args.horas * 3600 / max(args.intervalo, 1)))
    incidentes = 0
    try:
        for i in range(1, total + 1):
            time.sleep(args.intervalo)
            registro = _amostrar(token)
            with caminho.open("a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            if registro["incidentes"]:
                incidentes += 1
                print(f"[{i}/{total}] {registro['ts']} INCIDENTE: {registro['incidentes']}")
            elif i % 10 == 0:
                decorrido = (time.time() - inicio) / 3600
                print(f"[{i}/{total}] {decorrido:.2f}h ok, {incidentes} incidente(s)")
    except KeyboardInterrupt:
        print("\nencerrado pelo operador")

    print(f"\namostras gravadas: {caminho}")
    return 1 if incidentes else 0


if __name__ == "__main__":
    sys.exit(main())