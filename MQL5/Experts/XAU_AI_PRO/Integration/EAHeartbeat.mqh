
// Heartbeat somente leitura para integração EA -> Gateway -> App.
// Não envia ordens, não altera risco e não interfere no TradePipeline.
datetime g_heartbeat_last_write = 0;
int g_heartbeat_write_count = 0;

bool EAHeartbeatWrite(const string state = "RUNNING")
  {
   const datetime now = TimeCurrent();
   if(g_heartbeat_last_write == now)
      return true;

   ResetLastError();
   const int handle = FileOpen("XAU_AI_PRO_heartbeat.json", FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(handle == INVALID_HANDLE)
      return false;

   const bool trade_allowed = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   const string json = StringFormat(
      "{\"schema\":\"ea-heartbeat.v1\",\"state\":\"%s\",\"timestamp\":\"%s\",\"login\":%I64d,\"server\":\"%s\",\"symbol\":\"%s\",\"timeframe\":%d,\"autotrading\":%s,\"balance\":%.2f,\"equity\":%.2f,\"positions\":%d,\"write_count\":%d}",
      state,
      TimeToString(now, TIME_DATE | TIME_SECONDS),
      AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_SERVER),
      _Symbol,
      Period(),
      trade_allowed ? "true" : "false",
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
