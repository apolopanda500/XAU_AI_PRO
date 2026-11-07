//==================================================
// XAU_AI_PRO v1.2.167
//==================================================

#property strict
// v1.2.27 (30/10/2026) - HG-02: este bloco mandava procurar a versao em
// `VERSION` na raiz, em `scripts/sync_version.py` e em `Docs/version.json`.
// Nenhum dos tres existe nesta arvore, logo descrevia um mecanismo morto.
// Fonte unica real: `EA_VERSION_STRING` em `Enterprise/VersionManager.mqh`,
// publicada no journal pela linha `[VERSION]` do arranque.
//
// Dois formatos convivem aqui, por exigencia do compilador:
//   * texto semantico "1.2.27" -> `EA_VERSION_STRING`, `EV_VERSION_STRING`
//     e o log `[VERSION]`;
//   * `#property version` aceita SO `xxx.yyy` (dois numeros), por isso a
//     identidade numerica e minor*100 + patch: 1.2.27 -> "1.227". Sem isso o
//     MetaEditor emite `warning 68: version ... is incompatible with MQL5
//     Market` e o produto deixa de passar a validacao do catalogo.
// A versao legivel ("1.2.27") vai na descricao do projeto (XAU_AI_PRO.mqproj),
// tambem exibida na aba de propriedades. O build do projeto ja injeta essa
// propriedade; repetir com `#property description` gera `warning 90`.
#property version   "1.380"

#include <Trade/Trade.mqh>

CTrade trade;


//==================================================
// CORE
//==================================================

#include "Core/Config.mqh"
#include "Core/MCPServer.mqh"      // ETAPA MCP: servidor MCP (Model Context Protocol)
// v1.2.115: expoe funcionalidades do EA para IA externa (risco, sinais, saude, contas, posicoes)
#include "Monitoring/AccountLogGate.mqh"   // v1.2.91 P1.78: um facto por CONTA
// P1.61 (v1.2.75): fonte unica de verdade das permissoes de negociacao.
// Incluido logo apos Config, antes de qualquer modulo que possa negociar.
#include "Core/TradeGate.mqh"
// F2.1 (v1.2.176): kill switch do PLANO_10_10. Incluido DEPOIS de
// <Trade/Trade.mqh> (usa CTrade) e de Monitoring/AccountLogGate.mqh (usa
// AccountLogGatePodeImprimir), e antes de qualquer modulo que negocie.
#include "Core/KillSwitch.mqh"
#include "Core/StalenessGuard.mqh"
// v1.2.42 (31/10/2026) P1.17: portao de diagnostico do journal. Incluido
// logo apos Config para estar disponivel a TODOS os modulos seguintes
// (StateMachine, RiskEngine, ExecutionEngine). Nao depende de inputs.
#include "Monitoring/DiagGate.mqh"
// ETAPA 15.6: EventEmitter - camada unica de eventos (forward_test_events.csv)
#include "Monitoring/EventEmitter.mqh"
#include "Core/StateMachine.mqh"   // v1.4.0 (Etapa 4): maquina de estados
#include "Core/RiskCenter.mqh"     // ETAPA 15.5: Risk Control Center (fachada unica de risco)
#include "Core/SystemManager.mqh"
#include "Core/BrokerConfig.mqh"
#include "Core/BrokerInfo.mqh"
#include "Core/EnvironmentManager.mqh"
#include "Core/RealAccountGuard.mqh"   // v1.2.37 P1.10: endurecimento de conta REAL
#include "Core/CompatibilityManager.mqh"
#include "Core/PathManager.mqh"
#include "Core/TimeFrameManager.mqh"

// ETAPA 11: o AuditLog e incluido cedo porque NewsFilter/DecisionEngine
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
#include "Filters/MarketIntelligence.mqh"


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
#include "AI/LearningHistory.mqh"   // v1.2.10: aprendizado persistente (manual + EA)
#include "Core/SessionState.mqh"    // v1.2.10: contadores/pico sobrevivem a recarga


//==================================================
// SIGNAL
//==================================================

#include "Core/SignalCore.mqh"
// Signal Core v2 (paralelo): seletor SignalCoreVersion + GetActiveSignal.
// Modulo paralelo ao v1 por decisao propria do autor: nao altera RiskHub,
// SafetyManager, ExecutionEngine nem a gestao de posicoes.
#include "Core/SignalCoreV2.mqh"
// Ponte somente leitura EA -> Gateway -> App. Grava
// XAU_AI_PRO_heartbeat.json em FILE_COMMON, consumido por backend/ea_manager.py.
#include "Integration/EAHeartbeat.mqh"
#include "Integration/ExternalBridge.mqh"
#include "Core/DecisionEngine.mqh"
#include "Core/ValidationEngine.mqh"


//==================================================
// MANAGEMENT
//==================================================

#include "Management/BreakEven.mqh"
#include "Management/MoneyLadder.mqh"
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
// v1.2.91 (02/11/2026) - P1.78: o portao de conta passou para o topo do EA,
// logo a seguir ao Core/Config.mqh, para que qualquer modulo possa chamar
// AccountLogGatePodeImprimir sem repetir o #include em cada .mqh.
#include "Monitoring/SystemStatus.mqh"  // ETAPA 15.6: snapshot JSON para o app
#include "Monitoring/TradeLogger.mqh"
#include "Monitoring/Logger.mqh"          // v1.2.95: LoggerInit() no OnInit
// P2.11: desligado por omissao (Monitoring/TradeLoggerSQLite.mqh precisa de
// Database.mqh, que nao existe). Ver o cabecalho desse ficheiro.
#ifdef XAI_USE_TRADELOG_SQLITE
#include "Monitoring/TradeLoggerSQLite.mqh"  // v1.2.116: SQLite nativo para histórico de trades
#endif   // XAI_USE_TRADELOG_SQLITE
#include "Monitoring/PerformanceAnalyzer.mqh"
#include "Monitoring/Statistics.mqh"
#include "Monitoring/OperatorBrief.mqh"   // v1.2.19: resumo periodico para o operador

// ETAPA 6: Monitoring & Auditoria
#include "Monitoring/HealthMonitor.mqh"   // HealthMonitor + WatchDog integrado
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
// FREIO DE SEQUENCIA PERDEDORA (v1.2.20)
//==================================================
datetime g_streakBrakeUntil = 0;   // fim da pausa (0 = sem pausa)
datetime g_streakBrakeLogAt = 0;   // throttle do log de bloqueio

// true = pode abrir novas entradas. false = pausa por sequencia perdedora
// ainda em curso. Nunca interfere na gestao das posicoes ja abertas.
bool StreakBrakeAllowsEntry()
  {
   if(!EnableStreakBrake || StreakBrakeLosses <= 0 || StreakBrakePauseMinutes <= 0)
      return(true);

   if(g_streakBrakeUntil == 0)
      return(true);

   datetime agora = TimeCurrent();

   if(agora >= g_streakBrakeUntil)
     {
      g_streakBrakeUntil = 0;
      ConsecutiveLosses  = 0;
      Print("[STREAK] pausa encerrada | novas entradas liberadas");
      return(true);
     }

   if(agora - g_streakBrakeLogAt >= 300)
     {
      g_streakBrakeLogAt = agora;
      Print("[TRADE BLOCK] STREAK | perdas seguidas=", ConsecutiveLosses,
            " | pausa ate ", TimeToString(g_streakBrakeUntil, TIME_DATE|TIME_MINUTES));
     }

   return(false);
  }

// Chamado a cada perda fechada: arma/renova a pausa ao atingir o limite.
void StreakBrakeOnLoss()
  {
   if(!EnableStreakBrake || StreakBrakeLosses <= 0 || StreakBrakePauseMinutes <= 0)
      return;

   if(ConsecutiveLosses < StreakBrakeLosses)
      return;

   datetime agora = TimeCurrent();
   datetime ate   = agora + (StreakBrakePauseMinutes * 60);

   if(ate <= g_streakBrakeUntil)
      return;

   g_streakBrakeUntil = ate;

   Print("[STREAK] FREIO ARMADO | perdas seguidas=", ConsecutiveLosses,
         " | sem novas entradas por ", StreakBrakePauseMinutes, " min",
         " | ate ", TimeToString(ate, TIME_DATE|TIME_MINUTES));
  }

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

