#ifndef WATCHDOG_MQH
#define WATCHDOG_MQH

#include "../Tools/Logger.mqh"
#include "../Tools/HealthMonitor.mqh"

//==================================================
// WATCHDOG - FASE 8.5
//
// Reinicializa modulos que apresentarem falha:
//   - AI (reload prediction)
//   - Indicadores (recreate handle)
//   - Python (aguarda novo heartbeat)
//   - CSV/JSON (reabre arquivo)
//   - EquityProtection (aciona se DD critico)
//
// Limite: max 3 tentativas/min por modulo (anti loop).
//==================================================

#define WD_MAX_RETRIES_PER_MIN 3

string g_wdModules[8];
int    g_wdRetryCount[8];
datetime g_wdLastRetry[8];
bool   g_wdModuleInit[8];
int    g_wdModuleCount = 0;

void WatchRegister(string module)
{
   if(g_wdModuleCount >= 8) return;
   for(int i=0; i<g_wdModuleCount; i++)
      if(g_wdModules[i] == module) return;
   g_wdModules[g_wdModuleCount]    = module;
   g_wdRetryCount[g_wdModuleCount] = 0;
   g_wdLastRetry[g_wdModuleCount]  = 0;
   g_wdModuleInit[g_wdModuleCount] = false;
   g_wdModuleCount++;
}

void WatchInit()
{
   g_wdModuleCount = 0;
   WatchRegister("AI");
   WatchRegister("INDICATOR");
   WatchRegister("PYTHON");
   WatchRegister("CSV");
   WatchRegister("JSON");
   WatchRegister("EQUITY");
   LogSystem("WatchDog", "WatchDog inicializado (" +
             IntegerToString(g_wdModuleCount) + " modulos)");
}

int WatchFindModule(string module)
{
   for(int i=0; i<g_wdModuleCount; i++)
      if(g_wdModules[i] == module) return i;
   return -1;
}

bool WatchCanRetry(int idx)
{
   if(idx < 0) return false;
   // Reset contador se passou mais de 60s
   if(TimeCurrent() - g_wdLastRetry[idx] > 60)
      g_wdRetryCount[idx] = 0;
   if(g_wdRetryCount[idx] >= WD_MAX_RETRIES_PER_MIN)
      return false;
   return true;
}

void WatchMarkRetry(int idx)
{
   if(idx < 0) return;
   g_wdRetryCount[idx]++;
   g_wdLastRetry[idx]  = TimeCurrent();
}

//==================================================
// WATCH TICK (executa a cada OnTick; rapido)
//==================================================
bool WatchTick()
{
   if(g_wdModuleCount == 0)
      return true;

   bool allHealthy = true;

   // Verifica AI
   int idxAI = WatchFindModule("AI");
   if(idxAI >= 0 && HealthStatusFromIdx(2) == HEALTH_ERROR)
   {
      if(WatchCanRetry(idxAI))
      {
         WatchMarkRetry(idxAI);
         LogWarn("WatchDog", "AI com problema - tentativa " +
                 IntegerToString(g_wdRetryCount[idxAI]) + " de reload");
         // AI sera recarregada no proximo LoadAIPrediction()
      }
      else
      {
         LogError("WatchDog", "AI sem recovery apos " +
                  IntegerToString(WD_MAX_RETRIES_PER_MIN) + " tentativas");
         allHealthy = false;
      }
   }

   // Verifica INDICATOR
   int idxInd = WatchFindModule("INDICATOR");
   if(idxInd >= 0 && HealthStatusFromIdx(5) == HEALTH_ERROR)
   {
      if(WatchCanRetry(idxInd))
      {
         WatchMarkRetry(idxInd);
         LogWarn("WatchDog", "Indicadores com handle invalido - recriacao na proxima chamada");
      }
      else
      {
         LogError("WatchDog", "Indicadores nao recuperados");
         allHealthy = false;
      }
   }

   // Verifica PYTHON
   int idxPy = WatchFindModule("PYTHON");
   if(idxPy >= 0 && HealthStatusFromIdx(4) == HEALTH_ERROR)
   {
      if(WatchCanRetry(idxPy))
      {
         WatchMarkRetry(idxPy);
         LogWarn("WatchDog", "Python heartbeat ausente - aguardando novo heartbeat");
      }
   }

   return allHealthy;
}

string WatchGetLog()
{
   string out = "WatchDog=";
   int totalRetries = 0;
   for(int i=0; i<g_wdModuleCount; i++)
      totalRetries += g_wdRetryCount[i];
   out += IntegerToString(totalRetries) + " retries total";
   return out;
}

void WatchClose()
{
   LogInfo("WatchDog", "WatchDog fechado");
   g_wdModuleCount = 0;
}

#endif
