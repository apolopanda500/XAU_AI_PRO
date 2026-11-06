// XAU_AI_PRO v1.2.9
// BacktestAnalyzer - ETAPA 8 (v2.0)
// Registra cada trade do tester em BacktestReport.csv
// (FILE_COMMON) e calcula metricas completas: win rate,
// profit factor, drawdown maximo, sharpe e expectativa.
#ifndef BACKTESTANALYZER_MQH
#define BACKTESTANALYZER_MQH

#define BACKTEST_MAX_TRADES 10000

int btFile = INVALID_HANDLE;

bool BacktestReady = false;
ulong BacktestTrades = 0;
ulong BacktestWins = 0;
ulong BacktestLosses = 0;

double BacktestProfit = 0.0;
double BacktestGrossProfit = 0.0;
double BacktestGrossLoss = 0.0;
double BacktestExpectancy = 0.0;
double BacktestProfitFactor = 0.0;
double BacktestMaxDD = 0.0;
double BacktestMaxDDPct = 0.0;
double BacktestSharpe = 0.0;
double BacktestPeakEquity = 0.0;
double BacktestEquity = 0.0;

double btReturns[BACKTEST_MAX_TRADES];
int    btReturnCount = 0;

//==================================================
// INIT
//==================================================

bool BacktestInit()
{
   if(btFile != INVALID_HANDLE)
   {
      FileClose(btFile);
      btFile = INVALID_HANDLE;
   }

   BacktestReady = false;

   BacktestTrades = 0;
   BacktestWins = 0;
   BacktestLosses = 0;

   BacktestProfit = 0.0;
   BacktestGrossProfit = 0.0;
   BacktestGrossLoss = 0.0;
   BacktestExpectancy = 0.0;
   BacktestProfitFactor = 0.0;
   BacktestMaxDD = 0.0;
   BacktestMaxDDPct = 0.0;
   BacktestSharpe = 0.0;
   BacktestPeakEquity = 0.0;
   BacktestEquity = 0.0;
   btReturnCount = 0;

   ArrayInitialize(btReturns, 0.0);

   btFile = FileOpen(
      "BacktestReport.csv",
      FILE_COMMON |
      FILE_READ |
      FILE_WRITE |
      FILE_CSV |
      FILE_ANSI |
      FILE_SHARE_READ |
      FILE_SHARE_WRITE
   );

   if(btFile == INVALID_HANDLE)
   {
      Print("BACKTEST ERROR | Code=", GetLastError());
      return false;
   }

   FileSeek(btFile, 0, SEEK_END);

   if(FileSize(btFile) == 0)
   {
      FileWrite(
         btFile,
         "Time",
         "Symbol",
         "Signal",
         "Price",
         "Lot",
         "Spread",
         "ATR",
         "ADX",
         "RSI",
         "AI",
         "Result",
         "Profit"
      );

      FileFlush(btFile);
   }

   BacktestReady = true;

   // v1.2.88 (02/11/2026) - P1.75: tag [BT]; o texto era um titulo sem dados.
   if(LogInicioDetalhe()) Print("[BT] inicializado");

   return true;
}

//==================================================
// LOG TRADE (ENTRADA)
// Registra a abertura sem contabilizar resultado.
//==================================================

void BacktestLog(
   int signal,
   double price,
   double lot,
   double spread,
   double atr,
   double adx,
   double rsi,
   double aiScore,
   string result
)
{
   if(!BacktestReady)
      return;

   if(btFile == INVALID_HANDLE)
      return;

   string sig = "NONE";

   if(signal == 1)
      sig = "BUY";

   if(signal == -1)
      sig = "SELL";

   FileSeek(btFile, 0, SEEK_END);

   FileWrite(
      btFile,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
      _Symbol,
      sig,
      DoubleToString(price, _Digits),
      DoubleToString(lot, 2),
      DoubleToString(spread, 1),
      DoubleToString(atr, _Digits),
      DoubleToString(adx, 2),
      DoubleToString(rsi, 2),
      DoubleToString(aiScore, 2),
      result,
      "0.00"
   );

   FileFlush(btFile);
}

//==================================================
// LOG TRADE COM PROFIT (SAIDA)
// Contabiliza resultado + metricas de performance.
//==================================================

void BacktestLogResult(
   int signal,
   double price,
   double lot,
   double spread,
   double atr,
   double adx,
   double rsi,
   double aiScore,
   string result,
   double profit
)
{
   if(!BacktestReady)
      return;

   if(btFile == INVALID_HANDLE)
      return;

   string sig = "NONE";

   if(signal == 1)
      sig = "BUY";

   if(signal == -1)
      sig = "SELL";

   BacktestTrades++;

   if(profit > 0.0)
   {
      BacktestWins++;
      BacktestGrossProfit += profit;
   }
   else if(profit < 0.0)
   {
      BacktestLosses++;
      BacktestGrossLoss += -profit;
   }

   BacktestProfit += profit;

   // Equity acumulada + drawdown maximo
   BacktestEquity += profit;
   if(BacktestEquity > BacktestPeakEquity)
      BacktestPeakEquity = BacktestEquity;

   double dd = BacktestPeakEquity - BacktestEquity;
   if(dd > BacktestMaxDD)
   {
      BacktestMaxDD = dd;
      if(BacktestPeakEquity > 0.0)
         BacktestMaxDDPct = (dd / BacktestPeakEquity) * 100.0;
   }

   // Retorno por trade (para sharpe)
   if(btReturnCount < BACKTEST_MAX_TRADES)
   {
      btReturns[btReturnCount] = profit;
      btReturnCount++;
   }

   FileSeek(btFile, 0, SEEK_END);

   FileWrite(
      btFile,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
      _Symbol,
      sig,
      DoubleToString(price, _Digits),
      DoubleToString(lot, 2),
      DoubleToString(spread, 1),
      DoubleToString(atr, _Digits),
      DoubleToString(adx, 2),
      DoubleToString(rsi, 2),
      DoubleToString(aiScore, 2),
      result,
      DoubleToString(profit, 2)
   );

   FileFlush(btFile);
}

