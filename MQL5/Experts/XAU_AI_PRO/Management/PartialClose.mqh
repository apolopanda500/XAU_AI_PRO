// XAU_AI_PRO v1.2.9
#ifndef PARTIALCLOSE_MQH
#define PARTIALCLOSE_MQH

#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include "../Management/BreakEven.mqh"
#include <Trade/Trade.mqh>

extern CTrade trade;

void CheckPartialClose()
{
   if(!EnablePartialClose)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      long type = PositionGetInteger(POSITION_TYPE);

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double volume = PositionGetDouble(POSITION_VOLUME);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);

      double currentPrice = (type == POSITION_TYPE_BUY)
         ? SymbolInfoDouble(symbol, SYMBOL_BID)
         : SymbolInfoDouble(symbol, SYMBOL_ASK);

      if(currentPrice <= 0.0 || volume <= 0.0)
         continue;

      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point <= 0.0)
         point = _Point;

      double profitPoints = (type == POSITION_TYPE_BUY)
         ? (currentPrice - openPrice) / point
         : (openPrice - currentPrice) / point;

      // Trigger em pontos ou em ATR (escala do ativo).
      double trigger = (double)PartialTrigger;
      if(PartialTriggerInATR)
      {
         double atr = GetATR(symbol);
         if(atr > 0.0)
            trigger = PartialTriggerATRMult * atr / point;
      }

      if(profitPoints < trigger)
         continue;

      double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      if(step <= 0.0)
         step = 0.01;
      double toClose = MathFloor(volume * (PartialPercent / 100.0) / step) * step;
      double vmin = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      if(toClose < vmin)
         toClose = vmin;
      if(toClose >= volume)
         toClose = volume - step;
      if(toClose <= 0.0)
         continue;

      ResetLastError();
      if(!trade.PositionClosePartial(ticket, toClose))
      {
         PrintFormat("[PARTIAL] Falha #%I64u | %s | vol %.2f | Erro %d", ticket, symbol, toClose, GetLastError());
         continue;
      }

      // Move SL para break-even apos o parcial.
      double beSL = (type == POSITION_TYPE_BUY)
         ? openPrice + GetBreakEvenStopLevel(symbol) * point
         : openPrice - GetBreakEvenStopLevel(symbol) * point;
      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      beSL = NormalizeDouble(beSL, digits);
      trade.PositionModify(symbol, beSL, currentTP);

      PrintFormat("[PARTIAL] Fechado %.2f de #%I64u | %s | SL -> %.5f", toClose, ticket, symbol, beSL);
   }
}

#endif
