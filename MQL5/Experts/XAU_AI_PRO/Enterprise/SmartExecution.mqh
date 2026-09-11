//+------------------------------------------------------------------+
//|                                              SmartExecution.mqh |
//|                                  Smart Execution Engine - Core   |
//|                                            XAU_AI_PRO v1.2.0      |
//+------------------------------------------------------------------+

#ifndef SMART_EXECUTION_MQH
#define SMART_EXECUTION_MQH

#include "BrokerAnalyzer.mqh"
#include "VolumeValidator.mqh"
#include "MarginChecker.mqh"
#include "OrderRetry.mqh"
#include "ExecutionQuality.mqh"
#include "ExecutionStats.mqh"
#include "AntiLoop.mqh"
#include "PositionSynchronizer.mqh"

#include "../Core/Config.mqh"

// v1.2.2 - Janela (segundos) do guard inter-instancia de envio.
// Impede que as 3 instancias do EA (uma por grafico) enviem a
// mesma ordem (symbol+direcao) simultaneamente. Usa GlobalVariable
// do terminal: compartilhada entre instancias e resistente a
// reinicializacoes do EA (rede instavel).
#define INTER_INSTANCE_SEND_WINDOW_SEC 10


//==================================================
// EXECUTION RESULT
//==================================================

enum ExecResult
{
   EXEC_SUCCESS=0,
   EXEC_INVALID_VOLUME,
   EXEC_SPREAD_TOO_HIGH,
   EXEC_NO_MARGIN,
   EXEC_INVALID_PRICE,
   EXEC_RETRY_FAILED,
   EXEC_LOOP_DETECTED,
   EXEC_ERROR
};


//==================================================
// EXECUTION REQUEST
//==================================================

struct ExecRequest
{
   string          symbol;

   ENUM_ORDER_TYPE type;

   double          volume;

   double          price;

   double          sl;

   double          tp;

   string          comment;

   ulong           magic;
};


//==================================================
// SMART EXECUTION
//==================================================

class CSmartExecution
{
private:

   static bool m_initialized;


   static bool PrepareRequest(
      const ExecRequest &exec_req,
      MqlTradeRequest &request
   );


   static ExecResult ValidateExecution(
      const ExecRequest &exec_req
   );


   static ExecResult ExecuteOrder(
      const ExecRequest &exec_req,
      MqlTradeResult &result
   );


public:

   static void Init();


   static ExecResult OpenPosition(
      const ExecRequest &exec_req,
      ulong &ticket
   );


   static ExecResult ClosePosition(
      ulong ticket,
      double volume=0.0
   );


   static ExecResult ModifyPosition(
      ulong ticket,
      double sl,
      double tp
   );


   static void Synchronize();


   static string GetExecutionSummary();


   static void LogExecution(
      const ExecRequest &req,
      ExecResult res,
      const MqlTradeResult &result
   );
};


//==================================================
// STATIC VARIABLE
//==================================================

bool CSmartExecution::m_initialized=false;


//==================================================
// INIT
//==================================================

void CSmartExecution::Init()
{
   if(m_initialized)
      return;


   CBrokerAnalyzer::Init();

   CVolumeValidator::Init();

   CMarginChecker::Init();

   COrderRetry::Init();

   CExecutionQuality::Init();

   CExecutionStats::Init();

   CAntiLoop::Init();

   CPositionSynchronizer::Init();


   m_initialized=true;


   Print(
      "[EXECUTION] SmartExecution initialized"
   );
}


//==================================================
// PREPARE REQUEST
//==================================================

bool CSmartExecution::PrepareRequest(
   const ExecRequest &exec_req,
   MqlTradeRequest &request
)
{
   if(exec_req.symbol=="")
      return false;


   if(exec_req.volume<=0.0)
      return false;


   if(exec_req.price<=0.0)
      return false;


   if(!SymbolSelect(
      exec_req.symbol,
      true
   ))
   {
      return false;
   }


   ZeroMemory(
      request
   );


   request.action=
      TRADE_ACTION_DEAL;


   request.symbol=
      exec_req.symbol;


   // Normalizar volume para o step do simbolo
   double normalizedVolume=
      CVolumeValidator::NormalizeVolume(
         exec_req.volume
      );

   if(normalizedVolume<=0.0)
      return false;

   request.volume=
      normalizedVolume;


   request.type=
      exec_req.type;


   request.price=
      exec_req.price;


   request.sl=
      exec_req.sl;


   request.tp=
      exec_req.tp;


   request.deviation=
      CBrokerAnalyzer::GetRecommendedSlippage();


   request.magic=
      exec_req.magic;


   request.comment=
      exec_req.comment;


   request.type_filling=
      CBrokerAnalyzer::GetOptimalFillPolicy();


   return true;
}


//==================================================
// VALIDATE EXECUTION
//==================================================

