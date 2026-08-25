// XAU_AI_PRO v1.2.0
#ifndef CONFIG_MQH
#define CONFIG_MQH

//==================================================
// GERAL
//==================================================
input bool   AutoTrade          = true;
input long   MagicNumber        = 2026001;
input string TradeComment       = "XAU_AI_PRO";

//==================================================
// RISCO
//==================================================
input bool   UseRiskManagement  = true;
input double LotSize            = 0.01;
input double RiskPercent        = 1.0;

input double MaxDailyLossPercent= 5.0;
input double MaxDrawdownPercent = 15.0;
input double MinEquityPercent   = 10.0;  // Equity minima (% do balance) para operar

input double MinFreeMargin      = 20.0;  // Margem livre minima (moeda da conta)

input int    MaxTradesPerDay    = 20;
input int    MaxOpenPositions   = 5;

// v1.3.0 (Etapa 3): quando o risco configurado exige lote abaixo do
// minimo do broker. true = opera no minimo (comportamento antigo,
// risco real maior que o configurado). false = estrito, bloqueia.
input bool   AllowMinLotOverride = true;

//==================================================
// EXECUCAO
//==================================================
// MaxSpread (pontos) - limite de spread por simbolo.
// Antes 30.0: em backtest/M15 o GOLD# tem spread ~31,
// o que fazia o ValidateTrade bloquear com
// "[VALIDATION] BLOCK | SPREAD | GOLD# | 31.00/30.00".
// Ajustado para 50.0 para tolerar o spread normal do ouro
// (~30-40 pips) mantendo protecao contra spread anormal.
input double MaxSpread          = 50;
// Limites de spread POR SIMBOLO (pontos), separados por virgula.
// Formato: "SIMBOLO:limite,SIMBOLO:limite"
// Crypto (BTCUSD#, ETHUSD#) tem spread natural alto em pontos
// (~345-1500+), por isso usa limite proprio bem maior.
// Simbolos nao listados usam MaxSpread (fallback).
input string MaxSpreadBySymbol  = "GOLD#:350,BTCUSD#:600,ETHUSD#:600";

//==================================================
// GET MAX SPREAD BY SYMBOL
// Retorna o limite de spread especifico do simbolo
// ou o fallback MaxSpread se nao configurado.
//==================================================
double GetMaxSpread(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   string list = MaxSpreadBySymbol;
   StringTrimLeft(list);
   StringTrimRight(list);
   if(list == "")
      return MaxSpread;

   string entries[];
   int n = StringSplit(list, ',', entries);
   for(int i = 0; i < n; i++)
   {
      string kv[];
      int k = StringSplit(entries[i], ':', kv);
      if(k == 2)
      {
         string sym = kv[0];
         StringTrimLeft(sym);
         StringTrimRight(sym);
         string val = kv[1];
         StringTrimLeft(val);
         StringTrimRight(val);
         if(StringCompare(sym, symbol, false) == 0)
            return StringToDouble(val);
      }
   }
   return MaxSpread;
}
input int    Slippage           = 5;

//==================================================
// ORDER RETRY v1.2.0
// Parametros centralizados de retry de ordens.
//==================================================
input int    RetryMaxAttempts       = 5;
input int    RetryBaseDelayMs       = 100;
input double RetryDelayMultiplier   = 2.0;
input int    RetryMaxDelayMs        = 2000;
input int    RetryMaxSlippage       = 50;
input int    RetrySlippageIncrement = 2;


//==================================================
// STOP
//==================================================
input int StopLossPoints        = 300;
input int TakeProfitPoints      = 600;

//==================================================
// BREAK EVEN
//==================================================
input bool EnableBreakEven      = true;
input int  BreakEvenTrigger     = 80;
input int  BreakEvenOffset      = 10;

//==================================================
// TRAILING
//==================================================
input bool   EnableTrailingATR  = true;
input double ATRMultiplier      = 1.2;

//==================================================
// PARCIAL
//==================================================
input bool   EnablePartialClose = true;
input int    PartialTrigger     = 150;
input double PartialPercent     = 30.0;

//==================================================
// FILTROS
//==================================================
input bool EnableSpreadFilter      = true;
input bool EnableSessionFilter     = false;
input bool EnableTrendFilter       = true;
input bool EnableVolatilityFilter  = false;
input bool EnableADXFilter         = true;
input bool EnableMTFConfirmation   = false;
input bool EnableNewsFilter        = false;
input bool EnableAIFilter          = true;

