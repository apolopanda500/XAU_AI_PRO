//+------------------------------------------------------------------+
//|                                              EventEmitter.mqh    |
//|                                  Event Stream - ETAPA 15.6       |
//|                                            XAU_AI_PRO v1.2.0     |
//+------------------------------------------------------------------+
// ETAPA 15.6.1 / 15.6.2 - EVENT EMITTER (canal oficial de eventos)
//
// Funcao: camada UNICA e centralizada de eventos da plataforma.
// Todos os modulos emitem eventos AQUI (nunca escrevem o CSV direto).
//
//   EA --> EventEmitter --> forward_test_events.csv --> Python/App
//
// Formato (15.6.2 - 10 colunas):
//   Time,Event,Symbol,TF,Ticket,Severity,Module,Message,Value,Status
//
// Arquivo: Data\forward_test_events.csv (UTF-16 LE, append-only, 1 linha,
// com FILE_SHARE para leitura simultanea pelo App/Python).
//
// PRINCIPIO: nunca bloqueia/interrompe a execucao; apenas registra.

#ifndef EVENT_EMITTER_MQH
#define EVENT_EMITTER_MQH

//==================================================
// NOMES PADRAO DE EVENTOS (15.6.1)
//==================================================
#define EV_SYSTEM_START      "SYSTEM_START"
#define EV_SYSTEM_STOP       "SYSTEM_STOP"
#define EV_FWD_START         "FORWARD_TEST_START"
#define EV_HEALTH_UPDATE     "HEALTH_UPDATE"
#define EV_AI_PREDICTION     "AI_PREDICTION"
#define EV_AI_ERROR          "AI_ERROR"
#define EV_AI_BLOCK          "AI_BLOCK"
#define EV_SIGNAL_GENERATED  "SIGNAL_GENERATED"
#define EV_TRADE_APPROVED    "TRADE_APPROVED"
#define EV_TRADE_REJECTED    "TRADE_REJECTED"
#define EV_TRADE_OPEN        "TRADE_OPEN"
#define EV_TRADE_CLOSE       "TRADE_CLOSE"
#define EV_RISK_BLOCK        "RISK_BLOCK"
#define EV_NEWS_BLOCK        "NEWS_BLOCK"
#define EV_CIRCUIT_BREAKER   "CIRCUIT_BREAKER"
#define EV_SAFE_MODE         "SAFE_MODE"
#define EV_RECOVERY          "RECOVERY"
#define EV_BROKER_ERROR      "BROKER_ERROR"
#define EV_PYTHON_ERROR      "PYTHON_ERROR"
#define EV_DATABASE_ERROR    "DATABASE_ERROR"
#define EV_SYSTEM_ERROR      "SYSTEM_ERROR"
#define EV_HEALTH_WARNING    "HEALTH_WARNING"
#define EV_HEALTH_FAILURE    "HEALTH_FAILURE"

//==================================================
// SEVERIDADE
//==================================================
#define EV_SEV_INFO    "INFO"
#define EV_SEV_WARN    "WARN"
#define EV_SEV_ERROR   "ERROR"
#define EV_SEV_CRIT    "CRITICAL"

static string EV_FILE = "Data\\forward_test_events.csv";
static int    evHandle = INVALID_HANDLE;
static bool   evInitialized = false;

// Versao local (nao depende de VersionManager)
#define EV_VERSION_STRING "1.2.0"

//==================================================
// INIT - abre/garante header (append-only UTF-16)
//==================================================
bool EventInit()
{
   if(evInitialized && evHandle != INVALID_HANDLE)
      return true;

   ResetLastError();
   evHandle = FileOpen(
      EV_FILE,
      FILE_WRITE | FILE_READ | FILE_CSV | FILE_UNICODE |
      FILE_SHARE_READ | FILE_SHARE_WRITE,
      ','
   );

   if(evHandle == INVALID_HANDLE)
   {
      Print("[EVENT] falha ao abrir: ", EV_FILE, " | Err=", GetLastError());
      return false;
   }

   FileSeek(evHandle, 0, SEEK_END);

   if(FileSize(evHandle) == 0)
   {
      FileWrite(evHandle,
         "Time","Event","Symbol","TF","Ticket","Severity",
         "Module","Message","Value","Status");
      FileFlush(evHandle);
   }

   evInitialized = true;
   return true;
}

//==================================================
// EMIT - funcao central
//==================================================
bool EventEmit(
   const string event,
   const string severity = EV_SEV_INFO,
   const string symbol   = "",
   const string module   = "",
   const string message  = "",
   const string value    = "",
   const string status   = "OK",
   const long   ticket   = 0
)
{
   if(!evInitialized)
      EventInit();

   if(evHandle == INVALID_HANDLE)
      return false;

   string sym = (symbol == "" ? _Symbol : symbol);
   string tf  = EnumToString((ENUM_TIMEFRAMES)Period());

   FileSeek(evHandle, 0, SEEK_END);

   FileWrite(evHandle,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
      event,
      sym,
      tf,
      (ticket > 0 ? IntegerToString((long)ticket) : "0"),
      severity,
      module,
      message,
      value,
      status);

   FileFlush(evHandle);
   return true;
}

//==================================================
// METODOS PADRAO (wrappers convenientes)
//==================================================
bool EventSystemStart(string extra)
{
   return EventEmit(EV_SYSTEM_START, EV_SEV_INFO, "", "EA",
                    "EA inicializado " EV_VERSION_STRING, extra, "ONLINE");
}

