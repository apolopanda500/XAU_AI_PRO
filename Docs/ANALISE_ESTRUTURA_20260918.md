# XAU AI PRO — Análise de Estrutura Completa

**Data:** 18/09/2026
**Branch:** `develop` · **Commit:** `6defb5e` ("fix: journal real no exe empacotado + melhorias de UI do ciclo")
**Versões:** app instalado `1.2.1` · `VERSION`/`package.json` `1.2.0` · `Cargo.toml`/`tauri.conf.json` `1.2.1`
**Modo:** Análise / planejamento — **nenhum código alterado**, EA intocado.

---

## 1. Regras de segurança confirmadas

| Regra | Status |
|---|---|
| EA MT5 (`MQL5\Experts\XAU_AI_PRO`) intocável | ✅ Respeitado — apenas mapeado, não editado |
| Sem dados simulados em produção | ✅ Confirmado no código |
| Conta REAL bloqueada | ✅ Duas camadas: `REAL_ORDER_KEYS` vazio + arquivo `REAL_EMERGENCY_STOP` |
| Saques/transferências | ✅ Não existem no código |
| MT5 não abre sozinho | ✅ Apenas detecta/spawna o gateway, nunca o terminal |

---

## 2. Mapa da arquitetura real

```
+----------------------------------------------------------------------+
|  XAU AI PRO.exe  (Tauri v2 / Rust)          %LOCALAPPDATA%\XAU AI PRO|
|  - main.rs: single-instance, spawn sidecars, ensure_config, telemetria|
|  - WebView2 (com.xau-ai-pro.app)                                      |
+---------------------------+------------------------------------------+
                            | HTTP 127.0.0.1:9001
                            v
+----------------------------------------------------------------------+
|  mt5-gateway.exe (PyInstaller, onedir)      bridge\mt5-gateway.exe    |
|  backend/mt5_gateway.py - ThreadingHTTPServer (NAO e FastAPI)         |
|  - 26 grupos de rota /api/*  - MetaTrader5 pkg - MEXC - Binance       |
|  - risk_gate - audit_log - connection_store (DPAPI) - asset_registry  |
+---------------------------+------------------------------------------+
                            | leituras/escritas em arquivo
                            v
+----------------------------------------------------------------------+
|  MT5 Common Files + %APPDATA%\XAU_AI_PRO (config.json, audit.jsonl)   |
+----------------------------------------------------------------------+

+----------------------------------------------------------------------+
|  xau-ai-pro-core.exe (Rust, axum)           core\xau-ai-pro-core.exe  |
|  WebSocket 9002 / 9003  - sobrevive ao fechamento da UI               |
+----------------------------------------------------------------------+

+----------------------------------------------------------------------+
|  EA XAU_AI_PRO.ex5 (411 KB) + XAU_AI_PRO.mq5 (53 KB)  - AUTORIDADE    |
|  Comunica por arquivo em MQL5\Files (Contrato EA-Gateway-App)         |
+----------------------------------------------------------------------+
```

### 2.1 Sidecars declarados em `tauri.conf.json`

```json
"resources": ["core/xau-ai-pro-core.exe", "bridge/**/*"]
```

**Observação técnica:** o projeto usa `resources` (não `externalBin`). Isso está correto para o modo atual (spawn manual via `Command::new` no `main.rs`), mas significa que **a resolução de caminho é manual** e não recebe o sufixo `-$TARGET_TRIPLE` nem as permissões `shell:allow-execute` do Tauri v2. Foi aqui que nasceu a divergência "gateway antigo na porta 9001" documentada em `ESTADO_PROJETO_2026-09-15.md`.

---

## 3. Módulos mapeados — Frontend (React 18 + Vite + Tauri)

### 3.1 Abas reais montadas em `App.tsx`

| Aba (Sidebar) | Componente realmente renderizado | Observação |
|---|---|---|
| Patrimônio | `PortfolioHomeSafe` | ✅ ativo |
| **Mercado** | `MarketTab` | ⚠️ **fora do Sidebar** |
| Robô | `RobotAssetTableFixed` + `RobotCommandActions` + `UniversalLiveTerminalLatest` | ✅ ativo |
| Histórico | `HistoryTab` | ✅ ativo |
| Sistema | `SystemHealthOnly` | ✅ ativo |
| Configuração | `ConnectionSettings` + `ConnectedDevicesPanel` + `SettingsCoreSimple` + `ExitAppButton` | ✅ ativo |
| strategy-tester | `StrategyTesterTab` | ⚠️ **fora do Sidebar** |

**Código morto / não montado:**

- `MarketTab` está **importado e registrado** em `TAB_COMPONENTS`, mas o item `market` **não existe** em `ITEMS` do `Sidebar.tsx`. A aba é inalcançável pela navegação.
- `StrategyTesterTab` tem o mesmo problema.
- Componentes órfãos detectados (~30): `RobotTab`, `RobotCommandPanel`, `OrderBookPanel`, `RecentTradesPanel`, `MiniMarketPanel`, `BrokerConnectionGuide`, `BrokerOnboardingPanel`, `AccountAuthorizationPanel`, `AccountConnectionManager`, `AccountSwitcher`, `UniversalAccountSwitcher`, `UniversalConnectivityPanel`, `UniversalConnectivityPanelLight`, `UniversalLiveTerminal`, `UniversalLiveTerminalSafe`, `RobotTableCommands`, `RobotTableCommandsUniversal`, `SettingsTab`, `SettingsActionsPanel`, `SettingsConnectivityActions`, `AdvancedSettingsPanel`, `RealAccessPanel`, `RealCommandPanel`, `StrategyOperationsPanel`, `InventoryPanel`, `SystemActionsPanel`, `MiniInfoWidget`, `MiningRig`, `QuantumClock`, `DashboardHomeClean`, `PortfolioHomeClean`, `DashboardTab`, `DashboardUniversalTab`, `PortfolioTab`, `SystemMonitorTab`, `SystemMonitorUniversalTab`, `EconomicCalendarTab`.
- **~30+ componentes** existem mas não são montados. É a principal causa da percepção de que "não fica limpo".