//==================================================
// NEWS FILTER v1.3.0 (Etapa 6)
// Economic Calendar nativo MQL5 com estados
// NEWS_CLEAR/WARNING/BLOCK/ACTIVE, throttle de
// 60s e filtro por moeda.
// NewsCurrencies vazio = auto-derivacao pelo simbolo
// (XAUUSD->USD, EURUSD->EUR+USD). Lista manual tem
// prioridade sobre a auto-derivacao.
//==================================================
input string NewsCurrencies        = "";
input int    NewsImpactThreshold   = 2;        // 1=low, 2=medium, 3=high
input int    NewsMinutesBefore     = 30;
input int    NewsMinutesAfter      = 30;


//==================================================
// IA
//==================================================
input double MinAIConfidence    = 50.0;

//==================================================
// IA - JSON (v1.2.0)
//==================================================
// RequireAIJSON=false (padrao): o arquivo
// prediction_<SYMBOL>.json e opcional. Quando ausente,
// o AIEngine usa o fallback local (indicadores/score).
// Necessario para backtest, pois o pipeline Python
// nao roda dentro do Strategy Tester.
// RequireAIJSON=true: exige o JSON do pipeline Python
// para liberar o simbolo (modo producao estrito).
input bool   RequireAIJSON      = false;

//==================================================
// IA - STALENESS (ETAPA 15.3)
// Idade maxima aceita para o timestamp_utc do
// prediction JSON, em segundos. 0 = verificacao
// desativada. Previsao mais antiga que o limite
// e tratada como INDISPONIVEL (o AIEngine cai no
// fallback local ou bloqueia, conforme politica).
// Padrao 900s = 15 min (~3 candles M5).
//==================================================
input int    MaxPredictionAgeSec = 900;
//==================================================
// IA - GATE DIRECIONAL (ETAPA 20.x)
// Exige que a predicao do modelo concorde com a
// direcao do sinal tecnico (BUY/SELL) acima de um
// limiar de probabilidade. Desligado por padrao
// para preservar o baseline; ative nos testes que
// medem o impacto da IA na win-rate.
//==================================================
input bool   AIRequireDirection  = false;
input double AIMinDirectionProb  = 60.0;   // prob minima (0-100) da direcao para liberar


//==================================================
// KCI v1.2.0
// Parametros centralizados dos indicadores KCI.
//==================================================
input int    KCI_VD_Period        = 14;
input int    KCI_DX_BasePeriod    = 9;
input int    KCI_DX_ZScorePeriod  = 30;
input double KCI_DX_Sensitivity   = 1.5;
input double KCI_DX_MainThreshold = 30.0;


//==================================================
// SESSAO
//==================================================
input int TradeStartHour        = 0;
input int TradeEndHour          = 24;

//==================================================
// INDICADORES
//==================================================
input int FastEMA               = 50;
input int SlowEMA               = 200;

input int RSIPeriod             = 14;

//==================================================
// SINAL PULLBACK v1.2.0
// Niveis de RSI (vela fechada) para entrada por pullback:
//  - BUY  exige RSI fechado ABAIXO de RSIPullbackBuy  (dip na tendencia de alta)
//  - SELL exige RSI fechado ACIMA  de RSIPullbackSell (rally na tendencia de baixa)
// Valores 40/60 = mais seletivo (menos sinais, maior qualidade)
// Valores 45/55 = moderado (padrao)
// Valores 50/50 = comportamento antigo (muito permissivo)
//==================================================
input double RSIPullbackBuy     = 45.0;
input double RSIPullbackSell    = 55.0;

input int ATRPeriod             = 14;
input int ADXPeriod             = 14;

input double MinimumADX         = 18.0;

//==================================================
// SCHEDULER v1.2.0
// Agendador interno: intervalo de execucao + shutdown de fim de semana.
//==================================================
input bool   EnableScheduler       = true;
input int    SchedulerIntervalSec  = 60;
input bool   EnableWeekendShutdown = true;

//==================================================
// DATABASE / TELEMETRY v1.2.0
// Integracao com DatabaseManager,
// TradeLogger e Statistics.
//==================================================
input bool   EnableDatabase        = false;
input string DatabasePath          = "XAU_AI_PRO.db";
input bool   EnableTelemetry       = true;


//==================================================
// DATASET
//==================================================
input bool EnableDataset        = true;
input bool SaveDatasetCSV       = true;
input bool EnableBacktestLog    = true;

//==================================================
// DASHBOARD
//==================================================
input bool EnableDashboard      = true;
input bool EnableLogs           = true;
input bool DebugTradeDecision   = true;

