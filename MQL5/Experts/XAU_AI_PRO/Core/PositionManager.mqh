// XAU_AI_PRO v1.2.9
#ifndef POSITIONMANAGER_MQH
#define POSITIONMANAGER_MQH

#include "../Management/BreakEven.mqh"
#include "../Management/MoneyLadder.mqh"
#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include "../Indicators/MarketPulse.mqh"
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

//==================================================
// POSICAO MANUAL (ou de outro EA) NO MESMO SIMBOLO
//
// CanOpenPosition so contava posicoes com o MagicNumber
// do EA. Uma posicao aberta a mao no mesmo simbolo ficava
// invisivel: o EA somava volume em cima dela e a exposicao
// real do dono dobrava — e o stop de uma nao protege a outra.
// Aqui a posicao "de fora" passa a ser vista.
//==================================================
input bool EnableManualExposureGuard    = true;   // Nao abrir em simbolo com posicao manual aberta
input bool ManualGuardAllowSameDirection = false;  // true = so bloqueia a direcao OPOSTA

int ForeignPositionDirection(string symbol)
{
   if(symbol=="")
      return 0;

   int direcao=0;

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);

      if(ticket==0)
         continue;

      if(!PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL)!=symbol)
         continue;

      if(PositionGetInteger(POSITION_MAGIC)==MagicNumber)
         continue;

      ENUM_POSITION_TYPE tipo=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

      if(tipo==POSITION_TYPE_BUY)
         direcao=1;
      else
         if(tipo==POSITION_TYPE_SELL)
            direcao=-1;
   }

   return direcao;
}

// 0 = sem posicao manual, 1 = posicao manual A FAVOR, -1 = bloqueia
int ManualGuardState(string symbol,int sinal)
{
   if(!EnableManualExposureGuard)
      return 0;

   int direcao=ForeignPositionDirection(symbol);

   if(direcao==0)
      return 0;

   if(ManualGuardAllowSameDirection && sinal!=0)
      return(direcao==sinal ? 1 : -1);

   return -1;   // guarda ligada: qualquer posicao de fora bloqueia
}

