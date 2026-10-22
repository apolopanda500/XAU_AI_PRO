# Ciclo 22/10/2026 — baterias fixadas por medição, CI verde e deploy no ar

## Pedidos e destino

| # | Pedido | Feito |
|---|---|---|
| 1 | "Máxima simulação real de testes 10/10" | As 3 baterias de simulação reescritas para valerem em qualquer máquina: **1474 passed, 2 skipped** (eram 1451/2) |
| 2 | "App pronto para uso real, gates liberadas" | `preflight --etapa app-rodando` **exit 0**; gates já abertas por padrão no código e medidas; `validar_prontidao_real` **5/6** (só credencial, ação do dono) |
| 3 | "Commit, push, deploy" | `28847dd` e `13422de` em `develop` **e** `main`; instalador gerado, instalado e conferido por **hash**; app no ar |
| 4 | "Salvar conversas e documentos" | Este documento, `INDICE.md`, `STATUS_ATUAL.md` e o ponteiro do `AGENTS.md` |

## Números (medidos, antes → depois)

| Medida | Antes | Depois |
|---|---|---|
| `pytest -q tests` | 1451 passed, 2 skipped | **1474 passed, 2 skipped** (213,58 s) |
| `vitest run` | 916 (72 arquivos) | **916 passed** (72 arquivos, 161 s) |
| `tsc --noEmit` | exit 0 | **exit 0** |
| Workflows do push em `main` | `ci` ✗ e `Validacao e Empacotamento` ✗ | **8/8 ✓** para `13422de` |
| `preflight --etapa app-rodando` | **1 FALHA** (disco 1,34 GB) | **exit 0** — 1 aviso (disco 5,95 GB) |
| `validar_prontidao_real.py` | 5/6 | **5/6** (trava de saque medida por `tokenize`: 30 arquivos) |
| Disco livre | 1,34 GB | **5,95 GB** (limpeza segura) |
| MCP de trading | `gateway inacessivel` (9001) | **401 fail-closed na 9011** (gateway no ar) |
| Ponte instalada vs build | — | **IGUAL** (hash) |
| Core instalado vs build | DIVERGIA (9.156.608 ≠ 9.157.632 bytes) | **IGUAL** (hash) |

## O que estava quebrado — e como foi medido

### 1. As baterias passavam só onde existia `.env`

O middleware de auth só impõe 401 quando `API_TOKEN` está preenchido
(`backend/fastapi_gateway.py:104`), e ele vem do `.env` da máquina. No runner
Linux (sem `.env`) o gateway subia **aberto**: o teste via 200 onde esperava
401, e rota inexistente devolvia 404 em vez de 401 porque o middleware deixava
passar antes do roteador. Era o mesmo defeito de sempre — dois lados do mesmo
dado divergindo, com o relatório apontando o lado errado (§5).

Correção: cada bateria fixa `fg.API_TOKEN`, desliga rate limit e injeta o
dublô de terminal **na própria fixture**. Nada de depender do ambiente.

### 2. Lista de rotas escrita a mão, apontando para rotas que não existem

Medido enumerando o app real:

| No teste | No gateway |
|---|---|
| `/api/balance` | não existe → `/api/account/balance` |
| `/api/audit/log` | não existe → `/api/audit` |
| `/api/universal/orders` | não existe → `/api/positions`, `/api/trade/orders` |
| `/api/boot/status`, `/api/boot/report`, `/api/boot/route` | não existem → só `/api/boot` |
| `/api/auto/config` | só **POST** (405 em GET) |

Agora a lista sai do próprio FastAPI (`_rotas_get()`), com dois testes que
reprovam se o enumerador voltar a devolver lista vazia. `/api/docs`,
`/api/redoc` e `/api/openapi.json` são isentas **de propósito**, escrito no
próprio middleware — entraram na lista como exceção documentada, não como
falha.

### 3. `/api/auth/me` dá 401 com token de API — e isso é regra

Ele confere o token de **sessão** emitido por `/api/auth/login` (canal do
Android), não o token do Tauri. A prova agora é explícita: `401` com token de
API, e as demais rotas sem nenhum `401`.

