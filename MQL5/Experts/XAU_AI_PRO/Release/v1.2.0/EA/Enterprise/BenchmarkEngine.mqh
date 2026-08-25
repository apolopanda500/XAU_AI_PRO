//+------------------------------------------------------------------+
//|                                               BenchmarkEngine.mqh |
//|                                  Strategy Benchmark System        |
//|                                            XAU_AI_PRO v1.2.0      |
//|                                            ETAPA 8 - v2.0         |
//+------------------------------------------------------------------+
// BenchmarkEngine compara o desempenho de estrategias (Technical,
// AI, Hybrid, Ensemble) em tempo real, acumulando metricas por
// trade fechado e elegendo a melhor estrategia.
//
// v2.0 (ETAPA 8): correcoes e metricas completas
//  - win_rate agora e percentual real de vitorias (wins/trades*100)
//  - profit_factor = gross_profit / gross_loss (com protecao div/0)
//  - max_dd rastreado pela equity acumulada ($ e %)
//  - sharpe calculado a partir dos retornos por trade
//  - expectancy (lucro medio por trade) e avg R multiple
//  - RecordTrade usa sl/tp (risco) para o R multiple
//  - sem referencias C++ (MQL5 nao suporta '&r')
//+------------------------------------------------------------------+

#ifndef BENCHMARK_ENGINE_MQH
#define BENCHMARK_ENGINE_MQH

#define BENCHMARK_MAX_TRADES 10000

enum StrategyType { STRATEGY_TECHNICAL, STRATEGY_AI, STRATEGY_HYBRID, STRATEGY_ENSEMBLE };

struct StrategyResult
{
   StrategyType type;
   int          trades;
   int          wins;
   int          losses;
   double       profit;
   double       gross_profit;
   double       gross_loss;
   double       win_rate;
   double       profit_factor;
   double       max_dd;
   double       max_dd_pct;
   double       sharpe;
   double       expectancy;
   double       sum_r_multiple;
   double       avg_r_multiple;
   datetime     last_trade;
};

class CBenchmarkEngine
{
private:
   static StrategyResult m_strategies[4];
   static int            m_strategy_count;
   static bool           m_initialized;
   static int            m_benchmark_period_days;
   static StrategyType   m_best_strategy;
   static double         m_returns[4][BENCHMARK_MAX_TRADES];
   static int            m_return_count[4];
   static double         m_equity[4];
   static double         m_equity_peak[4];
   static double CalcSharpe(int idx);
   static void   EvaluateStrategies();
public:
   static void Init();
   static void RecordTrade(StrategyType type, double profit, double sl, double tp);
   static StrategyType GetBestStrategy();
   static string GetBestStrategyName();
   static double GetStrategyWinRate(StrategyType type);
   static double GetStrategyProfit(StrategyType type);
   static double GetStrategyProfitFactor(StrategyType type);
   static double GetStrategyMaxDD(StrategyType type);
   static double GetStrategySharpe(StrategyType type);
   static string GetComparisonSummary();
   static void LogComparison();
};

//--------------------------------------------------
// DEFINICOES ESTATICAS
//--------------------------------------------------

StrategyResult CBenchmarkEngine::m_strategies[4];
int            CBenchmarkEngine::m_strategy_count = 0;
bool           CBenchmarkEngine::m_initialized = false;
int            CBenchmarkEngine::m_benchmark_period_days = 30;
StrategyType   CBenchmarkEngine::m_best_strategy = STRATEGY_TECHNICAL;
double         CBenchmarkEngine::m_returns[4][BENCHMARK_MAX_TRADES];
int            CBenchmarkEngine::m_return_count[4];
double         CBenchmarkEngine::m_equity[4];
double         CBenchmarkEngine::m_equity_peak[4];

//--------------------------------------------------
// INIT
//--------------------------------------------------

