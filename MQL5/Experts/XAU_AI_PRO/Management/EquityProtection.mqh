// XAU_AI_PRO v1.2.9
#ifndef EQUITYPROTECTION_MQH
#define EQUITYPROTECTION_MQH

#include "../Core/Config.mqh"
#include "../Core/PositionManager.mqh"
#include <Trade/Trade.mqh>

extern CTrade trade;

bool EquityProtection(double maxDrawdownPercent = 15.0)
{
double balance = AccountInfoDouble(ACCOUNT_BALANCE);
double equity  = AccountInfoDouble(ACCOUNT_EQUITY);

if(balance <= 0.0)
return false;

double drawdown =
((balance - equity) / balance) * 100.0;

if(drawdown >= maxDrawdownPercent)
{
Print(
"[EQUITY] PROTECTION ATIVADO | DD: ",
DoubleToString(drawdown, 2),
"%"
);


  return false;


}

return true;
}

void EmergencyCloseAll()
{
Print(
"[EQUITY] EMERGENCY CLOSE ALL - Fechando todas as posições"
);

for(int i = PositionsTotal() - 1; i >= 0; i--)
{
ulong ticket = PositionGetTicket(i);


  if(ticket == 0)
     continue;

  if(!PositionSelectByTicket(ticket))
     continue;

  if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
     continue;

  string symbol =
     PositionGetString(POSITION_SYMBOL);

  ResetLastError();

  if(trade.PositionClose(ticket))
  {
     Print(
        "[EQUITY] Posição fechada: ",
        symbol,
        " #",
        ticket
     );
  }
  else
  {
     Print(
        "[EQUITY] Erro ao fechar: ",
        symbol,
        " #",
        ticket,
        " | Error=",
        GetLastError()
     );
  }


}
}

bool CheckEquityProtection()
{
double balance =
AccountInfoDouble(
ACCOUNT_BALANCE
);

double equity =
AccountInfoDouble(
ACCOUNT_EQUITY
);

if(balance <= 0.0)
return true;

double drawdown =
((balance - equity) / balance) * 100.0;

if(drawdown >= MaxDrawdownPercent)
{
Print(
"[EQUITY] DRAWDOWN CRÍTICO: ",
DoubleToString(drawdown, 2),
"%"
);


  EmergencyCloseAll();

  return false;


}

if(drawdown >= MaxDrawdownPercent * 0.8)
{
Print(
"[EQUITY] DRAWDOWN ALTO: ",
DoubleToString(drawdown, 2),
"%"
);

// Q-025 (v1.2.182) - CKillSwitch::ArmarAutomatico estava implementado em
// Core/KillSwitch.mqh:227 e tinha ZERO chamadores: um controlo sem gatilho.
// Passa a ser accionado no primeiro aviso de capital que o EA ja publica
// (0,8 x MaxDrawdownPercent). A partir dai as ENTRADAS ficam bloqueadas ate
// reiniciar o EA e as posicoes do magic passam a ser fechadas por
// CKillSwitch::Verificar(magic,true) no OnTick (XAU_AI_PRO.mq5:1217) e no
// OnTimer (:2207). Dependencia de ordem: Core/KillSwitch.mqh entra em
// XAU_AI_PRO.mq5 antes deste ficheiro.
if(!CKillSwitch::Ativo())
   CKillSwitch::ArmarAutomatico(
      "DRAWDOWN ALTO " +
      DoubleToString(drawdown, 2) + "% >= " +
      DoubleToString(MaxDrawdownPercent * 0.8, 2) + "%"
   );
}

return true;
}

#endif
