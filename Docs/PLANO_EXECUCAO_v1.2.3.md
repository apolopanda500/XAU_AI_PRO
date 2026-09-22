# XAU AI PRO — Plano de Execução Ciclo Limpo v1.2.3

**Data:** 18/09/2026
**Base:** `Docs/ANALISE_ESTRUTURA_20260918.md`
**Branch:** `develop` · Commit base `6defb5e`
**Regras:** EA intocado · conta REAL bloqueada · sem dados simulados · resposta em pt-BR

---

## 1. Visão do produto (definida pelo usuário)

> "Este app foi criado na intenção de **controlar o EA do MT5**, podendo controlar em **PC e celular**, e poder **operar com EA em qualquer corretora** usando o app fazer essa ligação."

```
                        +---------------------------+
                        |   XAU AI PRO (App)        |
                        |   PC (Tauri) + Celular    |
                        +-------------+-------------+
                                      |
                     +----------------+----------------+
                     |                                 |
              [PC: Core Rust 9002/9003]        [Celular: cliente]
                     |                                 |
                     +-------------> Gateway <---------+
                                      |
        +-----------------+-----------+-----------+-----------------+
        |                 |                       |                 |
   [MT5 + EA]      [MEXC Spot/Fut]        [Binance Spot/Fut]   [Futuras]
   autoridade       adaptador               adaptador          (Bybit/OKX...)
```

**Papel de cada camada:**
- **EA MT5** = autoridade final das operações (nunca contornado)
- **App** = cliente de controle (PC e celular)
- **Gateway** = tradutor universal: recebe comando do app, entrega no formato de cada corretora
- **Core Rust** = motor local (risco, estratégia, sessão MT5)

---

## 2. Decisões consolidadas

| # | Tema | Decisão |
|---|---|---|
| D1 | Motores IA | **Ligar todos** ao app |
| D2 | Órfãos | **Remover** os que pesam sem necessidade |
| D3 | Contratos | **Escolher os melhores/reais** para a necessidade do app |
| D4 | Instaladores antigos | **Apagar** — manter apenas atualizados |
| D5 | Versionamento | **1.2.3 → 1.2.4 → ...** (patch incremental) |
| D6 | Gateway | **Escolher o melhor** para o app |
| D7 | EA | **Intocável** — confirmado |
| D8 | Gateway | **FastAPI implementado** — `backend/fastapi_gateway.py` com 60 rotas (26 paths `/api/*` idênticos ao `Handler` original), 100% das 36 funções reutilizadas, 0 breaking change, testes verdes |
---

## 3. Recomendação técnica — Gateway (D6)

### Situação atual (mapeada)

| Camada | Tecnologia | Porta | Estado |
|---|---|---|---|
| `mt5_gateway.py` | `ThreadingHTTPServer` + `if/elif` | 9001 | 63 KB, 26 grupos de rota, funciona |
| `server-desktop.cjs` | Express + Socket.IO | — | 19 KB, relay + mobile + brokers |
| `xau-ai-pro-core.exe` | Rust + axum | 9002/9003 | funcionando, WS + HTTP do EA |

### Análise

**Manter `ThreadingHTTPServer`** — roteamento manual, sem OpenAPI, sem MCP real, difícil de testar em paralelo.

**Migrar para FastAPI** — padrão da referência de mercado (`ariadng/metatrader-mcp-server`):
- ✅ OpenAPI/Swagger automático (documentação viva)
- ✅ **MCP nativo** (transporte real: stdio + SSE) — resolve a lacuna L12
- ✅ Async real (`asyncio`) — melhor para WS de cotações e múltiplas corretoras
- ✅ Validação com Pydantic (reaproveita `universal_contracts.py`)
- ✅ Testável com `httpx`/`TestClient` (testes mais rápidos)
- ✅ Pronto para JWT (Fase 1 do `ROADMAP_MOBILE.md`)

### Veredito

