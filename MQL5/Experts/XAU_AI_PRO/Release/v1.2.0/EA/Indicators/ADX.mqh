// XAU_AI_PRO v1.2.0
#ifndef ADX_MQH
#define ADX_MQH

#include "../Core/Config.mqh"

//==================================================
// ADX INDICATOR
// XAU_AI_PRO
//==================================================

int adxHandle = INVALID_HANDLE;
double adxBuffer[];

//==================================================
// INIT
//==================================================

bool InitADX()
{
   if(adxHandle != INVALID_HANDLE)
      IndicatorRelease(adxHandle);

   adxHandle = iADX(
      _Symbol,
      PERIOD_CURRENT,
      ADXPeriod
   );

   if(adxHandle == INVALID_HANDLE)
   {
      Print(
         "[ADX] INIT ERROR | Symbol=",
         _Symbol,
         " | Error=",
         GetLastError()
      );

      return false;
   }

   ArrayResize(adxBuffer, 3);
   ArraySetAsSeries(adxBuffer, true);

   Print(
      "[ADX] INIT OK | Symbol=",
      _Symbol,
      " | Period=",
      ADXPeriod
   );

   return true;
}

//==================================================
// GET CURRENT ADX
//==================================================

double GetADX()
{
   if(adxHandle == INVALID_HANDLE)
      return 0.0;

   ResetLastError();

   int copied = CopyBuffer(
      adxHandle,
      0,
      0,
      1,
      adxBuffer
   );

   if(copied != 1)
   {
      // v1.2.1-crashfix: throttle do log de erro (1x/min). Antes imprimia
      // a cada tick -> saturacao de I/O de log no tester ("CPU travando").
      static datetime lastAdxErrLog = 0;
      datetime nowLog = TimeCurrent();
      if(nowLog - lastAdxErrLog >= 60)
        {
         lastAdxErrLog = nowLog;
         Print(
            "[ADX] CopyBuffer failed | Error=",
            GetLastError()
         );
      }

      return 0.0;
   }

   double value = adxBuffer[0];

   if(value <= 0.0)
      return 0.0;

   return value;
}

//==================================================
// MULTI SYMBOL
//==================================================

double GetADX(string symbol)
{
   if(symbol == "" || symbol == _Symbol)
      return GetADX();

   if(!SymbolSelect(symbol, true))
   {
      Print("[ADX] SymbolSelect failed: ", symbol);
      return 0.0;
   }

   int handle = iADX(
      symbol,
      PERIOD_CURRENT,
      ADXPeriod
   );

   if(handle == INVALID_HANDLE)
   {
      Print(
         "[ADX] Handle error | ",
         symbol,
         " | Error=",
         GetLastError()
      );

      return 0.0;
   }

   double buffer[];

   ArraySetAsSeries(buffer, true);

   int copied = CopyBuffer(
      handle,
      0,
      0,
      1,
      buffer
   );

   double result = 0.0;

   if(copied == 1)
      result = buffer[0];

   IndicatorRelease(handle);

   return result;
}

//==================================================
// FILTER
//==================================================

bool ADX_OK()
{
   double adx = GetADX();

   if(adx <= 0.0)
      return false;

   return (adx >= MinimumADX);
}

//==================================================
// MULTI SYMBOL FILTER
//==================================================

bool ADX_OK(string symbol)
{
   if(symbol == "")
      symbol = _Symbol;

   double adx = GetADX(symbol);

   if(adx <= 0.0)
      return false;

   return (adx >= MinimumADX);
}

//==================================================
// STRENGTH
//==================================================

double GetADXStrength(string symbol = "")
{
   double adx = GetADX(symbol);

   if(adx <= 0.0)
      return 0.0;

   if(adx >= 40.0)
      return 100.0;

   if(adx >= 30.0)
      return 80.0;

   if(adx >= 25.0)
      return 65.0;

   if(adx >= MinimumADX)
      return 50.0;

   if(adx >= MinimumADX * 0.8)
      return 30.0;

   return 0.0;
}

//==================================================
// RELEASE
//==================================================

void ReleaseADX()
{
   if(adxHandle != INVALID_HANDLE)
   {
      IndicatorRelease(adxHandle);
      adxHandle = INVALID_HANDLE;
   }

   ArrayFree(adxBuffer);
}

#endif