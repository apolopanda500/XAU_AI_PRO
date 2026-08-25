//+------------------------------------------------------------------+
//|                                                   OrderRetry.mqh |
//|                     Smart Execution Engine - Retry               |
//|                                            XAU_AI_PRO v1.2.0      |
//+------------------------------------------------------------------+
#ifndef ORDER_RETRY_MQH
#define ORDER_RETRY_MQH

#include "../Core/Config.mqh"

//==================================================
// RETRY RESULT
//==================================================

enum RetryResult
{
   RETRY_SUCCESS=0,
   RETRY_TIMEOUT,
   RETRY_INVALID,
   RETRY_ERROR
};

//==================================================
// RETRY CONFIGURATION
//==================================================

struct RetryConfig
{
   int    max_attempts;
   int    base_delay_ms;
   double delay_multiplier;
   int    max_delay_ms;
   int    max_slippage;
   int    slippage_increment;
};

//==================================================
// ORDER RETRY
//==================================================

class COrderRetry
{
private:

   static RetryConfig m_config;

   static bool m_initialized;

   static int m_total_retries;
   static int m_total_successes;
   static int m_total_failures;

   static uint   m_last_retcode;
   static int    m_last_error;
   static string m_last_comment;

   static int CalculateDelay(
      int attempt
   );

   static bool IsSuccessRetcode(
      uint retcode
   );

   static bool ShouldRetry(
      uint retcode
   );

   static bool IsInvalidRetcode(
      uint retcode
   );

   static bool RefreshRequestPrice(
      MqlTradeRequest &request
   );

   static void IncreaseDeviation(
      MqlTradeRequest &request
   );

   static void SaveLastResult(
      const MqlTradeResult &result
   );

public:

   static void Init();

   static RetryResult ExecuteWithRetry(
      MqlTradeRequest &request,
      MqlTradeResult &result
   );

   static void SetConfig(
      int max_attempts,
      int base_delay_ms,
      double multiplier
   );

   static void SetAdvancedConfig(
      int max_attempts,
      int base_delay_ms,
      double multiplier,
      int max_delay_ms,
      int max_slippage,
      int slippage_increment
   );

   static void ResetStatistics();

   static int GetTotalRetries();

   static int GetTotalSuccesses();

   static int GetTotalFailures();

   static uint GetLastRetcode();

   static int GetLastErrorCode();

   static string GetLastComment();

   static RetryConfig GetConfig();

   static string GetRetryResultString(
      RetryResult result
   );

   static string GetSummary();

   static void LogSummary();
};

//==================================================
// STATIC DEFINITIONS
//==================================================

RetryConfig COrderRetry::m_config;

bool COrderRetry::m_initialized=false;

int COrderRetry::m_total_retries=0;
int COrderRetry::m_total_successes=0;
int COrderRetry::m_total_failures=0;

uint COrderRetry::m_last_retcode=0;
int COrderRetry::m_last_error=0;
string COrderRetry::m_last_comment="";

//==================================================
// INIT
//==================================================

void COrderRetry::Init()
{
   if(m_initialized)
      return;

   m_config.max_attempts=RetryMaxAttempts;
   m_config.base_delay_ms=RetryBaseDelayMs;
   m_config.delay_multiplier=RetryDelayMultiplier;
   m_config.max_delay_ms=RetryMaxDelayMs;
   m_config.max_slippage=RetryMaxSlippage;
   m_config.slippage_increment=RetrySlippageIncrement;

   m_total_retries=0;
   m_total_successes=0;
   m_total_failures=0;

   m_last_retcode=0;
   m_last_error=0;
   m_last_comment="";

   m_initialized=true;

   Print(
      "[RETRY] OrderRetry initialized"
   );
}

//==================================================
// CALCULATE DELAY
//==================================================

