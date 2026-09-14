//+------------------------------------------------------------------+
//| XAU AI PRO — Protocolo v1 (MQL5 include)                         |
//| Espelho de core/src/protocol/mod.rs para o EA MT5.               |
//| Qualquer mudança no Rust exige atualização aqui.                 |
//| Envelope: {"protocol":"xau-ai-pro/1","type":"<Variante>",...}    |
//+------------------------------------------------------------------+
#property strict

//--- Constantes do protocolo
#define XAU_PROTOCOL_VERSION   "1.0.0"
#define XAU_PROTOCOL_ENVELOPE  "xau-ai-pro/1"
#define XAU_WS_URL             "ws://127.0.0.1:9002/ws/market"
#define XAU_PING_INTERVAL_MS   30000

//--- Origem do cliente no handshake
#define XAU_CLIENT_EA_MT5      "ea_mt5"

//--- Códigos de erro estáveis
#define XAU_ERR_BAD_REQUEST    "BAD_REQUEST"
#define XAU_ERR_VERSION        "VERSION_MISMATCH"
#define XAU_ERR_MT5_OFFLINE    "MT5_OFFLINE"
#define XAU_ERR_ORDER_REJECTED "ORDER_REJECTED"
#define XAU_ERR_NOT_FOUND      "NOT_FOUND"
#define XAU_ERR_INTERNAL       "INTERNAL"

//+------------------------------------------------------------------+
//| Monta o handshake Hello (primeiro comando de cada conexão).      |
//+------------------------------------------------------------------+
string XauHello()
{
   return StringFormat(
      "{\"protocol\":\"%s\",\"type\":\"Hello\",\"client\":\"%s\",\"version\":\"%s\"}",
      XAU_PROTOCOL_ENVELOPE, XAU_CLIENT_EA_MT5, XAU_PROTOCOL_VERSION
   );
}

//+------------------------------------------------------------------+
//| Monta Subscribe para a lista de símbolos (separados por vírgula).|
//+------------------------------------------------------------------+
string XauSubscribe(const string symbols_csv)
{
   string items[];
   int n = StringSplit(symbols_csv, ',', items);
   string arr = "";
   for(int i = 0; i < n; i++)
   {
      string s = items[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(i > 0) arr += ",";
      arr += StringFormat("\"%s\"", s);
   }
   return StringFormat(
      "{\"protocol\":\"%s\",\"type\":\"Subscribe\",\"symbols\":[%s]}",
      XAU_PROTOCOL_ENVELOPE, arr
   );
}

//+------------------------------------------------------------------+
//| Monta heartbeat Ping com request_id e timestamp ms.              |
//+------------------------------------------------------------------+
string XauPing(const string request_id, const long ts_ms)
{
   return StringFormat(
      "{\"protocol\":\"%s\",\"type\":\"Ping\",\"request_id\":\"%s\",\"ts_ms\":%I64d}",
      XAU_PROTOCOL_ENVELOPE, request_id, ts_ms
   );
}

//+------------------------------------------------------------------+
//| Monta PlaceOrder com request_id para correlação.                 |
//+------------------------------------------------------------------+
string XauPlaceOrder(
   const string symbol,
   const string side,
   const double volume,
   const double sl,
   const double tp,
   const int magic,
   const string request_id
)
{
   return StringFormat(
      "{\"protocol\":\"%s\",\"type\":\"PlaceOrder\",\"symbol\":\"%s\",\"side\":\"%s\","
      "\"volume\":%.2f,\"sl\":%.2f,\"tp\":%.2f,\"magic\":%d,\"request_id\":\"%s\"}",
      XAU_PROTOCOL_ENVELOPE, symbol, side, volume, sl, tp, magic, request_id
   );
}

//+------------------------------------------------------------------+
//| Extrai o campo "type" de uma mensagem (retorna "" se ausente).   |
//+------------------------------------------------------------------+
string XauMsgType(const string json)
{
   int p = StringFind(json, "\"type\":\"");
   if(p < 0) return "";
   int start = p + 8;
   int end = StringFind(json, "\"", start);
   if(end < 0) return "";
   return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
//| Extrai o campo "code" de uma mensagem Error ("" se ausente).     |
//+------------------------------------------------------------------+
string XauErrorCode(const string json)
{
   int p = StringFind(json, "\"code\":\"");
   if(p < 0) return "";
   int start = p + 8;
   int end = StringFind(json, "\"", start);
   if(end < 0) return "";
   return StringSubstr(json, start, end - start);
}
