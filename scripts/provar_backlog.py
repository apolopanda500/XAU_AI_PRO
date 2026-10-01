# -*- coding: utf-8 -*-
"""Experimento ISOLADO: o backlog decide se a conexao e recusada?

Separado de `provar_rajada.py` de proposito. Aqui nao ha gateway, nao ha MT5,
nao ha JSON: e um `BaseHTTPRequestHandler` minimo, e a unica variavel e o
`request_queue_size`. Isso elimina as duas fontes de ruido da medicao anterior
(rotulo de rota e estado do MT5) e responde so a pergunta: quantas conexoes
simultaneas o SO recusa antes de o servidor chegar nelas?

Cada medicao roda em um PROCESSO SEPARADO de proposito. `TIME_WAIT` dura
2*MSL (2 s a 4 min no Windows) e consome porta efemera do pool; medir dois
cenarios no mesmo processo faz o primeiro contaminar o segundo, e foi
exatamente o que aconteceu na primeira versao desta prova.
"""
from __future__ import annotations

import http.client
import multiprocessing
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Handler(BaseHTTPRequestHandler):
    """Responde o minimo possivel: uma linha e um Content-Length."""

    protocol_version = "HTTP/1.0"

    def log_message(self, *args):  # noqa: ANN002 - silencia o acesso
        pass

    def do_GET(self):  # noqa: N802
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _medir(backlog: int, conexoes: int) -> tuple[int, int, str]:
    """Roda a rajada e devolve (recusadas, total, primeira_mensagem)."""
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    servidor.daemon_threads = True
    servidor.request_queue_size = backlog
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    time.sleep(0.2)

    recusadas: list[str] = []
    trava = threading.Lock()
    barreira = threading.Barrier(conexoes)

    def trabalhador() -> None:
        # A barreira libera as conexoes NO MESMO INSTANTE. Sem ela as chegadas
        # se enfileiram e o SO nunca enche a fila de accept() — que e
        # exatamente a razao de a medicao anterior passar com backlog 5.
        barreira.wait()
        conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
        try:
            conexao.connect()  # so o TCP-connect: mede o backlog, nao o parse
            with trava:
                pass
        except Exception as exc:
            with trava:
                recusadas.append(f"{type(exc).__name__}: {exc}")
        finally:
            conexao.close()

    trabalhadores = [threading.Thread(target=trabalhador) for _ in range(conexoes)]
    for t in trabalhadores:
        t.start()
    for t in trabalhadores:
        t.join()

    servidor.shutdown()
    servidor.server_close()
    return len(recusadas), conexoes, (recusadas[0] if recusadas else "")


def _filho(backlog: int, conexoes: int, fila) -> None:
    fila.put(_medir(backlog, conexoes))


def main() -> int:
    conexoes = int(os.getenv("XAU_PROVA_CONEXOES", "64"))
    cenarios = [(5, "padrao do socketserver"),
                (128, "corrigido (backend/gateway_server.py)")]
    print(f"{conexoes} conexoes TCP simultaneas, liberadas no mesmo instante\n")
    print(f"{'backlog':>8} {'recusadas':>10}  descricao")
    print("-" * 62)

    recusa_total = 0
    for backlog, descricao in cenarios:
        fila = multiprocessing.Queue()
        processo = multiprocessing.Process(
            target=_filho, args=(backlog, conexoes, fila)
        )
        processo.start()
        recusadas, total, mensagem = fila.get()
        processo.join()
        recusa_total += recusadas
        marca = f"  <- {mensagem[:70]}" if recusadas else ""
        print(f"{backlog:>8} {recusadas:>10}  {descricao}{marca}")

    print()
    if recusa_total == 0:
        print("Sem recusa em nenhum cenario: a maquina esta folgada e o")
        print("experimento nao diz nada. Aumente XAU_PROVA_CONEXOES.")
        return 0
    if recusa_total:
        print("Leitura: o SO recusou conexao. `request_queue_size` e a fila de")
        print("accept(); com 5, o estouro aparece. E limite de SO, nao do codigo")
        print("de rota — nenhuma rota estava envolvida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
