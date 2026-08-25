// XAU_AI_PRO v1.2.0
#ifndef DECISIONENGINE_MQH
#define DECISIONENGINE_MQH

#include "../Core/Config.mqh"
#include "../Core/SignalCore.mqh"
#include "../Core/ValidationEngine.mqh"

#include "../Indicators/RSI.mqh"
#include "../Indicators/ADX.mqh"

#include <KCI\\KCI_Volatility_Distance.mqh>
#include <KCI\\KCI_Directional_Matrix.mqh>

#include "../AI/AIEngine.mqh"

//==================================================
// DECISION ENGINE
// MULTI SYMBOL
//==================================================

double MarketScore=0.0;


//==================================================
// MARKET SCORE
//==================================================

double CalculateMarketScore(
   int signal,
   string symbol=""
)
{
   if(signal==0)
      return 0.0;


   if(symbol=="")
      symbol=_Symbol;


   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastLogTime = 0;
   datetime logNow = TimeCurrent();
   bool logOnce = (logNow - lastLogTime >= 60);
   if(logOnce)
      lastLogTime = logNow;


   //================================================
   // BASE SCORE
   //================================================

   double score=50.0;


   //================================================
   // EMA TREND STRENGTH
   //================================================

   int emaFastHandle=
      iMA(
         symbol,
         PERIOD_CURRENT,
         FastEMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );


   int emaSlowHandle=
      iMA(
         symbol,
         PERIOD_CURRENT,
         SlowEMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );


   double emaStrength=0.0;


   if(
      emaFastHandle!=INVALID_HANDLE &&
      emaSlowHandle!=INVALID_HANDLE
   )
   {
      double fastBuf[];
      double slowBuf[];


      ArrayResize(
         fastBuf,
         3
      );


      ArrayResize(
         slowBuf,
         3
      );


      ArraySetAsSeries(
         fastBuf,
         true
      );


      ArraySetAsSeries(
         slowBuf,
         true
      );


      int fastCopied=
         CopyBuffer(
            emaFastHandle,
            0,
            0,
            3,
            fastBuf
         );


      int slowCopied=
         CopyBuffer(
            emaSlowHandle,
            0,
            0,
            3,
            slowBuf
         );


      if(
         fastCopied>0 &&
         slowCopied>0
      )
      {
         if(
            signal==1 &&
            fastBuf[0]>slowBuf[0]
         )
         {
            emaStrength=20.0;
         }
         else
         if(
            signal==-1 &&
            fastBuf[0]<slowBuf[0]
         )
         {
            emaStrength=20.0;
         }


         score+=emaStrength;
      }
   }


   //================================================
   // RELEASE EMA HANDLES
   //================================================

   if(
      emaFastHandle!=INVALID_HANDLE
   )
   {
      IndicatorRelease(
         emaFastHandle
      );
   }


       emaFastHandle=INVALID_HANDLE;  # v1.2.1-crashfix: invalidate after release
   if(
      emaSlowHandle!=INVALID_HANDLE
   )
   {
      IndicatorRelease(
         emaSlowHandle
      );
   }


       emaSlowHandle=INVALID_HANDLE;  # v1.2.1-crashfix: invalidate after release
   //================================================
   // RSI QUALITY
   //================================================

   double rsi=
      GetRSI(
         symbol
      );


   double rsiQuality=0.0;


   if(
      rsi>30.0 &&
      rsi<70.0
   )
   {
      rsiQuality=15.0;
   }
   else
   if(
      rsi>20.0 &&
      rsi<80.0
   )
   {
      rsiQuality=10.0;
   }


   score+=rsiQuality;


   //================================================
   // ADX QUALITY
   //================================================

   double adx=
      GetADX(
         symbol
      );


   double adxQuality=0.0;


   if(
      adx>=MinimumADX
   )
   {
      adxQuality=15.0;
   }
   else
   if(
      adx>=MinimumADX*0.8
   )
   {
      adxQuality=10.0;
   }


   score+=adxQuality;

   //================================================
   // KCI DIRECTIONAL QUALITY
   //================================================

   double kci_main=0.0, kdi_plus=0.0, kdi_minus=0.0;
   GetKCIDirectionalMatrix(symbol, PERIOD_CURRENT, kci_main, kdi_plus, kdi_minus, KCI_DX_BasePeriod, KCI_DX_ZScorePeriod, KCI_DX_Sensitivity);

   double kciQuality=0.0;

   if(signal==1 && kdi_plus>kdi_minus && kci_main>KCI_DX_MainThreshold)
   {
      kciQuality=10.0;
   }
   else
   if(signal==-1 && kdi_minus>kdi_plus && kci_main>KCI_DX_MainThreshold)
   {
      kciQuality=10.0;
   }

   score+=kciQuality;


   //================================================
   // KCI VOLATILITY FILTER
   //================================================

   double kci_vd=GetKCIVolatilityDistance(symbol, PERIOD_CURRENT, KCI_VD_Period, 0);

   double kciVolQuality=0.0;

   if(kci_vd>0.0 && kci_vd<=(GetATR(symbol)*0.5))
   {
      kciVolQuality=5.0;
   }

   score+=kciVolQuality;


   //================================================
   // AI CONFIDENCE
   //================================================

   double aiConfidence=
      GetAIConfidence(
         signal,
         symbol
      );


   score+=
      (
         aiConfidence*
         0.50
      );


   //================================================
   // LIMIT SCORE
   //================================================

   if(score>100.0)
      score=100.0;


   if(score<0.0)
      score=0.0;


   MarketScore=
      NormalizeDouble(
         score,
         2
      );


   //================================================
   // LOG (1x por minuto)
   //================================================

   if(logOnce)
      Print(
         "SCORE CALCULATED | Symbol=",
         symbol,
         " | Signal=",
         signal,
         " | EMA=",
         DoubleToString(
            emaStrength,
            2
         ),
         " | RSI=",
         DoubleToString(
            rsiQuality,
            2
         ),
         " | ADX=",
         DoubleToString(
            adxQuality,
            2
         ),
         " | AI=",
         DoubleToString(
            aiConfidence*0.50,
            2
         ),
         " | TOTAL=",
         DoubleToString(
            MarketScore,
            2
         )
      );


   return MarketScore;
}


