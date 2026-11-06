// XAU_AI_PRO v1.2.53
#ifndef MONEYLADDER_MQH
#define MONEYLADDER_MQH

#include "../Core/Config.mqh"
#include <Trade/Trade.mqh>

extern CTrade trade;

//==================================================
// ESCADA DE SAIDA EM DINHEIRO (29/10/2026)
//==================================================
// Regra pedida pelo operador, medida em DOLARES - nao em pontos e nao em R:
//   1) a posicao entra SEM stop (EnableStoplessEntry ja faz isso);
//   2) quando o lucro flutuante passa de LadderArmUsd, o stop vai para a
//      ENTRADA (zero a zero) para nao virar perda;
//   3) quando passa de LadderLockTriggerUsd, o stop vai para o nivel que
//      deixa LadderLockUsd travados;
//   4) o alvo passa a valer LadderTpUsd em dinheiro e fecha a posicao
//      inteira (sem parcial).
//
// RISCO POR DESENHO: entre a entrada e (2) NAO existe stop. O prejuizo fica
// aberto ate o vigia CheckStoplessEmergency (StoplessEmergencyPoints) agir.
// Quem liga esta escada aceita esse risco.
//
// Dinheiro -> preco usa o valor do tick do simbolo e o VOLUME da posicao: o
// mesmo numero de dolares vale distancias diferentes em 0,01 e em 1,00 lote.

double MoneyToPriceDistance(string symbol, double volume, double usd)
{
   if(volume <= 0.0 || usd <= 0.0)
      return 0.0;

   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);

   if(tickValue <= 0.0)
      tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickSize <= 0.0)
      tickSize = SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(tickValue <= 0.0 || tickSize <= 0.0)
      return 0.0;

   return (usd * tickSize) / (tickValue * volume);
}

// v1.2.16 - DISTANCIA DE RUIDO
// MEDIDO 29/10/2026 no forward test: LadderArmUsd=10 USD armava o stop na
// ENTRADA depois de 2,4 pips no GBPUSD 0,41 lote. O preco volta ao ponto de
// partida em qualquer respiracao e a posicao morria no zero-a-zero (ou no
// spread). O mesmo numero em USD e uma distancia minuscula em lote grande e
// enorme em lote 0,01: USD sozinho nao serve como gatilho.
// Esta funcao devolve a MENOR distancia em preco que nao e ruido: o maior
// entre ATR*StoplessArmATRMult, o piso StoplessArmMinPoints, o stops level do
// broker e 2x o spread.
double LadderNoiseDistance(string symbol)
{
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(point <= 0.0)
      point = _Point;

   double dist = 0.0;
   double atr  = GetATR(symbol);

   if(atr > 0.0)
      dist = atr * StoplessArmATRMult;

   double piso = (double)StoplessArmMinPoints * point;

   if(dist < piso)
      dist = piso;

   double stopsLevel = (double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;

   if(dist < stopsLevel)
      dist = stopsLevel;

   double spread = SymbolInfoDouble(symbol, SYMBOL_ASK) - SymbolInfoDouble(symbol, SYMBOL_BID);

   if(dist < spread * 2.0)
      dist = spread * 2.0;

   return(dist);
}

// Quanto essa distancia vale em USD para o lote da posicao. E o inverso de
// MoneyToPriceDistance: um gatilho em USD nunca pode valer menos que a
// distancia de ruido do simbolo.
double LadderDistanceToUsd(string symbol, double volume, double dist)
{
   if(dist <= 0.0 || volume <= 0.0)
      return(0.0);

   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);

   if(tickValue <= 0.0)
      tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickSize <= 0.0)
      tickSize = SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(tickValue <= 0.0 || tickSize <= 0.0)
      return(0.0);

   return (dist / tickSize) * tickValue * volume;
}

