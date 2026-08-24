#ifndef HEALTHMONITOR_MQH
#define HEALTHMONITOR_MQH

#include "../Tools/Logger.mqh"

//==================================================
// HEALTH MONITOR - FASE 8.4
//
// Monitora saude dos modulos criticos do EA.
// Atualiza um snapshot JSON e dispara WatchDog/FailSafe
// quando detecta anomalia.
//
// Categorias monitoradas:
//   - TICK        (tempo sem tick)
//   - BROKER      (conexao, ultimo erro)
//   - AI          (prediction_*.json presente e fresco)
//   - DATASET     (dataset.csv legivel)
//   - PYTHON      (heartbeat do pipeline Python)
//   - INDICATOR   (handles ATR/ADX/RSI validos)
//   - MEMORY      (uso de RAM do terminal)
//   - LATENCY     (tempo de processamento de OnTick)
//
// API:
//   HealthInit(ttlSeconds=60)
//   HealthTick(symbol)         // chamada rapida em OnTick
//   HealthSlowCheck(symbols)   // chamada a cada ~60s
//   HealthGetStatusJSON()      // snapshot para arquivo/dashboard
//   HealthIsCritical()         // true se alguma categoria em ERROR
//==================================================

enum ENUM_HEALTH_STATUS
{
   HEALTH_OK    = 0,
   HEALTH_WARN  = 1,
   HEALTH_ERROR = 2
};

#define HEALTH_CAT_COUNT 8

string g_healthCategories[HEALTH_CAT_COUNT] = {
   "TICK", "BROKER", "AI", "DATASET",
   "PYTHON", "INDICATOR", "MEMORY", "LATENCY"
};
int    g_healthStatus[HEALTH_CAT_COUNT];
string g_healthDetail[HEALTH_CAT_COUNT];
datetime g_healthLastCheck[HEALTH_CAT_COUNT];
datetime g_healthLastTick = 0;
datetime g_healthLastSlowCheck = 0;
int    g_healthTickTimeoutSec = 30;   // > 30s sem tick = ERROR
int    g_healthAITTLSec       = 3600; // 1h sem prediction = ERROR
int    g_healthPythonTTLSec   = 600;  // 10 min sem heartbeat = WARN
int    g_healthMemWarnPct     = 70;
int    g_healthMemErrorPct    = 90;
int    g_healthLatencyWarnMs  = 50;
int    g_healthLatencyErrorMs = 100;
int    g_healthLastOnTickMs   = 0;
int    g_healthInitialized    = 0;
datetime g_healthInitTime     = 0;

void HealthSetStatus(int idx, ENUM_HEALTH_STATUS st, string detail)
{
   g_healthStatus[idx]    = (int)st;
   g_healthDetail[idx]    = detail;
   g_healthLastCheck[idx] = TimeCurrent();
}

ENUM_HEALTH_STATUS HealthStatusFromIdx(int idx)
{
   if(idx < 0 || idx >= HEALTH_CAT_COUNT)
      return HEALTH_ERROR;
   return (ENUM_HEALTH_STATUS)g_healthStatus[idx];
}

string HealthStatusToStr(ENUM_HEALTH_STATUS st)
{
   if(st == HEALTH_OK)    return "OK";
   if(st == HEALTH_WARN)  return "WARN";
   return "ERROR";
}

bool HealthInit(int ttlSeconds=60)
{
   g_healthInitialized    = 1;
   g_healthInitTime       = TimeCurrent();
   g_healthLastTick       = TimeCurrent();
   g_healthLastSlowCheck  = 0;
   g_healthTickTimeoutSec = 30;
   g_healthAITTLSec       = 3600;
   g_healthPythonTTLSec   = 600;
   g_healthMemWarnPct     = 70;
   g_healthMemErrorPct    = 90;
   g_healthLatencyWarnMs  = 50;
   g_healthLatencyErrorMs = 100;
   g_healthLastOnTickMs   = 0;

   for(int i=0; i<HEALTH_CAT_COUNT; i++)
   {
      g_healthStatus[i]    = (int)HEALTH_OK;
      g_healthDetail[i]    = "init";
      g_healthLastCheck[i] = TimeCurrent();
   }
   LogSystem("Health", "HealthMonitor inicializado (ttl=" +
             IntegerToString(ttlSeconds) + "s)");
   return true;
}

