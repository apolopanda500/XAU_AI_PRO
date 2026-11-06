
// Heartbeat somente leitura para integração EA -> Gateway -> App.
// Não envia ordens, não altera risco e não interfere no TradePipeline.
#include "../Core/TradeGate.mqh"   // P1.62: veredito unico de negociacao
datetime g_heartbeat_last_write = 0;
int g_heartbeat_write_count = 0;

// Nome do heartbeat separado no backtest.
//
// A pasta Common e a MESMA para o terminal e para todos os agentes do tester.
// Sem separacao, um backtest sobrescreve o heartbeat da conta real e o app
// passa a ler login/saldo simulados como se fossem a operacao de verdade.
// MEDIDO em 26/10/2026: depois de 3 backtests o arquivo de producao ficou com
// login 113568614 e saldo 1000.00, e o EA real nao o reescreveu por minutos.
string EAHeartbeatFileName()
  {
   if(MQLInfoInteger(MQL_TESTER))
      return "XAU_AI_PRO_heartbeat_tester.json";

   return "XAU_AI_PRO_heartbeat.json";
  }

bool EAHeartbeatWrite(const string state = "RUNNING")
  {
   const datetime now = TimeCurrent();
   if(g_heartbeat_last_write == now)
      return true;

   ResetLastError();
   const int handle = FileOpen(EAHeartbeatFileName(), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(handle == INVALID_HANDLE)
      return false;

   // P1.62 (v1.2.76): MEDIDO em 02/11 08:17 - este campo publicava
   // "autotrading": true (bit do terminal) enquanto as 16 charts imprimiam
   // MQL_TRADE_ALLOWED=0 e nenhuma podia negociar. O campo passa a ser o
   // veredito do portao; o bit cru do terminal e o codigo do estado vao ao
   // lado, para diagnostico.
   const bool trade_allowed = CTradeGate::Ok();
   const bool terminal_bit  = (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   const int  gate_code     = (int)CTradeGate::Evaluate();
   const string json = StringFormat(
      "{\"schema\":\"ea-heartbeat.v1\",\"state\":\"%s\",\"timestamp\":\"%s\",\"login\":%I64d,\"server\":\"%s\",\"symbol\":\"%s\",\"timeframe\":%d,\"autotrading\":%s,\"terminal_trade_allowed\":%s,\"trade_gate_code\":%d,\"balance\":%.2f,\"equity\":%.2f,\"positions\":%d,\"write_count\":%d}",
      state,
      TimeToString(now, TIME_DATE | TIME_SECONDS),
      AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_SERVER),
      _Symbol,
      Period(),
      trade_allowed ? "true" : "false",
      terminal_bit ? "true" : "false",
      gate_code,
      AccountInfoDouble(ACCOUNT_BALANCE),
      AccountInfoDouble(ACCOUNT_EQUITY),
      PositionsTotal(),
      g_heartbeat_write_count + 1);

   FileWriteString(handle, json);
   FileClose(handle);
   g_heartbeat_last_write = now;
   g_heartbeat_write_count++;
   return true;
  }