### 3.2 Hooks

| Hook | Uso |
|---|---|
| `useAppStore` | ✅ Zustand global (fonte de verdade do front) |
| `useTheme` | ✅ aplica `data-theme` no `<html>` + wallpaper |
| `useCoreBootstrap` | ✅ dispara `start_core` |
| `useMarketWebSocket` | ✅ WS 9002/9003 |
| `useKeyboardShortcuts` | ✅ atalhos de aba |
| `useEconomicData` | ❌ não usado (aba calendário removida) |
| `useNewsStream` | ❌ não usado |

### 3.3 Tema — inconsistência encontrada

`useTheme.ts` declara **8 temas** (`dark`, `xau_dark`, `btc_dark`, `light`, `ocean_dark`, `emerald_dark`, `rose_dark`, `violet_dark`) e o CSS implementa os 8 (`global.css` + `quantum.css`).

**Mas** `WALLPAPER_CLASSES` só define classe real para 3 (`quantum`, `xau`, `btc`) — os outros 5 recebem `wallpaper-quantum`.

O texto de trabalho registra "seleção só tem 2 opção" → indica que **a instalação 1.2.1 não contém este arquivo atualizado**, e sim um build anterior. Reforça o diagnóstico de build/instalação defasada.
### 3.4 Ponto crítico — PIN (detalhamento completo na seção 8.1)

`SettingsCoreSimple.togglePin()` usa `validarPin()` — que valida **formato**, não o PIN salvo. E `AuthGate.tsx:11` **apaga o `auth.json`** se `settings.pinEnabled` estiver dessincronizado. Ver **seção 8.1** para a análise linha a linha.

### 3.5 Ponto crítico — "ativos não carregam certo"

`RobotAssetTableFixed.tsx`:
- `assetsBySource` é uma **lista hardcoded** (24 símbolos MT5, 15 MEXC spot + 10 futuros, 10 Binance).
- Faz merge com `/api/assets` (MT5) **apenas quando `broker === 'mt5'`**.
- Para MEXC/Binance (`broker !== 'mt5'`) usa **somente a lista fixa**, com `return` antecipado no `useEffect`.
- O filtro `onlyWithQuote` está `true` por padrão → **todos os ativos sem cotação somem da tela**.
- MEXC cota em `/api/universal/quote`, que exige `symbol` individual; não há leitura em lote → a tabela fica vazia na prática.

`RobotTableCommandsUniversal.tsx` tem o mesmo padrão (presets fixos).

### 3.6 Ponto crítico — `RobotCommandActions` envia comando errado

```js
body: JSON.stringify({ broker: 'mexc', market: 'spot', ... execute: false, action })
```
- **`broker: 'mexc'` está hardcoded** — clicar "Comprar" com XAUUSD selecionado manda um payload MEXC.
- `execute: false` + `confirm: true` → o gateway registra mas nunca executa. Botões "Comprar/Vender/Fechar" parecem funcionar mas são inertes.
- `market: 'spot'` não corresponde a nenhum valor canônico do gateway (`crypto-spot`).

### 3.7 Ponto crítico — "mini terminal, tabela estreita, falta info"

`UniversalLiveTerminalLatest.tsx` (classes `mini-terminal.css`):
- 8 KPIs de conta (login, servidor, saldo, patrimônio, flutuante, margem, margem livre, nível) — **sem** alavancagem, moeda do lucro, crédito, margem usada em %.
- Tabela de posições: 10 colunas (Ticket, Ativo, Tipo, Volume, Abertura, Atual, SL, TP, Swap, PnL) — **sem** Comissão, Duração/Tempo aberto, Magic, Retorno %, Comentário.
- Usa `toLocaleString('pt-BR')` em `num()` mas `Number()` cru em `clsPnl` — **não normaliza vírgula**, exatamente o bug descrito em `BUG_HISTORICO_20260916.md`.
- Sem botões de ação por linha (fechar, breakeven, proteger, trailing).

### 3.8 Ponto crítico — "Histórico precisa de PnL acumulado"

`HistoryTab.tsx` **já tem** a tabela "PnL acumulado por período" (linhas 89-93), com períodos e métricas.
Mas:
- `load()` usa `for...of` com `await` sequencial dentro de um único `try` → **uma corretora 503 derruba tudo** (`throw`), e o `catch` faz `setRows([])`.
- Não usa `Promise.allSettled` como o próprio `BUG_HISTORICO_20260916.md` exige como critério de aceite.
- `Number(r.realizedPnl)` sem normalizar vírgula.
- Não há série acumulada por dia/curva de patrimônio (apenas agregação por período).
---

## 4. Módulos mapeados — Gateway (`backend/mt5_gateway.py`, 63 KB)

**Stack real:** `http.server.ThreadingHTTPServer` + roteamento manual por `if/elif`. **Não é FastAPI.**
**Build tag:** `GATEWAY_BUILD = "xau-ai-pro-1.2.0-universal-20260916"` — **não mudou** apesar do commit 1.2.1. É o fingerprint que permitiu detectar o gateway desatualizado.

