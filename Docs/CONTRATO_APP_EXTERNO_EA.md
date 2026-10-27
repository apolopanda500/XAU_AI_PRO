# Contrato: app externo ↔ EA (ponte por arquivo)

MEDIDO em 26/10/2026, terminal `D0E8209F…`, MetaTrader build 6285,
EA `XAU_AI_PRO` v1.2.9. Implementação:
`Experts/XAU_AI_PRO/Integration/ExternalBridge.mqh`.
Read-only por desenho — ver seção 8.

## 1. Por que arquivo, e não rede

O EA **não abre socket**. `WebRequest` só faz requisição de saída — o EA nunca
recebe conexão. Então o único canal bidirecional disponível hoje é arquivo em
`FILE_COMMON`, que é a mesma pasta que o backend já lê para o heartbeat.

```
%APPDATA%\MetaQuotes\Terminal\Common\Files
```

Essa pasta é **comum a todos os terminais** da máquina — não é a pasta de dados
de um terminal específico.

## 2. Quem escreve o quê

| Arquivo | Quem escreve | Schema |
|---|---|---|
| `XAU_AI_PRO_heartbeat.json` | EA | `ea-heartbeat.v1` |
| `XAU_AI_PRO_command.json` | **o seu app** | `ea-command.v1` |
| `XAU_AI_PRO_command_ack.json` | EA | `ea-ack.v1` |
| `XAU_AI_PRO_bridge_state.json` | EA | estado interno (último `request_id`) |

### 2.1 Heartbeat (EA → app)

```json
{"schema":"ea-heartbeat.v1","state":"RUNNING","timestamp":"2026.10.26 22:10:05",
 "login":12345678,"server":"MetaQuotes-Demo","symbol":"XAUUSD","timeframe":15,
 "autotrading":true,"balance":1000.00,"equity":1000.00,"positions":0,"write_count":123}
```

`timestamp` é **hora do servidor**. Use exatamente esse valor no campo `ts` do
comando (ver 3.3).

### 2.2 Comando (app → EA)

```json
{
  "schema": "ea-command.v1",
  "request_id": "c8f1a2b30001",
  "token": "<valor do input ExternalBridgeToken>",
  "confirm": true,
  "ts": "2026.10.26 22:10:07",
  "action": "status"
}
```

### 2.3 Ack (EA → app)

```json
{"schema":"ea-ack.v1","request_id":"c8f1a2b30001","action":"status","ok":true,
 "result":"state=RUNNING version=1.2.9 …","version":"1.2.9","ts":"2026.10.26 22:10:08"}
```

O ack é escrito **sempre**, inclusive na recusa: `ok:false` e o motivo em
`result`. O app nunca fica no silêncio.

## 3. Regras do comando

### 3.1 `request_id` é idempotente

O EA grava o último `request_id` executado em `XAU_AI_PRO_bridge_state.json`
(sobrevive a reattach/restart). Reenviar o mesmo id **não** reexecuta. Use UUID,
nunca um contador que reinicia.

### 3.2 `confirm` precisa ser booleano `true`

`confirm: true` no JSON (sem aspas). `confirm: 1` é recusado.

### 3.3 `ts` é hora do servidor, não do seu relógio

Formato `YYYY.MM.DD HH:MM:SS`. Janela de **120 s**. O EA compara com
`TimeCurrent()` (hora do servidor da corretora), que normalmente **não** é a
hora local da máquina.

O jeito seguro: copie o campo `timestamp` do heartbeat para `ts`. Se omitir
`ts`, a janela não se aplica (a idempotência de `request_id` continua valendo).

### 3.4 `token`

O input `ExternalBridgeToken` do EA, mínimo **8 caracteres**. A comparação é
igualdade simples de texto — não é hash, não é constante no tempo. Serve para
impedir comando acidental, **não** para autenticar processo (ver seção 8).

## 4. Ações

| `action` | `ok` | `result` |
|---|---|---|
| `ping` | true | `pong` |
| `status` | true | `state=… version=… symbol=… period=… positions=… balance=… equity=… autotrading=on\|off` |
| `heartbeat` | true | `heartbeat escrito` (força um heartbeat agora) |
| `ai` | true | `total=… accuracy=… precision=… recall=… correct=… wrong=… tp=… fp=… tn=… fn=…` |

