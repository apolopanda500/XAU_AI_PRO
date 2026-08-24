// XAU_AI_PRO v1.2.0
#ifndef SPREADFILTER_MQH
#define SPREADFILTER_MQH

#include "../Core/Config.mqh"

//==================================================
// SPREAD FILTER PRO
// XAU_AI_PRO
//
// Trabalha em POINTS.
// Compatível com Multi-Symbol.
//==================================================

//==================================================
// GET SPREAD - SYMBOL
//==================================================

double GetSpread(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   if(!SymbolSelect(symbol, true))
      return -1.0;

   MqlTick tick;

   if(!SymbolInfoTick(symbol, tick))
   {
      Print(
         "[SPREAD] Falha ao obter tick | ",
         symbol,
         " | Error=",
         GetLastError()
      );

      return -1.0;
   }

   if(tick.ask <= 0.0 || tick.bid <= 0.0)
      return -1.0;

   double point = SymbolInfoDouble(
      symbol,
      SYMBOL_POINT
   );

   if(point <= 0.0)
      return -1.0;

   return (
      (tick.ask - tick.bid) / point
   );
}

//==================================================
// CHECK SPREAD - CURRENT SYMBOL
//==================================================

bool GoodSpread()
{
   return GoodSpread(_Symbol);
}

//==================================================
// CHECK SPREAD - MULTI SYMBOL
//==================================================

bool GoodSpread(string symbol)
{
   if(!EnableSpreadFilter)
      return true;

   if(symbol == "")
      symbol = _Symbol;

   double spread = GetSpread(symbol);

   // Sem tick válido = não pode operar
   if(spread < 0.0)
   {
      Print(
         "[SPREAD BLOCK] Sem tick válido | ",
         symbol
      );

      return false;
   }

   double maxAllowed = GetMaxSpread(symbol);

   if(spread > maxAllowed)
   {
      Print(
         "[SPREAD BLOCK] ",
         symbol,
         " | Current=",
         DoubleToString(spread, 1),
         " | Max=",
         DoubleToString(maxAllowed, 1)
      );

      return false;
   }

   return true;
}

//==================================================
// COMPATIBILITY
//==================================================

bool SpreadOK()
{
   return GoodSpread(_Symbol);
}

bool SpreadOK(string symbol)
{
   return GoodSpread(symbol);
}

//==================================================
// CURRENT SPREAD
//==================================================

double GetCurrentSpread()
{
   return GetSpread(_Symbol);
}

double GetCurrentSpread(string symbol)
{
   return GetSpread(symbol);
}

//==================================================
// DEBUG
//==================================================

void PrintSpreadStatus()
{
   double spread = GetCurrentSpread();
   double maxAllowed = GetMaxSpread(_Symbol);

   if(spread < 0.0)
   {
      Print(
         "[SPREAD] ",
         _Symbol,
         " | INVALID TICK"
      );

      return;
   }

   Print(
      "[SPREAD] ",
      _Symbol,
      " | Current=",
      DoubleToString(spread, 1),
      " points | Max=",
      DoubleToString(maxAllowed, 1),
      " | Status=",
      (spread <= maxAllowed ? "OK" : "BLOCKED")
   );
}

#endif