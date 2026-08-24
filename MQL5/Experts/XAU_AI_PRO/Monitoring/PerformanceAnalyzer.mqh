// XAU_AI_PRO v1.2.0
#ifndef PERFORMANCEANALYZER_MQH
#define PERFORMANCEANALYZER_MQH

#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include "../Indicators/ADX.mqh"
#include "../Indicators/RSI.mqh"
#include "../Monitoring/Logger.mqh"

//==================================================
// PERFORMANCE ANALYZER
// XAU_AI_PRO
//==================================================

struct TradeRecord
{
   datetime time;
   string   symbol;
   bool     isBuy;

   double entry;
   double exit;
   double profit;

   double aiScore;

   double atr;
   double adx;
   double rsi;
};

//==================================================
// STORAGE
//==================================================

TradeRecord g_trades[];
double      g_returns[];

int g_totalTrades   = 0;
int g_winningTrades = 0;
int g_losingTrades  = 0;

int g_returnsCount = 0;

//==================================================
// PROFIT
//==================================================

double g_totalProfit = 0.0;
double g_totalLoss   = 0.0;

double g_maxWin  = 0.0;
double g_maxLoss = 0.0;

//==================================================
// EQUITY / DRAWDOWN
//==================================================

double g_initialBalance = 0.0;
double g_maxEquity      = 0.0;
double g_maxDrawdown    = 0.0;

//==================================================
// INIT
//==================================================

bool PerformanceInit()
{
   g_initialBalance =
      AccountInfoDouble(ACCOUNT_BALANCE);

   g_maxEquity =
      g_initialBalance;

   g_totalTrades   = 0;
   g_winningTrades = 0;
   g_losingTrades  = 0;

   g_returnsCount = 0;

   g_totalProfit = 0.0;
   g_totalLoss   = 0.0;

   g_maxWin  = 0.0;
   g_maxLoss = 0.0;

   g_maxDrawdown = 0.0;

   ArrayResize(g_trades, 0, 1000);
   ArrayResize(g_returns, 0, 1000);

   LogSystem(
      "PerformanceAnalyzer inicializado. Balance inicial: ",
      DoubleToString(g_initialBalance, 2)
   );

   return true;
}

//==================================================
// REGISTER TRADE
//==================================================

void PerformanceRegisterTrade(
   bool isBuy,
   double entry,
   double exit,
   double profit,
   double aiScore = 0.0
)
{
   TradeRecord trade;

   trade.time   = TimeCurrent();
   trade.symbol = _Symbol;

   trade.isBuy = isBuy;

   trade.entry  = entry;
   trade.exit   = exit;
   trade.profit = profit;

   trade.aiScore = aiScore;

   trade.atr = GetATR();
   trade.adx = GetADX();
   trade.rsi = GetRSI();

   //==================================================
   // TRADE ARRAY
   //==================================================

   int newTradeCount =
      g_totalTrades + 1;

   if(ArrayResize(
      g_trades,
      newTradeCount,
      1000
   ) < 0)
   {
      LogError(
         "PerformanceAnalyzer: falha ao redimensionar trades"
      );

      return;
   }

   g_trades[g_totalTrades] = trade;

   g_totalTrades++;

   //==================================================
   // WIN / LOSS
   //==================================================

   if(profit > 0.0)
   {
      g_winningTrades++;

      g_totalProfit += profit;

      if(profit > g_maxWin)
         g_maxWin = profit;
   }
   else
   if(profit < 0.0)
   {
      g_losingTrades++;

      double loss =
         MathAbs(profit);

      g_totalLoss += loss;

      if(loss > g_maxLoss)
         g_maxLoss = loss;
   }

   //==================================================
   // EQUITY RETURN
   //==================================================

   double equity =
      AccountInfoDouble(ACCOUNT_EQUITY);

   double returnPct = 0.0;

   if(g_initialBalance > 0.0)
   {
      returnPct =
         ((equity - g_initialBalance)
         / g_initialBalance)
         * 100.0;
   }

   int newReturnCount =
      g_returnsCount + 1;

   if(ArrayResize(
      g_returns,
      newReturnCount,
      1000
   ) < 0)
   {
      LogError(
         "PerformanceAnalyzer: falha ao redimensionar returns"
      );

      return;
   }

   g_returns[g_returnsCount] =
      returnPct;

   g_returnsCount++;

   //==================================================
   // MAX EQUITY
   //==================================================

   if(equity > g_maxEquity)
      g_maxEquity = equity;

   //==================================================
   // MAX DRAWDOWN
   //==================================================

   if(g_maxEquity > 0.0)
   {
      double currentDD =
         ((g_maxEquity - equity)
         / g_maxEquity)
         * 100.0;

      if(currentDD > g_maxDrawdown)
         g_maxDrawdown = currentDD;
   }

   LogTrade(
      "Trade registrado",
      isBuy ? "BUY" : "SELL",
      "Profit=",
      DoubleToString(profit, 2)
   );
}

