//+------------------------------------------------------------------+
//|                                                    Telemetry.mqh |
//|                                  System Telemetry Monitor        |
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+
// ETAPA 15.6.1/15.6.3 - TELEMETRIA REAL (NO FALSIFICADA)
//
// PRINCIPIOS:
//   1. Nunca falsificar metricas. CPU/memoria del proceso SIN fuente
//      confiable -> se reportan como UNAVAILABLE (no 0).
//   2. Estado multi-nivel (15.6.5): HEALTHY / WARNING / ERROR / SAFE /
//      RECOVERY / UNAVAILABLE - no solo true/false.
//   3. Metricas REALES del sistema (las que MQL5 sabe medir):
//      uptime, ticks, trades, rechazos, latencias (Broker/Python/DB/AI),
//      fallos de ejecucion, recovery/SAFE, drawdown.

#include "../Core/Config.mqh"
#include "../Core/RiskHub.mqh"

#ifndef TELEMETRY_MQH
#define TELEMETRY_MQH

//==================================================
// ESTADO DE SALUD (15.6.5) - multi-nivel
//==================================================
enum ENUM_TELEMETRY_STATE
{
   TM_HEALTHY     = 0,
   TM_WARNING     = 1,
   TM_ERROR       = 2,
   TM_SAFE        = 3,
   TM_RECOVERY    = 4,
   TM_UNAVAILABLE = 5
};

struct TelemetryMetric
{
   string              name;
   double              value;
   string              unit;
   datetime            timestamp;
   ENUM_TELEMETRY_STATE state;   // 15.6.5: multi-estado, no bool
};

class CTelemetry
{
private:

   static TelemetryMetric m_metrics[];
   static int             m_metric_count;
   static bool            m_initialized;
   static datetime        m_last_check;
   static int             m_check_interval_sec;

   // Contadores reales del proceso (15.6.3)
   static int             m_uptimeStart;
   static long            m_tickCount;
   static int             m_tradeOpenCount;
   static int             m_tradeCloseCount;
   static int             m_rejectionCount;
   static int             m_errorCount;
   static int             m_recoveryCount;
   static int             m_safeCount;
   static double          m_peakDrawdown;
   static double          m_peakEquity;

   static void AddMetric(string name, double value, string unit);
   static void CheckHealth();

public:

   static void Init();
   static void Run();

   // Setters reales (15.6.3)
   static void RecordExecutionStart();     // uptime (trading day)
   static void RecordTick();               // ticks
   static void RecordTradeOpen();
   static void RecordTradeClose();
   static void RecordTradeRejected();
   static void RecordError();
   static void RecordRecovery();
   static void RecordSafe();                  // entrada a SAFE MODE
   static void RecordDrawdown(double pct);   // pico pct (0-100)

   static double GetMetric(string name);
   static ENUM_TELEMETRY_STATE GetState(string name);
   static bool IsHealthy(string name);        // HEALTHY o WARNING

   static void RecordExecutionTime(string operation, int ms);
   static void RecordLatency(string target, int ms);
   static void RecordBrokerLatency(int ms);
   static void RecordPythonLatency(int ms);
   static void RecordDatabaseLatency(int ms);
   static void RecordAILatency(int ms);

   static string GetSummary();
   static void LogSummary();
};

//==================================================
// STATIC INIT
//==================================================
TelemetryMetric CTelemetry::m_metrics[];
int             CTelemetry::m_metric_count = 0;
bool            CTelemetry::m_initialized  = false;
datetime        CTelemetry::m_last_check   = 0;
int             CTelemetry::m_check_interval_sec = 10;

int    CTelemetry::m_uptimeStart     = 0;
long   CTelemetry::m_tickCount       = 0;
int    CTelemetry::m_tradeOpenCount  = 0;
int    CTelemetry::m_tradeCloseCount = 0;
int    CTelemetry::m_rejectionCount  = 0;
int    CTelemetry::m_errorCount      = 0;
int    CTelemetry::m_recoveryCount   = 0;
int    CTelemetry::m_safeCount       = 0;
double CTelemetry::m_peakDrawdown    = 0.0;
double CTelemetry::m_peakEquity      = 0.0;

//==================================================
// INIT
//==================================================
void CTelemetry::Init()
{
   if(m_initialized)
      return;

   ArrayResize(m_metrics, 32);
   m_metric_count = 0;
   m_last_check   = 0;
   m_initialized  = true;

   // Reset de contadores reales
   m_uptimeStart    = 0;
   m_tickCount      = 0;
   m_tradeOpenCount = 0;
   m_tradeCloseCount= 0;
   m_rejectionCount = 0;
   m_errorCount     = 0;
   m_recoveryCount  = 0;
   m_safeCount      = 0;
   m_peakDrawdown   = 0.0;
   m_peakEquity     = AccountInfoDouble(ACCOUNT_EQUITY);

   Print("[TELEMETRY] Real telemetry initialized (15.6)");
}