bool VerboseMode = (EnableVerboseDebug && !MQLInfoInteger(MQL_TESTER));   // v1.2.35: verbose OFF no tester

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool InitializeModules()
  {
   // v1.2.89 (02/11/2026) - P1.76: "Inicializando modulos..." nao trazia
   // um dado e saia 16x por arranque; o [INIT] all modules OK diz o mesmo
   // com o resultado a frente.

   if(!InitSystem())
      return false;

// v1.2.1: cache de handles de indicadores do SignalCore
   SignalCoreInit();
   SignalCoreV2Init();   // modulo paralelo (SignalCoreVersion)
   EAHeartbeatWrite("RUNNING");
   StateMachineInit();   // v1.4.0 (Etapa 4): maquina de estados
   if(AccountLogGatePodeImprimir("init_base", 3600))
      Print("[INIT] system + signalcore OK");

   if(!InitATR())
      Print("[INIT] ATR OFF");

   if(!InitADX())
      Print("[INIT] ADX OFF");

   if(!InitRSI())
      Print("[INIT] RSI OFF");

   if(!InitTrendFilter())
      Print("[INIT] TrendFilter OFF");

   if(!InitMTF())
      Print("[INIT] MTF OFF");

   if(!InitSymbolManager())
      return false;

   if(SymbolsPending)
      Print("[SYMS] Simbolos pendentes de sincronizacao (retry automatico ativo)");

   if(AccountLogGatePodeImprimir("init_syms", 3600))
      Print("[INIT] symbol manager OK");
   AIClientInit();
   ModelGovernanceRefresh();   // ETAPA 15/16: metadados do modelo (vazio=nao-governado)

   if(!DataLoggerInit())
      Print("[INIT] DataLogger OFF");

   InitDailyRisk();

   PerformanceInit();

   CSafetyManager::Init();

   CCircuitBreaker::Init();

   CRecoveryManager::Init();
   FailureClassify(false, "Init");   // ETAPA 12: estado inicial NORMAL
   ConnectionGuardRefresh();         // ETAPA 12: guard de conexao pronta

   CSmartExecution::Init();
   if(AccountLogGatePodeImprimir("init_exec", 3600))
      Print("[INIT] execution engine OK");

//------------------------------------------------
// v1.2.0 - TRADE LOGGER / DATABASE / SCHEDULER / STATISTICS
//------------------------------------------------

   if(!InitTradeLogger())
      Print("[INIT] TradeLogger OFF");

   CDatabaseManager::Init();

   if(EnableDatabase)
     {
      CDatabaseManager::Connect();
      CDatabaseManager::LogStatus();
     }

   CScheduler::Init();

   // v1.2.10: restaura a memoria de aprendizado do disco e importa o
   // historico real da conta (operacoes manuais + operacoes do EA).
   AILearningInit();

   if(EnableScheduler)
     {
      // Registra tarefa de rotina diaria (ex.: backup)
      CScheduler::LogStatus();
     }

   StatisticsInit();
   if(AccountLogGatePodeImprimir("init_all", 3600))
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
      // v1.2.109 (03/11/2026) - P1.97: o else pertencia ao if INTERNO, nao ao
      // if(diagOK). MEDIDO no journal de 03/11 as 05:45 do servidor, XAUUSD:
      // o mesmo arranque imprimia "[STATUS] HEALTHY | 6 modulos OK |
      // Overall=RECOVERY_OK" e, dois segundos depois, "[DIAG] FALHAS
      // DETECTADAS" sem NENHUM [DIAG] FALHA a seguir - porque todos os testes
      // passaram e o que era falso era apenas o portao de impressao
      // LogInicioDetalhe() (falso nos graficos que nao sao o primeiro do
      // reload). A linha de falha era portanto impressa exactamente quando
      // NAO havia falha. Passa a haver chavetas e o else fica ligado ao
      // if(diagOK), que e o que o texto sempre quis dizer.
      if(diagOK)
      {
         if(LogInicioDetalhe()) Print("[DIAG] TODOS OS TESTES PASSARAM");
      }
      else
      {
         Print("[DIAG] FALHAS DETECTADAS");
         DiagnosticsPrintFailures();
      }
     }

//------------------------------------------------
// v1.2.0 - TELEMETRY
//------------------------------------------------

   if(EnableTelemetry)
     {
      CTelemetry::Init();
      CTelemetry::RecordBrokerLatency(0);
      CTelemetry::RecordExecutionStart();  // ETAPA 15.6.3: uptime real
     }

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

      if(AccountLogGatePodeImprimir("notify", 3600))
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
// F2.1 (v1.2.176) - KILL SWITCH: estado no arranque
//------------------------------------------------
// Sem esta linha, um EA que arranca ARMADO (ficheiro esquecido de uma paragem
// anterior) ficava calado a nao negociar e o operador procurava o defeito no
// sitio errado. Publica sempre, mesmo quando LIVRE, porque "LIVRE" e a
// informacao que autoriza confiar no silencio seguinte.
   if(AccountLogGatePodeImprimir("killswitch_arranque", XAI_KS_LOG_SEC))
      Print("[KILL SWITCH] estado no arranque | ", CKillSwitch::Estado());