> **Migrar o gateway para FastAPI mantendo as 26 rotas com os mesmos paths.**
>
> - **Zero breaking change:** os paths `/api/*` permanecem idênticos → o front não muda
> - **Ganho imediato:** OpenAPI + MCP real + async + JWT-ready (mobile)
> - **Reaproveitamento:** toda a lógica de negócio (`risk_gate`, `asset_registry`, adaptadores) é preservada — só o **roteamento** é reescrito
> - **Risco controlado:** migração feita com os 103 testes como rede de segurança

**Justificativa contra alternativas:**
- ❌ Manter como está → não resolve MCP, não documenta API, não escala para mobile
- ❌ ir só com Core Rust → axum é ótimo, mas os adaptadores (MEXC/Binance/MT5) já existem em Python; reescrever tudo em Rust é meses de trabalho

**Estratégia híbrida (recomendada):** FastAPI para o gateway (adaptadores em Python) + Core Rust permanece para risco/estratégia/sessão MT5/WS.

**Status da migração FastAPI (executado 18/09/2026):**

| Item | Resultado |
|---|---|
| Arquivo criado | `backend/fastapi_gateway.py` (23 KB) |
| Rotas criadas | 60 (incluindo `/api/docs`, `/api/redoc`, `/api/openapi.json`) |
| Paths `/api/*` preservados | 26 grupos (mesmos paths do `Handler` original) |
| Funções reutilizadas | 100% — `mt5_gateway.py` não foi alterado (só recebeu `APP_VERSION`, `_now()`, `validate_trade_with_context()`) |
| Compatibilidade | `uvicorn backend.fastapi_gateway:app` ou `python backend/fastapi_gateway.py` |
| Testes próprios | `backend/fastapi_gateway.py` → 60/60 endpoints OK (TestClient) |
| Testes legados (103) | 103/103 passando — `mt5_gateway.py` com `Handler` intacto |
| Scripts auxiliares removidos | `_test_gateway_import.py`, `_dbg.py`, `>script_version` |

### Arquivos criados/alterados nesta etapa

| Arquivo | Ação | Motivo |
|---|---|---|
| `backend/fastapi_gateway.py` | ✅ criado | Gateway FastAPI que reutiliza todos os helpers de `mt5_gateway.py` |
| `backend/mt5_gateway.py` | ✏️ acrescido | Adicionados `APP_VERSION`, `_now()`, `validate_trade_with_context()` (sem tocar no `Handler` nem no `main()`) |
| `scripts/sync_version.py` | ✅ corrigido | Bug fix: `TARGETS` agora usa tuplas de 2 elementos; detecção e patch são funções separadas |
| `Docs/PLANO_EXECUCAO_v1.2.3.md` | ✏️ atualizado | Registro da decisão D8 e status da migração |

---

## 4. Recomendação técnica — Contratos (D3)

### Contratos existentes (auditados)

| Arquivo | Tamanho | Avaliação |
|---|---|---|
| `Docs/EA_APP_CONTRACT.md` | 1.273 B | ✅ **MANTER** — autoridade do EA, 11 comandos, `COMMAND_RESULT` |
| `MQL5/Include/XAU_AI_PRO/ProtocolV1.mqh` | 4.313 B | ✅ **MANTER** — espelho MQL5 do protocolo Rust |
| `core/src/protocol/mod.rs` | 8.965 B | ✅ **MANTER** — fonte Rust do protocolo |
| `backend/universal_contracts.py` | 6.278 B | ✅ **MANTER** — `UniversalOrderRequest` com validação real |
| `Docs/ARCHITECTURE.md` | 6.167 B | ✅ **MANTER** — visão geral |
| `Docs/PLATFORM_PATTERNS.md` | 2.615 B | ✅ **MANTER** — padrões |
| `Docs/risk_control_policy.md` | 2.663 B | ✅ **MANTER** — política de risco |
| `Docs/security_policy_etapa19.md` | 1.581 B | ✅ **MANTER** — política de segurança |
| `Docs/model_governance_policy.md` | 1.703 B | ⚠️ **REVISAR** — validar se aplica aos motores IA ligados |
| `ETAPA15_BASELINE_CONTRATOS.md` | 36.230 B | ⚠️ **ARQUIVAR** — histórico, muito grande |
| `installer/ASSINATURA.md` | 4.290 B | ✅ MANTER |