//==================================================
// WIN RATE
//==================================================

double PerformanceWinRate()
{
   if(g_totalTrades <= 0)
      return 0.0;

   return NormalizeDouble(
      ((double)g_winningTrades
      / g_totalTrades) * 100.0,
      2
   );
}

//==================================================
// PROFIT FACTOR
//==================================================

double PerformanceProfitFactor()
{
   if(g_totalLoss <= 0.0)
   {
      if(g_totalProfit > 0.0)
         return 999.0;

      return 0.0;
   }

   return NormalizeDouble(
      g_totalProfit / g_totalLoss,
      2
   );
}

//==================================================
// AVERAGE WIN
//==================================================

double PerformanceAverageWin()
{
   if(g_winningTrades <= 0)
      return 0.0;

   return NormalizeDouble(
      g_totalProfit / g_winningTrades,
      2
   );
}

//==================================================
// AVERAGE LOSS
//==================================================

double PerformanceAverageLoss()
{
   if(g_losingTrades <= 0)
      return 0.0;

   return NormalizeDouble(
      g_totalLoss / g_losingTrades,
      2
   );
}

//==================================================
// EXPECTANCY
//==================================================

double PerformanceExpectancy()
{
   if(g_totalTrades <= 0)
      return 0.0;

   double winRate =
      PerformanceWinRate() / 100.0;

   double avgWin =
      PerformanceAverageWin();

   double avgLoss =
      PerformanceAverageLoss();

   if(avgLoss <= 0.0)
   {
      if(avgWin > 0.0)
         return 999.0;

      return 0.0;
   }

   return NormalizeDouble(
      (winRate * avgWin)
      -
      ((1.0 - winRate) * avgLoss),
      2
   );
}

//==================================================
// RECOVERY FACTOR
//==================================================

double PerformanceRecoveryFactor()
{
   if(g_maxDrawdown <= 0.0)
      return 0.0;

   if(g_initialBalance <= 0.0)
      return 0.0;

   double maxDDMoney =
      g_maxDrawdown
      * g_initialBalance
      / 100.0;

   if(maxDDMoney <= 0.0)
      return 0.0;

   return NormalizeDouble(
      g_totalProfit / maxDDMoney,
      2
   );
}

//==================================================
// SHARPE
//==================================================

double PerformanceSharpe()
{
   if(g_returnsCount < 2)
      return 0.0;

   double sum = 0.0;

   for(int i = 0;
       i < g_returnsCount;
       i++)
   {
      sum += g_returns[i];
   }

   double mean =
      sum / g_returnsCount;

   double variance = 0.0;

   for(int i = 0;
       i < g_returnsCount;
       i++)
   {
      double diff =
         g_returns[i] - mean;

      variance +=
         diff * diff;
   }

   variance /=
      (g_returnsCount - 1);

   double stdDev =
      MathSqrt(variance);

   if(stdDev <= 0.0)
      return 0.0;

   return NormalizeDouble(
      mean / stdDev,
      2
   );
}

//==================================================
// SORTINO
//==================================================

double PerformanceSortino()
{
   if(g_returnsCount < 2)
      return 0.0;

   double sum = 0.0;

   int negativeCount = 0;

   for(int i = 0;
       i < g_returnsCount;
       i++)
   {
      sum += g_returns[i];

      if(g_returns[i] < 0.0)
         negativeCount++;
   }

   double mean =
      sum / g_returnsCount;

   if(negativeCount == 0)
   {
      if(mean > 0.0)
         return 999.0;

      return 0.0;
   }

   double downsideVariance = 0.0;

   for(int i = 0;
       i < g_returnsCount;
       i++)
   {
      if(g_returns[i] < 0.0)
      {
         double diff =
            g_returns[i] - mean;

         downsideVariance +=
            diff * diff;
      }
   }

   downsideVariance /=
      negativeCount;

   double downsideDeviation =
      MathSqrt(downsideVariance);

   if(downsideDeviation <= 0.0)
      return 0.0;

   return NormalizeDouble(
      mean / downsideDeviation,
      2
   );
}

//==================================================
// ULCER INDEX
//==================================================

double PerformanceUlcerIndex()
{
   if(g_returnsCount <= 0)
      return 0.0;

   if(g_initialBalance <= 0.0)
      return 0.0;

   double peak =
      g_initialBalance;

   double ulcerSum = 0.0;

   for(int i = 0;
       i < g_returnsCount;
       i++)
   {
      double equity =
         g_initialBalance
         *
         (1.0 + g_returns[i] / 100.0);

      if(equity > peak)
         peak = equity;

      if(peak <= 0.0)
         continue;

      double dd =
         ((peak - equity)
         / peak)
         * 100.0;

      ulcerSum +=
         dd * dd;
   }

   return NormalizeDouble(
      MathSqrt(
         ulcerSum / g_returnsCount
      ),
      2
   );
}

//==================================================
// CURRENT DRAWDOWN
//==================================================

