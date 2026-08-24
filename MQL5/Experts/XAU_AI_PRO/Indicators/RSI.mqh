// XAU_AI_PRO v1.2.0
#ifndef RSI_MQH
#define RSI_MQH

#include "../Core/Config.mqh"

//==================================================
// RSI
//==================================================

int rsiHandle = INVALID_HANDLE;

//==================================================
// INIT
//==================================================

bool InitRSI()
{
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);

   rsiHandle = iRSI(
      _Symbol,
      PERIOD_CURRENT,
      RSIPeriod,
      PRICE_CLOSE
   );

   if(rsiHandle == INVALID_HANDLE)
   {
      Print(
         "[RSI] INIT ERROR | Error=",
         GetLastError()
      );

      return false;
   }

   Print(
      "[RSI] INIT OK | Period=",
      RSIPeriod
   );

   return true;
}

//==================================================
// GET RSI
//==================================================

double GetRSI()
{
   if(rsiHandle == INVALID_HANDLE)
      return 0.0;

   double buffer[];

   ArraySetAsSeries(buffer, true);

   ResetLastError();

   if(CopyBuffer(
      rsiHandle,
      0,
      0,
      1,
      buffer
   ) != 1)
   {
      return 0.0;
   }

   if(buffer[0] <= 0.0 || buffer[0] >= 100.0)
      return 0.0;

   return buffer[0];
}

//==================================================
// MULTI SYMBOL
//==================================================

double GetRSI(string symbol)
{
   if(symbol == "" || symbol == _Symbol)
      return GetRSI();

   if(!SymbolSelect(symbol, true))
      return 0.0;

   int handle = iRSI(
      symbol,
      PERIOD_CURRENT,
      RSIPeriod,
      PRICE_CLOSE
   );

   if(handle == INVALID_HANDLE)
      return 0.0;

   double buffer[];

   ArraySetAsSeries(buffer, true);

   double result = 0.0;

   if(CopyBuffer(
      handle,
      0,
      0,
      1,
      buffer
   ) == 1)
   {
      result = buffer[0];
   }

   IndicatorRelease(handle);

   return result;
}

//==================================================
// BUY
//==================================================

bool RSI_OK_Buy()
{
   double rsi = GetRSI();

   if(rsi <= 0.0)
      return false;

   return (rsi < 70.0);
}

//==================================================
// BUY MULTI SYMBOL
//==================================================

bool RSI_OK_Buy(string symbol)
{
   double rsi = GetRSI(symbol);

   if(rsi <= 0.0)
      return false;

   return (rsi < 70.0);
}

//==================================================
// SELL
//==================================================

bool RSI_OK_Sell()
{
   double rsi = GetRSI();

   if(rsi <= 0.0)
      return false;

   return (rsi > 30.0);
}

//==================================================
// SELL MULTI SYMBOL
//==================================================

bool RSI_OK_Sell(string symbol)
{
   double rsi = GetRSI(symbol);

   if(rsi <= 0.0)
      return false;

   return (rsi > 30.0);
}

//==================================================
// RELEASE
//==================================================

void ReleaseRSI()
{
   if(rsiHandle != INVALID_HANDLE)
   {
      IndicatorRelease(rsiHandle);
      rsiHandle = INVALID_HANDLE;
   }
}

#endif