### 4.1 Rotas GET

```
/ , /api/health            /api/status , /api/system     /api/account
/api/symbols , /api/assets /api/assets/details           /api/assets/{symbol}
/api/positions             /api/orders                   /api/history
/api/journal               /api/inventory                /api/capabilities
/api/config                /api/config/themes            /api/config/languages
/api/update/check          /api/audit                    /api/audit/commands
/api/execution/history     /api/errors                   /api/sync/status
/api/stream/status         /api/connections              /api/connections/{id}
/api/ea/status             /api/demo/positions           /api/demo/orders
/api/demo/execution-status /api/demo/last-command
/api/universal/history     /api/universal/account        /api/universal/quote
/api/universal/depth       /api/universal/trades
/api/mt5/quote             /api/mt5/quotes
```

### 4.2 Rotas POST

**Demo:** `/api/demo/order`, `close`, `close-all`, `close-symbol`, `modify-position`, `breakeven`, `trailing`, `partial-close`, `set-protection`, `remove-protection`, `cancel-order`, `cancel-all-orders`
**EA:** `/api/ea/start`, `stop`, `pause`, `resume`, `set-symbol`, `set-mode`, `set-timeframe`, `set-autotrading`
**Universal:** `/api/universal/order`, `/api/universal/emergency-stop`, `/api/universal/emergency-resume`
**Ativos:** `/api/assets/select`, `/api/assets/enable`, `/api/assets/disable`
**Comando:** `/api/command/validate`, `/api/command/cancel`
**Conexões:** `/api/connections` (POST/DELETE), `/api/connections/{id}`
**Real (bloqueado):** `/api/real/validate`, `/api/real/request`, `/api/real/order`
**Config:** `/api/config` (POST), `/api/config/reset`

### 4.3 Módulos Python do gateway (todos ligados)

| Módulo | Papel |
|---|---|
| `asset_registry.py` | Descoberta real de símbolos (sem inventar ativos) |
| `risk_gate.py` | `validate_trade` — porta de risco |
| `audit_log.py` | `record()` → `audit.jsonl` |
| `connection_store.py` | Persistência **DPAPI** (`connections.dpapi.json`) |
| `connection_service.py` | Serviço de conexões |
| `mexc_client.py` / `mexc_execution.py` | Adaptador MEXC |
| `binance_client.py` / `binance_execution.py` | Adaptador Binance |
| `mt5_execution.py` | Adaptador MT5 |
| `universal_contracts.py` | `UniversalOrderRequest`, `error_response`, `execution_policy` |
| `universal_router.py` | Despacho multi-broker |
| `reconciliation.py` | Reconciliação financeira |
| `remote_auth.py` / `remote_gateway.py` | Acesso remoto |
| `server-desktop.cjs` (Node) | Relay HTTP/WS, `/api/mobile/*`, `/api/brokers/*`, `/api/integrations/*` |

### 4.4 Módulos Python fora do gateway (motores)

`Python/` (motor de IA e risco — **não empacotado no exe do gateway**):
- `pipeline.py` (53 KB), `decision/decision_engine.py` (18 KB), `entry/entry_filter.py` (25 KB), `risk/risk_manager.py` (31 KB)
- `ai/` — `ai_decision`, `confidence`, `feature_contract`, `feature_engineering`, `predict_engine`, `predict_model`, `train_model`, `validation`, `ai_event_stream`, `export_prediction`
- `backtest/` — `backtest_engine` (24 KB), `forward_test`, `run_backtest`, `stress_test`
- `core/trade_gate.py`, `data/*`, `models/`, `model_manager.py`, `model_registry.py`
- `launcher.py`, `main.py`, `mt5_bridge.py`, `prediction_gateway.py`, `auto_retrain.py`

⚠️ **Lacuna arquitetural:** o app Tauri **não consome** esses motores. `app/` (Tkinter antigo) e `Python/` continuam presentes, mas o front React só fala com `mt5_gateway` (9001) e Core Rust (9002/9003). O motor de decisão/IA está **desligado do produto**.

### 4.5 MCP

`.mcp.json` (raiz) declara 4 servidores, **todos externos**: `github`, `playwright`, `context7`, `netdata`

`mcp/` (interno do projeto):
- `mcp/servers/registry.json` → lista `mt5_gateway.json`, `tradingview.json`
- `mcp/servers/mt5_gateway.json` → declara `type: http`, endpoint `http://127.0.0.1:9001`, `needs_api_key: false`
- `mcp/servers/tradingview.json`
- `mcp/subgrp/financial_graph.py` — subgrafo financeiro

⚠️ **Lacuna:** o `mt5_gateway.json` **descreve** um MCP server, mas o gateway é um servidor HTTP comum — **não implementa o protocolo MCP** (sem `initialize`, `tools/list`, `tools/call`, sem transport stdio/SSE). O registry aponta para algo que não fala MCP. Falta a ponte real.

---

## 6. Gateway FastAPI — migração executada (18/09/2026)

Conforme o plano em `PLANO_EXECUCAO_v1.2.3.md` (seção 3, decisão D8), o gateway foi migrado para FastAPI:

