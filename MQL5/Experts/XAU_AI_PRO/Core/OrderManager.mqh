// XAU_AI_PRO v1.2.0
#ifndef ORDERMANAGER_MQH
#define ORDERMANAGER_MQH

#include <Trade/Trade.mqh>
#include "../Core/Config.mqh"

extern CTrade trade;

//==================================================
// INIT
//==================================================

void InitOrderManager()
{
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(Slippage);
}

//==================================================
// BUY
//==================================================

bool OpenBuy(string symbol,double lot)
{
   if(symbol=="")
      return false;

   if(lot<=0)
      return false;

   double ask=
      SymbolInfoDouble(symbol,SYMBOL_ASK);

   double point=
      SymbolInfoDouble(symbol,SYMBOL_POINT);
   if(point<=0)
      point=_Point;

   double sl=0;
   double tp=0;

   if(StopLossPoints>0)
      sl=NormalizeDouble(
         ask-(StopLossPoints*point),
         (int)SymbolInfoInteger(symbol,SYMBOL_DIGITS)
      );

   if(TakeProfitPoints>0)
      tp=NormalizeDouble(
         ask+(TakeProfitPoints*point),
         (int)SymbolInfoInteger(symbol,SYMBOL_DIGITS)
      );

   bool result=
      trade.Buy(
         lot,
         symbol,
         ask,
         sl,
         tp,
         TradeComment
      );

   if(!result)
   {
      Print(
         "BUY ERROR ",
         symbol,
         " | ",
         trade.ResultRetcode(),
         " | ",
         trade.ResultRetcodeDescription()
      );
   }

   return result;
}

//==================================================
// SELL
//==================================================

bool OpenSell(string symbol,double lot)
{
   if(symbol=="")
      return false;

   if(lot<=0)
      return false;

   double bid=
      SymbolInfoDouble(symbol,SYMBOL_BID);

   double point=
      SymbolInfoDouble(symbol,SYMBOL_POINT);
   if(point<=0)
      point=_Point;

   double sl=0;
   double tp=0;

   if(StopLossPoints>0)
      sl=NormalizeDouble(
         bid+(StopLossPoints*point),
         (int)SymbolInfoInteger(symbol,SYMBOL_DIGITS)
      );

   if(TakeProfitPoints>0)
      tp=NormalizeDouble(
         bid-(TakeProfitPoints*point),
         (int)SymbolInfoInteger(symbol,SYMBOL_DIGITS)
      );

   bool result=
      trade.Sell(
         lot,
         symbol,
         bid,
         sl,
         tp,
         TradeComment
      );

   if(!result)
   {
      Print(
         "SELL ERROR ",
         symbol,
         " | ",
         trade.ResultRetcode(),
         " | ",
         trade.ResultRetcodeDescription()
      );
   }

   return result;
}

//==================================================
// CLOSE POSITION
//==================================================

bool ClosePosition(string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      if(!PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != symbol)
         continue;

      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      return trade.PositionClose(ticket);
   }

   return false;
}

#endif