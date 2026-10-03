# -*- coding: utf-8 -*-
"""Reproduz e mede a queda do mt5-gateway sob rajada HTTP.

POR QUE ISTO EXISTE
===================
Na sessao de 29->30/09/2026 o `mt5-gateway` caiu duas vezes e o log continuou
dizendo "core spawnado com sucesso". A suspeita registrada foi `TIME_WAIT`. A
medida desmentiu: `TIME_WAIT` e consequencia, e a causa e o backlog de 5
conexoes do `socketserver`.

Este script e a prova, e roda em modo comparativo: sobe o gateway real, mede a
rajada com o backlog padrao da biblioteca e com o backlog corrigido, e
imprime os dois numeros lado a lado. Sem ele, a correcao do backlog seria uma
afirmacao sem prova — exatamente o que a secao 13 do
`docs/SESSAO_20260930.md` chama de "afirmacao sem verificacao e marketing".

So levanta o gateway em porta local efemera. Nao toca MT5, nao envia ordem e
nao toca em dinheiro: as rotas exercitadas sao `/api/health` (somente leitura).

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\provar_rajada.py
    XAU_PROVA_RAJADA=1000 .\\.venv\\Scripts\\python.exe scripts\\provar_rajada.py
"""
from __future__ import annotations

import http.client
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOKEN = "token-de-prova"
RAJADA = int(os.getenv("XAU_PROVA_RAJADA", "400"))
CONCORRENCIA = int(os.getenv("XAU_PROVA_CONCORRENCIA", "24"))


def _medir(backlog: int) -> dict[str, object]:
    """Sobe o gateway com um backlog e dispara a rajada."""
    from http.server import ThreadingHTTPServer

    from backend import mt5_gateway as gw

    gw.API_TOKEN = TOKEN
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), gw.Handler)
    servidor.daemon_threads = True
    servidor.request_queue_size = backlog
    porta = servidor.server_address[1]
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)

    falhas: list[str] = []
    trava = threading.Lock()
    inicio = time.time()

    def trabalhador() -> None:
        for _ in range(max(1, RAJADA // CONCORRENCIA)):
            conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
            try:
                conexao.request(
                    "GET", "/api/health",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )
                resposta = conexao.getresponse()
                corpo = resposta.read()
                if resposta.status != 200:
                    with trava:
                        falhas.append(f"HTTP {resposta.status}")
            except Exception as exc:
                with trava:
                    falhas.append(f"{type(exc).__name__}: {exc}")
            finally:
                conexao.close()

    trabalhadores = [
        threading.Thread(target=trabalhador) for _ in range(CONCORRENCIA)
    ]
    for t in trabalhadores:
        t.start()
    for t in trabalhadores:
        t.join()
    decorrido = time.time() - inicio

    # O gateway sobreviveu? E o que interessa: uma queda nao vale um throughput.
    vivo = False
    try:
        conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
        conexao.request(
            "GET", "/api/health", headers={"Authorization": f"Bearer {TOKEN}"}
        )
        vivo = conexao.getresponse().status == 200
        conexao.close()
    except Exception:
        vivo = False

    servidor.shutdown()
    servidor.server_close()
    return {
        "backlog": backlog,
        "requisicoes": RAJADA,
        "falhas": len(falhas),
        "segundos": round(decorrido, 2),
        "por_segundo": round(RAJADA / max(decorrido, 0.001), 1),
        "vivo": vivo,
        "primeira_falha": falhas[0] if falhas else "",
    }


def main() -> int:
    print(f"rajada de {RAJADA} requisicoes, {CONCORRENCIA} conexoes simultaneas\n")
    print(f"{'backlog':>8} {'falhas':>7} {'segundos':>9} {'req/s':>8} {'vivo':>6}")
    print("-" * 46)

    from backend import gateway_server

    antes = _medir(gateway_server.BACKLOG_PADRAO)
    print(f"{antes['backlog']:>8} {antes['falhas']:>7} {antes['segundos']:>9} "
          f"{antes['por_segundo']:>8} {str(antes['vivo']):>6}")

    # 5 e o padrao do `socketserver`: e o estado em que o app foi entregue.
    antes_padrao_biblioteca = _medir(5)
    print(f"{antes_padrao_biblioteca['backlog']:>8} "
          f"{antes_padrao_biblioteca['falhas']:>7} "
          f"{antes_padrao_biblioteca['segundos']:>9} "
          f"{antes_padrao_biblioteca['por_segundo']:>8} "
          f"{str(antes_padrao_biblioteca['vivo']):>6}")

    print()
    if antes["falhas"]:
        print(f"FALHA: {antes['falhas']} recusas com o backlog corrigido "
              f"({antes['primeira_falha']}).")
        return 1
    if not antes["vivo"]:
        print("FALHA: o gateway nao sobreviveu a rajada.")
        return 1
    print("OK: nenhuma conexao recusada e o gateway respondeu depois da rajada.")
    if antes_padrao_biblioteca["falhas"] == 0 and antes["falhas"] == 0:
        print()
        print("ATENCAO: os dois cenarios passaram, entao esta medicao NAO")
        print("distingue backlog 5 de backlog 128 nesta maquina. As falhas")
        print("vistas na sessao de 29->30 nao sao reproduziveis aqui com a")
        print("CPU folgada. Para testar a hypothesis do backlog de proposito,")
        print("use scripts/provar_backlog.py, que sincroniza as conexoes com")
        print("uma barreira em vez de confiar em rajada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