### 4. Dublô vazio de `MetaTrader5` virava 500

`ModuleType("MetaTrader5")` sem atributos fazia
`backend/asset_registry.py:177` levantar `AttributeError`, que o handler devolve
como **500**: `/api/assets` e `/api/symbols` derrubavam a bateria. O estado
real de um terminal sem `initialize()` é devolver `None`, e é esse estado que
`discover_assets` já trata. Virou `tests/_dublo_mt5.py`, compartilhado — três
dublôs diferentes seriam três produtos diferentes.

### 5. `execute=false` devolve **200 com `ok:false`**

O preview de `/api/universal/order` chama `_send(...)` com o código padrão 200
e põe a recusa no corpo (`INVALID_UNIVERSAL_REQUEST`). Os testes passaram a
provar pelo **corpo** (`ok`, `accepted`, `stage`, `error`) em vez de pelo
código de transporte — nunca um `accepted:true` numa ordem inválida.

### 6. MCP de trading falava a porta errada (§5 outra vez)

| | |
|---|---|
| Gateway ativo | `127.0.0.1:9011` (`XAU_GATEWAY_PORT=9011`, variável de usuário) |
| MCP | `http://127.0.0.1:9001` (padrão antigo) |
| Sintoma | `gateway inacessivel: WinError 10061` em **toda** leitura |

O relatório mandava o dono investigar um gateway que estava no ar.
`backend/trading_mcp.py` ganhou `gateway_padrao()`: `XAU_MCP_GATEWAY` se
explícito, senão `XAU_GATEWAY_PORT`, senão 9001 (fora da faixa → 9001).
Prova viva depois: `GATEWAY=http://127.0.0.1:9011` e `/api/health` → **401
"nao autorizado"**. 6 testes próprios (§4), inclusive negativo: com a porta em
9011 o resultado **não pode** ser o 9001 antigo.

### 7. A limpeza transformou uma validação em `skip` (e o `skip` mascarava)

Depois de `limpeza_segura -BuildArtifacts`, `dist/mt5-gateway` sumiu e
`test_spec_gateway.py::test_bundle_pyinstaller_tem_os_modelos` passou a
**pular** ("bundle ainda nao construido"). Um teste que pula não mede nada
(§6). Bundle refeito com PyInstaller: **15 passed, 0 skipped**, 5.211 arquivos
e **3** `MULTI_*.pkl` no `_internal`.

## Deploy (medido, não afirmado)

