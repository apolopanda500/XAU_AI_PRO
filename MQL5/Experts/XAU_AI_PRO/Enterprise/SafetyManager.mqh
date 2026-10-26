//+------------------------------------------------------------------+
//|                                              SafetyManager.mqh   |
//|                                  Safety Management System        |
//|                                            XAU_AI_PRO v1.2.9       |
//+------------------------------------------------------------------+

#ifndef SAFETY_MANAGER_MQH
#define SAFETY_MANAGER_MQH

#include "../Core/Config.mqh"
#include "../Core/RiskHub.mqh"

//==================================================
// SAFETY LIMITS
//==================================================

struct SafetyLimits
{
   double max_daily_loss;
   double max_daily_drawdown;
   int    max_trades_per_day;
   double max_total_exposure;
   double min_free_margin;
   double max_risk_per_symbol;
   double max_risk_per_session;
};

//==================================================
// SAFETY MANAGER
//==================================================

class CSafetyManager
{
private:

   static SafetyLimits m_limits;
   static bool         m_initialized;

   static double       m_daily_profit;
   static double       m_daily_peak_equity;
   static double       m_session_profit;
   static double       m_daily_start_balance;
   static int          m_last_day_key;

public:

   static void Init();

   static void SetLimits(
      double daily_loss,
      double daily_dd,
      int    max_trades,
      double exposure,
      double margin,
      double risk_symbol,
      double risk_session
   );

   static bool CheckAll();

   static bool CheckDailyLoss();
   static bool CheckDailyDrawdown();
   static bool CheckDailyTrades();
   static bool CheckTotalExposure();
   static bool CheckFreeMargin();
   static bool CheckRiskPerSymbol();
   static bool CheckRiskPerSession();

   static void UpdateStats();


    static void RegisterTrade();
    static int GetDailyTrades();

   // MEDIDA UNICA do limite diario. O gate (`CheckDailyDrawdown`) e a tela
   // (`GetSafetySummary`) consomem ESTA funcao. Se cada um calculasse a
   // sua propria, a tela passaria a mostrar um numero que o gate nao usa,
   // e o operador leria a trava errada -- o mesmo defeito do §5 do AGENTS.md
   // So uma definicao, dois consumidores.
   static double GetDailyLossPercent(double &perda, double &base);

   static string GetSafetySummary();

   static void LogSafety();
};

//==================================================
// STATIC VARIABLES
//==================================================

SafetyLimits CSafetyManager::m_limits;

bool CSafetyManager::m_initialized = false;

double CSafetyManager::m_daily_profit = 0.0;

double CSafetyManager::m_daily_peak_equity = 0.0;
double CSafetyManager::m_session_profit = 0.0;

double CSafetyManager::m_daily_start_balance = 0.0;

int CSafetyManager::m_last_day_key = -1;

//==================================================
// DAY KEY
//==================================================

int SafetyDayKey()
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

//==================================================
// INIT
//==================================================

void CSafetyManager::Init()
{
   if(m_initialized)
      return;

   double balance =
      AccountInfoDouble(
         ACCOUNT_BALANCE
      );

   if(balance <= 0.0)
      balance = 0.0;

   //------------------------------------------------
   // Limites derivados do CONFIG
   //------------------------------------------------

   m_limits.max_daily_loss =
      balance *
      MaxDailyLossPercent /
      100.0;

   m_limits.max_daily_drawdown =
      MaxDailyLossPercent;

   m_limits.max_trades_per_day =
      MaxTradesPerDay;

   m_limits.max_total_exposure =
      10.0;

   m_limits.min_free_margin =
      MinFreeMargin;

   m_limits.max_risk_per_symbol =
      2.0;

   m_limits.max_risk_per_session =
      5.0;

   //------------------------------------------------
   // Estado diário
   //------------------------------------------------

   m_daily_profit = 0.0;

   // v1.3.0 (Etapa 3): contadores diarios persistentes via RiskHub.
   RiskHubNewDay();

   m_daily_start_balance =
      RiskHubGet("STARTBAL", balance);

   RiskHubSet("STARTBAL", m_daily_start_balance);

   m_daily_peak_equity = GetDailyPeakEquity();

   m_session_profit = 0.0;

   m_last_day_key =
      SafetyDayKey();

   m_initialized = true;

   Print(
      "[SAFETY] SafetyManager initialized | ",
      "DailyLoss=",
      DoubleToString(
         m_limits.max_daily_loss,
         2
      ),
      " | DailyDD=",
      DoubleToString(
         m_limits.max_daily_drawdown,
         2
      ),
      "% | MaxTrades=",
      IntegerToString(
         m_limits.max_trades_per_day
      ),
      " | MinMargin=",
      DoubleToString(
         m_limits.min_free_margin,
         2
      )
   );
}