`ai` vem de `AI/AIMetrics.mqh`: accuracy / precision / recall da direção da IA,
alimentados no fechamento de cada trade (`LogAIFeedback`). Só trades em que a IA
tinha direção entram na conta; abstenção (direção 0) fica fora.

## 5. Motivos de recusa

- `recusado: token invalido`
- `recusado: confirm ausente`
- `recusado: ts invalido (esperado "YYYY.MM.DD HH:MM:SS" na hora do servidor)`
- `recusado: comando velho (fora da janela de 120 s)`
- `recusado: acao desconhecida`

## 6. Como ligar no EA

Inputs (aba de parâmetros do EA):

```
EnableExternalBridge = true
ExternalBridgeToken  = "<8+ caracteres>"
```

A ponte nasce **fechada** e exige **duas** condições para abrir: chave ligada e
token com 8+ caracteres. É proposital — arquivo em `Common\Files` não identifica
quem escreveu.

Com a ponte desligada o custo é duas comparações por tick, sem acesso a disco.

Depois de mudar input: **recompilar e reanexar** o EA ao gráfico. Compilar não
reanexa.

## 7. Quando o EA lê o comando

- `OnTick` — a cada tick.
- `OnTimer` — a cada 30 s. Existe justamente para o app não ficar sem resposta
  com mercado fechado ou símbolo parado.
- Throttle interno de 1 s: chamar nos dois lugares não duplica leitura de disco.

O EA lê o arquivo inteiro por poll. Não há evento: a latência esperada é de até
1 s com tick, até 30 s sem tick.

## 8. O que esta ponte NÃO faz: mandar ordem

**Deliberado e permanente enquanto o canal não for autenticado.**

Arquivo em `Common\Files` não tem autenticação de processo — qualquer coisa
rodando na máquina do operador escreve ali. Um token dentro do próprio arquivo
não resolve: quem escreve o arquivo também lê o token.

Caminho correto para ordem já existe no projeto e tem as travas: gateway HTTP na
porta 9001 (`backend/mt5_gateway.py`), que exige `confirm=true`, `request_id`
idempotente e passa por `risk_gate`, `intent_log` e `audit_log`.

**Regra de arquitetura do app:** estado e leitura → arquivo (esta ponte).
Ordem → gateway HTTP. Não misture os dois.

## 9. Exemplo em Python

```python
import json
import os
import time
import uuid
from pathlib import Path

COMMON = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "Common" / "Files"
CMD = COMMON / "XAU_AI_PRO_command.json"
ACK = COMMON / "XAU_AI_PRO_command_ack.json"
HB = COMMON / "XAU_AI_PRO_heartbeat.json"


def heartbeat() -> dict:
    return json.loads(HB.read_text(encoding="utf-8"))


def send(action: str, token: str, timeout: float = 5.0) -> dict:
    hb = heartbeat()                 # ts na hora do SERVIDOR
    rid = uuid.uuid4().hex
    payload = {
        "schema": "ea-command.v1",
        "request_id": rid,
        "token": token,
        "confirm": True,
        "ts": hb["timestamp"],
        "action": action,
    }

    ACK.unlink(missing_ok=True)      # nao confundir com ack anterior
    tmp = CMD.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, CMD)             # escrita atomica: o EA nunca le metade

    deadline = time.time() + timeout
    while time.time() < deadline:
        if ACK.exists():
            ack = json.loads(ACK.read_text(encoding="utf-8"))
            if ack.get("request_id") == rid:
                return ack
        time.sleep(0.2)

    raise TimeoutError("EA nao respondeu: ponte desligada ou EA sem tick")
```

Duas armadilhas que o exemplo já evita:

1. **Escrita parcial.** `write_text` direto no arquivo de comando pode ser lido
   pelo EA na metade. Escreva em `.tmp` e `os.replace` (atômico).
