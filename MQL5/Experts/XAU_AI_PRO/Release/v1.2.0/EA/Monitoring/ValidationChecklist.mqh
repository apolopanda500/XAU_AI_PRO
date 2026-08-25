//+------------------------------------------------------------------+
//| ValidationChecklist.mqh                                         |
//| XAU_AI_PRO - Validacao real READY/WARNING/BLOCKED (ETAPA 10)    |
//| BLOCKED  = impede operacao segura (critico)                     |
//| WARNING  = degradado, nao bloqueia                              |
//| READY    = operacional                                          |
//+------------------------------------------------------------------+
#property copyright "XAU_AI_PRO"
#property version   "1.20"

#ifndef VALIDATIONCHECKLIST_MQH
#define VALIDATIONCHECKLIST_MQH

#include "../Core/Config.mqh"

//==================================================
// STATUS
//==================================================

enum VCheckStatus
{
   VC_READY   = 0,
   VC_WARNING = 1,
   VC_BLOCKED = 2
};

//==================================================
// ESTADO GLOBAL (arrays paralelos - seguro em MQL5)
//==================================================

string g_vcheck_names[15];
VCheckStatus g_vcheck_status[15];
string g_vcheck_msg[15];
int    g_vcheck_count = 15;
bool   g_validationPassed = false;

string g_vcheck_name(int i)
{
   switch(i)
   {
      case 0:  return "ATR";
      case 1:  return "ADX";
      case 2:  return "RSI";
      case 3:  return "EMA";
      case 4:  return "AI";
      case 5:  return "JSON";
      case 6:  return "Dataset";
      case 7:  return "Python";
      case 8:  return "Broker";
      case 9:  return "Spread";
      case 10: return "Session";
      case 11: return "Symbol Manager";
      case 12: return "Position Manager";
      case 13: return "Trade Manager";
      case 14: return "Dashboard";
   }
   return "?";
}

string g_vcheck_status_str(VCheckStatus s)
{
   switch(s)
   {
      case VC_READY:   return "READY";
      case VC_WARNING: return "WARNING";
      case VC_BLOCKED: return "BLOCKED";
   }
   return "?";
}

void g_vcheck_set(int i, VCheckStatus s, string msg)
{
   if(i < 0 || i >= g_vcheck_count)
      return;
   g_vcheck_status[i] = s;
   g_vcheck_msg[i]    = msg;
}

//==================================================
// EXECUTA CHECKLIST
//==================================================

