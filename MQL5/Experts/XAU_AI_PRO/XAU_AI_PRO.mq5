// recompile-trigger 19:40:47
//==================================================
// XAU_AI_PRO v1.2.0
//==================================================

#property strict
#property version "1.20"

#include <Trade/Trade.mqh>

CTrade trade;


//==================================================
// CORE
//==================================================

#include "Core/Config.mqh"
// ETAPA 15.6: EventEmitter - camada unica de eventos (forward_test_events.csv)
#include "Monitoring/EventEmitter.mqh"
#include "Core/StateMachine.mqh"   // v1.4.0 (Etapa 4): maquina de estados
#include "Core/RiskCenter.mqh"     // ETAPA 15.5: Risk Control Center (fachada unica de risco)
#include "Core/SystemManager.mqh"
#include "Core/BrokerConfig.mqh"
#include "Core/BrokerInfo.mqh"
#include "Core/EnvironmentManager.mqh"
#include "Core/CompatibilityManager.mqh"
#include "Core/PathManager.mqh"
#include "Core/TimeFrameManager.mqh"

// ETAPA 11: AuditLog ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â© incluÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­do cedo porque NewsFilter/DecisionEngine
// precisam registrar o motivo do bloqueo por noticias (AuditLogSimple).
#include "Monitoring/AuditLog.mqh"


//==================================================
// INDICATORS
//==================================================

#include "Indicators/ATR.mqh"
#include "Indicators/ADX.mqh"
#include "Indicators/RSI.mqh"
#include "Indicators/TrendStrength.mqh"
#include "Indicators/VolatilityFilter.mqh"


//==================================================
// FILTERS
//==================================================

#include "Filters/SpreadFilter.mqh"
#include "Filters/SessionFilter.mqh"
#include "Filters/TrendFilter.mqh"
#include "Filters/MultiTimeframeFilter.mqh"
#include "Filters/NewsFilter.mqh"


//==================================================
// AI
//==================================================

#include "AI/AIClient.mqh"
#include "AI/AIConnector.mqh"
#include "AI/ModelGovernance.mqh"   // ETAPA 15/16: versionamento modelo/dataset
#include "AI/AIEngine.mqh"
#include "AI/Dataset.mqh"
#include "AI/DataLogger.mqh"
#include "AI/AdaptiveWeights.mqh"


//==================================================
// SIGNAL
//==================================================

#include "Core/SignalCore.mqh"
#include "Core/DecisionEngine.mqh"
#include "Core/ValidationEngine.mqh"


//==================================================
// MANAGEMENT
//==================================================

#include "Management/BreakEven.mqh"
#include "Management/DailyRisk.mqh"
#include "Management/EquityProtection.mqh"
#include "Management/PortfolioManager.mqh"


//==================================================
// EXECUTION
//==================================================

#include "Core/RiskEngine.mqh"
#include "Core/ExecutionEngine.mqh"
#include "Core/OrderManager.mqh"
#include "Core/PositionManager.mqh"


//==================================================
// MULTI SYMBOL
//==================================================

#include "Core/SymbolValidator.mqh"
#include "Core/SymbolManager.mqh"
#include "Core/MarketScanner.mqh"
#include "Core/TradePipeline.mqh"


//==================================================
// MONITORING
//==================================================

#include "Monitoring/Dashboard.mqh"
#include "Monitoring/SystemStatus.mqh"  // ETAPA 15.6: snapshot JSON para o app
#include "Monitoring/TradeLogger.mqh"
#include "Monitoring/PerformanceAnalyzer.mqh"
#include "Monitoring/Statistics.mqh"

// ETAPA 6: Monitoring & Auditoria
#include "Monitoring/HealthMonitor.mqh"   // HealthMonitor + WatchDog integrado
#include "Monitoring/EventEmitter.mqh"    // ETAPA 15.6.1/15.6.2: event stream (canonico)
// Auditoria (AuditLog + FullAudit fundidos) - incluÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­do no top (ETAPA 11)
#include "Monitoring/Diagnostics.mqh"     // Diagnostico completo

// ETAPA 7: Data Recovery, Replay & Backup
#include "Monitoring/ReplayEngine.mqh"    // Replay de decisoes/OHLC/auditoria (REPLAY != LIVE)
#include "Monitoring/BacktestAnalyzer.mqh" // Analise de backtest + metricas (ETAPA 8)
#include "Monitoring/ProductionChecklist.mqh" // Readiness em producao (ETAPA 10)
#include "Monitoring/ValidationChecklist.mqh" // Validacao READY/WARNING/BLOCKED (ETAPA 10)


//==================================================
// ENTERPRISE
//==================================================

#include "Enterprise/SafetyManager.mqh"
#include "Enterprise/CircuitBreaker.mqh"
#include "Enterprise/RecoveryManager.mqh"
#include "Enterprise/SmartExecution.mqh"
#include "Enterprise/TradeMonitor.mqh"
#include "Enterprise/Scheduler.mqh"
#include "Enterprise/DatabaseManager.mqh"
#include "Enterprise/Telemetry.mqh"
#include "Enterprise/BackupManager.mqh"   // Backup/restore com validacao real (ETAPA 7)
#include "Enterprise/BenchmarkEngine.mqh"  // Benchmark de estrategias (ETAPA 8)
#include "Enterprise/NotificationCenter.mqh" // Central de notificacoes (ETAPA 9)
#include "Enterprise/ConfigManager.mqh"  // Perfis de config persistidos (ETAPA 10)
#include "Enterprise/VersionManager.mqh" // Versao/build/estado dos modulos (ETAPA 10)
#include "Enterprise/FailureMode.mqh"     // ETAPA 12: maquina de estados de resiliencia (SAFE/RECOVERY/RESUME)
#include "Enterprise/ConnectionGuard.mqh"