### Contrato que **falta criar** (crítico para "operar em qualquer corretora")

Hoje **não existe** um contrato de adaptador de corretora. Para o app operar EA em qualquer corretora, precisamos de:

```
Docs/BROKER_ADAPTER_CONTRACT.md
```

Interface única que TODO adaptador deve implementar:

| Método | Obrigatório | Descrição |
|---|---|---|
| `capabilities()` | ✅ | mercados suportados, tipos de ordem, limites |
| `account()` | ✅ | saldo, patrimônio, margem, moeda |
| `positions()` | ✅ | posições abertas normalizadas |
| `history(days)` | ✅ | execuções normalizadas |
| `quote(symbol)` / `quotes(symbols)` | ✅ | bid/ask/spread (lote quando suportado) |
| `place_order(request)` | ✅ | usa `UniversalOrderRequest` |
| `close_position(ticket)` | ✅ | |
| `modify_position(...)` | ⚠️ | SL/TP |
| `emergency_stop()` | ✅ | kill switch |
| `health()` | ✅ | estado da conexão |

**Adaptadores a implementar:** MT5 (via EA), MEXC, Binance, + **Bybit** e **OKX** (futuro).

### Matriz de compatibilidade EA × Corretora

| Capacidade | MT5 | CEX (MEXC/Binance) |
|---|---|---|
| Lots vs. quantidade | `volume` (lots) | `quantity` (base asset) |
| Hedge/NETTING | depende do modo | sempre hedge |
| SL/TP nativos | ✅ | ✅ (futuros), ❌ (spot) |
| Ordem parcial | ✅ | ✅ |
| Trailing | ✅ nativo | ❌ simulado |

⚠️ **Inconsistência confirmada em `universal_contracts.py`:**
`Market = Literal["spot", "futures", "forex", "indices", "metals"]`
mas o front (`RobotCommandActions.tsx`) envia `market: 'crypto-spot'`.
O contrato precisa ser o **ponto único de verdade**. Correção prevista na Fase 1.
---

## 5. Plano de ligação dos Motores IA (D1)

### 5.1 Inventário completo dos motores

Descobri que **o Core Rust já tem muito mais do que o front consome**:

| Motor | Local | Estado |
|---|---|---|
| `RiskEngine` | `core/src/risk/engine.rs` + `config.rs` + `mod.rs` | ✅ pronto, ligado ao Core |
| `PaperTrader` | `core/src/strategy/paper.rs` (10 KB) | ⚠️ **roda mas nada consome** |
| `CandleStore` | `core/src/strategy/candles.rs` (5,6 KB) | ️ roda, SQLite `strategy.db` |
| `backtest` | `core/src/strategy/backtest.rs` (5,4 KB) | ⚠️ não exposto |
| `ExecutionEngine` | `core/src/execution/mod.rs` | ⚠️ não exposto |
| `connectors/` | `mt5_connector`, `binance`, `connector_trait`, `rate_limiter` | ️ **`binance.rs` já existe!** |
| `updates/` | `channel`, `rollback`, `version` | ⚠️ não exposto |
| `pipeline.py` | `Python/pipeline.py` (53 KB) | ✅ fonte real do motor IA |
| `decision_engine` | `Python/decision/` (18 KB) | ❌ **desconectado** |
| `entry_filter` | `Python/entry/` (25 KB) | ❌ **desconectado** |
| `risk_manager` | `Python/risk/` (31 KB) | ❌ **desconectado** |
| `trade_gate` | `Python/core/` (8,6 KB) | ❌ **desconectado** |
| `backtest_engine` | `Python/backtest/` (24 KB) | ❌ **desconectado** |
| `model_manager` / `model_registry` | `Python/` | ❌ desconectado |

### 5.2 Órfãos JÁ documentados no próprio código

Encontrei marcações oficiais nos arquivos Python:

