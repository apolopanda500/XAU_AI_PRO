//+------------------------------------------------------------------+
//|                                         ForwardTestRunner.mqh    |
//|                                 XAU_AI_PRO - Forward Test E13   |
//|             Coletor de datos de sesion para reconciliacion       |
//+------------------------------------------------------------------+
// ATENCAO (ETAPA 15.10): este arquivo e um INCLUDE (.mqh).
// NAO compile-o isoladamente (F7 aqui gera "undeclared identifier"
// para ConnectionGuard/FailureMode/NewsFilter/AIClient/MarketScore,
// que vivem em outros modulos incluidos pelo EA principal).
//
// Para compilar o projeto, abra e compile SEMPRE:
//   XAU_AI_PRO.mq5  (Experts/XAU_AI_PRO/XAU_AI_PRO.mq5)
//
// ETAPA 13 - FORWARD TEST PROFISSIONAL
//
// Coletor centralizado de observabilidade para a fase A (Demo),
// B (Stress) e C (Reconciliacion) do forward test:
//
//   FILE: Data\forward_test_session.csv  (FILE_COMMON)  -> heartbeat
//   FILE: Data\forward_test_trades.csv   (FILE_COMMON)  -> trades
//
// Columnas (heartbeat, ~1x por segundo):
//   timestamp,balance,equity,drawdown_pct,free_margin,spread_points,
//   server_offset_sec,connection_state,failure_mode,news_state,ai_ready,
//   ai_confidence,market_score,positions_open,ea_version
//
// Columnas (trade):
//   timestamp,symbol,event,signal,score,ai_confidence,side,volume,
//   price,sl,tp,ticket,profit,exec_result,retcode,block_reason
//
// PRINCIPIO: nunca bloqueia ou interrompe a execucion; apenas registra.
// Reescrito por sesion ( OnInit ). O reconcilador (Fase C) compara este
// CSV contra AuditLog x TradeLogger x historico broker.
//+------------------------------------------------------------------+

#ifndef FORWARD_TEST_RUNNER_MQH
#define FORWARD_TEST_RUNNER_MQH

#include "../Core/Config.mqh"
#include "../Core/DecisionEngine.mqh"        // self-contained: MarketScore
#include "../Enterprise/ConnectionGuard.mqh" // self-contained: ConnectionGuardRefresh
#include "../Enterprise/FailureMode.mqh"     // self-contained: GetFailureStateString
#include "../Filters/NewsFilter.mqh"         // self-contained: GetNewsState
#include "../AI/AIClient.mqh"                // self-contained: AIClientConnected/LastAIConfidence

input bool EnableForwardLog      = true;   // ETAPA 13: coletor de sesion live
input int    ForwardHeartbeatSec = 1;      // intervalo minimo do heartbeat (seg)

string const FORWARD_FILE       = "Data\\forward_test_session.csv";
string const FORWARD_FILE_TRADE = "Data\\forward_test_trades.csv";

int       g_fwdHFile  = INVALID_HANDLE;
datetime  g_fwdLastHb = 0;

bool ForwardFileInit()
{
   if(!EnableForwardLog)
      return true;
   ResetLastError();
   g_fwdHFile = FileOpen(
      FORWARD_FILE,
      FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI |
      FILE_SHARE_READ | FILE_SHARE_WRITE
   );
   if(g_fwdHFile == INVALID_HANDLE)
   {
      Print("[FORWARD] falha ao abrir log: ", GetLastError());
      return false;
   }
   FileSeek(g_fwdHFile, 0, SEEK_END);
   if(FileSize(g_fwdHFile) == 0)
   {
      FileWrite(g_fwdHFile,
         "timestamp","balance","equity","drawdown_pct","free_margin",
         "spread_points","server_offset_sec","connection_state",
         "failure_mode","news_state","ai_ready","ai_confidence",
         "market_score","positions_open","ea_version");
      FileFlush(g_fwdHFile);
   }
   int hTr = FileOpen(FORWARD_FILE_TRADE,
      FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI |
      FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(hTr != INVALID_HANDLE)
   {
      FileSeek(hTr, 0, SEEK_END);
      if(FileSize(hTr) == 0)
      {
         FileWrite(hTr,
            "timestamp","symbol","event","signal","score","ai_confidence",
            "side","volume","price","sl","tp","ticket","profit",
            "exec_result","retcode","block_reason");
         FileFlush(hTr);
      }
      FileClose(hTr);
   }
   else
   {
      Print("[FORWARD] falha ao abrir trades log: ", GetLastError());
   }
   return true;
}

void ForwardLogClose()
{
   if(g_fwdHFile != INVALID_HANDLE)
   {
      FileFlush(g_fwdHFile);
      FileClose(g_fwdHFile);
      g_fwdHFile = INVALID_HANDLE;
   }
}

double ForwardGetDrawdownPercent()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   static double peakEquity = 0.0;
   if(peakEquity <= 0.0 || equity > peakEquity)
      peakEquity = equity;
   double dd = 0.0;
   if(peakEquity > 0.0)
      dd = MathMax(0.0, (peakEquity - equity) / peakEquity) * 100.0;
   return dd;
}