void CheckMoneyLadder()
{
   if(!EnableMoneyLadder)
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
      long   type   = PositionGetInteger(POSITION_TYPE);

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSl     = PositionGetDouble(POSITION_SL);
      double curTp     = PositionGetDouble(POSITION_TP);
      double volume    = PositionGetDouble(POSITION_VOLUME);
      double profit    = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

      if(openPrice <= 0.0 || volume <= 0.0)
         continue;

      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

      if(point <= 0.0)
         point = _Point;

      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);

      if(ask <= 0.0 || bid <= 0.0)
         continue;

      double currentPrice = (type == POSITION_TYPE_BUY) ? bid : ask;

      // distancia minima pratica: stops level do broker, freeze level e o
      // dobro do spread (evita "invalid stops" e alvo dentro do spread)
      double minDist = MathMax((double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL),
                               (double)SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL)) * point;

      if((ask - bid) * 2.0 > minDist)
         minDist = (ask - bid) * 2.0;

      if(minDist <= 0.0)
         minDist = 5.0 * point;

      // v1.2.16 - ALVO EM DINHEIRO EXECUTADO A MERCADO
      // O TP em preco nem sempre e executavel: com lote grande, LadderTpUsd
      // vale menos que o spread e a ordem e recusada ("invalid stops"), ou o
      // preco ja passou dele e a posicao nunca fecha. Aqui o alvo em USD e
      // cumprido fechando a posicao inteira - e uma saida NO LUCRO, a regra
      // do dono.
      if(LadderTpUsd > 0.0 && profit >= LadderTpUsd)
      {
         ResetLastError();

         if(trade.PositionClose(ticket))
         {
            PrintFormat("[LADDER] ALVO EM DINHEIRO #%I64u | %s | lucro %.2f USD >= %.2f | fechada",
                        ticket, symbol, profit, LadderTpUsd);
            continue;
         }

         PrintFormat("[LADDER] Falha ao fechar no alvo #%I64u | %s | lucro %.2f USD | erro %d",
                     ticket, symbol, profit, GetLastError());
      }

      //---------------- ALVO EM DINHEIRO ----------------
      double dTp   = MoneyToPriceDistance(symbol, volume, LadderTpUsd);
      double newTp = curTp;

      if(dTp > 0.0)
      {
         double tpPrice = (type == POSITION_TYPE_BUY) ? (openPrice + dTp) : (openPrice - dTp);
         tpPrice = NormalizeDouble(tpPrice, digits);

         // se o alvo em dinheiro cair dentro do spread/stop level para este
         // lote, ele nao e executavel: mantem o alvo atual em vez de piorar
         if(MathAbs(tpPrice - currentPrice) >= minDist)
            newTp = tpPrice;
      }

      //---------------- STOP EM DINHEIRO ----------------
      double dLock    = MoneyToPriceDistance(symbol, volume, LadderLockUsd);
      double targetSl = curSl;
      bool   wantSl   = false;
      string motivo   = "";

      // v1.2.16 - PISO DE RUIDO NO GATILHO
      // Armava em 10 USD e, no GBPUSD 0,41 lote, isso era 2,4 pips: o stop
      // nascia colado na entrada e morria na primeira respiracao. Agora o
      // gatilho em USD so vale se ele for MAIOR que a distancia de ruido;
      // caso contrario, espera o preco andar de verdade.
      double noiseDist = LadderNoiseDistance(symbol);
      double noiseUsd  = LadderDistanceToUsd(symbol, volume, noiseDist);

      // v1.2.23 - ARMADURA PROPORCIONAL AO RISCO (1R)
      // MEDIDO no backtest XAUUSD M15 20-29/10/2026 (banca 200 USD): com lote
      // pequeno o gatilho fixo de LadderArmUsd (10 USD) nunca era atingido - o
      // melhor trade do periodo fechou em 6,46 USD - e os trades que subiam
      // 2-3 USD devolviam tudo e terminavam em PERDA. Agora a armadura ocorre
      // a 1R, que e exatamente a distancia do stop de emergencia (ATR/pontos/
      // spread convertidos em dinheiro para este lote).
      // A regra do dono fica intacta: o stop so sobe para a ENTRADA ou acima
      // dela, nunca abaixo; e o alvo em LadderTpUsd continua a fechar no lucro.
      // Em lote grande noiseUsd > LadderArmUsd e a armadura espera o preco
      // andar de verdade, como na v1.2.16.
      // v1.2.43 (31/10/2026): a linha seguinte era CODIGO MORTO. Com
      // armUsd = noiseUsd quando noiseUsd > 0, a condicao `noiseUsd > armUsd`
      // nunca podia ser verdadeira. Removida sem mudar comportamento: a
      // armadura continua a ser 1R (v1.2.23) e so cai em LadderArmUsd quando
      // o ruido nao e mensuravel.
      // v1.2.69 (02/11/2026) - P1.55: o gatilho voltou a ser o INPUT DO DONO.
      // MEDIDO pela leitura do codigo da v1.2.68: `armUsd = noiseUsd` quando o
      // ruido era mensuravel, logo LadderArmUsd era codigo morto - configurar
      // 5 USD nao valia nada, a armadura acontecia a 1R (no XAUUSD 0.01 lote o
      // ruido vale ~2,4 USD, no GBPUSD 0.41 lote ~10 USD). O dono pediu o
      // degrau em DINHEIRO e e isso que passa a valer: armUsd = LadderArmUsd.
      // O gatilho apertado NAO consegue criar stop invalido: a armadura so e
      // aplicada se o preco ja estiver a mais de minDist da entrada (stops
      // level, freeze level e 2x spread) - com 5 USD apertado demais para o
      // lote, o stop simplesmente espera o preco andar, como antes.
      // LadderArmUsd <= 0 volta ao comportamento antigo (1R).
      double armUsd = LadderArmUsd;

      if(armUsd <= 0.0)
         armUsd = noiseUsd;

      // A trava tambem nunca nasce dentro do ruido: usa o maior entre o valor
      // em dinheiro e a trava em ATR/pontos (mesma escala da v1.2.13).
      double lockMin = noiseDist * StoplessLockATRMult;
      double lockPiso = (double)StoplessLockMinPoints * SymbolInfoDouble(symbol, SYMBOL_POINT);

      if(lockPiso > 0.0 && lockMin < lockPiso)
         lockMin = lockPiso;

      if(dLock > 0.0 && dLock < lockMin)
         dLock = lockMin;

      bool lockOk = false;

      if(profit >= LadderLockTriggerUsd && dLock > 0.0)
      {
         double lockPrice = (type == POSITION_TYPE_BUY) ? (openPrice + dLock) : (openPrice - dLock);
         lockPrice = NormalizeDouble(lockPrice, digits);

         bool ok = (type == POSITION_TYPE_BUY) ? (lockPrice <= currentPrice - minDist)
                                               : (lockPrice >= currentPrice + minDist);

         if(ok)
         {
            targetSl = lockPrice;
            wantSl   = true;
            motivo   = "STOP TRAVADO";
            lockOk   = true;
         }
      }
      // v1.2.69 (02/11/2026) - P1.55: esta armadura deixou de ser o "else" da
      // trava (ver nota acima). Se a trava for recusada, cai-se aqui.
      if(!lockOk && profit >= armUsd)
         {
            double bePrice = NormalizeDouble(openPrice, digits);

            bool ok = (type == POSITION_TYPE_BUY) ? (bePrice <= currentPrice - minDist)
                                                  : (bePrice >= currentPrice + minDist);

            if(ok)
            {
               targetSl = bePrice;
               wantSl   = true;
               motivo   = "STOP NA ENTRADA";
            }
         }

      //---------------- so melhora, nunca afasta o stop ----------------
      if(wantSl && curSl > 0.0)
      {
         if(type == POSITION_TYPE_BUY && targetSl <= curSl)
            wantSl = false;

         if(type == POSITION_TYPE_SELL && targetSl >= curSl)
            wantSl = false;
      }

      bool tpChanged = (newTp > 0.0 && MathAbs(newTp - curTp) > point * 0.5);

      if(!wantSl && !tpChanged)
         continue;

      double sendSl = wantSl ? targetSl : curSl;
      double sendTp = tpChanged ? newTp : curTp;

      // v1.2.42 (31/10/2026) - P1.17: nao reenviar o que ja esta la.
      // MEDIDO no log do tester de 31/10 (2 970 941 linhas): 54 093 linhas
      // [LADDER] para 269 tickets (201 por ticket) e, em cada ticket, o SL so
      // assumiu DOIS valores - 0,0 e a entrada. Isto e: a escada reenviava
      // PositionModify com o MESMO SL centenas de vezes por posicao, sem
      // falhar nenhuma vez (0 linhas "[LADDER] Falha"). Cada reenvio e um
      // round-trip ao servidor mais uma linha de log, e nada muda no stop.
      // A comparacao usa meia ponta para nao brigar com o arredondamento do
      // broker. A regra de trading fica intacta: se o SL ou o TP mudam de
      // facto, a ordem sai exactamente como antes.
      // v1.2.53 (31/10/2026) - P1.30: o TP em dinheiro e RECALCULADO a cada
      // passagem a partir do alvo em USD e do valor do tick, por isso mudava
      // 1 a 2 pontos de cada vez e o guarda do P1.18 (meia ponta) deixava
      // passar tudo. MEDIDO no ultimo run do backtest, sobre as linhas
      // [LADDER] do proprio journal: 88 287 PositionModify para 444 tickets
      // (198 por ticket, maximo 7 315 num unico ticket). Replicando a mesma
      // sequencia por ticket com banda morta: 2 pontos deixam sobreviver
      // 3 545 linhas (corte 95,98 por cento), 3 pontos 2 252 (97,45) e 5
      // pontos 1 623 (98,16); a partir dai a curva achata. Logo o que se
      // reenviava nao era o alvo a mover-se a serio, era ruido de recalculo.
      // A banda morta passa a ser o minDist que esta funcao ja calcula
      // (stops level, freeze level e 2x spread), ou seja o piso de ruido do
      // proprio simbolo, nunca menos de meia ponta.
      // A regra de saida nao muda: o SL continua a ir para a entrada e para a
      // trava quando o lucro passa dos gatilhos, o alvo em dinheiro continua a
      // fechar a posicao inteira a mercado, e se o SL mudar a ordem sai sempre
      // - o que deixa de existir e o reenvio de TP dentro do ruido.
      double tpTol = MathMax(point * 0.5, minDist);

      bool slSame = (MathAbs(sendSl - curSl) <= point * 0.5);
      bool tpSame = (MathAbs(sendTp - curTp) <= tpTol);

      if(slSame && tpSame)
         continue;

      if(motivo == "")
         motivo = "SO ALVO";

      ResetLastError();

      // ticket, e nao symbol: a conta e hedging e pode haver mais de uma
      // posicao do EA no mesmo simbolo.
      if(!trade.PositionModify(ticket, sendSl, sendTp))
      {
         PrintFormat("[LADDER] Falha #%I64u | %s | lucro %.2f USD | SL %.5f | TP %.5f | erro %d",
                     ticket, symbol, profit, sendSl, sendTp, GetLastError());
         continue;
      }

      PrintFormat("[LADDER] #%I64u | %s | lucro %.2f USD | SL %.5f | TP %.5f | %s",
                  ticket, symbol, profit, sendSl, sendTp, motivo);
   }
}

#endif