//==================================================
// ADD / UPDATE METRIC
//==================================================
void CTelemetry::AddMetric(string name, double value, string unit)
{
   if(!m_initialized)
      Init();

   for(int i = 0; i < m_metric_count; i++)
   {
      if(m_metrics[i].name == name)
      {
         m_metrics[i].value     = value;
         m_metrics[i].unit      = unit;
         m_metrics[i].timestamp = TimeCurrent();
         // Mantener estado previo; CheckHealth() lo recalcula
         return;
      }
   }

   if(m_metric_count >= ArraySize(m_metrics))
   {
      Print("[TELEMETRY] Metric buffer full: ", name);
      return;
   }

   TelemetryMetric metric;
   metric.name      = name;
   metric.value     = value;
   metric.unit      = unit;
   metric.timestamp = TimeCurrent();
   metric.state     = TM_HEALTHY;

   m_metrics[m_metric_count] = metric;
   m_metric_count++;
}

//==================================================
// RUN (llamado por el EA periodicamente)
//==================================================
void CTelemetry::Run()
{
   if(!m_initialized)
      Init();

   datetime now = TimeCurrent();
   if(m_last_check > 0 && now - m_last_check < m_check_interval_sec)
      return;
   m_last_check = now;

   //--- Metricas REALES (15.6.3): uptime, ticks, trades, errores
   if(m_uptimeStart == 0)
      m_uptimeStart = (int)TimeCurrent();
   int uptimeSec = (int)(TimeCurrent() - (datetime)m_uptimeStart);
   AddMetric("Uptime",      uptimeSec,           "s");
   AddMetric("Ticks",       (double)m_tickCount, "count");
   AddMetric("TradesOpen",  m_tradeOpenCount,    "count");
   AddMetric("TradesClosed",m_tradeCloseCount,   "count");
   AddMetric("Rejections",  m_rejectionCount,    "count");
   AddMetric("Errors",      m_errorCount,        "count");
   AddMetric("Recoveries",  m_recoveryCount,     "count");
   AddMetric("SafeEntries", m_safeCount,         "count");
   AddMetric("PeakDD",      m_peakDrawdown,      "%");

   // Uptime como metrica (ms) ya existente? No duplicar con Latency.

   // NOTE: Fake metrics ya removidas (CPU/Memory -> UNAVAILABLE, 15.6.3)
   AddMetric("CPU",     -1.0, "%");     // -1 = UNAVAILABLE
   AddMetric("Memory",  -1.0, "bytes"); // -1 = UNAVAILABLE

   //--- ETAPA 15.6.3: drawdown REAL via fonte unica (RiskHub)
   double ddCurrent = GetDrawdownPercent();
   RecordDrawdown(ddCurrent);
   AddMetric("DD_Current", ddCurrent, "%");

   CheckHealth();
}

//==================================================
// HEALTH CHECK - multi-estado (15.6.5)
//==================================================
void CTelemetry::CheckHealth()
{
   for(int i = 0; i < m_metric_count; i++)
   {
      string n = m_metrics[i].name;
      double v = m_metrics[i].value;

      // UNAVAILABLE si valor negativo y se trata de CPU/Memory
      if((n == "CPU" || n == "Memory") && v < 0.0)
      {
         m_metrics[i].state = TM_UNAVAILABLE;
         continue;
      }

      // Default: HEALTHY
      m_metrics[i].state = TM_HEALTHY;

      if(n == "Uptime")
      {
         // uptime alto sin comercio => WARNING? uptime no limita.
         continue;
      }

      if(StringFind(n, "Latency") >= 0)
      {
         if(v > 1000.0)
            m_metrics[i].state = TM_ERROR;       // >1s = error de latencia
         else if(v > 500.0)
            m_metrics[i].state = TM_WARNING;     // 500-1000 = warning
         continue;
      }

      if(StringFind(n, "Exec_") == 0)
      {
         if(v > 2000.0)
            m_metrics[i].state = TM_ERROR;
         else if(v > 1000.0)
            m_metrics[i].state = TM_WARNING;
         continue;
      }

      if(n == "Errors" || n == "Rejections")
      {
         if(v > 20.0)
            m_metrics[i].state = TM_ERROR;
         else if(v > 5.0)
            m_metrics[i].state = TM_WARNING;
         continue;
      }

      if(n == "SafeEntries")
      {
         if(v > 0.0)
            m_metrics[i].state = TM_SAFE;   // SAFE mode signalizado
         continue;
      }

      // ETAPA 15.6.1 FIX: metrica chama-se "Recoveries" (Run),
      // nao "Recovery". Antes nunca casava.
      if(n == "Recoveries")
      {
         if(v > 0.0)
            m_metrics[i].state = TM_RECOVERY;
         continue;
      }

      if(n == "PeakDD" || n == "DD_Current")
      {
         if(v > 10.0)
            m_metrics[i].state = TM_ERROR;
         else if(v > 5.0)
            m_metrics[i].state = TM_WARNING;
      }
   }
}

