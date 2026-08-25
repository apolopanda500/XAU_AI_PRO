//+------------------------------------------------------------------+
//| ProductionChecklist.mqh                                         |
//| XAU_AI_PRO - Production Readiness Checklist (ETAPA 10 v2.0)     |
//| Checagens reais de config, indicadores, IA/Python, dataset,     |
//| execucao, risco, notificacoes, auditoria e ambiente.            |
//+------------------------------------------------------------------+
#property copyright "XAU_AI_PRO"
#property version   "1.20"

#ifndef PRODUCTION_CHECKLIST_MQH
#define PRODUCTION_CHECKLIST_MQH

#include "../Core/Config.mqh"

//==================================================
// CLASSE (arrays paralelos - seguro em MQL5)
//==================================================

class CProductionChecklist
{
private:

   static string m_names[];
   static bool   m_passed[];
   static string m_messages[];
   static bool   m_critical[];
   static int    m_item_count;
   static bool   m_initialized;
   static bool   m_all_passed;

   static void SetResult(int idx, bool passed, string message);

public:

   static void Init();

   static bool Run();

   static bool IsReady();

   static string GetSummary();

   static void LogResults();

   static int GetPassedCount();

   static int GetFailedCount();

   static int GetCriticalFailedCount();

   static void CheckBroker();

   static void CheckAccount();

   static void CheckPermissions();

   static void CheckSymbols();

   static void CheckIndicators();

   static void CheckAI();

   static void CheckPython();

   static void CheckDataset();

   static void CheckJSON();

   static void CheckLogs();

   static void CheckRisk();

   static void CheckExecution();

   static void CheckNotifications();

   static void CheckAudit();

   static void CheckDashboard();

   static void CheckScanner();

   static void CheckPerformance();
};

//==================================================
// VARIAVEIS ESTATICAS
//==================================================

string CProductionChecklist::m_names[];
bool   CProductionChecklist::m_passed[];
string CProductionChecklist::m_messages[];
bool   CProductionChecklist::m_critical[];
int    CProductionChecklist::m_item_count = 0;
bool   CProductionChecklist::m_initialized = false;
bool   CProductionChecklist::m_all_passed = false;

//==================================================
// HELPERS
//==================================================

void CProductionChecklist::SetResult(int idx, bool passed, string message)
{
   if(idx < 0 || idx >= m_item_count)
      return;
   m_passed[idx]   = passed;
   m_messages[idx] = message;
}

//==================================================
// INIT
//==================================================

void CProductionChecklist::Init()
{
   if(m_initialized)
      return;

   ArrayResize(m_names, 17);
   ArrayResize(m_passed, 17);
   ArrayResize(m_messages, 17);
   ArrayResize(m_critical, 17);

   m_item_count = 17;

   // CRITICOS
   m_names[0]  = "Broker";          m_critical[0] = true;
   m_names[1]  = "Account";         m_critical[1] = true;
   m_names[2]  = "Permissions";     m_critical[2] = true;
   m_names[3]  = "Symbols";         m_critical[3] = true;
   m_names[4]  = "Indicators";      m_critical[4] = true;

   // NAO CRITICOS
   m_names[5]  = "AI";              m_critical[5] = false;
   m_names[6]  = "Python";          m_critical[6] = false;
   m_names[7]  = "Dataset";         m_critical[7] = false;
   m_names[8]  = "JSON";            m_critical[8] = false;
   m_names[9]  = "Logs";            m_critical[9] = false;

   // CRITICOS
   m_names[10] = "Risk";            m_critical[10] = true;
   m_names[11] = "Execution";       m_critical[11] = true;

   // NAO CRITICOS
   m_names[12] = "Notifications";   m_critical[12] = false;
   m_names[13] = "Audit";           m_critical[13] = false;
   m_names[14] = "Dashboard";       m_critical[14] = false;
   m_names[15] = "Scanner";         m_critical[15] = false;
   m_names[16] = "Performance";     m_critical[16] = false;

   for(int i = 0; i < m_item_count; i++)
   {
      m_passed[i]   = false;
      m_messages[i] = "pendente";
   }

   m_initialized = true;

   Print("[CHECKLIST] ProductionChecklist inicializado (17 itens)");
}

//==================================================
// RUN
//==================================================

bool CProductionChecklist::Run()
{
   if(!m_initialized)
      Init();

   CheckBroker();
   CheckAccount();
   CheckPermissions();
   CheckSymbols();
   CheckIndicators();

   CheckAI();
   CheckPython();
   CheckDataset();
   CheckJSON();
   CheckLogs();

   CheckRisk();
   CheckExecution();

   CheckNotifications();
   CheckAudit();
   CheckDashboard();
   CheckScanner();
   CheckPerformance();

   m_all_passed = true;

   for(int i = 0; i < m_item_count; i++)
   {
      if(!m_passed[i] && m_critical[i])
      {
         m_all_passed = false;
         break;
      }
   }

   LogResults();

   return m_all_passed;
}

