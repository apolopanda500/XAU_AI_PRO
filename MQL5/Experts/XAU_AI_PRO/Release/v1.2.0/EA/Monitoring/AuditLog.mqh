// XAU_AI_PRO v1.2.0
#ifndef AUDITLOG_MQH
#define AUDITLOG_MQH

#include "../Core/Config.mqh"
#include "Logger.mqh"

//==================================================
// XAU_AI_PRO — SISTEMA DE AUDITORIA (ETAPA 6)
//
// Unifica o AuditLog (decisões em CSV) com o antigo
// FullAudit (registros estruturados de entrada/saída
// por ticket, salvos em Data\full_audit.csv).
//==================================================

#define AUDIT_MAX_RECORDS 1000
#define AUDIT_FULL_FILE   "Data\\full_audit.csv"

int  auditHandle        = INVALID_HANDLE;
bool g_auditInitialized = false;

//==================================================
// FULL AUDIT — REGISTRO ESTRUTURADO (antigo FullAudit)
//==================================================

struct AuditRecord
{
   datetime time;
   ulong    ticket;
   string   symbol;
   double   price;
   double   rsi;
   double   adx;
   double   atr;
   double   ema;
   double   spread;
   string   session;
   string   ai_signal;
   double   ai_confidence;
   double   ai_score;
   string   entry_reason;
   string   exit_reason;
   double   result;
};

AuditRecord g_auditRecords[];
int         g_auditRecordCount = 0;

//==================================================
// INICIALIZA
//==================================================

bool AuditLogInit()
{
   if(g_auditInitialized && auditHandle != INVALID_HANDLE)
      return true;

   //----------------------------------------------
   // Buffer estruturado (FullAudit)
   //----------------------------------------------

   if(!g_auditInitialized)
   {
      ArrayResize(g_auditRecords, AUDIT_MAX_RECORDS);
      g_auditRecordCount = 0;
   }

   //----------------------------------------------
   // Decision log CSV
   //----------------------------------------------

   if(auditHandle == INVALID_HANDLE)
   {
      ResetLastError();

      auditHandle = FileOpen(
         "audit_log.csv",
         FILE_COMMON |
         FILE_READ |
         FILE_WRITE |
         FILE_CSV |
         FILE_ANSI |
         FILE_SHARE_READ |
         FILE_SHARE_WRITE
      );

      if(auditHandle == INVALID_HANDLE)
      {
         LogError(
            "AuditLog: falha ao abrir arquivo. Erro: ",
            IntegerToString(GetLastError())
         );

         return false;
      }

      FileSeek(auditHandle, 0, SEEK_END);

      if(FileSize(auditHandle) == 0)
      {
         FileWrite(
            auditHandle,
            "Time",
            "Symbol",
            "Timeframe",
            "Direction",
            "RSI",
            "ADX",
            "ATR",
            "EMA_Fast",
            "EMA_Slow",
            "AI_Score",
            "AI_Confidence",
            "Technical_Score",
            "Combined_Score",
            "Spread",
            "Session",
            "Result",
            "Ticket",
            "Profit"
         );

         FileFlush(auditHandle);
      }
   }

   g_auditInitialized = true;

   LogSystem("AuditLog inicializado");

   return true;
}

//==================================================
// REGISTRA DECISÃO
//==================================================

void AuditLogDecision(
   string symbol,
   string direction,

   double rsi,
   double adx,
   double atr,

   double emaFast,
   double emaSlow,

   double aiScore,
   double aiConfidence,

   double technicalScore,
   double combinedScore,

   double spread,

   string session,

   string result = "",

   ulong ticket = 0,

   double profit = 0.0
)
{
   if(auditHandle == INVALID_HANDLE)
      return;

   if(symbol == "")
      symbol = _Symbol;

   FileSeek(auditHandle, 0, SEEK_END);

   FileWrite(
      auditHandle,

      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),

      symbol,

      EnumToString((ENUM_TIMEFRAMES)Period()),

      direction,

      DoubleToString(rsi, 2),
      DoubleToString(adx, 2),
      DoubleToString(atr, _Digits),

      DoubleToString(emaFast, _Digits),
      DoubleToString(emaSlow, _Digits),

      DoubleToString(aiScore, 2),
      DoubleToString(aiConfidence, 2),

      DoubleToString(technicalScore, 2),
      DoubleToString(combinedScore, 2),

      DoubleToString(spread, 2),

      session,

      result,

      (ticket > 0 ? IntegerToString((long)ticket) : ""),

      DoubleToString(profit, 2)
   );

   FileFlush(auditHandle);
}

