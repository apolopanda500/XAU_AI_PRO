// XAU_AI_PRO v1.2.9
#ifndef TRAILINGSTOP_MQH
#define TRAILINGSTOP_MQH

#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include <Trade/Trade.mqh>

extern CTrade trade;

// Trailing stop por ATR: move o SL na direcao do lucro quando o preco
// avanca ATRMultiplier * ATR alem do preco de abertura.
void CheckTrailingStop()
{
   if(!EnableTrailingATR)
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
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);

      double currentPrice = (type == POSITION_TYPE_BUY)
         ? SymbolInfoDouble(symbol, SYMBOL_BID)
         : SymbolInfoDouble(symbol, SYMBOL_ASK);

      if(currentPrice <= 0.0)
         continue;

      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point <= 0.0)
         point = _Point;

      double atr = GetATR(symbol);
      if(atr <= 0.0)
         continue;

      double trailDistance = ATRMultiplier * atr;
      if(trailDistance <= 0.0)
         continue;

      double newSL = 0.0;
      bool mover = false;

      if(type == POSITION_TYPE_BUY)
      {
         // Lucro suficiente: SL = preco atual - distancia.
         if(currentPrice - openPrice >= trailDistance)
         {
            newSL = currentPrice - trailDistance;
            if(currentSL <= 0.0 || newSL > currentSL)
               mover = true;
         }
      }
      else if(type == POSITION_TYPE_SELL)
      {
         if(openPrice - currentPrice >= trailDistance)
         {
            newSL = currentPrice + trailDistance;
            if(currentSL <= 0.0 || newSL < currentSL)
               mover = true;
         }
      }

      if(!mover)
         continue;

      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      newSL = NormalizeDouble(newSL, digits);

      ResetLastError();
      if(!trade.PositionModify(symbol, newSL, currentTP))
      {
         PrintFormat("[TRAILING] Falha #%I64u | %s | SL %.5f | Erro %d", ticket, symbol, newSL, GetLastError());
      }
      else
      {
         PrintFormat("[TRAILING] Atualizado #%I64u | %s | SL %.5f", ticket, symbol, newSL);
      }
   }
}

#endif
