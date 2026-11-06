// XAU_AI_PRO v1.2.9
#ifndef VALIDATIONENGINE_MQH
#define VALIDATIONENGINE_MQH

#include "../Core/Config.mqh"

#include "../Filters/SpreadFilter.mqh"
#include "../Filters/SessionFilter.mqh"
#include "../Filters/TrendFilter.mqh"
#include "../Filters/MultiTimeframeFilter.mqh"
#include "../Filters/NewsFilter.mqh"
#include "../Filters/MarketRegime.mqh"
#include "../Filters/MarketScenario.mqh"   // v1.2.21: cenario global
#include "../Filters/GlobalScenario.mqh"    // v1.2.23: horas proibidas em GMT

#include "../Indicators/ADX.mqh"

#include "../AI/AIEngine.mqh"

// F4/20.15: contador de bloqueos por ADX inválido (valor válido < MinimumADX).
// Complementa a los contadores de ADX.mqh (unavailable/valid). Si block_count
// crece mucho, el filtro ADX está siendo el cuello de botella de validación.
int g_adxBlockCount = 0;

//==================================================
// THROTTLE DE LOG DE VALIDACAO (v1.2.16, 29/10/2026)
//==================================================
// Medido no journal do Strategy Tester: um job de 3 meses em USDBRL gerou
// 1,08 GB de log em ~25 minutos. Causa: ValidateTrade() roda a cada tick e
// cada chamada imprimia de 2 a 4 linhas ("[VALIDATION] <sym> | Spread=..",
// "[VALIDATION] <sym> | ADX=..", "[VALIDATION] BLOCK | TREND BUY | <sym>"),
// sempre com o mesmo conteudo. Repetir a mesma recusa a cada tick nao
// acrescenta informacao e o volume de I/O chega a inviabilizar o backtest.
// Aqui cada par simbolo+motivo imprime no maximo 1x por janela, usando o
// horario do servidor (no tester = tempo simulado). Cada instancia do EA tem
// sua propria tabela, portanto a janela vale por grafico.
#define VALIDATION_LOG_SLOTS  64
#define VALIDATION_LOG_WINDOW 300

string   g_valLogKey[VALIDATION_LOG_SLOTS];
datetime g_valLogLast[VALIDATION_LOG_SLOTS];
int      g_valLogUsed = 0;

// v1.2.20 (29/10/2026): o scanner dizia apenas
// "[SCANNER] BLOCK | AllowTrade (Validation/Score/IA)" e o dono nao sabia
// QUAL dos gates barrou (spread? hora proibida? ADX? noticia? score? IA?).
// ValidateTrade ja chama ValidationLogAllowed() com o motivo exato em TODA
// saida de bloqueio, entao basta memoriza-lo aqui para o chamador exibir
// junto do seu proprio log. Recurso apenas de diagnostico: nao decide nada.
string   g_validationLastBlock = "";

// Motivos de bloqueio sao os que NAO sao informativos: as chamadas com
// "INFO"/" OK"/"APPROVED"/"SKIP" descrevem o caminho aprovado e nao podem
// sobrescrever o motivo real do veto.
bool ValidationReasonIsBlock(string reason)
{
   if(reason == "")
      return false;

   if(StringFind(reason, "INFO") >= 0)
      return false;

   if(StringFind(reason, "OK") >= 0)
      return false;

   if(StringFind(reason, "APPROVED") >= 0)
      return false;

   if(StringFind(reason, "SKIP") >= 0)
      return false;

   return true;
}

// P2.15 (03/11/2026): o corpo abaixo passou a ser a janela por INSTANCIA e o
// portao por CONTA embrulha-o em ValidationLogAllowed(). Renomeado, sem
// alteracao de logica; o g_validationLastBlock continua a ser escrito aqui,
// antes de qualquer filtro, como sempre foi.
bool ValidationLogAllowedLocal(string symbol, string reason)
{
   if(ValidationReasonIsBlock(reason))
      g_validationLastBlock = reason;

   string key = symbol + "|" + reason;
   datetime now = TimeCurrent();

   for(int i = 0; i < g_valLogUsed; i++)
   {
      if(g_valLogKey[i] != key)
         continue;

      if(now - g_valLogLast[i] < VALIDATION_LOG_WINDOW)
         return false;

      g_valLogLast[i] = now;
      return true;
   }

   if(g_valLogUsed >= VALIDATION_LOG_SLOTS)
   {
      // Tabela cheia: descarta a entrada mais antiga (FIFO) em vez de liberar
      // o log sem limite quando muitos motivos se acumulam.
      for(int j = 1; j < VALIDATION_LOG_SLOTS; j++)
      {
         g_valLogKey[j-1]  = g_valLogKey[j];
         g_valLogLast[j-1] = g_valLogLast[j];
      }

      g_valLogUsed = VALIDATION_LOG_SLOTS - 1;
   }

   g_valLogKey[g_valLogUsed]  = key;
   g_valLogLast[g_valLogUsed] = now;
   g_valLogUsed++;

   return true;
}

