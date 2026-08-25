// XAU_AI_PRO v1.2.0
#ifndef BREAKEVEN_MQH
#define BREAKEVEN_MQH

#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include <Trade/Trade.mqh>

extern CTrade trade;

// Retorna o stop level do broker em pontos (fallback: BreakEvenOffset)
double GetBreakEvenStopLevel(string symbol)
{
   long level = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   return (level > 0) ? (double)level : (double)BreakEvenOffset;
}

void CheckBreakEven()
{
if(!EnableBreakEven)
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

  double currentPrice = 0.0;

  if(type == POSITION_TYPE_BUY)
     currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
  else if(type == POSITION_TYPE_SELL)
     currentPrice = SymbolInfoDouble(symbol, SYMBOL_ASK);
  else
     continue;

  if(currentPrice <= 0.0)
     continue;

  double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

  if(point <= 0.0)
     point = _Point;

  double atr = GetATR(symbol);
  double triggerPoints = 0.0;

  if(atr > 0.0)
     triggerPoints = MathMax(BreakEvenTrigger, atr / point);
  else
     triggerPoints = BreakEvenTrigger;

  // v1.2.0 fix: trigger deve ser MAIOR que o offset (SL valido)
  double offsetPoints = GetBreakEvenStopLevel(symbol);
  if(offsetPoints >= triggerPoints)
     triggerPoints = offsetPoints + 1.0;

  if(triggerPoints <= 0.0)
     continue;

  double profitPoints = 0.0;

  if(type == POSITION_TYPE_BUY)
     profitPoints = (currentPrice - openPrice) / point;
  else
     profitPoints = (openPrice - currentPrice) / point;

  if(profitPoints < triggerPoints)
     continue;

  double newSL = 0.0;

  if(type == POSITION_TYPE_BUY)
  {
     newSL = openPrice + GetBreakEvenStopLevel(symbol) * point;

     if(currentSL > 0.0 && newSL <= currentSL)
        continue;
  }
  else
  {
     newSL = openPrice - GetBreakEvenStopLevel(symbol) * point;

     if(currentSL > 0.0 && newSL >= currentSL)
        continue;
  }

  int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
  newSL = NormalizeDouble(newSL, digits);

  // v1.2.2-opt: skip se SL alvo == SL atual (apos normalizacao).
  // Evita OrderSend "modify [no changes]" repetido a cada tick.
  if(MathAbs(newSL-currentSL) < point/2.0)
     continue;

  ResetLastError();

  if(!trade.PositionModify(symbol, newSL, currentTP))
  {
     PrintFormat(
        "[BREAK EVEN] Falha #%I64u | %s | SL %.5f | Erro %d",
        ticket,
        symbol,
        newSL,
        GetLastError()
     );
  }
  else
  {
     PrintFormat(
        "[BREAK EVEN] Ativado #%I64u | %s | SL %.5f | Trigger %.1f",
        ticket,
        symbol,
        newSL,
        triggerPoints
     );
  }


}
}

#endif
