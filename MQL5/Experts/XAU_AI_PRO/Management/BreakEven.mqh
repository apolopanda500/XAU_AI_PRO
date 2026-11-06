// XAU_AI_PRO v1.2.9
#ifndef BREAKEVEN_MQH
#define BREAKEVEN_MQH

#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include "../Indicators/MarketPulse.mqh"
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

  // v1.2.16 (29/10/2026): R da posicao = distancia entrada -> alvo.
  // O TP e o alvo em R do trade (a sonda mediu TP ~ 1,0 R em todas as
  // posicoes), entao ele serve de escala para gatilho e trava do break even.
  double rDist = 0.0;

  if(currentTP > 0.0)
     rDist = MathAbs(currentTP - openPrice);

  if(rDist <= 0.0 && atr > 0.0)
     rDist = atr;
  double triggerPoints = 0.0;

  if(atr > 0.0)
     triggerPoints = MathMax(BreakEvenTrigger, atr / point);
  else
     triggerPoints = BreakEvenTrigger;

  if(BreakEvenInR && rDist > 0.0)
  {
     double triggerR = rDist * BreakEvenTriggerR / point;

     if(triggerR > triggerPoints)
        triggerPoints = triggerR;
  }

  // v1.2.0 fix: trigger deve ser MAIOR que o offset (SL valido)
  double offsetPoints = GetBreakEvenStopLevel(symbol);

  // v1.2.16: trava proporcional ao R do trade (antes: entrada + 10 pontos,
  // o que devolvia quase todo o movimento a favor em qualquer respiro).
  if(BreakEvenInR && rDist > 0.0)
  {
     double lockR = rDist * BreakEvenLockR / point;

     if(lockR > offsetPoints)
        offsetPoints = lockR;
  }

  //==================================================
  // STOP ARMADO NO LUCRO (29/10/2026)
  //==================================================
  // Posicao que entrou SEM stop espera o preco andar StoplessArmATRMult ATR a
  // favor e SO ENTAO recebe stop. O stop nasce StoplessLockATRMult ATR ALEM
  // da entrada, ou seja JA COM LUCRO TRAVADO: se o preco voltar, fecha no
  // positivo em vez de virar prejuizo.
  if(EnableStoplessEntry && currentSL <= 0.0)
  {
     double arm  = (atr > 0.0) ? (atr * StoplessArmATRMult  / point)
                               : (double)StoplessArmMinPoints;
     double lock = (atr > 0.0) ? (atr * StoplessLockATRMult / point)
                               : (double)StoplessLockMinPoints;

     if(arm < (double)StoplessArmMinPoints)
        arm = (double)StoplessArmMinPoints;

     if(lock < (double)StoplessLockMinPoints)
        lock = (double)StoplessLockMinPoints;

     // REGIME DE DISPARADA (29/10/2026): com volume alto e preco correndo, o
     // retorno e rapido. O stop e armado mais cedo e mais perto da entrada, em
     // vez de esperar StoplessArmATRMult ATR cheios.
     double pulseVol = 0.0;
     double pulseVel = 0.0;

     if(GetMarketPulse(symbol, pulseVol, pulseVel) != PULSE_NORMAL)
     {
        arm  *= PulseFastArmFactor;
        lock *= PulseFastLockFactor;

        if(arm < (double)StoplessArmMinPoints)
           arm = (double)StoplessArmMinPoints;

        if(lock < (double)StoplessLockMinPoints)
           lock = (double)StoplessLockMinPoints;
     }

     if(arm > triggerPoints)
        triggerPoints = arm;

     if(lock > offsetPoints)
        offsetPoints = lock;
  }

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
     newSL = openPrice + offsetPoints * point;

     if(currentSL > 0.0 && newSL <= currentSL)
        continue;
  }
  else
  {
     newSL = openPrice - offsetPoints * point;

     if(currentSL > 0.0 && newSL >= currentSL)
        continue;
  }

  int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
  newSL = NormalizeDouble(newSL, digits);

  // P2.25 (04/11/2026): o break even so validava o SL contra a ENTRADA e contra
  // o SL anterior, nunca contra o PRECO ATUAL. Medido no journal do run
  // 7704472817938539810 (04/11/2026 14:02): tres PositionModify no mesmo
  // segundo no #407 AUDUSD SELL, todos com sl/tp iguais ao que a posicao ja
  // tinha e todos rejeitados com [Invalid stops]. Duas causas independentes:
  // (1) a comparacao era feita com o newSL ainda por normalizar, por isso um
  //     desvio de menos de um ponto deixava passar o reenvio do MESMO SL;
  // (2) nada garantia que o SL ficava fora da zona morta do broker em relacao
  //     ao preco atual, e o servidor rejeita o pedido inteiro.
  // Agora a trava nunca e enviada para dentro da zona morta: fica onde esta e
  // volta a ser tentada quando o preco se afastar. Nenhuma regra de risco,
  // entrada ou alvo foi tocada - so a validacao do pedido de modificacao.
  double minDistPreco = MathMax((double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL), 10.0) * point;

  bool dentroZonaMorta = false;

  if(type == POSITION_TYPE_BUY && (currentPrice - newSL) < minDistPreco)
     dentroZonaMorta = true;

  if(type == POSITION_TYPE_SELL && (newSL - currentPrice) < minDistPreco)
     dentroZonaMorta = true;

  if(dentroZonaMorta)
     continue;

  // Banda morta POS-normalizacao: nao reenviar o SL que a posicao ja tem.
  if(currentSL > 0.0 && MathAbs(newSL - currentSL) < point * 0.5)
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
