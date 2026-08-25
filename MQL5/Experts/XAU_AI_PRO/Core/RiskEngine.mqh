// XAU_AI_PRO v1.2.0
#ifndef RISKENGINE_MQH
#define RISKENGINE_MQH

#include "../Core/Config.mqh"
#include "../Core/RiskHub.mqh"
#include "../Management/DailyRisk.mqh"

//==================================================
// RISK ENGINE
//==================================================

double CalculateLotByRisk(double riskPercent,int stopPoints)
{
   return CalculateLotByRisk(
      _Symbol,
      riskPercent,
      stopPoints
   );
}

double CalculateLotByRisk(
   string symbol,
   double riskPercent,
   int stopPoints
)
{
   if(symbol=="")
      return 0.01;

   if(stopPoints<=0)
      stopPoints=100;

   double balance=AccountInfoDouble(ACCOUNT_BALANCE);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   
   // Protecao: equity muito baixa
   double minEquityRatio = MinEquityPercent / 100.0;
   if(equity < balance * minEquityRatio)
   {
      Print("RISK: Equity critica (", DoubleToString(equity, 2),
            " < ", DoubleToString(balance * minEquityRatio, 2), "), bloqueando operacoes");
      return 0.0;   // bloqueia nova operacao
   }

   // Verificar stop loss diario
   if(!CheckDailyLossDaily())
   {
      Print("RISK: Limite de perda diaria atingido");
      return 0.0;   // bloqueia nova operacao
   }
   
   // ETAPA 15.5: fonte UNICA de drawdown (RiskHub, vs peak
   // diario persistente). Regra da Etapa 3: nenhum modulo
   // recalcula drawdown por conta propria.
   double drawdown = GetDrawdownPercent();
   
   // Ajustar risco baseado no drawdown (escalonado a partir de MaxDrawdownPercent)
   double adjustedRisk = riskPercent;
   double ddCritical = MaxDrawdownPercent;          // ex.: 15.0
   double ddHigh     = MaxDrawdownPercent * 0.67;   // ~10.0
   double ddModerate = MaxDrawdownPercent * 0.33;   // ~5.0
   
   if(drawdown > ddCritical)
   {
      Print("RISK: Drawdown critico (", DoubleToString(drawdown, 2), "%), reduzindo risco para 25%");
      adjustedRisk = riskPercent * 0.25;  // Reduz 75%
   }
   else if(drawdown > ddHigh)
   {
      Print("RISK: Drawdown alto (", DoubleToString(drawdown, 2), "%), reduzindo risco para 50%");
      adjustedRisk = riskPercent * 0.50;  // Reduz 50%
   }
   else if(drawdown > ddModerate)
   {
      Print("RISK: Drawdown moderado (", DoubleToString(drawdown, 2), "%), reduzindo risco para 75%");
      adjustedRisk = riskPercent * 0.75;  // Reduz 25%
   }
   
   double riskMoney = equity * adjustedRisk / 100.0;
   
   double tickValue=SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize=SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double point=SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(tickValue<=0 || tickSize<=0 || point<=0)
      return 0.0;   // dados invalidos -> bloqueia

   double lossPerLot=((stopPoints*point)/tickSize)*tickValue;

   if(lossPerLot<=0)
      return 0.0;   // calculo invalido -> bloqueia

   double lot=riskMoney/lossPerLot;

   double minLot=SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot=SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   // v1.3.0 (Etapa 3): lote abaixo do minimo NAO e mais forcado
   // silenciosamente. AllowMinLotOverride=true mantem o comportamento
   // antigo com log explicito do risco real; false bloqueia (estrito).
   if(lot < minLot)
   {
      if(!AllowMinLotOverride)
      {
         Print("RISK: Lote calculado (", DoubleToString(lot, 2),
               ") abaixo do minimo (", DoubleToString(minLot, 2),
               ") -> trade BLOQUEADO");
         return 0.0;
      }

      Print("RISK: ATENCAO | Lote minimo forcado (", DoubleToString(minLot, 2),
            ") | Risco real excede o configurado (",
            DoubleToString(riskPercent, 2), "%)");
      lot = minLot;
   }

   lot=MathMin(maxLot,lot);

   lot=MathFloor(lot/step)*step;

   Print("RISK CALC | Balance=", DoubleToString(balance, 2), 
         " | Equity=", DoubleToString(equity, 2),
         " | DD=", DoubleToString(drawdown, 2), "%",
         " | Risk%=", DoubleToString(adjustedRisk, 2),
         " | Lot=", DoubleToString(lot, 2));

   return NormalizeDouble(lot,2);
}

#endif