//==================================================
// HEALTH TICK (rapido - cada OnTick)
//==================================================
void HealthTick(string symbol="")
{
   if(!g_healthInitialized)
      return;

   uint t0 = GetTickCount();
   g_healthLastTick = TimeCurrent();

   // 1) TICK - checar intervalo desde o ultimo tick
   int idleSec = (int)(TimeCurrent() - g_healthLastTick);
   if(idleSec > g_healthTickTimeoutSec)
      HealthSetStatus(0, HEALTH_ERROR,
         "Sem tick ha " + IntegerToString(idleSec) + "s");
   else if(idleSec > g_healthTickTimeoutSec/2)
      HealthSetStatus(0, HEALTH_WARN,
         "Tick lento (" + IntegerToString(idleSec) + "s)");
   else
      HealthSetStatus(0, HEALTH_OK, "ativo");

   // 2) BROKER
   bool connected = (bool)TerminalInfoInteger(TERMINAL_CONNECTED);
   if(!connected)
      HealthSetStatus(1, HEALTH_ERROR, "Desconectado");
   else
   {
      int lastErr = GetLastError();
      if(lastErr != 0)
         HealthSetStatus(1, HEALTH_WARN,
            "GetLastError=" + IntegerToString(lastErr));
      else
         HealthSetStatus(1, HEALTH_OK, "conectado");
   }

   // latencia (medida entre o inicio e o fim do OnTick)
   g_healthLastOnTickMs = (int)(GetTickCount() - t0);
   if(g_healthLastOnTickMs > g_healthLatencyErrorMs)
      HealthSetStatus(7, HEALTH_ERROR,
         "OnTick=" + IntegerToString(g_healthLastOnTickMs) + "ms");
   else if(g_healthLastOnTickMs > g_healthLatencyWarnMs)
      HealthSetStatus(7, HEALTH_WARN,
         "OnTick=" + IntegerToString(g_healthLastOnTickMs) + "ms");
   else
      HealthSetStatus(7, HEALTH_OK,
         IntegerToString(g_healthLastOnTickMs) + "ms");
}

//==================================================
// HEALTH SLOW CHECK (~60s) - IA, Dataset, Python, Indicadores, Memoria
//==================================================
void HealthSlowCheck(string &symbols[], int symbolCount)
{
   if(!g_healthInitialized)
      return;

   // nao rodar mais que 1x por 30s
   if(TimeCurrent() - g_healthLastSlowCheck < 30)
      return;
   g_healthLastSlowCheck = TimeCurrent();

   // 2) AI - verificar idade do prediction mais recente
   datetime freshestPrediction = 0;
   int aiFiles = 0;
   for(int i=0; i<symbolCount; i++)
   {
      string fn = "Data\\prediction_" + symbols[i] + ".json";
      if(FileIsExist(fn))
      {
         aiFiles++;
         int h = FileOpen(fn, FILE_READ|FILE_TXT|FILE_ANSI);
         if(h != INVALID_HANDLE)
         {
            datetime ft = (datetime)FileGetInteger(h, FILE_MODIFY_DATE);
            if(ft > freshestPrediction) freshestPrediction = ft;
            FileClose(h);
         }
      }
   }
   if(aiFiles == 0)
      HealthSetStatus(2, HEALTH_WARN, "Nenhum prediction_*.json");
   else
   {
      int ageSec = (int)(TimeCurrent() - freshestPrediction);
      if(ageSec > g_healthAITTLSec)
         HealthSetStatus(2, HEALTH_ERROR,
            "Predictions stale ha " + IntegerToString(ageSec) + "s (" +
            IntegerToString(aiFiles) + " arquivos)");
      else if(ageSec > g_healthAITTLSec/4)
         HealthSetStatus(2, HEALTH_WARN,
            "Predictions " + IntegerToString(ageSec) + "s antigas");
      else
         HealthSetStatus(2, HEALTH_OK,
            IntegerToString(aiFiles) + " arquivos, " +
            IntegerToString(ageSec) + "s");
   }

   // 3) DATASET
   string dsPath = "Data\\dataset.csv";
   if(!FileIsExist(dsPath))
      HealthSetStatus(3, HEALTH_ERROR, "dataset.csv ausente");
   else
   {
      int h = FileOpen(dsPath, FILE_READ|FILE_CSV|FILE_ANSI);
      if(h == INVALID_HANDLE)
         HealthSetStatus(3, HEALTH_ERROR, "dataset.csv nao abre");
      else
      {
         long sz = FileSize(h);
         FileClose(h);
         if(sz < 100)
            HealthSetStatus(3, HEALTH_WARN,
               "dataset.csv muito pequeno (" + IntegerToString((int)sz) + "B)");
         else
            HealthSetStatus(3, HEALTH_OK,
               IntegerToString((int)sz) + "B");
      }
   }

   // 4) PYTHON - heartbeat
   string hbPath = "python_heartbeat.txt";
   if(FileIsExist(hbPath))
   {
      int h = FileOpen(hbPath, FILE_READ|FILE_TXT|FILE_ANSI);
      if(h != INVALID_HANDLE)
      {
         datetime ft = (datetime)FileGetInteger(h, FILE_MODIFY_DATE);
         FileClose(h);
         int ageSec = (int)(TimeCurrent() - ft);
         if(ageSec > g_healthPythonTTLSec)
            HealthSetStatus(4, HEALTH_WARN,
               "Python heartbeat stale " + IntegerToString(ageSec) + "s");
         else
            HealthSetStatus(4, HEALTH_OK,
               IntegerToString(ageSec) + "s atras");
      }
      else
         HealthSetStatus(4, HEALTH_WARN, "heartbeat nao abre");
   }
   else
      HealthSetStatus(4, HEALTH_WARN, "sem heartbeat do Python");

   // 5) INDICATORS - chamado em XAU_AI_PRO.mq5 via HealthCheckIndicators()
   //     feito externamente; aqui so marcamos OK se funcao externa setar

   // 6) MEMORY
   long memUsed  = TerminalInfoInteger(TERMINAL_MEMORY_USED);
   long memTotal = TerminalInfoInteger(TERMINAL_MEMORY_LIMIT);
   if(memTotal > 0)
   {
      int pct = (int)((memUsed * 100) / memTotal);
      if(pct > g_healthMemErrorPct)
         HealthSetStatus(6, HEALTH_ERROR,
            "RAM " + IntegerToString(pct) + "%");
      else if(pct > g_healthMemWarnPct)
         HealthSetStatus(6, HEALTH_WARN,
            "RAM " + IntegerToString(pct) + "%");
      else
         HealthSetStatus(6, HEALTH_OK,
            IntegerToString(pct) + "%");
   }
   else
      HealthSetStatus(6, HEALTH_OK, "n/a");
}

