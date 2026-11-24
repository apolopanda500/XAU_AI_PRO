
## [Unreleased] - 13/11/2026 - app: ROBO sem scroll emperrado, grafico acessivel

### Corrigido
- `frontend/src/theme/robo.css`: `.robo` agora e `height: 100%` com
  `min-height: 0` e `overflow-y: auto` (a pagina rola dentro de si; o
  `.content` nao entregava a rolagem ao WebView - medido: wheel e setas
  nao moviam nada). Novo `.robo-grafico-slot` ocupa o espaco restante da
  viewport da aba ROBO.
- `frontend/src/theme/robo.css`: a pagina rola dentro de si (`overflow-y: auto`). CORREÇÃO DE RAIZ (medido via CDP no WebView2 em
  13/11/2026): com altura fixa no slot flex, os filhos com `overflow: hidden`
  recebiam `min-height: auto = 0` (regra CSS flex) e a cadeia `.robo-grafico-slot`
  → `.robo-grafico` → `.grafico-viewport` → `.price-chart` encolhia até 0 — a
  toolbar do `.price-chart` ficava clipada pelo card com h=26px e o canvas nunca
  aparecia. Agora o slot é `flex: 0 0 auto` (altura natural) e a altura da página
  é natural (`.grafico-viewport` sem altura fixa; `height: auto` na viewport e na
  wrap; `min-height: 260px` na wrap) — tudo flui e pagina rola dentro de `.robo`.
  LARGURA também foi corrigida (2ª medição CDP): o slot `flex: 0 0 auto` resolvia a
  largura pela max-content (2282px) e o gráfico era desenhado fora da tela — agora
  `.robo-grafico-slot` e `.robo-grafico` usam `width: 100%` e `min-width: 0`.
