// XAU_AI_PRO v1.2.9
#ifndef AIENGINE_MQH
#define AIENGINE_MQH

#include "../Core/Config.mqh"

#include "../Core/SignalCore.mqh"

#include "../Filters/TrendFilter.mqh"
#include "../Filters/SpreadFilter.mqh"
#include "../Filters/MarketIntelligence.mqh" // v1.3: inteligencia de mercado para ajuste da IA

#include "../Indicators/ATR.mqh"
#include "../Indicators/ADX.mqh"
#include "../Indicators/RSI.mqh"
#include "../Indicators/TrendStrength.mqh"
#include "../Indicators/VolatilityFilter.mqh"

#include "AdaptiveWeights.mqh"
#include "AIConnector.mqh"
#include "AILearningMemory.mqh"
#include "AIMetrics.mqh"

//==================================================
// PROTOTYPES
//==================================================

double GetAIConfidence(int signal,string symbol="");
bool   AITradeAllowed(string symbol="");
int    GetAIEngineSignal(string symbol="");
int    GetCombinedSignal(string symbol="");
double GetAILotMultiplier(double confidence);
double GetAIVetoThreshold(string symbol="");
void   LogAIFeedback(string symbol,double profit);

//==================================================
// AI FILTER
//==================================================

//==================================================
// GATE DE IA
//==================================================
// A IA so PODE barrar entrada quando ela e obrigatoria. Com
// `EnableAutonomousMode=true` (Config.mqh) o gateway ausente deixa de
// bloquear o EA: a IA continua calculando score e registrando feedback,
// mas nao veta e nao exige disponibilidade.
bool AIGateRequired()
{
   if(!EnableAIFilter)
      return(false);

   if(EnableAutonomousMode)
      return(false);

   return(!AllowTradeWithoutAI);
}

bool AITradeAllowed(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   if(!AIGateRequired())
      return(true);

   int signal=GetSignal(symbol);

   if(signal==0)
      return false;

   double confidence=GetAIConfidence(signal,symbol);

   if(confidence<MinAIConfidence)
      return false;

   if(LoadAIPrediction(symbol))
   {
      //------------------------------------------------
      // ETAPA 15.3: sinal UNAVAILABLE = IA indisponivel.
      // NAO confirma e NAO veta; o score base prevalece.
      // Comportamento fail-safe identico a ausencia de JSON.
      //------------------------------------------------
      if(AI_Signal=="UNAVAILABLE")
         return true;

      if(signal==1 && AI_Signal=="SELL")
         return false;

      if(signal==-1 && AI_Signal=="BUY")
         return false;

      double contra=
         (signal==1)?
         AI_SellProbability:
         AI_BuyProbability;

      if(contra>GetAIVetoThreshold(symbol))
         return false;
   }

   return true;
}

//==================================================
// AI CONFIDENCE
//==================================================

