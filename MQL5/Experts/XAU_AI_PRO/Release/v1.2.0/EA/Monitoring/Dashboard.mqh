// XAU_AI_PRO v1.2.0
#ifndef DASHBOARD_MQH
#define DASHBOARD_MQH

#include "../Core/SignalCore.mqh"
#include "../Core/DecisionEngine.mqh"
#include "../Core/PositionManager.mqh"
#include "../Core/RiskEngine.mqh"
#include "../Core/PerformanceAnalyzer.mqh"

#include "../Indicators/TrendStrength.mqh"
#include "../Indicators/RSI.mqh"
#include "../Indicators/ADX.mqh"
#include "../Indicators/VolatilityFilter.mqh"

//==================================================
// DASHBOARD
// XAU_AI_PRO — MULTI-SYMBOL READY
//==================================================

bool DashboardReady = false;


//==================================================
// INIT
//==================================================

void DashboardInit()
{
   DashboardReady = true;

   Comment(
      "XAU_AI_PRO\n",
      "Dashboard inicializado..."
   );
}


//==================================================
// SIGNAL TEXT
//==================================================

string DashboardSignalText(int signal)
{
   if(signal == 1)
      return "BUY";

   if(signal == -1)
      return "SELL";

   return "WAIT";
}


//==================================================
// BOOLEAN TEXT
//==================================================

string DashboardBoolText(bool value)
{
   return value ? "SIM" : "NAO";
}


//==================================================
// UPDATE
//==================================================

void DashboardUpdate()
{
   if(!DashboardReady)
      return;


   double balance =
      AccountInfoDouble(
         ACCOUNT_BALANCE
      );


   double equity =
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );


   double profit =
      AccountInfoDouble(
         ACCOUNT_PROFIT
      );


   int signal =
      GetSignal(_Symbol);


   string signalText =
      DashboardSignalText(
         signal
      );


   bool position =
      HasOpenPosition();


   double atr =
      GetATR(_Symbol);


   double adx =
      GetADX(_Symbol);


   double rsi =
      GetRSI(_Symbol);


   double drawdown = 0.0;


   if(balance > 0.0)
   {
      drawdown =
         ((balance - equity) / balance)
         * 100.0;
   }


   Comment(

      "========== XAU_AI_PRO ==========",

      "\nSymbol: ",
      _Symbol,

      "\nTimeframe: ",
      EnumToString(
         (ENUM_TIMEFRAMES)_Period
      ),

      "\n-------------------------------",

      "\nBalance: ",
      DoubleToString(
         balance,
         2
      ),

      "\nEquity: ",
      DoubleToString(
         equity,
         2
      ),

      "\nProfit: ",
      DoubleToString(
         profit,
         2
      ),

      "\nDrawdown: ",
      DoubleToString(
         drawdown,
         2
      ),
      "%",

      "\n-------------------------------",

      "\nSignal: ",
      signalText,

      "\nPosition: ",
      DashboardBoolText(
         position
      ),

      "\n-------------------------------",

      "\nATR: ",
      DoubleToString(
         atr,
         2
      ),

      "\nADX: ",
      DoubleToString(
         adx,
         2
      ),

      "\nRSI: ",
      DoubleToString(
         rsi,
         2
      ),

      "\n-------------------------------",

      "\nTrades: ",
      PerformanceTrades(),

      "\nWinRate: ",
      DoubleToString(
         PerformanceWinRate(),
         2
      ),
      "%",

      "\n==============================="
   );
}


//==================================================
// CLEAR
//==================================================

void DashboardClear()
{
   Comment("");
}


//==================================================
// DESTROY
//==================================================

void DashboardDestroy()
{
   DashboardClear();

   DashboardReady = false;
}


#endif