int COrderRetry::CalculateDelay(
   int attempt
)
{
   if(attempt<0)
      attempt=0;

   double calculatedDelay=
      (double)m_config.base_delay_ms*
      MathPow(
         m_config.delay_multiplier,
         attempt
      );

   if(calculatedDelay<0.0)
      calculatedDelay=0.0;

   if(
      calculatedDelay>
      (double)m_config.max_delay_ms
   )
   {
      calculatedDelay=
         (double)m_config.max_delay_ms;
   }

   return (int)calculatedDelay;
}

//==================================================
// SUCCESS RETCODES
//==================================================

bool COrderRetry::IsSuccessRetcode(
   uint retcode
)
{
   switch(retcode)
   {
      case TRADE_RETCODE_DONE:
      case TRADE_RETCODE_DONE_PARTIAL:
      case TRADE_RETCODE_PLACED:
      case TRADE_RETCODE_ORDER_CHANGED:
      case TRADE_RETCODE_NO_CHANGES:
         return true;
   }

   return false;
}

//==================================================
// RETRIABLE RETCODES
//==================================================

bool COrderRetry::ShouldRetry(
   uint retcode
)
{
   switch(retcode)
   {
      case TRADE_RETCODE_REQUOTE:
      case TRADE_RETCODE_TIMEOUT:
      case TRADE_RETCODE_PRICE_CHANGED:
      case TRADE_RETCODE_PRICE_OFF:
      case TRADE_RETCODE_TOO_MANY_REQUESTS:
      case TRADE_RETCODE_CONNECTION:
      case TRADE_RETCODE_LOCKED:
         return true;
   }

   return false;
}

//==================================================
// INVALID / PERMANENT RETCODES
//==================================================

bool COrderRetry::IsInvalidRetcode(
   uint retcode
)
{
   switch(retcode)
   {
      case TRADE_RETCODE_INVALID:
      case TRADE_RETCODE_INVALID_VOLUME:
      case TRADE_RETCODE_INVALID_PRICE:
      case TRADE_RETCODE_INVALID_STOPS:
      case TRADE_RETCODE_TRADE_DISABLED:
      case TRADE_RETCODE_MARKET_CLOSED:
      case TRADE_RETCODE_NO_MONEY:
      case TRADE_RETCODE_INVALID_EXPIRATION:
      case TRADE_RETCODE_INVALID_FILL:
      case TRADE_RETCODE_INVALID_ORDER:
      case TRADE_RETCODE_INVALID_CLOSE_VOLUME:
      case TRADE_RETCODE_LIMIT_ORDERS:
      case TRADE_RETCODE_LIMIT_VOLUME:
      case TRADE_RETCODE_LIMIT_POSITIONS:
      case TRADE_RETCODE_LONG_ONLY:
      case TRADE_RETCODE_SHORT_ONLY:
      case TRADE_RETCODE_CLOSE_ONLY:
      case TRADE_RETCODE_FIFO_CLOSE:
      case TRADE_RETCODE_HEDGE_PROHIBITED:
         return true;
   }

   return false;
}

//==================================================
// REFRESH MARKET PRICE
//==================================================

bool COrderRetry::RefreshRequestPrice(
   MqlTradeRequest &request
)
{
   if(request.action!=TRADE_ACTION_DEAL)
      return true;

   if(request.symbol=="")
      return false;

   MqlTick tick;

   ZeroMemory(tick);

   if(
      !SymbolInfoTick(
         request.symbol,
         tick
      )
   )
   {
      return false;
   }

   if(
      tick.ask<=0.0 ||
      tick.bid<=0.0
   )
   {
      return false;
   }

   if(request.type==ORDER_TYPE_BUY)
   {
      request.price=tick.ask;
      return true;
   }

   if(request.type==ORDER_TYPE_SELL)
   {
      request.price=tick.bid;
      return true;
   }

   return false;
}

//==================================================
// INCREASE DEVIATION
//==================================================

void COrderRetry::IncreaseDeviation(
   MqlTradeRequest &request
)
{
   ulong increment=
      (ulong)MathMax(
         m_config.slippage_increment,
         0
      );

   ulong maximum=
      (ulong)MathMax(
         m_config.max_slippage,
         0
      );

   request.deviation+=increment;

   if(request.deviation>maximum)
      request.deviation=maximum;
}

