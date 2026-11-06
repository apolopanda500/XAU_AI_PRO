//+------------------------------------------------------------------+
//|                                                      MCPServer.mqh |
//| XAU_AI_PRO v1.2.116 — Servidor MCP (Model Context Protocol)      |
//| Expõe funcionalidades do EA para agentes de IA via MCP           |
//+------------------------------------------------------------------+
// CORRECAO v1.2.116 — o modulo compilava e nao cumpria o que prometia.
// Medido no ficheiro anterior (v1.2.111):
//   (1) GetChecklistStatus() devolvia "true","true","false" FIXOS, sem ler
//       nada: um agente recebia production_ready=true mesmo com o EA em
//       SAFE_MODE e a checklist reprovada.
//   (2) ValidateTrade() recebia type, sl e tp e nao olhava para nenhum dos
//       tres: dizia {\"valid\":true} para um SL do lado errado.
//   (3) LogRequest() descartava operation e success (nao escrevia nada).
//   (4) GetOpenPositions() devolvia posicoes de QUALQUER programa da conta.
//   (5) MCPInitServer()/MCPHandleRequest() estavam DECLARADOS e nunca
//       definidos — erro de link no primeiro chamador.
//   (6) Init() marcava m_initialized=true com token vazio, logo IsEnabled()
//       e a mensagem do journal discordavam do estado real.
// Nenhum limite de risco, lote, spread, alvo ou regra de entrada foi
// tocado: muda apenas o que a API responde e o que fica no journal.
//
// CORRECAO P2.09 (03/11/2026) — quatro defeitos medidos por leitura:
//   (1) CheckToken() estava DEFINIDO e nunca era CHAMADO. MCPHandleRequest()
//       testava apenas IsEnabled(), logo o input MCPServerToken nao protegia
//       nada: qualquer chamador lia conta, posicoes e risco sem apresentar
//       token. Passa a existir MCPHandleRequest(method, params, token) que
//       verifica o token ANTES de tocar em qualquer metodo.
//   (2) CheckToken() incrementava m_rejected_count e o chamador voltava a
//       incrementar em LogRequest(..., false): uma recusa somava 2 e o
//       numero publicado no journal nao media nada. Os contadores passam a
//       ser exclusivos do LogRequest().
//   (3) Em trade.validate, StringToInteger("") devolve 0, que e
//       ORDER_TYPE_BUY: um pedido SEM "type" era validado como COMPRA. Os
//       parametros symbol/type/lots passam a ser exigidos explicitamente.
//   (4) O simbolo vinha do chamador e entrava cru no JSON ("%s"): uma aspa
//       no nome quebrava o documento devolvido ao agente. Passa por
//       MCPJsonEsc().
// Continua a nao existir socket, envio de ordem, alteracao de lote, spread,
// alvo ou parametro de risco: muda apenas autenticacao e formato.
//
// O EA nao abre socket. Este modulo e uma API in-process: quem transporta
// os pedidos e um processo externo, que faz a autenticacao. Por isso nao
// ha credenciais em transito aqui.
//+------------------------------------------------------------------+
#ifndef XAI_MCP_SERVER_MQH
#define XAI_MCP_SERVER_MQH

#include "../Core/Config.mqh"
#include "../Core/RiskHub.mqh"
#include "../Core/TradeGate.mqh"
#include "../Core/SymbolValidator.mqh"   // ValidateSymbol() usado em ValidateTrade()
#include "../Core/StateMachine.mqh"
#include "../AI/AIConnector.mqh"
#include "../Monitoring/HealthMonitor.mqh"
#include "../Monitoring/ValidationChecklist.mqh"
#include "../Monitoring/ProductionChecklist.mqh"
#include "../Monitoring/AccountLogGate.mqh"
// P2.10 (03/11/2026): o modulo compilava DENTRO do EA mas nao FORA dele —
// CTRL+F7 sobre este ficheiro dava 19 erros. Causa medida: dependia de
// simbolos definidos em headers que o .mq5 inclui DEPOIS deste:
//   GetATR()             -> Indicators/VolatilityFilter.mqh (chamado em Config.mqh)
//   DiagGateAllow()      -> Monitoring/DiagGate.mqh (chamado em StateMachine.mqh)
//   GetSignal()          -> Core/SignalCore.mqh
//   GetAIConfidence(i,s) -> AI/AIEngine.mqh
//   SafeMode / RecoveryRunning -> globais do .mq5 que nunca eram escritos
// As dependencias passam a ser declaradas aqui e o estado de saude passa a
// ser lido dos modulos que o produzem, nao de variaveis mortas do host.
#include "../Indicators/VolatilityFilter.mqh"   // GetATR() usado em Config.mqh
#include "../Monitoring/DiagGate.mqh"           // DiagGateAllow() usado em StateMachine.mqh
#include "../Core/SignalCore.mqh"               // GetSignal()
#include "../AI/AIEngine.mqh"                   // GetAIConfidence(signal,symbol)
#include "../Enterprise/CircuitBreaker.mqh"     // CCircuitBreaker::IsSafeMode()
#include "../Enterprise/RecoveryManager.mqh"    // CRecoveryManager::GetStatus()

