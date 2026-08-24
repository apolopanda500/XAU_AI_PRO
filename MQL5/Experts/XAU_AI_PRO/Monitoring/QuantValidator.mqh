//+------------------------------------------------------------------+
//|                                          QuantValidator.mqh      |
//|                                     XAU_AI_PRO - Validation E14  |
//|                 Matriz de avaliacao quantitativa (11 metricas)   |
//+------------------------------------------------------------------+
// ETAPA 14 - VALIDACAO QUANTITATIVA
//
// Monta a matriz de avaliacao do roadmap consolidando as metricas ja
// calculadas pelos modulos existentes e derivando as que faltam:
//
//   Fonte                    Metricas
//   Statistics.mqh           Win Rate, Profit Factor, streaks
//   BacktestAnalyzer.mqh     Expectancy, MaxDD, Sharpe, PF
//   ExecutionStats.mqh       Slippage, Latencia (delay), Rejeicoes
//   QuantValidator (novo)    Recovery Factor, Avg R, Trades/dia
//
// Saidas (FILE_COMMON):
//   QuantValidationReport.txt   -> relatorio legivel
//   quant_matrix.csv            -> matriz em CSV (Backtest/Forward/Broker)
//
// PRINCIPIO: modulo 100% passivo (apenas le e grava). NUNCA bloqueia
// trading nem altera decisoes. Serve de camada de observacao para a
// comparacao Backtest <-> Forward Demo <-> Broker (Fase C / Etapa 14).
//
// NOTA METODOLOGICA (honestidade quantitativa):
//   - Avg R usa como proxy de 1R o prejuizo medio por trade (gross loss /
//     numero de perdas). E uma aproximacao documentada: o risco real por
//     trade (SL distance) podera ser refinado na Etapa 17 (Risk Engine).
//   - Sharpe: por trade, anualizado aproximado (mesma convencao do
//     BacktestAnalyzer ja existente).
//   - Trades/dia: media sobre dias corridos desde o inicio da sessao
//     (conservador; subestima em sessoes curtas).
//+------------------------------------------------------------------+

#ifndef QUANT_VALIDATOR_MQH
#define QUANT_VALIDATOR_MQH

#include "../Core/Config.mqh"
#include "Statistics.mqh"
#include "BacktestAnalyzer.mqh"
#include "../Enterprise/ExecutionStats.mqh"

//==================================================
// CONFIG
//==================================================
#define QUANT_MAX_DAYS_PROXY 3650   // cap de dias para o proxy de trades/dia

//==================================================
// STRUCT DA MATRIZ
//==================================================
struct QuantMetric
{
   string name;        // nome da metrica
   double value;       // valor numerico
   string unit;        // unidade/nota
};

//==================================================
// REGISTRO DE RESULTADO (para Avg R)
//==================================================
int    g_quantTrades       = 0;
double g_quantSumR         = 0.0;
double g_quantSumRisk      = 0.0;   // soma do risco estimado por trade

// Registra um trade fechado com o risco estimado (em dinheiro).
// Se riskAmount <= 0, usa o prejuizo medio como proxy (honesto e
// conservador: so conta quando ja existe historico de perdas).
void QuantRecordResult(double profit, double riskAmount)
{
   g_quantTrades++;

   double risk = riskAmount;

   if(risk <= 0.0)
   {
      int losses = g_statsLosses;
      if(losses > 0 && g_statsTotalLoss > 0.0)
         risk = g_statsTotalLoss / (double)losses;
   }

   if(risk > 0.0)
   {
      g_quantSumR    += profit / risk;
      g_quantSumRisk += risk;
   }
}

//==================================================
// TRADES POR DIA (proxy conservador)
//==================================================
double QuantTradesPerDay()
{
   int total = g_statsTotalTrades;
   if(total <= 0)
      return 0.0;

   datetime now = TimeCurrent();
   datetime dayStart = StatisticsGetDayStart(now);

   int days = (int)((now - dayStart) / 86400) + 1;
   if(days <= 0)
      days = 1;
   if(days > QUANT_MAX_DAYS_PROXY)
      days = QUANT_MAX_DAYS_PROXY;

   return NormalizeDouble((double)total / (double)days, 2);
}

//==================================================
// RECOVERY FACTOR = NetProfit / MaxDD ($)
//==================================================
double QuantRecoveryFactor()
{
   double net = g_statsTotalProfit - g_statsTotalLoss;
   double maxDD = BacktestMaxDD;
   if(maxDD <= 0.0)
      return (net > 0.0 ? 999.0 : 0.0);
   return NormalizeDouble(net / maxDD, 2);
}

//==================================================
// AVG R
//==================================================
double QuantAvgR()
{
   if(g_quantTrades <= 0)
      return 0.0;
   return NormalizeDouble(g_quantSumR / (double)g_quantTrades, 2);
}

