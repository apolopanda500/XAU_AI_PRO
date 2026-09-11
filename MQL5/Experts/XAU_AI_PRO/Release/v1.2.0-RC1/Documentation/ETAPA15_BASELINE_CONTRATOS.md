# XAU_AI_PRO — ETAPA 15: Baseline da Plataforma + Contratos

Data: 2026-08-23 | Fase: 15.1 (baseline) + 15.2 (contratos)

---

## 15.1 — Baseline oficial (congelado)

Estado REAL mapeado (não é idealizado — é o que existe):

```
XAU_AI_PRO v1.2.0-RC1
│
├── EA MQL5          → Experts/XAU_AI_PRO/XAU_AI_PRO.mq5 (+ .mqproj valido, build 0/0)
├── Módulos MQL5     → Core/, AI/, Indicators/, Filters/, Management/,
│                      Enterprise/, Monitoring/ (todos no controle, commit d07170e)
├── Python/IA        → ⚠️ DISPERSO: empacotado em Files/Temp/_MEI*/Python/
│                      (main.py, pipeline.py, predict.py, train.py, ai/,
│                       data/, decision/, risk/, backend/api.py, dashboard/app.py)
│                      + scripts soltos em Files/Temp/*.py (build_dataset,
│                       run_predict, run_train, etc.)
├── Dataset          → Experts/XAU_AI_PRO/Data/ (dataset.csv, prediction_*.json)
├── Configurações    → Core/Config.mqh (inputs) + Enterprise/ConfigManager.mqh
│                      (perfis) + Profiles/Tester/*.ini (presets backtest)
├── Logs             → MQL5/logs/, Tester/logs/, XAU_AI_PRO.log
├── Auditoria        → AuditLog (FILE_COMMON), forward_test_session.csv,
│                      forward_test_trades.csv, QuantValidationReport.txt,
│                      quant_matrix.csv
└── Aplicativo       → ⚠️ NÃO formalizado. Existe um esboço Python:
                      Files/Temp/_MEI*/Python/dashboard/app.py (não versionado)
```

### Regra de congelamento (Fase 15.1)
- `AIConnector.mqh`, `DecisionEngine.mqh`, `NewsFilter.mqh` → **modificados antes da ETAPA 14**;
  NÃO entram no baseline até auditoria separada (pendência formal).
- Nenhum módulo novo sem necessidade real de plataforma.

## 15.2 — Contratos formais EA ↔ Python ↔ App

### Contrato A — Prediction JSON (Python → EA)
Arquivo: `Data/prediction_<SYMBOL>.json` (ex.: prediction_XAUUSD.json)
Formato e campos que o EA **lê** (AIConnector.mqh `ExtractJSON`):

```json
{
  "symbol": "XAUUSD",
  "signal": "BUY",              // BUY | SELL | STRONG_BUY | STRONG_SELL | NEUTRAL
  "price": 4608.82,
  "buy": 62.5,                  // probabilidade compra %
  "sell": 37.5,                 // probabilidade venda %
  "score": 78.3,                // 0-100
  "confidence": 75.0            // 0-100 (se <=0, fallback = score)
}
```

