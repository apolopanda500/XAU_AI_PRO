// XAU_AI_PRO v1.2.0
#ifndef HEALTHMONITOR_MQH
#define HEALTHMONITOR_MQH

#include "../Core/Config.mqh"
#include "Logger.mqh"

//==================================================
// XAU_AI_PRO — HEALTH MONITOR (ETAPA 6)
// Sistema central de monitoramento de saúde.
//
// Absorveu o antigo WatchDog.mqh: heartbeat dos
// módulos ATR / ADX / RSI / AI / PYTHON / CSV / JSON
// com timeout e contagem de falhas.
//==================================================

//==================================================
// CONTADORES DE ERRO
//==================================================

int g_healthBrokerErrors    = 0;
int g_healthAIErrors        = 0;
int g_healthDatasetErrors   = 0;
int g_healthFileErrors      = 0;
int g_healthJSONErrors      = 0;
int g_healthPythonErrors    = 0;
int g_healthIndicatorErrors = 0;

//==================================================
// TICK MONITOR
//==================================================

datetime g_lastTickTime      = 0;
datetime g_lastSecond        = 0;
datetime g_lastHealthCheck   = 0;

int g_ticksPerSecond         = 0;
int g_ticksThisSecond        = 0;

//==================================================
// UPTIME / MÉTRICAS (ETAPA 6)
//==================================================

datetime g_healthUptimeStart = 0;
ulong    g_healthTotalTicks  = 0;
ulong    g_healthCheckCount  = 0;
bool     g_healthLastCheckOK = true;

//==================================================
// WATCHDOG — HEARTBEAT DOS MÓDULOS (ETAPA 6)
// Absorvido do antigo WatchDog.mqh
//==================================================

#define HEALTH_WD_MODULES      7
#define HEALTH_WD_MAX_FAILURES 3

string g_wdModuleNames[HEALTH_WD_MODULES] = {"ATR", "ADX", "RSI", "AI", "PYTHON", "CSV", "JSON"};
ulong  g_wdLastTime[HEALTH_WD_MODULES];
int    g_wdFailures[HEALTH_WD_MODULES];
bool   g_wdActive[HEALTH_WD_MODULES];

//==================================================
// ESTADO
//==================================================

bool g_healthInitialized = false;
bool g_healthStatus      = true;

//==================================================
// ÍNDICE DO MÓDULO
//==================================================

int HealthModuleIndex(string module)
{
   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      if(StringCompare(g_wdModuleNames[i], module, false) == 0)
         return i;
   }

   return -1;
}

//==================================================
// INIT
//==================================================

bool HealthMonitorInit()
{
   datetime now = TimeCurrent();

   g_lastTickTime      = now;
   g_lastSecond        = now;
   g_lastHealthCheck   = now;
   g_healthUptimeStart = now;

   g_ticksPerSecond  = 0;
   g_ticksThisSecond = 0;

   g_healthTotalTicks  = 0;
   g_healthCheckCount  = 0;
   g_healthLastCheckOK = true;

   // WatchDog (ETAPA 6)
   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      g_wdLastTime[i] = 0;
      g_wdFailures[i] = 0;
      g_wdActive[i]   = true;
   }

   g_healthStatus      = true;
   g_healthInitialized = true;

   LogSystem("HealthMonitor inicializado (WatchDog integrado)");

   return true;
}

//==================================================
// UPDATE TICKS
//==================================================

void HealthMonitorUpdateTicks()
{
   if(!g_healthInitialized)
      return;

   datetime now = TimeCurrent();

   g_lastTickTime = now;
   g_healthTotalTicks++;

   MqlDateTime currentTime;
   MqlDateTime previousTime;

   TimeToStruct(now, currentTime);
   TimeToStruct(g_lastSecond, previousTime);

   // Novo segundo
   if(currentTime.sec != previousTime.sec)
   {
      g_ticksPerSecond  = g_ticksThisSecond;
      g_ticksThisSecond = 0;
      g_lastSecond      = now;
   }

   g_ticksThisSecond++;
}

//==================================================
// TICK TIMEOUT
//==================================================

bool HealthMonitorCheckTickTimeout(int maxSeconds = 10)
{
   if(!g_healthInitialized)
      return false;

   datetime now = TimeCurrent();

   int secondsSinceLastTick = (int)(now - g_lastTickTime);

   if(secondsSinceLastTick > maxSeconds)
   {
      LogError(
         "HealthMonitor: timeout de tick",
         "Seconds=" + IntegerToString(secondsSinceLastTick)
      );

      return false;
   }

   return true;
}

//==================================================
// REGISTRO DE ERRO
//==================================================