// Token minimo aceito. Config.mqh anuncia "8+ caracteres"; o codigo
// anterior aceitava vazio e ficava num estado ambiguo.
#define MCP_MIN_TOKEN_LEN 8

//+------------------------------------------------------------------+
//| Estruturas de resposta MCP                                       |
//+------------------------------------------------------------------+
struct MCPResponse
{
   bool   success;
   string data;
   string error;
};

//+------------------------------------------------------------------+
//| Resposta vazia — evita membros por inicializar                   |
//+------------------------------------------------------------------+
MCPResponse MCPEmpty()
{
   MCPResponse r;
   r.success = false;
   r.data    = "";
   r.error   = "";
   return(r);
}

//+------------------------------------------------------------------+
//| true/false em JSON                                               |
//+------------------------------------------------------------------+
string MCPBool(const bool v)
{
   return(v ? "true" : "false");
}

//+------------------------------------------------------------------+
//| Escapa aspas, barras e quebras de linha de um valor vindo do       |
//| chamador. Sem isto, um simbolo como XAU"USD quebrava o JSON que o   |
//| agente ia ler, porque o valor era interpolado em "%s".            |
//+------------------------------------------------------------------+
string MCPJsonEsc(const string s)
{
   if(s == "") return("");

   string out = s;
   StringReplace(out, "\\", "\\\\");
   StringReplace(out, "\"", "\\\"");
   StringReplace(out, "\r", " ");
   StringReplace(out, "\n", " ");
   return(out);
}

//+------------------------------------------------------------------+
//| Classe MCP Server                                                |
//+------------------------------------------------------------------+
class CMCPServer
{
private:
   bool   m_initialized;
   string m_token;
   int    m_request_count;
   int    m_rejected_count;

public:
   void Init(const string token = "");
   bool IsEnabled() const   { return(m_initialized && StringLen(m_token) >= MCP_MIN_TOKEN_LEN); }
   int  RequestCount() const  { return(m_request_count); }
   int  RejectedCount() const { return(m_rejected_count); }
   // P2.08: corre os metodos de LEITURA uma vez e devolve o resultado.
   string SelfTest();

   //--- Operações de leitura (sempre permitidas se token válido)
   MCPResponse GetRiskStatus();
   MCPResponse GetAISignal(const string symbol = "");
   MCPResponse GetHealthStatus();
   MCPResponse GetAccountInfo();
   MCPResponse GetOpenPositions();
   MCPResponse GetChecklistStatus();

   //--- Operações de execução (requer confirmação explícita)
   MCPResponse ValidateTrade(const string symbol, long type, double lots, double sl, double tp, string &reason);
   MCPResponse GetTradeGateVerdict();

   //--- Utilitário de autenticação
   bool CheckToken(const string token);

   void LogRequest(const string operation, bool success);
};

//+------------------------------------------------------------------+
//| Variável global                                                  |
//+------------------------------------------------------------------+
CMCPServer MCPServer;

//+------------------------------------------------------------------+
void CMCPServer::Init(const string token)
{
   m_token          = token;
   m_initialized    = (StringLen(token) >= MCP_MIN_TOKEN_LEN);
   m_request_count  = 0;
   m_rejected_count = 0;

   // Com token vazio/curto o servidor fica DESLIGADO e diz por que.
   if(!m_initialized && AccountLogGatePodeImprimir("mcp_init", 3600))
      Print("[MCP] desligado | token com ", StringLen(token), " caracteres, minimo ", MCP_MIN_TOKEN_LEN);
}