ExecResult CSmartExecution::ValidateExecution(
   const ExecRequest &exec_req
)
{
   if(exec_req.symbol=="")
      return EXEC_ERROR;


   if(
      !CAntiLoop::CanTrade()
   )
   {
      return EXEC_LOOP_DETECTED;
   }


   if(
      !CVolumeValidator::ValidateVolume(
         exec_req.volume
      )
   )
   {
      return EXEC_INVALID_VOLUME;
   }



   //------------------------------------------------
   // VERIFICAR SPREAD
   //------------------------------------------------

   double ask=
      SymbolInfoDouble(
         exec_req.symbol,
         SYMBOL_ASK
      );

   double bid=
      SymbolInfoDouble(
         exec_req.symbol,
         SYMBOL_BID
      );

   double point=
      SymbolInfoDouble(
         exec_req.symbol,
         SYMBOL_POINT
      );

   if(
      ask>0.0 &&
      bid>0.0 &&
      point>0.0
   )
   {
      double spread=
         (ask-bid)/point;

      if(
         spread>GetMaxSpread(exec_req.symbol)
      )
      {
         PrintFormat(
            "[EXECUTION] SPREAD TOO HIGH | %s | %.1f / %.1f",
            exec_req.symbol,
            spread,
            GetMaxSpread(exec_req.symbol)
         );

         return EXEC_SPREAD_TOO_HIGH;
      }
   }

   //------------------------------------------------
   // VERIFICAR MARGEM
   //------------------------------------------------
   // v1.3.0: usa o volume NORMALIZADO (step do broker).
   // O lote fracionario da IA (ex.: 0.01 x 1.25 = 0.0125)
   // inflava a margem requerida e rejeitava ordens que
   // caberiam apos a normalizacao para 0.01.
   //------------------------------------------------

   double marginVolume =
      CVolumeValidator::NormalizeVolume(
         exec_req.volume
      );

   if(marginVolume <= 0.0)
      return EXEC_INVALID_VOLUME;

   if(
      !CMarginChecker::CheckMargin(
         exec_req.symbol,
         marginVolume,
         exec_req.price
      )
   )
   {
      return EXEC_NO_MARGIN;
   }


   if(exec_req.price<=0.0)
      return EXEC_INVALID_PRICE;



    //------------------------------------------------
    // VERIFICAR STOPS LEVEL DO BROKER
    //------------------------------------------------

    long stopLevel =
       SymbolInfoInteger(
          exec_req.symbol,
          SYMBOL_TRADE_STOPS_LEVEL
       );

    if(stopLevel > 0 && (exec_req.sl != 0.0 || exec_req.tp != 0.0))
    {
       double point =
          SymbolInfoDouble(
             exec_req.symbol,
             SYMBOL_POINT
          );

       if(point > 0.0)
       {
          double slDistance =
             MathAbs(exec_req.price - exec_req.sl) / point;

          double tpDistance = MathAbs(exec_req.price - exec_req.tp) / point;

          if(slDistance < (double)stopLevel || tpDistance < (double)stopLevel)
          {
             PrintFormat(
                "[EXECUTION] STOP LEVEL VIOLATION | %s | SL dist=%.0f < broker min=%d",
                exec_req.symbol,
                slDistance,
                (int)stopLevel
             );

             return EXEC_INVALID_PRICE;
          }
       }
    }

   return EXEC_SUCCESS;
}


//==================================================
// EXECUTE ORDER
//==================================================

ExecResult CSmartExecution::ExecuteOrder(
   const ExecRequest &exec_req,
   MqlTradeResult &result
)
{
   MqlTradeRequest request;


   if(
      !PrepareRequest(
         exec_req,
         request
      )
   )
   {
      return EXEC_ERROR;
   }


   ZeroMemory(
      result
   );


   ulong start=
      GetTickCount();


   RetryResult retry_res=
      COrderRetry::ExecuteWithRetry(
         request,
         result
      );


   int delay=
      (int)(
         GetTickCount()-
         start
      );


   if(
      retry_res==
      RETRY_SUCCESS
   )
   {
      QualityScore qscore=
         CExecutionQuality::CalculateScore(
            exec_req.price,
            result.price,
            delay
         );


      CExecutionStats::RecordOrder(
         true,
         result.retcode,
         qscore.slippage_pips,
         delay,
         qscore.score
      );


      CAntiLoop::RecordOpen();


      return EXEC_SUCCESS;
   }


   CExecutionStats::RecordOrder(
      false,
      result.retcode,
      0,
      delay,
      0
   );


   return EXEC_RETRY_FAILED;
}


//==================================================
// OPEN POSITION
//==================================================