//+------------------------------------------------------------------+
//| P2.15 (03/11/2026) - um facto por CONTA, nao por grafico.         |
//| A janela acima e por INSTANCIA (o comentario de v1.2.16 di-lo:    |
//| "a janela vale por grafico"). Com 15 graficos, o MESMO veto saia  |
//| uma vez em cada um a cada 5 min. MEDIDO no journal do expert:     |
//| "[VALIDATION] BLOCK | TREND SELL | <sym> | contramao vetada |     |
//| ADX indisponivel" 23 vezes na sessao, sempre o mesmo texto e      |
//| sempre o mesmo par simbolo+motivo. Aqui a mesma chave passa       |
//| tambem pelo portao por conta (Monitoring\AccountLogGate.mqh), com |
//| a mesma janela de 5 min: a primeira instancia escreve, as outras  |
//| calam-se. No tester nao ha portao (FILE_COMMON e partilhado entre |
//| passes): cada passe continua a registar o proprio veto. Decide    |
//| apenas se a linha volta a sair; nenhuma validacao muda.          |
//+------------------------------------------------------------------+
string ValidationGateTag(string symbol, string reason)
{
   string tag = symbol + "_" + reason;

   // O portao usa a tag como NOME DE FICHEIRO: nada de "|", "=", "%", ">".
   StringReplace(tag, " ", "_");
   StringReplace(tag, "|", "_");
   StringReplace(tag, "=", "_");
   StringReplace(tag, "-", "_");
   StringReplace(tag, ".", "p");
   StringReplace(tag, "%", "pc");
   StringReplace(tag, ">", "g");
   StringReplace(tag, "<", "l");
   StringReplace(tag, ",", "_");

   if(StringLen(tag) > 48)
      tag = StringSubstr(tag, 0, 48);

   return("val_" + tag);
}

bool ValidationLogAllowed(string symbol, string reason)
{
   if(!ValidationLogAllowedLocal(symbol, reason))
      return(false);

   if(MQLInfoInteger(MQL_TESTER))
      return(true);

   return(AccountLogGatePodeImprimir(ValidationGateTag(symbol, reason), VALIDATION_LOG_WINDOW));
}


//==================================================
// VALIDATION ENGINE
// XAU_AI_PRO v1.2.9
// MULTI SYMBOL
//==================================================

