//+------------------------------------------------------------------+
//|                                            ExecutionQuality.mqh |
//|                                  Smart Execution Engine - Quality|
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+

#ifndef EXECUTION_QUALITY_MQH
#define EXECUTION_QUALITY_MQH

//+------------------------------------------------------------------+
//| Execution Quality Score                                          |
//+------------------------------------------------------------------+
struct QualityScore
{
   double score;           // 0-100
   double slippage_pips;   // Slippage em pips
   int    delay_ms;        // Delay em ms
   double price_expected;  // Preço esperado
   double price_executed;  // Preço executado
};

class CExecutionQuality
{
private:
   static QualityScore m_last_score;
   static double       m_avg_slippage;
   static double       m_avg_delay;
   static int          m_samples;
   
public:
   static void Init();
   static QualityScore CalculateScore(double expected_price, double executed_price, int delay_ms);
   static QualityScore GetLastScore();
   static double GetAverageSlippage();
   static double GetAverageDelay();
   static void LogScore(const QualityScore &score);
   static string GetQualityGrade(double score);
};

QualityScore CExecutionQuality::m_last_score;
double CExecutionQuality::m_avg_slippage = 0;
double CExecutionQuality::m_avg_delay = 0;
int CExecutionQuality::m_samples = 0;

void CExecutionQuality::Init()
{
   Print("[QUALITY] ExecutionQuality initialized");
}

QualityScore CExecutionQuality::CalculateScore(double expected_price, double executed_price, int delay_ms)
{
   QualityScore score;
   score.price_expected = expected_price;
   score.price_executed = executed_price;
   score.delay_ms = delay_ms;
   
   // Calcula slippage em pips
   double point = SymbolInfoDouble(Symbol(), SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(Symbol(), SYMBOL_DIGITS);
   double pip = (digits == 3 || digits == 5) ? point * 10 : point;
   
   score.slippage_pips = MathAbs(executed_price - expected_price) / pip;
   
   // Calcula score (0-100)
   double slippage_penalty = MathMin(score.slippage_pips * 5, 50); // Até 50 pontos de penalidade
   double delay_penalty = MathMin(delay_ms / 100.0, 30);           // Até 30 pontos de penalidade
   double requote_penalty = 0;
   
   if(score.slippage_pips > 10) requote_penalty = 20; // Penalidade extra para slippage alto
   
   score.score = MathMax(0, 100 - slippage_penalty - delay_penalty - requote_penalty);
   
   // Atualiza médias
   m_avg_slippage = (m_avg_slippage * m_samples + score.slippage_pips) / (m_samples + 1);
   m_avg_delay = (m_avg_delay * m_samples + delay_ms) / (m_samples + 1);
   m_samples++;
   
   m_last_score = score;
   return score;
}

QualityScore CExecutionQuality::GetLastScore() { return m_last_score; }
double CExecutionQuality::GetAverageSlippage() { return m_avg_slippage; }
double CExecutionQuality::GetAverageDelay() { return m_avg_delay; }

void CExecutionQuality::LogScore(const QualityScore &score)
{
   PrintFormat("[QUALITY] Score: %.1f (%s) | Slippage: %.2f pips | Delay: %dms",
               score.score, GetQualityGrade(score.score), score.slippage_pips, score.delay_ms);
}

string CExecutionQuality::GetQualityGrade(double score)
{
   if(score >= 90) return "EXCELLENT";
   if(score >= 80) return "GOOD";
   if(score >= 70) return "FAIR";
   if(score >= 60) return "POOR";
   return "BAD";
}

#endif // EXECUTION_QUALITY_MQH