```
Python/ai/predict_engine.py  -> "LEGACY/ORFAO - NAO CONECTADO (15.3). Usar pipeline.py"
Python/ai/predict_model.py   -> "LEGACY/ORFAO - NAO CONECTADO (15.3). Usar pipeline.py"
Python/ai/train_model.py     -> "LEGACY/ORFAO - NAO CONECTADO (15.3). Usar pipeline.py"
```

✅ Isso confirma a decisão D2 e define o que remover com segurança.

### 5.3 Arquitetura de ligação proposta

Fluxo único de decisão, com uma só fonte de verdade:

```
   [Market data]  (cotacoes reais MT5 + corretoras)
          |
          v
   [Core Rust: MarketDataService + CandleStore]   <- armazena candles no SQLite
          |
          v
   [Motor IA: Python/pipeline.py]                 <- a FONTE REAL de predicao
          |  predict_all() -> save_prediction_json()
          v
   [prediction.json]                              <- arquivo de contrato
          |
          v
   [Core Rust: RiskEngine + PaperTrader]          <- aplica risco e gera sinal
          |
          v
   [Gateway: /api/ai/*]                           <- expoe ao app
          |
          v
   [App: previa IA no ticket]                     <- usuario confirma manualmente
          |
          v
   [EA MT5 / adaptadores]                         <- execucao (so com confirmacao)
```

### 5.4 Endpoints novos a criar no gateway

| Endpoint | Método | Função |
|---|---|---|
| `/api/ai/status` | GET | estado do motor, modelo ativo, versão, última predição |
| `/api/ai/prediction` | GET | predição atual (`symbol`, `signal`, `score`, `buy`, `sell`) |
| `/api/ai/history` | GET | histórico de predições (`ai_history.csv`) |
| `/api/ai/confidence` | GET | confiança atual do modelo |
| `/api/ai/decision` | GET | decisão do `decision_engine` (APPROVED/BLOCKED + motivo) |
| `/api/ai/entry-filter` | GET | resultado do `entry_filter` |
| `/api/ai/risk-state` | GET | estado do `risk_manager` (`risk_state.json`) |
| `/api/ai/train` | POST | dispara treino (`train_all_models`) — protegido |
| `/api/ai/backtest` | POST | roda backtest — protegido, somente leitura de resultado |
| `/api/ai/models` | GET | modelos disponíveis (`model_registry`) |

⚠️ **Regra:** todos os endpoints de IA são **somente leitura** para o app, exceto `train`/`backtest` que exigem confirmação explícita e **não enviam ordens**.

### 5.5 Fases de ligação

| Etapa | Escopo | Resultado |
|---|---|---|
| **IA-1** | `/api/ai/status`, `/prediction`, `/history`, `/confidence` | App mostra predição real |
| **IA-2** | `/api/ai/decision`, `/entry-filter`, `/risk-state` | App mostra decisão + motivo do bloqueio |
| **IA-3** | UI: prévia de IA no ticket do Robô | Usuário vê sugestão antes de confirmar |
| **IA-4** | `/api/ai/backtest` + aba `strategy-tester` | Backtest acessível no app |
| **IA-5** | `/api/ai/train` + `/api/ai/models` | Treino e governança de modelos |
| **IA-6** | Ligar `PaperTrader` (Rust) ao pipeline | Sinais auditáveis em modo paper |
---

## 6. Remoção de órfãos (D2)

### 6.1 Frontend — código morto confirmado