double GetAIConfidence(int signal,string symbol="")
{
   if(signal==0)
      return 0;

   if(symbol=="")
      symbol=_Symbol;

   double score=50.0;

   //------------------------------------------------
   // ETAPA 15.3: UNAVAILABLE nao gera bonus de IA;
   // cai no fallback local (trend/RSI/ADX).
   //------------------------------------------------
   // v1.2.162 - P1.125: diz-se se a leitura veio MESMO da IA. O teto do
   // fallback so pode valer quando o numero vem dos indicadores; aplicado
   // tambem com IA real a responder, ele fechava o gate para sempre (ver
   // o bloco abaixo).
   bool aiReal = (LoadAIPrediction(symbol) && AI_Signal!="UNAVAILABLE");

   if(aiReal)
   {
      if(signal==1 && AI_Signal=="BUY")
         score+=20.0;

      if(signal==-1 && AI_Signal=="SELL")
         score+=20.0;

      score+=AI_Score*0.40;

      double prob=
         (signal==1)?
         AI_BuyProbability:
         AI_SellProbability;

      score+=prob*0.30;
   }
   else
   {
      if(signal==1 && TrendBuy(symbol))
         score+=15;

      if(signal==-1 && TrendSell(symbol))
         score+=15;

      double rsi=GetRSI(symbol);

      if(rsi>30 && rsi<70)
         score+=10;

      if(GetADX(symbol)>=MinimumADX)
         score+=10;
   }

   // Fallback NAO e IA. MEDIDO 23/10/2026: sem gateway, o score chegava a 85
   // (50 de base + 15 tendencia + 10 RSI + 10 ADX), o multiplicador de lote ia
   // a 1,00 e o piso de veto (50) passava sem nenhum modelo responder. O
   // numero era de indicador com nome de IA.
   //
   // v1.2.162 - P1.125 CORRIGIDO: MEDIDO 05/11/2026 - o teto era
   // aplicado quando `AIGateRequired()` era VERDADEIRO, ou seja
   // exactamente quando a IA e obrigatoria: 40 < MinAIConfidence 60,
   // logo `AITradeAllowed()` devolvia false SEMPRE - com gateway, sem
   // gateway, com score 95 ou com score 0. O texto do Config.mqh
   // manda capar o fallback, nao a leitura real. Agora o teto vale so
   // quando `aiReal` e falso.
   if(!aiReal)
      score = MathMin(score, AIUnavailableConfidenceCap);

   score *= MemoryBoost(symbol);

   if(score>100)
      score=100;

   if(score<0)
      score=0;

   return NormalizeDouble(score,2);
}

//==================================================
// DYNAMIC VETO
//==================================================

double GetAIVetoThreshold(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   double atr=GetATR(symbol);

   double point=
      SymbolInfoDouble(
         symbol,
         SYMBOL_POINT
      );

   if(point<=0)
      return 60;

   double atrPoints=atr/point;

   double baseThreshold;

   if(atrPoints>200)
      baseThreshold = 70;
   else if(atrPoints>100)
      baseThreshold = 65;
   else if(atrPoints>50)
      baseThreshold = 60;
   else
      baseThreshold = 55;

   //------------------------------------------------
   // v1.3: AJUSTE POR INTELIGÊNCIA DE MERCADO
   // Quando o mercado tem baixa inteligencia (fora de
   // sessao principal, proximo de fechamento, evento
   // de alto impacto), a IA fica MAIS conservadora:
   // abaixa o threshold de veto (mais facil barrar).
   //------------------------------------------------
   double intelScore = GetMarketIntelligenceScore(symbol);

   double intelPenalty = 0.0;
   if(intelScore < 40)      intelPenalty = 15.0; // inteligencia muito baixa
   else if(intelScore < 60) intelPenalty = 8.0;  // inteligencia baixa
   else if(intelScore < 70) intelPenalty = 3.0;  // inteligencia media-baixa

   double finalThreshold = baseThreshold + intelPenalty;

   // Cap em 85 para nunca tornar impossível
   if(finalThreshold > 85) finalThreshold = 85;

   return finalThreshold;
}

//==================================================
// LOT ADJUSTMENT
//==================================================

double GetAILotMultiplier(double confidence)
{
   if(confidence>=90)
      return 1.25;

   if(confidence>=80)
      return 1.00;

   if(confidence>=70)
      return 0.75;

   if(confidence>=60)
      return 0.50;

   return 0.25;
}

//==================================================
// AI SIGNAL
//==================================================