//==================================================
// SETTERS REALES (15.6.3)
//==================================================
void CTelemetry::RecordExecutionStart()
{
   m_uptimeStart = (int)TimeCurrent();
   m_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
}

void CTelemetry::RecordTick()
{
   m_tickCount++;
}

void CTelemetry::RecordTradeOpen()
{
   m_tradeOpenCount++;
}

void CTelemetry::RecordTradeClose()
{
   m_tradeCloseCount++;
}

void CTelemetry::RecordTradeRejected()
{
   m_rejectionCount++;
}

void CTelemetry::RecordError()
{
   m_errorCount++;
}

void CTelemetry::RecordRecovery()
{
   m_recoveryCount++;
}

void CTelemetry::RecordSafe()
{
   m_safeCount++;
}

void CTelemetry::RecordDrawdown(double pct)
{
   if(pct > m_peakDrawdown)
      m_peakDrawdown = pct;
}

//==================================================
// GET METRIC
//==================================================
double CTelemetry::GetMetric(string name)
{
   if(!m_initialized)
      Init();
   for(int i = 0; i < m_metric_count; i++)
      if(m_metrics[i].name == name)
         return m_metrics[i].value;
   return 0.0;
}

//==================================================
// GET STATE (15.6.5)
//==================================================
ENUM_TELEMETRY_STATE CTelemetry::GetState(string name)
{
   if(!m_initialized)
      Init();
   for(int i = 0; i < m_metric_count; i++)
      if(m_metrics[i].name == name)
         return m_metrics[i].state;
   return TM_UNAVAILABLE;
}

//==================================================
// HEALTH (true = HEALTHY o WARNING; false = resto)
//==================================================
bool CTelemetry::IsHealthy(string name)
{
   ENUM_TELEMETRY_STATE s = GetState(name);
   return (s == TM_HEALTHY || s == TM_WARNING);
}

//==================================================
// LATENCIA / TIEMPO (con tipo int ms, no double)
//==================================================
void CTelemetry::RecordExecutionTime(string operation, int ms)
{
   AddMetric("Exec_" + operation, (double)ms, "ms");
}

void CTelemetry::RecordLatency(string target, int ms)
{
   AddMetric("Latency_" + target, (double)ms, "ms");
}

void CTelemetry::RecordBrokerLatency(int ms)  { AddMetric("Broker_Latency", (double)ms, "ms"); }
void CTelemetry::RecordPythonLatency(int ms)  { AddMetric("Python_Latency", (double)ms, "ms"); }
void CTelemetry::RecordDatabaseLatency(int ms){ AddMetric("DB_Latency",     (double)ms, "ms"); }
void CTelemetry::RecordAILatency(int ms)       { AddMetric("AI_Latency",     (double)ms, "ms"); }

//==================================================
// SUMMARY / LOG (multi-estado textual)
//==================================================
string CTelemetry::GetSummary()
{
   if(!m_initialized)
      Init();

   string result = StringFormat("Metrics: %d | ", m_metric_count);
   for(int i = 0; i < m_metric_count; i++)
   {
      string stxt;
      switch(m_metrics[i].state)
      {
         case TM_HEALTHY:     stxt = "OK";     break;
         case TM_WARNING:     stxt = "WARN";   break;
         case TM_ERROR:       stxt = "ERROR";  break;
         case TM_SAFE:        stxt = "SAFE";   break;
         case TM_RECOVERY:    stxt = "REC";    break;
         case TM_UNAVAILABLE: stxt = "NA";     break;
         default:             stxt = "?";      break;
      }
      result += StringFormat("%s: %.1f%s(%s) ", m_metrics[i].name,
                             m_metrics[i].value, m_metrics[i].unit, stxt);
   }
   return result;
}

void CTelemetry::LogSummary()
{
   Print("[TELEMETRY] ", GetSummary());
}

#endif // TELEMETRY_MQH