// XAU_AI_PRO v1.2.9
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

//==================================================
// NORMALIZACAO DE VOLUME PELO STEP DO SIMBOLO
//==================================================
// MEDIDO em 23/10/2026: o retorno era `NormalizeDouble(lot, 2)`. Em corretora
// com `SYMBOL_VOLUME_STEP = 0,001` (cripto), 0,001 vira 0,00 — a ordem sai com
// volume zero ou com o dobro do pretendido. As casas decimais vem do STEP, que
// e a unica fonte que sabe a unidade daquele simbolo.
double NormalizarVolume(double volume, double step)
{
   if(step <= 0.0)
      return(NormalizeDouble(volume, 2));

   volume = MathFloor(volume / step + 1e-8) * step;

   int casas = 0;
   double s = step;

   while(casas < 8 && MathAbs(s - MathRound(s)) > 1e-9)
   {
      s *= 10.0;
      casas++;
   }

   return(NormalizeDouble(volume, casas));
}

double CalculateLotByRisk(
   string symbol,
   double riskPercent,
   int stopPoints
)
{
   // Simbolo vazio e RECUSA, nunca um lote padrao. MEDIDO: a versao anterior
   // devolvia 0.01 aqui, ou seja, inventava um ativo para o risco.
   if(symbol=="")
      return(0.0);

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

   lot=NormalizarVolume(lot, step);

   if(DiagGateAllow(symbol, "RISK_CALC",
            DoubleToString(balance, 2) + "|" + DoubleToString(lot, 2), 14400))
   Print("RISK CALC | Balance=", DoubleToString(balance, 2), 
         " | Equity=", DoubleToString(equity, 2),
         " | DD=", DoubleToString(drawdown, 2), "%",
         " | Risk%=", DoubleToString(adjustedRisk, 2),
         " | Lot=", DoubleToString(lot, 2));

   return(lot);
}



//==================================================
// LOTE POR RISCO EM DINHEIRO (29/10/2026)
//==================================================
// MEDIDO na conta 113568614: a ordem saia com 0,41 lote e stop de 5 PONTOS.
// O lote vinha de `RiskPercent` (1% do saldo, dimensionado para 300 pontos);
// o stop vinha de `RiskPerTradeUsd` (US$ 2,00 / 0,41 lote = 5 pontos). Os dois
// numeros descreviam operacoes diferentes, e a que ia para o mercado era a
// mais fragil possivel: 0,5 pip de stop, dentro do spread.
//
// Aqui o lote e dimensionado pela MESMA distancia que o stop usa
// (`StopLossPoints`): o risco em dolares fica igual ao configurado e o stop
// fica fora do spread. Sem dados de tick na ficha do simbolo, devolve 0.
double CalculateLotByRiskUSD(
   string symbol,
   double riskUsd,
   int stopPoints
)
{
   if(symbol=="" || riskUsd<=0.0)
      return(0.0);

   if(stopPoints<=0)
      stopPoints=100;

   double balance=AccountInfoDouble(ACCOUNT_BALANCE);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double minEquityRatio=MinEquityPercent/100.0;

   if(equity < balance*minEquityRatio)
   {
      Print("RISK: Equity critica (", DoubleToString(equity, 2),
            " < ", DoubleToString(balance*minEquityRatio, 2),
            "), bloqueando operacoes");
      return 0.0;
   }

   if(!CheckDailyLossDaily())
   {
      Print("RISK: Limite de perda diaria atingido");
      return 0.0;
   }

   // Mesma reducao escalonada por drawdown do CalculateLotByRisk.
   double drawdown=GetDrawdownPercent();
   double fator=1.0;

   if(drawdown > MaxDrawdownPercent)
      fator=0.25;
   else if(drawdown > MaxDrawdownPercent*0.67)
      fator=0.50;
   else if(drawdown > MaxDrawdownPercent*0.33)
      fator=0.75;

   // Valor em dinheiro de 1 ponto para 1,0 lote (TICK_VALUE/TICK_SIZE).
   double perLot=RiscoEmDinheiroDaOrdem(symbol, 1.0, (double)stopPoints);

   if(perLot<=0.0)
   {
      Print("RISK: valor do ponto indisponivel | ", symbol,
            " | tick_value=", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE), 5),
            " | tick_size=", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE), 5),
            " | point=", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_POINT), 5));
      return 0.0;
   }

   double lot=(riskUsd*fator)/perLot;

   double minLot=SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot=SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   if(lot < minLot)
   {
      if(!AllowMinLotOverride)
      {
         Print("RISK: Lote calculado (", DoubleToString(lot, 4),
               ") abaixo do minimo (", DoubleToString(minLot, 2),
               ") -> trade BLOQUEADO");
         return 0.0;
      }

      lot=minLot;
   }

   lot=MathMin(maxLot, lot);
   lot=NormalizarVolume(lot, step);

   if(DiagGateAllow(symbol, "RISK_CALC_USD",
            DoubleToString(balance, 2) + "|" + DoubleToString(lot, 2), 14400))
   Print("[RISK] CALC USD | Balance=", DoubleToString(balance, 2),
         " | Risco=", DoubleToString(riskUsd, 2), " USD",
         " | Stop=", IntegerToString(stopPoints), " pts",
         " | ValorPorLote=", DoubleToString(perLot, 2),
         " | DD=", DoubleToString(drawdown, 2), "%",
         " | Fator=", DoubleToString(fator, 2),
         " | Lot=", DoubleToString(lot, 2));

   return(lot);
}