//==================================================
// SET LIMITS
//==================================================

void CSafetyManager::SetLimits(
   double daily_loss,
   double daily_dd,
   int    max_trades,
   double exposure,
   double margin,
   double risk_symbol,
   double risk_session
)
{
   m_limits.max_daily_loss =
      MathMax(
         0.0,
         daily_loss
      );

   m_limits.max_daily_drawdown =
      MathMax(
         0.0,
         daily_dd
      );

   m_limits.max_trades_per_day =
      MathMax(
         0,
         max_trades
      );

   m_limits.max_total_exposure =
      MathMax(
         0.0,
         exposure
      );

   m_limits.min_free_margin =
      MathMax(
         0.0,
         margin
      );

   m_limits.max_risk_per_symbol =
      MathMax(
         0.0,
         risk_symbol
      );

   m_limits.max_risk_per_session =
      MathMax(
         0.0,
         risk_session
      );
}

//==================================================
// CHECK ALL
//==================================================

bool CSafetyManager::CheckAll()
{
   if(!m_initialized)
      Init();

   UpdateStats();

   if(!CheckDailyLoss())
      return false;

   if(!CheckDailyDrawdown())
      return false;

   if(!CheckDailyTrades())
      return false;

   if(!CheckTotalExposure())
      return false;

   if(!CheckFreeMargin())
      return false;

   if(!CheckRiskPerSymbol())
      return false;

   if(!CheckRiskPerSession())
      return false;

   return true;
}

//==================================================
// DAILY LOSS
//==================================================

bool CSafetyManager::CheckDailyLoss()
{
   if(m_limits.max_daily_loss <= 0.0)
      return true;

   if(m_daily_profit < 0.0)
   {
      double loss =
         MathAbs(
            m_daily_profit
         );

      if(loss >= m_limits.max_daily_loss)
      {
         PrintFormat(
            "[SAFETY] Daily loss limit: %.2f/%.2f",
            loss,
            m_limits.max_daily_loss
         );

         return false;
      }
   }

   return true;
}

//==================================================
// DAILY DRAWDOWN
//==================================================

bool CSafetyManager::CheckDailyDrawdown()
{
   double equity =
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );

   if(equity <= 0.0)
      return true;

   if(m_daily_peak_equity <= 0.0)
   {
      m_daily_peak_equity =
         equity;

      return true;
   }

   //==================================================
   // PERDA DIARIA = PERDA REALIZADA (decisao do dono, 08/10/2026)
   //==================================================
   // MEDIDO na conta 391773676, conta REAL, com o AUTO ligado:
   //
   //   P/L: -0.16 | Trades: 1/20 | DD: 5.63%/5.00%
   //   [TRADE BLOCK] SAFETY | DD: 5.63%/5.00%
   //
   // A conta tinha perdido $0,16 no dia. O bloqueio dizia 5,63%.
   //
   // O 5,63% vinha de `GetDrawdownPercent()`, que e AMPLITUDE de patrimonio:
   // (pico - agora) / pico. E o pico era 21,32, de 08/10 23:47:53 UTC, com a
   // posicao USDCAD recem-aberta lucando $6,90 de flutuante sobre um balance
   // de $14,42. Ou seja: o sistema contou a IDA E A VOLTA de uma posicao como
   // "perda diaria", sem a conta ter perdido dinheiro.
   //
   // `MaxDailyLossPercent` diz LOSS. O que era entregue era DRAWDOWN. Sao dois
   // numeros com nomes diferentes e o `AGENTS.md` §5 na forma mais limpa: o
   // nome do limite e uma medida, o codigo entrega outra, e quem decide quem
   // opera e o codigo.
   //
   // AGORA: o numerador e o realizado do dia (`m_daily_profit`, que ja e
   // persistido e reiniciado no virada do dia em :542), e o denominador e o
   // SALDO do inicio do dia (`m_daily_start_balance`, persistido como
   // `STARTBAL` em :171). Saldo, e nao patrimonio: patrimonio muda a cada
   // tique, e um limite que muda sozinho nao e um limite.
   //
   // `GetDrawdownPercent()` NAO foi mexido e continua servindo a quem mede
   // amplitude de verdade — `RiskCenter`, `RiskEngine`, `Telemetry`,
   // `CircuitBreaker`. Um numero que e certo para uma coisa e errado para
   // outra nao e defeito da formula; e a formula certa no lugar errado.
   //
   // MEDIDO com o numero real: perda 0,16 sobre saldo inicial ~15,30 = 1,05%,
   // contra o limite de 5,00%. Passa com 4,8x de folga, que e o que a tela
   // mostrava no P/L e nao mostrava no DD.
   double perdaDoDia = 0.0;
   double base = 0.0;
   double dd = GetDailyLossPercent(perdaDoDia, base);

   if(dd >= m_limits.max_daily_drawdown)
   {
      PrintFormat(
         "[SAFETY] Daily loss limit: %.2f%%/%.2f%% (realizado %.2f de %.2f)",
         dd,
         m_limits.max_daily_drawdown,
         perdaDoDia,
         base
      );

      return false;
   }

   return true;
}

