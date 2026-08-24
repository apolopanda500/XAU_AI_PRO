// XAU_AI_PRO v1.3.0 - RISK HUB (Etapa 3: hierarquia unica de risco)
#ifndef RISKHUB_MQH
#define RISKHUB_MQH

#include "../Core/Config.mqh"

//==================================================
// RISK HUB
// Fonte UNICA das metricas de risco diario.
// Persistencia via GlobalVariable do terminal:
// sobrevive a reinicializacoes do EA (quedas de
// rede nao zeram mais os limites diarios).
//
// Regra da Etapa 3: modulos inferiores CONSUMEM
// estas metricas; nenhum recalcula drawdown ou
// mantem contador proprio.
//==================================================

//--------------------------------------------------
// CHAVE DO DIA (ano*1000 + dia_do_ano)
//--------------------------------------------------

int RiskHubDayKey()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return(dt.year * 1000 + dt.day_of_year);
}

string RiskHubGV(string suffix)
{
   bool rhTester=(MQLInfoInteger(MQL_TESTER)!=0);
   return "XAI_PRO_" + (rhTester ? "T_" : "") + "RH_" + suffix + "_" + IntegerToString(RiskHubDayKey());
}

//--------------------------------------------------
// GET/SET GENERICOS
//--------------------------------------------------

double RiskHubGet(string suffix, double def)
{
   string gv = RiskHubGV(suffix);
   if(GlobalVariableCheck(gv))
      return GlobalVariableGet(gv);
   return def;
}

void RiskHubSet(string suffix, double value)
{
   GlobalVariableSet(RiskHubGV(suffix), value);
}

//--------------------------------------------------
// LIMPEZA DE DIAS ANTIGOS (1x por hora)
//--------------------------------------------------

void RiskHubCleanupOldDays()
{
   static datetime lastClean = 0;
   datetime now = TimeCurrent();

   if(lastClean > 0 && now - lastClean < 3600)
      return;

   lastClean = now;

   string name;

   for(int i = GlobalVariablesTotal()-1; i >= 0; i--)
   {
      name = GlobalVariableName(i);

      string rhPrefix="XAI_PRO_RH_";

      if(MQLInfoInteger(MQL_TESTER)!=0)
         rhPrefix="XAI_PRO_T_RH_";

      if(StringFind(name, rhPrefix) != 0)
         continue;

      string parts[];

      if(StringSplit(name, '_', parts) >= 4)
      {
         int key = (int)StringToInteger(parts[ArraySize(parts)-1]);

         if(key != RiskHubDayKey())
            GlobalVariableDel(name);
      }
   }
}

//--------------------------------------------------
// PEAK EQUITY DIARIO (persistente)
//--------------------------------------------------

double GetDailyPeakEquity()
{
   RiskHubCleanupOldDays();

   double eq   = AccountInfoDouble(ACCOUNT_EQUITY);
   double peak = RiskHubGet("PEAK", eq);

   if(eq > peak)
   {
      peak = eq;
      RiskHubSet("PEAK", peak);
   }

   return peak;
}

//--------------------------------------------------
// DRAWDOWN PERCENTUAL UNICO (vs peak diario)
// TODOS os modulos consomem esta funcao.
//--------------------------------------------------

double GetDrawdownPercent()
{
   double peak = GetDailyPeakEquity();

   if(peak <= 0.0)
      return 0.0;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (peak - eq) / peak * 100.0;

   return MathMax(dd, 0.0);
}

//--------------------------------------------------
// TRADES DO DIA (persistente)
//--------------------------------------------------

int GetDailyTradesCount()
{
   return (int)RiskHubGet("TRADES", 0);
}

void IncrementDailyTrades()
{
   RiskHubSet("TRADES", GetDailyTradesCount() + 1);
}

//--------------------------------------------------
// DETECCAO DE NOVO DIA
//--------------------------------------------------

bool RiskHubNewDay()
{
   bool isNew = !GlobalVariableCheck(RiskHubGV("TRADES"));

   if(isNew)
      RiskHubSet("TRADES", 0);

   if(!GlobalVariableCheck(RiskHubGV("PEAK")))
      RiskHubSet("PEAK", AccountInfoDouble(ACCOUNT_EQUITY));

   return isNew;
}

#endif // RISKHUB_MQH