//------------------------------------------------
// ETAPA MCP - SERVIDOR MCP (Model Context Protocol)
//------------------------------------------------
   if(EnableMCPServer)
     {
      // P2.16 (03/11/2026): o token literal esteve versionado em Core/Config.mqh
      // (publico no GitHub) e o servidor MCP embutido arrancava com ele nos 15
      // graficos - medido em "[MCP] servidor ativo | metodos=7/7 ..." as 21:44:59.
      // O codigo deixa de ter segredo (input privado do grafico) e o valor antigo
      // e recusado aqui, sem depender de reconfigurar os 15 graficos a mao.
      if(MCPServerToken == "xau-mcp-local-2026")
        {
         if(AccountLogGatePodeImprimir("mcp_publico", 3600))
            Print("[MCP] DESATIVADO | token literal publico recusado | ",
                  "defina um token privado no input MCPServerToken");
        }
      else
        {
         MCPServer.Init(MCPServerToken);
         if(MCPServer.IsEnabled())
           {
            if(AccountLogGatePodeImprimir("mcp", 3600))
               Print("[MCP] servidor ativo | metodos=", MCPServer.SelfTest());   // P2.08: prova de vida
           }
         else
           {
            if(AccountLogGatePodeImprimir("mcp_fail", 3600))
               Print("[MCP] nao arrancou | token com ", StringLen(MCPServerToken),
                     " caracteres, minimo ", MCP_MIN_TOKEN_LEN, " (input MCPServerToken)");
           }
        }
     }

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
   SignalCoreV2Release();   // libera handles do modulo paralelo
   EAHeartbeatWrite("STOPPED");

   DataLoggerClose();

   AIClientShutdown();

   CloseTradeLogger();

   CDatabaseManager::Disconnect();

   if(EnableMCPServer)
      MCPServer.LogRequest("SHUTDOWN", true);

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
// F4/1.2: retorna TRUE apenas com progresso REAL (nova vela detectada),
// para que HealthMonitorProgress seja chamado somente com avance verificado.
bool UpdateDataset()
  {
   if(!EnableDataset)
      return false;

   datetime candle =
      iTime(
         _Symbol,
         PERIOD_CURRENT,
         0
      );

   if(candle==LastDatasetBar)
      return false;   // sem nova vela => sem progresso

   LastDatasetBar=candle;

   int total=TotalSymbols();

   for(int i=0;i<total;i++)
     {
      string symbol=
         GetTradeSymbol(i);

      if(symbol!="")
         SaveMarketData(symbol);
     }

   return true;   // nova vela processada => progresso real do pipeline
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

// v1.2.10: grava trades do dia, sequencia e pico de equity (por conta e dia)
void SessionStateStore()
{
   static datetime g_lastSessionSave=0;
   datetime agoraSession=TimeCurrent();

   if(g_lastSessionSave>0 && (agoraSession-g_lastSessionSave)<300)
      return;

   g_lastSessionSave=agoraSession;

   if(!EnableSessionStatePersistence)
      return;

   EASessionState st;

   st.tradesToday   = TradesToday;
   st.consecWins    = ConsecutiveWins;
   st.consecLosses  = ConsecutiveLosses;
   st.peakEquity    = PeakEquity;

   if(!SessionStateSave(st))
      return;

   EASessionState chk;

   if(SessionStateLoad(chk))
     {
      // v1.2.83 (02/11/2026) - P1.70: MEDIDO no Logs de 02/11 - 3 181 linhas
      // "[SESSION] estado salvo" (2,3 por cento do journal), 16 instancias a
      // repetir a MESMA linha (trades=1 | W=0 | L=0 | pico=12535.64) a cada
      // 5 minutos. Agora so imprime quando o resumo MUDA, com heartbeat de
      // 30 min para se saber que a gravacao continua viva.
      static string   sUltimoResumoSession = "";
      static datetime sUltimoLogSession    = 0;
      string resumoSession = SessionStateSummary(chk);
      datetime agoraSessao = TimeCurrent();
      // P1.73: MEDIDO - 16 instancias imprimiam o MESMO "estado salvo" (no
      // rollover de 03/11 foram 12 linhas iguais em 40 s). A condicao passou
      // a incluir a janela por CONTA: 1 linha a cada 10 min no maximo.
      bool sessaoQuerLog = (resumoSession != sUltimoResumoSession || (agoraSessao - sUltimoLogSession) >= 3600);

      if(sessaoQuerLog && AccountLogGatePodeImprimir("session", 600))
        {
         sUltimoResumoSession = resumoSession;
         sUltimoLogSession    = agoraSessao;
         Print("[SESSION] estado salvo | ",resumoSession);
        }
     }
}

// v1.2.10: restaura o estado da sessao. PeakEquity so herda o pico do MESMO
// dia; em dia novo o pico recomeca no equity atual (drawdown e intradiario).
void SessionStateRestore()
{
   EASessionState st;

   if(!SessionStateLoad(st))
   {
      SessionStateStore();
      return;
   }

   TradesToday       = st.tradesToday;
   ConsecutiveWins   = st.consecWins;
   ConsecutiveLosses = st.consecLosses;

   if(st.peakEquity > PeakEquity)
      PeakEquity = st.peakEquity;

   if(LogInicioDetalhe()) Print("[SESSION] estado restaurado | ",SessionStateSummary(st),
         " | pico_atual=",DoubleToString(PeakEquity,2));
}

// Salva as estatisticas de performance em arquivo
void PerformanceSave()
  {
   // v1.2.124 (03/11/2026) - P2.16: MEDIDO por leitura de codigo no varrimento
   // de FileOpen com FILE_WRITE: este era o ULTIMO ponto do EA sem partilha.
   // O ficheiro XAU_AI_PRO_stats.csv esta em Files (pasta comum a todas as
   // instancias do terminal) e e reescrito por cada grafico, logo a abertura
   // em corrida devolvia 5004 e a funcao saia em silencio sem gravar. Passa a
   // pedir FILE_SHARE_READ | FILE_SHARE_WRITE e a repetir 3x com Sleep(10),
   // que e o mesmo padrao ja usado no AuditLog, no SystemStatus e no
   // BackupManager. Nenhum contador, limite, regra de entrada ou de saida,
   // lote, spread, alvo, precificacao ou parametro de risco muda: muda apenas
   // se a gravacao deste retrato de estatisticas consegue abrir o ficheiro.
   int handle = INVALID_HANDLE;

   for(int tentativaStats = 0; tentativaStats < 3; tentativaStats++)
     {
      handle = FileOpen("XAU_AI_PRO_stats.csv",
                        FILE_WRITE | FILE_CSV | FILE_ANSI |
                        FILE_SHARE_READ | FILE_SHARE_WRITE, ',');

      if(handle != INVALID_HANDLE)
         break;

      Sleep(10);
     }

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
   // v1.2.87 (02/11/2026) - P1.74: eram 9 linhas (3 separadores + 6 campos)
   // por arranque, 144 num reload dos 16 graficos. Passam a UMA linha.
   Print("[START] XAU_AI_PRO v", EA_VERSION_STRING,
         " | conta=", AccountInfoInteger(ACCOUNT_LOGIN),
         " | ", AccountInfoString(ACCOUNT_COMPANY), "/", AccountInfoString(ACCOUNT_SERVER),
         " | simbolo=", _Symbol,
         " | saldo=", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),
         " | equity=", DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));

   // v1.2.95 (02/11/2026) - P1.83: o logger de ficheiro nunca era aberto
   // porque LoggerInit() nao era chamado em lado nenhum. Medido no journal
   // de 02/11: 1 366 linhas "[LOGGER OFFLINE]" e 284 registos importantes
   // descartados so na ultima hora. Passa a abrir AGORA, com ficheiro por
   // grafico (symbol+period), e o fallback deixa de ser o caminho normal.
   LoggerInit();

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(Slippage);
   // v1.2.55 (P1.32): o CTrade da biblioteca standard imprime em INFO cada
   // OrderSend/modify e cada 'position modified'. Medido no run 1 287 596 linhas:
   // 32 505 + 13 187 = 45 692 linhas (3,55 por cento) que repetem o que o proprio
   // EA ja registra com o retcode. Aqui so ficam os ERROS da biblioteca; nenhuma
   // regra de execucao muda, so a verbosidade.
   trade.LogLevel(LOG_LEVEL_ERRORS);

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

   // v1.2.37 P1.10: publica no journal o que o guarda de conta REAL esta a fazer.
   RealGuardLogBanner();
   PeakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   // v1.2.10: recupera trades do dia, sequencia e PICO de equity do mesmo dia
   SessionStateRestore();
//------------------------------------------------
// F2.9 (v1.2.179) - FONTE UNICA do limite de frescura
//------------------------------------------------
// EnableStaleDataGuard/MaxSymbolTickAgeSec ja eram as inputs do
// SymbolDataFresh() do MarketScanner. O guarda do OnTick/OnTimer passa a
// ler as MESMAS, em vez de carregar 120 s escondidos no codigo: uma
// pergunta, uma resposta. Sem esta chamada o guarda usa o valor de recurso.
   CStalenessGuard::Configurar(EnableStaleDataGuard, MaxSymbolTickAgeSec);
   EventSetTimer(30);   // executa a cada 30 segundos

   SystemInitialized = true;

   // Ponte app -> EA: recupera o ultimo request_id processado, para um
   // comando nao ser reexecutado depois de reattach. Inerte se desligada.
   ExternalBridgeInit();

   if(LogSessaoPodeImprimir("init_pronto_" + _Symbol))
   Print("[INIT] pronto | simbolo=", _Symbol, " | timer=30s");


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
//| v1.2.81 (02/11/2026) - P1.68: journal legivel, sem repeticao.      |
//| O gate antigo deixava sair o MESMO [TRADE BLOCK] 1x/60 s por       |
//| grafico: medido no Logs de 02/11, 7 272 linhas com a mesma causa.  |
//| Agora a CAUSA e a chave: causa nova imprime na hora, causa igual   |
//| sai 1x/10 min. Nao decide nada, so decide se a linha volta a sair. |
// v1.2.85 (02/11/2026) - P1.72: MEDIDO na janela 17:40-18:44 do Logs de
// 02/11 (872 linhas): 117 eram ESTA linha com a MESMA causa, 16 instancias
// a 1/10 min. O bit por programa nao se cura sozinho e a causa ja sai por
// inteiro, logo a janela passou a 1x/hora: 117/h -> ~19/h. Causa NOVA
// continua a sair na hora. Decide apenas se a linha volta a ser escrita.
//+------------------------------------------------------------------+
string   g_lastBlockCausa     = "";
datetime g_lastBlockCausaHora = 0;

bool AllowBlockPrintCausa(string causa)
  {
   datetime agora = TimeLocal();
   if(causa != g_lastBlockCausa)
     {
      g_lastBlockCausa     = causa;
      g_lastBlockCausaHora = agora;
      g_lastBlockPrint     = agora;
      // P1.73: causa NOVA continua a sair na hora, mas so uma vez por CONTA
      // a cada 2 min - o reload dos 16 graficos escrevia a mesma causa 16x.
      return AccountLogGatePodeImprimir("tradeblock_nova", 120);
     }
   if(agora - g_lastBlockCausaHora >= 3600)
     {
      g_lastBlockCausaHora = agora;
      g_lastBlockPrint     = agora;
      // P1.73: MEDIDO - a 1x/hora POR INSTANCIA o journal voltava a ter 16
      // linhas/hora com o MESMO texto (16 graficos). A janela passou a ser
      // por CONTA: 1 linha/hora no total.
      return AccountLogGatePodeImprimir("tradeblock", 3600);
     }
   return false;
  }

//+------------------------------------------------------------------+
//| JournalOneLine: colapsa um retrato multi-linha numa linha so.     |
//| Usado pelos retratos periodicos (STATUS e HEALTH) para que o      |
//| journal tenha os MESMOS numeros em 1 linha em vez de 14 ou 20.    |
//+------------------------------------------------------------------+
string JournalOneLine(string texto)
  {
   StringReplace(texto, "\r\n", " | ");
   StringReplace(texto, "\n", " | ");
   StringReplace(texto, "\r", " | ");
   for(int i = 0; i < 8; i++)
      StringReplace(texto, " |  | ", " | ");
   for(int i = 0; i < 8; i++)
      StringReplace(texto, "| |", "|");
   return texto;
  }

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

// Ponte app -> EA (Integration/ExternalBridge.mqh). Throttle interno de 1 Hz e
// duas comparacoes quando desligada. So leitura: nao manda ordem.
   ExternalBridgePoll();



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
// Portao de negociacao (v1.2.75: 5 bits, fonte unica)
//------------------------------------------------

