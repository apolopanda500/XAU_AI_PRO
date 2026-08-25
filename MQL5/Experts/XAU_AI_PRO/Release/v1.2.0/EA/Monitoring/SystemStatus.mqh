// XAU_AI_PRO v1.2.0 - SYSTEM STATUS (ETAPA 15.6)
#ifndef SYSTEMSTATUS_MQH
#define SYSTEMSTATUS_MQH

#include "../Core/Config.mqh"
#include "../Core/RiskHub.mqh"
#include "../Core/RiskCenter.mqh"
#include "../Core/PositionManager.mqh"
#include "../AI/AIConnector.mqh"
#include "HealthMonitor.mqh"   // ETAPA 15.6.5: estado multi-nivel do watchdog
#include "../Filters/NewsFilter.mqh"   // self-contained: IsNewsBlocked

//==================================================
// SYSTEM STATUS SNAPSHOT
//
// Gera MQL5\Files\Data\system_status.json com a
// visao operacional unica consumivel pelo app:
//
// HEALTH | TRADING | RISK | AI | EXECUTION |
// NEWS | PYTHON | DATABASE
//
// Regras:
// - Gravacao throttled (min 15s entre gravacoes).
// - Conteudo ASCII puro (compativel ANSI/UTF-8).
// - Heartbeat = presenca do arquivo + generated_at.
//==================================================

datetime g_statusLastWrite=0;

//--------------------------------------------------
// HELPERS JSON
//--------------------------------------------------

string SSBool(bool v)
{
   return(v ? "true" : "false");
}

string SSQuote(string s)
{
   // Escapa aspas duplas simples (conteudo controlado)
   StringReplace(s,"\"","'");
   return "\"" + s + "\"";
}

//--------------------------------------------------
// SECOES
//--------------------------------------------------

string SSHealthSection()
{
   bool connected   =(TerminalInfoInteger(TERMINAL_CONNECTED)!=0);
   bool tradeAllowed=(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)!=0);
   bool eaTradeOK   =(MQLInfoInteger(MQL_TRADE_ALLOWED)!=0);

   // ETAPA 15.6.5: estado multi-nivel (nao apenas true/false)
   return "\"health\": {"
          "\"state\": " + SSQuote(HealthGetStateString()) + ", "
          "\"terminal_connected\": " + SSBool(connected) + ", "
          "\"algo_trading_enabled\": " + SSBool(tradeAllowed) + ", "
          "\"ea_trade_allowed\": " + SSBool(eaTradeOK) +
          "}";
}

string SSTradingSection(string symbol)
{
   bool hasPos=HasPosition(symbol);
   int dir=(hasPos ? GetPositionDirection(symbol) : 0);

   double pl=(hasPos ? AccountInfoDouble(ACCOUNT_PROFIT) : 0.0);

   string posType="NONE";
   if(dir==1)  posType="BUY";
   if(dir==-1) posType="SELL";

   return "\"trading\": {"
          "\"symbol\": "          + SSQuote(symbol) + ", "
          "\"position\": "        + SSQuote(posType) + ", "
          "\"floating_pl\": "     + DoubleToString(pl,2) + ", "
          "\"balance\": "         + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2) + ", "
          "\"equity\": "          + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2) +
          "}";
}

string SSRiskSection(string symbol)
{
   RiskDecision d=RiskEvaluate(symbol);

   return "\"risk\": {"
          "\"status\": "           + SSQuote(d.allowed ? "OPEN" : "BLOCKED") + ", "
          "\"reason\": "           + SSQuote(d.reason) + ", "
          "\"drawdown_pct\": "     + DoubleToString(d.drawdown_pct,2) + ", "
          "\"trades_today\": "     + IntegerToString(d.trades_today) + ", "
          "\"daily_loss_pct\": "   + DoubleToString(d.daily_loss_pct,2) + ", "
          "\"free_margin\": "      + DoubleToString(d.free_margin,2) +
          "}";
}