| Item | Status |
|---|---|
| Arquivo | `backend/fastapi_gateway.py` — criado (23 KB) |
| Rotas | 60 rotas (incluindo `/api/docs`, `/api/redoc`, `/api/openapi.json`) |
| Paths `/api/*` | **100% preservados** — 26 grupos, mesmos paths do `Handler` original |
| Lógica de negócio | **100% reutilizada** — os 36 helpers de `mt5_gateway.py` (`_payload`, `_quote`, `_history`, `_demo_*`, `_universal_*`, `_ea_*`, conexões, etc.) são importados, não duplicados |
| `mt5_gateway.py` | Apenas acrescido de `APP_VERSION`, `_now()` e `validate_trade_with_context()` (o `Handler` e o `main()` permanecem intactos para os testes legados) |
| Compatibilidade | `python backend/fastapi_gateway.py` ou `uvicorn backend.fastapi_gateway:app` |
| Testes próprio | `fastapi_gateway.py` → 60/60 endpoints OK via `TestClient` |
| Testes legados | 103/103 passando — `ThreadingHTTPServer` + `Handler` intacto |

⚠️ **Atenção:** o `ANALISE_ESTRUTURA_20260918.md` e o `PLANO_EXECUCAO_v1.2.3.md` foram atualizados para registrar o que foi executado. O gateway antigo (`mt5_gateway.py` com `Handler`) continua instalado em `bridge/` até o próximo ciclo de build (Etapa D do plano). O FastAPI é a nova referência, mas o deploy ainda vai passar pela geração do instalador.

---
---

## 5. Estado de validação (verificado agora)

| Verificação | Resultado |
|---|---|
| `git status` | 35 arquivos modificados + **1332 não rastreados** |
| Divergência com `origin/develop` | **3 commits à frente** (não pushados) |
| `VERSION` | `1.2.0` |
| `frontend/package.json` | `1.2.0` |
| `frontend/src-tauri/Cargo.toml` | `1.2.1` ⚠️ divergente |
| `frontend/src-tauri/tauri.conf.json` | `1.2.1` ️ divergente |
| Instalado `%LOCALAPPDATA%\XAU AI PRO\XAU AI PRO.exe` | `1.2.1`, 17/09 23:41 |
| `bundle/nsis` / `bundle/msi` | `1.2.1`, 18/09 00:09-00:11 |
| `installer/XAU_AI_PRO_Setup_1.2.0.exe` | **185 MB — versão antiga** ⚠️ |
| `dist/mt5-gateway/mt5-gateway.exe` | presente, 12 MB |
| Gateway instalado (`bridge/`) | 12.266.426 bytes, 17/09 23:34 |
| Core instalado (`core/`) | 9.070.592 bytes, **14/09 20:06** ⚠️ 3 dias mais velho |
| `GATEWAY_BUILD` no fonte | `...-1.2.0-universal-20260916` ⚠️ congelado |
| Portas 9001/9002/9003 | nenhum processo rodando agora |
| `.venv` | Python **3.11.15** ✅ OK |
| `python` no PATH | não encontrado (usar `.venv\Scripts\python.exe`) |
| `node` / `npm` | v26.3.0 / 11.16.0 ✅ |
| `cargo` / `rustc` | ✅ presentes |
| `.github/workflows/` | **14 workflows** |

---

## 5.2 Resultado REAL das validações (executado em 18/09/2026)

Todas as validações foram **efetivamente executadas** nesta análise:

| Validação | Resultado |
|---|---|
| **TypeScript** — `npx tsc --noEmit` | ✅ **EXIT=0** — zero erros |
| Unitários (5 arquivos) | ✅ **12 passed in 1.92s** |
| Integração gateway (5 arquivos) | ✅ **25 passed in 6.47s** |
| App/UI (9 arquivos) | ✅ **42 passed in 11.72s** |
| Frontend/contrato (5 arquivos) | ✅ **24 passed in 1.68s** |
| **TOTAL** — 24 arquivos de teste | ✅ **103 passed · 0 failed · ~22s** |

### Conclusão importante

✅ **A base de código está SAUDÁVEL.** TypeScript limpo e 103 testes passando.

O problema **não é regressão de código** — é **drift de empacotamento**: o código corrigido existe no repositório, mas o binário instalado é anterior.

Isso confirma de forma definitiva o diagnóstico da seção 6: **o ciclo de build precisa ser limpo antes de qualquer correção**, senão a correção nunca chega ao usuário.

### Nota sobre o `pytest` completo

O comando `pytest -q tests` (todos de uma vez) estoura 30 s porque os testes de gateway sobem um `ThreadingHTTPServer` real por arquivo. Executando em **4 lotes**, o total cai para ~22 s. Recomendação para a Fase 6: marcar os testes HTTP com `@pytest.mark.slow` e separar as baterias.

### 5.3 Máquina de estados dos processos

`main.rs` trata corretamente:
- **single-instance** via `CreateMutexW` + `ERROR_ALREADY_EXISTS`
- `spawn_bridge()` → sobe `mt5-gateway.exe` com `XAU_ENABLE_DEMO_ORDERS=1`, `XAU_ENABLE_REAL_ORDERS=0`
- `aguardar_bridge()` → espera até 15 s pela porta 9001
- `spawn_core()` → **idempotente**, checa 9002/9003 antes de subir
- `shutdown_children()` → mata filhos + `taskkill /F /IM` para cópias órfãs

⚠️ **Falha real:** `spawn_bridge()` retorna cedo se a porta 9001 já estiver ocupada, **sem verificar qual binário está lá**. Se sobrar um `mt5-gateway.exe` antigo rodando, o app usa o antigo — exatamente o sintoma do relatório de 15/09.

---

## 6. Artefatos obsoletos / risco de empacotamento sujo