//==================================================
// HEALTH CHECK INDICATORS (chamado de XAU_AI_PRO.mq5)
//==================================================
void HealthCheckIndicators(int atrHandle, int adxHandle, int rsiHandle)
{
   string detail = "";
   ENUM_HEALTH_STATUS worst = HEALTH_OK;
   if(atrHandle == INVALID_HANDLE) { worst = HEALTH_ERROR; detail += "ATR "; }
   if(adxHandle == INVALID_HANDLE) { worst = HEALTH_ERROR; detail += "ADX "; }
   if(rsiHandle == INVALID_HANDLE) { worst = HEALTH_ERROR; detail += "RSI "; }
   if(worst == HEALTH_ERROR)
      HealthSetStatus(5, HEALTH_ERROR, "Handles invalidos: " + detail);
   else
      HealthSetStatus(5, HEALTH_OK, "ATR/ADX/RSI OK");
}

//==================================================
// HEALTH IS CRITICAL
//==================================================
bool HealthIsCritical()
{
   for(int i=0; i<HEALTH_CAT_COUNT; i++)
      if(g_healthStatus[i] == (int)HEALTH_ERROR)
         return true;
   return false;
}

bool HealthIsWarn()
{
   for(int i=0; i<HEALTH_CAT_COUNT; i++)
      if(g_healthStatus[i] == (int)HEALTH_WARN)
         return true;
   return false;
}

//==================================================
// HEALTH GET JSON
//==================================================
string HealthGetStatusJSON()
{
   string json = "{";
   json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",";
   json += "\"initialized\":" + (g_healthInitialized ? "true" : "false") + ",";
   json += "\"uptime_sec\":" + IntegerToString((int)(TimeCurrent() - g_healthInitTime)) + ",";
   json += "\"critical\":" + (HealthIsCritical() ? "true" : "false") + ",";
   json += "\"categories\":[";
   for(int i=0; i<HEALTH_CAT_COUNT; i++)
   {
      if(i > 0) json += ",";
      json += "{\"name\":\"" + g_healthCategories[i] + "\",";
      json += "\"status\":\"" + HealthStatusToStr(HealthStatusFromIdx(i)) + "\",";
      json += "\"detail\":\"" + g_healthDetail[i] + "\"}";
   }
   json += "]}";
   return json;
}

string HealthGetStatusCSV()
{
   string csv = "Category,Status,Detail\n";
   for(int i=0; i<HEALTH_CAT_COUNT; i++)
   {
      csv += g_healthCategories[i] + "," +
             HealthStatusToStr(HealthStatusFromIdx(i)) + "," +
             g_healthDetail[i] + "\n";
   }
   return csv;
}

void HealthClose()
{
   g_healthInitialized = 0;
   LogInfo("Health", "HealthMonitor fechado");
}

#endif