//+------------------------------------------------------------------+
bool CMCPServer::CheckToken(const string token)
{
   // Os contadores pertencem ao LogRequest(). Antes esta funcao somava
   // m_rejected_count e o chamador somava outra vez em LogRequest(...,false),
   // portanto uma recusa contava 2 e o valor do journal era inutil.
   if(!IsEnabled())                          return(false);
   if(StringLen(token) < MCP_MIN_TOKEN_LEN)  return(false);
   return(token == m_token);
}

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| CMCPServer::SelfTest                                            |
//| P2.08: prova de vida da API MCP. Corre os SETE metodos de LEITURA|
//| uma vez e devolve a contagem e o estado de cada um, para que o    |
//| arranque possa afirmar que o servidor responde de facto em vez de |
//| dizer apenas que o input esta ligado. Nao envia, modifica nem     |
//| fecha nada: nenhum destes metodos toca em ordens ou em risco.     |
//+------------------------------------------------------------------+
string CMCPServer::SelfTest()
{
   if(!IsEnabled()) return("desligado (token com menos de " + IntegerToString(MCP_MIN_TOKEN_LEN) + " caracteres)");

   string partes[];
   int n = StringSplit("risk ai health account positions checklist gate", (ushort)32, partes);

   string out = "";
   int ok = 0;
   for(int i = 0; i < n; i++)
     {
      MCPResponse r = MCPEmpty();
      if(i == 0)      r = GetRiskStatus();
      else if(i == 1) r = GetAISignal("");
      else if(i == 2) r = GetHealthStatus();
      else if(i == 3) r = GetAccountInfo();
      else if(i == 4) r = GetOpenPositions();
      else if(i == 5) r = GetChecklistStatus();
      else            r = GetTradeGateVerdict();

      if(r.success) ok++;
      out += (i == 0 ? "" : " ") + partes[i] + "=" + (r.success ? "ok" : "falha");
     }
   return(IntegerToString(ok) + "/" + IntegerToString(n) + " " + out);
}

//+------------------------------------------------------------------+
MCPResponse CMCPServer::GetRiskStatus()
{
   MCPResponse resp = MCPEmpty();

   double peak   = GetDailyPeakEquity();
   double dd     = GetDrawdownPercent();
   int    trades = GetEffectiveDailyTradesCount();
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance= AccountInfoDouble(ACCOUNT_BALANCE);

   resp.success = true;
   resp.data = StringFormat(
      "{\"peak_equity\":%.2f,\"drawdown_pct\":%.2f,\"trades_today\":%d,\"equity\":%.2f,\"balance\":%.2f,\"max_daily_loss_pct\":%.2f,\"max_drawdown_pct\":%.2f}",
      peak, dd, trades, equity, balance, MaxDailyLossPercent, MaxDrawdownPercent
   );

   return(resp);
}

//+------------------------------------------------------------------+
MCPResponse CMCPServer::GetAISignal(const string symbol)
{
   MCPResponse resp = MCPEmpty();

   string sym = (symbol == "") ? _Symbol : symbol;
   int signal = GetSignal(sym);
   double conf = GetAIConfidence(signal, sym);

   resp.success = true;
   resp.data = StringFormat(
      "{\"symbol\":\"%s\",\"signal\":%d,\"confidence\":%.4f,\"buy_prob\":%.4f,\"sell_prob\":%.4f,\"score\":%.4f,\"is_stale\":%s,\"age_sec\":%.0f}",
      MCPJsonEsc(sym), signal, conf, AI_BuyProbability, AI_SellProbability, AI_Score,
      AI_IsStale ? "true" : "false", AI_AgeSeconds
   );

   return(resp);
}

