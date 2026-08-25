// XAU_AI_PRO v1.2.0
#ifndef DAILYRISK_MQH
#define DAILYRISK_MQH

#include "../Core/Config.mqh"
#include "../Enterprise/SafetyManager.mqh"

//==================================================
// DAILY RISK - DELEGA PARA SAFETY MANAGER
//==================================================

int GetDayKey()
{
   MqlDateTime dt;

   TimeToStruct(
      TimeCurrent(),
      dt
   );

   return(
      dt.year * 1000 +
      dt.day_of_year
   );
}

void InitDailyRisk()
{
   CSafetyManager::Init();

   PrintFormat(
      "[DAILYRISK] Delegating to SafetyManager"
   );
}

void ResetDaily()
{
   // SafetyManager gerencia reset diario automaticamente
}

void RegisterDailyTrade()
{
   CSafetyManager::RegisterTrade();
}

//==================================================
// COMPATIBILIDADE - Calcula perda diaria
//==================================================

double GetDailyLossPercentDaily()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   if(balance <= 0.0)
      return 0.0;

   double loss =
      (balance - equity) / balance * 100.0;

   return NormalizeDouble(
      MathMax(loss, 0.0),
      2
   );
}

bool CheckDailyLossDaily()
{
   return CSafetyManager::CheckDailyLoss();
}

bool CanTradeToday()
{
   if(!CSafetyManager::CheckDailyLoss())
      return false;

   if(!CSafetyManager::CheckDailyDrawdown())
      return false;

   if(!CSafetyManager::CheckDailyTrades())
      return false;

   return true;
}

void PrintDailyRisk()
{
   Print(
      "Trades hoje: ",
      CSafetyManager::GetDailyTrades(),
      " | Loss diario: ",
      DoubleToString(
         GetDailyLossPercentDaily(),
         2
      ),
      "%"
   );
}

#endif