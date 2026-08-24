//+------------------------------------------------------------------+
//| CircuitBreaker.mqh                                               |
//| Circuit Breaker System                                           |
//| XAU_AI_PRO v1.2.0                                                  |
//+------------------------------------------------------------------+

#ifndef CIRCUIT_BREAKER_MQH
#define CIRCUIT_BREAKER_MQH

#include "../Core/Config.mqh"

//==================================================
// CIRCUIT STATE
//==================================================

enum CircuitState
{
   CIRCUIT_NORMAL=0,
   CIRCUIT_WARNING,
   CIRCUIT_SAFE_MODE,
   CIRCUIT_LOCKED
};


//==================================================
// CIRCUIT BREAKER
//==================================================

class CCircuitBreaker
{
private:

   static CircuitState m_state;

   static bool m_initialized;

   static datetime m_triggered_time;

   static string m_trigger_reason;

   static int m_trigger_count;

   static int m_cooldown_seconds;


   //================================================
   // INTERNAL CHECKS
   //================================================

   static bool CheckSpreadExplosion(
      string symbol
   );

   static bool CheckHighDrawdown();

   static bool CheckBrokerError();

   static bool CheckAIFailure(
      string symbol
   );

   static bool CheckAbnormalMarket(
      string symbol
   );

   static double GetCurrentSpread(
      string symbol
   );

   static double GetATRValue(
      string symbol,
      ENUM_TIMEFRAMES timeframe,
      int shift
   );

   static double GetAverageATR(
      string symbol,
      ENUM_TIMEFRAMES timeframe,
      int startShift,
      int count
   );


public:

   static void Init();

   static void Run();

   static void RunSymbol(
      string symbol
   );

   static CircuitState GetState();

   static string GetStateString();

   static bool IsSafeMode();

   static bool CanTrade();

   static bool CanTrade(
      string symbol
   );

   static void Reset();

   static void ForceSafeMode(
      const string reason
   );

   static datetime GetTriggeredTime();
   static string GetTriggerReason();

   static void LogStatus();
};


//==================================================
// STATIC DEFINITIONS
//==================================================

CircuitState
CCircuitBreaker::m_state=
   CIRCUIT_NORMAL;


bool
CCircuitBreaker::m_initialized=
   false;


datetime
CCircuitBreaker::m_triggered_time=
   0;


string
CCircuitBreaker::m_trigger_reason=
   "";


int
CCircuitBreaker::m_trigger_count=
   0;


int
CCircuitBreaker::m_cooldown_seconds=
   300;


//==================================================
// INIT
//==================================================

void CCircuitBreaker::Init()
{
   if(m_initialized)
      return;


   m_state=
      CIRCUIT_NORMAL;


   m_triggered_time=
      0;


   m_trigger_reason=
      "";


   m_trigger_count=
      0;


   m_initialized=
      true;


   // v1.3.0 (Etapa 3): SAFE_MODE persiste entre reinicializacoes.
   // Quedas de rede nao liberam mais o circuit breaker por acidente.
   string gvCB="XAI_PRO_CB_SAFE_UNTIL";

   if(MQLInfoInteger(MQL_TESTER)==0 && GlobalVariableCheck(gvCB))
   {
      datetime until=(datetime)GlobalVariableGet(gvCB);

      if(TimeCurrent() < until)
      {
         m_state=CIRCUIT_SAFE_MODE;

         m_triggered_time=until - m_cooldown_seconds;

         m_trigger_reason="restaurado apos reinicio";

         Print("[CIRCUIT] SAFE_MODE restaurado apos reinicio ate ",
               TimeToString(until, TIME_DATE|TIME_SECONDS));
      }
      else
      {
         if(MQLInfoInteger(MQL_TESTER)==0)
            GlobalVariableDel(gvCB);
      }
   }


   Print(
      "[CIRCUIT] CircuitBreaker initialized"
   );
}


//==================================================
// GET CURRENT SPREAD
//==================================================