//==================================================
// SAVE LAST RESULT
//==================================================

void COrderRetry::SaveLastResult(
   const MqlTradeResult &result
)
{
   m_last_retcode=result.retcode;
   m_last_error=GetLastError();
   m_last_comment=result.comment;
}

//==================================================
// EXECUTE WITH RETRY
//==================================================

RetryResult COrderRetry::ExecuteWithRetry(
   MqlTradeRequest &request,
   MqlTradeResult &result
)
{
   if(!m_initialized)
      Init();

   ZeroMemory(result);

   m_last_retcode=0;
   m_last_error=0;
   m_last_comment="";

   if(m_config.max_attempts<=0)
   {
      m_total_failures++;
      return RETRY_INVALID;
   }

   if(request.symbol=="")
   {
      m_total_failures++;
      return RETRY_INVALID;
   }

   if(
      request.action==TRADE_ACTION_DEAL &&
      request.volume<=0.0
   )
   {
      m_total_failures++;
      return RETRY_INVALID;
   }

   if(
      !SymbolSelect(
         request.symbol,
         true
      )
   )
   {
      m_total_failures++;
      return RETRY_INVALID;
   }

   for(
      int attempt=0;
      attempt<m_config.max_attempts;
      attempt++
   )
   {
      ResetLastError();

      ZeroMemory(result);

      if(
         !RefreshRequestPrice(
            request
         )
      )
      {
         m_last_error=GetLastError();
         m_total_failures++;

         return RETRY_INVALID;
      }

      //------------------------------------------------
      // ORDER CHECK - Valida a requisicao antes de enviar
      //------------------------------------------------

      MqlTradeCheckResult checkResult;
      ZeroMemory(checkResult);

      if(!OrderCheck(request, checkResult))
      {
         m_last_error = GetLastError();

         PrintFormat(
            "[RETRY] ORDERCHECK FAILED | Symbol=%s | Attempt=%d/%d | Retcode=%u | Error=%d | Comment=%s",
            request.symbol,
            attempt+1,
            m_config.max_attempts,
            checkResult.retcode,
            m_last_error,
            checkResult.comment
         );

         m_total_failures++;

         return RETRY_INVALID;
      }

      bool sent=
         OrderSend(
            request,
            result
         );

      SaveLastResult(
         result
      );

      if(
         sent &&
         IsSuccessRetcode(
            result.retcode
         )
      )
      {
         m_total_successes++;

         if(attempt>0)
            m_total_retries+=attempt;

         PrintFormat(
            "[RETRY] SUCCESS | Symbol=%s | Attempt=%d/%d | Retcode=%u | Order=%I64u | Deal=%I64u",
            request.symbol,
            attempt+1,
            m_config.max_attempts,
            result.retcode,
            result.order,
            result.deal
         );

         return RETRY_SUCCESS;
      }

      if(
         IsInvalidRetcode(
            result.retcode
         )
      )
      {
         m_total_failures++;

         PrintFormat(
            "[RETRY] INVALID | Symbol=%s | Retcode=%u | Comment=%s",
            request.symbol,
            result.retcode,
            result.comment
         );

         return RETRY_INVALID;
      }

      if(
         !ShouldRetry(
            result.retcode
         )
      )
      {
         m_total_failures++;

         PrintFormat(
            "[RETRY] ERROR | Symbol=%s | Retcode=%u | LastError=%d | Comment=%s",
            request.symbol,
            result.retcode,
            m_last_error,
            result.comment
         );

         return RETRY_ERROR;
      }

      if(
         attempt>=
         m_config.max_attempts-1
      )
      {
         break;
      }

      m_total_retries++;

      IncreaseDeviation(
         request
      );

      int delay=
         CalculateDelay(
            attempt
         );

      PrintFormat(
         "[RETRY] RETRYING | Symbol=%s | Attempt=%d/%d | Retcode=%u | Delay=%dms | Deviation=%I64u",
         request.symbol,
         attempt+1,
         m_config.max_attempts,
         result.retcode,
         delay,
         request.deviation
      );

      if(
         delay>0 &&
         !MQLInfoInteger(
            MQL_TESTER
         )
      )
      {
         Sleep(delay);
      }
   }

   m_total_failures++;

   PrintFormat(
      "[RETRY] TIMEOUT | Symbol=%s | Attempts=%d | Retcode=%u | Comment=%s",
      request.symbol,
      m_config.max_attempts,
      result.retcode,
      result.comment
   );

   return RETRY_TIMEOUT;
}