//==================================================
// DAILY TRADES
//==================================================

bool CSafetyManager::CheckDailyTrades()
{
   if(m_limits.max_trades_per_day <= 0)
      return true;

   int tradesToday = GetEffectiveDailyTradesCount();

   if(tradesToday >=
      m_limits.max_trades_per_day)
   {
      PrintFormat(
         "[SAFETY] Daily trades limit: %d/%d",
         tradesToday,
         m_limits.max_trades_per_day
      );

      return false;
   }

   return true;
}

//==================================================
// TOTAL EXPOSURE
//==================================================

bool CSafetyManager::CheckTotalExposure()
{
   double balance =
      AccountInfoDouble(
         ACCOUNT_BALANCE
      );

   if(balance <= 0.0)
      return true;

   double floatingProfit = 0.0;

   int total =
      PositionsTotal();

   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if(!PositionSelectByTicket(ticket))
         continue;

      long magic =
         PositionGetInteger(
            POSITION_MAGIC
         );

      if(magic != MagicNumber)
         continue;

      floatingProfit +=
         PositionGetDouble(
            POSITION_PROFIT
         );
   }

   double exposurePct =
      MathAbs(
         floatingProfit
      )
      /
      balance
      *
      100.0;

   if(exposurePct >=
      m_limits.max_total_exposure)
   {
      PrintFormat(
         "[SAFETY] Exposure limit: %.2f%%/%.2f%%",
         exposurePct,
         m_limits.max_total_exposure
      );

      return false;
   }

   return true;
}

//==================================================
// FREE MARGIN
//==================================================

bool CSafetyManager::CheckFreeMargin()
{
   double freeMargin =
      AccountInfoDouble(
         ACCOUNT_MARGIN_FREE
      );

   if(freeMargin <= 0.0)
   {
      Print(
         "[SAFETY] Free margin unavailable"
      );

      return false;
   }

   if(freeMargin <
      m_limits.min_free_margin)
   {
      PrintFormat(
         "[SAFETY] Free margin low: %.2f/%.2f",
         freeMargin,
         m_limits.min_free_margin
      );

      return false;
   }

   return true;
}

//==================================================
// RISK PER SYMBOL
//==================================================

bool CSafetyManager::CheckRiskPerSymbol()
{
   // Reservado para integração
   // com RiskManager / PositionManager.

   return true;
}

//==================================================
// RISK PER SESSION
//==================================================

bool CSafetyManager::CheckRiskPerSession()
{
   // Reservado para integração
   // com SessionFilter / RiskManager.

   return true;
}

//==================================================
// UPDATE STATS
//==================================================