//------------------------------------------------
// F2.1 (v1.2.176) - KILL SWITCH: precedencia sobre todos os portoes
//------------------------------------------------
// MEDIDO em 06/11/2026: nao existia neste EA nenhum interruptor accionavel
// por uma pessoa (busca por KillSwitch|Halt|Freeze|Panic|EmergencyStop em toda
// a arvore: zero ocorrencias). O PLANO_10_10 F2.1 exige-o e o GATE F2 e
// bloqueante para conta real.
// Este teste vem ANTES do portao de permissoes de proposito:
//  (1) quem manda parar quer ver a PARAGEM como primeira causa no journal, e
//      nao uma linha [TRADE BLOCK] que sugere que o problema e do terminal;
//  (2) e o que torna o interruptor observavel enquanto o P0 mantem
//      MQL_TRADE_ALLOWED=0 nos 13 graficos - sem isto, o kill switch ficaria
//      atras de um portao fechado e nao se podia provar que funciona.
   if(CKillSwitch::Verificar(MagicNumber, true))
      return;

   ETradeGate tradeGate = CTradeGate::Evaluate();

   if(tradeGate != TG_OK)
     {
      if(AllowBlockPrintCausa(CTradeGate::Cause(tradeGate)))
         Print("[TRADE BLOCK] ", CTradeGate::Cause(tradeGate), " | ", CTradeGate::Bits());

      // P1.83 (v1.2.95): portao fechado barra NEGOCIACAO, nao barra LEITURA.
      // Sem esta chamada o journal fica vazio e nao ha como saber o que
      // bloqueia (ver o comentario de ReadOnlyScanTick em MarketScanner.mqh).
      ReadOnlyScanTick((int)tradeGate);

      return;
     }

