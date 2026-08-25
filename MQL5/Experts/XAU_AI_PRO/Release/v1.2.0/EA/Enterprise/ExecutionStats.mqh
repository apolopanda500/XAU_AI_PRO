// XAU_AI_PRO v1.2.0
#ifndef EXECUTION_STATS_MQH
#define EXECUTION_STATS_MQH

struct ExecStats
{
   int    total_orders;
   int    executed;
   int    rejected;
   int    requotes;
   int    timeouts;

   double avg_slippage;
   double avg_delay_ms;

   double best_score;
   double worst_score;
   double avg_score;
};

class CExecutionStats
{
private:

   static ExecStats m_stats;

   static double m_total_slippage;
   static double m_total_score;
   static double m_total_delay;

public:

   static void Init();
   static void RecordOrder(bool success,
                           uint error_code,
                           double slippage_pips,
                           int delay_ms,
                           double score);

   static void UpdateAfterTrade(double profit);

   static ExecStats GetStats();

   static void Reset();

   static string GetSummary();

   static void LogStats();
};

ExecStats CExecutionStats::m_stats;

double CExecutionStats::m_total_slippage=0;
double CExecutionStats::m_total_score=0;
double CExecutionStats::m_total_delay=0;


//==================================================

void CExecutionStats::Init()
{
   ZeroMemory(m_stats);

   m_total_slippage=0;
   m_total_score=0;
   m_total_delay=0;

   m_stats.best_score=-DBL_MAX;
   m_stats.worst_score= DBL_MAX;

   Print("[STATS] ExecutionStats initialized");
}


//==================================================

void CExecutionStats::RecordOrder(
      bool success,
      uint error_code,
      double slippage_pips,
      int delay_ms,
      double score)
{
   m_stats.total_orders++;

   if(success)
   {
      m_stats.executed++;

      m_total_slippage+=slippage_pips;
      m_total_score+=score;
      m_total_delay+=delay_ms;

      if(score>m_stats.best_score)
         m_stats.best_score=score;

      if(score<m_stats.worst_score)
         m_stats.worst_score=score;

      m_stats.avg_slippage=
         m_total_slippage/
         m_stats.executed;

      m_stats.avg_delay_ms=
         m_total_delay/
         m_stats.executed;
   }
   else
   {
      m_stats.rejected++;

      if(error_code==TRADE_RETCODE_REQUOTE)
         m_stats.requotes++;

      if(error_code==TRADE_RETCODE_TIMEOUT)
         m_stats.timeouts++;
   }
}


//==================================================

void CExecutionStats::UpdateAfterTrade(double profit)
{
   m_total_score+=profit;
}


//==================================================

ExecStats CExecutionStats::GetStats()
{
   return m_stats;
}


//==================================================

void CExecutionStats::Reset()
{
   ZeroMemory(m_stats);

   m_total_slippage=0;
   m_total_score=0;
   m_total_delay=0;

   m_stats.best_score=-DBL_MAX;
   m_stats.worst_score= DBL_MAX;
}


//==================================================

string CExecutionStats::GetSummary()
{
   // Sem execuções: evita exibir os valores sentinela ±DBL_MAX
   double best = 0.0;
   double worst = 0.0;
   if(m_stats.executed > 0)
   {
      best  = m_stats.best_score;
      worst = m_stats.worst_score;
   }

   return StringFormat(
      "Orders=%d | Exec=%d | Reject=%d | Requotes=%d | AvgSlip=%.2f | AvgDelay=%.1f ms | AvgScore=%.2f | Best=%.2f | Worst=%.2f",
      m_stats.total_orders,
      m_stats.executed,
      m_stats.rejected,
      m_stats.requotes,
      m_stats.avg_slippage,
      m_stats.avg_delay_ms,
      m_stats.avg_score,
      best,
      worst
   );
}


//==================================================

void CExecutionStats::LogStats()
{
   Print("[STATS] ",GetSummary());
}

#endif