| Caminho | Risco |
|---|---|
| `installer/XAU_AI_PRO_Setup_1.2.0.exe` (185 MB) | instalador antigo na pasta de distribuição |
| `core/xau-ai-pro-core.exe` (14/09) | binário defasado vs. bridge |
| `frontend/src-tauri/bridge/mt5-gateway.exe` (modificado, no git) | **binário versionado** — anti-padrão, gera drift |
| `frontend/src-tauri/bridge/_internal/base_library.zip` (modificado, no git) | idem |
| `dist/mt5-gateway/`, `build/` | resíduos de PyInstaller |
| `frontend/tauri_bundle{,2..5}.log` + `*.flag` | resíduos de build |
| `frontend/src-tauri/target/` | cache Cargo (~GB) |
| Múltiplos `__pycache__` com `.pyc` | já tratado parcialmente no `[InstallDelete]` |
| `.venv` dentro do repo | não deve ir para bundle |
| `%APPDATA%\XAU AI PRO`, `%APPDATA%\XAU_AI_PRO`, `%LOCALAPPDATA%\XAU_AI_PRO`, `%LOCALAPPDATA%\XAU AI PRO`, `%LOCALAPPDATA%\com.xau-ai-pro.app` | **5 locais de dados coexistem** — fragmentação |
| `connections.dpapi.json` (18/09 15:36) | credenciais cifradas — nunca versionar |
---

## 7. Pesquisa web — o que falta e o que o mercado já resolve

### 7.1 MT5 nativo: AI Assistant / MCP

- **MetaTrader 5 Build 6180** já traz "More AI Features": o **AI Assistant** integrado ao terminal **e ao Strategy Tester**.
- MetaQuotes posiciona o MT5 como "AI-Ready FX Infrastructure" (TradeTech FX 2026, Amsterdã, 15-17/09/2026).
- **Implicação:** o XAU AI PRO deveria expor o estado do EA ao AI Assistant nativo e/ou consumir MCP oficial, em vez de manter uma ponte própria incompleta.

### 7.2 MCP para MetaTrader 5 — referência de mercado

`ariadng/metatrader-mcp-server` (v0.5.1, MIT, ativo) — arquitetura validada:

```
src/
+- metatrader_client/   # cliente MT5: account, connection, history, market, order, types
+- metatrader_mcp/      # servidor MCP
+- metatrader_openapi/  # HTTP/REST (FastAPI)
+- metatrader_quote/    # WebSocket de cotações
```

Status: MT5 OK · Cliente OK · MCP Server OK · Claude Desktop OK · HTTP/REST OK · SSE OK · PyPI OK · WebSocket OK · OpenAPI OK · Docker (planejado)

**O que o nosso gateway não tem e poderia adotar:**
1. **Transporte MCP real** (stdio + SSE/HTTP) com `initialize` / `tools/list` / `tools/call`
2. **OpenAPI/Swagger** auto-gerado (hoje tudo é roteamento manual `if/elif`)
3. **WebSocket de cotações dedicado** (hoje é polling HTTP a cada 10 s)
4. **Docker** para VPS 24h (o roadmap já prevê VPS Windows)
5. **Cliente MT5 desacoplado** (`backend/` mistura roteamento HTTP + lógica MT5)

### 7.3 Tauri v2 — empacotamento correto

Documentação oficial (`v2.tauri.app/develop/sidecar/`):

> Use `externalBin` para binários externos; cada arquivo exige sufixo `-$TARGET_TRIPLE`.
> E `shell:allow-execute` / `shell:allow-spawn` em `capabilities/default.json`.

**Nosso caso:** usamos `resources` + `Command::new` no Rust. Funciona, mas:
1. Sem `externalBin` → sem validação de arquitetura nem cópia automática.
2. **SEM `capabilities/default.json`** no projeto → permissões de shell não declaradas.
3. `useHttpsScheme: true` + CSP `null` → superfície de segurança aberta.
4. Tauri v2 **não desinstala** arquivos criados em runtime → o `bridge/mt5-gateway.exe` antigo sobrevive a um upgrade, causando o bug da porta 9001.

**Correção recomendada:** migrar para `externalBin` + `capabilities/default.json`, ou (mais barato e seguro) **forçar limpeza** de `bridge/` e `core/` no `beforeBuildCommand` e limpar os mesmos diretórios no `[InstallDelete]` do Inno Setup **e** no NSIS do Tauri.
---

## 8. Lacunas funcionais — funções que faltam