//==================================================
// MONITORING & AUDITORIA (ETAPA 6)
// HealthMonitor absorveu o WatchDog (heartbeat dos
// modulos ATR/ADX/RSI/AI/PYTHON/CSV/JSON).
// AuditLog absorveu o FullAudit (registro estruturado
// de entrada/saida por ticket em Data\full_audit.csv).
//==================================================
input bool EnableHealthMonitor   = true;   // HealthMonitor + WatchDog integrado
input int  HealthCheckInterval   = 60;     // segundos entre health checks completos
input int  HealthWatchdogInterval= 120;    // segundos sem heartbeat para contar falha
input bool EnableAuditLog        = true;   // Auditoria (decisoes + full audit)
input bool EnableDiagnostics     = true;   // Diagnostico completo no OnInit

//==================================================
// REPLAY & BACKUP (ETAPA 7)
// ReplayEngine: reproduz decisoes/eventos historicos
// sem interferir na execucao real (REPLAY != LIVE).
// BackupManager: snapshots em FILE_COMMON + local,
// com wildcards, manifesto e restauracao validada.
//==================================================
input bool   EnableReplay          = false;  // REPLAY: reproduz historico, bloqueia trades reais
input string ReplayDatasetFile     = "Data\\trades_dataset.csv"; // decisoes (Dataset.mqh export)
input string ReplayOHLCFile        = "Data\\dataset.csv";        // OHLC/tick (DataLogger.mqh)
input string ReplayAuditFile       = "Data\\full_audit.csv";     // entradas/saidas (AuditLog.mqh)
input string ReplaySymbolFilter    = "";     // vazio = todos; ex: "XAUUSD" ou "GOLD#"
input bool   EnableBackupManager   = true;   // Backup automatico dos dados do EA
input int    BackupIntervalMinutes = 60;     // 0 = somente manual (OnInit)
input int    BackupMaxKeep         = 10;     // snapshots mantidos (limpeza automatica)

//==================================================
// BACKTEST ANALYZER & BENCHMARK (ETAPA 8)
// BacktestAnalyzer: registra cada trade do tester
// em BacktestReport.csv e calcula metricas (win rate,
// profit factor, drawdown, sharpe, expectativa).
// BenchmarkEngine: compara estrategias (Technical,
// AI, Hybrid, Ensemble) e elege a melhor.
//==================================================
input bool EnableBacktestAnalyzer = true;   // ANALISE: log + metricas de backtest
input bool EnableBenchmark        = true;   // BENCHMARK: comparacao de estrategias

//==================================================
// NOTIFICATION CENTER (ETAPA 9)
// Camada de observabilidade (Push nativo + Telegram).
// NUNCA bloqueia o trading: falha de notificacao apenas
// conta e registra, sem interferir no fluxo do EA.
//==================================================
input bool   EnableNotifications     = true;   // Central de notificacoes
input bool   NotifyPushEnabled       = true;   // Push nativo MT5 (SendNotification)
input string NotifyTelegramToken     = "";     // Token do bot Telegram (vazio = OFF)
input string NotifyTelegramChatID    = "";     // Chat ID do Telegram
input int    NotifyCooldownSec       = 30;     // cooldown entre mensagens (mesma categoria)
input int    NotifyMaxPerMinute      = 10;     // limite anti-spam global
input bool   NotifyTradeEvents       = true;   // notificar abertura/fechamento
input bool   NotifyErrors            = true;   // notificar erros
input bool   NotifyDrawdown          = true;   // notificar drawdown
input double NotifyDrawdownThreshold = 5.0;    // % minimo de drawdown para alertar
input bool   NotifyHealth            = true;   // notificar falha de HealthMonitor
input bool   NotifyCircuitBreaker    = true;   // notificar Circuit Breaker / SAFE
input bool   NotifyExecutionFailures = true;   // notificar rejeicoes de ordem

//==================================================
// MULTI SYMBOL
//==================================================
input bool EnableMultiSymbol    = true;

input string Symbols=
"XAUUSD,"    // Conta DEMO - nomes reais sem sufixo
"EURUSD,"
"GBPUSD,"
"USDJPY,"
"AUDUSD,"
"USDCAD,"
"NZDUSD,"
"USDCHF,"
"XAGUSD,"
"US30,"
"US500,"
"USTEC";

//==================================================
// DEBUG - NAO ALTERE
//==================================================
input bool EnableVerboseDebug    = true;  // Logs detalhados para debug

#endif
