// XAU_AI_PRO v1.2.9
#ifndef SESSIONFILTER_MQH
#define SESSIONFILTER_MQH

#include "../Core/Config.mqh"

//==================================================
// SESSION FILTER
//==================================================

//==================================================
// HORAS PROIBIDAS (29/10/2026)
//==================================================
// `AvoidHoursList` (Core/Config.mqh) e uma lista de horas do SERVIDOR onde
// nenhuma entrada nova e permitida. Formato "0,20". Vazio/"off"/"none" desliga.
// Evidencia em ai_feedback.csv (402 trades): hora 00 -> 39 trades, WR 43,6%,
// -27,87; hora 20 -> 19 trades, WR 21,1%, -31,88. As duas somam 59,75 de
// prejuizo em 14,4% dos trades; o resto rende +79,15 com WR 78,2%.
bool IsAvoidHourListed(
   const int hour,
   string    list = ""
)
{
   string src = (list == "") ? AvoidHoursList : list;

   StringTrimLeft(src);
   StringTrimRight(src);
   StringToLower(src);

   if(src == "" || src == "off" || src == "none")
      return(false);

   string parts[];
   int n = StringSplit(src, StringGetCharacter(",", 0), parts);

   for(int i = 0; i < n; i++)
   {
      string p = parts[i];
      StringTrimLeft(p);
      StringTrimRight(p);

      if(p == "")
         continue;

      int h = (int)StringToInteger(p);

      if(h < 0 || h > 23)
         continue;

      if(h == hour)
         return(true);
   }

   return(false);
}

// Hora ATUAL do servidor comparada com a lista. Independente de
// EnableSessionFilter: a janela TradeStartHour..TradeEndHour e outro controle.
bool IsAvoidedHour()
{
   MqlDateTime tm;
   TimeToStruct(TimeCurrent(), tm);

   return(IsAvoidHourListed(tm.hour));
}

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
      TradeEndHour,
      " | AvoidHours=",
      AvoidHoursList
   );
}

#endif