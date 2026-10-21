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

   // Normalizar SL para o sÃ­mbolo
   int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   newSL=NormalizeDouble(newSL,digits);

   trade.PositionModify(symbol,newSL,tp);
}

//==================================================
// PARTIAL CLOSE
//==================================================

//==================================================
// GATILHO DO PARCIAL, EM ATR OU EM PONTOS
//==================================================
// MEDIDO 05/10/2026: `PartialTrigger` era sempre em PONTOS. Com 150, a
// mesma configuracao e 0,17% no BTCUSD (86.439) e 1,5% no EURUSD (1,125).
// O numero e o mesmo; o significado nao. E a mesma armadilha do
// `XAUUSD`/`GOLD`.
//
// Em ATR, 1,0 significa "o preco percorreu uma unidade de volatilidade a
// favor" — que e o mesmo evento em metais, forex e cripto.

double PartialTriggerDistancia(string symbol, double point, double atr)
{
   if(!PartialTriggerInATR)
      return((double)PartialTrigger * point);

   if(atr<=0.0)
      return((double)PartialTrigger * point);

   return(atr * PartialTriggerATRMult);
}

//==================================================
// TP QUE SO APROXIMA (05/10/2026)
//==================================================
// MEDIDO: o SL se movia, o parcial fechava, mas o TP NUNCA se mexia. O alvo
// ficava no numero original enquanto o preco ia e voltava.
//
// POR QUE SO APROXIMA, E NAO PERSEGUE
// ------------------------------------
// Se o TP perseguisse o preco como o SL, uma oscilacao contra moveria os DOIS
// para baixo e o alvo que estava quase alcancado se afastaria junto. Com
// "so aproxima", um degrau ja alcancado NUNCA recua: um alvo que recua deixa
// de ser alvo.
//
// O DEGRAU E O ATR MULTIPLICADO
// -------------------------------
// A escala e ATR pelo mesmo motivo do parcial: um passo fixo em pontos e
// colado em um ativo e inteligente em outro.

void ApproxTakeProfit(string symbol, ulong ticket)
{
   if(!EnableDynamicTP)
      return;

   if(!PositionSelectByTicket(ticket))
      return;

   if(PositionGetInteger(POSITION_MAGIC)!=MagicNumber)
      return;

   double sl=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   double openPrice=PositionGetDouble(POSITION_PRICE_OPEN);
   double volume=PositionGetDouble(POSITION_VOLUME);

   // Sem TP, ou com volume minimo (contas micro nao aceitam modify de 0,001
   // com TP), nao ha o que aproximar.
   if(tp<=0.0 || volume<=0.0)
      return;

   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   if(point<=0)
      point=_Point;

   int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);

   double currentPrice;
   if(type==POSITION_TYPE_BUY)
      currentPrice=SymbolInfoDouble(symbol,SYMBOL_BID);
   else
      currentPrice=SymbolInfoDouble(symbol,SYMBOL_ASK);

   double atr=GetATR(symbol);
   if(atr<=0)
      return;

   double degrau=atr*TPAproxStepATRMult;

   double novoTP;
   if(type==POSITION_TYPE_BUY)
     {
      // Em BUY o TP so desce (fica mais proximo do preco, que subiu).
      novoTP=currentPrice-degrau;

      // JA ALCANCADO: nunca piora o TP. E o que garante a monotonicidade.
      if(tp<=novoTP)
         return;
     }
   else
     {
      // Em SELL o TP so sobe.
      novoTP=currentPrice+degrau;

      if(tp>=novoTP)
         return;
     }

   // O TP nao pode atravessar o preco: um TP do lado errado fecha a posicao na
   // hora, que e o oposto de segurar o alvo.
   if(type==POSITION_TYPE_BUY && novoTP>=currentPrice)
      return;

   if(type==POSITION_TYPE_SELL && novoTP<=currentPrice)
      return;

   // Teto: nao passa da fracao do caminho original autorizada. 1.0 = pode
   // chegar no alvo original, e nunca alem dele.
   if(TPAproxMaxFraction>0.0)
     {
      double teto=openPrice+(tp-openPrice)*TPAproxMaxFraction;
      if(type==POSITION_TYPE_BUY && novoTP<teto)
         novoTP=teto;

      if(type==POSITION_TYPE_SELL && novoTP>teto)
         novoTP=teto;
     }

   // Nunca encostar no SL: TP e SL trocados de lado fecham a posicao na hora.
   if(sl>0.0)
     {
      if(type==POSITION_TYPE_BUY && novoTP<=sl)
         return;

      if(type==POSITION_TYPE_SELL && novoTP>=sl)
         return;
     }

   // Stop level do broker: modification fora da faixa minima e rejeitada.
   long stopLevelBroker=SymbolInfoInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double minStopDistance=MathMax((double)stopLevelBroker,10.0)*point;
   if(type==POSITION_TYPE_BUY && (currentPrice-novoTP)<minStopDistance)
      return;

   if(type==POSITION_TYPE_SELL && (novoTP-currentPrice)<minStopDistance)
      return;

   novoTP=NormalizeDouble(novoTP,digits);
   if(MathAbs(novoTP-tp)<point)
      return;

   trade.PositionModify(symbol,sl,novoTP);
}

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

   // O gatilho segue a ESCALA escolhida: ATR por padrao, pontos quando
   // `PartialTriggerInATR` e falso.
   double triggerDistancia=PartialTriggerDistancia(symbol,point,GetATR(symbol));

   if(MathAbs(currentPrice-openPrice)<triggerDistancia)
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

      // O TP ANTES do parcial: se o parcial fecha parte da posicao, o TP
      // restante precisa ser ajustado sobre a posicao que sobrou, e o preco
      // pode ja ter saido da zona do alvo antigo.
      ApproxTakeProfit(symbol,ticket);
      TrailingStopATR(symbol,ticket);
      PartialClose(symbol,ticket);
   }
}

#endif