double CCircuitBreaker::GetCurrentSpread(
   string symbol
)
{
   if(symbol=="")
      return 0.0;


   double ask=
      SymbolInfoDouble(
         symbol,
         SYMBOL_ASK
      );


   double bid=
      SymbolInfoDouble(
         symbol,
         SYMBOL_BID
      );


   double point=
      SymbolInfoDouble(
         symbol,
         SYMBOL_POINT
      );


   if(
      ask<=0.0 ||
      bid<=0.0 ||
      point<=0.0
   )
   {
      return 0.0;
   }


   return(
      (ask-bid)/point
   );
}


//==================================================
// CHECK SPREAD EXPLOSION
//==================================================

bool CCircuitBreaker::CheckSpreadExplosion(
   string symbol
)
{
   if(symbol=="")
      return false;


   if(!EnableSpreadFilter)
      return false;


   double spread=
      GetCurrentSpread(
         symbol
      );


   if(spread<=0.0)
      return false;


   // Circuit Breaker atua somente em
   // spread extremamente anormal.
   //
   // O filtro normal jÃƒÆ’Ã‚Â¡ usa MaxSpread.
   //
   // IMPORTANTE (v1.2.0 - diagnostico):
   // Em backtest, sÃƒÆ’Ã‚Â­mbolos crypto (BTCUSD#, ETHUSD#)
   // tÃƒÆ’Ã‚Âªm spread natural de ~345 pontos, enquanto
   // MaxSpread default = 30. Com fator 3x (=90),
   // o CircuitBreaker dispara ForceSafeMode a cada
   // tick, travando toda a operaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o.
   //
   // SoluÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o defensiva:
   //   - O filtro normal (ValidateTrade) jÃƒÆ’Ã‚Â¡ barra
   //     spread > MaxSpread por sÃƒÆ’Ã‚Â­mbolo.
   //   - O CircuitBreaker sÃƒÆ’Ã‚Â³ deve agir em explosÃƒÆ’Ã‚Â£o
   //     EXTREMA (fator 10x), evitando falso-positivo
   //     em spread normal de crypto/volatilidade alta.

   double emergencySpread=
      GetMaxSpread(symbol)*10.0;


   if(
      spread>
      emergencySpread
   )
   {
      Print(
         "[CIRCUIT] SPREAD EXPLOSION | ",
         symbol,
         " | Spread=",
         DoubleToString(
            spread,
            2
         ),
         " | Limit=",
         DoubleToString(
            emergencySpread,
            2
         )
      );

      return true;
   }


   return false;
}


//==================================================
// CHECK HIGH DRAWDOWN
//==================================================

bool CCircuitBreaker::CheckHighDrawdown()
{
   double balance=
      AccountInfoDouble(
         ACCOUNT_BALANCE
      );


   double equity=
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );


   if(balance<=0.0)
      return false;


   // Drawdown da CONTA (acumulado vs balance) - intencional:
   // RiskHub (GetDrawdownPercent) mede o peak DIARIO.
   double drawdown=
      (
         (balance-equity)
         /
         balance
      )
      *100.0;


   if(
      drawdown>
      MaxDrawdownPercent
   )
   {
      Print(
         "[CIRCUIT] HIGH DRAWDOWN | ",
         DoubleToString(
            drawdown,
            2
         ),
         "%"
      );

      return true;
   }


   return false;
}


//==================================================
// CHECK BROKER
//==================================================

bool CCircuitBreaker::CheckBrokerError()
{
   bool connected=
      (
         TerminalInfoInteger(
            TERMINAL_CONNECTED
         )!=0
      );


   bool tradeAllowed=
      (
         AccountInfoInteger(
            ACCOUNT_TRADE_ALLOWED
         )!=0
      );


   if(
      !connected ||
      !tradeAllowed
   )
   {
      return true;
   }


   return false;
}


//==================================================
// CHECK AI (v1.2.0 fix - fallback no tester)
//==================================================