2. **Ack de comando anterior.** Apague o ack antes de enviar e confira o
   `request_id` — senão você lê a resposta da pergunta anterior.

## 10. Checklist de integração

1. Ler `XAU_AI_PRO_heartbeat.json`. Existe? `timestamp` recente? Se o arquivo não
   existe, o EA não está rodando naquele terminal.
2. Ligar `EnableExternalBridge` + `ExternalBridgeToken`, recompilar, reanexar.
3. `send("ping", token)` → esperar `ok:true, result:"pong"`.
4. `send("status", token)` → conferir `symbol`, `period` e `autotrading`.
5. `send("ai", token)` → métricas de direção da IA.
6. Só então montar a tela em cima desses campos.

## 11. Limitações conhecidas

- **Sem evento, só poll.** Latência de até 1 s (com tick) ou 30 s (sem tick).
- **Sem autenticação de processo.** Qualquer processo local pode escrever o
  comando. Por isso só leitura.
- **Um comando por vez.** Um arquivo, um `request_id`. Enviar dois comandos
  antes do primeiro ack faz o segundo sobrescrever o primeiro.
- **Sem mtime.** O EA não usa a data do arquivo: se um comando novo reutilizar
  um `request_id` antigo, é recusado como duplicado.
- **`status` mostra o símbolo do gráfico onde o EA está anexado**, não um símbolo
  escolhido pelo app.
- **Arquivo órfão na pasta Common.** Existe
  `XAU_AI_PRO_ea_command_result.json` (58 bytes, 15/09/2026) com
  `{"command":"","status":"error","detail":"unknown_command"}`. Não é escrito nem
  lido por nenhum `.mq5`/`.mqh` do EA nem por nenhum `.py` do backend — é resto
  de protótipo. **Não use esse nome**: o contrato vigente é
  `XAU_AI_PRO_command_ack.json`.

## 12. Provas medidas (26/10/2026)

Compilação do projeto (`XAU_AI_PRO.mqproj`, MetaEditor build 6285):
**0 errors, 0 warnings**. Artefato `XAU_AI_PRO.ex5` com 452.686 bytes.

Execução real em backtest isolado (`XAUUSD` M15, 20-22/10/2026, depósito 1000,
`AutoTrade=false`), com `EnableExternalBridge=true` e
`ExternalBridgeToken=prova12345678`:

| Comando enviado | Ack devolvido |
|---|---|
| `ping`, token **errado** | `ok:false` — `recusado: token invalido` |
| `ping`, token certo | `ok:true` — `pong` |
| `status`, token certo | `ok:true` — `state=RUNNING version=1.2.9 symbol=XAUUSD period=15 positions=0 balance=1000.00 equity=1000.00 autotrading=on` |
| `ai`, token certo | `ok:true` — `total=0 accuracy=0.00 precision=0.00 recall=0.00 correct=0 wrong=0 tp=0 fp=0 tn=0 fn=0` |
| `ping` **sem** `confirm` | `ok:false` — `recusado: confirm ausente` |
| `action:"fechar_tudo"` | `ok:false` — `recusado: acao desconhecida` |

O último caso é a prova negativa que importa: **uma ação que mandaria ordem não
existe e é recusada pelo nome**, não executada por engano.

### Defeito encontrado e corrigido durante a própria prova

O ramo de idempotência reescrevia o ack com `"duplicado: ja processado"` no poll
seguinte, porque o arquivo de comando continua no disco. Medido: o app enviava
`ping`, recebia `pong` e, um segundo depois, lia `duplicado: ja processado` —
recusa com motivo errado, exatamente o padrão que o projeto trata como caro.
Corrigido: o ack só é reescrito quando não existe ack respondendo àquele
`request_id`. Re-medido: o `pong` permaneceu intacto após 45 s de polls
contínuos.

### Custo medido do poll

O throttle usa `TimeCurrent()`, resolvido ao segundo. Em backtest isso vira uma
leitura de disco por segundo **simulado**: num intervalo de 2 dias são 172.800
leituras e o backtest ficou ~4x mais lento. Em conta real são 1 leitura/s, o que
é barato. Com a ponte desligada não há acesso a disco.