void HealthMonitorLogError(string module)
{
   if(module == "BROKER")
      g_healthBrokerErrors++;
   else if(module == "AI")
      g_healthAIErrors++;
   else if(module == "DATASET")
      g_healthDatasetErrors++;
   else if(module == "FILE")
      g_healthFileErrors++;
   else if(module == "JSON")
      g_healthJSONErrors++;
   else if(module == "PYTHON")
      g_healthPythonErrors++;
   else if(module == "INDICATOR")
      g_healthIndicatorErrors++;
   else
   {
      LogWarning(
         "HealthMonitor: módulo desconhecido",
         "Module=" + module
      );
   }
}

//==================================================
// HEARTBEAT (ETAPA 6 — absorve WatchDogHeartbeat)
//==================================================

void HealthMonitorHeartbeat(string module)
{
   if(!g_healthInitialized)
      return;

   int idx = HealthModuleIndex(module);

   if(idx < 0)
      return;

   g_wdLastTime[idx] = GetTickCount64();
   g_wdFailures[idx] = 0;
}

//==================================================
// RESET HEARTBEAT (ETAPA 6 — absorve WatchDogResetFailures)
//==================================================

void HealthMonitorResetHeartbeat(string module)
{
   int idx = HealthModuleIndex(module);

   if(idx < 0)
      return;

   g_wdLastTime[idx] = 0;
   g_wdFailures[idx] = 0;
}

//==================================================
// CHECK HEARTBEAT DE UM MÓDULO (ETAPA 6)
//==================================================

bool HealthMonitorCheckHeartbeatModule(int idx)
{
   if(idx < 0 || idx >= HEALTH_WD_MODULES)
      return true;

   if(!g_wdActive[idx])
      return true;

   // Módulo nunca enviou heartbeat -> não é falha
   if(g_wdLastTime[idx] == 0)
      return true;

   ulong now       = GetTickCount64();
   ulong timeoutMs = (ulong)HealthWatchdogInterval * 1000;

   if(now - g_wdLastTime[idx] > timeoutMs)
   {
      g_wdFailures[idx]++;

      if(g_wdFailures[idx] >= HEALTH_WD_MAX_FAILURES)
      {
         LogWarning(
            "HealthMonitor: módulo sem heartbeat",
            g_wdModuleNames[idx],
            "Segundos=" + IntegerToString((int)((now - g_wdLastTime[idx]) / 1000))
         );

         return false;
      }

      return true;
   }

   g_wdFailures[idx] = 0;

   return true;
}

//==================================================
// CHECK HEARTBEATS (ETAPA 6 — absorve WatchDogRunCheck)
//==================================================

bool HealthMonitorCheckHeartbeats()
{
   bool allOK = true;

   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      if(!HealthMonitorCheckHeartbeatModule(i))
         allOK = false;
   }

   return allOK;
}

//==================================================
// HEALTH CHECK
//==================================================

bool HealthMonitorCheck()
{
   if(!g_healthInitialized)
      return false;

   datetime now = TimeCurrent();

   // Não executa análise completa em todos os ticks.
   if(now - g_lastHealthCheck < HealthCheckInterval)
      return g_healthStatus;

   g_lastHealthCheck = now;
   g_healthCheckCount++;

   bool healthy = true;

   //================================================
   // TICK
   //================================================

   if(!HealthMonitorCheckTickTimeout(15))
   {
      LogWarning("HealthMonitor: tick timeout");
      healthy = false;
   }

   //================================================
   // HEARTBEATS (WatchDog integrado — ETAPA 6)
   //================================================

   if(!HealthMonitorCheckHeartbeats())
      healthy = false;

   //================================================
   // BROKER
   //================================================

   if(g_healthBrokerErrors > 5)
   {
      LogError("HealthMonitor: erros de broker", IntegerToString(g_healthBrokerErrors));
      healthy = false;
   }

   //================================================
   // AI
   //================================================

   if(g_healthAIErrors > 3)
   {
      LogError("HealthMonitor: erros de IA", IntegerToString(g_healthAIErrors));
      healthy = false;
   }

   //================================================
   // DATASET
   //================================================

   if(g_healthDatasetErrors > 2)
   {
      LogError("HealthMonitor: erros de dataset", IntegerToString(g_healthDatasetErrors));
      healthy = false;
   }

   //================================================
   // FILE
   //================================================

   if(g_healthFileErrors > 2)
   {
      LogError("HealthMonitor: erros de arquivo", IntegerToString(g_healthFileErrors));
      healthy = false;
   }

   //================================================
   // JSON
   //================================================

   if(g_healthJSONErrors > 2)
   {
      LogError("HealthMonitor: erros de JSON", IntegerToString(g_healthJSONErrors));
      healthy = false;
   }

   //================================================
   // PYTHON
   //================================================

   if(g_healthPythonErrors > 1)
   {
      LogError("HealthMonitor: erros de Python", IntegerToString(g_healthPythonErrors));
      healthy = false;
   }

   //================================================
   // INDICADORES
   //================================================

   if(g_healthIndicatorErrors > 5)
   {
      LogError("HealthMonitor: erros de indicadores", IntegerToString(g_healthIndicatorErrors));
      healthy = false;
   }

   //================================================
   // RESULTADO
   //================================================

   g_healthStatus      = healthy;
   g_healthLastCheckOK = healthy;

   if(healthy)
      LogInfo("HealthMonitor: HEALTH OK");
   else
      LogWarning("HealthMonitor: HEALTH FAILURE");

   return healthy;
}

