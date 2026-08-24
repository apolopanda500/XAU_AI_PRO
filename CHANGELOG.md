# CHANGELOG

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