//==================================================
// MONTA A MATRIZ (11 metricas do roadmap)
//==================================================
int QuantBuildMatrix(QuantMetric &m[], int maxItems)
{
   int n = 0;

   if(n < maxItems)
   {
      m[n].name  = "Profit Factor";
      double pf = (g_statsTotalLoss > 0.0
                   ? g_statsTotalProfit / g_statsTotalLoss
                   : (g_statsTotalProfit > 0.0 ? 999.0 : 0.0));
      m[n].value = NormalizeDouble(pf, 2);
      m[n].unit  = "x";
      n++;
   }

   if(n < maxItems)
   {
      m[n].name  = "Win Rate";
      int total = g_statsWins + g_statsLosses;
      m[n].value = (total > 0
                    ? NormalizeDouble(100.0 * g_statsWins / total, 2)
                    : 0.0);
      m[n].unit  = "%";
      n++;
   }

   if(n < maxItems)
   {
      m[n].name  = "Expectancy";
      m[n].value = (g_statsTotalTrades > 0
                    ? NormalizeDouble((g_statsTotalProfit - g_statsTotalLoss) / g_statsTotalTrades, 2)
                    : 0.0);
      m[n].unit  = "USD/trade";
      n++;
   }

   if(n < maxItems)
   {
      m[n].name  = "Max Drawdown";
      m[n].value = BacktestMaxDDPct;
      m[n].unit  = "%";
      n++;
   }

   if(n < maxItems)
   {
      m[n].name  = "Recovery Factor";
      m[n].value = QuantRecoveryFactor();
      m[n].unit  = "x";
      n++;
   }

   if(n < maxItems)
   {
      m[n].name  = "Sharpe";
      m[n].value = BacktestSharpeCalc();
      m[n].unit  = "(por trade)";
      n++;
   }

   if(n < maxItems)
   {
      m[n].name  = "Avg R";
      m[n].value = QuantAvgR();
      m[n].unit  = "R";
      n++;
   }

   if(n < maxItems)
   {
      ExecStats es = CExecutionStats::GetStats();
      m[n].name  = "Slippage";
      m[n].value = es.avg_slippage;
      m[n].unit  = "pips";
      n++;
   }

   if(n < maxItems)
   {
      ExecStats es = CExecutionStats::GetStats();
      m[n].name  = "Latencia";
      m[n].value = es.avg_delay_ms;
      m[n].unit  = "ms";
      n++;
   }

   if(n < maxItems)
   {
      ExecStats es = CExecutionStats::GetStats();
      m[n].name  = "Rejeicoes";
      m[n].value = es.rejected;
      m[n].unit  = "ordens";
      n++;
   }

   if(n < maxItems)
   {
      m[n].name  = "Trades/dia";
      m[n].value = QuantTradesPerDay();
      m[n].unit  = "trades";
      n++;
   }

   return n;
}

//==================================================
// SALVA RELATORIO (TXT + CSV em FILE_COMMON)
//==================================================
void QuantSaveReport()
{
   QuantMetric m[11];
   int n = QuantBuildMatrix(m, 11);

   // ----- TXT -----
   int h = FileOpen("QuantValidationReport.txt",
      FILE_COMMON | FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      FileSeek(h, 0, SEEK_END);
      FileWrite(h, "===== QUANT VALIDATION REPORT =====");
      FileWrite(h, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
      FileWrite(h, "Symbol: " + _Symbol);
      FileWrite(h, "Source: EA session | Compare: Backtest / Forward / Broker");

      for(int i = 0; i < n; i++)
      {
         FileWrite(h, StringFormat("%-18s | %-12s | %s",
            m[i].name, DoubleToString(m[i].value, 2), m[i].unit));
      }

      FileWrite(h, "--------------------------------------");
      FileWrite(h, "Nota Avg R: proxy = lucro/prejuizo medio por trade (refinamento na Etapa 17).");
      FileClose(h);
   }

   // ----- CSV -----
   int c = FileOpen("quant_matrix.csv",
      FILE_COMMON | FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(c != INVALID_HANDLE)
   {
      FileSeek(c, 0, SEEK_END);
      if(FileSize(c) == 0)
      {
         FileWrite(c, "metrica", "unidade", "backtest", "forward_demo", "broker");
      }

      for(int i = 0; i < n; i++)
      {
         FileWrite(c, m[i].name, m[i].unit, DoubleToString(m[i].value, 2), "", "");
      }

      FileFlush(c);
      FileClose(c);
   }
}

//==================================================
// SUMMARY (para log / dashboard)
//==================================================
string QuantSummary()
{
   QuantMetric m[11];
   int n = QuantBuildMatrix(m, 11);

   string s = "=== QUANT MATRIX ===\n";
   for(int i = 0; i < n; i++)
   {
      s += StringFormat("  %-18s %-10s %s\n",
         m[i].name, DoubleToString(m[i].value, 2), m[i].unit);
   }
   return s;
}

#endif // QUANT_VALIDATOR_MQH