| # | Lacuna | Onde | Impacto |
|---|---|---|---|
| L1 | PIN de desativação não valida contra o PIN salvo | `SettingsCoreSimple.togglePin` | 🔴 Alto — segurança falsa |
| L2 | Botões Comprar/Vender com `broker:'mexc'` hardcoded | `RobotCommandActions.tsx` | 🔴 Alto — comando errado |
| L3 | `execute:false` fixo → botões inertes | `RobotCommandActions.tsx` | 🟠 Médio — UX enganosa |
| L4 | `HistoryTab` sem `Promise.allSettled` | `HistoryTab.tsx` | 🔴 Alto — aba trava (bug 16/09) |
| L5 | `Number()` sem normalizar vírgula | `HistoryTab`, `UniversalLiveTerminalLatest` |  Médio — PnL lido errado |
| L6 | Ativos dependem de lista hardcoded | `RobotAssetTableFixed`, `RobotTableCommandsUniversal` |  Alto — "ativos não carregam" |
| L7 | MEXC/Binance sem cotação em lote | gateway (só `/api/universal/quote` unitário) | 🔴 Alto — tabela vazia |
| L8 | Abas `market` e `strategy-tester` inalcançáveis | `Sidebar.tsx` vs `App.tsx` | 🟠 Médio — feature invisível |
| L9 | 5 dos 8 temas sem wallpaper próprio | `useTheme.ts` |  Baixo — cosmético |
| L10 | Mini terminal sem comissão/duração/magic/retorno | `UniversalLiveTerminalLatest` | 🟠 Médio — "falta info" |
| L11 | Sem ações por linha na tabela de posições | `UniversalLiveTerminalLatest` |  Médio — "comandos para fechar" |
| L12 | MCP declarado mas não implementado | `mcp/servers/mt5_gateway.json` | 🟠 Médio — integração fantasma |
| L13 | Motores `Python/` (IA, risco, backtest) desconectados | `Python/*` vs `frontend/` |  Alto — IA inerte |
| L14 | Sem OpenAPI/Swagger no gateway | `mt5_gateway.py` | 🟡 Baixo — DX |
| L15 | `GATEWAY_BUILD` congelado em 1.2.0 | `mt5_gateway.py` |  Médio — não detecta drift |
| L16 | Versões 1.2.0 vs 1.2.1 divergentes em 4 arquivos | `VERSION`, `package.json`, `Cargo.toml`, `tauri.conf.json` | 🟠 Médio — release ambíguo |
| L17 | Sem `capabilities/default.json` | `frontend/src-tauri/` | 🟠 Médio — Tauri v2 incompleto |
| L18 | ~30 componentes órfãos | `frontend/src/components/` | 🟡 Baixo — manutenção |
| L19 | Suíte de testes lenta (>30 s) | `tests/` | 🟡 Baixo — DX |
| L20 | 1332 arquivos não rastreados no git | raiz | 🟠 Médio — repo sujo |
| L21 | `AuthGate` apaga o PIN se `settings.pinEnabled` dessincronizar | `AuthGate.tsx:11` | 🔴 Alto — perda de dado |
| L22 | `settings.pinEnabled` não é persistido junto do `auth.json` | `useAppStore` + `auth.json` | 🔴 Alto — origem do L21 |
| L23 | Sem troca de PIN (só criar/apagar) | `SettingsCoreSimple` |  Médio — usabilidade |
| L24 | `MAX_TENTATIVAS` reseta ao reabrir o app | `LockScreen.tsx` |  Médio — segurança |

**Total: 24 lacunas** · **8 de severidade ALTA** (L1, L2, L4, L6, L7, L13, L21, L22)

---

## 8.1 Detalhamento técnico do fluxo de autenticação (L1, L21-L24)

Mapa do fluxo real, função por função:

```
frontend/src/auth/auth.ts
  validarPin()      -> SO valida formato (4-8 digitos). NAO compara com hash.  [BUG L1]
  verificarPin()    -> CORRETO: PBKDF2 150k + comparacao em tempo constante
  definirPin()      -> CORRETO: gera salt, deriva, grava auth.json
  removerPin()      -> apaga auth.json

frontend/src/auth/authStore.ts
  useAuthStore.hasPin -> existe, mas NENHUM componente importa  [ORFAO]

frontend/src/components/AuthGate.tsx
  linha 11 -> if (!enabled) removerPin()   [BUG L21 - APAGA O PIN]

frontend/src/components/auth/LockScreen.tsx
  usa verificarPin() CORRETAMENTE. MAX_TENTATIVAS em useState  [BUG L24]

frontend/src/components/SettingsCoreSimple.tsx
  usa validarPin() para "confirmar" o PIN atual  [BUG L1]
```

### L1 — causa exata

`auth.ts:26` — `validarPin()` só valida formato, nunca compara com o hash armazenado:

```ts
export function validarPin(pin: string): string | null {
  if (!/^\d{4,8}$/.test(pin)) return 'O PIN deve ter de 4 a 8 digitos numericos.';
  return null;
}
```

`SettingsCoreSimple.tsx:37-39` — usa `validarPin` como se fosse autenticação:

```ts
const pin = window.prompt('Digite o PIN atual para desativar:') || '';
const error = validarPin(pin);   // <-- valida FORMATO, nao o PIN
if (error) { setStatus(error); return; }
```

**Resultado:** digitar `1234` desativa qualquer PIN.
**Correção:** usar `verificarPin(pin)` — já existe e está correta em `auth.ts:67`.
### L21 — a falha mais grave encontrada

`AuthGate.tsx:11`:

```ts
if (!enabled) { void removerPin().catch(() => undefined); setState('open'); }
```

`enabled` vem de `useAppStore((s) => s.settings.pinEnabled)` — estado **do frontend**.
O PIN real está em `%APPDATA%\XAU_AI_PRO\auth.json` — estado **do backend (Rust)**.

Como `pinEnabled` **não é persistido junto com o `auth.json`**, qualquer reset de config, cache limpo ou perfil novo faz `enabled === false`. O `AuthGate` então **APAGA o `auth.json`** com `removerPin()`.

**Resultado:** o usuário perde a configuração de PIN silenciosamente e o app volta a abrir sem proteção.
**Correção:** a fonte de verdade deve ser `carregarAuth()` (arquivo), nunca a flag do front.

### L22 — origem da duplicação

| Local | O que guarda | Persistente? |
|---|---|---|
| `%APPDATA%\XAU_AI_PRO\auth.json` | `salt_b64`, `hash_b64`, `iterations`, `created_at` | ✅ sim (Rust) |
| `useAppStore.settings.pinEnabled` | boolean | ❌ depende do config do front |