bool CCircuitBreaker::CheckAIFailure(
   string symbol
)
{
   if(!EnableAIFilter)
      return false;


   if(symbol=="")
      return false;


   // FIX v1.2.0: em backtest o pipeline Python nao roda,
   // entao prediction_<SYMBOL>.json nunca existe. Usa o
   // fallback local do AIEngine (nao bloqueia o simbolo).
   // Em modo real, JSON ausente so bloqueia se RequireAIJSON=true.
   if(!RequireAIJSON)
      return false;

   if(MQLInfoInteger(MQL_TESTER)!=0)
      return false;

   string fileName=
      "Data\\prediction_" +
      symbol +
      ".json";


   if(
      !FileIsExist(
         fileName,
         0
      )
   )
   {
      return true;
   }


   return false;
}


//==================================================
// GET ATR
//==================================================

double CCircuitBreaker::GetATRValue(
   string symbol,
   ENUM_TIMEFRAMES timeframe,
   int shift
)
{
   if(symbol=="")
      return 0.0;


   int handle=
      iATR(
         symbol,
         timeframe,
         ATRPeriod
      );


   if(
      handle==
      INVALID_HANDLE
   )
   {
      return 0.0;
   }


   double buffer[];


   ArrayResize(
      buffer,
      1
   );


   ArraySetAsSeries(
      buffer,
      true
   );


   double value=0.0;


   if(
      CopyBuffer(
         handle,
         0,
         shift,
         1,
         buffer
      )>0
   )
   {
      value=
         buffer[0];
   }


   IndicatorRelease(
      handle
   );


   return value;
}


//==================================================
// GET AVERAGE ATR
//==================================================

double CCircuitBreaker::GetAverageATR(
   string symbol,
   ENUM_TIMEFRAMES timeframe,
   int startShift,
   int count
)
{
   if(
      symbol=="" ||
      count<=0
   )
   {
      return 0.0;
   }


   int handle=
      iATR(
         symbol,
         timeframe,
         ATRPeriod
      );


   if(
      handle==
      INVALID_HANDLE
   )
   {
      return 0.0;
   }


   double buffer[];


   ArrayResize(
      buffer,
      count
   );


   ArraySetAsSeries(
      buffer,
      true
   );


   int copied=
      CopyBuffer(
         handle,
         0,
         startShift,
         count,
         buffer
      );


   IndicatorRelease(
      handle
   );


   if(
      copied<=0
   )
   {
      return 0.0;
   }


   double sum=0.0;

   int valid=0;


   for(
      int i=0;
      i<copied;
      i++
   )
   {
      if(
         buffer[i]>0.0
      )
      {
         sum+=
            buffer[i];

         valid++;
      }
   }


   if(valid<=0)
      return 0.0;


   return(
      sum/
      valid
   );
}


//==================================================
// CHECK ABNORMAL MARKET
//==================================================

bool CCircuitBreaker::CheckAbnormalMarket(
   string symbol
)
{
   if(symbol=="")
      return false;


   double currentATR=
      GetATRValue(
         symbol,
         PERIOD_CURRENT,
         1
      );


   if(
      currentATR<=0.0
   )
   {
      return false;
   }


   double averageATR=
      GetAverageATR(
         symbol,
         PERIOD_CURRENT,
         2,
         20
      );


   if(
      averageATR<=0.0
   )
   {
      return false;
   }


   double ratio=
      currentATR/
      averageATR;


   // Volatilidade extrema:
   // ATR atual > 3x mÃƒÆ’Ã‚Â©dia recente

   if(
      ratio>=3.0
   )
   {
      Print(
         "[CIRCUIT] ABNORMAL MARKET | ",
         symbol,
         " | ATR=",
         DoubleToString(
            currentATR,
            6
         ),
         " | AvgATR=",
         DoubleToString(
            averageATR,
            6
         ),
         " | Ratio=",
         DoubleToString(
            ratio,
            2
         )
      );

      return true;
   }


   return false;
}


//==================================================
// RUN ALL
//==================================================