//==================================================
// SET BASIC CONFIG
//==================================================

void COrderRetry::SetConfig(
   int max_attempts,
   int base_delay_ms,
   double multiplier
)
{
   if(!m_initialized)
      Init();

   m_config.max_attempts=
      MathMax(
         max_attempts,
         1
      );

   m_config.base_delay_ms=
      MathMax(
         base_delay_ms,
         0
      );

   m_config.delay_multiplier=
      MathMax(
         multiplier,
         1.0
      );
}

//==================================================
// SET ADVANCED CONFIG
//==================================================

void COrderRetry::SetAdvancedConfig(
   int max_attempts,
   int base_delay_ms,
   double multiplier,
   int max_delay_ms,
   int max_slippage,
   int slippage_increment
)
{
   if(!m_initialized)
      Init();

   m_config.max_attempts=
      MathMax(
         max_attempts,
         1
      );

   m_config.base_delay_ms=
      MathMax(
         base_delay_ms,
         0
      );

   m_config.delay_multiplier=
      MathMax(
         multiplier,
         1.0
      );

   m_config.max_delay_ms=
      MathMax(
         max_delay_ms,
         0
      );

   m_config.max_slippage=
      MathMax(
         max_slippage,
         0
      );

   m_config.slippage_increment=
      MathMax(
         slippage_increment,
         0
      );
}

//==================================================
// RESET STATISTICS
//==================================================

void COrderRetry::ResetStatistics()
{
   m_total_retries=0;
   m_total_successes=0;
   m_total_failures=0;

   m_last_retcode=0;
   m_last_error=0;
   m_last_comment="";
}

//==================================================
// GETTERS
//==================================================

int COrderRetry::GetTotalRetries()
{
   return m_total_retries;
}

int COrderRetry::GetTotalSuccesses()
{
   return m_total_successes;
}

int COrderRetry::GetTotalFailures()
{
   return m_total_failures;
}

uint COrderRetry::GetLastRetcode()
{
   return m_last_retcode;
}

int COrderRetry::GetLastErrorCode()
{
   return m_last_error;
}

string COrderRetry::GetLastComment()
{
   return m_last_comment;
}

RetryConfig COrderRetry::GetConfig()
{
   return m_config;
}

//==================================================
// RESULT TO STRING
//==================================================

string COrderRetry::GetRetryResultString(
   RetryResult result
)
{
   switch(result)
   {
      case RETRY_SUCCESS:
         return "Sucesso";

      case RETRY_TIMEOUT:
         return "Timeout";

      case RETRY_INVALID:
         return "Invalido";

      case RETRY_ERROR:
         return "Erro";
   }

   return "Desconhecido";
}

//==================================================
// SUMMARY
//==================================================

string COrderRetry::GetSummary()
{
   return StringFormat(
      "Retries=%d | Successes=%d | Failures=%d | LastRetcode=%u | LastError=%d | LastComment=%s",
      m_total_retries,
      m_total_successes,
      m_total_failures,
      m_last_retcode,
      m_last_error,
      m_last_comment
   );
}

//==================================================
// LOG SUMMARY
//==================================================

void COrderRetry::LogSummary()
{
   Print(
      "[RETRY] ",
      GetSummary()
   );
}

#endif // ORDER_RETRY_MQH