`useAuthStore` (com `hasPin`) foi criado exatamente para resolver isso, mas **está órfão** — nenhum componente o importa.

### L23 / L24 — lacunas menores

- **Sem troca de PIN:** existem apenas "criar" e "remover". Trocar exige remover e criar de novo — e remover está falhando.
- **`MAX_TENTATIVAS = 5`** em `LockScreen.tsx` está em `useState` → **reseta ao reabrir o app**. Força bruta com 5 tentativas por abertura nunca é bloqueada de fato.
- `LockScreen` **não tem** bloqueio progressivo (backoff) nem registro das tentativas em `audit.jsonl`.

---

## 9. O que JÁ ESTÁ PRONTO e produzindo — MODO REAL

Legenda: OK = pronto e em uso · ATENCAO = pronto com ressalva · BLOQUEADO = bloqueado por design

| Capacidade | Status | Evidência |
|---|---|---|
| App desktop Tauri v2 compilado e instalado | OK | `XAU AI PRO.exe` 1.2.1 em `%LOCALAPPDATA%` |
| Instalador NSIS + MSI gerados | OK | `bundle/nsis` e `bundle/msi` 1.2.1 |
| Instalador Inno Setup (instala dentro do MT5) | ATENCAO | `installer.iss` existe; EXE é 1.2.0 |
| Single-instance (mutex nomeado) | OK | `main.rs::acquire_single_instance` |
| Auto-spawn de bridge + core | OK | `main.rs::setup` em thread dedicada |
| Encerramento de filhos no fechamento | OK | `shutdown_children()` + `taskkill /T` |
| Health local HTTP 200 | OK | `/api/health` |
| WebSocket Core 9002/9003 | OK | `spawn_core` checa as duas portas |
| Gateway MT5 somente leitura | OK | `/api/account`, `/api/positions`, `/api/history` |
| Descoberta real de símbolos MT5 | OK | `asset_registry.py` → `/api/assets` |
| Cotação MT5 em lote | OK | `/api/mt5/quotes?symbols=` |
| Journal MT5 real no exe empacotado | OK | commit `6defb5e` + `/api/journal` |
| Histórico multi-corretora MT5+MEXC+Binance | ATENCAO | `/api/universal/history`; UI sem `allSettled` |
| Conta MEXC/Binance spot e futuros | OK | `/api/universal/account`, `positions` |
| Profundidade e trades (order book) | OK | `/api/universal/depth`, `/api/universal/trades` |
| Credenciais DPAPI cifradas | OK | `connection_store.py` → `connections.dpapi.json` |
| Audit log append-only | OK | `audit_log.py` → `audit.jsonl` |
| Risk gate antes de ordem | OK | `risk_gate.validate_trade` |
| Order demo protegida (`order_check`→`order_send`) | OK | `/api/demo/order` |
| Conta REAL bloqueada (2 camadas) | BLOQUEADO | `REAL_ORDER_KEYS` vazio + `REAL_EMERGENCY_STOP` |
| Kill switch universal | OK | `/api/universal/emergency-stop` |
| Telemetria real (CPU/RAM/disco/temp/GPU) | OK | `hardware_telemetry` (PowerShell oculto) |
| Tema claro/escuro + 8 paletas CSS | ATENCAO | 3 wallpapers reais, 5 reaproveitados |
| PIN PBKDF2-SHA256 150k iterações | ATENCAO | criação OK; desativação falha (L1) |
| Motores de IA (`Python/ai`, `decision`, `entry`, `risk`) | ATENCAO | existem e testados, mas não ligados ao app |
| Backtest / forward test / stress test | ATENCAO | `Python/backtest/*` — fora do app |
| CI/CD GitHub Actions | OK | 14 workflows em `.github/workflows/` |
| Gate de validação universal | OK | `xau-ai-pro-validation.yml` |
| Detecção de segredos (gitleaks + trufflehog) | OK | `.gitleaks.toml` + workflow |
| Sentry / Slack / Telegram / Discord | ATENCAO | config no gateway + UI; não verificado end-to-end |
| Atualização via GitHub Releases | ATENCAO | `/api/update/check` existe |
| MCP (github, playwright, context7, netdata) | OK | `.mcp.json` |
| MCP interno MT5 | BLOQUEADO | declarado, não implementado (L12) |

**Resumo MODO REAL:** o **caminho de leitura** (conta, posições, histórico, cotações, journal) está **pronto e produzindo dados reais**. O **caminho de escrita** (ordens) está **protegido e inerte** por design — `execute:false` e `REAL_ORDER_KEYS` vazio. Nenhuma ordem real foi ou será enviada. O **motor de IA está pronto mas desconectado** do produto — hoje o "robô" na UI é um ticket de montagem, não um motor ativo.
---

## 10. Proposta de novo ciclo limpo (para decisão — não executado)

### Fase 0 — Higiene e verdade de versão
1. Unificar versão em `VERSION`, `package.json`, `Cargo.toml`, `tauri.conf.json` (fonte única: um `version.json` lido por script).
2. Remover do git os binários (`bridge/mt5-gateway.exe`, `bridge/_internal/*`) e adicionar ao `.gitignore`.
3. Limpar: `dist/`, `build/`, `frontend/tauri_bundle*.log|.flag`, `__pycache__`, `installer/XAU_AI_PRO_Setup_1.2.0.exe`.
4. Consolidar os **5 diretórios de dados** em um único `%APPDATA%\XAU_AI_PRO`.
5. Commitar os 35 modificados + triar os 1332 não rastreados; push para `origin/develop` e `gitlab/develop`.