//==================================================
// SINAL DA IA A PARTIR DO `signal` TEXTUAL (05/10/2026)
//==================================================
// MEDIDO: o backend devolve `signal` ("BUY", "SELL", "NEUTRAL",
// "STRONG_BUY"), e `AI_BuyProbability`/`AI_SellProbability` chegam 0.0
// porque o payload canonico usa `prob_buy`/`prob_sell`. Ler as
// probabilidades dava 0 contra 0, a diferenca de 10 pontos nunca era
// atingida, e `GetAIEngineSignal` devolvia SEMPRE 0 — a IA nao decidia
// nada, so vetava.
//
// A funcao abaixo le o texto, que e o que o backend realmente publica.
// `AI_Score<MinAIConfidence` continua barrando: e o mesmo piso do veto,
// e um score alto com sinal BUY e exatamente o caso que deve operar.
int GetAIEngineSignal(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   if(!LoadAIPrediction(symbol))
      return 0;

   if(AI_Score<MinAIConfidence)
      return 0;

   // O TEXTO PRIMEIRO, e so depois as probabilidades.
   //
   // "STRONG_BUY"/"STRONG_SELL" sao os sinais de maior conviccao que o
   // backend emite, e o `AIBuyAllowed`/`AISellAllowed` ja os tratavam
   // (AIConnector.mqh). Aqui o mesmo criterio, no mesmo lugar da decisao.
   if(AI_Signal=="STRONG_BUY")
      return 1;

   if(AI_Signal=="STRONG_SELL")
      return -1;

   if(AI_Signal=="BUY" && AI_BuyProbability>AI_SellProbability)
      return 1;

   if(AI_Signal=="SELL" && AI_SellProbability>AI_BuyProbability)
      return -1;

   // Fallback para as probabilidades: vale quando o sinal vier de um
   // pipeline antigo, que mandava so os numeros.
   if(AI_BuyProbability>AI_SellProbability+10)
      return 1;

   if(AI_SellProbability>AI_BuyProbability+10)
      return -1;

   return 0;
}

//==================================================
// COMBINED SIGNAL
//==================================================

//==================================================
// CONFLITO IA x TECNICO (v1.2.10 - 29/10/2026)
//==================================================
// MEDIDO: `GetCombinedSignal` devolvia 0 sempre que tecnico e IA apontavam
// lados opostos. Com previsao fraca ou desatualizada isso zerava TODA
// entrada: o EA varria os 11 simbolos, logava "No Signal" e nunca chegava
// ao AllowTrade (zero linhas DECISION em 3h de journal). Nao era falta de
// setup tecnico, era o empate.
//
// Politica nova: a IA so cancela a entrada quando esta fresca E confiavel
// (score >= AIConflictMinScore). Fora disso o tecnico prevalece e o evento
// vira `[AI CONFLICT]`, nunca silencio.
bool AIConflictBlocks(int tech,int ai,string symbol="")
{
   if(!EnableAIConflictResolve)
      return(true);   // comportamento antigo: empate = nao operar

   bool iaConfiavel = (!AI_IsStale && AI_Score >= AIConflictMinScore);

   static datetime lastConflictLog = 0;
   datetime conflitoAgora = TimeCurrent();

   if(conflitoAgora - lastConflictLog >= 60)
     {
      lastConflictLog = conflitoAgora;

      PrintFormat("[AI CONFLICT] %s | tech=%d | ai=%d | ai_score=%.2f | stale=%s | decisao=%s | min=%.2f",
                  symbol,
                  tech,
                  ai,
                  AI_Score,
                  (AI_IsStale ? "SIM" : "NAO"),
                  (iaConfiavel ? "IA" : "TECNICO"),
                  AIConflictMinScore);
     }

   return(iaConfiavel);
}