bool EventSystemStop(string reason)
{
   return EventEmit(EV_SYSTEM_STOP, EV_SEV_INFO, "", "EA",
                    "EA finalizado", reason, "OFFLINE");
}

bool EventForwardStart(string mode)
{
   return EventEmit(EV_FWD_START, EV_SEV_INFO, "", "FT",
                    "Forward test iniciado", mode, "ONLINE");
}

bool EventHealthUpdate(string metric, string value, string status)
{
   return EventEmit(EV_HEALTH_UPDATE, EV_SEV_INFO, "", "HEALTH",
                    metric, value, status);
}

bool EventHealthWarning(string metric, string value)
{
   return EventEmit(EV_HEALTH_WARNING, EV_SEV_WARN, "", "HEALTH",
                    metric, value, "WARNING");
}

bool EventHealthFailure(string metric, string value)
{
   return EventEmit(EV_HEALTH_FAILURE, EV_SEV_ERROR, "", "HEALTH",
                    metric, value, "FAILURE");
}

bool EventAIPrediction(string symbol, string signal, string score)
{
   return EventEmit(EV_AI_PREDICTION, EV_SEV_INFO, symbol, "AI",
                    "Predicao IA", signal, score);
}

bool EventAIBlock(string symbol, string reason)
{
   return EventEmit(EV_AI_BLOCK, EV_SEV_WARN, symbol, "AI",
                    "IA indisponivel/bloqueio", reason, "UNAVAILABLE");
}

bool EventAIError(string symbol, string reason)
{
   return EventEmit(EV_AI_ERROR, EV_SEV_ERROR, symbol, "AI",
                    "Erro IA", reason, "ERROR");
}

bool EventSignalGenerated(string symbol, string direction, string score)
{
   return EventEmit(EV_SIGNAL_GENERATED, EV_SEV_INFO, symbol, "SCANNER",
                    "Sinal gerado", direction, score);
}

bool EventTradeApproved(string symbol, string side, string volume)
{
   return EventEmit(EV_TRADE_APPROVED, EV_SEV_INFO, symbol, "EXEC",
                    "Trade aprovado", side + " vol=" + volume, "APPROVED");
}

bool EventTradeRejected(string symbol, string reason, string retcode)
{
   return EventEmit(EV_TRADE_REJECTED, EV_SEV_WARN, symbol, "EXEC",
                    "Trade rejeitado", reason, retcode);
}

bool EventTradeOpen(string symbol, long ticket, string volume)
{
   return EventEmit(EV_TRADE_OPEN, EV_SEV_INFO, symbol, "EXEC",
                    "Posicao aberta", "vol=" + volume, "OPEN", ticket);
}

bool EventTradeClose(string symbol, long ticket, string profit)
{
   return EventEmit(EV_TRADE_CLOSE, EV_SEV_INFO, symbol, "EXEC",
                    "Posicao fechada", "profit=" + profit, "CLOSED", ticket);
}

bool EventRiskBlock(string symbol, string reason)
{
   return EventEmit(EV_RISK_BLOCK, EV_SEV_WARN, symbol, "RISK",
                    "Bloqueio de risco", reason, "BLOCKED");
}

bool EventNewsBlock(string symbol, string reason)
{
   return EventEmit(EV_NEWS_BLOCK, EV_SEV_WARN, symbol, "NEWS",
                    "Bloqueio de noticia", reason, "BLOCKED");
}

bool EventCircuitBreaker(string reason)
{
   return EventEmit(EV_CIRCUIT_BREAKER, EV_SEV_CRIT, "", "CIRCUIT",
                    "Circuit breaker", reason, "SAFE");
}

bool EventSafeMode(string reason)
{
   return EventEmit(EV_SAFE_MODE, EV_SEV_WARN, "", "SAFETY",
                    "Modo seguro", reason, "SAFE");
}

bool EventRecovery(string reason)
{
   return EventEmit(EV_RECOVERY, EV_SEV_INFO, "", "RECOVERY",
                    "Recuperacao", reason, "RECOVERED");
}

bool EventBrokerError(string reason)
{
   return EventEmit(EV_BROKER_ERROR, EV_SEV_ERROR, "", "BROKER",
                    "Erro de broker", reason, "ERROR");
}

bool EventPythonError(string reason)
{
   return EventEmit(EV_PYTHON_ERROR, EV_SEV_ERROR, "", "PYTHON",
                    "Erro de Python/IA", reason, "ERROR");
}

bool EventDatabaseError(string reason)
{
   return EventEmit(EV_DATABASE_ERROR, EV_SEV_ERROR, "", "DB",
                    "Erro de banco de dados", reason, "ERROR");
}

bool EventSystemError(string reason)
{
   return EventEmit(EV_SYSTEM_ERROR, EV_SEV_CRIT, "", "EA",
                    "Erro de sistema", reason, "ERROR");
}

//==================================================
// FLUSH / CLOSE
//==================================================
void EventFlush()
{
   if(evHandle != INVALID_HANDLE)
      FileFlush(evHandle);
}

void EventShutdown()
{
   if(evHandle != INVALID_HANDLE)
   {
      FileFlush(evHandle);
      FileClose(evHandle);
      evHandle = INVALID_HANDLE;
   }
   evInitialized = false;
}

//==================================================
// SUMMARY
//==================================================
string EventSummary()
{
   return StringFormat("EventEmitter | File=%s | State=%s",
      EV_FILE,
      (evHandle != INVALID_HANDLE ? "ON" : "OFF"));
}

#endif // EVENT_EMITTER_MQH