bool CanOpenPosition(string symbol)
{
   if(HasPosition(symbol))
      return false;

   // guarda de exposicao manual: posicao de fora no mesmo simbolo
   if(ManualGuardState(symbol,0)<0)
   {
      static datetime g_lastManualGuardPrint=0;
      datetime agoraGuard=TimeCurrent();

      if(agoraGuard-g_lastManualGuardPrint>=60)
      {
         g_lastManualGuardPrint=agoraGuard;

         Print("[POSITION GUARD] ",symbol,
               " | posicao MANUAL aberta no mesmo simbolo | nova entrada recusada",
               " | dir_manual=",IntegerToString(ForeignPositionDirection(symbol)),
               " | desligue EnableManualExposureGuard para ignorar");
      }

      return false;
   }

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

//==================================================
// SEM STOP: VIGIA DE PERDA (29/10/2026)
//==================================================
// Entrada sem stop nao tem limite individual no servidor. Quando
// StoplessEmergencyPoints > 0 este vigia FECHA a posicao a mercado ao atingir
// a perda configurada em pontos. E a unica forma de "stop" sem stop: um SL
// colocado nesse nivel ja nasceria violado. 0 = automatico em R (v1.2.29).
// v1.2.13: 0 passou a significar AUTOMATICO.
// v1.2.29 (30/10/2026): o automatico deixou de ser 3xATR e passou a ser
// `StoplessEmergencyRMult` x 1R, onde 1R = max(ATR x StoplessArmATRMult,
// StoplessArmMinPoints) - a MESMA referencia usada para dimensionar o risco da
// entrada. Motivo medido em ai_feedback.csv (402 trades): a perda media (1,31)
// e 2,4x o ganho medio (0,55) e metade do prejuizo bruto vem de 12 trades. O
// corte antigo em 3xATR equivalia a ~3,75R, ou seja a posicao podia perder
// quase quatro vezes o que foi orcado para ela. 1,5R corta a cauda sem
// estrangular a entrada: o limite novo e SEMPRE menor ou igual ao antigo
// (3xATR com piso 150 pts), portanto esta mudanca so aperta, nunca afrouxa.
double StoplessEmergencyDistance(string symbol, double point)
{
   if(StoplessEmergencyPoints > 0)
      return((double)StoplessEmergencyPoints);

   // v1.2.37 P1.10: em conta REAL o guarda garante que existe teto de perda.
   // StoplessEmergencyRMult=0 continua a desligar o vigia em demo/backtest,
   // mas numa conta real passa a valer o piso do guarda (1,5R por omissao).
   double mult = RealGuardStoplessEmergencyRMult();

   if(mult <= 0.0)
      return(0.0);

   double atr  = GetATR(symbol);
   double umR  = ((atr > 0.0 && point > 0.0) ? (atr * StoplessArmATRMult / point) : 0.0);
   double piso = (double)StoplessArmMinPoints;

   if(umR < piso)
      umR = piso;

   return(umR * mult);
}

void CheckStoplessEmergency()
{
   if(!EnableStoplessEntry)
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

      if(PositionGetDouble(POSITION_SL) > 0.0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      long   type   = PositionGetInteger(POSITION_TYPE);
      double open   = PositionGetDouble(POSITION_PRICE_OPEN);
      double point  = SymbolInfoDouble(symbol, SYMBOL_POINT);

      if(point <= 0.0)
         point = _Point;

      double price = 0.0;

      if(type == POSITION_TYPE_BUY)
         price = SymbolInfoDouble(symbol, SYMBOL_BID);
      else if(type == POSITION_TYPE_SELL)
         price = SymbolInfoDouble(symbol, SYMBOL_ASK);
      else
         continue;

      if(price <= 0.0)
         continue;

      double perda = (type == POSITION_TYPE_BUY)
                     ? (open - price) / point
                     : (price - open) / point;

      double limite = StoplessEmergencyDistance(symbol, point);

      if(limite <= 0.0 || perda < limite)
         continue;

      ResetLastError();

      if(trade.PositionClose(ticket))
         Print("[SEM STOP] VIGIA FECHOU #", ticket, " | ", symbol,
               " | perda ", DoubleToString(perda, 0), " pts >= ",
               DoubleToString(limite, 0),
               ((StoplessEmergencyPoints > 0) ? " (fixo)" : " (auto R)"));
      else
         Print("[SEM STOP] VIGIA FALHOU #", ticket, " | ", symbol,
               " | erro ", GetLastError());
   }
}

//==================================================
// META DIARIA BATIDA -> PROTEGER O QUE ESTA ABERTO (29/10/2026)
//==================================================
// Pedido do dono: "chegando na meta do dia ja pode colocar stop na entrada ou
// acima da entrada". A meta e de lucro FECHADO (LucroRealizadoHojeUSD), mas o
// que esta aberto continua exposto. Esta rotina trava o resultado:
//   BUY  -> SL = entrada + trava   (nunca pior que a entrada)
//   SELL -> SL = entrada - trava   (nunca pior que a entrada)
// A trava e a mesma do stop armado no lucro (ATR, com piso em pontos), e o
// stop level do broker manda: se nao couber, aproxima do preco; se nem a
// entrada couber, espera o proximo tick.
void ProtectPositionsOnDailyTarget()
{
   if(!EnableDailyProfitTarget || !DailyProfitProtectPositions)
      return;

   double metaBase = EnableDailyTargetBalancePct ? DailyTargetEffectiveUsd()
                                                 : DailyProfitTargetUsd;

   if(metaBase <= 0.0)
      return;

   double pct  = MathMin(MathMax(DailyProfitSlowPercent, 0.0), 100.0);
   double meta = metaBase * pct / 100.0;

   if(meta <= 0.0)
      return;

   if(LucroRealizadoHojeUSD() < meta)
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
      double open   = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl     = PositionGetDouble(POSITION_SL);
      double tp     = PositionGetDouble(POSITION_TP);

      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point <= 0.0)
         point = _Point;

      double atr = GetATR(symbol);

      double trava = (atr > 0.0) ? (atr * StoplessLockATRMult / point)
                                 : (double)StoplessLockMinPoints;

      if(trava < (double)StoplessLockMinPoints)
         trava = (double)StoplessLockMinPoints;

      double minDist = MathMax((double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL), 10.0) * point;

      double price = 0.0;

      if(type == POSITION_TYPE_BUY)
         price = SymbolInfoDouble(symbol, SYMBOL_BID);
      else if(type == POSITION_TYPE_SELL)
         price = SymbolInfoDouble(symbol, SYMBOL_ASK);
      else
         continue;

      if(price <= 0.0)
         continue;

      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      double novo = 0.0;

      if(type == POSITION_TYPE_BUY)
      {
         novo = open + trava * point;

         double maxAllowed = price - minDist;
         if(novo > maxAllowed)
            novo = maxAllowed;

         // Nunca pior que a entrada: a meta pedida e "entrada ou acima".
         if(novo < open)
            novo = open;

         if(novo > maxAllowed)
            continue;

         if(sl > 0.0 && novo <= sl)
            continue;
      }
      else
      {
         novo = open - trava * point;

         double minAllowed = price + minDist;
         if(novo < minAllowed)
            novo = minAllowed;

         if(novo > open)
            novo = open;

         if(novo < minAllowed)
            continue;

         if(sl > 0.0 && novo >= sl)
            continue;
      }

      novo = NormalizeDouble(novo, digits);

      ResetLastError();

      if(trade.PositionModify(symbol, novo, tp))
         Print("[META DIA] STOP PROTEGIDO #", ticket, " | ", symbol,
               " | entrada=", DoubleToString(open, digits),
               " | SL=", DoubleToString(novo, digits));
      else
         Print("[META DIA] FALHA AO PROTEGER #", ticket, " | ", symbol,
               " | erro ", GetLastError());
   }
}

