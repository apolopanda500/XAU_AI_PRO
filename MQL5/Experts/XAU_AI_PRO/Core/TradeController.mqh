// XAU_AI_PRO v1.2.0
#ifndef TRADECONTROLLER_MQH
#define TRADECONTROLLER_MQH

#include "../Core/Config.mqh"
#include "../Core/PositionManager.mqh"

//==================================================
// TRADE CONTROLLER
//==================================================

datetime LastTradeTime=0;

//==================================================
// PODE OPERAR
//==================================================

bool CanTrade(string symbol)
{
   if(symbol=="")
      return false;

   if(!CanOpenPosition(symbol))
      return false;

   if(TimeCurrent()-LastTradeTime<10)
      return false;

   return true;
}

//==================================================
// REGISTRA NOVA OPERAÇÃO
//==================================================

void RegisterTrade()
{
   LastTradeTime=TimeCurrent();
}

//==================================================
// RESET
//==================================================

void ResetTradeController()
{
   LastTradeTime=0;
}

//==================================================
// TEMPO DESDE ÚLTIMA OPERAÇÃO
//==================================================

int SecondsFromLastTrade()
{
   return (int)(TimeCurrent()-LastTradeTime);
}

//==================================================
// EXISTE TEMPO MÍNIMO
//==================================================

bool TradeCooldownFinished(int seconds)
{
   return SecondsFromLastTrade()>=seconds;
}

#endif