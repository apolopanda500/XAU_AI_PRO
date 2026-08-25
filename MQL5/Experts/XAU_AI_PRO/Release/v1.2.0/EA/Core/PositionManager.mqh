// XAU_AI_PRO v1.2.0
#ifndef POSITIONMANAGER_MQH
#define POSITIONMANAGER_MQH

#include "../Management/BreakEven.mqh"
#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include <Trade/Trade.mqh>

extern CTrade trade;

//==================================================
// EXISTE POSIÃ‡ÃƒO DO EA
//==================================================

bool HasPosition(string symbol)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);

      if(ticket==0)
         continue;

      if(!PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL)!=symbol)
         continue;

      if(PositionGetInteger(POSITION_MAGIC)!=MagicNumber)
         continue;

      return true;
   }

   return false;
}

//==================================================
// POSIÃ‡ÃƒO NO SÃMBOLO ATUAL
//==================================================

bool HasOpenPosition()
{
   return HasPosition(_Symbol);
}

//==================================================
// CONTAR POSIÃ‡Ã•ES DO EA
//==================================================

int CountPositions()
{
   int total=0;

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);

      if(ticket==0)
         continue;

      if(!PositionSelectByTicket(ticket))
         continue;

      if(PositionGetInteger(POSITION_MAGIC)!=MagicNumber)
         continue;

      total++;
   }

   return total;
}

//==================================================
// PODE ABRIR
//==================================================

bool CanOpenPosition(string symbol)
{
   if(HasPosition(symbol))
      return false;

   if(CountPositions()>=MaxOpenPositions)
      return false;

   return true;
}

//==================================================
// DIREÃ‡ÃƒO
//==================================================

int GetPositionDirection(string symbol)
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

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

      if(type == POSITION_TYPE_BUY)
         return 1;

      if(type == POSITION_TYPE_SELL)
         return -1;
   }

   return 0;
}

//==================================================
// FECHAR POSIÃ‡ÃƒO
//==================================================

bool CloseSymbolPosition(string symbol)
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

//==================================================
// GERENCIAR
//==================================================

//==================================================
// TRAILING STOP ATR
//==================================================

void TrailingStopATR(string symbol, ulong ticket)
{
   if(!EnableTrailingATR)
      return;

   if(!PositionSelectByTicket(ticket))
      return;

   if(PositionGetInteger(POSITION_MAGIC)!=MagicNumber)
      return;

   double openPrice=PositionGetDouble(POSITION_PRICE_OPEN);
   double sl=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   if(point<=0)
      point=_Point;

   // Usar GetATR com sÃ­mbolo (jÃ¡ implementado)
   double atr=GetATR(symbol);

   if(atr<=0)
      atr=BreakEvenTrigger*point;

   double trailDistance=ATRMultiplier*atr;

   // MÃ­nimo de distÃ¢ncia do stop (proteÃ§Ã£o contra stops muito prÃ³ximos)
   // Usa o stop level do broker (em pontos) como distancia minima,
   // com piso de 10 pontos. Evita "Invalid stops" no trailing.
   long stopLevelBroker=SymbolInfoInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double minStopDistance=MathMax((double)stopLevelBroker,10.0)*point;
   if(trailDistance<minStopDistance)
      trailDistance=minStopDistance;

   double currentPrice;
   if(type==POSITION_TYPE_BUY)
      currentPrice=SymbolInfoDouble(symbol,SYMBOL_BID);
   else
      currentPrice=SymbolInfoDouble(symbol,SYMBOL_ASK);

   double newSL;
   if(type==POSITION_TYPE_BUY)
   {
      // SÃ³ trailing se jÃ¡ estiver em lucro
      if(currentPrice-openPrice<trailDistance)
         return;

      newSL=currentPrice-trailDistance;

      // NÃ£o mover SL para baixo
      if(sl>0 && newSL<=sl)
         return;

      // Verificar distÃ¢ncia mÃ­nima do preÃ§o atual
      if(currentPrice-newSL<minStopDistance)
         return;
   }
   else
   {
      // SÃ³ trailing se jÃ¡ estiver em lucro
      if(openPrice-currentPrice<trailDistance)
         return;

      newSL=currentPrice+trailDistance;

      // NÃ£o mover SL para cima
      if(sl>0 && newSL>=sl)
         return;

      // Verificar distÃ¢ncia mÃ­nima do preÃ§o atual
      if(newSL-currentPrice<minStopDistance)
         return;
   }

   // Normalizar SL para o simbolo
   int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   newSL=NormalizeDouble(newSL,digits);

   // v1.2.2-opt: skip se SL alvo == SL atual (apos normalizacao).
   // Evita OrderSend "modify [no changes]" repetido a cada tick.
   if(MathAbs(newSL-sl)<point/2.0)
      return;

   trade.PositionModify(symbol,newSL,tp);
}

//==================================================
// PARTIAL CLOSE
//==================================================

void PartialClose(string symbol, ulong ticket)
{
   if(!EnablePartialClose)
      return;

   if(!PositionSelectByTicket(ticket))
      return;

   if(PositionGetInteger(POSITION_MAGIC)!=MagicNumber)
      return;

   double openPrice=PositionGetDouble(POSITION_PRICE_OPEN);
   double volume=PositionGetDouble(POSITION_VOLUME);
   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   if(point<=0)
      point=_Point;

   double currentPrice;
   if(type==POSITION_TYPE_BUY)
      currentPrice=SymbolInfoDouble(symbol,SYMBOL_BID);
   else
      currentPrice=SymbolInfoDouble(symbol,SYMBOL_ASK);

   double profitPoints=MathAbs(currentPrice-openPrice)/point;

   if(profitPoints<PartialTrigger)
      return;

   double closeVolume=volume*(PartialPercent/100.0);
   double minLot=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);

   if(step<=0)
      step=minLot;

   closeVolume=MathFloor(closeVolume/step)*step;
   closeVolume=MathMax(minLot,closeVolume);

   if(closeVolume<=0)
      return;

   trade.PositionClosePartial(symbol,closeVolume);
}

//==================================================
// GERENCIAR
//==================================================

void ManagePositions()
{
   // Break-even management (iterates all positions internally)
   CheckBreakEven();

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);

      if(ticket==0)
         continue;

      if(!PositionSelectByTicket(ticket))
         continue;

      if(PositionGetInteger(POSITION_MAGIC)!=MagicNumber)
         continue;

      string symbol=PositionGetString(POSITION_SYMBOL);

      TrailingStopATR(symbol,ticket);
      PartialClose(symbol,ticket);
   }
}

#endif