int GetCombinedSignal(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   int tech=GetSignal(symbol);
   int ai=GetAIEngineSignal(symbol);

   // IA COM AUTORIDADE (05/10/2026)
   // =================================
   // Quando `AIHasSignalAuthority` esta ligado, a IA DECIDE — e o que o dono
   // pediu ("a IA pode fazer tudo, operar so quando eu decidir quem opera").
   // O sinal tecnico vira APOIO, e nao dono da decisao.
   //
   // O piso e `AIAuthorityMinScore` e nao `MinAIConfidence`: os dois medem
   // coisas diferentes. O veto e "esta IA ta confiavel?"; assumir a decisao e
   // "esta IA ta confiavel O BASTANTE para falar por mim?". Num numero so,
   // o operador nao consegue explicar por que a ordem saiu.
   if(AIHasSignalAuthority)
     {
      // Sem sinal da IA, NAO HAI FALLBACK TECNICO: e a diferenca entre
      // "operar guiado por IA" e "operar por tecnico com uma IA olhando".
      // Com a autoridade ligada e a IA calada, o certo e NAO operar.
      if(ai!=0)
         return ai;

      return 0;
     }

   if(tech==ai)
      return tech;

   if(tech==0 && ai!=0 && AI_Score>75)
      return ai;

   if(tech!=0 && ai!=0 && tech!=ai && AIConflictBlocks(tech,ai,symbol))
      return 0;

   return tech;
}

//==================================================
// ADVANCED AI SCORE (v1.4.0 - Etapa 5)
//==================================================
// O modulo orfao AI/AdvancedAI.mqh foi fundido aqui.
// Todas as dependencias (TrendFilter, SpreadFilter,
// ADX, TrendStrength, VolatilityFilter, AdaptiveWeights)
// ja estao incluidos neste arquivo.
//
// AdvancedAIScore() gera um score 0-100 ponderado:
//   AI base (GetAIConfidence) x ExecutionWeight
//   Trend (StrongTrend)          x TrendWeight
//   ADX strength                 x StrengthWeight
//   Spread (GoodSpread)          x MarketWeight
//   Volatilidade + bonus direcional
//
// FinalAIAllow() e um VETO: a IA NAO tem autoridade
// absoluta - pode bloquear o trade, mas nunca cria
// sinal. Usado no DecisionEngine (AllowTrade).
//==================================================

double ClampScore(double value)
{
   if(value < 0.0)
      return 0.0;
   if(value > 100.0)
      return 100.0;
   return value;
}

//==================================================

bool StrongTrend(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;
   return(TrendBuy(symbol) || TrendSell(symbol));
}

//==================================================

double AdvancedAIScore(int signal, string symbol="")
{
   if(signal == 0)
      return 0.0;

   if(symbol == "")
      symbol = _Symbol;

   double score = 0.0;

   //------------------------------------------
   // AI BASE
   //------------------------------------------

   score += GetAIConfidence(signal, symbol) * GetExecutionWeight();

   //------------------------------------------
   // TREND
   //------------------------------------------

   if(StrongTrend(symbol))
      score += 100.0 * GetTrendWeight();
   else
      score -= 40.0 * GetTrendWeight();

   //------------------------------------------
   // TREND STRENGTH (ADX)
   //------------------------------------------

   double trend = GetADX(symbol);
   if(trend > 100.0)
      trend = 100.0;
   // F4/20.15 §3: ADX indisponivel (negativo) -> neutro, sem penalizar
   if(trend < 0.0)
      trend = 0.0;
   score += trend * GetStrengthWeight();

   //------------------------------------------
   // SPREAD
   //------------------------------------------

   if(GoodSpread(symbol))
      score += 100.0 * GetMarketWeight();
   else
      score -= 60.0 * GetMarketWeight();

   //------------------------------------------
   // VOLATILITY
   //------------------------------------------

   if(GoodVolatility(30))
      score += 8.0;
   else
      score -= 12.0;

   //------------------------------------------
   // BONUS DIRECIONAL
   //------------------------------------------

   if(signal > 0 && TrendBuy())
      score += 6.0;
   if(signal < 0 && TrendSell())
      score += 6.0;

   score = ClampScore(score);
   return NormalizeDouble(score, 2);
}

//==================================================

