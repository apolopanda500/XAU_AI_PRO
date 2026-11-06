// XAU_AI_PRO v1.2.9 - SYSTEM STATUS (ETAPA 15.6)
#ifndef SYSTEMSTATUS_MQH
#define SYSTEMSTATUS_MQH

#include "../Core/Config.mqh"
#include "../Core/RiskHub.mqh"
#include "../Core/RiskCenter.mqh"
#include "../Core/PositionManager.mqh"
#include "../AI/AIConnector.mqh"
#include "HealthMonitor.mqh"   // ETAPA 15.6.5: estado multi-nivel do watchdog
#include "../Filters/NewsFilter.mqh"   // self-contained: IsNewsBlocked
#include "../AI/LearningHistory.mqh"   // v1.2.10: WR por simbolo/direcao/hora
#include "../Core/TradeGate.mqh"        // P1.62: veredito unico de negociacao

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
   // P1.62 (v1.2.76): o JSON levava dois bits crus e nenhum veredito; quem
   // lesse "algo_trading_enabled": true concluia "pode negociar" com o EA
   // bloqueado. O veredito passa a viajar junto, com o codigo do estado.
   const ETradeGate gate = CTradeGate::Evaluate();

   // ETAPA 15.6.5: estado multi-nivel (nao apenas true/false)
   return "\"health\": {"
          "\"state\": " + SSQuote(HealthGetStateString()) + ", "
          "\"terminal_connected\": " + SSBool(connected) + ", "
          "\"algo_trading_enabled\": " + SSBool(tradeAllowed) + ", "
          "\"ea_trade_allowed\": " + SSBool(eaTradeOK) + ", "
          "\"trade_gate_ok\": " + SSBool(gate == TG_OK) + ", "
          "\"trade_gate_code\": " + IntegerToString((int)gate) +
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

   // v1.2.11 (29/10/2026): o painel mostrava "blocked=false" sempre que
   // EnableNewsFilter estava desligado, mesmo com o modo "operar noticia"
   // ativo (EnableNewsTrading=true). O estado agora segue o modulo
   // (NewsModuleActive) e e consultado POR SIMBOLO, igual aos gates de
   // ValidateTrade/AllowTrade, em vez de sempre o grafico mestre.
   if(NewsModuleActive())
   {
      double nLotF  = 1.0;
      double nRiskF = 1.0;
      double nTpF   = 1.0;
      string nWhy   = "";

      if(!NewsTradeAllow(symbol, nLotF, nRiskF, nTpF, nWhy))
      {
         blocked=true;
         detail=GetNewsBlockDetail(symbol);
      }
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

//--------------------------------------------------
// APRENDIZADO (WR por simbolo, direcao e hora)
//
// O win rate existia apenas na memoria do EA. Aqui
// ele vai para o painel: sem isso nao ha como saber
// POR QUE o score do simbolo subiu ou caiu, nem quais
// direcoes/horarios o historico reprova.
// -1.0 = amostra insuficiente (nao e "0%").
//--------------------------------------------------

string SSLearningSection(string symbol)
{
   if(!EnableLearningFromHistory)
      return "\"learning\": {\"enabled\": false}";

   int id=FindLearningIndex(symbol);

   int    total=(id>=0 ? g_AIMemory[id].totalTrades : 0);
   int    wins =(id>=0 ? g_AIMemory[id].wins : 0);
   double wr   =(total>0 ? (100.0*wins/total) : 0.0);

   double boost=MemoryBoost(symbol);

   if(boost<1.0 && !LearningPenaltyEnabled)
      boost=1.0;

   int hora=LearningServerHour(TimeCurrent());

   return "\"learning\": {"
          "\"enabled\": true, "
          "\"symbol\": "            + SSQuote(symbol) + ", "
          "\"trades\": "            + IntegerToString(total) + ", "
          "\"wins\": "              + IntegerToString(wins) + ", "
          "\"winrate\": "           + DoubleToString(wr,1) + ", "
          "\"boost\": "             + DoubleToString(boost,2) + ", "
          "\"dir_buy_wr\": "        + DoubleToString(DirRawWinRate(symbol,1),1) + ", "
          "\"dir_buy_n\": "         + IntegerToString(DirTotal(symbol,1)) + ", "
          "\"dir_sell_wr\": "       + DoubleToString(DirRawWinRate(symbol,-1),1) + ", "
          "\"dir_sell_n\": "        + IntegerToString(DirTotal(symbol,-1)) + ", "
          "\"hour\": "              + IntegerToString(hora) + ", "
          "\"hour_wr\": "           + DoubleToString(HourWinRate(symbol,hora),1) + ", "
          "\"hour_n\": "            + IntegerToString(HourTotal(symbol,hora)) + ", "
          "\"dir_block_enabled\": " + SSBool(EnableDirectionBlacklist) + ", "
          "\"summary\": "           + SSQuote(LearningSymbolSummary(symbol)) +
          "}";
}

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
      + SSLearningSection(symbol) + ", "
      + SSAISection(symbol) + ", "
      + SSNewsSection(symbol) + ", "
      + SSPythonSection() + ", "
      + SSDatabaseSection() +
      "}";

   ResetLastError();

   int h=INVALID_HANDLE;
   int ssErr=0;

   // v1.2.108 (03/11/2026): 5004 = ERR_CANNOT_OPEN_FILE medido no journal.
   // Varias instancias abriam o mesmo retrato no mesmo ciclo e a abertura
   // exclusiva falhava. Abre com partilha e repete antes de desistir; o
   // ficheiro, a estrutura JSON, o throttle de 15s e o aviso 1x/sessao ficam.
   for(int tentativa=0; tentativa<3; tentativa++)
     {
      ResetLastError();

      h=FileOpen(
         "Data\\system_status.json",
         FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,
         0
      );

      if(h!=INVALID_HANDLE)
         break;

      ssErr=GetLastError();

      // Janela de conflito e de milissegundos: cede o escalonamento e repete.
      Sleep(20);
     }

   if(h==INVALID_HANDLE)
   {
      // v1.2.85 (02/11/2026) - P1.72: MEDIDO 71 linhas hoje. A causa e o
      // ficheiro de estado comum ser aberto por 17 instancias no mesmo
      // instante (5004 = ERR_CANNOT_WRITE_FILE, ficheiro ocupado). O retrato
      // e reescrito no ciclo seguinte, logo a falha e transitoria por
      // construcao: passa a sair UMA linha por sessao, com o codigo, em vez
      // de uma por ciclo. Nada muda no que e escrito quando a abertura passa.
      static bool s_avisouStatusWrite = false;


      if(!s_avisouStatusWrite)
        {
         s_avisouStatusWrite = true;
         Print("[STATUS] WRITE ERROR | Code=",ssErr,
               " | aviso 1x/sessao | 5004 = ficheiro de estado ocupado por outra instancia;",
               " o retrato e reescrito no ciclo seguinte");
        }
      return;
   }

   FileWriteString(h,json);
   FileClose(h);
}

#endif // SYSTEMSTATUS_MQH