// ETAPA 14: matriz de avaliacao quantitativa (11 metricas) - passivo/observacao
#include "Monitoring/QuantValidator.mqh"

// ETAPA 13: colector de datos de sesion de forward test (reconciliacion Fase A/B/C)
#include "Monitoring/ForwardTestRunner.mqh"


//==================================================
// UTILS
//==================================================


//==================================================
// OBJETOS GLOBAIS
//==================================================


//==================================================
// ESTADO DO SISTEMA
//==================================================

bool SystemInitialized = false;
bool TradingEnabled    = true;
bool AIReady           = false;
bool DatasetReady      = false;

//==================================================
// CONTROLE DE TEMPO
//==================================================

datetime LastTick             = 0;
datetime LastBar              = 0;
datetime LastDatasetBar       = 0;
datetime LastPerformanceCheck = 0;
datetime LastHealthCheck      = 0;
datetime g_lastBackupTime     = 0;   // ETAPA 7: ultimo backup agendado
// ETAPA 9: estado da central de notificacoes
int      g_lastRejectedOrders  = 0;   // contador de rejeicoes (falhas de execucao)
bool     g_notifyHealthFailed  = false; // dedup do alerta de saude
datetime g_lastDailyReport     = 0;   // relatorio diario

//==================================================
// CONTROLE DE ORDENS
//==================================================

ulong LastOrderTicket   = 0;
ulong LastPositionTicket= 0;

int TradesToday         = 0;
int ConsecutiveLosses   = 0;
int ConsecutiveWins     = 0;

//==================================================
// PERFORMANCE
//==================================================

double DailyProfit      = 0.0;
double WeeklyProfit     = 0.0;
double MonthlyProfit    = 0.0;

double PeakEquity       = 0.0;
double CurrentDrawdown  = 0.0;

//==================================================
// IA
//==================================================

bool AIConnected        = false;
string AIStatus         = "OFFLINE";

double AIScore          = 0.0;
double AIConfidence     = 0.0;

//==================================================
// DATASET
//==================================================

int DatasetIndex        = -1;
bool DatasetUpdated     = false;

//==================================================
// DASHBOARD
//==================================================

bool DashboardCreated   = false;

//==================================================
// CIRCUIT BREAKER
//==================================================

bool SafeMode           = false;

//==================================================
// RECOVERY
//==================================================

bool RecoveryRunning    = false;

//==================================================
// SMART EXECUTION
//==================================================

bool ExecutionReady     = false;

//==================================================
// DEBUG
//==================================================