bool ValidationChecklistRun()
{
   g_validationPassed = true;

   Print("[VALIDATION] Iniciando checklist READY/WARNING/BLOCKED...");

   // 0. ATR
   int hATR = iATR(_Symbol, PERIOD_CURRENT, ATRPeriod);
   bool atrOK = (hATR != INVALID_HANDLE);
   if(hATR != INVALID_HANDLE)
      IndicatorRelease(hATR);
   g_vcheck_set(0, atrOK ? VC_READY : VC_WARNING, atrOK ? "ATR OK" : "ATR indisponivel (degradado)");

   // 1. ADX
   int hADX = iADX(_Symbol, PERIOD_CURRENT, ADXPeriod);
   bool adxOK = (hADX != INVALID_HANDLE);
   if(hADX != INVALID_HANDLE)
      IndicatorRelease(hADX);
   g_vcheck_set(1, adxOK ? VC_READY : VC_WARNING, adxOK ? "ADX OK" : "ADX indisponivel (degradado)");

   // 2. RSI
   int hRSI = iRSI(_Symbol, PERIOD_CURRENT, RSIPeriod, PRICE_CLOSE);
   bool rsiOK = (hRSI != INVALID_HANDLE);
   if(hRSI != INVALID_HANDLE)
      IndicatorRelease(hRSI);
   g_vcheck_set(2, rsiOK ? VC_READY : VC_WARNING, rsiOK ? "RSI OK" : "RSI indisponivel (degradado)");

   // 3. EMA (tendencia)
   int hEMA = iMA(_Symbol, PERIOD_CURRENT, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   bool emaOK = (hEMA != INVALID_HANDLE);
   if(hEMA != INVALID_HANDLE)
      IndicatorRelease(hEMA);
   g_vcheck_set(3, emaOK ? VC_READY : VC_WARNING, emaOK ? "EMA OK" : "EMA indisponivel (degradado)");

   // 4. AI
   string predFile = "Data\\prediction_" + _Symbol + ".json";
   bool hasPred = FileIsExist(predFile, FILE_COMMON);

   if(!EnableAIFilter)
      g_vcheck_set(4, VC_READY, "Filtro IA desativado (nao requerido)");
   else if(hasPred)
      g_vcheck_set(4, VC_READY, "Prediction JSON presente");
   else if(RequireAIJSON)
      g_vcheck_set(4, VC_BLOCKED, "IA requerida mas prediction ausente");
   else
      g_vcheck_set(4, VC_WARNING, "IA sem prediction (fallback tecnico)");

   // 5. JSON
   bool jsonOK = false;
   if(FileIsExist(predFile, FILE_COMMON))
   {
      int jh = FileOpen(predFile, FILE_READ | FILE_BIN | FILE_COMMON);
      if(jh != INVALID_HANDLE)
      {
         jsonOK = (FileSize(jh) > 0);
         FileClose(jh);
      }
   }

   if(!EnableAIFilter || !RequireAIJSON)
      g_vcheck_set(5, jsonOK ? VC_READY : VC_WARNING, jsonOK ? "JSON OK" : "JSON ausente/vazio (opcional)");
   else
      g_vcheck_set(5, jsonOK ? VC_READY : VC_BLOCKED, jsonOK ? "JSON OK" : "JSON ausente/vazio (requerido)");

   // 6. Dataset
   string dsFile = "Data\\dataset.csv";
   bool dsOK = false;
   if(FileIsExist(dsFile, FILE_COMMON))
   {
      int dh = FileOpen(dsFile, FILE_READ | FILE_BIN | FILE_COMMON);
      if(dh != INVALID_HANDLE)
      {
         dsOK = (FileSize(dh) > 0);
         FileClose(dh);
      }
   }

   if(!EnableDataset)
      g_vcheck_set(6, VC_READY, "Dataset desativado");
   else
      g_vcheck_set(6, dsOK ? VC_READY : VC_BLOCKED, dsOK ? "Dataset OK" : "Dataset ausente/vazio (bloqueia)");

   // 7. Python
   bool pyOK = hasPred && dsOK;
   g_vcheck_set(7, pyOK ? VC_READY : VC_WARNING, pyOK ? "Pipeline Python OK" : "Pipeline Python incompleto (opcional)");

   // 8. Broker
   bool brokerOK = (TerminalInfoInteger(TERMINAL_CONNECTED) != 0);
   g_vcheck_set(8, brokerOK ? VC_READY : VC_BLOCKED, brokerOK ? "Terminal conectado" : "Terminal desconectado (bloqueia)");

   // 9. Spread
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   bool spreadOK = true;
   string spreadMsg = "Spread OK";

   if(ask > 0.0 && bid > 0.0 && point > 0.0)
   {
      double spreadPoints = (ask - bid) / point;
      if(spreadPoints > MaxSpread)
      {
         spreadOK = false;
         spreadMsg = "Spread " + DoubleToString(spreadPoints, 1) + " > max " + DoubleToString(MaxSpread, 1);
      }
   }

   if(!spreadOK && EnableSpreadFilter)
      g_vcheck_set(9, VC_BLOCKED, spreadMsg + " (bloqueia)");
   else if(!spreadOK)
      g_vcheck_set(9, VC_WARNING, spreadMsg + " (filtro desativado)");
   else
      g_vcheck_set(9, VC_READY, spreadMsg);

   // 10. Session
   int hourNow = (int)(TimeCurrent() / 3600) % 24;
   bool inSession = (hourNow >= TradeStartHour && hourNow < TradeEndHour);

   if(!EnableSessionFilter)
      g_vcheck_set(10, VC_READY, "Filtro de sessao desativado");
   else if(inSession)
      g_vcheck_set(10, VC_READY, "Dentro da sessao de trading");
   else
      g_vcheck_set(10, VC_WARNING, "Fora da sessao de trading (nao bloqueia)");

   // 11. Symbol Manager
   bool symOK = SymbolSelect(_Symbol, true);
   g_vcheck_set(11, symOK ? VC_READY : VC_BLOCKED, symOK ? "Symbol disponivel" : "Symbol indisponivel (bloqueia)");

   // 12. Position Manager (health geral de posicoes)
   // Sem dependencia externa: valida que o gerenciamento de posicoes
   // esta acessivel (historico selecionavel).
   bool posOK = HistorySelect(0, TimeCurrent());
   g_vcheck_set(12, posOK ? VC_READY : VC_WARNING, posOK ? "Historico de posicoes acessivel" : "Historico indisponivel (degradado)");

   // 13. Trade Manager
   bool tradeOK = (MQLInfoInteger(MQL_TRADE_ALLOWED) != 0) &&
                  (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   g_vcheck_set(13, tradeOK ? VC_READY : VC_BLOCKED, tradeOK ? "Trading permitido" : "Trading nao permitido (bloqueia)");

   // 14. Dashboard
   g_vcheck_set(14, EnableDashboard ? VC_READY : VC_WARNING, EnableDashboard ? "Dashboard ativo" : "Dashboard desativado (opcional)");

   //==================================================
   // RESULTADO FINAL: BLOCKED impede operacao
   //==================================================

   int blocked = 0;
   int warning = 0;

   for(int i = 0; i < g_vcheck_count; i++)
   {
      if(g_vcheck_status[i] == VC_BLOCKED)
         blocked++;
      if(g_vcheck_status[i] == VC_WARNING)
         warning++;
   }

   g_validationPassed = (blocked == 0);

   Print("[VALIDATION] Resultado: READY=", IntegerToString(g_vcheck_count - blocked - warning),
         " WARNING=", IntegerToString(warning),
         " BLOCKED=", IntegerToString(blocked));

   if(g_validationPassed)
      Print("[VALIDATION] SEM BLOCKED - operacao permitida");
   else
      Print("[VALIDATION] " + IntegerToString(blocked) + " BLOCKED - verificar antes de operar");

   int h = FileOpen("XAU_AI_PRO\\ValidationChecklist.txt", FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h != INVALID_HANDLE)
     {
      FileSeek(h, 0, SEEK_SET);
      FileWriteString(h, ValidationChecklistSummary());
      FileClose(h);
     }

   return g_validationPassed;
}

//==================================================
// STATUS
//==================================================

bool ValidationChecklistPassed()
{
   return g_validationPassed;
}

//==================================================
// SUMMARY
//==================================================

string ValidationChecklistSummary()
{
   string summary = "=== VALIDATION CHECKLIST (READY/WARNING/BLOCKED) ===\n";

   int blocked = 0;
   int warning = 0;

   for(int i = 0; i < g_vcheck_count; i++)
   {
      summary += g_vcheck_name(i) + ": " + g_vcheck_status_str(g_vcheck_status[i]) + " - " + g_vcheck_msg[i] + "\n";

      if(g_vcheck_status[i] == VC_BLOCKED)
         blocked++;
      if(g_vcheck_status[i] == VC_WARNING)
         warning++;
   }

   summary += "\nREADY=" + IntegerToString(g_vcheck_count - blocked - warning) +
              " | WARNING=" + IntegerToString(warning) +
              " | BLOCKED=" + IntegerToString(blocked);

   summary += "\nResultado: " + (g_validationPassed ? "APROVADO (operacao permitida)" : "REPROVADO (existem BLOCKED)");

   return summary;
}

#endif