//+------------------------------------------------------------------+
MCPResponse CMCPServer::GetHealthStatus()
{
   MCPResponse resp = MCPEmpty();

   // P2.10: SafeMode e RecoveryRunning eram globais declarados no .mq5 e
   // NUNCA escritos em lado nenhum (mortos): o modulo publicava sempre
   // false e, fora do EA, nem compilava. Passa a ler a fonte real do estado.
   bool           safeMode = CCircuitBreaker::IsSafeMode();
   RecoveryStatus recState = CRecoveryManager::GetStatus();
   bool           recovery = (recState == RECOVERY_CRITICAL || recState == RECOVERY_FAILED);

   string status = "HEALTHY";
   if(safeMode)  status = "SAFE_MODE";
   if(recovery)  status = "RECOVERY";

   // v1.2.116: "trade_allowed" lia so MQL_TRADE_ALLOWED, um dos 5 bits, e
   // podia dizer false com o trading liberado (ou true com o terminal off).
   // Passa a publicar o veredicto de Core/TradeGate.mqh, a mesma fonte que o
   // resto do EA usa.
   ETradeGate gate = CTradeGate::Evaluate();

   resp.success = true;
   resp.data = StringFormat(
      "{\"status\":\"%s\",\"safe_mode\":%s,\"recovery_running\":%s,\"recovery_state\":\"%s\",\"connected\":%s,\"trade_gate\":\"%s\",\"trade_gate_code\":%d,\"trade_allowed\":%s}",
      status,
      MCPBool(safeMode),
      MCPBool(recovery),
      EnumToString(recState),
      MCPBool(CTradeGate::Connected()),
      EnumToString(gate),
      (int)gate,
      MCPBool(gate == TG_OK)
   );

   return(resp);
}

//+------------------------------------------------------------------+
MCPResponse CMCPServer::GetAccountInfo()
{
   MCPResponse resp = MCPEmpty();

   resp.success = true;
   resp.data = StringFormat(
      "{\"login\":%I64d,\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"free_margin\":%.2f,\"margin_level\":%.2f,\"profit\":%.2f,\"leverage\":%I64d,\"currency\":\"%s\"}",
      (long)AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoDouble(ACCOUNT_BALANCE),
      AccountInfoDouble(ACCOUNT_EQUITY),
      AccountInfoDouble(ACCOUNT_MARGIN),
      AccountInfoDouble(ACCOUNT_MARGIN_FREE),
      AccountInfoDouble(ACCOUNT_MARGIN_LEVEL),
      AccountInfoDouble(ACCOUNT_PROFIT),
      (long)AccountInfoInteger(ACCOUNT_LEVERAGE),
      AccountInfoString(ACCOUNT_CURRENCY)
   );

   return(resp);
}

//+------------------------------------------------------------------+
//| Posicoes do EA. As de outros programas sao CONTADAS, nao listadas:|
//| um agente que gere o XAU_AI_PRO nao deve mexer no que nao e dele. |
//+------------------------------------------------------------------+
MCPResponse CMCPServer::GetOpenPositions()
{
   MCPResponse resp = MCPEmpty();

   int total   = PositionsTotal();
   int minhas  = 0;
   int alheias = 0;
   string json = "[";

   for(int i = total - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;

      // PositionGetTicket() ja selecionou a posicao: as leituras seguintes
      // referem-se a ela.
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
        {
         alheias++;
         continue;
        }

      string sym   = PositionGetString(POSITION_SYMBOL);
      long   type  = PositionGetInteger(POSITION_TYPE);
      double lots  = PositionGetDouble(POSITION_VOLUME);
      double price = PositionGetDouble(POSITION_PRICE_OPEN);
      double cur   = PositionGetDouble(POSITION_PRICE_CURRENT);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      double profit= PositionGetDouble(POSITION_PROFIT);
      int    dig   = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
      if(dig <= 0) dig = _Digits;

      if(minhas > 0) json += ",";
      json += "{\"ticket\":" + IntegerToString((long)ticket)
            + ",\"symbol\":\"" + sym + "\""
            + ",\"type\":" + IntegerToString(type)
            + ",\"lots\":" + DoubleToString(lots, 2)
            + ",\"price_open\":" + DoubleToString(price, dig)
            + ",\"price_current\":" + DoubleToString(cur, dig)
            + ",\"sl\":" + DoubleToString(sl, dig)
            + ",\"tp\":" + DoubleToString(tp, dig)
            + ",\"profit\":" + DoubleToString(profit, 2)
            + "}";
      minhas++;
     }
   json += "]";

   resp.success = true;
   resp.data = StringFormat(
      "{\"count\":%d,\"count_foreign\":%d,\"magic\":%I64d,\"positions\":%s}",
      minhas, alheias, MagicNumber, json
   );

   return(resp);
}