//==================================================
// REGISTRA DECISÃO SIMPLIFICADA
//==================================================

void AuditLogSimple(
   string symbol,
   string direction,
   string result,
   double score
)
{
   if(auditHandle == INVALID_HANDLE)
      return;

   if(symbol == "")
      symbol = _Symbol;

   FileSeek(auditHandle, 0, SEEK_END);

   FileWrite(
      auditHandle,

      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),

      symbol,

      EnumToString((ENUM_TIMEFRAMES)Period()),

      direction,

      "",
      "",
      "",

      "",
      "",

      DoubleToString(score, 2),

      "",

      "",
      DoubleToString(score, 2),

      "",

      "",

      result,

      "",

      "0.00"
   );

   FileFlush(auditHandle);
}

//==================================================
// REGISTRA RESULTADO DE TRADE
//==================================================

void AuditLogTradeResult(
   string symbol,
   ulong ticket,
   double profit,
   string result
)
{
   if(auditHandle == INVALID_HANDLE)
      return;

   if(symbol == "")
      symbol = _Symbol;

   FileSeek(auditHandle, 0, SEEK_END);

   FileWrite(
      auditHandle,

      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),

      symbol,

      EnumToString((ENUM_TIMEFRAMES)Period()),

      "",

      "",
      "",
      "",

      "",
      "",

      "",
      "",

      "",
      "",

      "",

      "",

      result,

      IntegerToString((long)ticket),

      DoubleToString(profit, 2)
   );

   FileFlush(auditHandle);
}

//==================================================
// FULL AUDIT — REGISTRA ENTRADA (antigo CFullAudit::LogDecision)
//==================================================

void AuditLogTrackEntry(
   string symbol,
   ulong ticket,
   double price,
   double rsi,
   double adx,
   double atr,
   double ema,
   double spread,
   string session,
   string ai_signal,
   double ai_confidence,
   double ai_score,
   string entry_reason
)
{
   if(!g_auditInitialized)
      AuditLogInit();

   //================================================
   // BUFFER CHEIO
   //================================================

   if(g_auditRecordCount >= AUDIT_MAX_RECORDS)
   {
      AuditLogSaveRecords();
      g_auditRecordCount = 0;
   }

   int index = g_auditRecordCount;

   //================================================
   // DADOS
   //================================================

   g_auditRecords[index].time          = TimeCurrent();
   g_auditRecords[index].ticket        = ticket;
   g_auditRecords[index].symbol        = symbol;
   g_auditRecords[index].price         = price;
   g_auditRecords[index].rsi           = rsi;
   g_auditRecords[index].adx           = adx;
   g_auditRecords[index].atr           = atr;
   g_auditRecords[index].ema           = ema;
   g_auditRecords[index].spread        = spread;
   g_auditRecords[index].session       = session;
   g_auditRecords[index].ai_signal     = ai_signal;
   g_auditRecords[index].ai_confidence = ai_confidence;
   g_auditRecords[index].ai_score      = ai_score;
   g_auditRecords[index].entry_reason  = entry_reason;
   g_auditRecords[index].exit_reason   = "";
   g_auditRecords[index].result        = 0.0;

   g_auditRecordCount++;
}

//==================================================
// FULL AUDIT — REGISTRA SAÍDA (antigo CFullAudit::LogExit)
//==================================================

void AuditLogTrackExit(
   ulong ticket,
   string exit_reason,
   double result
)
{
   if(!g_auditInitialized)
      AuditLogInit();

   if(ticket == 0)
      return;

   //================================================
   // PROCURAR TICKET
   //================================================

   for(int i = g_auditRecordCount - 1; i >= 0; i--)
   {
      if(g_auditRecords[i].ticket != ticket)
         continue;

      g_auditRecords[i].exit_reason = exit_reason;
      g_auditRecords[i].result      = result;

      return;
   }
}