//------------------------------------------------
// AutoTrade (input) - RELIGADO em 05/10/2026
//------------------------------------------------
// Antes era `if(false)`, com o comentario "AutoTrade nao bloqueia mais
// (controle = botao Algoritmos do terminal)". O input existia em
// `Config.mqh:8`, aparecia na aba Inputs do MT5 e NUNCA era lido.
//
// MEDIDO em 02/11 as 08:34: quem barra o trade e o portao acima, que le os
// CINCO bits em `Core/TradeGate.mqh` (MQL_TRADE_ALLOWED, TERMINAL_TRADE_ALLOWED,
// ACCOUNT_TRADE_ALLOWED, ACCOUNT_TRADE_EXPERT, TERMINAL_CONNECTED) e nomeia a
// causa. CircuitBreaker, SafetyManager e EquityProtection continuam a ser
// gates independentes e NAO substituem o portao.
// O `AutoTrade` e o UNICO ponto em que o operador desliga o EA sem fechar
// o MT5 — e ele estava inerte.
//
// Deixar assim e pior do que nao existir: o painel mostra um interruptor que
// nao faz nada, e o operador acredita que parou o sistema quando nao parou.
// Este bloco nao substitui os gates; e o interruptor que eles nao cobrem.
//
//------------------------------------------------
// F2.9 (v1.2.178) - COTACAO VELHA NAO OPERA
//------------------------------------------------
// O portao de permissoes le TERMINAL_CONNECTED. Estar LIGADO ao servidor
// nao e o mesmo que estar a RECEBER precos: um feed congelado, um simbolo
// suspenso ou uma sessao que fechou deixam o bit a 1 e a ultima cotacao
// parada. Decidir sobre um preco parado nao e operar, e adivinhar - e o
// resultado e uma entrada com preco e spread de um mercado que ja nao
// existe. Fail-closed: sem leitura de tick tambem nao opera.
   if(CStalenessGuard::CotacaoVelha(_Symbol))
     {
      static datetime g_lastEventStale = 0;
      datetime _agoraStale = TimeLocal();   // relogio do PC: avanca mesmo sem ticks
      if(_agoraStale - g_lastEventStale >= 300)
        {
         if(AllowBlockPrint())
            Print("[TRADE BLOCK] COTACAO VELHA | ", CStalenessGuard::Diagnostico(_Symbol), " | preco parado nao opera");
         g_lastEventStale = _agoraStale;
        }
      return;
     }

   if(!AutoTrade)
     {
      static datetime g_lastEventAutoTradeBlock = 0;
      datetime _now = TimeCurrent();
      if(_now - g_lastEventAutoTradeBlock >= 300)
        {
         if(AllowBlockPrint())
            Print("[TRADE BLOCK] AUTOTRADE OFF | AutoTrade=false neste EA");
         g_lastEventAutoTradeBlock = _now;
        }
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
// Market Intelligence (sessoes, calendario, fechamento, score)
//------------------------------------------------

   UpdateMarketContext();

//------------------------------------------------
// v1.2.138 P2.24: o retrato de MARKET INTELLIGENCE estava calculado e
// nunca publicado. PrintMarketIntelligence() existia em
// Filters/MarketIntelligence.mqh e nenhum ponto do pipeline a chamava,
// logo sessao, dia, feriado, minutos para fechar, proximo evento,
// score 0-100 e o veredicto de pode negociar ficavam so na memoria.
// 1x/hora por CONTA (o mesmo portao dos outros retratos) e fora do
// tester, para os 13 graficos nao repetirem a mesma foto.
//------------------------------------------------

   if(EnableMarketIntelligence && !MQLInfoInteger(MQL_TESTER) &&
      AccountLogGatePodeImprimir("market_intel", 3600))
     {
      PrintMarketIntelligence();
     }

//------------------------------------------------
//------------------------------------------------
// Atualiza Dataset
//------------------------------------------------

   bool datasetProgressed = UpdateDataset();

//------------------------------------------------
// Health Monitor - heartbeat dataset/python (ETAPA 6)
//------------------------------------------------
// Progresso REAL (F4/1.2): HealthMonitorProgress avanza SOLO quando
// UpdateDataset reporta nova vela (datasetProgressed==true). Nunca por tick.

   if(EnableHealthMonitor && EnableDataset && datasetProgressed)
     {
      HealthMonitorProgress("CSV");
      HealthMonitorProgress("JSON");
      HealthMonitorProgress("PYTHON");
     }

//------------------------------------------------
// Scanner Multi Symbol
//------------------------------------------------

   if(EnableVerboseDebug && !MQLInfoInteger(MQL_TESTER))
      {
      // v1.2.18 (29/10/2026): 1x por minuto por grafico. Antes esta linha
      // saia A CADA TICK (dezenas por segundo) e afogava o journal: o
      // operador nao conseguia ver o que o EA estava decidindo.
      static datetime lastPipelineLog = 0;
      datetime pipelineNow = TimeCurrent();

      if(pipelineNow - lastPipelineLog >= 60)
        {
         lastPipelineLog = pipelineNow;

         // v1.2.92 (02/11/2026) - P1.79: 15 graficos x 1/minuto = 900 linhas
         // por hora com o mesmo texto. Passa a 1x/30 min por CONTA.
         if(AccountLogGatePodeImprimir("pipeline", 1800))
            Print("[TRADE PIPELINE] INICIANDO | ", _Symbol, " ", EnumToString((ENUM_TIMEFRAMES)Period()));
        }
      }

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
            if(!StreakBrakeAllowsEntry())
              {
               // v1.2.20: pausa por sequencia perdedora. Bloqueia apenas NOVAS
               // entradas; a gestao das posicoes abertas roda logo abaixo.
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

   // ETAPA 12 (HARDENING): guard de conexao e failure mode bloqueiam
// NOVAS entradas sem parar a gestao de posicoes abertas.
// PIPELINE MASTER: so a instancia dona gerencia posicoes; as demais ficam em
// standby e assumem automaticamente se o mestre cair (ver PipelineIsMaster).

   if(PipelineIsMaster())
     {
      ManagePositions();

      // RESUMO PARA O OPERADOR (v1.2.19): somente leitura. Condensa o estado
      // (master, posicoes, meta do dia, degrau da escada) em poucas linhas
      // `[RESUMO]` a cada OperatorBriefSeconds. Nao decide, nao envia ordem e
      // nao toca em SL/TP. Roda so na instancia mestre, junto da gestao.
      OperatorBriefTick(TradesToday);

      // VIA RAPIDA (29/10/2026): volume alto + preco correndo nao espera o
      // ciclo do scheduler; roda o pipeline so para os simbolos em disparada.
      // O latch "1 operacao por vela" impede entrada duplicada no candle.
      if(EnableMarketPulse)
         MarketPulseFastLane();
     }

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
//+------------------------------------------------------------------+
//| Risco em DINHEIRO de uma posicao, lido do SL do deal de entrada.  |
//| Devolve 0.0 quando o broker nao devolve SL no deal: quem consome   |
//| trata 0.0 como "nao sei" e nao inventa R.                          |
//+------------------------------------------------------------------+
double RiscoDaPosicao(ulong positionId, double volumeFechado)
  {
   if(positionId == 0 || volumeFechado <= 0.0)
      return(0.0);

   if(!HistorySelectByPosition(positionId))
      return(0.0);

   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0)
         continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;

      double sl    = HistoryDealGetDouble(d, DEAL_SL);
      double price = HistoryDealGetDouble(d, DEAL_PRICE);
      string sym   = HistoryDealGetString(d, DEAL_SYMBOL);

      if(sl <= 0.0 || price <= 0.0 || sym == "")
         return(0.0);

      double point    = SymbolInfoDouble(sym, SYMBOL_POINT);
      double tickVal  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);

      if(point <= 0.0 || tickVal <= 0.0 || tickSize <= 0.0)
         return(0.0);

      double valorPorPonto = (tickVal / tickSize) * point;
      double distancia     = MathAbs(price - sl) / point;

      return(distancia * valorPorPonto * volumeFechado);
     }

   return(0.0);
  }

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
     {
      // OPERACAO MANUAL (29/10/2026): pedido do dono - o EA aprende com o
      // historico DELE. Antes este filtro devolvia em todo deal manual
      // (magic 0), e 100% das operacoes do operador eram descartadas: o EA
      // nunca aprendia com a mao de quem opera no grafico.
      //
      // O deal manual NAO e do EA, entao nada da contabilidade propria roda
      // aqui (telemetria, dataset, auditoria, painel, contadores, forward
      // log). Apenas o aprendizado.
      ENUM_DEAL_ENTRY manualEntry =
         (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);

      if(dealMagic == 0 &&
         EnableLearningFromHistory &&
         (manualEntry == DEAL_ENTRY_OUT || manualEntry == DEAL_ENTRY_OUT_BY))
        {
         // Uma vez por deal, mesmo com varios graficos com o EA anexado.
         string gvManual = "XAI_PRO_MDEAL_" + IntegerToString((long)deal);

         if(MQLInfoInteger(MQL_TESTER) != 0 || !GlobalVariableCheck(gvManual))
           {
            if(MQLInfoInteger(MQL_TESTER) == 0)
               GlobalVariableSet(gvManual, 1.0);

            string manualSymbol = HistoryDealGetString(deal, DEAL_SYMBOL);
            double manualProfit = HistoryDealGetDouble(deal, DEAL_PROFIT);

            AILearningRecordDeal(deal, manualSymbol, manualProfit);

            Print(
               "[LEARN] OPERACAO MANUAL APRENDIDA | ",
               manualSymbol,
               " | deal=",
               IntegerToString((long)deal),
               " | profit=",
               DoubleToString(manualProfit, 2)
            );
           }
        }

      return;
     }

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
         "[TRADE] OPEN | ",
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
         int type = (int)HistoryDealGetInteger(deal, DEAL_TYPE);
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
                         GetMarketScoreFor(symbol),
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

   if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
     {
      //------------------------------------------------
      // Performance
      //------------------------------------------------

      ulong posIdRisco  = HistoryDealGetInteger(deal, DEAL_POSITION_ID);
      double riscoPos   = RiscoDaPosicao(posIdRisco, volume);
      double rMultiplo  = (riscoPos > 0.0) ? (profit / riscoPos) : 0.0;

      HistoryDealSelect(deal);   // RiscoDaPosicao troca a selecao de historico

      // v1.2.10: alimenta o aprendizado persistente com o resultado real
      AILearningRecordDeal(deal, symbol, profit);

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

         // v1.2.20: freio de sequencia perdedora
         StreakBrakeOnLoss();
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

      // v1.2.41 - P1.16: o TradeLogger deixou de ter handle persistente.
      // O estado passou a ser explicito em TradeLoggerReady().
      if(TradeLoggerReady())
        {
         //--------------------------------------------------
         // P1.45 - o registo descreve a POSICAO, nao o deal de fecho
         //--------------------------------------------------
         //
         // O deal que chega aqui e DEAL_ENTRY_OUT: a sua DEAL_PRICE e o preco
         // de FECHO e a sua DEAL_TYPE e o lado do FECHO, por isso uma compra
         // fechada por venda era escrita como SELL. A direcao e o preco de
         // abertura de uma posicao estao no deal DEAL_ENTRY_IN da MESMA
         // posicao, que se pede por DEAL_POSITION_ID.
         //
         // Nota de escopo: dealMagic ja existe no inicio desta funcao, por isso
         // o magic e lido em linha em vez de repetir a declaracao.
         double closeFill = HistoryDealGetDouble(deal, DEAL_PRICE);
         ulong  posId     = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);

         // Fallback: se a posicao nao for seleccionavel, mantem-se o
         // comportamento antigo em vez de gravar zeros.
         double posOpen  = closeFill;
         bool   posDealFound = false;
         bool   posIsBuy = (HistoryDealGetInteger(deal, DEAL_TYPE) == DEAL_TYPE_BUY);

         if(posId > 0 && HistorySelectByPosition(posId))
           {
            int posDeals = HistoryDealsTotal();

            for(int pd = 0; pd < posDeals; pd++)
              {
               ulong pdTicket = HistoryDealGetTicket(pd);

               if(pdTicket == 0)
                  continue;

               if(HistoryDealGetInteger(pdTicket, DEAL_ENTRY) == DEAL_ENTRY_IN)
                 {
                  posOpen  = HistoryDealGetDouble(pdTicket, DEAL_PRICE);
                  posIsBuy = (HistoryDealGetInteger(pdTicket, DEAL_TYPE) == DEAL_TYPE_BUY);
                  posDealFound = true;
                  break;
                 }
              }
           }

         // P1.52 - o fallback do P1.45 passa a ser CONTADO, nao inferido.
         static ulong s_logFallbackCount = 0;

         if(!posDealFound)
           {
            s_logFallbackCount++;
            Print("TRADELOG FALLBACK | deal=", deal,
                  " | posId=", posId,
                  " | direcao e preco herdados do deal de FECHO",
                  " | acumulado=", s_logFallbackCount);
           }

         // HistorySelectByPosition troca a seleccao de historico que o resto
         // deste bloco usa; devolve-a ao deal do evento.
         HistoryDealSelect(deal);

         LogTradeCSV(
            symbol,               // P1.22: simbolo do DEAL
            posIsBuy,             // P1.45: direcao da POSICAO
            posOpen,              // P1.45: preco de ABERTURA da posicao
            closeFill,            // P1.45: preco de FECHO executado
            profit,
            AIScore,
            // P1.21: identidade do deal. DEAL_POSITION_ID liga a linha ao
            // historico do broker e DEAL_MAGIC diz quem a abriu - e o unico
            // campo causal para separar uma operacao deste EA (magic
            // 2026001) de uma operacao manual (magic 0) ou de outro EA.
            posId,
            HistoryDealGetInteger(deal, DEAL_MAGIC)
         );

         //------------------------------------------------
         // v1.2.116 - TRADELOGGER SQLITE: grava em banco estruturado
         //------------------------------------------------
#ifdef XAI_USE_TRADELOG_SQLITE
          // P2.11: DESLIGADO por omissao (Database.mqh em falta). O registo
          // em CSV acima e o caminho que sempre funcionou e nao muda.
         if(TradeLoggerSQLiteInit())
           {
            STradeRecord rec;
            rec.ticket    = deal;
            rec.magic     = HistoryDealGetInteger(deal, DEAL_MAGIC);
            rec.origin    = "EA";
            rec.time      = TimeCurrent();
            rec.symbol    = symbol;
            rec.type      = posIsBuy ? (long)POSITION_TYPE_BUY : (long)POSITION_TYPE_SELL;   // P2.10: cast explicito (STradeRecord::type e long)
            rec.volume    = volume;
            rec.price_open= posOpen;
            rec.price_close= closeFill;
            rec.profit    = profit;
            rec.details   = StringFormat(
               "SL=%.5f TP=%.5f AIScore=%.4f",
               HistoryDealGetDouble(deal, DEAL_SL),
               HistoryDealGetDouble(deal, DEAL_TP),
               AIScore
            );

            if(!TradeLoggerSQLiteLog(rec))
              {
               Print("[SQLITE] Erro ao gravar trade: ", GetLastError());
              }
            TradeLoggerSQLiteShutdown();
           }
#endif   // XAI_USE_TRADELOG_SQLITE
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

      StatisticsRegisterTrade(profit, symbol, deal);   // P2.12: simbolo NEGOCIADO + deal, nao o simbolo do grafico

      // ETAPA 14 - matriz quantitativa: registra resultado p/ Avg R
      QuantRecordResult(profit, rMultiplo);

      //------------------------------------------------
      // ETAPA 6 - AUDITORIA (saida)
      //------------------------------------------------

      if(EnableAuditLog)
        {
         ulong positionId = HistoryDealGetInteger(deal, DEAL_POSITION_ID);

         AuditLogTrackExit(
            positionId,
            (profit > 0.0 ? "WIN" : (profit < 0.0 ? "LOSS" : "BE")),
            profit
         );

         AuditLogTradeResult(
            symbol,
            positionId,
            profit,
            (profit > 0.0 ? "WIN" : (profit < 0.0 ? "LOSS" : "BE"))
         );

         // ETAPA 13 - forward test: registra saida/close de posicion
           {
            ENUM_DEAL_TYPE exType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE);
            ForwardLogDeal(symbol,
                           positionId,
                           (exType == DEAL_TYPE_BUY) ? 1 : -1,
                           GetMarketScoreFor(symbol),
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
            (profit > 0.0 ? "WIN" : (profit < 0.0 ? "LOSS" : "BE")),
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
            (profit > 0.0 ? "WIN" : (profit < 0.0 ? "LOSS" : "BE"))
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
// v1.2.96 (03/11/2026) - P1.84: heartbeat no timer
//------------------------------------------------
// MEDIDO em 02/11 22:25 (graficos sem tick, mercado parado no simbolo):
// 48 linhas [WARNING] "HealthMonitor: modulo sem heartbeat" em ~7 minutos,
// 4 modulos (ATR/ADX/RSI/AI) x cada instancia. A causa nao era modulo morto:
// o heartbeat so era enviado em OnInit e em OnTick, e sem tick nao ha OnTick.
// O proprio HealthMonitor documenta que esses quatro modulos usam liveness
// (sinal de vida), nao progresso - e o timer de 30 s e prova de vida melhor
// que o tick. Sem esta linha o journal enche quando o mercado esta parado e
// o operador aprende a ignorar [WARNING], que e o pior resultado possivel.
   if(EnableHealthMonitor)
     {
      HealthMonitorUpdateTicks();
      HealthMonitorHeartbeat("ATR");
      HealthMonitorHeartbeat("ADX");
      HealthMonitorHeartbeat("RSI");
      HealthMonitorHeartbeat("AI");
     }

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
// F2.1 (v1.2.176) - KILL SWITCH tambem SEM TICK
//------------------------------------------------
// O OnTimer corre a cada 30 s e nao depende de cotacoes. MEDIDO em 06/11/2026
// 23:59:58 (hora do servidor): sexta-feira, mercado fechado, journal do EA
// parado as 18:58:59 locais. Um interruptor que so vivesse no OnTick estaria
// morto exactamente no fim de semana, que e quando o operador tem tempo para
// o accionar. Nao retorna: o timer tem de continuar a alimentar o
// HealthMonitor (ver o comentario de P1.84 acima).
   CKillSwitch::Verificar(MagicNumber, true);
//------------------------------------------------
// F2.9b (v1.2.179) - COTACAO VELHA: deteccao tambem SEM TICK
//------------------------------------------------
// O F2.9 decide no OnTick, porque e la que se decide operar - mas e
// exactamente quando o feed morre que o OnTick deixa de correr. MEDIDO em
// 07/11/2026 01:33 (sabado): 21/21 simbolos com cotacao velha (5590 s a
// 30796 s) e ZERO linhas [TRADE BLOCK] no journal do EA, porque o guarda
// nunca chegou a ser avaliado. Aqui, no timer de 30 s, publica-se a
// TRANSICAO (congelou / voltou) e nao um aviso por ciclo: o estado muda
// duas vezes por fim de semana, nao a cada 30 s.
// Nao retorna: o timer tem de continuar a alimentar o HealthMonitor, a
// ponte e o resto (mesma regra do F2.1 acima).
   {
    static bool     s_cotacaoVelhaPublicada = false;
    static datetime s_cotacaoVelhaAviso     = 0;

    bool cotacaoVelhaAgora = CStalenessGuard::CotacaoVelha(_Symbol);

    if(cotacaoVelhaAgora && !s_cotacaoVelhaPublicada)
      {
       s_cotacaoVelhaPublicada = true;
       s_cotacaoVelhaAviso     = TimeLocal();
       Print("[TRADE BLOCK] COTACAO VELHA (timer) | ", CStalenessGuard::Diagnostico(_Symbol),
             " | sem tick o OnTick nao corre: preco parado nao opera");
      }
    else if(cotacaoVelhaAgora && s_cotacaoVelhaAviso > 0 &&
            (TimeLocal() - s_cotacaoVelhaAviso) >= 3600)
      {
       s_cotacaoVelhaAviso = TimeLocal();
       Print("[TRADE BLOCK] COTACAO VELHA (timer, lembrete 1h) | ",
             CStalenessGuard::Diagnostico(_Symbol), " | continua sem tick");
      }
    else if(!cotacaoVelhaAgora && s_cotacaoVelhaPublicada)
      {
       s_cotacaoVelhaPublicada = false;
       s_cotacaoVelhaAviso     = 0;
       Print("[TRADE BLOCK] COTACAO VOLTOU (timer) | ", CStalenessGuard::Diagnostico(_Symbol),
             " | feed vivo outra vez, o OnTick volta a decidir");
      }
   }


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
      // v1.2.10: atualiza o aprendizado com o historico real
      // (throttle interno de 1 hora por conta)
      AILearningImportHistory(LearningHistoryDays);

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
// RESUMO PARA O OPERADOR (v1.2.19)
// Tambem no timer, e nao so no tick: com o mercado parado (madrugada,
// feriado, simbolo sem cotacao) nao chega tick e o dono ficaria sem saber
// em que degrau da escada cada posicao esta. O throttle interno de
// OperatorBriefSeconds impede repeticao, e a funcao e somente leitura.
//------------------------------------------------

   if(EnableOperatorBrief && PipelineIsMaster())
      OperatorBriefTick(TradesToday);

//------------------------------------------------
// Ponte app -> EA (Integration/ExternalBridge.mqh)
// Tambem aqui, e nao so no OnTick: sem tick (mercado fechado, simbolo
// parado) o app ficaria sem resposta ao ping. O throttle interno e por
// segundo, entao chamar nos dois lugares nao duplica leitura de disco.
//------------------------------------------------

   ExternalBridgePoll();

//------------------------------------------------
// Salvar estatisticas
//------------------------------------------------

   // v1.2.10: estado da sessao (throttle interno de 300s)
   SessionStateStore();

   PerformanceSave();

//------------------------------------------------
// Health Monitor + Auditoria (ETAPA 6)
//------------------------------------------------

   if(EnableHealthMonitor)
     {
      HealthMonitorCheck();

      // v1.2.29 (30/10/2026) - P1.3/P0.4: este bloco era o maior emissor do
      // journal (~25 linhas por ciclo do OnTimer, por grafico). Medido na
      // janela 16:15-16:45 da v1.2.28: 959 blocos em 30 min nos 16 graficos,
      // ~60% das 40 203 linhas. Agora o bloco completo sai so quando HA algo
      // a dizer (estado nao saudavel ou mudanca de estado, no maximo 1x/5 min)
      // e o estado saudavel imprime UMA linha por hora. HealthMonitorCheck()
      // continua a rodar em todos os ciclos: muda apenas a impressao.
      static datetime s_lastHealthLog   = 0;
      static string   s_lastHealthState = "";
      const int       HEALTH_LOG_ALERT_SEC = 300;
      const int       HEALTH_LOG_QUIET_SEC = 3600;

      string healthState     = HealthGetStateString();
      bool   healthUnhealthy = (healthState != "HEALTHY");
      bool   healthChanged   = (s_lastHealthState != "" && healthState != s_lastHealthState);
      long   healthSince     = (s_lastHealthLog == 0 ? 2147483647 : (long)(TimeCurrent() - s_lastHealthLog));
      int    healthNeedSec   = (healthUnhealthy ? HEALTH_LOG_ALERT_SEC : HEALTH_LOG_QUIET_SEC);

      if(EnableVerboseDebug && !MQLInfoInteger(MQL_TESTER) && (healthChanged || healthSince >= healthNeedSec))
        {
         s_lastHealthLog   = TimeCurrent();
         s_lastHealthState = healthState;

         static datetime s_lastHealthFull = 0;
         bool healthFullDue = (s_lastHealthFull == 0 || (TimeCurrent() - s_lastHealthFull) >= 3600);

         // v1.2.39 (30/10/2026) - P1.12. O bloco de 25 linhas ja tinha passado a
         // sair 1x/5 min por grafico quando o estado NAO e saudavel, mas com o
         // mercado fechado o estado fica nao-saudavel para sempre (sem tick),
         // logo o throttle por tempo nunca cortava: medido no journal de 30/10,
         // 2 064 blocos entre 16:02 e 21:44 (~9 000 linhas/hora com 16 graficos).
         // Agora o bloco COMPLETO sai 1x/hora; nos ciclos de 5 min sem mudanca de
         // estado sai UMA linha de resumo. Mudanca de estado imprime na hora.
         if((healthUnhealthy || healthChanged) && (healthChanged || healthFullDue))
           {
            s_lastHealthFull = TimeCurrent();

            // v1.2.81 (02/11/2026) - P1.68: o bloco de 20 linhas foi medido
            // 152 vezes hoje. Continua a sair com TODOS os valores, agora
            // colapsado numa linha com o tag [HEALTH].
            string retratoSaude = HealthMonitorSummary() + "\n" +
                                  (EnableAuditLog ? AuditLogSummary() : "AuditLog OFF") + "\n" +
                                  ADXMetricsSummary() + " | block=" + IntegerToString(g_adxBlockCount);
            Print("[HEALTH] ", healthState, " | ", JournalOneLine(retratoSaude));
           }
         else
           {
            // P1.73: o resumo de hora sai 1x por CONTA (eram 16/hora iguais).
            // Mudanca de estado continua a sair na hora, sem filtro.
            if(AccountLogGatePodeImprimir("health", 3600))
               Print("[HEALTH] ", healthState,
                     " | uptime=", IntegerToString(HealthGetUptimeSeconds()), "s",
                     " | checks=", IntegerToString((long)g_healthCheckCount),
                     " | sem tick=", IntegerToString(HealthGetSecondsSinceTick()), "s",
                     " | resumo completo 1x/hora");
           }
        }
     }

   if(EnableAuditLog)
     {
      AuditLogFlush();
     }

   //------------------------------------------------
   // Backup agendado (ETAPA 7)
   //------------------------------------------------
   // v1.2.38 (30/10/2026) - P1.11. Dois defeitos medidos neste bloco:
   //   1) o backup vivia DENTRO de `if(EnableAuditLog)`. Com o audit log
   //      desligado o BackupManager nunca corria, apesar de
   //      `EnableBackupManager=true`. Sao dois assuntos independentes: o
   //      backup passou a ter bloco proprio.
   //   2) os 16 graficos avaliavam o mesmo minuto e corriam RunBackup() no
   //      mesmo instante, copiando o MESMO conjunto de ficheiros para o
   //      MESMO destino - 16x o mesmo IO. Numa maquina que ja abortou
   //      backtests por disco cheio (0,37 GB livres em 30/10) isso e
   //      desperdicio puro. Passa a correr so na instancia mestre do
   //      pipeline (mesmo padrao do OperatorBrief acima); as restantes
   //      avisam 1x/hora.

   if(EnableBackupManager && BackupIntervalMinutes > 0)
     {
      if(TimeCurrent() - g_lastBackupTime >= BackupIntervalMinutes * 60)
        {
         if(!PipelineIsMaster())
           {
            static datetime s_lastBackupSkipLog = 0;

            if(TimeCurrent() - s_lastBackupSkipLog >= 14400)
              {
               s_lastBackupSkipLog = TimeCurrent();

               if(AccountLogGatePodeImprimir("backup_standby", 21600)) Print("[BACKUP] STANDBY | esta instancia nao e a dona do backup | esta=", ChartID(), " | dono=", PipelineMasterChart());
              }
           }
         else
           {
            g_lastBackupTime = TimeCurrent();

            // P2.05: o CBackupManager publica a linha final (sucesso ou
            // problemas) com copiados, falhas e snapshot; este Print
            // repetia exactamente a mesma informacao.
            CBackupManager::RunBackup();
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

      // Relatorio diario (1x/dia) - v1.2.166 (P1.129): 1x por CONTA.
      // MEDIDO em Common\Files\Notifications.log: o mesmo [RELATORIO] saiu 14
      // vezes por recarga, uma por grafico, porque a ancora g_lastDailyReport
      // e por INSTANCIA e nasce a zero em cada carga. Passa a exigir o portao
      // por conta de 23 h. A primeira utilizacao do ficheiro do portao ainda
      // pode deixar passar mais do que uma instancia no mesmo segundo (a
      // licao do P2.14); a partir dai e 1 por conta e por dia.
      if(TimeCurrent() - g_lastDailyReport >= 86400)
        {
         g_lastDailyReport = TimeCurrent();
         if(AccountLogGatePodeImprimir("relatorio_diario", 82800))
            CNotificationCenter::SendDailyReport(DailyProfit, TradesToday, 0.0);
        }
     }

// Health Check
//------------------------------------------------

   // v1.2.27 (30/10/2026) - P0.4/P1.3: com EnableVerboseDebug=true este bloco
   // escrevia 5 linhas a cada tick (792 ocorrencias de EXECUTION SUMMARY em
   // cada 8 MB de log no backtest de 3 meses da v1.2.26). Passou a 1x/minuto.
   //
   // v1.2.30 (30/10/2026) - P1.3/P0.4 rodada 2: 1x/minuto ainda custa caro
   // porque ESTE bloco e o pai de TRES resumos: CRecoveryManager::GetHealthSummary()
   // (8 linhas "=== RECOVERY STATUS ==="), CSmartExecution::GetExecutionSummary()
   // (2 linhas "=== EXECUTION SUMMARY ===") e CSafetyManager::GetSafetySummary().
   // MEDIDO na v1.2.29, janela 17:05:00-17:08:30 (3,5 min, 16 graficos,
   // 1 426 linhas): 66 blocos RECOVERY (37% das linhas), 50 SYSTEM STATUS mais
   // 50 EXECUTION SUMMARY (28%). Nada disso era saude nem era evento: era o
   // mesmo retrato periodico. Agora, com tudo OK, sai 1x/4 h; com QUALQUER
   // problema (estado de saude != HEALTHY ou circuito aberto) ou na mudanca de
   // estado, sai em 60 s. O diagnostico nao foi removido, foi tornado raro.
   static datetime lastSystemStatusLog = 0;
   static string   lastSystemStatusState = "";
   datetime agoraSystemStatus = TimeCurrent();

   string diagHealthState = HealthGetStateString();
   bool   diagCircuitOk   = CCircuitBreaker::CanTrade();
   bool   diagChanged     = (lastSystemStatusState != "" && diagHealthState != lastSystemStatusState);

   // v1.2.31: tres niveis, porque a v1.2.30 usava 60 s para QUALQUER estado
   // diferente de HEALTHY. Com 16 graficos multi-ativo, a maioria dos simbolos
   // fica sem tick legitimo e responde FAILURE para sempre - o "alerta" de 60 s
   // virava o proprio ruido. Circuito ABERTO e o unico caso que bloqueia ordem
   // e merece 60 s; saude degradada com sessao aberta fica em 15 min; o resto
   // em 4 h.
   int    diagLogSec      = (!diagCircuitOk ? 60
                             : (diagHealthState != "HEALTHY" ? 900 : 14400));

   if(EnableVerboseDebug && !MQLInfoInteger(MQL_TESTER) &&
      (diagChanged ||
       (!diagCircuitOk && (agoraSystemStatus - lastSystemStatusLog) >= 60) ||
       (lastSystemStatusLog == 0 && LogSessaoPodeImprimir("status_retrato")) ||
       ((agoraSystemStatus - lastSystemStatusLog) >= diagLogSec && LogSessaoPodeImprimir("status_retrato"))))
     {
      lastSystemStatusLog = agoraSystemStatus;
      lastSystemStatusState = diagHealthState;
      // v1.2.81 (02/11/2026) - P1.68: este retrato saia em 14 linhas e foi
      // medido 586 vezes no Logs de hoje. Os valores sao os mesmos; o que
      // muda e que passam a caber numa linha, com o tag [STATUS].
      string retratoRecovery = CRecoveryManager::GetHealthSummary();
      string retratoExecucao = CSmartExecution::GetExecutionSummary();
      string retratoSeguranca = CSafetyManager::GetSafetySummary();

      // v1.2.107 (03/11/2026) - P1.97: a idade da previsao so existia dentro do
      // system_status.json e do ficheiro do ULTIMO grafico que o escreveu
      // (auditoria de 03/11: o JSON dizia age_seconds=30/stale=false enquanto
      // Data\prediction_XAUUSD.json tinha 1860 s e o limite era 900 s). O
      // [STATUS] passa a mostrar, no jornal, a idade do ficheiro do PROPRIO
      // simbolo do grafico e o limite que a reprova, para que a frescura da IA
      // seja verificavel simbolo a simbolo sem depender do heartbeat.
      // Isto e leitura de estado: nao altera filtro, entrada, saida, lote,
      // spread, alvo, precificacao nem qualquer parametro de risco.
      string retratoAI =
         StringFormat("[AI] %s | idade=%ds | limite=%ds | estado=%s | modelo=%s",
                      _Symbol,
                      (int)AI_AgeSeconds,
                      MaxPredictionAgeSec,
                      (AI_IsStale ? "VENCIDA"
                                  : (AI_AgeSeconds < 0.0 ? "SEM_DADO" : "OK")),
                      (AI_ModelVersion == "" ? "sem_modelo" : AI_ModelVersion));
      // v1.2.110 (03/11/2026) - P1.98: o bit de permissao do PROGRAMA e POR
      // GRAFICO (MQL_TRADE_ALLOWED), nao do terminal nem do .ex5. A auditoria de
      // 03/11 mostrou o grafico XAUUSD com este bit a 0 enquanto outro grafico
      // negociava, e a unica prova de =1 era o snapshot de INIT do ULTIMO grafico
      // que escreveu ProductionChecklist.txt (que nem sempre e o grafico em
      // causa). O [STATUS] passa a trazer os cinco bits medidos AGORA, nesta
      // instancia, para que a permissao seja verificavel no jornal por grafico.
      // Isto e leitura de estado: nao altera filtro, entrada, saida, lote,
      // spread, alvo, precificacao nem qualquer parametro de risco.
      string retratoPerm =
         StringFormat("[PERM] MQL_TRADE_ALLOWED=%d | TERMINAL_TRADE_ALLOWED=%d | ACCOUNT_TRADE_ALLOWED=%d | ACCOUNT_TRADE_EXPERT=%d | TERMINAL_CONNECTED=%d",
                      (int)MQLInfoInteger(MQL_TRADE_ALLOWED),
                      (int)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED),
                      (int)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED),
                      (int)AccountInfoInteger(ACCOUNT_TRADE_EXPERT),
                      (int)TerminalInfoInteger(TERMINAL_CONNECTED));
      string retratoStatus = "[STATUS] " + diagHealthState + " | " + retratoPerm + " | " +
                             retratoRecovery + "\n" + retratoExecucao + "\n" +
                             retratoSeguranca + "\n" + retratoAI;
      Print(JournalOneLine(retratoStatus));
     }
  }

//==================================================
// ON DEINIT
//==================================================

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double OnTester()
  {
   const double profit       = TesterStatistics(STAT_PROFIT);
   const double profitFactor = TesterStatistics(STAT_PROFIT_FACTOR);
   const double drawdownPct  = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   const double trades       = TesterStatistics(STAT_TRADES);

// O criterio so ordena os passes do Strategy Tester; nunca altera ordens.
   if(trades <= 0.0 || profit <= 0.0 || profitFactor <= 1.0)
      return 0.0;

   return (profit * profitFactor) / (1.0 + MathMax(0.0, drawdownPct));
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnDeinit(
   const int reason
)
  {
   // v1.2.88 (02/11/2026) - P1.75: eram 3 linhas decorativas no inicio do
   // encerramento (2 separadores + "FINALIZANDO" + "Reason=") e mais 2 no fim.
   // MEDIDO no Logs de 02/11, janela 19:34-19:40: 32 separadores "====", 16
   // "XAU_AI_PRO FINALIZANDO", 16 "Reason=N", 16 "XAU_AI_PRO FINALIZADO" e 16
   // "SYSTEM CLOSED" = 96 linhas para dizer que 16 graficos fecharam. Passa a
   // sair UMA linha [STOP] no fim, com simbolo, motivo e equity.

//================================================
// PARAR TIMER
//================================================

// ETAPA 15.6: sinaliza parada no event stream
   EventSystemStop("reason=" + IntegerToString(reason));
   EventShutdown();

// v1.2.0 - SALVAR RESUMO (win rate) em FILE_COMMON
   // v1.2.10: ultimo estado antes de sair (forca gravacao, ignora throttle)
   SessionStateStore();
   StatisticsSaveSummary();
   QuantSaveReport();   // ETAPA 14: matriz quantitativa (FILE_COMMON)
   // v1.2.83 (02/11/2026) - P1.70: o retrato quantitativo (14 linhas) e o
   // benchmark (10 linhas) saiam no encerramento de CADA uma das 16
   // instancias, e cada reanexacao produz 16 encerramentos. MEDIDO em
   // 02/11/2026 no MQL5\Logs: QUANT MATRIX 316 linhas, BENCHMARK 625,
   // BACKTEST ANALYZER 948 - quase tudo copia de [Trades=0 / PF=0.00].
   // O CSV continua a ser gravado (QuantSaveReport acima); o jornal de
   // producao deixa de repetir a mesma tabela. No tester continua igual.
   if(MQLInfoInteger(MQL_TESTER))
      Print(QuantSummary());

   // P1.17: auditoria do portao de diagnostico (linhas abafadas nesta sessao)
   if(LogInicioDetalhe()) Print(DiagGateSummary());

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
     {
      HealthMonitorShutdown();
     }

   if(EnableAuditLog)
     {
      AuditLogClose();
     }

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

   // v1.2.83 (02/11/2026) - P1.70: mesma razao do P1.70 acima - o relatorio
   // de benchmark volta a sair so no tester; BenchmarkReport.txt continua
   // a ser gravado em FILE_COMMON por LogComparison.
   if(EnableBenchmark && MQLInfoInteger(MQL_TESTER))
      CBenchmarkEngine::LogComparison();

//================================================
// ETAPA 9 - NOTIFICATION CENTER (encerramento)
//================================================

   if(EnableNotifications)
     {
      if(reason == REASON_INITFAILED)
         CNotificationCenter::SendError("EA", "falha na inicializacao");

      // v1.2.166 (P1.129): 14 graficos enviavam 14 notificacoes do MESMO
      // encerramento. MEDIDO em Common\Files\Notifications.log: [SISTEMA] EA
      // finalizado (reason=9) saiu 14 vezes as 20:26:51, 13 as 20:40:11 e
      // (reason=2) 14 vezes na recarga das 20:05:05. Os motivos que acordam
      // TODAS as instancias no mesmo segundo (recompilacao, conta, template e
      // fecho do terminal) passam a sair so da dona do pipeline, com o portao
      // por conta de 120 s por cima; os restantes continuam no portao.
      bool finalizadoPermitido = true;

      if(!MQLInfoInteger(MQL_TESTER))
        {
         bool simultaneo = (reason == REASON_RECOMPILE || reason == REASON_ACCOUNT ||
                            reason == REASON_TEMPLATE || reason == REASON_CLOSE);

         if(simultaneo && PipelineMasterFresh())
            finalizadoPermitido = (ChartID() == PipelineMasterChart()) &&
                                 AccountLogGatePodeImprimir("ea_finalizado_" + IntegerToString(reason), 120);
         else
            finalizadoPermitido = AccountLogGatePodeImprimir("ea_finalizado_" + IntegerToString(reason), 120);
        }

      if(finalizadoPermitido)
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

   // v1.2.88 (02/11/2026) - P1.75: uma linha por instancia em vez de cinco.
   // P2.13 (03/11/2026): MEDIDO no journal do expert - cada reload deixa uma
   // rajada de linhas [STOP], todas no mesmo segundo, com o mesmo motivo e a
   // mesma equity, uma por grafico (21:15:11 e 21:19:10 de 03/11, 15 linhas
   // cada). O motivo NOVO continua a sair na hora; a rajada do reload, que
   // repete o mesmo motivo, passa a 1 linha por conta. No tester nao ha portao
   // e a linha sai sempre, como antes.
   // P2.14 (03/11/2026): o portao por conta sozinho ainda deixava passar a
   // rajada na PRIMEIRA utilizacao - o ficheiro do portao nao existia, as 15
   // instancias leram "nunca impresso" ao mesmo tempo e escreveram todas.
   // MEDIDO no journal do expert: o reload de 21:29:47 (o primeiro com o
   // P2.13) deixou 15 linhas "[STOP] <SYM> | motivo=2 | equity=12592.02"; o
   // reload seguinte, as 21:32:13, ja deixou 1. O reload de recompilacao
   // (REASON_RECOMPILE) acorda TODAS as instancias no mesmo segundo, portanto
   // essa linha passa a sair so da dona do pipeline - eleicao que ja existe,
   // e uma so por conta. Qualquer outro motivo (fecho de um grafico, mudanca
   // de periodo, parametros) nao e simultaneo e continua a passar pelo portao
   // por conta, 1x/120 s. Sem dona publicada (init falhado ou guarda
   // desligada) o portao volta a decidir, como antes.
   bool stopLogPermitido = true;

   if(!MQLInfoInteger(MQL_TESTER))
     {
      // PipelineMasterFresh (nao PipelineMasterChart): id publicado com
      // batimento fresco. Dono morto ou batimento velho -> portao por conta.
      if(reason == REASON_RECOMPILE && PipelineMasterFresh())
         stopLogPermitido = (ChartID() == PipelineMasterChart());
      else
         stopLogPermitido = AccountLogGatePodeImprimir("stop_" + IntegerToString(reason), 120);
     }

   if(stopLogPermitido)
      Print("[STOP] ", _Symbol, " | motivo=", reason,
            " | equity=", DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
            " | estado, resumo e relatorios gravados");

   // v1.2.95 (02/11/2026) - P1.83: flush + close do logger de ficheiro que
   // o OnInit passou a abrir. Sem isto, o handle morria com a instancia e as
   // ultimas linhas podiam nao chegar ao disco.
   LoggerClose();
  }

//+------------------------------------------------------------------+
