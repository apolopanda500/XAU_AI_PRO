//+------------------------------------------------------------------+
//| XAU AI PRO — Bridge EA-Core (item 6 do roadmap)                  |
//| Conecta o EA ao Core via HTTP (WebRequest).                      |
//| Rotas: /api/ea/hello, /api/ea/heartbeat, /api/ea/status.        |
//+------------------------------------------------------------------+
#property strict

#include "ProtocolV1.mqh"

input string BridgeCoreUrl = "http://127.0.0.1:9003";
input int    BridgeHeartbeatSec = 5;
input string BridgeSymbols = "XAUUSD";

string GbSession = "";
datetime GbLastHeartbeat = 0;
bool GbOnline = false;

//+------------------------------------------------------------------+
//| POST JSON via WebRequest. Retorna corpo ou "".                   |
//+------------------------------------------------------------------+
string BridgePost(const string path, const string body, int &http_code)
{
   http_code = 0;
   string url = BridgeCoreUrl + path;
   string headers = "Content-Type: application/json\r\n";
   uchar body_bytes[];
   StringToCharArray(body, body_bytes, 0, StringLen(body));
   uchar result[];
   string result_headers;
   ResetLastError();
   int res = WebRequest("POST", url, NULL, 5000, body_bytes, ArraySize(body_bytes),
                        result, result_headers);
   if(res < 0)
   {
      Print("[Bridge] WebRequest falhou: ", GetLastError());
      return "";
   }
   http_code = res;
   return CharArrayToString(result, 0, ArraySize(result));
}

//+------------------------------------------------------------------+
//| Handshake com o Core. Chamar em OnInit.                          |
//+------------------------------------------------------------------+
bool BridgeHello()
{
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   string server = AccountInfoString(ACCOUNT_SERVER);
   string body = StringFormat(
      "{\"version\":\"%s\",\"login\":\"%I64d\",\"server\":\"%s\",\"symbols\":[\"%s\"],\"magic\":%d}",
      XAU_PROTOCOL_VERSION, login, server, BridgeSymbols, 2026001
   );
   int code = 0;
   string resp = BridgePost("/api/ea/hello", body, code);
   if(code != 200 || resp == "")
   {
      GbOnline = false;
      return false;
   }
   GbOnline = (StringFind(resp, "\"ok\":true") >= 0);
   Print("[Bridge] hello ok=", GbOnline);
   return GbOnline;
}


//+------------------------------------------------------------------+
//| Heartbeat com posições abertas. Chamar no timer.                 |
//+------------------------------------------------------------------+
bool BridgeHeartbeat()
{
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   string pos = BridgePositionsJson();
   string quote = BridgeQuoteJson(BridgeSymbols);
   string body = StringFormat(
      "{\"login\":\"%I64d\",\"positions\":[%s],\"quote\":%s}",
      login, pos, quote
   );
   int code = 0;
   string resp = BridgePost("/api/ea/heartbeat", body, code);
   if(code != 200 || resp == "")
   {
      GbOnline = false;
      return false;
   }
   GbOnline = (StringFind(resp, "\"ok\":true") >= 0);
   GbLastHeartbeat = TimeCurrent();
   BridgeHandleCommands(resp);
   return GbOnline;
}

//+------------------------------------------------------------------+
//| Serializa posições abertas do terminal em JSON.                  |
//+------------------------------------------------------------------+
string BridgePositionsJson()
{
   string out = "";
   int added = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      long ptype = PositionGetInteger(POSITION_TYPE);
      string side = (ptype == POSITION_TYPE_BUY) ? "buy" : "sell";
      double vol = PositionGetDouble(POSITION_VOLUME);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double cur = PositionGetDouble(POSITION_PRICE_CURRENT);
      double profit = PositionGetDouble(POSITION_PROFIT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(added > 0) out += ",";
      out += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"side\":\"%s\",\"volume\":%.2f,"
         "\"open_price\":%.2f,\"current_price\":%.2f,\"profit\":%.2f,\"magic\":%I64d}",
         ticket, sym, side, vol, open, cur, profit, magic
      );
      added++;
   }
   return out;
}

//+------------------------------------------------------------------+
//| Cotação de referência do símbolo principal.                      |
//+------------------------------------------------------------------+
string BridgeQuoteJson(const string symbol_csv)
{
   string items[];
   if(StringSplit(symbol_csv, ',', items) <= 0) return "null";
   string sym = items[0];
   StringTrimLeft(sym);
   StringTrimRight(sym);
   MqlTick tick;
   if(!SymbolInfoTick(sym, tick)) return "null";
   return StringFormat(
      "{\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"last\":%.5f,\"volume\":%.0f,"
      "\"high\":%.5f,\"low\":%.5f,\"change_pct\":0.0,\"timestamp\":\"-\",\"source\":\"mt5\"}",
      sym, tick.bid, tick.ask, tick.last, (double)tick.volume, tick.bid, tick.ask
   );
}

//+------------------------------------------------------------------+
//| Comandos pendentes do heartbeat (log; execução item 7).          |
//+------------------------------------------------------------------+
void BridgeHandleCommands(const string resp)
{
   int p = StringFind(resp, "\"pending_commands\":[");
   if(p < 0) return;
   int start = p + 20;
   int end = StringFind(resp, "]", start);
   if(end <= start + 1) return;
   Print("[Bridge] comandos: ", StringSubstr(resp, start, end - start));
}

//+------------------------------------------------------------------+
//| Estado da conexão para o painel do EA.                           |
//+------------------------------------------------------------------+
bool BridgeIsOnline() { return GbOnline; }