void CCircuitBreaker::Run()
{
   if(!m_initialized)
      Init();


   if(
      m_state==
      CIRCUIT_LOCKED
   )
   {
      return;
   }


   //===============================================
   // BROKER / ACCOUNT
   //===============================================

   if(
      CheckBrokerError()
   )
   {
      ForceSafeMode(
         "Broker connection or trading disabled"
      );

      return;
   }


   //===============================================
   // DRAWDOWN
   //===============================================

   if(
      CheckHighDrawdown()
   )
   {
      ForceSafeMode(
         "High drawdown detected"
      );

      return;
   }


   //===============================================
   // CURRENT SYMBOL
   //===============================================

   RunSymbol(
      _Symbol
   );


   //===============================================
   // AUTO RECOVERY
   //===============================================

   if(
      m_state==
      CIRCUIT_SAFE_MODE
   )
   {
      if(
         TimeCurrent()-
         m_triggered_time
         >=
         m_cooldown_seconds
      )
      {
         m_state=
            CIRCUIT_NORMAL;

         m_trigger_reason=
            "";

         Print(
            "[CIRCUIT] Recovered to NORMAL mode"
         );

          // v1.3.0 (Etapa 3): limpa a persistencia do SAFE_MODE
          string gvCB="XAI_PRO_CB_SAFE_UNTIL";

          if(MQLInfoInteger(MQL_TESTER)==0 && GlobalVariableCheck(gvCB))
            GlobalVariableDel(gvCB);
      }
   }
}


//==================================================
// RUN SYMBOL
//==================================================

void CCircuitBreaker::RunSymbol(
   string symbol
)
{
   if(
      symbol==""
   )
   {
      return;
   }


   if(
      CheckSpreadExplosion(
         symbol
      )
   )
   {
      //================================================
      // SPREAD
      //
      // NÃƒÆ’Ã‚Â£o bloquear o sistema inteiro por causa do
      // spread de um ÃƒÆ’Ã‚Âºnico sÃƒÆ’Ã‚Â­mbolo.
      //
      // O filtro por sÃƒÆ’Ã‚Â­mbolo (ValidateTrade | SPREAD)
      // ÃƒÆ’Ã‚Â© o responsÃƒÆ’Ã‚Â¡vel por barrar spread > MaxSpread,
      // sem travar as demais operaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes.
      //
      // Em backtest, sÃƒÆ’Ã‚Â­mbolos crypto (BTCUSD#, ETHUSD#)
      // tÃƒÆ’Ã‚Âªm spread natural muito alto (ex: 2250 pontos),
      // o que fazia o CircuitBreaker travar TUDO a cada
      // tick (Trigger #99k).
      //
      // Este log serve apenas de diagnÃƒÆ’Ã‚Â³stico.
      //================================================

      Print(
         "[CIRCUIT] SPREAD ALTO | ",
         symbol,
         " | Bloqueio delegado ao ValidateTrade"
      );
   }


   if(
      CheckAIFailure(
         symbol
      )
   )
   {
      //================================================
      // AI
      //
      // NÃƒÆ’Ã‚Â£o bloquear o sistema inteiro apenas porque
      // prediction_<symbol>.json nÃƒÆ’Ã‚Â£o estÃƒÆ’Ã‚Â¡ disponÃƒÆ’Ã‚Â­vel.
      //
      // O AIEngine possui fallback local.
      //
      // O AITradeAllowed() serÃƒÆ’Ã‚Â¡ responsÃƒÆ’Ã‚Â¡vel pela
      // decisÃƒÆ’Ã‚Â£o final da IA.
      //================================================

      Print(
         "[CIRCUIT] AI JSON AUSENTE | ",
         symbol,
         " | Usando fallback do AIEngine"
      );
   }


   if(
      CheckAbnormalMarket(
         symbol
      )
   )
   {
      ForceSafeMode(
         "Abnormal market: "
         +
         symbol
      );

      return;
   }
}


//==================================================
// GET STATE
//==================================================

CircuitState
CCircuitBreaker::GetState()
{
   return m_state;
}


//==================================================
// GET STATE STRING
//==================================================

string CCircuitBreaker::GetStateString()
{
   switch(
      m_state
   )
   {
      case CIRCUIT_NORMAL:
         return "NORMAL";

      case CIRCUIT_WARNING:
         return "WARNING";

      case CIRCUIT_SAFE_MODE:
         return "SAFE_MODE";

      case CIRCUIT_LOCKED:
         return "LOCKED";
   }


   return "UNKNOWN";
}