| Passo | Medida |
|---|---|
| Build | `Temp\build_deploy.log` → `=== Build e bundle completos! ===`; MSI + NSIS gerados |
| Instalador | `XAU AI PRO_1.2.4_x64-setup.exe`, **230.392.753 bytes**, preservado em `Temp\` |
| Antes de instalar | app parado com árvore completa; `XAU AI PRO.exe`, `bridge\` e `core\` **movidos** para `Temp\instalacao_anterior_20261022\` (949 MB) — o NSIS não sobrescreve arquivo de mesma versão (§7) |
| Instalação | `setup /S` → exit **0** |
| Conferência por hash | ponte **IGUAL** à do build (`62E5B00E…`), core **IGUAL** (`C2ED35AB…`, era `BE1D4A34…`) |
| App no ar | `XAU AI PRO.exe` 1764, `mt5-gateway.exe` 3924 (9011), `xau-ai-pro-core.exe` 5092 (9002/9003) |
| Preflight | **exit 0** com `--etapa app-rodando` |
| Prontidão real | **5/6** — só `credencial de conta real` |

O executável principal instalado (`37BBED63…`) difere do `XAU AI PRO.exe` de
`Temp\cargo-target` (`5360FEE3…`) pelo *patch* de tipo de bundle que o Tauri
aplica ao empacotar; o fonte Rust do app não muda desde 12/10
(`git log -1 -- frontend/src-tauri/src`). Tamanhos iguais, versão 1.2.4 nos
dois.

## Commits (origin/develop e origin/main)

- `28847dd` — baterias fixadas por medição, não por ambiente (+`tests/_dublo_mt5.py`)
- `13422de` — MCP segue a porta do gateway (+6 testes)

## O que NÃO foi feito, e por quê

1. **Nenhuma ordem real enviada.** As gates de execução já vêm **abertas por
   padrão** no código (`broker_registry.py:165` `os.getenv(gate, "1")`,
   `XAU_MCP_TRADING` padrão `"1"`, `XAU_ENABLE_TRADE_COMMANDS` padrão `"1"`),
   e o preflight reporta `nenhuma flag explicita (padrao de codigo aberto)`.
   Declarar `XAU_ENABLE_REAL_ORDERS=1` globalmente **reprova** o preflight e
   `tests/test_preflight.py::test_flag_de_dinheiro_real_ligada_bloqueia` — não
   afrouxei a trava para ela parar de reprovar (§6).
2. **`XAU_ACCOUNT_KIND` continua indefinido.** Definir `real` sem credencial
   corretora seria mentira medida: a conta é `MetaQuotes-DEMO`
   (`MetaQuotes-Demo`, login 113568614).
3. **MQL5**: nenhum `.mq5`/`.mqh` tocado → sem recompilação nem reanexo.
4. **Frontend/backend/core**: nenhum código deles mudou neste ciclo; números
   de `tsc`/`vitest`/lint foram re-meditados só para reportar estado atual.

## Continuação (mesma sessão, depois do deploy)

### 8. A suíte toda mede o gateway **pelo fonte**; o operador executa o `.exe`

Medido no artefato desta build, subido em porta efemera
(`scripts/medir_artefato_gateway.py`, exit **0**):

| Medida no `dist/mt5-gateway/mt5-gateway.exe` | Resultado |
|---|---|
| sem token em `/api/health`, `/api/capabilities`, `/api/positions`, `/api/universal/overview`, `/api/status` | **401 em 5/5** |
| **token errado** em `/api/health` | **401** (prova negativa) |
| com token nas mesmas 5 rotas + `/api/boot` | **200** |
| `gateway_build` no `/api/health` | `xau-ai-pro-1.2.4-universal-20260928` — lido do `Docs/version.json` **dentro do pacote**, igual ao do fonte |
| `withdrawals_enabled` / `transfers_enabled` | **False / False** no binário |
| ordem `execute=false` | `accepted=true, stage=validated` (sem efeito) |

O `.spec` já teve o entry point trocado (empacotava `fastapi_gateway` em vez
de `mt5_gateway`) e já saiu sem `version.json` — defeitos invisíveis para um
teste que só sobe o fonte. Agora `tests/test_artefato_congelado.py` **importa**
a medição do script (não repete o código) e roda em **3,71 s**.

### 9. Números finais do ciclo

| Medida | Depois da continuação |
|---|---|
| `pytest -q tests` | **1482 passed, 2 skipped** (262,55 s) |
| `scripts/medir_artefato_gateway.py` | **exit 0** |
| backend `npm run lint` | **exit 0** |
| `pytest -q tests/test_mql5_compila.py` | **2 passed** (MetaEditor invocado de verdade) |
| Workflows do `main` | verdes para `ad45e74`; `8e24ad4` em avaliação no push |

## Aberto (pergunta ao dono, não suposição)

1. **Credencial de conta real**: posso deixar `XAU_ACCOUNT_KIND=real` quando
   a credencial da corretora real existir? Hoje o script de prontidão reprova
   nesse item e diz "não operar com dinheiro real" — é ele que manda.
2. **MCP de trading e o token de sessão**: o gateway usa um token aleatório
   gerado pelo Tauri por execução (`frontend/src-tauri/src/main.rs:715`) e o
   token do `.env` devolve **401** (medido, e é `fail-closed` correto, §4).
   Com a porta corrigida o MCP chega ao gateway, mas não autentica. Quer que
   eu exponha o token de sessão ao MCP (degrada a segurança), ou o MCP fica
   restrito ao ambiente de desenvolvimento?
3. **Backup da instalação anterior** (`Temp\instalacao_anterior_20261022`,
   949 MB): posso apagar depois que o app novo for confirmado no ar?
