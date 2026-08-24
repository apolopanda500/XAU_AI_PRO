#ifndef FAILSAFE_MQH
#define FAILSAFE_MQH

#include "../Tools/Logger.mqh"
#include "../Tools/HealthMonitor.mqh"

//==================================================
// FAILSAFE - FASE 8.6
//
// Maquina de estados:
//
//   NORMAL  --trigger-->  SAFE MODE  --recovery-->  NORMAL
//      ^                       |
//      |------- manual --------|
//
// Em SAFE MODE:
//   - Nenhuma nova entrada
//   - Apenas gerencia posicoes abertas
//   - Tenta recuperar a cada 60s
//   - Log verbose
//
// Trigger para SAFE:
//   - Drawdown > limite
//   - CPU > 90% por Y tempo
//   - AI error consecutivos > N
//   - Tick ausente > Z segundos
//   - Broker disconnect
//==================================================

enum ENUM_FAILSAFE_STATE
{
   FS_NORMAL  = 0,
   FS_SAFE    = 1,
   FS_MANUAL  = 2
};

#define FS_RECOVERY_OK_SEC  300    // precisa ficar 5min sem trigger para voltar a NORMAL
#define FS_TRIGGER_HOLD_SEC 30     // trigger precisa persistir 30s antes de acionar

int    g_fsState            = FS_NORMAL;
int    g_fsPreviousState    = FS_NORMAL;
string g_fsReason           = "";
datetime g_fsEnteredAt      = 0;
datetime g_fsLastTrigger    = 0;
datetime g_fsLastOk         = 0;
bool    g_fsInitialized     = false;
int     g_fsErrorCount      = 0;
int     g_fsErrorThreshold  = 5;
double  g_fsMaxDrawdownPct  = 15.0;

string FSStateToStr(ENUM_FAILSAFE_STATE s)
{
   if(s == FS_NORMAL) return "NORMAL";
   if(s == FS_SAFE)   return "SAFE";
   return "MANUAL";
}

bool FailSafeInit()
{
   g_fsState         = FS_NORMAL;
   g_fsPreviousState = FS_NORMAL;
   g_fsReason        = "";
   g_fsEnteredAt     = 0;
   g_fsLastTrigger   = 0;
   g_fsLastOk        = TimeCurrent();
   g_fsErrorCount    = 0;
   g_fsInitialized   = true;
   LogSystem("FailSafe", "FailSafe inicializado - estado: NORMAL");
   return true;
}

void FailSafeEnter(ENUM_FAILSAFE_STATE newState, string reason)
{
   if(g_fsState == newState) return;
   g_fsPreviousState = g_fsState;
   g_fsState         = newState;
   g_fsReason        = reason;
   g_fsEnteredAt     = TimeCurrent();
   g_fsLastTrigger   = TimeCurrent();
   LogWarn("FailSafe", "Transicao " + FSStateToStr(g_fsPreviousState) +
           " -> " + FSStateToStr(newState) + " | motivo: " + reason);
}

void FailSafeExit(string reason)
{
   if(g_fsState == FS_NORMAL) return;
   LogInfo("FailSafe", "Recuperado: " + FSStateToStr(g_fsState) +
           " -> NORMAL | " + reason);
   g_fsPreviousState = g_fsState;
   g_fsState         = FS_NORMAL;
   g_fsReason        = "";
   g_fsErrorCount    = 0;
}

void FailSafeForce(ENUM_FAILSAFE_STATE state, string reason)
{
   FailSafeEnter(state, "MANUAL: " + reason);
}

//==================================================
// FAILSAFE TICK - detecta triggers e tenta recovery
//==================================================
void FailSafeTick()
{
   if(!g_fsInitialized) return;

   // Avaliar triggers
   bool triggerSafe = false;
   string triggerReason = "";

   // 1) Drawdown
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   if(balance > 0)
   {
      double dd = ((balance - equity) / balance) * 100.0;
      if(dd > g_fsMaxDrawdownPct)
      {
         triggerSafe = true;
         triggerReason = "DD=" + DoubleToString(dd, 2) + "% > " +
                         DoubleToString(g_fsMaxDrawdownPct, 2) + "%";
      }
   }

   // 2) Broker disconnect
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      triggerSafe = true;
      triggerReason = "Broker desconectado";
   }

   // 3) Health critico
   if(HealthIsCritical())
   {
      // pegar categoria em error
      for(int i=0; i<HEALTH_CAT_COUNT; i++)
      {
         if(g_healthStatus[i] == (int)HEALTH_ERROR)
         {
            triggerSafe = true;
            triggerReason = "Health ERROR: " + g_healthCategories[i] +
                            " (" + g_healthDetail[i] + ")";
            break;
         }
      }
   }

   // 4) Latencia alta
   if(g_healthLastOnTickMs > 200)
   {
      triggerSafe = true;
      triggerReason = "Latencia OnTick=" +
                      IntegerToString(g_healthLastOnTickMs) + "ms";
   }

   // Transicao
   if(triggerSafe)
   {
      g_fsLastTrigger = TimeCurrent();
      g_fsErrorCount++;
      if(g_fsState == FS_NORMAL)
      {
         if(g_fsErrorCount >= g_fsErrorThreshold)
            FailSafeEnter(FS_SAFE, triggerReason);
      }
   }
   else
   {
      g_fsLastOk = TimeCurrent();
      g_fsErrorCount = 0;

      // Tentar recovery
      if(g_fsState == FS_SAFE)
      {
         if(TimeCurrent() - g_fsLastTrigger > FS_RECOVERY_OK_SEC)
            FailSafeExit("Sem trigger ha " +
                         IntegerToString(FS_RECOVERY_OK_SEC) + "s");
      }
   }
}

ENUM_FAILSAFE_STATE FailSafeGetState() { return (ENUM_FAILSAFE_STATE)g_fsState; }
string FailSafeGetReason()             { return g_fsReason; }
bool   FailSafeCanTrade()              { return g_fsState == FS_NORMAL; }

string FailSafeGetStatusJSON()
{
   string json = "{";
   json += "\"state\":\"" + FSStateToStr((ENUM_FAILSAFE_STATE)g_fsState) + "\",";
   json += "\"previous\":\"" + FSStateToStr((ENUM_FAILSAFE_STATE)g_fsPreviousState) + "\",";
   json += "\"reason\":\"" + g_fsReason + "\",";
   json += "\"entered_at\":\"" + TimeToString(g_fsEnteredAt, TIME_DATE|TIME_SECONDS) + "\",";
   json += "\"error_count\":" + IntegerToString(g_fsErrorCount) + ",";
   json += "\"can_trade\":" + (FailSafeCanTrade() ? "true" : "false");
   json += "}";
   return json;
}

void FailSafeClose()
{
   LogInfo("FailSafe", "FailSafe fechado");
   g_fsInitialized = false;
}

#endif
