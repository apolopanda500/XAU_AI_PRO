// XAU_AI_PRO v1.2.0
#ifndef TRENDFILTER_MQH
#define TRENDFILTER_MQH

#include "../Core/Config.mqh"

#define TREND_EMA_PERIOD 200

input ENUM_TIMEFRAMES TrendTF = PERIOD_H1;

int trendEMAHandle = INVALID_HANDLE;

double trendEMABuffer[];

//==================================================
// INIT
//==================================================

bool InitTrendFilter()
{
   if(trendEMAHandle != INVALID_HANDLE)
      IndicatorRelease(trendEMAHandle);

   trendEMAHandle = iMA(
      _Symbol,
      TrendTF,
      TREND_EMA_PERIOD,
      0,
      MODE_EMA,
      PRICE_CLOSE
   );

   if(trendEMAHandle == INVALID_HANDLE)
   {
      Print(
         "[TREND] INIT ERROR | Error=",
         GetLastError()
      );

      return false;
   }

   ArrayResize(trendEMABuffer, 3);
   ArraySetAsSeries(trendEMABuffer, true);

   Print(
      "[TREND] INIT OK | ",
      _Symbol,
      " | TF=",
      EnumToString(TrendTF),
      " | EMA=",
      TREND_EMA_PERIOD
   );

   return true;
}

//==================================================
// GET EMA
//==================================================

bool GetTrendEMA(double &value)
{
   value = 0.0;

   if(trendEMAHandle == INVALID_HANDLE)
      return false;

   if(CopyBuffer(
      trendEMAHandle,
      0,
      0,
      1,
      trendEMABuffer
   ) != 1)
   {
      return false;
   }

   value = trendEMABuffer[0];

   return (value > 0.0);
}

//==================================================
// MULTI SYMBOL
//==================================================

bool GetTrendEMA(
   double &value,
   string symbol
)
{
   value = 0.0;

   if(symbol == "" || symbol == _Symbol)
      return GetTrendEMA(value);

   if(!SymbolSelect(symbol, true))
      return false;

   int handle = iMA(
      symbol,
      TrendTF,
      TREND_EMA_PERIOD,
      0,
      MODE_EMA,
      PRICE_CLOSE
   );

   if(handle == INVALID_HANDLE)
      return false;

   double buffer[];

   ArraySetAsSeries(buffer, true);

   bool ok = false;

   if(CopyBuffer(
      handle,
      0,
      0,
      1,
      buffer
   ) == 1)
   {
      value = buffer[0];
      ok = (value > 0.0);
   }

   IndicatorRelease(handle);

   return ok;
}

//==================================================
// BUY
//==================================================

bool TrendBuy(string symbol = "")
{
   if(symbol == "")
      symbol = _Symbol;

   double ema = 0.0;

   if(!GetTrendEMA(ema, symbol))
      return false;

   double bid = SymbolInfoDouble(
      symbol,
      SYMBOL_BID
   );

   if(bid <= 0.0)
      return false;

   return (bid > ema);
}

//==================================================
// SELL
//==================================================

bool TrendSell(string symbol = "")
{
   if(symbol == "")
      symbol = _Symbol;

   double ema = 0.0;

   if(!GetTrendEMA(ema, symbol))
      return false;

   double bid = SymbolInfoDouble(
      symbol,
      SYMBOL_BID
   );

   if(bid <= 0.0)
      return false;

   return (bid < ema);
}

//==================================================
// SIGNAL
//==================================================

int GetTrendSignal()
{
   if(TrendBuy())
      return 1;

   if(TrendSell())
      return -1;

   return 0;
}

//==================================================
// DISTANCE
//==================================================

double GetTrendDistance()
{
   double ema = 0.0;

   if(!GetTrendEMA(ema))
      return 0.0;

   double bid = SymbolInfoDouble(
      _Symbol,
      SYMBOL_BID
   );

   if(bid <= 0.0)
      return 0.0;

   double point = SymbolInfoDouble(
      _Symbol,
      SYMBOL_POINT
   );

   if(point <= 0.0)
      return 0.0;

   return NormalizeDouble(
      MathAbs(bid - ema) / point,
      2
   );
}

//==================================================
// RELEASE
//==================================================

void ReleaseTrendFilter()
{
   if(trendEMAHandle != INVALID_HANDLE)
   {
      IndicatorRelease(trendEMAHandle);
      trendEMAHandle = INVALID_HANDLE;
   }

   ArrayFree(trendEMABuffer);
}

#endif