ExecResult CSmartExecution::OpenPosition(
   const ExecRequest &exec_req,
   ulong &ticket
)
{
   if(!m_initialized)
      Init();


   ticket=0;


   //------------------------------------------------
   // v1.2.2 - GUARD INTER-INSTANCIA
   // Bloqueia se outra instancia enviou a mesma ordem
   // (symbol+direcao) ha menos de INTER_INSTANCE_SEND_WINDOW_SEC.
   // O registro da GlobalVariable so acontece apos confirmacao
   // de sucesso no envio, entao falha nao cria bloqueio indevido.
   //------------------------------------------------

   string gvSent="XAI_PRO_SENT_"
                 +exec_req.symbol+"_"
                 +IntegerToString((int)exec_req.type);

   datetime lastSent=0;

   bool sgTester=(MQLInfoInteger(MQL_TESTER)!=0);
   if(!sgTester && GlobalVariableCheck(gvSent))
      lastSent=(datetime)GlobalVariableGet(gvSent);

   if(!sgTester && TimeCurrent()-lastSent < INTER_INSTANCE_SEND_WINDOW_SEC)
   {
      MqlTradeResult skipResult;

      ZeroMemory(skipResult);

      LogExecution(exec_req, EXEC_LOOP_DETECTED, skipResult);

      return EXEC_LOOP_DETECTED;
   }


   ExecResult validationResult=
      ValidateExecution(
         exec_req
      );


   if(
      validationResult!=
      EXEC_SUCCESS
   )
   {
      MqlTradeResult emptyResult;

      ZeroMemory(
         emptyResult
      );


      LogExecution(
         exec_req,
         validationResult,
         emptyResult
      );


      return validationResult;
   }


   MqlTradeResult result;

   ZeroMemory(
      result
   );


   ExecResult executionResult=
      ExecuteOrder(
         exec_req,
         result
      );


   if(
      executionResult==
      EXEC_SUCCESS
   )
   {
      ticket=
         result.order;

      // v1.2.2 - registra o envio SOMENTE apos sucesso
      if(MQLInfoInteger(MQL_TESTER)==0)
         GlobalVariableSet(gvSent, (double)TimeCurrent());
   }


   LogExecution(
      exec_req,
      executionResult,
      result
   );


   return executionResult;
}


//==================================================
// CLOSE POSITION
//==================================================

ExecResult CSmartExecution::ClosePosition(
   ulong ticket,
   double volume
)
{
   if(!m_initialized)
      Init();


   if(ticket==0)
      return EXEC_ERROR;


   if(
      !PositionSelectByTicket(
         ticket
      )
   )
   {
      return EXEC_ERROR;
   }


   string symbol=
      PositionGetString(
         POSITION_SYMBOL
      );


   if(symbol=="")
      return EXEC_ERROR;


   ENUM_POSITION_TYPE positionType=
      (ENUM_POSITION_TYPE)
      PositionGetInteger(
         POSITION_TYPE
      );


   double positionVolume=
      PositionGetDouble(
         POSITION_VOLUME
      );


   if(volume<=0.0)
      volume=positionVolume;


   volume=
      MathMin(
         volume,
         positionVolume
      );


   if(volume<=0.0)
      return EXEC_INVALID_VOLUME;


   double price=0.0;


   ENUM_ORDER_TYPE orderType;


   if(
      positionType==
      POSITION_TYPE_BUY
   )
   {
      orderType=
         ORDER_TYPE_SELL;


      price=
         SymbolInfoDouble(
            symbol,
            SYMBOL_BID
         );
   }
   else
   {
      orderType=
         ORDER_TYPE_BUY;


      price=
         SymbolInfoDouble(
            symbol,
            SYMBOL_ASK
         );
   }


   if(price<=0.0)
      return EXEC_INVALID_PRICE;


   MqlTradeRequest request;

   MqlTradeResult result;


   ZeroMemory(
      request
   );

   ZeroMemory(
      result
   );


   request.action=
      TRADE_ACTION_DEAL;


   request.symbol=
      symbol;


   request.volume=
      volume;


   request.type=
      orderType;


   request.price=
      price;


   request.position=
      ticket;


   request.deviation=
      CBrokerAnalyzer::GetRecommendedSlippage();


   request.magic=
      MagicNumber;


   request.comment=
      TradeComment;


   request.type_filling=
      CBrokerAnalyzer::GetOptimalFillPolicy();


   RetryResult retryResult=
      COrderRetry::ExecuteWithRetry(
         request,
         result
      );


   if(
      retryResult==
      RETRY_SUCCESS
   )
   {
      CAntiLoop::RecordClose();

      return EXEC_SUCCESS;
   }


   return EXEC_RETRY_FAILED;
}


//==================================================
// MODIFY POSITION
//==================================================