void CBenchmarkEngine::Init()
{
   if(m_initialized)
      return;

   m_strategy_count = 4;

   for(int i = 0; i < m_strategy_count; i++)
   {
      m_strategies[i].type           = (StrategyType)i;
      m_strategies[i].trades         = 0;
      m_strategies[i].wins           = 0;
      m_strategies[i].losses         = 0;
      m_strategies[i].profit         = 0.0;
      m_strategies[i].gross_profit   = 0.0;
      m_strategies[i].gross_loss     = 0.0;
      m_strategies[i].win_rate       = 0.0;
      m_strategies[i].profit_factor  = 0.0;
      m_strategies[i].max_dd         = 0.0;
      m_strategies[i].max_dd_pct     = 0.0;
      m_strategies[i].sharpe         = 0.0;
      m_strategies[i].expectancy     = 0.0;
      m_strategies[i].sum_r_multiple = 0.0;
      m_strategies[i].avg_r_multiple = 0.0;
      m_strategies[i].last_trade     = 0;

      m_return_count[i] = 0;
      m_equity[i]       = 0.0;
      m_equity_peak[i]  = 0.0;
   }

   ArrayInitialize(m_returns, 0.0);

   m_best_strategy = STRATEGY_TECHNICAL;
   m_initialized   = true;

   Print("[BENCHMARK] BenchmarkEngine inicializado (4 estrategias)");
}

//--------------------------------------------------
// RECORD TRADE
//--------------------------------------------------

void CBenchmarkEngine::RecordTrade(StrategyType type, double profit, double sl, double tp)
{
   if(!m_initialized)
      Init();

   if(type < 0 || type >= m_strategy_count)
      return;

   int idx = (int)type;

   m_strategies[idx].trades++;
   m_strategies[idx].profit     += profit;
   m_strategies[idx].last_trade  = TimeCurrent();

   if(profit > 0.0)
   {
      m_strategies[idx].wins++;
      m_strategies[idx].gross_profit += profit;
   }
   else if(profit < 0.0)
   {
      m_strategies[idx].losses++;
      m_strategies[idx].gross_loss += -profit;
   }

   // Win rate percentual real
   if(m_strategies[idx].trades > 0)
      m_strategies[idx].win_rate = (m_strategies[idx].wins * 100.0) / m_strategies[idx].trades;

   // Profit factor (protecao contra divisao por zero)
   if(m_strategies[idx].gross_loss > 0.0)
      m_strategies[idx].profit_factor = m_strategies[idx].gross_profit / m_strategies[idx].gross_loss;
   else if(m_strategies[idx].gross_profit > 0.0)
      m_strategies[idx].profit_factor = 999.0;   // sem perdas: PF ilimitado (cap exibicao)
   else
      m_strategies[idx].profit_factor = 0.0;

   // Expectancy (lucro medio por trade)
   if(m_strategies[idx].trades > 0)
      m_strategies[idx].expectancy = m_strategies[idx].profit / m_strategies[idx].trades;

   // R multiple: profit / risco (sl em valor monetario)
   if(sl > 0.0)
   {
      double risk = MathAbs(sl);
      if(risk > 0.0)
      {
         double rMult = profit / risk;
         m_strategies[idx].sum_r_multiple += rMult;
         if(m_strategies[idx].trades > 0)
            m_strategies[idx].avg_r_multiple = m_strategies[idx].sum_r_multiple / m_strategies[idx].trades;
      }
   }

   // Equity acumulada + drawdown
   m_equity[idx] += profit;
   if(m_equity[idx] > m_equity_peak[idx])
      m_equity_peak[idx] = m_equity[idx];

   double dd = m_equity_peak[idx] - m_equity[idx];
   if(dd > m_strategies[idx].max_dd)
   {
      m_strategies[idx].max_dd = dd;
      if(m_equity_peak[idx] > 0.0)
         m_strategies[idx].max_dd_pct = (dd / m_equity_peak[idx]) * 100.0;
   }

   // Retorno por trade (para sharpe)
   if(m_return_count[idx] < BENCHMARK_MAX_TRADES)
   {
      m_returns[idx][m_return_count[idx]] = profit;
      m_return_count[idx]++;
   }

   // Sharpe incremental (recalcula quando houver >= 2 trades)
   if(m_return_count[idx] >= 2)
      m_strategies[idx].sharpe = CalcSharpe(idx);

   EvaluateStrategies();
}

//--------------------------------------------------
// CALC SHARPE
//--------------------------------------------------

double CBenchmarkEngine::CalcSharpe(int idx)
{
   int n = m_return_count[idx];
   if(n < 2)
      return 0.0;

   double sum = 0.0;
   for(int i = 0; i < n; i++)
      sum += m_returns[idx][i];

   double mean = sum / n;

   double var = 0.0;
   for(int i = 0; i < n; i++)
   {
      double d = m_returns[idx][i] - mean;
      var += d * d;
   }

   if(n > 1)
      var /= (n - 1);

   if(var <= 0.0)
      return 0.0;

   double std = MathSqrt(var);
   if(std == 0.0)
      return 0.0;

   // Sharpe por trade (anualizacao aproximada: sqrt(n))
   return NormalizeDouble(mean / std * MathSqrt(n), 2);
}