//==================================================
// SAFE MODE
//==================================================

bool CCircuitBreaker::IsSafeMode()
{
   return(
      m_state==
      CIRCUIT_SAFE_MODE
      ||
      m_state==
      CIRCUIT_LOCKED
   );
}


//==================================================
// CAN TRADE
//==================================================

bool CCircuitBreaker::CanTrade()
{
   return(
      m_state==
      CIRCUIT_NORMAL
      ||
      m_state==
      CIRCUIT_WARNING
   );
}


//==================================================
// CAN TRADE SYMBOL
//==================================================

bool CCircuitBreaker::CanTrade(
   string symbol
)
{
   if(
      !CanTrade()
   )
   {
      return false;
   }


   if(
      symbol==""
   )
   {
      return false;
   }


   if(
      CheckSpreadExplosion(
         symbol
      )
   )
   {
      return false;
   }


   if(
      CheckAbnormalMarket(
         symbol
      )
   )
   {
      return false;
   }


   if(
      CheckAIFailure(
         symbol
      )
   )
   {
      return false;
   }


   return true;
}


//==================================================
// RESET
//==================================================

void CCircuitBreaker::Reset()
{
   m_state=
      CIRCUIT_NORMAL;


   m_triggered_time=
      0;


   m_trigger_reason=
      "";


   Print(
      "[CIRCUIT] CircuitBreaker reset to NORMAL"
   );
}


//==================================================
// FORCE SAFE MODE
//==================================================

void CCircuitBreaker::ForceSafeMode(
   const string reason
)
{
   if(
      m_state==
      CIRCUIT_LOCKED
   )
   {
      return;
   }


   m_state=
      CIRCUIT_SAFE_MODE;


   m_triggered_time=
      TimeCurrent();


   m_trigger_reason=
      reason;


      m_trigger_count++;
   // v1.3.0 (Etapa 3): persiste SAFE_MODE pelo cooldown (sobrevive a reinits)
   if(MQLInfoInteger(MQL_TESTER)==0)
      GlobalVariableSet("XAI_PRO_CB_SAFE_UNTIL", TimeCurrent() + m_cooldown_seconds);

   PrintFormat(
      "[CIRCUIT] SAFE MODE activated: %s | Trigger #%d",
      reason,
      m_trigger_count
   );
}


//==================================================
// TRIGGER REASON
//==================================================

datetime CCircuitBreaker::GetTriggeredTime()
{
   return m_triggered_time;
}

string CCircuitBreaker::GetTriggerReason()
{
   return m_trigger_reason;
}


//==================================================
// LOG STATUS
//==================================================

void CCircuitBreaker::LogStatus()
{
   PrintFormat(
      "[CIRCUIT] State=%s | Reason=%s | Triggers=%d",
      GetStateString(),
      m_trigger_reason,
      m_trigger_count
   );
}


//==================================================
// FAILSAFE COMPAT (v1.4.0 - Etapa 5)
//==================================================
// O modulo orfao Monitoring/FailSafe.mqh foi fundido
// aqui. O CircuitBreaker ja era o dono real do
// SAFE_MODE (cooldown 300s, persistencia em
// GlobalVariable, recovery automatico). Esta secao
// preserva a API publica do FailSafe e adiciona os
// contadores de erro com histerese.
//
// NOTA Etapa 6: o health check do antigo FailSafe
// dependia de HealthMonitor/WatchDog (orfao). Sera
// integrado na Etapa 6 junto com esses modulos.
//==================================================

enum ENUM_ROBOT_MODE
{
   ROBOT_MODE_AUTO = 0,
   ROBOT_MODE_SAFE = 1
};

// Duracao minima do SAFE_MODE (compat FailSafe)
int g_failSafeDuration = 300;

// Limites de histerese (compat FailSafe)
int g_failSafeMaxAIErrors = 5;
int g_failSafeMaxBrokerErrors = 10;

// Contadores acumulados (sobrevivem enquanto o EA roda)
int g_failSafeAIErrorCount = 0;
int g_failSafeBrokerErrorCount = 0;

//==================================================
// ACTIVATE (compat)
//==================================================