//==================================================
// READY
//==================================================

bool CProductionChecklist::IsReady()
{
   return m_all_passed;
}

//==================================================
// BROKER
//==================================================

void CProductionChecklist::CheckBroker()
{
   bool ok = (TerminalInfoInteger(TERMINAL_CONNECTED) != 0);

   SetResult(0, ok, ok ? "Terminal conectado" : "Terminal desconectado");
}

//==================================================
// ACCOUNT
//==================================================

void CProductionChecklist::CheckAccount()
{
   long login = AccountInfoInteger(ACCOUNT_LOGIN);

   bool ok = (login > 0);

   SetResult(1, ok, ok ? ("Conta OK: " + IntegerToString(login)) : "Conta nao identificada");
}

//==================================================
// PERMISSIONS
//==================================================

void CProductionChecklist::CheckPermissions()
{
   bool terminalTrade = (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   bool accountTrade  = (AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) != 0);

   bool ok = terminalTrade && accountTrade;

   SetResult(2, ok, ok ? "Trading permitido" : "Trading nao permitido (Algoritmos OFF?)");
}

//==================================================
// SYMBOL
//==================================================

void CProductionChecklist::CheckSymbols()
{
   string symbol = _Symbol;

   bool selected = SymbolSelect(symbol, true);

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);

   bool ok = selected && bid > 0.0 && ask > 0.0;

   SetResult(3, ok, ok ? ("Symbol OK: " + symbol) : "Symbol sem cotacao");
}

//==================================================
// INDICATORS (ATR + ADX + RSI reais)
//==================================================

void CProductionChecklist::CheckIndicators()
{
   int hATR = iATR(_Symbol, PERIOD_CURRENT, ATRPeriod);
   int hADX = iADX(_Symbol, PERIOD_CURRENT, ADXPeriod);
   int hRSI = iRSI(_Symbol, PERIOD_CURRENT, RSIPeriod, PRICE_CLOSE);

   bool ok = (hATR != INVALID_HANDLE) && (hADX != INVALID_HANDLE) && (hRSI != INVALID_HANDLE);

   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
   if(hADX != INVALID_HANDLE) IndicatorRelease(hADX);
   if(hRSI != INVALID_HANDLE) IndicatorRelease(hRSI);

   SetResult(4, ok, ok ? "ATR+ADX+RSI handles OK" : "Falha ao criar handles de indicadores");
}

//==================================================
// AI (prediction JSON do simbolo)
//==================================================

void CProductionChecklist::CheckAI()
{
   string file = "Data\\prediction_" + _Symbol + ".json";

   bool ok = FileIsExist(file, FILE_COMMON);

   SetResult(5, ok, ok ? "Prediction JSON encontrado" : "Prediction JSON nao encontrado (IA offline)");
}

//==================================================
// PYTHON (pipeline: prediction + dataset)
//==================================================

void CProductionChecklist::CheckPython()
{
   string pred = "Data\\prediction_" + _Symbol + ".json";
   string ds   = "Data\\dataset.csv";

   bool ok = FileIsExist(pred, FILE_COMMON) && FileIsExist(ds, FILE_COMMON);

   SetResult(6, ok, ok ? "Pipeline Python: prediction + dataset OK" : "Pipeline Python incompleto");
}

//==================================================
// DATASET
//==================================================

void CProductionChecklist::CheckDataset()
{
   string file = "Data\\dataset.csv";

   bool ok = false;

   if(FileIsExist(file, FILE_COMMON))
   {
      int h = FileOpen(file, FILE_READ | FILE_BIN | FILE_COMMON);

      if(h != INVALID_HANDLE)
      {
         ok = (FileSize(h) > 0);
         FileClose(h);
      }
   }

   SetResult(7, ok, ok ? "Dataset OK" : "Dataset ausente ou vazio");
}

//==================================================
// JSON
//==================================================

void CProductionChecklist::CheckJSON()
{
   string file = "Data\\prediction_" + _Symbol + ".json";

   bool ok = false;

   if(FileIsExist(file, FILE_COMMON))
   {
      int h = FileOpen(file, FILE_READ | FILE_BIN | FILE_COMMON);

      if(h != INVALID_HANDLE)
      {
         ok = (FileSize(h) > 0);
         FileClose(h);
      }
   }

   SetResult(8, ok, ok ? "JSON acessivel" : "JSON ausente ou vazio");
}

//==================================================
// LOGS
//==================================================

void CProductionChecklist::CheckLogs()
{
   bool ok = EnableLogs;

   SetResult(9, ok, ok ? "Sistema de logs habilitado" : "Logs desabilitados no input");
}

//==================================================
// RISK (margem + parametros de risco validos)
//==================================================