//==================================================
// SAIDA RAPIDA EM REGIME DE DISPARADA (29/10/2026)
//==================================================
// Pedido do dono: com volume alto e preco correndo, "se melhor ja fechar a
// posicao" quando o lucro passar de ~10 USD (ou um % do saldo, o que for
// maior). Sem volume, nada acontece aqui: quem cuida e o break-even/trailing.
double PulseQuickProfitTargetUsd()
{
   double alvo = PulseQuickProfitMinUsd;

   if(PulseQuickProfitBalancePct > 0.0)
   {
      double saldo = AccountInfoDouble(ACCOUNT_BALANCE);

      if(saldo > 0.0)
      {
         double porPct = saldo * PulseQuickProfitBalancePct / 100.0;

         if(porPct > alvo)
            alvo = porPct;
      }
   }

   // Teto absoluto: 3% de uma conta grande nao e 'saida rapida'. Com
   // PulseQuickProfitMaxUsd > 0 o alvo nunca passa desse valor.
   if(PulseQuickProfitMaxUsd > 0.0 && alvo > PulseQuickProfitMaxUsd)
      alvo = PulseQuickProfitMaxUsd;

   return(alvo);
}

void PulseQuickExit()
{
   if(!EnableMarketPulse)
      return;

   double alvo = PulseQuickProfitTargetUsd();

   if(alvo <= 0.0)
      alvo = 10.0;

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

      double pulseVol = 0.0;
      double pulseVel = 0.0;
      ENUM_PULSE_REGIME regime = GetMarketPulse(symbol, pulseVol, pulseVel);

      // Mercado normal: sai daqui. A gestao paciente (break-even/trailing)
      // continua sendo a dona da posicao.
      if(regime == PULSE_NORMAL)
         continue;

      double lucro = PositionGetDouble(POSITION_PROFIT)
                   + PositionGetDouble(POSITION_SWAP);

      bool sairNoLucro = (lucro >= alvo);
      // REGRA DO DONO: saida SEMPRE no lucro. O freio de perda exige lucro
      // NEGATIVO, logo nunca fecha posicao no zero ou no positivo.
      bool sairNaPerda = (PulseQuickLossUsd > 0.0 && lucro < 0.0 &&
                          lucro <= -PulseQuickLossUsd);

      if(!sairNoLucro && !sairNaPerda)
         continue;

      ResetLastError();

      if(trade.PositionClose(ticket))
         Print("[SAIDA RAPIDA] FECHOU #", ticket, " | ", symbol,
               " | lucro=", DoubleToString(lucro, 2),
               " | alvo=", DoubleToString(alvo, 2),
               " | motivo=", (sairNoLucro ? "LUCRO" : "FREIO DE PERDA"),
               " | Regime=", PulseRegimeName(regime),
               " | Volume x", DoubleToString(pulseVol, 2));
      else
         Print("[SAIDA RAPIDA] FALHOU #", ticket, " | ", symbol,
               " | erro ", GetLastError());
   }
}

void ManagePositions()
{
   // SEM STOP: vigia de perda a mercado (somente se StoplessEmergencyPoints > 0)
   CheckStoplessEmergency();

   // REGIME DE DISPARADA: fecha no lucro sem esperar o alvo/trailing
   // v1.2.17: com a escada em dinheiro ligada, a saida e decidida por ela
   // (fechamento total no alvo em USD), nao pelo regime de disparada.
   if(!EnableMoneyLadder)
      PulseQuickExit();

   // META DIARIA BATIDA: trava entrada/entrada+trava em tudo que esta aberto
   ProtectPositionsOnDailyTarget();

   // Break-even management (iterates all positions internally)
   // v1.2.17: a escada em dinheiro e a UNICA dona de SL/TP quando ligada.
   // Break-even em R e escada em USD nao podem disputar o mesmo stop.
   if(EnableMoneyLadder)
      CheckMoneyLadder();
   else
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
      if(!EnableMoneyLadder)
         ApproxTakeProfit(symbol,ticket);
      if(!EnableMoneyLadder)
         TrailingStopATR(symbol,ticket);
      // v1.2.17: a escada em dinheiro fecha a posicao INTEIRA no alvo em
      // USD, portanto a parcial de 30% fica desligada quando ela esta ativa.
      if(!EnableMoneyLadder)
         PartialClose(symbol,ticket);
   }
}

#endif

