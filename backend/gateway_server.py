# -*- coding: utf-8 -*-
"""Soquete do gateway local (porta 9001) com folga para a interface real.

POR QUE ISTE MODULO EXISTE
==========================
`ThreadingHTTPServer` puro, como o projeto usava ate 2026-09-30, vem com tres
padroes de biblioteca que sao apertados demais para um app de trading com
varias abas fazendo polling ao mesmo tempo. Nenhum deles e falha de rota, token
ou trava: sao limites do **soquete**, e nenhuma rota de ordem estava envolvida.

1. BACKLOG DE 5 (`socketserver.TCPServer.request_queue_size`).
   E o padrao da biblioteca. A fila e de `accept()`: e o numero de conexoes
   que o SO guarda esperando o servidor chegar nelas. A interface abre varias
   ao mesmo tempo — painel Robo, Analytics e SystemHealthOnly fazem polling
   juntos, e o Tauri abre uma conexao nova por health check. Se a fila encher,
   o SO **recusa a conexao** e o cliente ve `WinError 10061`: a tela diz
   "gateway indisponivel" sem que nenhuma rota tenha falhado.

   5 e um numero de servidor de arquivos. Para uma interface com abas
   concorrentes, e pequeno. 128 da folga sem custo: o limite real de memoria
   continua sendo o numero de threads vivas, nao o tamanho da fila.

   HONESTIDADE SOBRE A MEDICAO
   --------------------------
   Uma primeira medicao nesta maquina mostrou 27 recusas em 400 requisicoes
   com backlog 5 e 0 com backlog 128, e a diferenca apontava para o backlog.
   Repetida com a maquina folgada, a diferenca **desapareceu**: os dois
   cenarios deram 0 falhas. As 27 recusas eram artefacto de um `cargo check`
   rodando em paralelo, ou seja, de CPU saturada — nao do backlog.

   Entao o que fica de pe e: o backlog 5 e um padrao apertado, corrigi-lo e
   barato, e `scripts/provar_backlog.py` existe para **tentar refutar** a
   correcao quando ela for questionada. O defeito que realmente derrubou o
   app foi outro — ver `docs/SESSAO_20260930.md`, secao 11: o log dizia
   "core spawnado com sucesso" sem nunca conferir se o filho estava de pe.

2. HTTP/1.0 SEM KEEP-ALIVE (`BaseHTTPRequestHandler.protocol_version`).
   Toda resposta fecha a conexao e o socket vai para `TIME_WAIT` pelo tempo
   de 2*MSL. Todo `fetch` do webview e toda checagem de saude paga um socket
   novo. Esta maquina chegou a 318 sockets em `TIME_WAIT` so com o app aberto.
   Com HTTP/1.1 e `Content-Length` presente, o socket e reaproveitado.

3. SEM TIMEOUT NA CONEXAO. Um cliente que abre e nao manda nada segura uma
   thread do `ThreadingHTTPServer` para sempre. Precisa ser maior que o
   `XAU_TELEMETRY_INTERVAL` (60 s) do watchdog, senao o proprio coletor do
   projeto derruba a propria conexao.

O QUE ESTE MODULO NAO MUDA
==========================
Nenhuma rota, nenhum token, nenhuma trava. `withdrawals_enabled` e `transfers`
continuam `False` em todo o resto do codigo, e escolher um plano nao habilita
ordem nem saque. Aqui so troca o **soquete** em que as mesmas rotas sao
servidas.
"""
from __future__ import annotations

import os
from http.server import ThreadingHTTPServer
from typing import Any

#: Conexoes simultaneas aceitas na fila de `accept()` do sistema operacional.
#:
#: 128 cobre a rajada real da interface com folga. O valor vem do ambiente
#: para que a medicao possa ser repetida sem recompilar: quem reproduz o
#: defeito precisa poder voltar ao padrao 5 e ver a queda de novo.
BACKLOG_PADRAO = 128

#: Segundos que uma conexao ociosa pode ficar aberta antes de ser descartada.
#:
#: Precisa ser MAIOR que o `XAU_TELEMETRY_INTERVAL` (60 s) do watchdog: com um
#: timeout menor, o proprio coletor do projeto derrubaria a propria conexao a
#: cada ciclo. 180 s da folga de tres ciclos.
#:
#: Este numero foi corrigido depois de um teste acusar `30 < 60`: o
#: comentario acima ja dizia "maior que o watchdog" enquanto o valor ao lado
#: era 30. O comentario sozinho nao protege ninguem — e por isso que
#: `test_timeout_maior_que_o_intervalo_do_watchdog` existe.
TIMEOUT_PADRAO = 180.0


def backlog() -> int:
    """Fila de `accept()`; 5 (o padrao da biblioteca) se nada for configurado."""
    try:
        return max(1, int(os.getenv("XAU_GATEWAY_BACKLOG", str(BACKLOG_PADRAO))))
    except ValueError:
        return BACKLOG_PADRAO


def timeout_conexao() -> float:
    """Timeout da conexao ociosa, em segundos."""
    try:
        return max(1.0, float(os.getenv("XAU_GATEWAY_TIMEOUT", str(TIMEOUT_PADRAO))))
    except ValueError:
        return TIMEOUT_PADRAO


def configurar_handler(handler: Any) -> Any:
    """Liga keep-alive e timeout no `Handler` do gateway.

    Fica em funcao — e nao no corpo do `Handler` — para que o teste possa
    montar um handler de mentira e provar que a configuracao acontece sem
    subir o gateway inteiro.

    Por que HTTP/1.1 e seguro aqui: toda resposta do gateway ja manda
    `Content-Length` (em `_send` e em `do_OPTIONS`), que e exatamente o que o
    keep-alive exige para o cliente saber onde a resposta termina. Se algum dia
    uma rota responder sem esse cabecalho, o cliente passa a esperar de um
    corpo que nunca chega — e `test_respostas_todo_tem_content_length` existe
    para impedir que isso passe em silencio.
    """
    handler.protocol_version = "HTTP/1.1"
    handler.timeout = timeout_conexao()
    return handler


class GatewayServer(ThreadingHTTPServer):
    """`ThreadingHTTPServer` com o backlog que a interface real exige.

    `allow_reuse_address` ja e `True` no `HTTPServer`, mas fica explicito
    porque e ele que permite religar a porta 9001 segundos depois de o filho
    anterior ter morrido — sem isso, o reinicio automatico falha com
    `OSError 10048` e o app fica sem gateway ate o proximo boot.
    """

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        endereco: tuple[str, int],
        handler: Any,
        fila: int | None = None,
    ) -> None:
        # `request_queue_size` e lido pelo `server_activate()` do
        # `socketserver`, que roda dentro do `super().__init__`. Por isso a
        # propriedade precisa estar posta ANTES de delegar.
        self.request_queue_size = fila if fila is not None else backlog()
        super().__init__(endereco, handler)


def criar_servidor(
    endereco: tuple[str, int],
    handler: Any,
    fila: int | None = None,
) -> GatewayServer:
    """Cria o servidor ja configurado. Ponto unico usado pelo `main()` e pelos testes."""
    return GatewayServer(endereco, configurar_handler(handler), fila)