//+------------------------------------------------------------------+
//| Estado das checklists REAIS (ultima execucao), nao fixo.         |
//| Nao chama Run(): as checklists escrevem no journal e custam      |
//| caro; o retrato publicado e o da ultima execucao, e o campo      |
//| "source" diz isso em vez de deixar o leitor supor que e ao vivo. |
//+------------------------------------------------------------------+
MCPResponse CMCPServer::GetChecklistStatus()
{
   MCPResponse resp = MCPEmpty();

   int  prodPassed   = CProductionChecklist::GetPassedCount();
   int  prodFailed   = CProductionChecklist::GetFailedCount();
   int  prodCritical = CProductionChecklist::GetCriticalFailedCount();
   bool prodReady    = CProductionChecklist::IsReady();
   bool valPassed    = ValidationChecklistPassed();

   resp.success = true;
   resp.data = StringFormat(
      "{\"source\":\"last_run\",\"production_ready\":%s,\"production_passed\":%d,\"production_failed\":%d,\"production_critical_failed\":%d,\"validation_ready\":%s,\"blocked_critical\":%s}",
      MCPBool(prodReady), prodPassed, prodFailed, prodCritical,
      MCPBool(valPassed), MCPBool(prodCritical > 0)
   );

   return(resp);
}

//+------------------------------------------------------------------+
//| Valida um pedido de entrada SEM enviar ordem.                    |
//| Cobre: porta de negociacao, simbolo/volume, tipo, lado e          |
//| distancia minima de SL/TP (SYMBOL_TRADE_STOPS_LEVEL) e margem.   |
//+------------------------------------------------------------------+
MCPResponse CMCPServer::ValidateTrade(const string symbol, long type, double lots, double sl, double tp, string &reason)
{
   MCPResponse resp = MCPEmpty();
   reason = "";

   if(symbol == "")
     {
      reason = "simbolo vazio";
      resp.error = reason;
      return(resp);
     }
   if(lots <= 0.0)
     {
      reason = "lote invalido (" + DoubleToString(lots, 2) + ")";
      resp.error = reason;
      return(resp);
     }
   if(type != ORDER_TYPE_BUY && type != ORDER_TYPE_SELL)
     {
      reason = "tipo nao suportado: " + IntegerToString(type) + " (0=BUY, 1=SELL)";
      resp.error = reason;
      return(resp);
     }

   ETradeGate gate = CTradeGate::Evaluate();
   if(gate != TG_OK)
     {
      reason = "TradeGate: " + CTradeGate::Cause(gate);
      resp.error = reason;
      return(resp);
     }

   // O ponto tem de vir do SIMBOLO PEDIDO, nunca de _Point (que e o do
   // grafico onde o EA esta pendurado).
   double ponto   = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int    digitos = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(ponto <= 0.0)
     {
      reason = "simbolo desconhecido ou sem SYMBOL_POINT: " + symbol;
      resp.error = reason;
      return(resp);
     }
   if(digitos <= 0) digitos = 2;

   // SymbolValidator cobre selecao no Market Watch, bid/ask>0, lote
   // minimo/maximo/passo e volume.
   string valReason = "";
   if(!ValidateSymbol(symbol, lots, 0.0, valReason))
     {
      reason = valReason;
      resp.error = reason;
      return(resp);
     }

   double bid  = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask  = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double preco = (type == ORDER_TYPE_BUY) ? ask : bid;

   // Servidor sem stops level declarado: usa 1 ponto, o minimo que o
   // MetaTrader aceita em qualquer simbolo.
   double stopsPts = (double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(stopsPts <= 0.0) stopsPts = 1.0;
   double distMin = stopsPts * ponto;

   if(sl > 0.0)
     {
      if(type == ORDER_TYPE_BUY && sl > preco - distMin)
        {
         reason = "SL de compra tem de ficar <= " + DoubleToString(preco - distMin, digitos)
                + " (preco " + DoubleToString(preco, digitos)
                + ", stops " + DoubleToString(stopsPts, 0) + " pontos)";
         resp.error = reason;
         return(resp);
        }
      if(type == ORDER_TYPE_SELL && sl < preco + distMin)
        {
         reason = "SL de venda tem de ficar >= " + DoubleToString(preco + distMin, digitos)
                + " (preco " + DoubleToString(preco, digitos)
                + ", stops " + DoubleToString(stopsPts, 0) + " pontos)";
         resp.error = reason;
         return(resp);
        }
     }

   if(tp > 0.0)
     {
      if(type == ORDER_TYPE_BUY && tp < preco + distMin)
        {
         reason = "TP de compra tem de ficar >= " + DoubleToString(preco + distMin, digitos)
                + " (preco " + DoubleToString(preco, digitos)
                + ", stops " + DoubleToString(stopsPts, 0) + " pontos)";
         resp.error = reason;
         return(resp);
        }
      if(type == ORDER_TYPE_SELL && tp > preco - distMin)
        {
         reason = "TP de venda tem de ficar <= " + DoubleToString(preco - distMin, digitos)
                + " (preco " + DoubleToString(preco, digitos)
                + ", stops " + DoubleToString(stopsPts, 0) + " pontos)";
         resp.error = reason;
         return(resp);
        }
     }

   // SL e TP coerentes entre si (o servidor tambem recusa, mas o motivo
   // tem de sair daqui, legivel).
   if(sl > 0.0 && tp > 0.0)
     {
      if(type == ORDER_TYPE_BUY && sl >= tp)
        {
         reason = "numa compra o SL tem de ser menor que o TP";
         resp.error = reason;
         return(resp);
        }
      if(type == ORDER_TYPE_SELL && sl <= tp)
        {
         reason = "numa venda o SL tem de ser maior que o TP";
         resp.error = reason;
         return(resp);
        }
     }

   // Margem: a mesma funcao que o servidor usa; falha = recusa explicita.
   double margem = 0.0;
   if(!OrderCalcMargin((ENUM_ORDER_TYPE)type, symbol, lots, preco, margem))
     {
      reason = "OrderCalcMargin falhou | err=" + IntegerToString(GetLastError());
      resp.error = reason;
      return(resp);
     }
   double livre = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(margem > livre)
     {
      reason = "margem insuficiente: precisa " + DoubleToString(margem, 2)
             + ", livre " + DoubleToString(livre, 2);
      resp.error = reason;
      return(resp);
     }

   resp.success = true;
   resp.data = "{\"valid\":true"
             + ",\"symbol\":\"" + MCPJsonEsc(symbol) + "\""
             + ",\"type\":" + IntegerToString(type)
             + ",\"lots\":" + DoubleToString(lots, 2)
             + ",\"price\":" + DoubleToString(preco, digitos)
             + ",\"sl\":" + DoubleToString(sl, digitos)
             + ",\"tp\":" + DoubleToString(tp, digitos)
             + ",\"stops_level_points\":" + DoubleToString(stopsPts, 0)
             + ",\"margin\":" + DoubleToString(margem, 2)
             + "}";
   return(resp);
}

//+------------------------------------------------------------------+
MCPResponse CMCPServer::GetTradeGateVerdict()
{
   MCPResponse resp = MCPEmpty();

   ETradeGate gate = CTradeGate::Evaluate();
   resp.success = true;
   resp.data = StringFormat("{\"verdict\":\"%s\",\"code\":%d,\"cause\":\"%s\"}",
                            EnumToString(gate), (int)gate, CTradeGate::Cause(gate));
   return(resp);
}

//+------------------------------------------------------------------+
//| Registo: antes nao escrevia nada. Gate por conta para um agente  |
//| a sondar em ciclo nao encher o journal.                          |
//+------------------------------------------------------------------+
void CMCPServer::LogRequest(const string operation, bool success)
{
   m_request_count++;
   if(!success) m_rejected_count++;

   if(!AccountLogGatePodeImprimir("mcp_req", 60)) return;

   Print("[MCP] ", operation, " | ok=", MCPBool(success),
         " | pedidos=", m_request_count, " | recusados=", m_rejected_count);
}

//+------------------------------------------------------------------+
//| Parametros no formato "chave=valor;chave=valor"                  |
//| (o EA nao abre socket e nao transporta credenciais; a autentica- |
//| cao e do processo externo que chama esta API)                    |
//+------------------------------------------------------------------+
string MCPParamGet(const string params, const string key)
{
   if(params == "" || key == "") return("");

   string partes[];
   int n = StringSplit(params, ';', partes);
   for(int i = 0; i < n; i++)
     {
      string kv = partes[i];
      int eq = StringFind(kv, "=");
      if(eq <= 0) continue;

      string k = StringSubstr(kv, 0, eq);
      string v = StringSubstr(kv, eq + 1);
      StringTrimLeft(k);
      StringTrimRight(k);
      StringTrimLeft(v);
      StringTrimRight(v);

      if(k == key) return(v);
     }
   return("");
}

//+------------------------------------------------------------------+
//| API externa — declarada e agora DEFINIDA                         |
//+------------------------------------------------------------------+
void MCPInitServer(const string token = "")
{
   MCPServer.Init(token);
}

//+------------------------------------------------------------------+
//| AUTENTICACAO — unico ponto de entrada da API.                    |
//| Antes so IsEnabled() era testado e CheckToken() nunca era chamado;|
//| com isso o input MCPServerToken nao protegia nada. O token passa  |
//| a ser verificado ANTES de qualquer metodo ser executado.          |
//+------------------------------------------------------------------+
MCPResponse MCPHandleRequest(const string method, const string params_json, const string token)
{
   MCPResponse resp = MCPEmpty();

   if(!MCPServer.IsEnabled())
     {
      resp.error = "MCP desligado (EnableMCPServer=false ou token < "
                 + IntegerToString(MCP_MIN_TOKEN_LEN) + " caracteres)";
      MCPServer.LogRequest("recusado:" + method, false);
      return(resp);
     }

   if(!MCPServer.CheckToken(token))
     {
      resp.error = "token invalido ou em falta (minimo "
                 + IntegerToString(MCP_MIN_TOKEN_LEN) + " caracteres)";
      MCPServer.LogRequest("recusado:" + method, false);
      return(resp);
     }

   string m = method;
   StringToLower(m);

   if(m == "risk.status")
      resp = MCPServer.GetRiskStatus();
   else if(m == "ai.signal")
      resp = MCPServer.GetAISignal(MCPParamGet(params_json, "symbol"));
   else if(m == "health.status")
      resp = MCPServer.GetHealthStatus();
   else if(m == "account.info")
      resp = MCPServer.GetAccountInfo();
   else if(m == "positions.open")
      resp = MCPServer.GetOpenPositions();
   else if(m == "checklist.status")
      resp = MCPServer.GetChecklistStatus();
   else if(m == "gate.verdict")
      resp = MCPServer.GetTradeGateVerdict();
   else if(m == "trade.validate")
     {
      string sym     = MCPParamGet(params_json, "symbol");
      string rawType = MCPParamGet(params_json, "type");
      string rawLots = MCPParamGet(params_json, "lots");

      // StringToInteger("") devolve 0, que e ORDER_TYPE_BUY: sem estas
      // guardas um pedido sem "type" era validado como COMPRA.
      if(sym == "")
         resp.error = "parametro 'symbol' em falta";
      else if(rawType == "")
         resp.error = "parametro 'type' em falta (0=BUY, 1=SELL)";
      else if(rawLots == "")
         resp.error = "parametro 'lots' em falta";
      else
        {
         string why = "";
         resp = MCPServer.ValidateTrade(sym,
                                        (long)StringToInteger(rawType),
                                        StringToDouble(rawLots),
                                        StringToDouble(MCPParamGet(params_json, "sl")),
                                        StringToDouble(MCPParamGet(params_json, "tp")),
                                        why);
         if(!resp.success && resp.error == "" && why != "")
            resp.error = why;
        }
     }
   else
      resp.error = "metodo desconhecido: " + method;

   MCPServer.LogRequest(method, resp.success);
   return(resp);
}

//+------------------------------------------------------------------+
//| Sobrecarga de dois argumentos: mantida para nao quebrar chamador |
//| existente. Sem token o pedido e RECUSADO quando o servidor esta   |
//| ligado, porque e exactamente isso que MCPServerToken promete.     |
//+------------------------------------------------------------------+
MCPResponse MCPHandleRequest(const string method, const string params_json)
{
   return(MCPHandleRequest(method, params_json, ""));
}

#endif
