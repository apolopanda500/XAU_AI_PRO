// XAU_AI_PRO v1.2.0
#ifndef PERFORMANCEANALYZER_MQH
#define PERFORMANCEANALYZER_MQH

//==================================================
// PERFORMANCE ANALYZER
//==================================================

int PA_TotalTrades = 0;
int PA_Wins = 0;
int PA_Losses = 0;

double PA_TotalProfit = 0.0;
double PA_TotalLoss = 0.0;

//==================================================
// INIT
//==================================================

void PerformanceInit()
{
   PA_TotalTrades = 0;
   PA_Wins = 0;
   PA_Losses = 0;
   PA_TotalProfit = 0.0;
   PA_TotalLoss = 0.0;
}

//==================================================
// REGISTER
//==================================================

void RegisterTradePerformance(double profit)
{
   PA_TotalTrades++;

   if(profit > 0)
   {
      PA_Wins++;
      PA_TotalProfit += profit;
   }
   else
   {
      PA_Losses++;
      PA_TotalLoss += MathAbs(profit);
   }
}

//==================================================
// WIN RATE
//==================================================

double PA_WinRate()
{
   if(PA_TotalTrades == 0)
      return 0.0;

   return NormalizeDouble(
      (double)PA_Wins * 100.0 / PA_TotalTrades,
      2
   );
}

//==================================================
// PROFIT FACTOR
//==================================================

double PA_ProfitFactor()
{
   if(PA_TotalLoss <= 0)
      return 999.0;

   return NormalizeDouble(
      PA_TotalProfit / PA_TotalLoss,
      2
   );
}

//==================================================
// NET PROFIT
//==================================================

double PA_NetProfit()
{
   return NormalizeDouble(
      PA_TotalProfit - PA_TotalLoss,
      2
   );
}

//==================================================
// DEBUG
//==================================================

void PrintPerformance()
{
   Print("==============================");
   Print("PERFORMANCE");
   Print("==============================");
   Print("Trades : ",PA_TotalTrades);
   Print("Wins   : ",PA_Wins);
   Print("Losses : ",PA_Losses);
   Print("WinRate: ",PA_WinRate(),"%");
   Print("Profit : ",PA_TotalProfit);
   Print("Loss   : ",PA_TotalLoss);
   Print("Factor : ",PA_ProfitFactor());
   Print("Net    : ",PA_NetProfit());
   Print("==============================");
}

//==================================================
// DASHBOARD INTERFACE
//==================================================

int PerformanceTrades()
{
   return PA_TotalTrades;
}


double PerformanceWinRate()
{
   return PA_WinRate();
}

//==================================================
// CURRENT DRAWDOWN
//==================================================

double PerformanceCurrentDrawdown()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);

   if(balance <= 0)
      return 0.0;

   return ((balance - equity) / balance) * 100.0;
}

//==================================================
// SUMMARY
//==================================================

string PerformanceSummary()
{
   string summary = "=== PERFORMANCE ===\n";
   summary += "Trades: " + IntegerToString(PA_TotalTrades) + "\n";
   summary += "Win Rate: " + DoubleToString(PA_WinRate(), 2) + "%\n";
   summary += "Profit Factor: " + DoubleToString(PA_ProfitFactor(), 2) + "\n";
   summary += "Net Profit: " + DoubleToString(PA_NetProfit(), 2) + "\n";
   summary += "Drawdown: " + DoubleToString(PerformanceCurrentDrawdown(), 2) + "%\n";
   return summary;
}

#endif