| Grupo | Componentes | Ação |
|---|---|---|
| Abas duplicadas | `DashboardTab`, `DashboardUniversalTab`, `DashboardHomeClean`, `PortfolioTab`, `PortfolioHomeClean`, `SystemMonitorTab`, `SystemMonitorUniversalTab` | **REMOVER** |
| Robô duplicado | `RobotTab`, `RobotTableCommands`, `RobotTableCommandsUniversal`, `RobotCommandPanel` | **REMOVER** |
| Terminais duplicados | `UniversalLiveTerminal`, `UniversalLiveTerminalSafe` | **REMOVER** |
| Config duplicada | `SettingsTab`, `SettingsActionsPanel`, `SettingsConnectivityActions`, `AdvancedSettingsPanel` | **REMOVER** |
| Contas duplicadas | `AccountSwitcher`, `UniversalAccountSwitcher`, `AccountAuthorizationPanel`, `AccountConnectionManager` | **REMOVER** |
| Conectividade | `UniversalConnectivityPanel`, `UniversalConnectivityPanelLight` | **REMOVER** |
| Comandos reais | `RealAccessPanel`, `RealCommandPanel` | **REMOVER** (real bloqueado) |
| Outros | `OrderBookPanel`, `RecentTradesPanel`, `MiniMarketPanel`, `BrokerConnectionGuide`, `BrokerOnboardingPanel`, `StrategyOperationsPanel`, `InventoryPanel`, `MiniInfoWidget`, `MiningRig`, `QuantumClock`, `EconomicCalendarTab` | **REMOVER** |
| Hooks | `useEconomicData`, `useNewsStream` | **REMOVER** |
| Store | `useAuthStore` | **MANTER** — usado na correção L21/L22 |
| Aba | `RobotWorkspaceTab` | **MANTER** — usado em `App.tsx` |
| Aba | `AssetSelectionPanel` | **PRESERVAR** — uso futuro |

**Mantidos (efetivamente usados):** `PortfolioHomeSafe`, `RobotAssetTableFixed`, `RobotCommandActions`, `UniversalLiveTerminalLatest`, `MarketTab`, `HistoryTab`, `SystemHealthOnly`, `SettingsCoreSimple`, `ConnectionSettings`, `ConnectedDevicesPanel`, `ExitAppButton`, `AuthGate`, `LockScreen`, `Onboarding`, `Splash`, `QuantumBackground`, `Sidebar`, `TopNav`, `QuantumIcon`, `MiniPriceChart`, `QuantumChart`, `AppIdentity`, `SystemStartupSync`, `StrategyTesterTab`, `RobotWorkspaceTab`.

**Estimativa:** ~35 arquivos removidos no frontend.

### 6.2 Python — órfãos confirmados pelo próprio código

| Arquivo | Ação |
|---|---|
| `Python/ai/predict_engine.py` | **REMOVER** (marcado LEGACY/ORFAO) |
| `Python/ai/predict_model.py` | **REMOVER** (marcado LEGACY/ORFAO) |
| `Python/ai/train_model.py` | **REMOVER** (marcado LEGACY/ORFAO) |
| `Python/dashboard/app.py` (Streamlit) | **ARQUIVAR** — não vai para loja |
| `Python/data/data_engine.py` (737 B, stub) | **REMOVER** |
| `Python/test_etapa18.py`, `test_sentry_integration.py` | **MOVER** para `tests/` |
| `Python/*.pyc`, `__pycache__/` | **REMOVER** (build limpo) |
| `app/` (Tkinter completo) | **ARQUIVAR** em `_legacy/tkinter/` |
| `ai-text-demo/`, `sandbox-quickstart/`, `experiments/` | **ARQUIVAR** |
| `backend/*.pyc` | **REMOVER** |

⚠️ **Nada de IA real é removido** — apenas o que o próprio código já marcou como órfão. `pipeline.py`, `decision/`, `entry/`, `risk/`, `core/`, `backtest/`, `ai/` (restante) são **preservados e serão ligados**.

### 6.3 Raiz do projeto

| Item | Ação |
|---|---|
| `installer/XAU_AI_PRO_Setup_1.2.0.exe` (185 MB) | **APAGAR** (D4) |
| `installer/legacy_specs/` | **ARQUIVAR** |
| `dist/`, `build/`, `frontend/tauri_bundle*.log|.flag` | **APAGAR** |
| `build_log.txt`, `build_log2.txt`, `versao_log.txt` | **APAGAR** |
| `core/*.log`, `core/*.flag`, `core/commit_msg.txt` | **APAGAR** |
| `MQL5/Experts/XAU_AI_PRO/*.md` (docs do EA) | **ARQUIVAR** em `Docs/EA/` |
| Branches `baseline-sync-backup`, `v1.2.1-crashfix`, `crewai-v1-deploy` | **AVALIAR** remoção |

**Economia estimada:** ~1,5 GB (`target/`, `dist/`, `build/`, instalador antigo).