// Seletor unico usado pelo ExecutionEngine: quando o risco em DINHEIRO esta
// configurado ele manda (lote derivado da mesma distancia do stop); senao cai
// no dimensionamento por percentual, que continua intacto.
double CalculateLotByRiskAuto(
   string symbol,
   int stopPoints
)
{
   double riscoTrade = RiscoPorTradeUsd();

   if(riscoTrade > 0.0)
      return CalculateLotByRiskUSD(symbol, riscoTrade, stopPoints);

   return CalculateLotByRisk(symbol, RiskPercent, stopPoints);
}

//==================================================
// MOTIVO DO LOTE ZERO (P1.3514 - v1.2.191)
//==================================================
// O lote pode ser recusado por razoes diferentes e quem chama
// (CalculateDynamicLot) escrevia sempre "risco/escala", que e' a causa ERRADA
// quando a ficha do simbolo nao tem dados de tick. MEDIDO no servidor actual:
// USDCLP e USDRUB tem tick_value=0.00000000, tick_size=0.00000000 e
// margin_initial=0.00, e nesse caso a recusa acontece em CalculateLotByRiskUSD
// com a linha "RISK: valor do ponto indisponivel"; a mensagem seguinte
// atribuia o bloqueio ao risco, ou seja o operador ficava com duas frases
// contraditorias sobre o mesmo evento.
//
// Esta funcao mede a MESMA ficha que as guardas leem e devolve o motivo medido.
// Nao decide nada: as guardas de divisao por zero (Config.mqh:1046,
// Config.mqh:1102, RiskEngine.mqh:114) continuam a recusar exactamente onde
// recusavam. Muda so o texto que explica a recusa.
string RiskLotBlockReason(string symbol)
{
   double tv = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double pt = SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(tv <= 0.0 || ts <= 0.0 || pt <= 0.0)
      return("ficha do simbolo sem dados de tick (tick_value=" +
             DoubleToString(tv, 5) + " tick_size=" + DoubleToString(ts, 5) +
             " point=" + DoubleToString(pt, 5) +
             ") -> nao e' limite de risco, e' dado do broker");

   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);

   if(minLot <= 0.0)
      return("ficha do simbolo sem volume_min (volume_min=" +
             DoubleToString(minLot, 2) + ")");

   return("risco/escala: ver a linha RISK: anterior (equity, perda diaria, stop ou lote minimo)");
}

#endif