string SSAISection(string symbol)
{
   bool loaded=LoadAIPrediction(symbol);

   if(!loaded)
   {
      return "\"ai\": {"
             "\"available\": false, "
             "\"signal\": \"UNAVAILABLE\", "
             "\"confidence\": 0.0, "
             "\"model_version\": \"\", "
             "\"age_seconds\": -1, "
             "\"stale\": true"
             "}";
   }

   return "\"ai\": {"
          "\"available\": "        + SSBool(AI_Signal!="UNAVAILABLE") + ", "
          "\"signal\": "           + SSQuote(AI_Signal) + ", "
          "\"confidence\": "       + DoubleToString(AI_Confidence,2) + ", "
          "\"model_version\": "    + SSQuote(AI_ModelVersion) + ", "
          "\"age_seconds\": "      + DoubleToString(AI_AgeSeconds,0) + ", "
          "\"stale\": "            + SSBool(AI_IsStale) +
          "}";
}

string SSNewsSection(string symbol)
{
   bool blocked=false;
   string detail="";

   if(EnableNewsFilter && IsNewsBlocked())
   {
      blocked=true;
      detail=GetNewsBlockDetail(symbol);
   }

   return "\"news\": {"
          "\"filter_enabled\": " + SSBool(EnableNewsFilter) + ", "
          "\"blocked\": "        + SSBool(blocked) + ", "
          "\"detail\": "         + SSQuote(detail) +
          "}";
}

string SSPythonSection()
{
   // Idade da previsao (preenchida pela secao AI) como proxy
   // de saude do Python. Limite 900s alinhado ao contrato.
   double age=AI_AgeSeconds;
   bool available=(!AI_IsStale && age>=0.0 && age<=900.0);

   return "\"python\": {"
          "\"predictions_available\": " + SSBool(available) + ", "
          "\"prediction_age_sec\": "    + DoubleToString(age,0) +
          "}";
}

string SSDatabaseSection()
{
   // Dataset.csv = banco operacional (contrato 15.2).
   string file="Data\\dataset.csv";
   bool exists=FileIsExist(file);
   ulong size=0;

   if(exists)
   {
      int h=FileOpen(file,FILE_READ|FILE_BIN|FILE_SHARE_READ|FILE_SHARE_WRITE);
      if(h!=INVALID_HANDLE)
      {
         size=FileSize(h);
         FileClose(h);
      }
   }

   return "\"database\": {"
          "\"dataset_exists\": " + SSBool(exists) + ", "
          "\"dataset_bytes\": "  + IntegerToString((int)size) +
          "}";
}

//--------------------------------------------------
// UPDATE PRINCIPAL (throttled 15s)
//--------------------------------------------------

void SystemStatusUpdate()
{
   static datetime lastAttempt=0;
   datetime now=TimeCurrent();

   if(lastAttempt>0 && now-lastAttempt<15)
      return;

   lastAttempt=now;

   string symbol=_Symbol;

   string json="{"
      "\"schema_version\": \"1.0\", "
      "\"generated_at\": "  + SSQuote(TimeToString(now,TIME_DATE|TIME_SECONDS)) + ", "

      + SSHealthSection() + ", "
      + SSTradingSection(symbol) + ", "
      + SSRiskSection(symbol) + ", "
      + SSAISection(symbol) + ", "
      + SSNewsSection(symbol) + ", "
      + SSPythonSection() + ", "
      + SSDatabaseSection() +
      "}";

   ResetLastError();

   int h=FileOpen(
      "Data\\system_status.json",
      FILE_WRITE|FILE_TXT|FILE_ANSI,
      0
   );

   if(h==INVALID_HANDLE)
   {
      Print("SYSTEM STATUS WRITE ERROR | Code=",GetLastError());
      return;
   }

   FileWriteString(h,json);
   FileClose(h);
}

#endif // SYSTEMSTATUS_MQH