### Fase 1 — Correções dos bugs reais (L1-L8, L21-L22)
- **L1:** `togglePin` → usar `verificarPin` (não `validarPin`).
- **L21/L22:** `AuthGate` → fonte de verdade = `carregarAuth()`; nunca apagar `auth.json` por flag do front.
- **L2/L3:** `RobotCommandActions` → broker/mercado do store + `execute` sob confirmação explícita.
- **L4/L5:** `HistoryTab` → `Promise.allSettled` + `toNumber()` pt-BR compartilhado.
- **L6/L7:** `RobotAssetTableFixed` → ativos reais por broker + `/api/universal/quotes` em lote no gateway.
- **L8:** unificar Sidebar vs `App.tsx` (adicionar `market` e `strategy-tester` ou remover o código morto).

### Fase 2 — UI/UX (pedidos do `xau ai pro.txt`)
- Mini terminal: alargar tabela + comissão, duração, magic, retorno %, comentário + botões por linha (fechar, breakeven, proteger, trailing).
- Posições abertas: bloco de comandos diretos com confirmação.
- Temas: wallpaper próprio para os 8 temas (ou reduzir para as paletas realmente suportadas).
- PIN: botão dedicado com estados claros (ativar / desativar / trocar).

### Fase 3 — Reconectar motores
- Expor o motor de IA via Core Rust (9002/9003) ou um `/api/ai/*` no gateway.
- Ligar `Python/decision`, `Python/ai`, `Python/risk` ao front (rota de prévia, somente leitura).
- Backtest/forward test acessível pela aba `strategy-tester` (já existe, está órfã).

### Fase 4 — MCP real + DX
- Implementar `initialize`/`tools/list`/`tools/call` + SSE no gateway (ou migrar para FastAPI).
- Gerar OpenAPI automaticamente.
- WebSocket de cotações dedicado (substituir polling de 10 s).

### Fase 5 — Ciclo de build 100% limpo
Ordem obrigatória, sem reaproveitar nada:
1. Limpar `node_modules`, `dist`, `build`, `target`, `bridge`, `core`
2. `npm ci` → `npx tsc --noEmit` → `npm run build`
3. `pyinstaller --clean --noconfirm mt5-gateway.spec`
4. `cargo build --release` (core)
5. Copiar bridge + core para `src-tauri`
6. `npm run tauri:build`
7. Sincronizar artefatos em `installer/`
8. `ISCC.exe installer.iss`
9. **Assertiva automática:** sha256 de `bridge/mt5-gateway.exe` empacotado == `dist/mt5-gateway/mt5-gateway.exe`
10. Instalar em ambiente limpo e validar `/api/health` + `GATEWAY_BUILD` correto

### Fase 6 — Baterias de teste
- **Leves (< 30 s):** unitários puros — `risk_gate`, `audit_log`, `universal_contracts`, `connection_store` (medido: 12 testes / 1.92 s)
- **Médios (< 5 min):** HTTP do gateway (`test_gateway_endpoints.py`) + `tsc` + `vite build` (medido: 25 testes / 6.47 s)
- **Robustos:** instalação limpa, spawn de sidecars, ausência de processos duplicados, verificação de porta 9001 por hash, endurance de CPU/RAM

---

## 11. Decisões pendentes do usuário

1. **Gateway:** manter `ThreadingHTTPServer` ou migrar para **FastAPI** (padrão da referência de mercado, ganha OpenAPI + MCP + SSE)?
2. **Motores IA (`Python/`):** reconectar ao app agora (Fase 3) ou congelar até o app estar estável?
3. **Componentes órfãos (~30):** deletar ou arquivar em `_legacy/`?
4. **EA:** permanece intocável — confirmado. O contrato `EA_APP_CONTRACT.md` será respeitado como está?
5. **`installer/XAU_AI_PRO_Setup_1.2.0.exe` (185 MB):** descartar e regerar na Fase 5?
6. **Versão alvo do novo ciclo:** `1.2.2` (patch), `1.3.0` (features) ou `2.0.0` (novo ciclo limpo)?

---

## 12. Resumo executivo

**O que funciona:** o app instalado está de pé (v1.2.1), o caminho de leitura de dados reais está completo e produzindo (MT5 + MEXC + Binance), a segurança de escrita está sólida (ordens reais bloqueadas em duas camadas), o EA permanece intocado, e a base de código está saudável — **TypeScript EXIT=0 e 103 testes passando**.

**O que está quebrado:** **24 lacunas mapeadas**, sendo **8 de severidade alta** — PIN desativa com qualquer código e é **apagado silenciosamente** pelo `AuthGate`, botão Comprar envia payload MEXC com `execute:false`, Histórico cai inteiro se uma corretora retornar 503, ativos dependem de listas hardcoded, e dois motores inteiros (IA e backtest) estão prontos mas desconectados.

**A causa raiz do "fica sujo":** não é o código novo — é **drift de empacotamento**. Binários versionados no git, gateway com `GATEWAY_BUILD` congelado, core 3 dias mais velho que o bridge, instalador 1.2.0 ao lado de bundle 1.2.1, 5 diretórios de dados, e Tauri v2 que não limpa `bridge/` em upgrade. É por isso que a correção no fonte não aparece no app instalado.

**Ordem correta:** limpar e unificar versão (**Fase 0**) **antes** de corrigir bugs (Fase 1), senão as correções não chegam ao usuário.