bool FinalAIAllow(int signal, string symbol="")
{
   if(signal == 0)
      return false;

   if(symbol == "")
      symbol = _Symbol;

   // Sem IA nao ha veto; e sem veto nao ha entrada. `AllowTradeWithoutAI=true`
   // e o caminho do Strategy Tester, onde o pipeline Python nao roda.
   if(AIGateRequired())
   {
      if(!LoadAIPrediction(symbol) || AI_Signal=="UNAVAILABLE" || AI_Signal=="ERROR")
      {
         static datetime lastNoAI = 0;
         datetime agora = TimeCurrent();

         if(agora - lastNoAI >= 60)
         {
            lastNoAI = agora;
            Print("[ADV AI] BLOQUEADO | IA indisponivel (", AI_Signal, ") | ", symbol);
         }

         return false;
      }
   }

   double score = AdvancedAIScore(signal, symbol);

   // Este log era impresso a CADA tick, por simbolo: 11 simbolos x ~20 ticks/s
   // viravam milhares de linhas por minuto no journal. Throttle de 1/min.
   static datetime lastScoreLog = 0;
   datetime logNow = TimeCurrent();

   if(logNow - lastScoreLog >= 60)
   {
      lastScoreLog = logNow;
      PrintFormat(
         "[ADV AI] Score %.2f | Min %.2f | Symbol %s",
         score,
         MinAIConfidence,
         symbol
      );
   }

   //------------------------------------------------
   // VETO DE SCORE ZERO (29/10/2026)
   //------------------------------------------------
   // `AIGateRequired()` e false com EnableAutonomousMode=true (padrao) e com
   // AllowTradeWithoutAI=true. Nesse caminho a funcao devolvia TRUE logo
   // abaixo, sem olhar o score - foi assim que 67 entradas com score 0
   // passaram (ai_feedback.csv): WR 34,3% e -56,77. Score 0 nao e sinal
   // fraco: e ausencia de leitura (nenhum componente somou). O veto e
   // proprio, vale nos dois modos e nao mexe em posicoes abertas.
   if(BlockZeroAIScore && score <= 0.0)
   {
      static datetime lastZeroScore = 0;
      datetime zeroNow = TimeCurrent();

      if(zeroNow - lastZeroScore >= 60)
      {
         lastZeroScore = zeroNow;
         PrintFormat(
            "[ADV AI] BLOQUEADO | score=%.2f (sem leitura) | %s",
            score,
            symbol
         );
      }

      return(false);
   }

   if(!AIGateRequired())
      return(true);

   return(score >= MinAIConfidence);
}

//==================================================
// FEEDBACK
//==================================================

void LogAIFeedback(string symbol,double profit)
{
   // Uma unica leitura da direcao: alimenta o aprendizado E as metricas.
   const int aiSignal = GetAIEngineSignal(symbol);

   StoreExperience(
   symbol,
   aiSignal,
   AI_Score,
   profit>0
);

   // Metricas de IA (AI/AIMetrics.mqh). Somente observabilidade: nao
   // altera sinal, risco nem execucao. Direcao 0 = IA sem opiniao, fica
   // fora da conta, senao a accuracy ficaria diluida por abstencoes.
   if(aiSignal != 0)
      AIMetricsRegister(aiSignal, profit);

   int file=
      FileOpen(
         "Data\\ai_feedback.csv",
         FILE_READ|
         FILE_WRITE|
         FILE_CSV|
         FILE_SHARE_READ|
         FILE_SHARE_WRITE,
         ','
      );

   if(file==INVALID_HANDLE)
      return;

   FileSeek(file,0,SEEK_END);

   if(FileSize(file)==0)
      FileWrite(file,
         "Time",
         "Symbol",
         "AIScore",
         "BuyProb",
         "SellProb",
         "Profit",
         "Result"
      );

   FileWrite(
      file,
      TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
      symbol,
      AI_Score,
      AI_BuyProbability,
      AI_SellProbability,
      profit,
      (profit>0?"WIN":"LOSS")
   );

   FileClose(file);
}

#endif