void ForwardHeartbeat()
{
   if(!EnableForwardLog)
      return;
   if(g_fwdHFile == INVALID_HANDLE)
      return;
   datetime now = TimeCurrent();
   if(g_fwdLastHb > 0 && (now - g_fwdLastHb) < ForwardHeartbeatSec)
      return;
   g_fwdLastHb = now;
   ConnectionGuardRefresh();
   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double spread = (point > 0.0) ? (ask - bid) / point : 0.0;
   int latency = (int)(TimeLocal() - TimeCurrent());
   string connState = ConnectionGuardSummary();
   string fmState   = GetFailureStateString();
   string newsState = "CLEAR";
   if(EnableNewsFilter)
      newsState = EnumToString(GetNewsState());
   bool aiReady = AIClientConnected();
   double aiConf = LastAIConfidence();
   string version = "1.2.0";
   FileWrite(g_fwdHFile,
      TimeToString(now, TIME_DATE | TIME_SECONDS),
      DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
      DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
      DoubleToString(ForwardGetDrawdownPercent(), 2),
      DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2),
      DoubleToString(spread, 2),
      latency,
      connState,
      fmState,
      newsState,
      (aiReady ? "ON" : "OFF"),
      DoubleToString(aiConf, 2),
      DoubleToString(MarketScore, 2),
      (string)PositionsTotal(),
      version);
   FileFlush(g_fwdHFile);
}

void ForwardLogTrade(const string symbol,
                     const string evt,
                     const int signal,
                     const double score,
                     const string aiConf,
                     const string side,
                     double volume,
                     double price,
                     double sl,
                     double tp,
                     const ulong ticket,
                     const string execResult,
                     const int retcode,
                     const string blockReason)
{
   if(!EnableForwardLog)
      return;
   int h = FileOpen(FORWARD_FILE_TRADE,
      FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI |
      FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return;
   FileSeek(h, 0, SEEK_END);
   FileWrite(h,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
      symbol, evt, (string)signal, DoubleToString(score, 2),
      aiConf, side,
      DoubleToString(volume, 2),
      DoubleToString(price, _Digits),
      DoubleToString(sl, _Digits),
      DoubleToString(tp, _Digits),
      (string)ticket, (string)0.0, execResult, (string)retcode, blockReason);
   FileFlush(h);
   FileClose(h);
}

void ForwardLogDeal(const string symbol,
                    const ulong ticket,
                    const int signal,
                    double score,
                    const string aiConf,
                    const string side,
                    double volume,
                    double price,
                    double profit,
                    const string execResult,
                    const int retcode)
{
   if(!EnableForwardLog)
      return;
   int h = FileOpen(FORWARD_FILE_TRADE,
      FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI |
      FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return;
   FileSeek(h, 0, SEEK_END);
   FileWrite(h,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
      symbol, "CLOSE", (string)signal, DoubleToString(score, 2),
      aiConf, side,
      DoubleToString(volume, 2),
      DoubleToString(price, _Digits),
      (string)0.0, (string)0.0,
      (string)ticket,
      DoubleToString(profit, 2),
      execResult, (string)retcode, "");
   FileFlush(h);
   FileClose(h);
}

void ForwardFlush()
{
   if(g_fwdHFile != INVALID_HANDLE)
      FileFlush(g_fwdHFile);
}

string ForwardSummary()
{
   return StringFormat("ForwardTest | Log=%s | HFile=%s",
      (EnableForwardLog ? "ON" : "OFF"),
      (g_fwdHFile != INVALID_HANDLE ? "open" : "closed"));
}

#endif // FORWARD_TEST_RUNNER_MQH
