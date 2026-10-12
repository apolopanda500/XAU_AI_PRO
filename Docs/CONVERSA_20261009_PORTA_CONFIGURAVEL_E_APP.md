# Conversa 09/10/2026 — porta configurável do gateway (opção B) e estado do build

> Documento de trabalho. Sem data e sem hora de propósito: as regras valem para
> sempre, os números não. Se um número aqui divergir do que o comando medir,
> **o comando vence**; corrija o número.

Complementa `SESSAO_20261009_RISCO_DINHEIRO_ESCADA_E_CONTA_ZERO.md`, que cobre a
parte de risco do EA. Aqui está a parte do **app**.

---

## 1. As decisões do dono, nesta ordem

| # | pergunta | resposta | efeito |
|---|---|---|---|
| 1 | as operações que zeraram a conta foram tuas? | **"foi quem assumiu"** | encerrado, sem investigação adicional |
| 2 | porta: desligar o MCP do MT5 ou tornar configurável? | **(b) tornar configurável** | trabalho abaixo |
| 3 | a escada de lotes 0,2–0,5 | **"conta suporta"** | fica o que a conta suporta: 0,01 a 0,05 |
| 4 | sem stop a partir de qual lote? | **0,4** | implementado com esse número, não dispara hoje |

---

## 2. O defeito do app: MT5 e gateway na mesma porta

### 2.1 O sintoma, medido como usuário normal

App instalado, aberto pelo atalho da Área de Trabalho. A janela abre e **não sobe
backend nenhum**: 9002 e 9003 ficam livres, e nenhum processo `mt5-gateway` ou
`xau-ai-pro-core` aparece.

Com `stdout` e `stderr` capturados:

```
[gateway] snapshot inicial: equity=10.75 posicoes=1 ea=alive
Traceback (most recent call last):
  File "mt5_gateway.py", line 3794, in <module>
  File "mt5_gateway.py", line 3778, in main
  File "backend\gateway_server.py", line 147, in criar_servidor
  File "backend\gateway_server.py", line 138, in __init__
  File "socketserver.py", line 456, in __init__
  File "http\server.py", line 140, in server_bind
PermissionError: [WinError 10013] Foi feita uma tentativa de acesso a um soquete
                 de uma maneira que e proibida pelas permissoes de acesso
[PYI-7844:ERROR] Failed to execute script 'mt5_gateway' due to unhandled exception!
```

### 2.2 A causa, medida

```
Get-NetTCPConnection -LocalPort 9001
  Listen  local=127.0.0.1:9001  PID=<terminal64>
```

E a configuração que provoca:

```
<terminal>\config\assistant.ini
  [MCP.MetaTrader]
  Enable=1
  Endpoint=http://127.0.0.1:9001/mcp

backend\mt5_gateway.py:55 (antes)
  PORT = 9001
```

**MT5 e gateway estavam configurados para a mesma porta.** Não é o MT5 "roubando" a
porta: os dois lados do projeto pediram 9001. Quem sobe primeiro ganha, e o app
perde sempre porque o MT5 já está aberto quando o app entra.

### 2.3 Por que (b) e não (a)

Desligar `[MCP.MetaTrader]` seria uma linha, mas resolve **este** conflito e só
ele: qualquer outrooccupied no 9001 volta a derrubar o app do mesmo jeito, e o
defeito reaparece sem ninguém lembrar por quê. O dono escolheu tornar a porta
configurável, que é a correção que sobrevive.

---

## 3. O que mudou (opção B)

### 3.1 Backend Python

| arquivo | antes | depois |
|---|---|---|
| `backend/mt5_gateway.py` | `PORT = 9001` | `PORT = _porta_gateway()`, que lê `XAU_GATEWAY_PORT` |
| `backend/mt5_gateway.py` | CORS com `9001` escrito à mão | CORS deriva de `PORT` |
| `backend/fastapi_gateway.py` | `uvicorn.run(port=9001)` | `port=_porta_gateway()` |
| `backend/copilot_data.py` | `BASE_PADRAO = "http://127.0.0.1:9001"` | deriva de `_porta_gateway()` |
| `backend/trading_mcp.py` | já lia `XAU_MCP_GATEWAY` | inalterado |

A função recusa valor inválido **em voz alta**, em vez de aceitar em silêncio:

```python
bruto = os.environ.get("XAU_GATEWAY_PORT", "").strip()
if not bruto:
    return 9001
try:
    porta = int(bruto)
except ValueError:
    print(f"[gateway] XAU_GATEWAY_PORT invalido: {bruto!r} -> usando 9001")
    return 9001
if not (1 <= porta <= 65535):
    print(f"[gateway] XAU_GATEWAY_PORT fora da faixa: {porta} -> usando 9001")
    return 9001
return porta
```

**Medido:**

```
XAU_GATEWAY_PORT=9011  ->  mt5_gateway.PORT = 9011
                           copilot_data.BASE_PADRAO = http://127.0.0.1:9011
XAU_GATEWAY_PORT=abc   ->  [gateway] XAU_GATEWAY_PORT invalido: 'abc' -> usando 9001
                           mt5_gateway.PORT = 9001
sem variável           ->  mt5_gateway.PORT = 9001
```

O CORS também precisou derivar: com a porta movida, um CORS escrito com `9001`
pararia de valer, e o sintoma seria "o navegador bloqueia" — o mesmo defeito de
nome e medida do `AGENTS.md` §5, agora do outro lado.

### 3.2 Core (Rust)

