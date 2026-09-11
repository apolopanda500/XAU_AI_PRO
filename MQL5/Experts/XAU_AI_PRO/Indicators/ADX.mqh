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
// MÉTRICAS ADX (F4/20.15)
// adx_unavailable_count: nº de lecturas en las que el
//   ADX no estaba disponible (warm-up/INVALID_HANDLE/err 4807-4073)
//   -> el consumidor hace SKIP (fail-open).
// adx_valid_count: nº de lecturas con valor ADX válido y > 0.
// Si unavailable_count se mantiene ALTO en operación normal,
// indica un problema persistente del indicador (y el fail-open
// lo estaría enmascarando). Reset en InitADX.
//==================================================

int g_adxUnavailable = 0;
int g_adxValid       = 0;

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

   g_adxUnavailable = 0;
   g_adxValid       = 0;

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
// F4/20.15 §3: retorna -1.0 (sentinel "indisponivel")
// quando o indicador nao esta pronto (INVALID_HANDLE,
// warm-up com poucos dados, CopyBuffer err 4807/4073).
// Consumidores tratam valor negativo como neutro/skip.
//==================================================

double GetADX()
{
   if(adxHandle == INVALID_HANDLE)
   {
      g_adxUnavailable++;
      return -1.0;
   }

   // Warm-up: dados insuficientes para o ADX ficar estable
   if(Bars(_Symbol, PERIOD_CURRENT) < ADXPeriod * 3)
   {
      g_adxUnavailable++;
      return -1.0;
   }

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
      int err = GetLastError();

      // 4807 = indicador aún no inicializado; 4073 = serie no encontrada
      if(err == 4807 || err == 4073)
      {
         g_adxUnavailable++;
         return -1.0;
      }

      Print(
         "[ADX] CopyBuffer failed | Error=",
         err
      );

      return 0.0;
   }

   double value = adxBuffer[0];

   if(value <= 0.0)
      return 0.0;

   g_adxValid++;

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
      g_adxUnavailable++;
      return -1.0;
   }

   // Warm-up: datos insuficientes para el ADX quede estable
   if(Bars(symbol, PERIOD_CURRENT) < ADXPeriod * 3)
   {
      g_adxUnavailable++;
      return -1.0;
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

      g_adxUnavailable++;
      return -1.0;
   }

   double buffer[];

   ArraySetAsSeries(buffer, true);

   ResetLastError();

   int copied = CopyBuffer(
      handle,
      0,
      0,
      1,
      buffer
   );

   double result = 0.0;

   if(copied == 1)
   {
      result = buffer[0];

      if(result > 0.0)
         g_adxValid++;
      else
         g_adxUnavailable++;
   }
   else
   {
      int err = GetLastError();

      if(err == 4807 || err == 4073)
      {
         result = -1.0;
         g_adxUnavailable++;
      }
   }

   IndicatorRelease(handle);

   return result;
}

//==================================================
// FILTER
// F4/20.15 §3: ADX indisponible (negativo) -> fail-open
// (retorna true = neutro, no bloquea). Solo bloquea
// cuando hay un valor valido por debajo del minimo.
//==================================================

bool ADX_OK()
{
   double adx = GetADX();

   if(adx < 0.0)
      return true;

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

   if(adx < 0.0)
      return true;

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
// GETTERS ADX (F4/20.15)
//==================================================

int ADXGetUnavailableCount()
{
   return g_adxUnavailable;
}

int ADXGetValidCount()
{
   return g_adxValid;
}

string ADXMetricsSummary()
{
   return StringFormat(
      "ADX | unavailable=%d | valid=%d",
      g_adxUnavailable,
      g_adxValid
   );
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