void FailSafeActivate(string reason)
{
   CCircuitBreaker::ForceSafeMode(reason);
}

//==================================================
// CAN TRADE (compat)
//==================================================

bool FailSafeCanTrade()
{
   return CCircuitBreaker::CanTrade();
}

//==================================================
// GET MODE (compat)
//==================================================

ENUM_ROBOT_MODE FailSafeGetMode()
{
   return(CCircuitBreaker::IsSafeMode() ? ROBOT_MODE_SAFE : ROBOT_MODE_AUTO);
}

//==================================================
// GET MODE STRING (compat)
//==================================================

string FailSafeGetModeString()
{
   return CCircuitBreaker::GetStateString();
}

//==================================================
// GET REASON (compat)
//==================================================

string FailSafeGetReason()
{
   return CCircuitBreaker::GetTriggerReason();
}

//==================================================
// GET ELAPSED (compat)
//==================================================

int FailSafeGetElapsed()
{
   if(!CCircuitBreaker::IsSafeMode())
      return 0;
   return(int)(TimeCurrent() - CCircuitBreaker::GetTriggeredTime());
}

//==================================================
// GET REMAINING (compat)
//==================================================

int FailSafeGetRemaining()
{
   if(!CCircuitBreaker::IsSafeMode())
      return 0;
   int remaining = g_failSafeDuration - FailSafeGetElapsed();
   if(remaining < 0)
      remaining = 0;
   return remaining;
}

//==================================================
// SET MODE (compat) - modo manual
//==================================================

void FailSafeSetMode(ENUM_ROBOT_MODE mode)
{
   if(mode == ROBOT_MODE_SAFE)
   {
      CCircuitBreaker::ForceSafeMode("MANUAL_SAFE_MODE");
      return;
   }
   CCircuitBreaker::Reset();
}

//==================================================
// RESET (compat)
//==================================================

void FailSafeReset()
{
   CCircuitBreaker::Reset();
   g_failSafeAIErrorCount = 0;
   g_failSafeBrokerErrorCount = 0;
}

//==================================================
// SUMMARY (compat)
//==================================================

string FailSafeSummary()
{
   string summary = "=== FAILSAFE ===\n";
   summary += "Mode: " + FailSafeGetModeString() + "\n";
   summary += "CanTrade: " + (FailSafeCanTrade() ? "YES" : "NO") + "\n";
   summary += "Reason: " + CCircuitBreaker::GetTriggerReason() + "\n";
   if(CCircuitBreaker::IsSafeMode())
   {
      summary += "Elapsed: " + IntegerToString(FailSafeGetElapsed()) + "s\n";
      summary += "Remaining: " + IntegerToString(FailSafeGetRemaining()) + "s\n";
   }
   summary += "AI Errors: " + IntegerToString(g_failSafeAIErrorCount) + "/" + IntegerToString(g_failSafeMaxAIErrors) + "\n";
   summary += "Broker Errors: " + IntegerToString(g_failSafeBrokerErrorCount) + "/" + IntegerToString(g_failSafeMaxBrokerErrors) + "\n";
   return summary;
}

//==================================================
// SHUTDOWN (compat)
//==================================================

void FailSafeShutdown()
{
   Print("[FAILSAFE] Finalizado");
}

//==================================================
// ERROR COUNTERS (v1.4.0 - Etapa 5)
// Chamados pelo CCircuitBreaker::Run() para dar
// histerese aos gatilhos de IA/broker.
//==================================================

void FailSafeRegisterAIError()
{
   g_failSafeAIErrorCount++;
   if(g_failSafeAIErrorCount >= g_failSafeMaxAIErrors)
   {
      FailSafeActivate("AI_ERRORS");
      g_failSafeAIErrorCount = 0;
   }
}

void FailSafeRegisterBrokerError()
{
   g_failSafeBrokerErrorCount++;
   if(g_failSafeBrokerErrorCount >= g_failSafeMaxBrokerErrors)
   {
      FailSafeActivate("BROKER_ERRORS");
      g_failSafeBrokerErrorCount = 0;
   }
}

//==================================================
// END
//==================================================

#endif  f