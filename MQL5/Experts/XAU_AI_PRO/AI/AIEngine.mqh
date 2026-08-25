// XAU_AI_PRO v1.2.0
#ifndef AIENGINE_MQH
#define AIENGINE_MQH

#include "../Core/Config.mqh"

#include "../Core/SignalCore.mqh"

#include "../Filters/TrendFilter.mqh"
#include "../Filters/SpreadFilter.mqh"

#include "../Indicators/ATR.mqh"
#include "../Indicators/ADX.mqh"
#include "../Indicators/RSI.mqh"
#include "../Indicators/TrendStrength.mqh"
#include "../Indicators/VolatilityFilter.mqh"

#include "AdaptiveWeights.mqh"
#include "AIConnector.mqh"
#include "AILearningMemory.mqh"

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

bool AITradeAllowed(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

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
   if(LoadAIPrediction(symbol) && AI_Signal!="UNAVAILABLE")
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

   if(atrPoints>200)
      return 70;

   if(atrPoints>100)
      return 65;

   if(atrPoints>50)
      return 60;

   return 55;
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

int GetAIEngineSignal(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   if(!LoadAIPrediction(symbol))
      return 0;

   if(AI_Score<MinAIConfidence)
      return 0;

   if(AI_BuyProbability>AI_SellProbability+10)
      return 1;

   if(AI_SellProbability>AI_BuyProbability+10)
      return -1;

   return 0;
}

//==================================================
// COMBINED SIGNAL
//==================================================

int GetCombinedSignal(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   int tech=GetSignal(symbol);
   int ai=GetAIEngineSignal(symbol);

   if(tech==ai)
      return tech;

   if(tech==0 && ai!=0 && AI_Score>75)
      return ai;

   if(tech!=0 && ai!=0 && tech!=ai)
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

   //------------------------------------------------
   // ETAPA 20.x: GATE DIRECIONAL DA IA
   // Quando AIRequireDirection=true, exige que a
   // predicao (prediction_<SYMBOL>.json) concorde com
   // a direcao do sinal tecnico com probabilidade
   // >= AIMinDirectionProb. SELL vs BUY = veto.
   // UNAVAILABLE/ausencia de JSON = fail-safe (nao
   // bloqueia; o score base prevalece).
   //------------------------------------------------
   if(AIRequireDirection)
   {
      if(LoadAIPrediction(symbol) && AI_Signal != "UNAVAILABLE")
      {
         double dirProb =
            (signal > 0) ? AI_BuyProbability : AI_SellProbability;

         bool aiAgrees =
            (signal > 0 && (AI_Signal == "BUY" || AI_Signal == "STRONG_BUY")) ||
            (signal < 0 && (AI_Signal == "SELL" || AI_Signal == "STRONG_SELL"));

         if(!aiAgrees || dirProb < AIMinDirectionProb)
         {
            PrintFormat(
               "[ADV AI] DIRECTION VETO | Signal=%d | AI=%s | DirProb=%.2f | Min=%.2f | %s",
               signal,
               AI_Signal,
               dirProb,
               AIMinDirectionProb,
               symbol
            );
            EventAIBlock(symbol, "AI_direction_veto");
            return false;
         }
      }
   }

   double score = AdvancedAIScore(signal, symbol);

   PrintFormat(
      "[ADV AI] Score %.2f | Min %.2f | Symbol %s",
      score,
      MinAIConfidence,
      symbol
   );

   return(score >= MinAIConfidence);
}

//==================================================
// FEEDBACK
//==================================================

void LogAIFeedback(string symbol,double profit)
{
   StoreExperience(
   symbol,
   GetAIEngineSignal(symbol),
   AI_Score,
   profit>0
);

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
