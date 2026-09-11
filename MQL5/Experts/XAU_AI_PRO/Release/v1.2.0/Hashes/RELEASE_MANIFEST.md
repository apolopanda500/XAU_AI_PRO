# ============================================================
# XAU_AI_PRO v1.2.0 — RELEASE MANIFEST (ETAPA 20.10)
# Data original: 2026-08-25 | RE-PACKAGE: 2026-08-28
# Estado: RELEASE CANDIDATE (aguardando forward/endurance/reconciliacao)
# ============================================================

[IDENTIFICACAO]
PRODUTO          = XAU_AI_PRO
VERSAO           = 1.2.0
BUILD            = baseline-restaurado (SignalCore revertido p/ baseline operacional)
COMPILADOR       = MetaEditor MQL5 build 6140 (x64)
COMPILE          = 0 errors / 0 warnings
COMPILED_AT      = 2026-08-28 17:58 UTC (re-compilacao baseline para re-package)
COMMIT_BASE      = fab96b0 (fix SignalCore) — baseline congelado intacto

[HASHES — ATUALIZADOS 2026-08-28 (re-package)]
EX5              = d996bc2f83a1bd6004cc25aca8277b898127d38c43262b3e8eaa5483d287f215
EX5_SIZE_BYTES   = 399236
MQL5_SRC         = 787b53206d546e5e4ba9d5f41b84fde50870a6a825a697fb7e2488c479d39566
SIGNALCORE       = 67f28a9bd1708d0a97e04ea2a9f14e311cc6e9ba13a0bd8bf9870f618251069b

[HASHES — REFERENCIA MANIFESTO ORIGINAL 25/08 (obsolescente)]
EX5_OLD          = 9303e3838e73e056b9dec4c06147d1f801fe403153806372d85a50d761949cc3 (400118 bytes)
MOTIVO           = ex5 nao e bit-a-bit reproduzivel (timestamp embutido); fontes identicas + mesmo compilador garantem comportamento identico. Pacote anterior (165e73f6...) estava STALE em relacao ao manifesto — corrigido no re-package.

[ARVORE]
EA/              = XAU_AI_PRO.mq5 + .mqproj + Core/AI/Filters/Management/Monitoring/Enterprise/Indicators
Python/          = predict_engine.py, train_model.py, validation.py, feature_engineering.py, export_prediction.py, predict_model.py, sentry_config.py
Backend/         = api.py (servico de autenticacao/predicao)
App/             = app.py (dashboard)
Config/          = XAU_AI_PRO.PRO.set, XAU_AI_PRO.AUTOTRADE_ON.set, XAU_AI_PRO.QUALITY.set (+ FASE_FINAL_20_5.SYMBOLS_AMPLIADO.set)
Documentation/   = BASELINE_v120.md, SECURITY_v120.md, FORWARD_DEMO_REATTACH_v120.md, ARQUITETURA_V120_ETAPA1.md, RELATORIO_FINAL_ETAPAS1_13.md, ETAPA12_13_FORWARD_TEST_PRODUCTION.md, FASE_FINAL_20_5_20_11.md, FORWARD_TEST_20_6.md, ETAPA_20_7_20_8.md
Hashes/          = este manifesto
Validation/      = checklist ETAPA 20.11

[CONFIG_REFERENCIA]
SIMBOLO          = XAUUSD (mais 10 graficos M5: EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF, USDSEK, GBPUSD, USDCAD, USDJPY, USDCNH)
TIMEFRAME        = M5
MAGIC            = 2026001
ESTRATEGIA       = EMA 50/200 (M15) + RSI 14 pullback 45/55, vela fechada
GESTAO           = SL 300 / TP 600 (RR 2:1)
RISCO            = RiskPercent 1%, MaxDailyLoss 5%, MaxDrawdown 15% (config PRO)
FILTROS          = AI/News/Spread/Session/Trend/ADX: OFF na validacao atual (config graficos)
MODELO_IA        = model.pkl (Files/Data)

[VALIDACOES_REALIZADAS]
20.1 Baseline    = OK (hash + commit fab96b0)
20.2 Caminho     = OK (RSI 0 erros, sinais BUY, execucao retcode 10009)
20.3 Auditoria   = OK (nenhum gate bloqueando; Algo Trading ON)
20.4 Tester      = REALIZADO (XAUUSD M5, ticks reais, 10 trades; PF 0.72 — NAO aprovado economicamente)
20.5 Reattach    = OK (11 EAs baseline, log limpo, EventStream ativo, 3 posicoes)
20.6 Endurance   = EM ANDAMENTO (janela limpa desde 28/08 21:05 UTC)
20.7 Stress/Recovery = PREPARADO (runbook) — executar com posicoes abertas
20.8 Reconciliation  = PRE-CHECAGEM OK (0 divergencias na amostra pos-reanexacao)
20.9 Seguranca   = APROVADO (sem credenciais)

[STATUS_GATES]
CAPITAL GATE     = FECHADO (PF janela contaminada 0,12; janela limpa 20.6 em medicao — PF >= 1,0 exigido)
FORWARD DEMO     = EM ANDAMENTO (janela limpa 28/08 21:05 UTC, 11 simbolos)
RELEASE FINAL    = PENDENTE (endurance 20.6 + stress 20.7 + reconciliacao 20.8 + gate 20.11)

[NOTA]
Baseline congelado: NAO alterar SignalCore.mqh/Dashboard.mqh durante 20.5-20.7. WIP v1.3.1 preservado em stash@{0} (fora da estrategia sob validacao).