// XAU_AI_PRO v1.2.0
#ifndef VALIDATIONENGINE_MQH
#define VALIDATIONENGINE_MQH

#include "../Core/Config.mqh"

#include "../Filters/SpreadFilter.mqh"
#include "../Filters/SessionFilter.mqh"
#include "../Filters/TrendFilter.mqh"
#include "../Filters/MultiTimeframeFilter.mqh"
#include "../Filters/NewsFilter.mqh"
#include "../Filters/MarketRegime.mqh"

#include "../Indicators/ADX.mqh"

#include "../AI/AIEngine.mqh"

// F4/20.15: contador de bloqueos por ADX inválido (valor válido < MinimumADX).
// Complementa a los contadores de ADX.mqh (unavailable/valid). Si block_count
// crece mucho, el filtro ADX está siendo el cuello de botella de validación.
int g_adxBlockCount = 0;


//==================================================
// VALIDATION ENGINE
// XAU_AI_PRO v1.2.0
// MULTI SYMBOL
//==================================================

bool ValidateTrade(
   string symbol,
   const int signal
)
{
   if(symbol=="")
   {
      Print("[VALIDATION] BLOCK | Empty symbol");
      return false;
   }

   if(signal==0)
   {
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

   if(EnableSessionFilter)
   {
      if(!IsTradingSession())
      {
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
      if(
         signal==1 &&
         !TrendBuy(symbol)
      )
      {
         Print(
            "[VALIDATION] BLOCK | TREND BUY | ",
            symbol
         );

         return false;
      }

      if(
         signal==-1 &&
         !TrendSell(symbol)
      )
      {
         Print(
            "[VALIDATION] BLOCK | TREND SELL | ",
            symbol
         );

         return false;
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
         Print(
            "[VALIDATION] BLOCK | VOLATILITY/REGIME | ",
            symbol,
            " | Regime=",
            MarketRegimeToString(regime)
         );

         return false;
      }

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
         Print(
            "[VALIDATION] BLOCK | AI | ",
            symbol
         );

         return false;
      }

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

   if(EnableNewsFilter)
   {
      if(!CanTradeNews())
      {
         Print(
            "[VALIDATION] BLOCK | NEWS | ",
            symbol
         );

         return false;
      }

      Print(
         "[VALIDATION] NEWS OK | ",
         symbol
      );
   }

   //================================================
   // APPROVED
   //================================================

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
