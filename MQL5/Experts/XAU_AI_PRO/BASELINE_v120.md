# ============================================================
# XAU_AI_PRO v1.2.0 — BASELINE CONGELADO (ETAPA 20.1)
# Data: 2026-08-25
# Estado: ponto imutavel de recuperacao — NAO ALTERAR durante testes
# ============================================================

[BUILD]
VERSION          = 1.2.0
BUILD_LABEL      = baseline-restaurado
COMPILER         = MetaEditor (MQL5 build 6140, x64)
RESULT           = 0 errors / 0 warnings
COMPILED_AT      = 2026-08-25 14:25 (local)

[COMMIT]
COMMIT           = fab96b0
MESSAGE          = fix(signal): reverter SignalCore p/ baseline v1.2.0
BRANCH           = main

[HASHES]
EX5_SHA256       = 9303e3838e73e056b9dec4c06147d1f801fe403153806372d85a50d761949cc3
EX5_SIZE_BYTES   = 400118
MQL5_SHA256      = 787b53206d546e5e4ba9d5f41b84fde50870a6a825a697fb7e2488c479d39566
SIGNALCORE_SHA256= 67f28a9bd1708d0a97e04ea2a9f14e311cc6e9ba13a0bd8bf9870f618251069b
SIGNALCORE_SIZE  = 3780

[SIGNALCORE]
STATE            = RESTAURADO (baseline v1.2.0 original)
MUDANCA_REVERTIDA= cache de handles 1x/simbolo -> causa 'Falha ao copiar RSI'
COMPORTAMENTO    = handles criados/copiados/liberados a cada GetSignal()
LOGICA_SINAL     = preservada (EMA50>EMA200 + RSI<45 BUY | EMA50<EMA200 + RSI>55 SELL, vela fechada)
STUBS            = SignalCoreInit()/ReleaseSignalHandles() mantidos p/ compat OnInit/OnDeinit

[CONFIG_ATIVA]
TIMEFRAME        = M5 (PERIOD_CURRENT nos 6 graficos)
SYMBOLS          = XAUUSD, EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF
MAGIC            = 2026001
FASTEMA          = 50
SLOWEMA          = 200
RSIPERIOD        = 14
RSI_PULLBACK_BUY = 45.0
RSI_PULLBACK_SELL= 55.0
STOP_LOSS_PTS    = 300
TAKE_PROFIT_PTS  = 600
MAX_OPEN         = 5
RISK_PERCENT     = 1
MAX_DAILY_LOSS   = 5%
MAX_DRAWDOWN     = 15%

[MODULOS_ATIVOS]
ENABLE_NEWS_FILTER   = 0
ENABLE_AI_FILTER     = 0
ENABLE_SPREAD_FILTER = 0
ENABLE_SESSION_FILTER= 0
ENABLE_TREND_FILTER  = 0
ENABLE_ADX_FILTER    = 0
ENABLE_DASHBOARD     = 0
ENABLE_AUDIT_LOG     = 0
ENABLE_LOGS          = 0
AUTOTRADE_INPUT      = 0 (nao bloqueia mais desde v1.2.1; gate real = botao Algoritmos)

[GATE_ENTRADA]
ALGO_TRADING_BUTTON  = PENDENTE (usuario precisa ativar 'Algoritmos' no MT5, verde)

[NOTAS]
- Nenhum parametro de risco/filtro/estrategia foi alterado.
- Proibido alterar SignalCore.mqh e Dashboard.mqh durante as etapas 20.2-20.7.
- Este arquivo e o commit fab96b0 formam o ponto de recuperacao oficial.