void CProductionChecklist::CheckRisk()
{
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);

   bool paramsOK =
      RiskPercent > 0.0 &&
      MaxDailyLossPercent > 0.0 &&
      MaxDrawdownPercent > 0.0 &&
      MaxTradesPerDay > 0 &&
      MaxOpenPositions > 0;

   bool ok = paramsOK && freeMargin >= MinFreeMargin;

   string msg = "";

   if(!paramsOK)
      msg = "Parametros de risco invalidos (RiskPercent/MaxDailyLoss/MaxDrawdown/MaxTrades/MaxOpen)";
   else if(freeMargin < MinFreeMargin)
      msg = "Margem livre insuficiente: " + DoubleToString(freeMargin, 2);
   else
      msg = "Risco OK | margem livre=" + DoubleToString(freeMargin, 2);

   SetResult(10, ok, msg);
}

//==================================================
// EXECUTION (bid/ask + spread)
//==================================================

void CProductionChecklist::CheckExecution()
{
   double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   bool ok = (bid > 0.0 && ask > 0.0);

   string msg = ok ? "Bid/Ask disponiveis" : "Preco indisponivel";

   if(ok && point > 0.0)
   {
      double spreadPoints = (ask - bid) / point;

      if(spreadPoints > MaxSpread)
      {
         ok = false;
         msg = "Spread acima do maximo: " + DoubleToString(spreadPoints, 1) + " pts (max=" + DoubleToString(MaxSpread, 1) + ")";
      }
   }

   SetResult(11, ok, msg);
}

//==================================================
// NOTIFICATIONS
//==================================================

void CProductionChecklist::CheckNotifications()
{
   bool ok = EnableNotifications;

   string msg = ok ? "Central de notificacoes habilitada" : "Notificacoes desabilitadas";

   if(ok && NotifyTelegramToken != "" && NotifyTelegramChatID == "")
      msg = "Telegram configurado sem ChatID (apenas Push)";

   SetResult(12, ok, msg);
}

//==================================================
// AUDIT
//==================================================

void CProductionChecklist::CheckAudit()
{
   bool ok = EnableAuditLog;

   SetResult(13, ok, ok ? "Auditoria habilitada" : "Auditoria desabilitada");
}

//==================================================
// DASHBOARD
//==================================================

void CProductionChecklist::CheckDashboard()
{
   bool ok = EnableDashboard;

   SetResult(14, ok, ok ? "Dashboard habilitado" : "Dashboard desabilitado");
}

//==================================================
// SCANNER
//==================================================

void CProductionChecklist::CheckScanner()
{
   bool ok = EnableMultiSymbol;

   SetResult(15, ok, ok ? "Multi-symbol habilitado" : "Scanner multi-symbol desabilitado");
}

//==================================================
// PERFORMANCE (analise/benchmark ativos)
//==================================================

void CProductionChecklist::CheckPerformance()
{
   bool ok = EnableBacktestAnalyzer || EnableBenchmark;

   SetResult(16, ok, ok ? "Metricas de performance ativas" : "Analise de performance desabilitada");
}

//==================================================
// SUMMARY
//==================================================

string CProductionChecklist::GetSummary()
{
   string summary = "=== PRODUCTION CHECKLIST ===\n";

   int passed = 0;
   int failed = 0;
   int criticalFailed = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      string status = m_passed[i] ? "PASS" : "FAIL";
      string critical = m_critical[i] ? "[CRITICAL]" : "[OPTIONAL]";

      summary += critical + " " + m_names[i] + ": " + status + " - " + m_messages[i] + "\n";

      if(m_passed[i])
         passed++;
      else
      {
         failed++;
         if(m_critical[i])
            criticalFailed++;
      }
   }

   summary += "\nResult: " + IntegerToString(passed) + "/" + IntegerToString(m_item_count) + " passed";
   summary += " | " + IntegerToString(failed) + " failed";
   summary += " | " + IntegerToString(criticalFailed) + " critical failed";
   summary += "\nREADY: " + (m_all_passed ? "YES" : "NO");

   return summary;
}

//==================================================
// LOG RESULTS
//==================================================

void CProductionChecklist::LogResults()
{
   string summary = GetSummary();
   Print("[CHECKLIST]\n", summary);

   int h = FileOpen("XAU_AI_PRO\\ProductionChecklist.txt", FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h != INVALID_HANDLE)
     {
      FileSeek(h, 0, SEEK_SET);
      FileWriteString(h, summary);
      FileClose(h);
     }
}

//==================================================
// COUNTERS
//==================================================

int CProductionChecklist::GetPassedCount()
{
   int count = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      if(m_passed[i])
         count++;
   }

   return count;
}

//==================================================

int CProductionChecklist::GetFailedCount()
{
   int count = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      if(!m_passed[i])
         count++;
   }

   return count;
}

//==================================================

int CProductionChecklist::GetCriticalFailedCount()
{
   int count = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      if(!m_passed[i] && m_critical[i])
         count++;
   }

   return count;
}

#endif