//==================================================
// ALLOW TRADE
//==================================================

bool AllowTrade(
   int signal,
   string symbol=""
)
{
   if(signal==0)
      return false;


   if(symbol=="")
      symbol=_Symbol;


   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastAllowLog = 0;
   datetime allowNow = TimeCurrent();
   bool allowLogOnce = (allowNow - lastAllowLog >= 60);
   if(allowLogOnce)
      lastAllowLog = allowNow;


   //================================================
   // CORREÃƒÆ’Ã¢â‚¬Â¡ÃƒÆ’Ã†â€™O PRINCIPAL
   //
   // ValidateTrade espera:
   // 1Ãƒâ€šÃ‚Âº = string symbol
   // 2Ãƒâ€šÃ‚Âº = int signal
   //================================================

   if(
      !ValidateTrade(
         symbol,
         signal
      )
   )
   {
      return false;
   }


   //------------------------------------------------
   // ETAPA 11 - NEWS FILTER: integraÃ§Ã£o explÃ­cita
   // ReforÃ§o a capa de noticias no DecisionEngine,
   // NON sÃ³ via ValidateTrade. NÃ£o bloquea a gestÃ£o de
   // posiciones abertas (solo novas entradas).
   //------------------------------------------------

   if(EnableNewsFilter && IsNewsBlocked())
   {
      g_newsBlockReason = GetNewsBlockDetail(symbol);

      if(allowLogOnce)
         Print(
            "DECISION BLOCKED | NEWS | Symbol=",
            symbol,
            " | Signal=",
            signal,
            " | Reason=",
            g_newsBlockReason
         );

      NewsLogBlock();
      return false;
   }

   double score=
      CalculateMarketScore(
         signal,
         symbol
      );


   if(
      score<60.0
   )
   {
      if(allowLogOnce)
         Print(
            "DECISION BLOCKED | Symbol=",
            symbol,
            " | Score=",
            DoubleToString(
               score,
               2
            )
         );

      return false;
   }


   //------------------------------------------------
   // v1.4.0 (Etapa 5): ADVANCED AI - veto final
   // A IA NAO tem autoridade absoluta: pode BLOQUEAR,
   // mas nunca cria sinal. Score ponderado (trend,
   // strength, spread, market, execution).
   //------------------------------------------------

   if(EnableAIFilter && !FinalAIAllow(signal, symbol))
   {
      if(allowLogOnce)
         Print(
            "DECISION BLOCKED | ADV AI | Symbol=",
            symbol,
            " | Signal=",
            signal
         );

      return false;
   }

   return true;
}


//==================================================
// FINAL DECISION
//==================================================

int GetDecision(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;


   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastDecisionLog = 0;
   datetime decisionNow = TimeCurrent();
   bool decisionLogOnce = (decisionNow - lastDecisionLog >= 60);
   if(decisionLogOnce)
      lastDecisionLog = decisionNow;


   int signal=
      GetSignal(
         symbol
      );


   if(signal==0)
   {
      return 0;
   }


   if(
      !AllowTrade(
         signal,
         symbol
      )
   )
   {
      return 0;
   }


   if(decisionLogOnce)
      Print(
         "DECISION APPROVED | Symbol=",
         symbol,
         " | SIGNAL=",
         signal,
         " | SCORE=",
         DoubleToString(
            MarketScore,
            2
         )
      );


   return signal;
}


#endif