//==================================================
// GETTERS
//==================================================

int HealthGetBrokerErrors()
{
   return g_healthBrokerErrors;
}

int HealthGetAIErrors()
{
   return g_healthAIErrors;
}

int HealthGetDatasetErrors()
{
   return g_healthDatasetErrors;
}

int HealthGetFileErrors()
{
   return g_healthFileErrors;
}

int HealthGetJSONErrors()
{
   return g_healthJSONErrors;
}

int HealthGetPythonErrors()
{
   return g_healthPythonErrors;
}

int HealthGetIndicatorErrors()
{
   return g_healthIndicatorErrors;
}

//==================================================
// TICK METRICS
//==================================================

int HealthGetTicksPerSecond()
{
   return g_ticksPerSecond;
}

int HealthGetSecondsSinceTick()
{
   if(!g_healthInitialized)
      return -1;

   return (int)(TimeCurrent() - g_lastTickTime);
}

//==================================================
// UPTIME / MÉTRICAS (ETAPA 6)
//==================================================

ulong HealthGetTotalTicks()
{
   return g_healthTotalTicks;
}

datetime HealthGetUptimeStart()
{
   return g_healthUptimeStart;
}

int HealthGetUptimeSeconds()
{
   if(!g_healthInitialized)
      return 0;

   return (int)(TimeCurrent() - g_healthUptimeStart);
}

ulong HealthGetCheckCount()
{
   return g_healthCheckCount;
}

bool HealthGetLastCheckOK()
{
   return g_healthLastCheckOK;
}

//==================================================
// HEARTBEAT FAILURES (ETAPA 6)
//==================================================

int HealthGetHeartbeatFailures(string module)
{
   int idx = HealthModuleIndex(module);

   if(idx < 0)
      return 0;

   return g_wdFailures[idx];
}

//==================================================
// STATUS
//==================================================

bool HealthIsHealthy()
{
   return g_healthStatus;
}

//==================================================
// SUMMARY
//==================================================

string HealthMonitorSummary()
{
   string summary = "=== HEALTH MONITOR ===\n";

   summary += "Status: " + (g_healthStatus ? "HEALTHY" : "FAILURE") + "\n";
   summary += "Uptime (s): " + IntegerToString(HealthGetUptimeSeconds()) + "\n";
   summary += "Ticks/seg: " + IntegerToString(g_ticksPerSecond) + "\n";
   summary += "Total ticks: " + IntegerToString((long)g_healthTotalTicks) + "\n";
   summary += "Checks: " + IntegerToString((long)g_healthCheckCount) + "\n";
   summary += "Segundos sem tick: " + IntegerToString(HealthGetSecondsSinceTick()) + "\n\n";

   summary += "--- Heartbeats ---\n";

   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      summary += g_wdModuleNames[i] + ": " + IntegerToString(g_wdFailures[i]) + " falhas\n";
   }

   summary += "\n--- Erros ---\n";

   summary += "Broker errors: " + IntegerToString(g_healthBrokerErrors) + "\n";
   summary += "AI errors: " + IntegerToString(g_healthAIErrors) + "\n";
   summary += "Dataset errors: " + IntegerToString(g_healthDatasetErrors) + "\n";
   summary += "File errors: " + IntegerToString(g_healthFileErrors) + "\n";
   summary += "JSON errors: " + IntegerToString(g_healthJSONErrors) + "\n";
   summary += "Python errors: " + IntegerToString(g_healthPythonErrors) + "\n";
   summary += "Indicator errors: " + IntegerToString(g_healthIndicatorErrors);

   return summary;
}

//==================================================
// RESET ERRORS
//==================================================

void HealthMonitorResetErrors()
{
   g_healthBrokerErrors    = 0;
   g_healthAIErrors        = 0;
   g_healthDatasetErrors   = 0;
   g_healthFileErrors      = 0;
   g_healthJSONErrors      = 0;
   g_healthPythonErrors    = 0;
   g_healthIndicatorErrors = 0;

   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      g_wdFailures[i] = 0;
   }

   g_healthStatus      = true;
   g_healthLastCheckOK = true;

   LogSystem("HealthMonitor: contadores resetados");
}

//==================================================
// SHUTDOWN
//==================================================

void HealthMonitorShutdown()
{
   LogSystem(
      "HealthMonitor finalizado | Uptime(s)=" +
      IntegerToString(HealthGetUptimeSeconds()) +
      " | Ticks=" +
      IntegerToString((long)g_healthTotalTicks)
   );

   g_healthInitialized = false;
}

#endif