ExecResult CSmartExecution::ModifyPosition(
   ulong ticket,
   double sl,
   double tp
)
{
   if(!m_initialized)
      Init();


   if(ticket==0)
      return EXEC_ERROR;


   if(
      !PositionSelectByTicket(
         ticket
      )
   )
   {
      return EXEC_ERROR;
   }


   string symbol=
      PositionGetString(
         POSITION_SYMBOL
      );


   if(symbol=="")
      return EXEC_ERROR;


   MqlTradeRequest request;

   MqlTradeResult result;


   ZeroMemory(
      request
   );

   ZeroMemory(
      result
   );


   request.action=
      TRADE_ACTION_SLTP;


   request.symbol=
      symbol;


   request.position=
      ticket;


   //------------------------------------------------
   // Normaliza SL/TP contra o stop level do broker
   // (evita "Invalid stops" no break-even/trailing)
   //------------------------------------------------

   double pointM = SymbolInfoDouble(symbol, SYMBOL_POINT);
   long stopLevelM = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   int digitsM = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   ENUM_POSITION_TYPE ptypeM = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double curM = (ptypeM == POSITION_TYPE_BUY)
                 ? SymbolInfoDouble(symbol, SYMBOL_BID)
                 : SymbolInfoDouble(symbol, SYMBOL_ASK);

   if(pointM > 0.0 && curM > 0.0 && stopLevelM > 0)
   {
      double minDist = (double)stopLevelM * pointM;

      if(sl != 0.0 && MathAbs(curM - sl) < minDist)
         sl = (sl > curM) ? curM + minDist : curM - minDist;

      if(tp != 0.0 && MathAbs(curM - tp) < minDist)
         tp = (tp > curM) ? curM + minDist : curM - minDist;
   }

   request.sl =
      NormalizeDouble(sl, digitsM);


   request.tp=
      NormalizeDouble(tp, digitsM);


   request.magic=
      MagicNumber;


   if(
      !OrderSend(
         request,
         result
      )
   )
   {
      return EXEC_ERROR;
   }


   if(
      result.retcode==
      TRADE_RETCODE_DONE
   )
   {
      return EXEC_SUCCESS;
   }


   return EXEC_ERROR;
}


//==================================================
// SYNCHRONIZE
//==================================================

void CSmartExecution::Synchronize()
{
   if(!m_initialized)
      Init();


   CPositionSynchronizer::Synchronize();
}


//==================================================
// EXECUTION SUMMARY
//==================================================

string CSmartExecution::GetExecutionSummary()
{
   if(!m_initialized)
      return "Not initialized";


   string summary=
      "=== EXECUTION SUMMARY ===\n";


   summary+=
      CExecutionStats::GetSummary();


   summary+=
      "\nAntiLoop: ";


   summary+=
      CAntiLoop::GetLoopStatus();


   summary+=
      "\nPositions: ";


   summary+=
      IntegerToString(
         CPositionSynchronizer::GetTerminalPositions()
      );


   summary+=
      " total EA (terminal)\n";


   QualityScore lastScore=
      CExecutionQuality::GetLastScore();


   summary+=
      StringFormat(
         "Last Quality: %.1f (%.2f pips slippage, %dms delay)",
         lastScore.score,
         lastScore.slippage_pips,
         lastScore.delay_ms
      );


   return summary;
}


//==================================================
// LOG EXECUTION
//==================================================

void CSmartExecution::LogExecution(
   const ExecRequest &req,
   ExecResult res,
   const MqlTradeResult &result
)
{
   string type=
      (
         req.type==
         ORDER_TYPE_BUY
      )
      ?
      "BUY"
      :
      "SELL";


   string resultString="";


   switch(res)
   {
      case EXEC_SUCCESS:
         resultString=
            "SUCCESS";
         break;



       case EXEC_SPREAD_TOO_HIGH:
          resultString=
             "SPREAD_TOO_HIGH";
          break;

      case EXEC_INVALID_VOLUME:
         resultString=
            "INVALID_VOLUME";
         break;


      case EXEC_NO_MARGIN:
         resultString=
            "NO_MARGIN";
         break;


      case EXEC_INVALID_PRICE:
         resultString=
            "INVALID_PRICE";
         break;


      case EXEC_RETRY_FAILED:
         resultString=
            "RETRY_FAILED";
         break;


      case EXEC_LOOP_DETECTED:
         resultString=
            "LOOP_DETECTED";
         break;


      default:
         resultString=
            "ERROR";
         break;
   }


   if(
      res==
      EXEC_SUCCESS
   )
   {
      PrintFormat(
         "[EXECUTION] %s %.2f %s @ %.5f | Ticket: %I64u | Result: %s",
         type,
         req.volume,
         req.symbol,
         req.price,
         result.order,
         resultString
      );
   }
   else
   {
      PrintFormat(
         "[EXECUTION] %s %.2f %s @ %.5f | FAILED: %s",
         type,
         req.volume,
         req.symbol,
         req.price,
         resultString
      );
   }
}


#endif