//==================================================
// WIN RATE
//==================================================

double BacktestWinRate()
{
   if(BacktestTrades == 0)
      return 0.0;

   return NormalizeDouble(
      (BacktestWins * 100.0) / (double)BacktestTrades,
      2
   );
}

//==================================================
// PROFIT FACTOR
//==================================================

double BacktestProfitFactorCalc()
{
   if(BacktestGrossLoss > 0.0)
      return NormalizeDouble(BacktestGrossProfit / BacktestGrossLoss, 2);

   if(BacktestGrossProfit > 0.0)
      return 999.0;

   return 0.0;
}

//==================================================
// SHARPE (por trade, anualizado aproximado)
//==================================================

double BacktestSharpeCalc()
{
   int n = btReturnCount;
   if(n < 2)
      return 0.0;

   double sum = 0.0;
   for(int i = 0; i < n; i++)
      sum += btReturns[i];

   double mean = sum / n;

   double var = 0.0;
   for(int i = 0; i < n; i++)
   {
      double d = btReturns[i] - mean;
      var += d * d;
   }

   if(n > 1)
      var /= (n - 1);

   if(var <= 0.0)
      return 0.0;

   double std = MathSqrt(var);
   if(std == 0.0)
      return 0.0;

   return NormalizeDouble(mean / std * MathSqrt(n), 2);
}

//==================================================
// GETTERS
//==================================================

ulong BacktestTotalTrades()
{
   return BacktestTrades;
}

ulong BacktestTotalWins()
{
   return BacktestWins;
}

ulong BacktestTotalLosses()
{
   return BacktestLosses;
}

double BacktestTotalProfit()
{
   return NormalizeDouble(BacktestProfit, 2);
}

bool BacktestIsReady()
{
   return (BacktestReady && btFile != INVALID_HANDLE);
}

//==================================================
// SUMMARY
//==================================================

string BacktestSummary()
{
   // v1.2.87 (02/11/2026) - P1.74: 4 linhas por chamada (init e deinit de
   // cada instancia). O mesmo dado passa a UMA linha.
   string s = StringFormat(
      "[BT] Trades=%d W=%d L=%d | Profit=%.2f | WR=%.2f%% | PF=%.2f | MaxDD=%.2f (%.2f%%) | Sharpe=%.2f | Expect=%.2f",
      (int)BacktestTrades, (int)BacktestWins, (int)BacktestLosses,
      BacktestProfit, BacktestWinRate(), BacktestProfitFactorCalc(),
      BacktestMaxDD, BacktestMaxDDPct, BacktestSharpeCalc(),
      (BacktestTrades > 0 ? BacktestProfit / (double)BacktestTrades : 0.0));

   return s;
}

//==================================================
// CLOSE
//==================================================

void BacktestClose()
{
   if(btFile != INVALID_HANDLE)
   {
      FileFlush(btFile);
      FileClose(btFile);
      btFile = INVALID_HANDLE;
   }

   BacktestSharpe = BacktestSharpeCalc();
   BacktestProfitFactor = BacktestProfitFactorCalc();

   if(BacktestTrades > 0)
      BacktestExpectancy = BacktestProfit / (double)BacktestTrades;

   BacktestReady = false;

   // v1.2.83 (02/11/2026) - P1.70: linha de encerramento so no tester.
   if(MQLInfoInteger(MQL_TESTER))
      Print("BACKTEST ANALYZER | Finalizado | ",
      "Trades=", IntegerToString((int)BacktestTrades),
      " | Wins=", IntegerToString((int)BacktestWins),
      " | Losses=", IntegerToString((int)BacktestLosses),
      " | WinRate=", DoubleToString(BacktestWinRate(), 2),
      "% | Profit=", DoubleToString(BacktestProfit, 2),
      " | PF=", DoubleToString(BacktestProfitFactor, 2),
      " | MaxDD=", DoubleToString(BacktestMaxDD, 2),
      " | Sharpe=", DoubleToString(BacktestSharpe, 2));

   // v1.2.88 (02/11/2026) - P1.75: com 0 trades o resumo era uma linha de zeros
   // por instancia (Trades=0 W=0 L=0 PF=0.00). Sem trades nao ha resumo a dar.
   if(BacktestTrades > 0)
      Print(BacktestSummary());

   // Grava resumo em arquivo (FILE_COMMON) para validacao observavel
   int h = FileOpen("BacktestSummary.txt", FILE_COMMON | FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h != INVALID_HANDLE)
   {
      FileSeek(h, 0, SEEK_END);
      FileWrite(h, "===== " + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + " =====");
      FileWrite(h, BacktestSummary());
      FileClose(h);
   }
}

#endif
