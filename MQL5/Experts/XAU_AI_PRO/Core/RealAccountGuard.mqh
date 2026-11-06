// XAU_AI_PRO v1.2.37
#ifndef REALACCOUNTGUARD_MQH
#define REALACCOUNTGUARD_MQH

//==================================================
// REAL ACCOUNT GUARD (P1.10 - v1.2.37, 30/10/2026)
//==================================================
// ESTUDO QUE ORIGINOU ESTE MODULO
// `IsRealAccount` (Core/EnvironmentManager.mqh) existe desde a v1.2.9, mas
// NUNCA era consultado em nenhum outro ficheiro da arvore. Consequencia:
// demo, backtest e conta REAL corriam com o mesmo codigo, os mesmos numeros
// e os mesmos relaxamentos. Numa conta real isso significa que um parametro
// pensado para "estudar em demo" (por exemplo `BlockWhenMinLotExceedsRiskCap
// = false`, que AVISA e abre mesmo quando o lote minimo estoura o teto por
// operacao) viajava intacto para o capital real.
//
// O QUE ESTE MODULO FAZ
// Nada. Em backtest/optimizacao e em demo todas as funcoes devolvem
// exactamente o que os inputs dizem - paridade de backtest preservada ao
// bit. So numa conta REAL (ACCOUNT_TRADE_MODE_REAL, fora do testador) o
// guarda aperta tres regras de SEGURANCA PURA:
//
//   1) lote minimo acima do teto por operacao passa a BLOQUEAR a entrada
//      (`RealGuardBlockMinLotExceedsCap`), em vez de avisar e abrir;
//   2) o vigia do stopless passa a ter teto de perda garantido: se
//      `StoplessEmergencyRMult` estiver a 0 (vigia desligado), em real ele
//      vale `RealGuardStoplessEmergencyRMultFloor` (1,5R); se estiver mais
//      frouxo que o piso, e apertado para o piso;
//   3) no maximo `RealGuardMaxUnarmedPositions` posicoes deste EA, no mesmo
//      simbolo, podem estar SEM stop de corretora ao mesmo tempo (a regra do
//      dono e entrar sem stop e armar depois; varias entradas nuas ao mesmo
//      tempo multiplicam a exposicao sem limite definido).
//
// O que o guarda NAO faz: nao muda direccao, nao muda score, nao muda
// alvos, nao muda o lote para alem do que o teto de risco ja faz, nao fecha
// posicoes. Pode ser desligado com `EnableRealAccountGuard=false`.
//==================================================

//==================================================
// INPUTS
//==================================================

input bool   EnableRealAccountGuard             = true;  // Guarda de conta REAL (demo/backtest intactos)
input bool   RealGuardBlockMinLotExceedsCap     = true;  // REAL: bloqueia se o lote minimo estoura o teto por operacao
input double RealGuardStoplessEmergencyRMultFloor = 1.5; // REAL: piso do teto de perda do stopless, em R
input int    RealGuardMaxUnarmedPositions       = 1;     // REAL: maximo de posicoes sem stop por simbolo (-1 desliga)

//==================================================
// ESTADO
//==================================================

bool RealGuardIsActive()
  {
   if(!EnableRealAccountGuard)
      return(false);

// Paridade: no testador o guarda fica inerte, mesmo que a conta usada
// para o teste reporte ACCOUNT_TRADE_MODE_REAL.
   if(IsTester || IsOptimization)
      return(false);

   return(IsRealAccount);
  }

//==================================================
// REGRA 1 - LOTE MINIMO ACIMA DO TETO
//==================================================
// Devolve o valor que o ExecutionEngine deve usar no `if(...)`.
bool RealGuardBlockOnMinLot()
  {
   if(RealGuardIsActive() && RealGuardBlockMinLotExceedsCap)
      return(true);

   return(BlockWhenMinLotExceedsRiskCap);
  }

//==================================================
// REGRA 2 - TETO DE PERDA DO STOPLESS
//==================================================
// Multiplicador de 1R usado pelo vigia `StoplessEmergencyDistance`.
// Em real nunca devolve 0 (perda sem limite) e nunca fica acima do piso.
double RealGuardStoplessEmergencyRMult()
  {
   double piso = RealGuardStoplessEmergencyRMultFloor;

   if(piso <= 0.0)
      piso = 1.5;

   if(!RealGuardIsActive())
      return(StoplessEmergencyRMult);

   if(StoplessEmergencyRMult <= 0.0)
      return(piso);

   if(StoplessEmergencyRMult > piso)
      return(piso);

   return(StoplessEmergencyRMult);
  }

//==================================================
// REGRA 3 - EXPOSICAO SEM STOP
//==================================================
// Conta apenas posicoes DESTE EA (MagicNumber) no simbolo indicado.
// Posicoes manuais do dono (magic 0) nunca entram nesta conta.
int RealGuardCountUnarmedPositions(string symbol)
  {
   int total = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if(PositionGetInteger(POSITION_MAGIC) != (long)MagicNumber)
         continue;

      if(symbol != "" && PositionGetString(POSITION_SYMBOL) != symbol)
         continue;

      if(PositionGetDouble(POSITION_SL) <= 0.0)
         total++;
     }

   return(total);
  }

// true = a nova entrada deve ser recusada por ja existir exposicao nua
// suficiente neste simbolo.
bool RealGuardUnarmedExposureBlocked(string symbol)
  {
   if(!RealGuardIsActive())
      return(false);

   if(RealGuardMaxUnarmedPositions < 0)
      return(false);

   if(RealGuardMaxUnarmedPositions == 0)
      return(false);

   return(RealGuardCountUnarmedPositions(symbol) >= RealGuardMaxUnarmedPositions);
  }

//==================================================
// BANNER DE ARRANQUE
//==================================================
// Publica no journal, uma vez por arranque, o que o guarda esta mesmo a
// fazer. Numero, nao confianca: o dono ve na primeira linha do dia se a
// conta e real e quais os limites que estao a valer.
void RealGuardLogBanner()
  {
   if(LogInicioDetalhe()) Print("[REAL GUARD] EnableRealAccountGuard=", EnableRealAccountGuard);

   if(!EnableRealAccountGuard)
     {
      Print("[REAL GUARD] DESLIGADO pelo input - nenhum endurecimento");
      return;
     }

   if(IsTester || IsOptimization)
     {
      Print("[REAL GUARD] INERTE no testador (paridade de backtest)");
      return;
     }

   if(!IsRealAccount)
     {
      if(LogInicioDetalhe()) { Print("[REAL GUARD] conta NAO e real (demo/contest) - sem endurecimento"); }
      return;
     }

   Print("[REAL GUARD] CONTA REAL - endurecimento ACTIVO");
   PrintFormat("[REAL GUARD] lote minimo acima do teto: %s (input BlockWhenMinLotExceedsRiskCap=%s)",
               (RealGuardBlockOnMinLot() ? "BLOQUEIA" : "libera"),
               (BlockWhenMinLotExceedsRiskCap ? "true" : "false"));
   PrintFormat("[REAL GUARD] teto de perda do stopless: %.2fR (input StoplessEmergencyRMult=%.2f | piso %.2f)",
               RealGuardStoplessEmergencyRMult(), StoplessEmergencyRMult,
               RealGuardStoplessEmergencyRMultFloor);
   PrintFormat("[REAL GUARD] maximo de posicoes SEM stop por simbolo: %d (-1 = desligado)",
               RealGuardMaxUnarmedPositions);
  }

#endif
// REALACCOUNTGUARD_MQH