bool VerboseMode = EnableVerboseDebug;

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool InitializeModules()
  {
   Print("=================================");
   Print("Inicializando modulos...");
   Print("=================================");

   if(!InitSystem())
      return false;

// v1.2.1: cache de handles de indicadores do SignalCore
   SignalCoreInit();
   StateMachineInit();   // v1.4.0 (Etapa 4): maquina de estados
   Print("[INIT] system + signalcore OK");

   if(!InitATR())
      Print("ATR OFF");

   if(!InitADX())
      Print("ADX OFF");

   if(!InitRSI())
      Print("RSI OFF");

   if(!InitTrendFilter())
      Print("TrendFilter OFF");

   if(!InitMTF())
      Print("MTF OFF");

   if(!InitSymbolManager())
      return false;

   if(SymbolsPending)
      Print("SYMBOL MANAGER | Simbolos pendentes de sincronizacao (retry automatico ativo)");

   Print("[INIT] symbol manager OK");
   AIClientInit();
   ModelGovernanceRefresh();   // ETAPA 15/16: metadados do modelo (vazio=nao-governado)

   if(!DataLoggerInit())
      Print("DataLogger OFF");

   InitDailyRisk();

   PerformanceInit();

   CSafetyManager::Init();

   CCircuitBreaker::Init();

   CRecoveryManager::Init();
   FailureClassify(false, "Init");   // ETAPA 12: estado inicial NORMAL
   ConnectionGuardRefresh();         // ETAPA 12: guard de conexao pronta

   CSmartExecution::Init();
   Print("[INIT] execution engine OK");

//------------------------------------------------
// v1.2.0 - TRADE LOGGER / DATABASE / SCHEDULER / STATISTICS
//------------------------------------------------

   if(!InitTradeLogger())
      Print("TradeLogger OFF");

   CDatabaseManager::Init();

   if(EnableDatabase)
     {
      CDatabaseManager::Connect();
      CDatabaseManager::LogStatus();
     }

   CScheduler::Init();

   if(EnableScheduler)
     {
      // Registra tarefa de rotina diaria (ex.: backup)
      CScheduler::LogStatus();
     }

   StatisticsInit();
   Print("[INIT] all modules OK");

//------------------------------------------------
// ETAPA 6 - MONITORING & AUDITORIA
//------------------------------------------------

   if(EnableHealthMonitor)
     {
      HealthMonitorInit();

      // Heartbeat inicial dos modulos
      HealthMonitorHeartbeat("ATR");
      HealthMonitorHeartbeat("ADX");
      HealthMonitorHeartbeat("RSI");
      HealthMonitorHeartbeat("AI");

      if(EnableDataset)
        {
         HealthMonitorHeartbeat("CSV");
         HealthMonitorHeartbeat("JSON");
         HealthMonitorHeartbeat("PYTHON");
        }
     }

   if(EnableAuditLog)
     {
      if(!AuditLogInit())
         Print("[AUDIT] AuditLog OFF");
     }

   if(EnableDiagnostics)
     {
      bool diagOK = DiagnosticsRun();
      Print(diagOK ? "[DIAG] TODOS OS TESTES PASSARAM" : "[DIAG] FALHAS DETECTADAS (ver log)");
     }

//------------------------------------------------
// v1.2.0 - TELEMETRY
//------------------------------------------------

   if(EnableTelemetry)
     {
      CTelemetry::Init();
      CTelemetry::RecordBrokerLatency(0);
      CTelemetry::RecordExecutionStart();  // ETAPA 15.6.3: uptime real

      //------------------------------------------------
      // ETAPA 7 - REPLAY & BACKUP
      //------------------------------------------------

      //------------------------------------------------
      // ETAPA 8 - BACKTEST ANALYZER & BENCHMARK
      //------------------------------------------------

      if(EnableBacktestAnalyzer)
        {
         if(!BacktestInit())
            Print("[BACKTEST] BacktestAnalyzer OFF");
        }

      if(EnableBenchmark)
        {
         CBenchmarkEngine::Init();
        }

      //------------------------------------------------
      // ETAPA 9 - NOTIFICATION CENTER
      //------------------------------------------------

      if(EnableNotifications)
        {
         CNotificationCenter::Init();
         CNotificationCenter::SetPushEnabled(NotifyPushEnabled);

         if(NotifyTelegramToken != "" && NotifyTelegramChatID != "")
            CNotificationCenter::SetTelegram(NotifyTelegramToken, NotifyTelegramChatID);

         CNotificationCenter::SetCooldown(NCAT_TRADE_OPEN, NotifyCooldownSec);
         CNotificationCenter::SetCooldown(NCAT_TRADE_CLOSE, NotifyCooldownSec);
         CNotificationCenter::SetCooldown(NCAT_HEALTH, 600);
         CNotificationCenter::SetCooldown(NCAT_CIRCUIT, 300);
         CNotificationCenter::SetCooldown(NCAT_EXECUTION, 300);
         CNotificationCenter::SetCooldown(NCAT_DRAWDOWN, 600);
         CNotificationCenter::SetMaxPerMinute(NotifyMaxPerMinute);

         Print("[NOTIFY] " + CNotificationCenter::GetStatus());
   }

   //------------------------------------------------
   // ETAPA 10 - CONFIG MANAGER + VERSION MANAGER
   //------------------------------------------------

   CConfigManager::Init();
   CConfigManager::SetProfile(CConfigManager::GetCurrentProfile());
   CConfigManager::LogStatus();

   CVersionManager::Init();
   CVersionManager::RegisterModules();
   CVersionManager::LogStatus();

   //------------------------------------------------
   // ETAPA 10 - PRODUCTION + VALIDATION CHECKLISTS
   //------------------------------------------------

   CProductionChecklist::Init();
   CProductionChecklist::Run();
   ValidationChecklistRun();

      if(EnableBackupManager)
        {
         CBackupManager::Init();
        }

      if(EnableReplay)
        {
         if(ReplayEngineInit())
           {
            if(ReplaySymbolFilter != "")
               ReplayEngineSetSymbolFilter(ReplaySymbolFilter);

            Print("[REPLAY] MODO REPLAY ATIVO | trades reais BLOQUEADOS | origem=", ReplayEngineSource());
           }
         else
           {
            Print("[REPLAY] Falha ao inicializar replay (operacao normal)");
           }
        }
     }
   return true;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void ShutdownModules()
  {
   ReleaseTrendFilter();

   ReleaseATR();

   ReleaseADX();

   ReleaseRSI();

   ReleaseMTF();

// v1.2.1: libera handles cacheados do SignalCore
   ReleaseSignalHandles();

   DataLoggerClose();

   AIClientShutdown();

   CloseTradeLogger();

   CDatabaseManager::Disconnect();

   ShutdownSystem();
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void UpdatePerformance()
  {
//==================================================
// PERFORMANCE UPDATE
//
// NAO chama ProcessClosedTrades() aqui.
//
// O registro de trades fechados e responsabilidade
// exclusiva de OnTradeTransaction() (evento por deal),
// evitando duplicidade em RegisterTradePerformance().
//
// Antes, ProcessClosedTrades() reprocessava as ultimas
// 24h a cada tick, somando o mesmo profit multiplas
// vezes e inflando DailyProfit / ConsecutiveWins /
// ConsecutiveLosses.
//==================================================

   DailyProfit =
      AccountInfoDouble(
         ACCOUNT_PROFIT
      );

   double equity =
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );

   if(equity > PeakEquity)
      PeakEquity = equity;

   if(PeakEquity > 0.0)
     {
      CurrentDrawdown =
         (
            (PeakEquity - equity)
            /
            PeakEquity
         )
         * 100.0;
     }
   else
     {
      CurrentDrawdown = 0.0;
     }
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void UpdateSafety()
  {
   CSafetyManager::UpdateStats();

   CCircuitBreaker::Run();

   CRecoveryManager::Run();
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void UpdateDataset()
  {
   if(!EnableDataset)
      return;

   datetime candle =
      iTime(
         _Symbol,
         PERIOD_CURRENT,
         0
      );

   if(candle==LastDatasetBar)
      return;

   LastDatasetBar=candle;

   int total=TotalSymbols();

   for(int i=0;i<total;i++)
     {
      string symbol=
         GetTradeSymbol(i);

      if(symbol!="")
         SaveMarketData(symbol);
     }
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void UpdateDashboard()
  {
   if(!EnableDashboard)
      return;

   DashboardUpdate();
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool CheckTradingConditions()
  {
   if(!TradingEnabled)
      return false;

   if(!CheckEquityProtection())
      return false;

   if(!CSafetyManager::CheckAll())
      return false;

   if(!CCircuitBreaker::CanTrade())
      return false;

   return true;
  }

// FUNCOES AUXILIARES AUSENTES
//==================================================

// Processa trades fechados para atualizar performance
void ProcessClosedTrades()
  {
   datetime from = TimeCurrent() - 86400; // ultimas 24h
   if(!HistorySelect(from, TimeCurrent()))
      return;

   int deals = HistoryDealsTotal();
   for(int i = 0; i < deals; i++)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;

      if(HistoryDealGetInteger(deal, DEAL_ENTRY) != DEAL_ENTRY_OUT)
         continue;

      if(HistoryDealGetInteger(deal, DEAL_MAGIC) != MagicNumber)
         continue;

      double profit = HistoryDealGetDouble(deal, DEAL_PROFIT);
      RegisterTradePerformance(profit);
     }
  }

// Atualiza o estado do cliente IA (fallback local)
void UpdateAIStatus()
  {
// IA local - apenas mantem o estado atualizado
   if(EnableAIFilter)
     {
      AIReady = AIClientConnected();
      AIStatus = AIReady ? "ONLINE" : "OFFLINE";
     }
  }

// Salva as estatisticas de performance em arquivo
void PerformanceSave()
  {
   int handle = FileOpen("XAU_AI_PRO_stats.csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
      return;

   FileWrite(handle, "metric,value");
   FileWrite(handle, "TradesToday", TradesToday);
   FileWrite(handle, "ConsecutiveWins", ConsecutiveWins);
   FileWrite(handle, "ConsecutiveLosses", ConsecutiveLosses);
   FileWrite(handle, "DailyProfit", DoubleToString(DailyProfit, 2));
   FileWrite(handle, "PeakEquity", DoubleToString(PeakEquity, 2));
   FileWrite(handle, "CurrentDrawdown", DoubleToString(CurrentDrawdown, 2));
   FileClose(handle);
  }

//==================================================
// ON INIT
//==================================================

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int OnInit()
  {
   Print("========================================");
   Print("        XAU_AI_PRO v1.2.0");
   Print("========================================");

   Print("Conta.............: ", AccountInfoInteger(ACCOUNT_LOGIN));
   Print("Corretora.........: ", AccountInfoString(ACCOUNT_COMPANY));
   Print("Servidor..........: ", AccountInfoString(ACCOUNT_SERVER));
   Print("Simbolo...........: ", _Symbol);
   Print("Saldo.............: ", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2));
   Print("Equity............: ", DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));

   trade.SetExpertMagicNumber(MagicNumber);
      trade.SetDeviationInPoints(Slippage);

   ForwardFileInit(); // ETAPA 13: abre CSV de sesion de forward test (FILE_COMMON)

   // ETAPA 15.6: EventEmitter (canal oficial de eventos)
   EventInit();
   EventSystemStart("mode=live chart=" + _Symbol);
   EventForwardStart("forward test ativo");

   if(!InitializeModules())
     {
      Print("ERRO: Falha ao inicializar modulos.");
      return INIT_FAILED;
     }

   PeakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   EventSetTimer(30);   // executa a cada 30 segundos

   SystemInitialized = true;

   Print("----------------------------------------");
   Print("Sistema inicializado com sucesso.");
   Print("----------------------------------------");


   return INIT_SUCCEEDED;
  }


//==================================================
// ON TICK
//==================================================

//==================================================
// THROTTLE DE LOG (v1.2.0)
// Evita spam de "[TRADE BLOCK]" no OnTick.
//==================================================
datetime g_lastBlockPrint = 0;

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool AllowBlockPrint()
  {
   datetime now = TimeCurrent();
   if(now - g_lastBlockPrint >= 60)
     {
      g_lastBlockPrint = now;
      return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnTick()
  {
//------------------------------------------------
// Telemetria real: contador de ticks (ETAPA 15.6.3)
//------------------------------------------------

   CTelemetry::RecordTick();

//------------------------------------------------
// Sistema inicializado?
//------------------------------------------------

      if(!SystemInitialized)
     {
      Print("[TRADE BLOCK] SYSTEM NOT INITIALIZED");
      return;
     }

   // ETAPA 13 - heartbeat de sesion live (1Hz via throttle interno).
   // Corre SEMPRE que recibe tick, incluso cando bloqueado, para monitorizar
   // estado de conexion/failure_mode/news/IA no forward test.
   ForwardHeartbeat();



//------------------------------------------------
//------------------------------------------------
// Health Monitor (ETAPA 6)
//------------------------------------------------

   if(EnableHealthMonitor)
     {
      HealthMonitorUpdateTicks();
      HealthMonitorHeartbeat("ATR");
      HealthMonitorHeartbeat("ADX");
      HealthMonitorHeartbeat("RSI");
      HealthMonitorHeartbeat("AI");
     }
//------------------------------------------------
// ETAPA 15.6 - EventEmitter: HEALTH + AI_BLOCK
//------------------------------------------------
   static bool g_lastEventHealthOK = true;
   bool _hOk = HealthMonitorCheck();
   if(!_hOk && g_lastEventHealthOK)
     {
      EventHealthFailure("HealthMonitor", "check falhou");
      g_lastEventHealthOK = false;
     }
   else
   if(_hOk && !g_lastEventHealthOK)
     {
      EventRecovery("health restaurado");
      g_lastEventHealthOK = true;
     }

   if(AI_Signal == "UNAVAILABLE" || AI_Signal == "ERROR" || AI_Signal == "HOLD")
     {
      static datetime g_lastEventAIBlock = 0;
      datetime _now = TimeCurrent();
      if(_now - g_lastEventAIBlock >= 300)
        {
         EventAIBlock(_Symbol, "AI_" + AI_Signal);
         g_lastEventAIBlock = _now;
        }
     }

//------------------------------------------------
// Algo Trading do terminal habilitado? (v1.2.1)
//------------------------------------------------
//------------------------------------------------

   if(!MQLInfoInteger(MQL_TRADE_ALLOWED) || !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
     {
      if(AllowBlockPrint())
         Print("[TRADE BLOCK] ALGO TRADING OFF | Ative o botao 'Algoritmos' no MT5 (Ferramentas > Opcoes > Expert Advisors)");
      return;
     }

//------------------------------------------------
// AutoTrade (input) - v1.2.0
//------------------------------------------------

   if(false)   // v1.2.1: AutoTrade nao bloqueia mais (controle = botao Algoritmos do terminal)
     {
      // v1.2.1 - throttle do log
      if(AllowBlockPrint())
         Print("[TRADE BLOCK] AUTOTRADE OFF | Ative AutoTrade=true no EA");
      return;
     }

//------------------------------------------------
// Retry de simbolos pendentes (abertura do terminal)
//------------------------------------------------

   if(SymbolsPending)
     {
      UpdateSymbolManager();
      if(SymbolsPending)
         return;
     }

   LastTick = TimeCurrent();

//------------------------------------------------
// Circuit Breaker
//------------------------------------------------

   CCircuitBreaker::Run();

   if(!CCircuitBreaker::CanTrade())
     {
      if(AllowBlockPrint())
         Print("[TRADE BLOCK] CIRCUIT BREAKER | State=", CCircuitBreaker::GetStateString(), " | Reason=", CCircuitBreaker::GetTriggerReason());
      return;
     }

//------------------------------------------------
// Recovery
//------------------------------------------------

   CRecoveryManager::Run();

//------------------------------------------------
// Safety
//------------------------------------------------

   if(!CSafetyManager::CheckAll())
     {
      if(AllowBlockPrint())
         Print("[TRADE BLOCK] SAFETY | ", CSafetyManager::GetSafetySummary());
      return;
     }

//------------------------------------------------
// Equity Protection
//------------------------------------------------

   if(!CheckEquityProtection())
     {
      if(AllowBlockPrint())
         Print("[TRADE BLOCK] EQUITY PROTECTION");
      return;
     }

//------------------------------------------------
// Atualiza Performance
//------------------------------------------------

   UpdatePerformance();

//------------------------------------------------
// Atualiza IA
//------------------------------------------------

   if(EnableAIFilter)
     {
      UpdateAIStatus();
     }

//------------------------------------------------
// Atualiza Dataset
//------------------------------------------------

   UpdateDataset();

//------------------------------------------------
// Health Monitor - heartbeat dataset/python (ETAPA 6)
//------------------------------------------------

   if(EnableHealthMonitor && EnableDataset)
     {
      HealthMonitorHeartbeat("CSV");
      HealthMonitorHeartbeat("JSON");
      HealthMonitorHeartbeat("PYTHON");
     }

//------------------------------------------------
// Scanner Multi Symbol
//------------------------------------------------

   if(EnableVerboseDebug)
      Print("[TRADE PIPELINE] INICIANDO");

   StateSet("", STATE_MARKET_SCAN);   // v1.4.0 (Etapa 4)

// ETAPA 7 - SEPARACAO ABSOLUTA REPLAY vs LIVE
   if(EnableReplay && ReplayEngineBlocksLiveTrading())
     {
      if(AllowBlockPrint())
         Print("[REPLAY] Modo replay ativo - execucao real BLOQUEADA");
     }
   else
   if(!ConnectionGuardCanOperate())
     {
      if(AllowBlockPrint())
         Print("[TRADE BLOCK] CONNECTION | ", ConnectionGuardGetError());
     }
   else
   if(!FailureModeOperational())
     {
      if(AllowBlockPrint())
         Print("[TRADE BLOCK] FAILURE MODE | State=", GetFailureStateString(), " | Reason=", g_failureReason);
     }
   else
     {
      RunTradePipeline();
     }

   // ETAPA 12 (HARDENING): guard de conexao e failure mode bloqueiam
   // NOVAS ENTRADAS sem parar a gestao de posicoes abertas.

//------------------------------------------------
// Gerenciamento das posicoes
//------------------------------------------------

   ManagePositions();

//------------------------------------------------
// v1.4.0 (Etapa 4): posicoes abertas -> MANAGING
//------------------------------------------------

   for(int pi = PositionsTotal() - 1; pi >= 0; pi--)
     {
      ulong pt = PositionGetTicket(pi);
      if(pt == 0)
         continue;
      if(!PositionSelectByTicket(pt))
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      StateSet(PositionGetString(POSITION_SYMBOL), STATE_MANAGING);
     }

//------------------------------------------------
// Dashboard
//------------------------------------------------

   UpdateDashboard();

  }

//==================================================
// ON TRADE TRANSACTION
//==================================================

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnTradeTransaction(
   const MqlTradeTransaction &trans,
   const MqlTradeRequest &request,
   const MqlTradeResult &result
)
  {
//------------------------------------------------
// Apenas DEALS
//------------------------------------------------

   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;

   ulong deal = trans.deal;

   if(deal == 0)
      return;

   if(!HistoryDealSelect(deal))
      return;

//------------------------------------------------
// v1.2.2 - FILTRO MAGIC + DEDUP INTER-INSTANCIA
//------------------------------------------------

   long dealMagic = HistoryDealGetInteger(deal, DEAL_MAGIC);
   if(dealMagic != MagicNumber)
      return;

   string gvDeal = "XAI_PRO_DEAL_" + IntegerToString((long)deal);
   if(MQLInfoInteger(MQL_TESTER)==0 && GlobalVariableCheck(gvDeal))
      return;
   if(MQLInfoInteger(MQL_TESTER)==0)
      GlobalVariableSet(gvDeal, 1.0);

   string symbol =
      HistoryDealGetString(
         deal,
         DEAL_SYMBOL
      );

   double profit =
      HistoryDealGetDouble(
         deal,
         DEAL_PROFIT
      );

   double volume =
      HistoryDealGetDouble(
         deal,
         DEAL_VOLUME
      );

   ENUM_DEAL_ENTRY entry =
      (ENUM_DEAL_ENTRY)
      HistoryDealGetInteger(
         deal,
         DEAL_ENTRY
      );

//------------------------------------------------
// Entrada
//------------------------------------------------

   if(entry == DEAL_ENTRY_IN)
     {
      TradesToday++;

      // v1.4.0 (Etapa 4): maquina de estados
      StateSet(symbol, STATE_POSITION_OPEN);

      // ETAPA 15.6: evento de abertura
      EventTradeOpen(symbol, (long)deal, DoubleToString(volume,2));

      Print(
         "TRADE OPEN | ",
         symbol,
         " | LOT=",
         DoubleToString(volume,2)
      );

      //------------------------------------------------
      // v1.2.0 - POSITION SYNC + DATABASE
      //------------------------------------------------

      CSmartExecution::Synchronize();

      if(EnableDatabase)
        {
         int type = 0;
         CDatabaseManager::Connect();

         CDatabaseManager::InsertTrade(
            deal,
            symbol,
            type,
            volume,
            HistoryDealGetDouble(deal, DEAL_PRICE),
            TimeCurrent(),
            TradeComment
         );
        }

      StatisticsRegisterTrade(0.0);

      // ETAPA 15/16 - registra modelo usado neste trade (auditoria)
      ModelLogTradeUsage((ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID), symbol);   // ETAPA 15/16

      //------------------------------------------------
      // ETAPA 6 - AUDITORIA (entrada)
      //------------------------------------------------

      if(EnableAuditLog)
        {
         ENUM_DEAL_TYPE dType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE);
         ulong positionId = HistoryDealGetInteger(deal, DEAL_POSITION_ID);

         double spread = 0.0;
         double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
         double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
         double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

         if(ask > 0.0 && bid > 0.0 && point > 0.0)
            spread = (ask - bid) / point;

         AuditLogTrackEntry(
            symbol,
            positionId,
            HistoryDealGetDouble(deal, DEAL_PRICE),
            GetATR(symbol),
            GetADX(symbol),
            GetRSI(symbol),
            0.0,
            spread,
                        IsTradingSession() ? "OPEN" : "CLOSED",
            (dType == DEAL_TYPE_BUY) ? "BUY" : "SELL",
            AIConfidence,
            AIScore,
            "ENTRY_DEAL"
         );

         // ETAPA 13 - forward test: registra entrada de posicion
         ForwardLogTrade(symbol, "OPEN",
            (dType == DEAL_TYPE_BUY) ? 1 : -1,
            MarketScore,
            DoubleToString(AIConfidence, 2),
            (dType == DEAL_TYPE_BUY) ? "BUY" : "SELL",
            HistoryDealGetDouble(deal, DEAL_VOLUME),
            HistoryDealGetDouble(deal, DEAL_PRICE),
            HistoryDealGetDouble(deal, DEAL_SL),
            HistoryDealGetDouble(deal, DEAL_TP),
            positionId,
            "OPEN",
            0,
            "");
        }

      //------------------------------------------------
      // ETAPA 8 - BACKTEST ANALYZER (entrada)
      //------------------------------------------------

      if(BacktestIsReady())
        {
         ENUM_DEAL_TYPE bType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE);
         double bAsk = SymbolInfoDouble(symbol, SYMBOL_ASK);
         double bBid = SymbolInfoDouble(symbol, SYMBOL_BID);
         double bPoint = SymbolInfoDouble(symbol, SYMBOL_POINT);
         double bSpread = 0.0;

         if(bAsk > 0.0 && bBid > 0.0 && bPoint > 0.0)
            bSpread = (bAsk - bBid) / bPoint;

         BacktestLog(
            (bType == DEAL_TYPE_BUY) ? 1 : -1,
            HistoryDealGetDouble(deal, DEAL_PRICE),
            volume,
            bSpread,
            GetATR(symbol),
            GetADX(symbol),
            GetRSI(symbol),
            AIScore,
            "OPEN"
         );
        }

      //------------------------------------------------
      // ETAPA 9 - NOTIFICACAO (entrada)
      //------------------------------------------------

      if(EnableNotifications && NotifyTradeEvents)
        {
         ENUM_DEAL_TYPE nType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE);

         CNotificationCenter::SendTradeOpen(
            symbol,
            volume,
            HistoryDealGetDouble(deal, DEAL_PRICE),
            (nType == DEAL_TYPE_BUY) ? "BUY" : "SELL"
         );
        }

      return;
     }

//------------------------------------------------
// Saida
//------------------------------------------------

   if(entry == DEAL_ENTRY_OUT)
     {
      //------------------------------------------------
      // Performance
      //------------------------------------------------

      RegisterTradePerformance(profit);

      // v1.4.0 (Etapa 4): maquina de estados
      StateSet(symbol, STATE_CLOSED);
      StateSet(symbol, STATE_LEARNING);

      // ETAPA 15.6: evento de fechamento
      EventTradeClose(symbol, (long)deal, DoubleToString(profit,2));

      //------------------------------------------------
      // Estatisticas
      //------------------------------------------------

      if(profit > 0)
        {
         ConsecutiveWins++;
         ConsecutiveLosses=0;
        }
      else
        {
         ConsecutiveLosses++;
         ConsecutiveWins=0;
        }

      //------------------------------------------------
      // Dataset
      //------------------------------------------------

      if(EnableDataset)
        {
         UpdateDatasetResult(
            DatasetIndex,
            (profit>0)
         );
        }

      //------------------------------------------------
      // Feedback IA
      //------------------------------------------------

      if(EnableAIFilter)
        {
         LogAIFeedback(
            symbol,
            profit
         );
        }

      //------------------------------------------------
      // Smart Execution
      //------------------------------------------------

      CExecutionStats::UpdateAfterTrade(
         profit
      );

      //------------------------------------------------
      // Dashboard
      //------------------------------------------------

      DashboardUpdate();

      //------------------------------------------------
      // Log
      //------------------------------------------------

      Print(
         "TRADE CLOSED | ",
         symbol,
         " | PROFIT=",
         DoubleToString(
            profit,
            2
         )
      );

      //------------------------------------------------
      // v1.2.0 - POSITION SYNC
      //------------------------------------------------

      CSmartExecution::Synchronize();

      //------------------------------------------------
      // v1.2.0 - TRADE LOGGER
      //------------------------------------------------

      if(tradeLoggerHandle != INVALID_HANDLE)
        {
         // Usa DEAL_TYPE (mais confiavel em DEAL_ENTRY_OUT,
         // pois a posicao pode ja estar fechada).
         ENUM_DEAL_TYPE dealType =
            (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE);
         bool isBuy = (dealType == DEAL_TYPE_BUY);

         LogTradeCSV(
            isBuy,
            HistoryDealGetDouble(deal, DEAL_PRICE),
            SymbolInfoDouble(symbol, SYMBOL_BID),
            profit,
            AIScore
         );
        }

      //------------------------------------------------
      // v1.2.0 - DATABASE
      //------------------------------------------------

      if(EnableDatabase)
        {
         CDatabaseManager::Connect();

         CDatabaseManager::UpdateTrade(
            deal,
            SymbolInfoDouble(symbol, SYMBOL_BID),
            TimeCurrent(),
            profit,
            HistoryDealGetDouble(deal, DEAL_COMMISSION),
            HistoryDealGetDouble(deal, DEAL_SWAP)
         );
        }

      //------------------------------------------------
      // v1.2.0 - STATISTICS
      //------------------------------------------------

      StatisticsRegisterTrade(profit);

      // ETAPA 14 - matriz quantitativa: registra resultado p/ Avg R
      QuantRecordResult(profit, 0.0);

      //------------------------------------------------
      // ETAPA 6 - AUDITORIA (saida)
      //------------------------------------------------

      if(EnableAuditLog)
        {
         ulong positionId = HistoryDealGetInteger(deal, DEAL_POSITION_ID);

         AuditLogTrackExit(
            positionId,
            (profit > 0.0 ? "WIN" : "LOSS"),
            profit
         );

                  AuditLogTradeResult(
            symbol,
            positionId,
            profit,
            (profit > 0.0 ? "WIN" : "LOSS")
         );

         // ETAPA 13 - forward test: registra saida/close de posicion
         {
          ENUM_DEAL_TYPE exType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE);
          ForwardLogDeal(symbol,
             positionId,
             (exType == DEAL_TYPE_BUY) ? 1 : -1,
             MarketScore,
             DoubleToString(AIConfidence, 2),
             (exType == DEAL_TYPE_BUY) ? "BUY" : "SELL",
             HistoryDealGetDouble(deal, DEAL_VOLUME),
             HistoryDealGetDouble(deal, DEAL_PRICE),
             profit,
             "CLOSE",
             0);
         }
        }

      //------------------------------------------------
      // ETAPA 8 - BACKTEST ANALYZER + BENCHMARK (saida)
      //------------------------------------------------

      if(BacktestIsReady())
        {
         ENUM_DEAL_TYPE outType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE);

         BacktestLogResult(
            (outType == DEAL_TYPE_BUY) ? 1 : -1,
            HistoryDealGetDouble(deal, DEAL_PRICE),
            volume,
            0.0,
            GetATR(symbol),
            GetADX(symbol),
            GetRSI(symbol),
            AIScore,
            (profit > 0.0 ? "WIN" : "LOSS"),
            profit
         );
        }

      if(EnableBenchmark)
        {
         StrategyType st = (EnableAIFilter && AIConfidence > 0.0) ? STRATEGY_HYBRID : STRATEGY_TECHNICAL;
         CBenchmarkEngine::RecordTrade(st, profit, 0.0, 0.0);
        }

      //------------------------------------------------
      // ETAPA 9 - NOTIFICACAO (saida)
      //------------------------------------------------

      if(EnableNotifications && NotifyTradeEvents)
        {
         CNotificationCenter::SendTradeClose(
            symbol,
            profit,
            (profit > 0.0 ? "WIN" : "LOSS")
         );
        }

  }
  }

//==================================================
// ON TIMER
//==================================================

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnTimer()
  {
//------------------------------------------------
// Sistema inicializado?
//------------------------------------------------

   if(!SystemInitialized)
      return;

//------------------------------------------------
// Retry de simbolos pendentes
//------------------------------------------------

   if(SymbolsPending)
      UpdateSymbolManager();

   CRecoveryManager::Run();

   // ETAPA 12 - failure mode (recuperacion automatica)
   bool fBrokerOK = CRecoveryManager::IsModuleHealthy("Broker");
   bool fAiOK     = CRecoveryManager::IsModuleHealthy("AI");
   FailureModeFeed(fBrokerOK, fAiOK);
   FailureModeRun();

//------------------------------------------------
// Circuit Breaker
//------------------------------------------------

   CCircuitBreaker::Run();

//------------------------------------------------
// Safety
//------------------------------------------------

   CSafetyManager::UpdateStats();

//------------------------------------------------
// Atualizacao IA
//------------------------------------------------

   if(EnableAIFilter)
     {
      UpdateAIStatus();
     }

//------------------------------------------------
// Sincronizar posicoes
//------------------------------------------------

   CSmartExecution::Synchronize();

//------------------------------------------------
// Scheduler (v1.2.0)
//------------------------------------------------

   if(EnableScheduler)
     {
      CScheduler::Run();
     }

//------------------------------------------------
// Atualizar Dashboard
//------------------------------------------------

   if(EnableDashboard)
     {
      DashboardUpdate();
     }

//------------------------------------------------
// System Status Snapshot (ETAPA 15.6)
// JSON para o app: health/trading/risk/ai/news/
// python/database. Throttle interno de 15s.
//------------------------------------------------

   SystemStatusUpdate();

//------------------------------------------------
// Salvar estatisticas
//------------------------------------------------

   PerformanceSave();

//------------------------------------------------
// Health Monitor + Auditoria (ETAPA 6)
//------------------------------------------------

   if(EnableHealthMonitor)
     {
      HealthMonitorCheck();

      if(EnableVerboseDebug)
        {
         Print("========== HEALTH MONITOR ==========");
         Print(HealthMonitorSummary());
         Print(EnableAuditLog ? AuditLogSummary() : "AuditLog OFF");
         Print("====================================");
        }
     }

   if(EnableAuditLog)
     {
      AuditLogFlush();

      //------------------------------------------------
      // Backup agendado (ETAPA 7)
      //------------------------------------------------

      if(EnableBackupManager && BackupIntervalMinutes > 0)
        {
         if(TimeCurrent() - g_lastBackupTime >= BackupIntervalMinutes * 60)
           {
            g_lastBackupTime = TimeCurrent();

            bool bkOK = CBackupManager::RunBackup();

            Print("[BACKUP] ", bkOK ? "OK" : "FAIL", " | copiados=", CBackupManager::GetLastFilesCopied(), " | falhas=", CBackupManager::GetLastFilesFailed());
           }
        }
     }

//------------------------------------------------
//------------------------------------------------
// ETAPA 9 - NOTIFICATION CENTER (alertas periodicos)
//------------------------------------------------

   if(EnableNotifications)
     {
      // HealthMonitor
      if(NotifyHealth && EnableHealthMonitor)
        {
         bool healthy = HealthMonitorCheck();
         if(!healthy && !g_notifyHealthFailed)
           {
            g_notifyHealthFailed = true;
            CNotificationCenter::SendHealthAlert(HealthMonitorSummary());
           }
         if(healthy)
            g_notifyHealthFailed = false;
        }

      // Circuit Breaker / SAFE
      if(NotifyCircuitBreaker && !CCircuitBreaker::CanTrade())
        {
         CNotificationCenter::SendCircuitBreaker(
            CCircuitBreaker::GetStateString(),
            CCircuitBreaker::GetTriggerReason()
         );
        }

      // Drawdown
      if(NotifyDrawdown && CurrentDrawdown >= NotifyDrawdownThreshold)
        {
         CNotificationCenter::SendDrawdown(CurrentDrawdown);
        }

      // Falhas de execucao (rejeicoes de ordem)
      if(NotifyExecutionFailures)
        {
         int rej = CExecutionStats::GetStats().rejected;
         if(rej > g_lastRejectedOrders)
           {
            g_lastRejectedOrders = rej;
            CNotificationCenter::SendExecutionFailure(_Symbol, "ordem rejeitada (total=" + IntegerToString(rej) + ")");
           }
        }

      // Relatorio diario (1x/dia)
      if(TimeCurrent() - g_lastDailyReport >= 86400)
        {
         g_lastDailyReport = TimeCurrent();
         CNotificationCenter::SendDailyReport(DailyProfit, TradesToday, 0.0);
        }
     }

// Health Check
//------------------------------------------------

   if(EnableVerboseDebug)
     {
      Print("========== SYSTEM STATUS ==========");
      Print(CRecoveryManager::GetHealthSummary());
      Print(CSmartExecution::GetExecutionSummary());
      Print(CSafetyManager::GetSafetySummary());
      Print("==================================");
     }
  }

//==================================================
// ON DEINIT
//==================================================

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnDeinit(
   const int reason
)
  {
   // ETAPA 15.6.1: ultimo evento do event stream (API canonica)
   EventSystemStop("deinit_reason=" + IntegerToString(reason));
   EventShutdown();

   Print(
      "========================================"
   );

   Print(
      "XAU_AI_PRO FINALIZANDO"
   );

   Print(
      "Reason=",
      reason
   );

//================================================
// PARAR TIMER
//================================================

// ETAPA 15.6: sinaliza parada no event stream
   EventSystemStop("reason=" + IntegerToString(reason));
   EventShutdown();

// v1.2.0 - SALVAR RESUMO (win rate) em FILE_COMMON
   StatisticsSaveSummary();
   QuantSaveReport();   // ETAPA 14: matriz quantitativa (FILE_COMMON)
   Print(QuantSummary());

   EventKillTimer();


//================================================
// DESABILITAR SISTEMA
//================================================

   SystemInitialized=false;

   TradingEnabled=false;


//================================================
// SHUTDOWN DOS MODULOS
//================================================

   ShutdownModules();

//================================================
// MONITORING & AUDITORIA (ETAPA 6)
//================================================

   if(EnableHealthMonitor)
      HealthMonitorShutdown();

      if(EnableAuditLog)
      AuditLogClose();

   ForwardLogClose(); // ETAPA 13: pecha CSV de sesion de forward test (flush+close)

//================================================
// REPLAY (ETAPA 7)
//================================================

   if(EnableReplay)
      ReplayEngineClose();

//================================================
// ETAPA 8 - BACKTEST ANALYZER + BENCHMARK
//================================================

   if(EnableBacktestAnalyzer)
      BacktestClose();

   if(EnableBenchmark)
      CBenchmarkEngine::LogComparison();

//================================================
// ETAPA 9 - NOTIFICATION CENTER (encerramento)
//================================================

   if(EnableNotifications)
     {
      if(reason == REASON_INITFAILED)
         CNotificationCenter::SendError("EA", "falha na inicializacao");

      CNotificationCenter::SendSystemAlert("EA finalizado (reason=" + IntegerToString(reason) + ")");
      CNotificationCenter::LogStatus();
   }

   //================================================
   // ETAPA 10 - CONFIG + VERSION (encerramento)
   //================================================

   CConfigManager::LogStatus();
   CVersionManager::LogStatus();


//================================================
// LOG FINAL
//================================================

   Print(
      "XAU_AI_PRO FINALIZADO"
   );

   Print(
      "========================================"
   );
  }

//+------------------------------------------------------------------+
