// XAU_AI_PRO v1.2.9
#ifndef EXTERNALBRIDGE_MQH
#define EXTERNALBRIDGE_MQH

// Metricas de IA expostas pela acao "ai" (guarda AIMETRICS_MQH torna
// a inclusao inofensiva quando AIEngine.mqh ja incluiu antes).
#include "../AI/AIMetrics.mqh"
#include "../Core/TradeGate.mqh"   // P1.62: veredito unico de negociacao

//==================================================================
// PONTE APP EXTERNO <-> EA (FILE_COMMON)
//
// O heartbeat (`Integration/EAHeartbeat.mqh`) ja leva estado do EA PARA o
// app: `Common\Files\XAU_AI_PRO_heartbeat.json`, consumido por
// `backend/mt5_gateway.py` e `backend/watchdog.py`. Faltava o caminho de
// volta. v1.2.59 (P1.41): a frase seguinte dizia que "MQL5 nao abre socket"
// e isso e FALSO - a documentacao oficial de SocketCreate/SocketConnect
// mostra sockets nativos no MQL5, disponiveis a Expert Advisors e a scripts
// (ate 128 sockets abertos, com a familia TLS em SocketTlsRead/SocketTlsWrite).
// O que continua verdade, e que justifica este desenho: `WebRequest` so sai
// (o EA nao recebe pedidos HTTP) e um socket de ENTRADA exigiria um servidor
// a escutar, o que o EA nao e. O canal comum aos dois lados e, de facto,
// arquivo em
// FILE_COMMON — a mesma pasta que o app ja le.
//
// CONTRATO — o app ESCREVE este arquivo:
//   <Common>\Files\XAU_AI_PRO_command.json
//   {
//     "schema"    : "ea-command.v1",
//     "request_id": "<unico por comando>",
//     "token"     : "<igual ao input ExternalBridgeToken>",
//     "confirm"   : true,
//     "ts"        : "YYYY.MM.DD HH:MM:SS",   // hora do servidor, janela de 120 s
//     "action"    : "ping" | "status" | "heartbeat" | "ai"
//   }
//
// O EA RESPONDE em <Common>\Files\XAU_AI_PRO_command_ack.json:
//   {"schema":"ea-ack.v1","request_id":"...","action":"...","ok":true,
//    "result":"...","version":"1.2.9","ts":"..."}
//
// Idempotencia: `request_id` ja processado nao executa de novo (o EA grava
// o ultimo em XAU_AI_PRO_bridge_state.json, para nao repetir apos reattach).
//
// POR QUE AQUI NAO EXISTE ENVIO DE ORDEM: arquivo em Common nao tem
// autenticacao de processo — qualquer coisa rodando na maquina escreve ali.
// Enquanto o canal nao for autenticado, esta ponte serve para PROVAR o
// caminho e LER estado. Nenhuma acao daqui toca risco, posicao, SL/TP ou o
// TradePipeline. Ordem continua nascendo dentro do EA (sinal proprio) ou
// pela mesa.
//==================================================================

#define EB_CMD_FILE      "XAU_AI_PRO_command.json"
#define EB_ACK_FILE      "XAU_AI_PRO_command_ack.json"
#define EB_STATE_FILE    "XAU_AI_PRO_bridge_state.json"
#define EB_MAX_AGE_SEC   120          // comando mais velho que isto e recusado
#define EB_MIN_TOKEN_LEN 8            // token curto = ponte desligada

string   g_eb_last_request = "";
datetime g_eb_last_poll    = 0;

//------------------------------------------------------------------
// A ponte so existe com as DUAS condicoes: chave ligada e token real.
// Sem token o arquivo em Common seria um controle remoto aberto.
//------------------------------------------------------------------
bool ExternalBridgeEnabled()
  {
   if(!EnableExternalBridge)
      return false;

   if(StringLen(ExternalBridgeToken) < EB_MIN_TOKEN_LEN)
      return false;

   return true;
  }

// Mesmo isolamento do heartbeat: em backtest os arquivos da ponte ganham
// sufixo. Sem isto, um backtest responderia o app de producao no lugar da
// conta real. Aplicado na LEITURA e na ESCRITA, num lugar so.
string EB_Name(const string base)
  {
   if(MQLInfoInteger(MQL_TESTER))
      return base + ".tester";

   return base;
  }