bool ValidateTrade(
   string symbol,
   const int signal
)
{
   if(symbol=="")
   {
      if(ValidationLogAllowed(symbol, "EMPTY SYMBOL"))
         Print("[VALIDATION] BLOCK | Empty symbol");
      return false;
   }

   if(signal==0)
   {
      if(ValidationLogAllowed(symbol, "SIGNAL 0"))
      Print(
         "[VALIDATION] BLOCK | Signal=0 | ",
         symbol
      );

      return false;
   }


   //================================================
   // SPREAD
   //================================================

   if(EnableSpreadFilter)
   {
      double ask=
         SymbolInfoDouble(
            symbol,
            SYMBOL_ASK
         );

      double bid=
         SymbolInfoDouble(
            symbol,
            SYMBOL_BID
         );

      double point=
         SymbolInfoDouble(
            symbol,
            SYMBOL_POINT
         );

      if(
         ask<=0.0 ||
         bid<=0.0 ||
         point<=0.0
      )
      {
         if(ValidationLogAllowed(symbol, "INVALID PRICE"))
         Print(
            "[VALIDATION] BLOCK | Invalid price | ",
            symbol
         );

         return false;
      }

      double maxAllowed = GetMaxSpread(symbol);

      double spread=
         (ask-bid)/
         point;

      // P2.01 (03/11/2026): a linha de CONTEXTO do spread (spread lido vs
      // maximo permitido) saia 1x/5 min por INSTANCIA, ou seja 15 linhas por
      // 5 minutos a dizer a mesma leitura. Passa a 1x/hora por CONTA e por
      // simbolo. O veto real ("[VALIDATION] BLOCK | SPREAD") nao e tocado.
      if(ValidationLogAllowed(symbol, "SPREAD INFO") &&
         AccountLogGatePodeImprimir("val_spread_" + symbol, 3600))
      Print(
         "[VALIDATION] ",
         symbol,
         " | Spread=",
         DoubleToString(
            spread,
            2
         ),
         " | Max=",
         DoubleToString(
            maxAllowed,
            2
         )
      );

      if(
         spread>
         maxAllowed
      )
      {
         if(ValidationLogAllowed(symbol, "SPREAD"))
         Print(
            "[VALIDATION] BLOCK | SPREAD | ",
            symbol
         );

         return false;
      }
   }


   //================================================
   // SESSION
   //================================================

   //================================================
   // HORAS PROIBIDAS (29/10/2026)
   //================================================
   // Veto PROPRIO, independente de EnableSessionFilter. Ate agora o filtro de
   // sessao so agia com EnableSessionFilter=true, que e false por padrao — ou
   // seja, a janela de horas nunca barrava nada. Aqui a lista AvoidHoursList
   // (Config.mqh) fecha as horas 0 e 20 por padrao, com evidencia medida em
   // ai_feedback.csv. Vale so para entradas novas: posicoes abertas seguem
   // geridas por BreakEven/DailyRisk/EquityProtection.
   // v1.2.23 (29/10/2026): a lista passa a ser lida em GMT (ou por classe de
   // ativo) em vez de hora de servidor. Motivo medido: este servidor esta em
   // GMT+2, entao a lista antiga "0,20" bania GMT 22 (fecho de NY, correto) e
   // GMT 18 (MEIO da sessao de NY, errado para majors) - e ainda derivava com
   // o DST do broker. Ver Filters/GlobalScenario.mqh.
   if(IsAvoidedHourGlobal(symbol))
   {
      if(ValidationLogAllowed(symbol, "AVOID HOUR"))
      Print(
         "[VALIDATION] BLOCK | AVOID HOUR | ",
         symbol,
         " | ", AvoidedHourDetail(symbol)
      );

      return false;
   }


   if(EnableSessionFilter)
   {
      if(!IsTradingSession())
      {
         if(ValidationLogAllowed(symbol, "SESSION"))
         Print(
            "[VALIDATION] BLOCK | SESSION | ",
            symbol
         );

         return false;
      }
   }


   //================================================
   // TREND
   //================================================

   if(EnableTrendFilter)
   {
      // v1.2.21 (29/10/2026): GATE ADAPTATIVO.
      //
      // O veto antigo era binario: BUY so acima da EMA200 H1, SELL so abaixo.
      // Em mercado sem tendencia isso veta TODA entrada - medido no journal
      // em 29/10/2026 como "VALIDATION: TREND SELL" (EURUSD) e "VALIDATION:
      // TREND BUY" (USDCHF), as duas unicas do dia.
      //
      // Agora quem decide e o CENARIO (Filters/MarketScenario.mqh):
      //   * tendencia formada (ADX >= ScenarioCounterTrendMaxADX) -> VETA;
      //   * volatilidade alta                                  -> VETA;
      //   * lateral / tendencia fraca                          -> PERMITE,
      //     com lote reduzido por ScenarioLotFactor.
      // Sem leitura de ADX o rigor antigo e mantido.
      string trendWhy = "";

      if(!ScenarioTrendGate(symbol, signal, trendWhy))
      {
         string motivoTrend = (signal == 1) ? "TREND BUY" : "TREND SELL";

         if(ValidationLogAllowed(symbol, motivoTrend))
            Print(
               "[VALIDATION] BLOCK | ",
               motivoTrend,
               " | ",
               symbol,
               " | ",
               trendWhy
            );

         return false;
      }

      // Contra-tendencia autorizada pelo cenario: o journal PRECISA dizer
      // por que, senao a permissao parece falha de filtro. O motivo carrega
      // "OK" de proposito (nao e um veto, nao deve poluir
      // g_validationLastBlock).
      if(StringFind(trendWhy, "contramao PERMITIDA") == 0)
      {
         if(ValidationLogAllowed(symbol, "TREND CONTRA OK"))
            Print(
               "[VALIDATION] TREND CONTRA OK | ",
               symbol,
               " | Signal=",
               signal,
               " | ",
               trendWhy
            );
      }
   }


   //================================================
   // ADX
   //================================================

   if(EnableADXFilter)
   {
      double adx=
         GetADX(
            symbol
         );

      if(ValidationLogAllowed(symbol, "ADX INFO"))
      Print(
         "[VALIDATION] ",
         symbol,
         " | ADX=",
         DoubleToString(
            adx,
            2
         ),
         " | Min=",
         DoubleToString(
            MinimumADX,
            2
         )
      );

      if(
         adx<
         0.0
      )
      {
         // F4/20.15 §3: ADX indisponivel (warm-up/erro) -> neutro, nao bloqueia
         if(ValidationLogAllowed(symbol, "ADX SKIP"))
         Print(
            "[VALIDATION] SKIP | ADX | ",
            symbol,
            " | nao disponivel"
         );
      }
      else
      if(
         adx<
         MinimumADX
      )
      {
         g_adxBlockCount++;

         if(ValidationLogAllowed(symbol, "ADX BLOCK"))
         Print(
            "[VALIDATION] BLOCK | ADX | ",
            symbol
         );

         return false;
      }
   }


   //================================================
   // VOLATILITY / MARKET REGIME
   //================================================

   if(EnableVolatilityFilter)
   {
      MarketRegimeType regime = GetMarketRegime(symbol);

      if(!IsGoodMarket(symbol))
      {
         if(ValidationLogAllowed(symbol, "VOLATILITY"))
         Print(
            "[VALIDATION] BLOCK | VOLATILITY/REGIME | ",
            symbol,
            " | Regime=",
            MarketRegimeToString(regime)
         );

         return false;
      }

      if(ValidationLogAllowed(symbol, "REGIME OK"))
      Print(
         "[VALIDATION] REGIME OK | ",
         symbol,
         " | ",
         MarketRegimeToString(regime)
      );
   }


   //================================================
   // AI
   //================================================

   if(EnableAIFilter)
   {
      if(
         !AITradeAllowed(
            symbol
         )
      )
      {
         if(ValidationLogAllowed(symbol, "AI"))
         Print(
            "[VALIDATION] BLOCK | AI | ",
            symbol
         );

         return false;
      }

      if(ValidationLogAllowed(symbol, "AI OK"))
      Print(
         "[VALIDATION] AI OK | ",
         symbol
      );
   }


   //================================================
   // MTF
   //================================================

   if(EnableMTFConfirmation)
   {
      if(
         !MTFApproved(
            signal,
            symbol
         )
      )
      {
         if(ValidationLogAllowed(symbol, "MTF"))
         Print(
            "[VALIDATION] BLOCK | MTF | ",
            symbol
         );

         return false;
      }
   }

   //================================================
   // NEWS (Economic Calendar)
   //================================================

   // v1.2.9 (29/10/2026): o modulo de noticia vale para FILTRAR e para
   // OPERAR. NewsModuleActive() liga com EnableNewsFilter ou com
   // EnableNewsTrading, e o gate passou a ser POR SIMBOLO (a versao sem
   // simbolo consultava sempre o grafico mestre).
   if(NewsModuleActive())
   {
      if(!CanTradeNews(symbol))
      {
         if(ValidationLogAllowed(symbol, "NEWS"))
         Print(
            "[VALIDATION] BLOCK | NEWS | ",
            symbol
         );

         return false;
      }

      if(ValidationLogAllowed(symbol, "NEWS OK"))
      Print(
         "[VALIDATION] NEWS OK | ",
         symbol
      );
   }

   //================================================
   // APPROVED
   //================================================

   if(ValidationLogAllowed(symbol, "APPROVED"))
   Print(
      "[VALIDATION] APPROVED | ",
      symbol,
      " | Signal=",
      signal
   );

   return true;
}


//==================================================
// COMPATIBILITY OVERLOAD
// MANTÉM MÓDULOS ANTIGOS FUNCIONANDO
//==================================================

bool ValidateTrade(
   const int signal
)
{
   return ValidateTrade(
      _Symbol,
      signal
   );
}


#endif
