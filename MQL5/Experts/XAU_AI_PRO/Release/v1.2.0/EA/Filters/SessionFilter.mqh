// XAU_AI_PRO v1.2.0
#ifndef SESSIONFILTER_MQH
#define SESSIONFILTER_MQH

#include "../Core/Config.mqh"

//==================================================
// SESSION FILTER
//==================================================

bool IsTradingSession()
{
   // Filtro desativado = sessão sempre liberada
   if(!EnableSessionFilter)
      return true;

   MqlDateTime tm;

   TimeToStruct(
      TimeCurrent(),
      tm
   );

   if(tm.hour >= TradeStartHour &&
      tm.hour < TradeEndHour)
   {
      return true;
   }

   return false;
}

//==================================================
// LEGACY COMPATIBILITY
//==================================================

bool IsMarketSession()
{
   return IsTradingSession();
}

//==================================================
// DEBUG
//==================================================

void PrintSessionStatus()
{
   bool open = IsTradingSession();

   Print(
      "[SESSION] ",
      _Symbol,
      " | Status=",
      open ? "OPEN" : "CLOSED",
      " | Filter=",
      EnableSessionFilter ? "ON" : "OFF",
      " | Hours=",
      TradeStartHour,
      "-",
      TradeEndHour
   );
}

#endif