string EB_Version()
  {
#ifdef EV_VERSION_STRING
   return EV_VERSION_STRING;
#else
   return "desconhecida";
#endif
  }

//------------------------------------------------------------------
// Le o arquivo inteiro (FILE_COMMON = a pasta Common\Files do terminal).
//------------------------------------------------------------------
bool EB_ReadFile(const string name, string &out)
  {
   out = "";
   ResetLastError();

   const int h = FileOpen(EB_Name(name), FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return false;

   while(!FileIsEnding(h))
      out += FileReadString(h);

   FileClose(h);
   return (StringLen(out) > 0);
  }

bool EB_WriteFile(const string name, const string payload)
  {
   ResetLastError();

   const int h = FileOpen(EB_Name(name), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return false;

   FileWriteString(h, payload);
   FileClose(h);
   return true;
  }

//------------------------------------------------------------------
// Extrator minimo de campo JSON. Nao e parser: o contrato e plano
// (chave: valor escalar), e um parser completo aqui seria codigo sem
// consumidor. Valor entre aspas volta sem aspas; numero/bool volta cru.
//------------------------------------------------------------------
string EB_Field(const string json, const string key)
  {
   const string pat = "\"" + key + "\"";
   int p = StringFind(json, pat);
   if(p < 0)
      return "";

   p = StringFind(json, ":", p + StringLen(pat));
   if(p < 0)
      return "";

   p++;
   while(p < StringLen(json))
     {
      const ushort ch = StringGetCharacter(json, p);
      if(ch != ' ' && ch != '\t')
         break;
      p++;
     }

   if(p >= StringLen(json))
      return "";

   if(StringGetCharacter(json, p) == '"')
     {
      const int e = StringFind(json, "\"", p + 1);
      if(e < 0)
         return "";
      return StringSubstr(json, p + 1, e - p - 1);
     }

   int e = p;
   while(e < StringLen(json))
     {
      const ushort ch = StringGetCharacter(json, e);
      if(ch == ',' || ch == '}' || ch == '\n' || ch == '\r')
         break;
      e++;
     }

   string raw = StringSubstr(json, p, e - p);
   StringTrimRight(raw);
   StringTrimLeft(raw);
   return raw;
  }

string EB_StatusText()
  {
   return StringFormat("state=RUNNING version=%s symbol=%s period=%d positions=%d balance=%.2f equity=%.2f autotrading=%s terminal_trade_allowed=%s trade_gate=%d",
                       EB_Version(),
                       _Symbol,
                       Period(),
                       PositionsTotal(),
                       AccountInfoDouble(ACCOUNT_BALANCE),
                       AccountInfoDouble(ACCOUNT_EQUITY),
                       (CTradeGate::Ok() ? "on" : "off"),
                        ((bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) ? "on" : "off"),
                        (int)CTradeGate::Evaluate());
  }

void EB_WriteAck(const string request_id, const string action, const bool ok,
                 const string result, const datetime when)
  {
   const string ack = StringFormat("{\"schema\":\"ea-ack.v1\",\"request_id\":\"%s\",\"action\":\"%s\",\"ok\":%s,\"result\":\"%s\",\"version\":\"%s\",\"ts\":\"%s\"}",
                                   request_id,
                                   action,
                                   (ok ? "true" : "false"),
                                   result,
                                   EB_Version(),
                                   TimeToString(when, TIME_DATE | TIME_SECONDS));
   EB_WriteFile(EB_ACK_FILE, ack);
  }

//------------------------------------------------------------------
// Chamar uma vez no OnInit: recupera o ultimo request_id processado,
// para um comando nao ser reexecutado depois de reattach/restart.
//------------------------------------------------------------------
void ExternalBridgeInit()
  {
   g_eb_last_request = "";
   g_eb_last_poll    = 0;

   if(!ExternalBridgeEnabled())
      return;

   string raw = "";
   if(!EB_ReadFile(EB_STATE_FILE, raw))
      return;

   g_eb_last_request = EB_Field(raw, "last_request_id");

   Print("[BRIDGE] ponte app->EA ativa | arquivo ", EB_CMD_FILE,
         " | ultimo request_id=", (StringLen(g_eb_last_request) > 0 ? g_eb_last_request : "(nenhum)"));
  }

//------------------------------------------------------------------
// Chamar no OnTick: throttle interno de 1 Hz. Barato quando desligada
// (duas comparacoes) e sem acesso a disco.
//------------------------------------------------------------------
void ExternalBridgePoll()
  {
   if(!ExternalBridgeEnabled())
      return;

   const datetime now = TimeCurrent();
   if(now == g_eb_last_poll)
      return;
   g_eb_last_poll = now;

   string raw = "";
   if(!EB_ReadFile(EB_CMD_FILE, raw))
      return;

   const string request_id = EB_Field(raw, "request_id");
   const string action     = EB_Field(raw, "action");
   const string token      = EB_Field(raw, "token");
   const string confirm    = EB_Field(raw, "confirm");
   const string ts         = EB_Field(raw, "ts");

   if(StringLen(request_id) == 0)
      return;

   // Idempotencia: o mesmo request_id nao executa duas vezes.
   //
   // O ack original ja esta no disco e NAO pode ser sobrescrito: reescrever
   // "duplicado" por cima apagava o resultado real (`pong` virava recusa) e
   // mandava o operador procurar defeito no lado errado. So escreve quando
   // nao existe ack respondendo ESTE request_id â€” o caso de o app ter
   // apagado o ack antes de reenviar o mesmo id.
   if(request_id == g_eb_last_request)
     {
      string ackAnterior = "";
      const bool jaRespondido = (EB_ReadFile(EB_ACK_FILE, ackAnterior) &&
                                 EB_Field(ackAnterior, "request_id") == request_id);

      if(!jaRespondido)
         EB_WriteAck(request_id, action, true, "duplicado: ja processado", now);

      return;
     }

   bool   ok     = false;
   string result = "";

   if(token != ExternalBridgeToken)
      result = "recusado: token invalido";
   else if(confirm != "true")
      result = "recusado: confirm ausente";
   else if(StringLen(ts) > 0 && StringToTime(ts) == 0)
      result = "recusado: ts invalido (esperado \"YYYY.MM.DD HH:MM:SS\" na hora do servidor)";
   else if(StringLen(ts) > 0 && MathAbs((double)(now - StringToTime(ts))) > (double)EB_MAX_AGE_SEC)
      result = "recusado: comando velho (fora da janela de " + IntegerToString(EB_MAX_AGE_SEC) + " s)";
   else
     {
      if(action == "ping")
        {
         ok     = true;
         result = "pong";
        }
      else
         if(action == "status")
           {
            ok     = true;
            result = EB_StatusText();
           }
         else
            if(action == "heartbeat")
              {
               ok     = EAHeartbeatWrite("RUNNING");
               result = (ok ? "heartbeat escrito" : "falha ao escrever heartbeat");
              }
            else
               if(action == "ai")
                 {
                  ok     = true;
                  result = StringFormat("total=%d accuracy=%.2f precision=%.2f recall=%.2f correct=%d wrong=%d tp=%d fp=%d tn=%d fn=%d",
                                        g_aiTotal, AIM_Accuracy(), AIM_Precision(), AIM_Recall(),
                                        g_aiCorrect, g_aiWrong,
                                        g_aiTruePos, g_aiFalsePos, g_aiTrueNeg, g_aiFalseNeg);
                 }
               else
                  result = "recusado: acao desconhecida";
     }

   // Ack sempre, inclusive na recusa: o app precisa do motivo, nao do silencio.
   EB_WriteAck(request_id, action, ok, result, now);

   if(!ok)
     {
      Print("[BRIDGE] comando ", request_id, " recusado: ", result);
      return;
     }

   g_eb_last_request = request_id;
   EB_WriteFile(EB_STATE_FILE,
                StringFormat("{\"last_request_id\":\"%s\",\"ts\":\"%s\"}",
                             request_id, TimeToString(now, TIME_DATE | TIME_SECONDS)));

   Print("[BRIDGE] comando ", request_id, " executado: ", action);
  }

#endif // EXTERNALBRIDGE_MQH