//--------------------------------------------------
// EVALUATE STRATEGIES
//--------------------------------------------------

void CBenchmarkEngine::EvaluateStrategies()
{
   double best_score = -999999.0;
   bool   found      = false;

   for(int i = 0; i < m_strategy_count; i++)
   {
      // Estrategia sem trades nao concorre
      if(m_strategies[i].trades == 0)
         continue;

      double score = m_strategies[i].profit;

      if(score > best_score)
      {
         best_score = score;
         m_best_strategy = (StrategyType)i;
         found = true;
      }
   }

   // Se nenhuma estrategia tem trades, mantem a padrao
   if(!found)
      m_best_strategy = STRATEGY_TECHNICAL;
}

//--------------------------------------------------
// GETTERS
//--------------------------------------------------

StrategyType CBenchmarkEngine::GetBestStrategy()
{
   return m_best_strategy;
}

string CBenchmarkEngine::GetBestStrategyName()
{
   switch(m_best_strategy)
   {
      case STRATEGY_TECHNICAL: return "Technical";
      case STRATEGY_AI:        return "AI";
      case STRATEGY_HYBRID:    return "Hybrid";
      case STRATEGY_ENSEMBLE:  return "Ensemble";
      default:                 return "Unknown";
   }
}

double CBenchmarkEngine::GetStrategyWinRate(StrategyType type)
{
   if(type >= 0 && type < m_strategy_count)
      return m_strategies[(int)type].win_rate;
   return 0.0;
}

double CBenchmarkEngine::GetStrategyProfit(StrategyType type)
{
   if(type >= 0 && type < m_strategy_count)
      return m_strategies[(int)type].profit;
   return 0.0;
}

double CBenchmarkEngine::GetStrategyProfitFactor(StrategyType type)
{
   if(type >= 0 && type < m_strategy_count)
      return m_strategies[(int)type].profit_factor;
   return 0.0;
}

double CBenchmarkEngine::GetStrategyMaxDD(StrategyType type)
{
   if(type >= 0 && type < m_strategy_count)
      return m_strategies[(int)type].max_dd;
   return 0.0;
}

double CBenchmarkEngine::GetStrategySharpe(StrategyType type)
{
   if(type >= 0 && type < m_strategy_count)
      return m_strategies[(int)type].sharpe;
   return 0.0;
}

//--------------------------------------------------
// COMPARISON SUMMARY
//--------------------------------------------------

string CBenchmarkEngine::GetComparisonSummary()
{
   string s = "=== BENCHMARK DE ESTRATEGIAS ===\n";
   string names[] = {"Technical", "AI", "Hybrid", "Ensemble"};

   s += StringFormat("  %-10s %6s %5s %5s %9s %8s %9s %8s %8s %8s\n",
      "Estrategia", "Trades", "Wins", "Loss", "Profit", "WinRate", "PF", "MaxDD%", "Sharpe", "Expect");

   for(int i = 0; i < m_strategy_count; i++)
   {
      string best = (i == (int)m_best_strategy) ? " *BEST*" : "";

      s += StringFormat("  %-10s %6d %5d %5d %9.2f %7.1f%% %8.2f %7.2f%% %8.2f %8.2f%s\n",
         names[i],
         m_strategies[i].trades,
         m_strategies[i].wins,
         m_strategies[i].losses,
         m_strategies[i].profit,
         m_strategies[i].win_rate,
         m_strategies[i].profit_factor,
         m_strategies[i].max_dd_pct,
         m_strategies[i].sharpe,
         m_strategies[i].expectancy,
         best);
   }

   s += StringFormat("\nMelhor estrategia: %s (profit=%.2f)",
      GetBestStrategyName(), GetStrategyProfit(m_best_strategy));

   return s;
}

void CBenchmarkEngine::LogComparison()
{
   string summary = GetComparisonSummary();
   Print("[BENCHMARK] " + summary);

   // Grava resumo em arquivo (FILE_COMMON) para validacao observavel
   int h = FileOpen("BenchmarkReport.txt", FILE_COMMON | FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      FileSeek(h, 0, SEEK_END);
      FileWrite(h, "===== " + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + " =====");
      FileWrite(h, summary);
      FileClose(h);
   }
}

#endif // BENCHMARK_ENGINE_MQH
