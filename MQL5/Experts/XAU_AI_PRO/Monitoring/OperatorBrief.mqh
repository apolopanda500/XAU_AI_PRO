// XAU_AI_PRO v1.2.19
#ifndef OPERATORBRIEF_MQH
#define OPERATORBRIEF_MQH

#include "../Core/Config.mqh"
#include "../Core/TradePipeline.mqh"
#include "../AI/AIConnector.mqh"

//==================================================
// RESUMO PARA O OPERADOR (29/10/2026)
//==================================================
// PEDIDO DO DONO: "quero entender o que o EA esta fazendo".
//
// O journal do EA provava tudo o que ele decidia, mas espalhado em dezenas de
// linhas tecnicas por minuto. Aqui a informacao e CONDENSADA em duas partes:
//
//   1) uma linha de estado: quem manda no pipeline, quantas posicoes sao do
//      EA e quantas sao manuais, quanto o dia ja rendeu (FECHADO, a mesma
//      medida que a meta usa) contra a meta efetiva, o flutuante da conta e
//      se a IA esta respondendo;
//   2) uma linha por posicao do EA: em que degrau da escada em dinheiro ela
//      esta e quanto vale o alvo em USD.
//
// Este modulo NAO decide nada, NAO envia ordem e NAO modifica SL/TP. Ele so
// le estado. Se a leitura falhar, o resumo sai incompleto e nada mais muda.

// Distancia em dinheiro entre dois precos para o volume informado.
// Mesma matematica de MoneyToPriceDistance (Management/MoneyLadder.mqh), mas
// usada aqui apenas para EXPLICAR o alvo, nunca para decidir.
double BriefUsdBetween(string symbol, double volume, double from, double to)
{
   if(symbol == "" || volume <= 0.0)
      return 0.0;

   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);

   if(tickValue <= 0.0)
      tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickSize <= 0.0)
      tickSize = SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(tickValue <= 0.0 || tickSize <= 0.0)
      return 0.0;

   double ticks = MathAbs(to - from) / tickSize;

   return ticks * tickValue * volume;
}

// Meta do dia em dinheiro: UMA unica fonte de verdade, a mesma que o
// ExecutionEngine (freio de entradas) e o PositionManager (trava das posicoes)
// consomem. Duplicar a conta aqui faria o resumo mentir sobre a meta.
double OperatorBriefDailyTarget()
{
   return DailyTargetEffectiveUsd();
}

void OperatorBriefTick(int tradesToday)
{
   if(!EnableOperatorBrief || OperatorBriefSeconds <= 0)
      return;

   static datetime lastBrief = 0;
   datetime now = TimeCurrent();

   // O primeiro resumo sai assim que o EA inicia; depois, respeita o intervalo.
   if(lastBrief != 0 && (now - lastBrief) < (datetime)OperatorBriefSeconds)
      return;

   lastBrief = now;

   //---------------- CONTAGEM DE POSICOES ----------------
   int    eaPositions     = 0;
   int    manualPositions = 0;
   double eaFloating      = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if(!PositionSelectByTicket(ticket))
         continue;

      if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
      {
         eaPositions++;

         eaFloating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      }
      else
         manualPositions++;
   }

   //---------------- LINHA 1: ESTADO ----------------
   double meta      = OperatorBriefDailyTarget();
   double realizado = LucroRealizadoHojeUSD();      // FECHADO do EA (a meta usa este numero)
   double flutuante = AccountInfoDouble(ACCOUNT_PROFIT);
   double pctMeta   = (meta > 0.0) ? (realizado / meta * 100.0) : 0.0;

   string master = PipelineIsMaster() ? "SIM" : "STANDBY";

   // P1.102: AI_Symbol/AI_Signal sao um slot unico e o pipeline do master
   // percorre 11 simbolos por volta; o [RESUMO] mostrava o estado do ULTIMO
   // visitado, nao do par dono do grafico. MEDIDO a 21:27:55: XAUUSD SELL
   // 76.80% escrito e, 5 s depois, "IA=UNAVAILABLE 0.0%" no resumo.
   string aiSignal="";
   double aiConf=0.0;
   datetime aiWhen=0;
   string ai;

   if(AIStateForSymbol(_Symbol, aiSignal, aiConf, aiWhen))
   {
      ai = aiSignal + " " + DoubleToString(aiConf, 1) + "%";

      // v1.2.167 (P1.131): a idade tem de ser medida com o MESMO relogio que a
      // gravou. AIConnector grava g_aiStateWhen com AIClockRelogio (TimeLocal em
      // producao); comparar aqui com TimeCurrent, que e tempo do servidor e fica
      // parado com o broker em baixo, dava idade errada por +/- 18000 s.
      if(aiWhen > 0 && AIClockRelogio() >= aiWhen)
         ai += " (ha " + IntegerToString((int)(AIClockRelogio() - aiWhen)) + "s)";
   }
   else if(AI_Signal != "")
      ai = AI_Signal + " " + DoubleToString(AI_Confidence, 1) + "%"
           + (AI_Symbol != "" ? " (ultimo " + AI_Symbol + ")" : "");
   else
      ai = "SEM PRECO";

   string ladder = "OFF";

   if(EnableMoneyLadder)
      ladder = "ON arma " + DoubleToString(LadderArmUsd, 2) +
               " / trava " + DoubleToString(LadderLockUsd, 2) +
               " em " + DoubleToString(LadderLockTriggerUsd, 2) +
               " / alvo " + DoubleToString(LadderTpUsd, 2) + " USD";

   PrintFormat(
      "[RESUMO] master=%s | posicoes: %d EA (%+.2f USD) + %d manual | dia fechado: %+.2f de %.2f USD (%.0f%%) | flutuante conta: %+.2f | trades=%d | IA(" + _Symbol + ")=%s | escada=%s",
      master,
      eaPositions,
      eaFloating,
      manualPositions,
      realizado,
      meta,
      pctMeta,
      flutuante,
      tradesToday,
      ai,
      ladder
   );

   //---------------- LINHA 2+: UMA POR POSICAO DO EA ----------------
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
      double volume    = PositionGetDouble(POSITION_VOLUME);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      double floating  = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

      // Em que degrau da escada esta esta posicao AGORA.
      string step = "escada OFF (break-even em R)";

      if(EnableMoneyLadder)
      {
         if(floating >= LadderLockTriggerUsd)
            step = "TRAVADO: " + DoubleToString(LadderLockUsd, 2) + " USD garantidos";
         else
            if(floating >= LadderArmUsd)
               step = "STOP na entrada (risco zero)";
            else
               step = "SEM STOP: arma em " + DoubleToString(LadderArmUsd, 2) + " USD";
      }

      string stopText = (sl > 0.0) ? DoubleToString(sl, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS))
                                   : "sem stop";

      string tpUsd = "-";

      if(tp > 0.0)
         tpUsd = DoubleToString(BriefUsdBetween(symbol, volume, openPrice, tp), 2) + " USD";

      PrintFormat(
         "[RESUMO] #%I64u %s %s %.2f | flutuante %+.2f USD | %s | stop=%s | alvo=%s",
         ticket,
         symbol,
         (type == POSITION_TYPE_BUY ? "BUY" : "SELL"),
         volume,
         floating,
         step,
         stopText,
         tpUsd
      );
   }
}

#endif