- `frontend/src/components/charts/PriceChart.tsx`: a lista de indicadores
  (`PainelIndicadores`) passou a ficar recolhida em `<details>` ("Indicadores
  (7)") por padrão, para a toolbar encolher de ~498 para ~230px e o canvas subir.
- `frontend/src/components/RobotTabs.tsx`: o grafico (`AcompanharModelos`)
  passa a viver dentro do `.robo-grafico-slot`.
- `frontend/src/components/AcompanharModelos.tsx` e
  `frontend/src/theme/market.css`: `.grafico-viewport` usa `height: 100%`
  (antes `calc(100vh - 470px)`, que empurrava o canvas para abaixo da dobra
  em 839px de viewport).
- `frontend/src/components/RobotTabs.test.tsx`: assercao atualizada para o
  slot; 56/56 verdes. `tsc --noEmit` exit 0.

## [Unreleased] - 13/11/2026 - app: fusao de temas dark e violet

### Corrigido
- `data-theme='dark'` adota a paleta violeta que estava reservada para
  `violet_dark` (fundo `#0e0a1a`, acento `#a78bfa`, borda `#2e2153`).
- Removido o tema `violet_dark` (theme id, entradas em `useTheme.ts`,
  `useAppStore.ts`, `wallpapers.css`, `global.css`, `quantum.css`,
  `settings.css`).
- `normalizeTheme` migra `violet_dark` → `dark`; o `.theme-swatch-dark`
  passou a usar cor violeta.
- `useTheme.migracao.test.ts` agora cobre a migrcao `violet_dark → dark`.
- Testes da fronteira: 1017/1017 verdes; `tsc --noEmit` exit 0.


### Corrigido
- `frontend/src/hooks/useTheme.ts`: removido o tema `laranja_dark` (tema superado
  de cripto/BTC). `btc_dark` e `laranja_dark` migram para `dark` em
  `normalizeTheme`. Removido `[data-theme='btc_dark']` e o alias `[btc]` do
  `global.css`, o `.wallpaper-laranja` do `wallpapers.css`, o bloco BTC do
  `quantum.css` e os `.theme-swatch.t-btc_dark`/`.t-dourado_dark` do
  `settings.css`. Testes de migração e `ativoPresumido` alinhados.
- `frontend/src/theme/settings.css`: renomeadas as classes do swatch do
  dourado (`theme-swatch.t-xau_dark`/`.theme-swatch-xau_dark` →
  `t-dourado_dark`/`.theme-swatch-dourado_dark`) — a província de seletores
  dizia respeito a `xau_dark`, ID que o produto não emite mais, e o swatch do
  Dourado ficava sem estilo.
- `frontend/src/components/UniversalLiveTerminal.tsx` (+ `hooks/queries.ts`):
  removidos os probes ao vivo `MEXC / Spot`, `MEXC / Futuros`,
  `BINANCE / Spot` e `BINANCE / Futuros` (`/api/universal/account`), que
  geravam quatro linhas WARN com HTTP 503 a cada 30 s no terminal ao vivo —
  ruído para um broker fora de escopo.
- `frontend/src/lib/marketApi.ts` (`MARKET_SOURCES`): removidas as corretoras
  `binance`, `mexc`, `bybit`, `okx`; sobrou `mt5` (a única ativa). Testes
  `marketApi.test.ts` adaptados para MT5 sem afrouxar asserções.
- `frontend/src/components/DeclaracoesConfianca.tsx`: a linha do gateway
  passou a descrever o gateway local do app (em vez de um endereço fixo
  9011, que não é onde o app fala hoje).
- `frontend/src/theme/indicadores.css`: indicadores agora em grelha de 2
  colunas (antes, 7 linhas verticais consumindo a altura toda).
- `frontend/src/components/AcompanharModelos.tsx`: altura da viewport do
  gráfico para `calc(100vh - 470px)`, para o gráfico caber no ecrã sem scroll.

### Documentado
- `README.md`: seção "Começar" descreve o produto como é hoje (app desktop
  Tauri, instalação por NSIS em `%LOCALAPPDATA%\XAU AI PRO`); a página de
  apresentação (`site/index.html`) passou a 1.2.191 e ao estado atual do ciclo.



### Corrigido (defeito que sairia no instalador)
- `frontend/src-tauri/bridge/`: estava defasado em relacao a `dist/mt5-gateway`. Os dois
  declaravam o MESMO tamanho (28 759 944 B) e hashes DIFERENTES: o bridge dizia
  `gateway_build xau-ai-pro-1.2.183-universal-20261113` e o dist dizia `1.2.191`. Como
  `tauri.conf.json` empacota `bridge/**/*` e nunca o `dist`, o NSIS sairia com o gateway
  velho. Corrigido com `robocopy /MIR dist\mt5-gateway -> bridge` e provado por hash:
  `bridge/mt5-gateway.exe` e `dist/mt5-gateway/mt5-gateway.exe` passaram a ser
  `C42E18F9408A7AC4B281BA969BEE08577075D25ED923F3B485832BFE55308A8F`.

### Alterado
- Versao do produto `1.2.183 -> 1.2.191` em `Docs/version.json` e nos 9 portadores de
  `scripts/sync_version.py` (`VERSION`, `pyproject.toml`, os dois `package.json`,
  `Cargo.toml` do core e do src-tauri, `tauri.conf.json` e `frontend/src/version.ts`).
  A direcao foi subir o produto, e nao rotular o EA para baixo, porque o EA e
  genuinamente 1.2.191 (`Enterprise/VersionManager.mqh` tem entradas reais ate v1.2.191,
  patch maximo 191 em 210 ocorrencias). Rotular o EA de 1.2.183 seria mentira.
- `dist/mt5-gateway`: bundle congelado reconstruido com PyInstaller (155 s, 3 498
  arquivos); o anterior ficou em `dist/mt5-gateway.bak_182`.

### Testes
- `tests/test_ai_inference.py`: duas travas estavam ERRADAS e foram consertadas, nao
  afrouxadas. (1) a assercao de que a recusa do modelo do ativo nao pode ser apagada
  usava um duble que lia o campo errado; agora injeta o duble e exige
  `meta["cobertura_sobre_recusa"]`. (2) `assert "_" not in r.modelo` proibia o `_` do
  proprio ID do artefato (`MULTI_METALS`, regra D-175: artefato primeiro, alvo depois) e
  passou a medir so o ALVO (`XAUUSD 1H`). Prova negativa: as duas versoes antigas
  reprovam. Resultado: **91 passed**.
- `tests/test_versao_consistente.py`: **6 passed** com a versao unica.

### Empacotado (nao instalado)
- `dist/installers/XAU AI PRO_1.2.191_x64-setup.exe` (NSIS, 142 121 988 B,
  SHA256 `83553C5999E4AF1109D92310312B1469682F27B6A221E422C58B03207083B56E`) e
  `XAU AI PRO_1.2.191_x64_en-US.msi` (210 434 790 B). `npx tauri build` com
  `CARGO_TARGET_DIR` fora do repositorio, 13m26s, 0 erros. Prova de que o instalador
  levou o gateway certo: o `bridge/mt5-gateway.exe` estagiado no `release` tem hash
  identico ao do `dist`. A instalacao escreve em `%LOCALAPPDATA%`, fora das raizes de
  escrita do agente, e por isso e passo do dono (ver `Docs/INSTALAR_1_2_191_DONO.md`).
# CHANGELOG

## [1.2.183] - 13/11/2026 - PC: o grafico da aba ROBO pede o PAR, nao o nome do modelo

### Corrigido (causa real do "Grafico indisponivel")
- `frontend/src/lib/parNaTela.ts`: novo `ehClasseDeModelo()` (`/^MULTI_[A-Z0-9_]+$/`) e
  `parDeVerdade()`. O nome de um modelo de CLASSE nunca mais conta como par: `parNaTela`
  filtra os DOIS lados (motor e tela), o que tambem limpa um `selectedSymbol` ja gravado no
  `localStorage` (o store e zustand `persist`, por isso o valor antigo voltava a cada arranque).
- `frontend/src/components/ListaModelos.tsx::escolher`: o card de classe nao escreve simbolo.
  Com par ja escolhido na tela ele troca so o periodo e manda o par; sem par **recusa com
  motivo** ("modelo de CLASSE ... escolha o par em «Par para operar»"). Nenhum ativo e
  presumido (AGENTS.md 3).
- `frontend/src/components/SeletorModelo.tsx`: a mesma guarda na lista de pares e no valor
  lido do store (fechou os 5 testes que falhavam por heranca do valor persistido).

### Medido (13/11/2026 - no repositorio e no artefacto, nao suposto)
- `classe_de('MULTI_METALS') = OUTROS`, `simbolo_valido('MULTI_METALS') = False`,
  `_tentativas_multi('MULTI_METALS','M5') = []`: o backend **nunca** aceitou o nome do modelo
  como ativo — quem o gravava era o frontend (`m.symbol` do `MULTI_METALS.meta.json`).
- `_tentativas_multi('XAUUSD','M5') = [('MULTI_METALS','MULTI_METALS_M5'),
  ('MULTI_METALS','MULTI_METALS')]`: o modelo de classe entra sozinho para o par real.
- Rota do grafico: `_universal_candles('mt5','metals','MULTI_METALS')` -> `ok=False`,
  `count=0`, `fallback_publico=None` (recusa com motivo, nunca dado falso);
  `_universal_candles('mt5','metals','XAUUSD')` -> `ok=True`, `count=10`,
  `source='mt5_gateway'`, `fallback_publico=None`, ultima vela
  O 3.918,76 / H 3.921,40 / L 3.917,63 / C 3.919,43. O singular `'metal'` devolve as
  mesmas 10 velas (aliasing `metal`->`metals`).

### Testes
- `npx vitest run`: **83 ficheiros, 1019 testes, todos verdes** (`VITEST_EXIT=0`, 668 s).
- `npx tsc --noEmit`: `TSC_EXIT=0`.
- `tests/test_candles_publicos_sem_conta.py`: **16 passed** (as 4 falhas herdadas de
  "so MT5 ativo" foram fechadas).
- A trava antiga de `ListaModelos.test.tsx` esperava `corpo.simbolo === 'MULTI_METALS'`, ou
  seja, **travava o defeito**; foi reescrita para exigir o par do operador e ganhou prova
  negativa (card de classe sem par RECUSA e nao grava nada).

### Build
- 8 manifestos em `1.2.183`; `gateway_build = xau-ai-pro-1.2.183-universal-20261113`.
- Core Rust: `xau-ai-pro-core.exe` 9 157 120 B. Gateway PyInstaller: `mt5-gateway.exe`
  28 759 944 B, 3497 ficheiros em `_internal` (sincronizado para `frontend/src-tauri/bridge`).
- Bundle NSIS: `XAU AI PRO_1.2.183_x64-setup.exe`, 142 102 924 B, SHA256
  `EEB57D996A9A5F9A47FC3EA1D29277BB9B9EF31CF536EE4E94594CFECC4D5AAD`;
  `XAU AI PRO.exe` 13 998 080 B, FileVersion e ProductVersion `1.2.183`.
- Bateria do artefacto (`scripts/medir_artefato_gateway.py --exe Temp\dist-gw\...`):
  **exit 0** — 5 rotas `401` sem token, `401` com token errado,
  `withdrawals_enabled=False`, `transfers_enabled=False`, ordem `execute=false` ->
  `stage=validated`, `gateway_build=xau-ai-pro-1.2.183-universal-20261113`.

### Nao feito, e por que
- **Instalacao nao executada**: o NSIS escreve em `%LOCALAPPDATA%\XAU AI PRO` e em
  `Program Files`, fora das raizes autorizadas do terminal. E acao do dono.
- O bundle **MSI** ficou pendurado (`light.exe` escreveu `output.wixpdb` e nunca criou
  `output.msi`); a corrida foi terminada e o NSIS reconstruido com `--bundles nsis`, que e
  o entregavel.

## [1.2.182] - 12/11/2026 - PC: o grafico da aba ROBO volta a ser dado do MT5
### Corrigido
- `frontend/src/lib/mercadoCanonico.ts` (novo) e `PriceChart.tsx::mercadoParaConsulta`: o
  nome do mercado passa a ser canonizado no ULTIMO portao antes da consulta
  (`metal`->`metals`, `index`/`indice`->`indices`, `stock`/`equity`->`stocks`,
  `commodity`->`commodities`, `bond`->`bonds`, `crypto`->`crypto-spot`). Nome
  desconhecido continua a voltar como veio (`cfd`->`cfd`): quem recusa e o
  `normalizeMarketSource`, com motivo (AGENTS.md 3).
- `frontend/src/components/OperacaoAutomatica.tsx` e `AcompanharModelos.tsx`: o mercado
  vem de `mercadoDoAtivo` (a ficha que a corretora publica), nao do singular cru do motor.

### Medido (12/11/2026, no ARTEFACTO congelado - nao no fonte)
- `GET /api/universal/candles?broker=mt5&market=metal&symbol=XAUUSD&timeframe=M1&limit=3`
  -> `http=200`, `count=10`, `source=mt5_gateway`, `fallback_publico=None`, ultima vela
  O 3911.23 / H 3911.49 / L 3909.38 / C 3909.39. Antes: erro -> fallback publico
  (yahoo GC=F) com a ultima vela degenerada (`Abr=Max=Min=Fecha`).
- Bateria de artefacto (`scripts/medir_artefato_gateway.py`): fail-closed nas rotas sem
  token, token errado 401, ordem `execute=false` -> `stage=validated`,
  `withdrawals_enabled=False`, `transfers_enabled=False`,
  `gateway_build=xau-ai-pro-1.2.182-universal-20261112`.

### Build
- `scripts/sync_version.py`: 8 manifestos alinhados a `1.2.182` (`VERSION`,
  `pyproject.toml`, `backend/package.json`, `frontend/package.json`,
  `frontend/src-tauri/Cargo.toml`, `tauri.conf.json`, `core/Cargo.toml`,
  `frontend/src/version.ts`); `GATEWAY_BUILD` derivado, nao escrito a mao.
- Core Rust recompilado: `core/Cargo.lock` mudou 1 linha (versao do pacote local).
- Gateway PyInstaller: 28 759 944 B, 3497 ficheiros em `_internal`.
- Bundle NSIS: `XAU AI PRO_1.2.182_x64-setup.exe`, 142 143 096 B, SHA256
  `71EFF9CBA6F91401D3531113C6771C490162996D06C3A52C837C232D2F573B1C`;
  `XAU AI PRO.exe` com FileVersion e ProductVersion `1.2.182`.
- Frontend: `npm test` 1015/1015 (83 ficheiros), `tsc --noEmit` exit 0, `vite build` exit 0.

### Nao feito, e por que
- **Instalacao do NSIS nao executada**: o instalador escreve fora das raizes permitidas
  do terminal (`%LOCALAPPDATA%\XAU AI PRO`, `Program Files`). Exige acao do dono.
- Bundle **MSI** nao completou: `failed to bundle project: O arquivo ja esta sendo usado
  por outro processo (os error 32)` ao aplicar a informacao de versao. O NSIS, que e o
  entregavel, completou.
- `dist\mt5-gateway` estava bloqueado (`PermissionError WinError 5`); o gateway foi
  construido em `Temp\dist-gw` e sincronizado para `frontend\src-tauri\bridge`.

## [Unreleased] - 12/11/2026 — PC: gráfico MT5 com classe institucional singular
### Corrigido
- `backend/broker_registry.py`: `normalize_market` agora mapeia a classe do ativo no
  singular (`metal`, `index`, `indice`, `stock`, `equity`, `commodity`, `bond`,
  `titulo`) para o plural esperado pelo `MT5_MARKETS` (`metals`, `indices`,
  `stocks`, `commodities`, `bonds`). Antes disso, `normalize_read_scope('mt5','metal',…)`
  levantava `ValueError("mercado não suportado para mt5")`, o gateway devolvia
  resposta sem velas com `fallback_publico: true`, e a aba ROBÔ → GRÁFICO AO VIVO
  mostrava dado público stale (Yahoo GC=F M1 ~3916, último candle plano —
  `Abr=Máx=Mín=Fecha`) mesmo com o MT5 vivo. Medido 12/11/2026:
  `_universal_candles('mt5','metal','XAUUSD','M1',3)` → 10 candles reais MT5.
- Ver `Docs/FINALIZAR_VERSAO_PC_20261112.md` para o diagnóstico completo e a
  divisão de trabalho CMD/ALFA/DELTA.

## [Unreleased] - Auditoria de segurança + correção anti-falso-positivo
### Segurança
- `launcher.spec`: `upx=True` → `upx=False` (elimina gatilho de heurística
  associado à detecção falsa `Trojan:Win32/Bearfoos.A!ml` em 21/09/2026).
- `app/updater.py`: `check_update()` agora localiza o asset versionado
  `XAU_AI_PRO_Setup_<versão>.exe` (antes buscava nome literal inexistente).
- `.gitignore`: nova seção operacional — nunca versionar backups locais,
  logs de build/validação, laudos gerados por máquina, dados
  `*.dpapi.json`/`*.dpapi.tmp`, nem a pasta local `XAU AI PRO/`.
### Corrigido
- Resolução da raiz do projeto em `validar_build.ps1` robusta a CWD incorreto.
- Gates do validador agora leem apenas código (ignoram comentários/docstrings),
  evitando falso alarme sobre `upx` e falso OK sobre onefile/onedir.

## [1.3.2] - 2026-08-30
### Integração Slack + Notificações
- Novos módulos Python: `slack_notifier.py` (cliente Webhook) e `slack_watcher.py` (monitor de eventos MT5).
- `integrations.py`: adicionado `SlackClient` (testar/send) com padrão GitHub/Figma/Brave.
- `config_store.py`: campos `slack_webhook_url`, `slack_enabled`, `slack_notify_trades/errors/risk`.
- GUI aba Integrações: seção "Slack Notifications" (webhook URL, checkboxes, teste de conexão).
- `auto_engine.py`: notifica resultado do auto-approve no Slack.
- `auto_watch.py`: inicia Slack watcher em background.
- `.env.example`: variáveis `SLACK_WEBHOOK_URL`, `SLACK_ENABLED`, etc.
- Docs: `README_APP.md` com guia completo de configuração Slack.

### 2026-08-24 - Correcoes de integracao EventEmitter
- Removida duplicacao de EventSystemStart no OnInit (XAU_AI_PRO.mq5).
- Removida duplicacao de EventTradeOpen no ExecutionEngine (fluxo unico via OnTradeTransaction).
- EA recompilado: 0 erros / 0 avisos.
- Sincronizado workspace -> plataforma (XAU_AI_PRO.mq5, ExecutionEngine.mqh, .ex5).

## [1.2.0-RC1] - 2026-08-23
### ETAPA 14 + ETAPA 15 (baseline/contratos)
- EA MQL5 v1.2.0-RC1 (build 0/0) injetado na Plataforma a partir do workspace.
- ETAPA 15.1: baseline oficial da plataforma (EA + Python + App + Frontend/Backend + MCP + Sentry).
- ETAPA 15.2.1: auditoria do Contrato do Dataset.
  - Encoding UTF-16 LE (BOM FF FE) verificado, FILE_UNICODE explícito no DataLogger.mqh.
- ETAPA 15.2.2: auditoria do Contrato de Features (FECHADA).
  - 25 features unificadas, prepare_features() valida ausentes, ordem fixa.
  - Opção B: deteção de encoding por BOM em data_engine_xau.py.
  - AIConnector lê metadados v2: model_version, model_id, feature_hash, inference_ms, timestamp_utc.

- ETAPA 15.2.3: auditoria do Contrato de Previsão AI (FECHADA).
  - Metadados v2 verificados ponta a ponta: model_version, model_id, feature_hash, inference_ms, timestamp_utc.
  - AIConnector bloqueia estados UNAVAILABLE/ERROR/HOLD (nunca viram sinal de trade).
  - Drift de convenção de modelos documentado (pipeline.py ativo vs predict_model/train_model/predict_engine órfãos).
- ETAPA 15.2.4: auditoria do Contrato de Segurança (FECHADA).
  - UNAVAILABLE fail-safe: sem bônus e sem veto no DecisionEngine/AIEngine.
  - Dupla camada IA (score + veto FinalAIAllow) documentada.
  - Gap observabilidade (AuditLog/Notification no veto AI) -> 15.6.
- ETAPA 15.2.5: Contrato de Eventos (ESPECIFICADO).
  - Canal forward_test_events.csv (append-only, UTF-16) + 16 eventos padrão.
  - Hallazgo: App consome só prediction_*.json hoje; emissor + consumo -> 15.6.
- ETAPA 15.2.6: Latência (AUDITADA).
  - CTelemetry (Telemetry.mqh) com RecordBrokerLatency/PythonLatency/DatabaseLatency/AILatency + health.
  - Fiação dos pontos de medição -> 15.6.
- **ETAPA 15.2 FECHADA** (contratos EA <-> Python <-> App auditados e documentados).
  - 25 features unificadas, prepare_features() valida ausentes, ordem fixa.
  - Opção B: deteção de encoding por BOM em data_engine_xau.py.
  - AIConnector lê metadados v2: model_version, model_id, feature_hash, inference_ms, timestamp_utc.
- Contrato A (prediction JSON), B (dataset/heartbeat), C (eventos app) formalizados.
- Docs/contracts/ea_python_app_contract.md criado.

## [1.2.0-RC1] - 2026-08-24

### ETAPA 15.6 - Observabilidade (EventEmitter)
- EventEmitter (15.6.1): camada unica de eventos (forward_test_events.csv, UTF-16, separador virgula).
- Telemetria multinivel (15.6.3/15.6.5): HEALTHY/WARNING/ERROR/SAFE/RECOVERY/UNAVAILABLE.
- Python event_reader (15.6.2/15.6.4): leitura/estado do stream para o App/Dashboard.
- Dashboard (15.6.6): secao Event Stream consumindo eventos em tempo real.
- 15.6 FECHADA. EA 0 erros/0 avisos.
### ETAPA 15.3/15.8/15.10 - IA + Seguranca + Production Candidate
- 15.3 FECHADA: predict_all grava UNAVAILABLE quando sem modelo; legado marcado (predict_model/train_model/predict_engine).
- 15.8 FECHADA: secrets centralizadas (inputs vazios + env).
- 15.10 FECHADA: Release/v1.2.0-RC1 Production Candidate (PRODUCTION_CANDIDATE.md).
- Workspace -> Plataforma sincronizado (Telemetry, EventEmitter, AIConnector, NewsFilter, XAU_AI_PRO.mq5/.ex5).


## [1.2.0] - 2026-08-18
### Versao unificada v1.2.0
- Todos os modulos MQL5 (Core, AI, Filters, Indicators, Management, Monitoring, Enterprise) padronizados para v1.2.0.
- EA XAU_AI_PRO.mq5 atualizado para v1.2.0 (property + cabecalhos + logs).
- Corrigido bug: input AutoTrade nao era verificado no OnTick (agora e respeitado).
- App desktop (app/, Python/, specs) padronizado para v1.2.0.
- VersionManager.mqh atualizado para 1.2.0.
- README e frontend renomeados de Crypto Trader Pro para XAU AI PRO.

## [1.13] - 2026-08-08
### Adicionado
- Script de diagnóstico de integração em `Tools/check_integration.py`.
- Instalação e configuração da biblioteca `MetaTrader5` no Python.
- Tutorial de gestão de credenciais no `AGENTS.md`.

### Corrigido
- Sincronização de chaves JSON entre Python e MQL5: chaves `buy`/`sell` adicionadas e sinais normalizados para `BUY`/`SELL`/`STRONG_BUY`.
- Compatibilidade do `AIConnector.mqh` com sinais de alta confiança (Strong Buy/Sell).

## [1.12] - 2026-08-08
### Adicionado
- Expansão do ecossistema MCP: Integrados servidores Brave Search, Alpha Vantage e MetaTrader 5 para enriquecimento de dados e execução.
- Configuração de caminhos absolutos para npx e node, resolvendo erros de ambiente.
- Novas habilidades (skills) de especialista em Trading XAU e análise de dados configuradas no AGENTS.md.
- Recomendações de extensões para VS Code/Cursor no arquivo `.junie/extensions.json`.

## [1.11] - 2026-08-08
### Adicionado
- Documentación de configuración de GitHub Issues en `Docs/GITHUB_ISSUES_CONFIG.md`.
- Integración verificada con el servidor MCP de GitHub.
- Estructura de base de datos SQLite validada para la versión 1.11.

### Corrigido
- **Crítico:** Erro de compilação MQL5 `function 'GetAISignal' already defined`. As funções foram renomeadas para `GetClientAISignal` (em `AIClient.mqh`) e `GetAIEngineSignal` (em `AIEngine.mqh`) para evitar conflitos de escopo global.
- **Crítico:** Error de `UnicodeDecodeError` en el pipeline de Python al leer `dataset.csv` (UTF-16 con BOM). Se implementó un cargador de bytes robusto en `data_engine_xau.py`.
- Bugs críticos de inicialización en `AIClient.mqh`, `ValidationChecklist.mqh` y `Diagnostics.mqh` (errores de INIT_FAILED).
- Rutas de archivos en MQL5 para lectura de `prediction_*.json` y `dataset.csv`.
- Lógica de señales en `SignalCore.mqh` para ser menos restrictiva y permitir operaciones en condiciones reales.
- Pipeline de Python: implementación de `feature_engineering.py` que estaba vacío.

### Otimizado
- Flujo de IA: Validación de extremo a extremo (Entrenamiento -> Predicción -> JSON) completada con éxito.
- Parámetros de gestión de riesgo en `Config.mqh`:
    - `ATRMultiplier`: 2.0 -> 1.2
    - `BreakEvenTrigger`: 150 -> 80
    - `PartialTrigger`: 300 -> 150
    - `PartialPercent`: 50.0% -> 30.0%
- `MaxSpread` aumentado a 50 para evitar bloqueos innecesarios en el Oro.

### Segurança
- Verificación completa de dependencias Python (27/27 OK).
- Aplicación de linting (`Ruff`) y formateo (`Black`) en el código Python.
- Restaurado el umbral mínimo de 500 muestras para entrenamiento real en `pipeline.py`.

---
*Próximo paso: Recompilar EA en MetaEditor y testear en gráfico XAUUSD.*