double PerformanceCurrentDrawdown()
{
   double equity =
      AccountInfoDouble(ACCOUNT_EQUITY);

   double balance =
      AccountInfoDouble(ACCOUNT_BALANCE);

   if(balance <= 0.0)
      return 0.0;

   double dd =
      ((balance - equity)
      / balance)
      * 100.0;

   if(dd < 0.0)
      dd = 0.0;

   return NormalizeDouble(
      dd,
      2
   );
}

//==================================================
// CURRENT EQUITY DRAWDOWN FROM PEAK
//==================================================

double PerformancePeakDrawdown()
{
   double equity =
      AccountInfoDouble(ACCOUNT_EQUITY);

   if(g_maxEquity <= 0.0)
      return 0.0;

   double dd =
      ((g_maxEquity - equity)
      / g_maxEquity)
      * 100.0;

   if(dd < 0.0)
      dd = 0.0;

   return NormalizeDouble(
      dd,
      2
   );
}

//==================================================
// TOTAL TRADES
//==================================================

int PerformanceTrades()
{
   return g_totalTrades;
}

//==================================================
// TOTAL PROFIT
//==================================================

double PerformanceTotalProfit()
{
   return g_totalProfit;
}

//==================================================
// TOTAL LOSS
//==================================================

double PerformanceTotalLoss()
{
   return g_totalLoss;
}

//==================================================
// MAX WIN
//==================================================

double PerformanceMaxWin()
{
   return g_maxWin;
}

//==================================================
// MAX LOSS
//==================================================

double PerformanceMaxLoss()
{
   return g_maxLoss;
}

//==================================================
// MAX DRAWDOWN
//==================================================

double PerformanceMaxDrawdown()
{
   return g_maxDrawdown;
}

//==================================================
// SUMMARY
//==================================================

string PerformanceSummary()
{
   string summary =
      "=== PERFORMANCE SUMMARY ===\n";

   summary +=
      "Total Trades: "
      + IntegerToString(g_totalTrades)
      + "\n";

   summary +=
      "Winning Trades: "
      + IntegerToString(g_winningTrades)
      + "\n";

   summary +=
      "Losing Trades: "
      + IntegerToString(g_losingTrades)
      + "\n";

   summary +=
      "Win Rate: "
      + DoubleToString(
         PerformanceWinRate(),
         2
      )
      + "%\n";

   summary +=
      "Total Profit: "
      + DoubleToString(
         g_totalProfit,
         2
      )
      + "\n";

   summary +=
      "Total Loss: "
      + DoubleToString(
         g_totalLoss,
         2
      )
      + "\n";

   summary +=
      "Profit Factor: "
      + DoubleToString(
         PerformanceProfitFactor(),
         2
      )
      + "\n";

   summary +=
      "Avg Win: "
      + DoubleToString(
         PerformanceAverageWin(),
         2
      )
      + "\n";

   summary +=
      "Avg Loss: "
      + DoubleToString(
         PerformanceAverageLoss(),
         2
      )
      + "\n";

   summary +=
      "Expectancy: "
      + DoubleToString(
         PerformanceExpectancy(),
         2
      )
      + "\n";

   summary +=
      "Recovery Factor: "
      + DoubleToString(
         PerformanceRecoveryFactor(),
         2
      )
      + "\n";

   summary +=
      "Sharpe: "
      + DoubleToString(
         PerformanceSharpe(),
         2
      )
      + "\n";

   summary +=
      "Sortino: "
      + DoubleToString(
         PerformanceSortino(),
         2
      )
      + "\n";

   summary +=
      "Ulcer Index: "
      + DoubleToString(
         PerformanceUlcerIndex(),
         2
      )
      + "\n";

   summary +=
      "Max Drawdown: "
      + DoubleToString(
         g_maxDrawdown,
         2
      )
      + "%\n";

   summary +=
      "Peak Drawdown: "
      + DoubleToString(
         PerformancePeakDrawdown(),
         2
      )
      + "%\n";

   summary +=
      "Current Drawdown: "
      + DoubleToString(
         PerformanceCurrentDrawdown(),
         2
      )
      + "%\n";

   return summary;
}

//==================================================
// RESET
//==================================================

void PerformanceReset()
{
   g_totalTrades   = 0;
   g_winningTrades = 0;
   g_losingTrades  = 0;

   g_totalProfit = 0.0;
   g_totalLoss   = 0.0;

   g_maxWin  = 0.0;
   g_maxLoss = 0.0;

   g_maxDrawdown = 0.0;

   g_returnsCount = 0;

   ArrayResize(g_trades, 0);
   ArrayResize(g_returns, 0);

   g_initialBalance =
      AccountInfoDouble(ACCOUNT_BALANCE);

   g_maxEquity =
      g_initialBalance;

   LogSystem(
      "Performance resetada. Novo balance inicial: ",
      DoubleToString(
         g_initialBalance,
         2
      )
   );
}

#endif