void CSafetyManager::UpdateStats()
{
   if(!m_initialized)
      return;

   int currentDay =
      SafetyDayKey();

   //------------------------------------------------
   // Novo dia
   //------------------------------------------------

   if(currentDay !=
      m_last_day_key)
   {
      m_daily_profit = 0.0;

      // v1.3.0 (Etapa 3): RiskHub detecta novo dia e persiste
      RiskHubNewDay();

      m_daily_start_balance =
         RiskHubGet("STARTBAL", AccountInfoDouble(ACCOUNT_BALANCE));

      RiskHubSet("STARTBAL", m_daily_start_balance);

      m_daily_peak_equity =
         GetDailyPeakEquity();

      m_session_profit = 0.0;

      m_last_day_key =
         currentDay;

      Print(
         "[SAFETY] Daily statistics reset"
      );
   }

   //------------------------------------------------
   // Atualiza peak equity
   //------------------------------------------------

   // v1.3.0 (Etapa 3): peak persistente via RiskHub
   m_daily_peak_equity =
      GetDailyPeakEquity();

   //------------------------------------------------
   // P/L diário baseado no balance
   //------------------------------------------------

   double balance =
      AccountInfoDouble(
         ACCOUNT_BALANCE
      );

   if(m_daily_start_balance > 0.0)
   {
      m_daily_profit =
         balance -
         m_daily_start_balance;
   }
}

//==================================================
// MEDIDA UNICA DA PERDA DIARIA
//==================================================
// Definicao unica. O gate e a tela consomem ISTE numero.
//
// MEDIDO 08/10/2026, conta 391773676: depois de corrigir o gate, a tela ainda
// imprimia `DD: 5.02%/5.00%` com perda realizada de 0,16. O gate ja nao usava
// aquele numero, mas a tela usava `GetDrawdownPercent()`. O operador lia
// 5,02% e concluia que a trava era o DD, quando a trava era a margem livre.
// Duas leituras do mesmo limite divergindo: e o §5 do AGENTS.md de novo, so que
// agora entre duas linhas do mesmo arquivo.
//
// Por isso a formula mora AQUI e nao em dois lugares. Regra do §9 tambem: cada
// numero mostrado precisa de um consumidor que saiba o que ele e. Por isso o
// resumo passa a nomear as duas medidas em vez de chamar as duas de "DD".
double CSafetyManager::GetDailyLossPercent(double &perda, double &base)
{
   // Numerador: o REALIZADO do dia. Nao o patrimonio, que muda a cada tique.
   perda = (m_daily_profit < 0.0) ? MathAbs(m_daily_profit) : 0.0;

   // Denominador: o SALDO do inicio do dia. Nao o patrimonio.
   base = (m_daily_start_balance > 0.0)
             ? m_daily_start_balance
             : AccountInfoDouble(ACCOUNT_BALANCE);

   return (base > 0.0) ? (perda / base) * 100.0 : 0.0;
}

//==================================================
// SAFETY SUMMARY
//==================================================

string CSafetyManager::GetSafetySummary()
{
   double perdaTela = 0.0;
   double baseTela = 0.0;
   double perdaPct = GetDailyLossPercent(perdaTela, baseTela);

   // `PerdaDia` e o numero que o gate usa e o que trava. `Amplitude` e a
   // medida pico-vale, que continua existindo e e informative, mas com o
   // nome que ela mede. Nenhum dos dois se apresenta como "DD" sem dizer o
   // que e: e o que fez o operador procurar DD num bloqueio que era margem.
   return StringFormat(
      "P/L: %.2f | Trades: %d/%d | PerdaDia: %.2f%%/%.2f%% | Amplitude: %.2f%% | FreeMargin: %.2f",
      m_daily_profit,
      GetDailyTrades(),
      m_limits.max_trades_per_day,
      perdaPct,
      m_limits.max_daily_drawdown,
      GetDrawdownPercent(),
      AccountInfoDouble(
         ACCOUNT_MARGIN_FREE
      )
   );
}

//==================================================
// LOG
//==================================================

void CSafetyManager::LogSafety()
{
   PrintFormat(
      "[SAFETY] %s",
      GetSafetySummary()
   );
}


//==================================================
// REGISTER TRADE
//==================================================

void CSafetyManager::RegisterTrade()
{
   if(!m_initialized)
      Init();

   // v1.3.0 (Etapa 3): contador persistente sobrevive a reinits
   IncrementDailyTrades();
}

//==================================================
// GET DAILY TRADES
//==================================================

int CSafetyManager::GetDailyTrades()
{
   if(!m_initialized)
      Init();

   // v1.3.0 (Etapa 3): fonte unica persistente
   return GetDailyTradesCount();
}

#endif // SAFETY_MANAGER_MQH
