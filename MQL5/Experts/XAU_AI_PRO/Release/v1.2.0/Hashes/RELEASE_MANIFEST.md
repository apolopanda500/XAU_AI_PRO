# ============================================================
# XAU_AI_PRO v1.2.0 — RELEASE MANIFEST (ETAPA 20.10)
# Data: 2026-08-25
# Estado: RELEASE CANDIDATE (aguardando forward/endurance/reconciliacao)
# ============================================================

[IDENTIFICACAO]
PRODUTO          = XAU_AI_PRO
VERSAO           = 1.2.0
BUILD            = baseline-restaurado (SignalCore revertido p/ baseline operacional)
COMPILADOR       = MetaEditor MQL5 build 6140 (x64)
COMPILE          = 0 errors / 0 warnings (25/08 14:25)
COMMIT_BASE      = fab96b0 (fix SignalCore)
COMMIT_DOCS      = d6662ac (baseline) | 0a2fd8b (security+forward)

[HASHES]
EX5              = 9303e3838e73e056b9dec4c06147d1f801fe403153806372d85a50d761949cc3
MQL5_SRC         = 787b53206d546e5e4ba9d5f41b84fde50870a6a825a697fb7e2488c479d39566
SIGNALCORE       = 67f28a9bd1708d0a97e04ea2a9f14e311cc6e9ba13a0bd8bf9870f618251069b
PY_PREDICT       = f773a6642713fb6040437427bdbd83aae187f435c5fd555d5378a56e30e79f2f

[ARVORE]
EA/              = XAU_AI_PRO.mq5 + .mqproj + Core/AI/Filters/Management/Monitoring/Enterprise/Indicators
Python/          = predict_engine.py, train_model.py, validation.py, feature_engineering.py, export_prediction.py, predict_model.py, sentry_config.py
Backend/         = api.py (servico de autenticacao/predicao)
App/             = app.py (dashboard)
Config/          = XAU_AI_PRO.PRO.set, XAU_AI_PRO.AUTOTRADE_ON.set, XAU_AI_PRO.QUALITY.set
Documentation/   = BASELINE_v120.md, SECURITY_v120.md, FORWARD_DEMO_REATTACH_v120.md, ARQUITETURA_V120_ETAPA1.md, RELATORIO_FINAL_ETAPAS1_13.md, ETAPA12_13_FORWARD_TEST_PRODUCTION.md
Hashes/          = este manifesto
Validation/      = checklist ETAPA 20.11

[CONFIG_REFERENCIA]
SIMBOLO          = XAUUSD (mais 5 graficos M5: EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF)
TIMEFRAME        = M5
MAGIC            = 2026001
ESTRATEGIA       = EMA 50/200 (M15) + RSI 14 pullback 45/55, vela fechada
GESTAO           = SL 300 / TP 600 (RR 2:1)
RISCO            = RiskPercent 1%, MaxDailyLoss 5%, MaxDrawdown 15% (config PRO)
FILTROS          = AI/News/Spread/Session/Trend/ADX: OFF na validacao atual (config graficos)
MODELO_IA        = model.pkl (Files/Data)

[VALIDACOES_REALIZADAS]
20.1 Baseline    = OK (hash + commit)
20.2 Caminho     = OK (RSI 0 erros, sinais BUY, execucao retcode 10009)
20.3 Auditoria   = OK (nenhum gate bloqueando; Algo Trading ON)
20.4 Tester      = REALIZADO (XAUUSD M5, ticks reais, 10 trades; PF 0.72 — NAO aprovado economicamente)
20.9 Seguranca   = APROVADO (sem credenciais)

[STATUS_GATES]
CAPITAL GATE     = FECHADO (PF < 1, drawdown 25.75% no backtest)
FORWARD DEMO     = EM ANDAMENTO (posicao USDJPY BUY aberta 25/08 21:05 server)
RELEASE FINAL    = PENDENTE (endurance 20.6 + reconciliacao 20.7 + IA 20.8)

[NOTA]
Baseline congelado: NAO alterar SignalCore.mqh/Dashboard.mqh durante 20.5-20.7.