| arquivo | mudança |
|---|---|
| `core/src/bridge/mod.rs` | `MT5Bridge::default_gateway_url()` lê `XAU_GATEWAY_PORT`; `unwrap_or_else` passou a apontar para ela |
| `core/src/config.rs` | nova função `porta_de(variavel, padrao)`; WebSocket usa `XAU_WS_PORT` (9002) e HTTP usa `XAU_HTTP_PORT` (9003) |

**Validado:** `cargo fmt --all -- --check` → exit 0; `cargo check --locked` →
`Finished dev profile`, exit 0.

### 3.3 Tauri (Rust)

`frontend/src-tauri/src/main.rs` ganhou `porta_gateway()`, `porta_core()` e
`porta_ws()`, com a mesma regra de fallback, e `bridge_atual_ativo()` /
`core_atual_ativo()` passaram a usá-las. As ocorrências restantes de `9001`/`9002`/
`9003` no arquivo são comentários ou os próprios defaults das funções.

### 3.4 CSP

`frontend/src-tauri/tauri.conf.json` tem a CSP **estática**, com `9001` escrito no
`connect-src`. Ela é a que vale no build do desktop: `apply-csp.mjs` gera um
override em arquivo separado (`tauri.producao.conf.json`) e `build_app.bat` não o
usa.

Uma CSP estática não consegue acompanhar um número que muda em tempo de execução,
então o `connect-src` passou a aceitar **qualquer porta local**:

```
http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:*
```

As entradas explícitas de 9001/9002 foram mantidas ao lado, e o arquivo continua
sendo JSON válido.

### 3.5 Configuração no ambiente

Definido para o usuário, então todo lançamento pega:

```
XAU_GATEWAY_PORT = 9011
```

MEDIDO: 9011 estava livre no momento da definição.

---

## 4. O que NÃO está pronto

**O build foi interrompido pelo dono antes de terminar.** Portanto:

- O **app instalado é o build anterior** (o das 23:37), que ainda tem a porta
  fixa em 9001.
- As mudanças de backend/core/Tauri estão **no fonte, compiladas e testadas
  isoladamente**, mas **não estão empacotadas em nenhum instalador**.
- **Não reinstalei e não revalidei.** Não vou dizer que o app funciona sem ter
  rodado o ciclo de novo.

Falta refazer, nesta ordem:

```powershell
.\.venv\Scripts\python.exe scripts\preflight.py --etapa app-rodando
cmd /c "scripts\build_app.bat"
# desinstalar o antigo e instalar o novo, depois abrir pelo atalho e medir
```

E o passo de validação que importa, o mesmo que pegou este defeito:

```
esperar o gateway subir e conferir que NAO ha PermissionError no stderr
medir 9011 (gateway), XAU_HTTP_PORT (core) e XAU_WS_PORT (websocket)
conferir que o MT5 continua em 9001 sem reclamar
```

---

## 5. Estado medido agora

```
app instalado            build das 23:37 (anterior a esta mudanca)
XAU_GATEWAY_PORT         9011 (definido para o usuario)
porta 9011               livre
porta 9001               com terminal64 (MCP do MT5) — conflito conhecido
core/src                 cargo fmt 0, cargo check 0
backend                  py_compile ok
```

---

## 6. Continuação da conversa, resumida

**Dono:** quer risco em dinheiro, escada de padrões, sem stop acima de 0,4, escada de
lotes, mover TP/SL ao vivo, fechar 30%, documentação e o app 10/10.

**Medido e respondido:**

- Mover TP/SL e fechar 30% **já existiam** — `OnTick` → `ManagePositions()` →
  `TrailingStopATR` → `PositionModify`, e `PartialClose` →
  `PositionClosePartial`. Nada foi escrito para isso.
- O que estava errado era o **gatilho**, em pontos crus. Convertido.
- Escada de lotes 0,2–0,5 **impossível** nesta conta: 0,4 de ouro exige 165,91 de
  margem contra 15,48 livres. Maior lote que passa: 0,01 a 0,05.
- "Sem stop a partir de 0,4" implementado com o número do dono. **Não dispara
  hoje**, e o log `[RISCO] SEM STOP` é explícito sobre isso.
- A conta foi a zero por operações com **`magic 0`**; o EA é `magic 2026001` e
  estava travado por `Daily loss limit` desde 22:33. O dono assumiu.

**Pendências abertas, todas esperando o dono:**

1. Reanexar o EA — risco em dólares, tela `PerdaDia`/`Amplitude` e conserto do
   backup só entram no ar depois disso. `ex5` compilado às 23:03:42.
2. Refazer build, reinstalar e revalidar o app com a porta configurável (§4).
3. Commitar — 25 arquivos pendentes, nada commitado.
4. Port dos 4 arquivos MQL5 desta rodada para o repo — o dono priorizou a árvore
   real. **Consequência medida:** `tests/test_mql5_compila.py` compila o repo, então
   **não prova mais a árvore real**; só o MetaEditor manual prova.
5. Rotacionar as chaves de API do MT5 — eu as imprimi no console por engano
   (§3 da sessão anterior, erro 7).
6. Duplicados medidos: dois `Temp/monitor_conta.py` e dois `backend.trading_mcp`
   rodando ao mesmo tempo, escrevendo no mesmo `monitor_conta.jsonl`.
7. Perfil `Default` tem um gráfico em `XAUUSD`, símbolo que a XMGlobal não oferece
   nesta conta. O ouro dela é `GOLD`, no perfil `F1_SINGLE_11SYM`.