### 6.4 Diretórios de dados — consolidação

Unificar os **5 locais** em um único canônico:

```
MANTER:    %APPDATA%\XAU_AI_PRO\                (config.json, auth.json, audit.jsonl, connections.dpapi.json)
MIGRAR:    %LOCALAPPDATA%\XAU_AI_PRO\           (strategy.db, logs)
APAGAR:    %APPDATA%\XAU AI PRO\                (connections.dpapi.json duplicado)
APAGAR:    %LOCALAPPDATA%\com.xau-ai-pro.app\   (cache WebView2 - recriado automaticamente)
```

⚠️ **Atenção:** `%LOCALAPPDATA%\XAU AI PRO\` é onde o app **instalado** reside (exe, bridge, core). Não confundir com dados. O plano é: **binários** em `%LOCALAPPDATA%\XAU AI PRO\` (padrão Tauri NSIS), **dados** em `%APPDATA%\XAU_AI_PRO\`.

---

## 7. Roadmap incremental de versões (D5)

| Versão | Escopo | Entregável |
|---|---|---|
| **1.2.3** | Fase 0 (higiene) + Fase 1 (bugs L1-L8, L21-L22) | Ciclo limpo + bugs críticos corrigidos |
| **1.2.4** | Fase 2 (UI/UX: mini terminal, posições, temas, PIN) | Pedidos do `xau ai pro.txt` atendidos |
| **1.2.5** | Fase 3 IA-1 e IA-2 (endpoints de leitura) | App mostra predição e decisão reais |
| **1.2.6** | Fase 3 IA-3 e IA-4 (UI de prévia + backtest) | Prévia de IA no ticket + aba de teste |
| **1.2.7** | Fase 4 (gateway FastAPI + OpenAPI + MCP real) | Documentação viva + MCP funcional |
| **1.2.8** | Adaptador Bybit + OKX (BROKER_ADAPTER_CONTRACT) | "Operar em qualquer corretora" |
| **1.3.0** | Fase 3 IA-5/IA-6 (treino, governança, paper) | Motor IA completo e auditável |
| **2.0.0** | Mobile (Flutter) + JWT | Controle em PC e celular |

**Regra de versionamento:** um `Docs/version.json` como **fonte única**, lido por script que atualiza `VERSION`, `package.json`, `Cargo.toml` e `tauri.conf.json` de uma só vez. Elimina a divergência 1.2.0 vs 1.2.1 (lacuna L16).
---

## 8. Ordem de execução do Ciclo Limpo (v1.2.3)

### Etapa A — Higiene (Fase 0)
1. Criar `Docs/version.json` (fonte única de versão)
2. Criar `scripts/sync_version.py` que atualiza os 4 arquivos de versão
3. `.gitignore`: excluir `bridge/`, `core/*.exe`, `dist/`, `build/`, `target/`, `*.pyc`
4. `git rm --cached frontend/src-tauri/bridge/mt5-gateway.exe` + `bridge/_internal/*`
5. Apagar instalador antigo, logs de build, flags, `__pycache__`
6. Consolidar diretórios de dados
7. Arquivar órfãos em `_legacy/` (não deletar direto — permite conferência)

### Etapa B — Correções críticas (Fase 1)
8. **L1:** `SettingsCoreSimple.togglePin` → `verificarPin`
9. **L21/L22:** `AuthGate` → fonte de verdade `carregarAuth()`; usar `useAuthStore`
10. **L2/L3:** `RobotCommandActions` → broker/mercado do store; `execute` sob confirmação
11. **L4/L5:** `HistoryTab` → `Promise.allSettled` + `toNumber()` pt-BR
12. **L6/L7:** ativos reais por broker + `/api/universal/quotes` em lote
13. **L8:** unificar Sidebar ↔ `App.tsx` (adicionar `market` e `strategy-tester`)
14. **L15:** `GATEWAY_BUILD` dinâmico (deriva de `version.json`)
15. **L16:** versão unificada nos 4 arquivos

### Etapa C — Remoção de órfãos (D2)
16. Remover ~35 componentes do frontend
17. Remover 3 arquivos Python marcados LEGACY/ORFAO
18. Arquivar `app/` (Tkinter), `Python/dashboard`, demos
19. Rodar `tsc --noEmit` (garantir 0 erros após remoção)

### Etapa D — Ciclo de build limpo
20. Limpar `node_modules`, `dist`, `build`, `target`, `bridge`, `core`
21. `npm ci` → `npx tsc --noEmit` → `npm run build`
22. `pyinstaller --clean --noconfirm mt5-gateway.spec`
23. `cargo build --release` (core)
24. Copiar bridge + core para `src-tauri`
25. `npm run tauri:build`
26. Sincronizar bundle em `installer/`
27. `ISCC.exe installer.iss` → `XAU_AI_PRO_Setup_1.2.3.exe`
28. **Assertiva:** sha256(`bridge/mt5-gateway.exe`) == sha256(`dist/mt5-gateway/mt5-gateway.exe`)

### Etapa E — Validação e publicação
29. Testes leves (12) + médios (25) + robustos (42+24)
30. Instalar em ambiente limpo; conferir `/api/health` + `GATEWAY_BUILD`
31. Conferir ausência de processos duplicados
32. `git add` + commit + push `origin/develop` e `gitlab/develop`
33. Criar tag `v1.2.3`

---

## 9. Checklist de aceite v1.2.3

| # | Critério | Como validar |
|---|---|---|
| 1 | Versão única em 4 arquivos | `scripts/sync_version.py --check` |
| 2 | `GATEWAY_BUILD` bate com a versão | `/api/health` |
| 3 | Instalador 1.2.3 gerado, 1.2.0 apagado | `Get-ChildItem installer/*.exe` |
| 4 | Nenhum binário versionado no git | `git ls-files` filtrando `.exe` |
| 5 | `tsc --noEmit` = 0 erros | executar |
| 6 | 103 testes passando | `pytest` em 4 lotes |
| 7 | PIN não desativa com código errado | teste manual |
| 8 | PIN não é apagado ao reiniciar | teste manual |
| 9 | Histórico sobrevive a corretora 503 | teste manual |
| 10 | Ativos MEXC/Binance carregam | teste manual |
| 11 | Comprar usa broker selecionado | inspeção de payload |
| 12 | Abas Mercado e Strategy acessíveis | teste manual |
| 13 | Sem processos duplicados | `Get-Process mt5-gateway` |
| 14 | Nenhuma ordem real enviada | `audit.jsonl` sem REAL |
| 15 | EA inalterado | `git status MQL5/Experts/` |

---

## 10. Regras invioláveis durante a execução

1. **EA MT5 intocável** — apenas leitura/mapeamento
2. **Conta REAL bloqueada** — `REAL_ORDER_KEYS` vazio, `REAL_EMERGENCY_STOP` presente
3. **Nenhuma ordem é enviada** em nenhuma fase — `execute:false` por padrão
4. **Sem dados simulados** — indisponível é indisponível
5. **Backup antes de remover** — órfãos vão para `_legacy/`, não são deletados direto
6. **Testes verdes obrigatórios** antes de cada build
7. **Nada é empacotado sem passar pela Etapa D completa**

---

## 11. Confirmações necessárias antes de executar

| # | Pergunta | Proposta |
|---|---|---|
| 1 | Migrar gateway para **FastAPI**? | ✅ Recomendado (seção 3) |
| 2 | Aprovar remoção dos ~35 componentes órfãos? | ✅ Lista na seção 6.1 |
| 3 | Arquivar `app/` (Tkinter) em `_legacy/`? | ✅ Sim |
| 4 | Criar `BROKER_ADAPTER_CONTRACT.md`? | ✅ Sim (seção 4) |
| 5 | Começar pela **Etapa A + B** (v1.2.3)? | ✅ Sim |

> **Próximo passo:** com a aprovação, executo a **Etapa A** (higiene + versão unificada) e a **Etapa B** (8 bugs críticos), entrego o build 1.2.3 com testes verdes e instalador novo, e apago o antigo.