//==================================================
// FULL AUDIT — SALVA REGISTROS (antigo CFullAudit::SaveToFile)
//==================================================

void AuditLogSaveRecords()
{
   if(!g_auditInitialized)
      return;

   if(g_auditRecordCount <= 0)
      return;

   ResetLastError();

   int handle = FileOpen(
      AUDIT_FULL_FILE,
      FILE_READ |
      FILE_WRITE |
      FILE_CSV |
      FILE_ANSI |
      FILE_SHARE_READ |
      FILE_SHARE_WRITE,
      ';'
   );

   if(handle == INVALID_HANDLE)
   {
      LogError(
         "AuditLog: erro ao abrir full_audit.csv",
         "Code=" + IntegerToString(GetLastError())
      );

      return;
   }

   //================================================
   // IR PARA FIM
   //================================================

   FileSeek(handle, 0, SEEK_END);

   //================================================
   // HEADER
   //================================================

   if(FileSize(handle) == 0)
   {
      FileWrite(
         handle,
         "Time",
         "Ticket",
         "Symbol",
         "Price",
         "RSI",
         "ADX",
         "ATR",
         "EMA",
         "Spread",
         "Session",
         "AI_Signal",
         "AI_Confidence",
         "AI_Score",
         "Entry_Reason",
         "Exit_Reason",
         "Result"
      );
   }

   //================================================
   // RECORDS
   //================================================

   for(int i = 0; i < g_auditRecordCount; i++)
   {
      FileWrite(
         handle,

         TimeToString(g_auditRecords[i].time, TIME_DATE | TIME_SECONDS),

         (string)g_auditRecords[i].ticket,

         g_auditRecords[i].symbol,

         DoubleToString(g_auditRecords[i].price, _Digits),

         DoubleToString(g_auditRecords[i].rsi, 2),
         DoubleToString(g_auditRecords[i].adx, 2),
         DoubleToString(g_auditRecords[i].atr, _Digits),
         DoubleToString(g_auditRecords[i].ema, _Digits),

         DoubleToString(g_auditRecords[i].spread, 2),

         g_auditRecords[i].session,

         g_auditRecords[i].ai_signal,

         DoubleToString(g_auditRecords[i].ai_confidence, 2),
         DoubleToString(g_auditRecords[i].ai_score, 2),

         g_auditRecords[i].entry_reason,

         g_auditRecords[i].exit_reason,

         DoubleToString(g_auditRecords[i].result, 2)
      );
   }

   FileFlush(handle);
   FileClose(handle);

   // Registros persistidos - libera o buffer (ETAPA 6)
   g_auditRecordCount = 0;
}

//==================================================
// FLUSH (ETAPA 6)
//==================================================

void AuditLogFlush()
{
   if(auditHandle != INVALID_HANDLE)
      FileFlush(auditHandle);

   AuditLogSaveRecords();
}

//==================================================
// SUMMARY (ETAPA 6)
//==================================================

string AuditLogSummary()
{
   return StringFormat(
      "AuditLog | DecisionLog=%s | Records=%d | File=%s | Status=%s",
      (auditHandle != INVALID_HANDLE ? "ON" : "OFF"),
      g_auditRecordCount,
      AUDIT_FULL_FILE,
      g_auditInitialized ? "READY" : "OFF"
   );
}

//==================================================
// FECHA
//==================================================

void AuditLogClose()
{
   AuditLogSaveRecords();

   if(auditHandle != INVALID_HANDLE)
   {
      FileFlush(auditHandle);
      FileClose(auditHandle);
      auditHandle = INVALID_HANDLE;
   }

   g_auditInitialized = false;

   LogSystem("AuditLog finalizado");
}

//==================================================
// STATUS
//==================================================

bool AuditLogIsReady()
{
   return g_auditInitialized && auditHandle != INVALID_HANDLE;
}

//==================================================

#endif // AUDITLOG_MQH