**Regras do contrato:**
1. `symbol` deve ser o nome base normalizado (XAUUSD, BTCUSD, ETHUSD…) — aceito exato ou via `NormalizeAISymbol` (GOLD#→XAUUSD).
2. Valores numéricos em ponto decimal; `signal` em maiúsculas.
3. `confidence<=0` → EA usa `score` como fallback (já implementado).
4. **Extensões planejadas (não quebram o parse atual):** `model_version`, `model_id`, `feature_hash`, `inference_ms`, `timestamp_utc`. O `GetAIMetaString()` já retorna `"production"` para `MODEL_STATUS` — quando o Python publicar esses campos, ativar a leitura.
5. Falta de arquivo/JSON inválido → `LoadAIPrediction=false` → comportamento definido pela política (SAFE/fallback, nunca ponto único de falha).

### Contrato B — Dataset (EA → Python)
Arquivo: `Data/dataset.csv` (colunas atuais via Dataset/DataLogger) e
`Data/forward_test_session.csv` (heartbeat) — heartbeat 1x/s:
`timestamp,balance,equity,drawdown_pct,free_margin,spread_points,server_offset_sec,connection_state,failure_mode,news_state,ai_ready,ai_confidence,market_score,positions_open,ea_version`
Trades: `timestamp,symbol,event,signal,score,ai_confidence,side,volume,price,sl,tp,ticket,profit,exec_result,retcode,block_reason`

### Contrato C — Eventos para App/Monitoring (EA → App)
Fonte única: `quant_matrix.csv` + `QuantValidationReport.txt` (FILE_COMMON) +
`forward_test_*` + Notifications (push/Telegram). O app (dashboard Python)
deve consumir SOMENTE esses arquivos — nenhum campo novo sem contrato.

## 🚧 Pendências de baseline (registradas, não resolvidas agora)
1. **Consolidar o pipeline Python** em pasta versionada oficial (ex.: `Python/` no repo) — hoje está só em Temp (não-versionado, risco).
2. Auditar `AIConnector` / `DecisionEngine` / `NewsFilter` (modificados pré-14) antes do baseline final.
3. Formalizar o app/dashboard (fase 15.6 Observabilidade).
4. Segurança (15.8): credenciais/Telegram fora do código (hoje inputs vazios — OK, mas documentar).

---

*Este documento é o artefato oficial da Fase 15.1/15.2. Próximas fases (15.3 IA, 15.4 Execution, 15.5 Risk, 15.6 Observabilidade) atualizam este baseline.*

---

## ✅ ETAPA 20.1 — BASELINE CONGELADO (2026-08-24 17:44 -03:00)

### Estado oficial (🟩 congelado / imutável)

| Item | Status |
|---|---|
| EA XAU_AI_PRO v1.2.0 | ✅ compilação 0 erros / 0 avisos |
| 89 .mqh/.mq5 de código-fonte limpos | ✅ UTF-8 sem BOM |
| Encoding corrigido | ✅ (incidente BOM duplo C3 AF C2 BB resolvido) |
| Compilação x64 | ✅ 0/0, cpu='X64 Regular', 9030 ms |
| Arquitetura | 🔒 CONGELADA |
| Código de trading | 🔒 NÃO ALTERAR |
| IA | 🔒 NÃO ALTERAR |
| Risk/Execution | 🔒 NÃO ALTERAR |
| Backend/Dashboard | 🔒 baseline |
| Versão | **v1.2.0** |

### Evidência de build (registro imutável — v1.2.0)

| Metadado | Valor |
|---|---|
| Commit do estado limpo | `22fdbf45ada6689c4856e481c1b74470f7892d6f` |
| Commit do estado limpo (message) | `20.1 baseline: telegra stats csv como artefato runtime (gitignore)` |
| SHA-256 do `XAU_AI_PRO.ex5` | `036cc18d6015913c6919d3856f8211bbe4e1e3e870e81fb728a0c2cfd584cfe4` |
| SHA-256 do `XAU_AI_PRO.mq5` | `e72caefb8ce9c1ad879f1e54c87ff41295557a7f99aa28765a1bff46724ef333` |
| Tamanho do `.ex5` | 402,226 bytes |
| MetaEditor/MQL5 build | **6140** |
| Alvo de compilação | x64 (`X64 Regular`) |
| Data/hora da build | 2026-08-24 17:44 -03:00 (UTC 20:44) |
| Resultado compilação | ✅ **0 erros / 0 avisos** (9030 ms) |
| Git working tree | ✅ **limpo** (nothing to commit, working tree clean) |
| Branch | `main` → remoto `github/apolopanda500/mql5` |
| Push | ✅ `839b803..22fdbf4` main → main |

### Arquivos incluídos (conjunto compilado)

- **2× .mq5** (XAU_AI_PRO.mq5 + T7_BackupRecoveryTest.mq5) e **87× .mqh** = **89 arquivos** de código-fonte MQL5 limpos (UTF-8 no BOM).
- Cadeia de `#include` completa (pré-processador MQL5) verificada na compilação: Trade/+Object.mqh, Trade/*.mqh, Core/Config.mqh, Monitoring/EventEmitter.mqh, Core/StateMachine, RiskCenter, RiskHub, SystemManager, CompatibilityManager, SymbolManager, PathManager, EnvironmentManager, TimeFrameManager, AI/*, Indicators/*, Filters/*, Management/*, Enterprise/*, Monitoring/*.
- O `property tester_indicator "KCI_Directional_Matrix"` foi adicionado implicitamente (uso em iCustom).

### Regra de imutabilidade (obrigatória a partir de agora)

| Módulo | Status |
|---|---|
| DecisionEngine.mqh | 🔒 congelado |
| RiskEngine.mqh | 🔒 congelado |
| ExecutionEngine.mqh | 🔒 congelado |
| AIEngine.mqh | 🔒 congelado |
| AIConnector.mqh | 🔒 congelado |
| SignalCore.mqh | 🔒 congelado |
| NewsFilter.mqh | 🔒 congelado |

> ⚠️ **Regra**: qualquer mudança nesses módulos **não altera o baseline v1.2.0 diretamente**. Deve ser criada a **branch/versão experimental v1.2.1** e comparada contra o baseline. Isso é crítico após o incidente de encoding: o préprocessador MQL5 processa os `#include` antes da compilação, portanto uma alteração aparentemente pequena em um `.mqh` pode gerar cascata de erros no EA inteiro.

> 🚩 **PF = 0,46** é um resultado a ser investigado (medir causa), NÃO "forçado" para >1. Alteração só após medição e com justificativa, via v1.2.1.

### Sequência pós-baseline (20.2 → 20.7)
```
20.1 — Baseline congelado 🔒  ✅ (registrado aqui)
20.2 — Endurance técnica        → pendente
20.3 — Forward test prolongado  → pendente
20.4 — Análise estatística      → pendente
20.5 — Performance/PF           → pendente
20.6 — Failure & Recovery       → pendente
20.7 — Production Gate definitivo → pendente
```