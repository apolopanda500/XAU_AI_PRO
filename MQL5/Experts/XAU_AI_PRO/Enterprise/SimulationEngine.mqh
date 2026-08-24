//+------------------------------------------------------------------+
//|                                             SimulationEngine.mqh |
//|                                  Pre-Execution Simulation        |
//|                                            XAU_AI_PRO v1.2.1     |
//+------------------------------------------------------------------+

#ifndef SIMULATION_ENGINE_MQH
#define SIMULATION_ENGINE_MQH

#include "../Core/Config.mqh"

struct SimulationResult
{
   bool   should_execute;
   double probability_success;
   double expected_profit;
   double risk_reward;
   double max_adverse_excursion;
   double max_favorable_excursion;
   string reason;
};

class CSimulationEngine
{
private:
   static int             m_simulation_count;
   static int             m_approved_count;
   static int             m_rejected_count;
   static bool            m_initialized;
   static double          m_min_probability;
   static double          m_min_expected_profit;
   static double          m_max_risk;
   static SimulationResult SimulateTrade(string symbol, int type, double volume, double entry, double sl, double tp);
public:
   static void Init();
   static SimulationResult Evaluate(string symbol, int type, double volume, double entry, double sl, double tp);
   static bool ShouldExecute(SimulationResult &result);
   static void SetThresholds(double min_prob, double min_profit, double max_risk);
   static int GetSimulationCount();
   static int GetApprovedCount();
   static int GetRejectedCount();
   static double GetApprovalRate();
   static string GetSummary();
   static void LogSummary();
};

int CSimulationEngine::m_simulation_count = 0;
int CSimulationEngine::m_approved_count = 0;
int CSimulationEngine::m_rejected_count = 0;
bool CSimulationEngine::m_initialized = false;
// v1.2.1: thresholds em unidades de RISCO (R), independentes do simbolo.
double CSimulationEngine::m_min_probability = 0.5;
double CSimulationEngine::m_min_expected_profit = 0.05;
double CSimulationEngine::m_max_risk = 2.0;

void CSimulationEngine::Init()
{
   if(m_initialized) return;
   m_initialized = true;
   Print("[SIMULATION] SimulationEngine initialized");
}

SimulationResult CSimulationEngine::SimulateTrade(string symbol, int type, double volume, double entry, double sl, double tp)
{
   SimulationResult result;

   // Calculate risk/reward
   double risk = MathAbs(entry - sl);
   double reward = MathAbs(tp - entry);
   result.risk_reward = (risk > 0) ? reward / risk : 0;

   // Historical win rate for similar setups (simplified)
   result.probability_success = 0.5 + (result.risk_reward * 0.1); // Base probability
   if(result.probability_success > 0.95) result.probability_success = 0.95;

   // v1.2.1 FIX: expected profit normalizado em unidades de RISCO (R):
   // EP_R = prob*RR - (1-prob). Independe do point/preco do simbolo.
   // Antes (v1.2.0) o EP era calculado em preco absoluto e comparado
   // com 0.5, o que bloqueava SEMPRE pares FX (point 0.00001) com
   // "Low expected profit" (EP ~0.003). Corrigido em v1.2.1.
   result.expected_profit =
      (result.probability_success * result.risk_reward) -
      (1.0 - result.probability_success);

   // Max adverse/favorable excursion (simplified)
   result.max_adverse_excursion = risk * 1.5;
   result.max_favorable_excursion = reward * 1.2;

   // Decision - thresholds em unidades de R (nao preco absoluto)
   result.should_execute = (result.probability_success >= m_min_probability &&
                           result.expected_profit >= m_min_expected_profit &&
                           result.risk_reward >= 1.0);

   result.reason = result.should_execute ? "All criteria met" :
                  (result.probability_success < m_min_probability ? "Low probability" :
                  result.expected_profit < m_min_expected_profit ? "Low expected profit" : "Poor risk/reward");

   return result;
}

SimulationResult CSimulationEngine::Evaluate(string symbol, int type, double volume, double entry, double sl, double tp)
{
   if(!m_initialized) Init();
   m_simulation_count++;

   SimulationResult result = SimulateTrade(symbol, type, volume, entry, sl, tp);

   if(result.should_execute) m_approved_count++; else m_rejected_count++;

   return result;
}

bool CSimulationEngine::ShouldExecute(SimulationResult &result)
{
   return result.should_execute;
}

void CSimulationEngine::SetThresholds(double min_prob, double min_profit, double max_risk)
{
   m_min_probability = min_prob;
   m_min_expected_profit = min_profit;
   m_max_risk = max_risk;
}

int CSimulationEngine::GetSimulationCount() { return m_simulation_count; }
int CSimulationEngine::GetApprovedCount() { return m_approved_count; }
int CSimulationEngine::GetRejectedCount() { return m_rejected_count; }

double CSimulationEngine::GetApprovalRate()
{
   return (m_simulation_count > 0) ? (double)m_approved_count / m_simulation_count * 100 : 0;
}

string CSimulationEngine::GetSummary()
{
   return StringFormat("Simulations: %d | Approved: %d | Rejected: %d | Approval Rate: %.1f%%",
      m_simulation_count, m_approved_count, m_rejected_count, GetApprovalRate());
}

void CSimulationEngine::LogSummary() { Print("[SIMULATION] " + GetSummary()); }

#endif // SIMULATION_ENGINE_MQH
