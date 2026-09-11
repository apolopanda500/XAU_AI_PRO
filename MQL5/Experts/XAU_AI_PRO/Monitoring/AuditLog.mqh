// XAU_AI_PRO v1.2.2
#ifndef AUDITLOG_MQH
#define AUDITLOG_MQH

#include "../Core/Config.mqh"
#include "Logger.mqh"
#include "EventLock.mqh"      // F4: serializa escrita dos arquivos de auditoria

//==================================================
// XAU_AI_PRO — SISTEMA DE AUDITORIA (ETAPA 6)
//
// Unifica o AuditLog (decisões em CSV) com o antigo
// FullAudit (registros estruturados de entrada/saída
// por ticket, salvos em Data\full_audit.csv).
//
// F4 v1.2.2 - SERIALIZACAO: os arquivos compartilhados
// (audit_log.csv FILE_COMMON e full_audit.csv) sao escritos
// sob o mesmo lock global do EventEmitter (EventLock.mqh),
// evitando entrelacamento/race entre as 11 instancias.
//
// PADRAO DE ESCRITA (F4): ABRIR -> SEEK(END) -> WRITE -> FLUSH -> FECHAR
// sob o lock. NAO manter handle persistente aberto entre gravacoes:
// com 11 instancias abrindo o mesmo arquivo, o FileSeek(SEEK_END) de
// um handle antigo nao enxerga o tamanho atualizado pelos outros
// handles -> overlay/interleave. Handle novo a cada escrita resolve.
//==================================================

#define AUDIT_MAX_RECORDS 1000
#define AUDIT_FULL_FILE   "Data\\full_audit.csv"

bool g_auditInitialized = false;

// F4: total de gravacoes perdidas por lock/timeout (auditoria)
int  g_audit_dropped    = 0;

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
// HELPERS F4 — escrita atomica por gravacao
//==================================================

// Abre audit_log.csv (FILE_COMMON) com handle novo. Retorna handle ou INVALID_HANDLE.
int AuditOpenDecisionLog()
{
   ResetLastError();

   int h = FileOpen(
      "audit_log.csv",
      FILE_COMMON |
      FILE_READ |
      FILE_WRITE |
      FILE_CSV |
      FILE_ANSI |
      FILE_SHARE_READ |
      FILE_SHARE_WRITE,
      ','
   );

   return h;
}

// Grava header do decision log se arquivo vazio (chamado sob lock).
void AuditEnsureDecisionHeader(int handle)
{
   if(handle == INVALID_HANDLE)
      return;

   FileSeek(handle, 0, SEEK_END);

   if(FileSize(handle) == 0)
   {
      FileWrite(
         handle,
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

      FileFlush(handle);
   }
}

//==================================================
// INICIALIZA
//==================================================

bool AuditLogInit()
{
   if(g_auditInitialized)
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
   // Decision log CSV — header serializado (F4)
   //----------------------------------------------

   if(EventLockAcquire())
   {
      int h = AuditOpenDecisionLog();

      if(h != INVALID_HANDLE)
      {
         AuditEnsureDecisionHeader(h);
         FileClose(h);
         EventLockRelease();
      }
      else
      {
         EventLockRelease();

         LogError(
            "AuditLog: falha ao abrir arquivo. Erro: ",
            IntegerToString(GetLastError())
         );

         return false;
      }
   }
   else
      LogError("AuditLog: header sem lock (concorrencia)",
               "Code=EV_LOCK_TIMEOUT");

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
   if(!g_auditInitialized)
      AuditLogInit();

   if(symbol == "")
      symbol = _Symbol;

   // F4: serializa seek->write->flush->close (1 escritor por vez)
   if(!EventLockAcquire())
   {
      g_audit_dropped++;
      Print("[AUDIT] DROP | decision | ", symbol,
            " | dropped=", g_audit_dropped);
      return;
   }

   int h = AuditOpenDecisionLog();

   if(h == INVALID_HANDLE)
   {
      EventLockRelease();

      LogError(
         "AuditLog: falha ao abrir audit_log.csv",
         "Code=" + IntegerToString(GetLastError())
      );

      return;
   }

   AuditEnsureDecisionHeader(h);

   FileWrite(
      h,

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

   FileFlush(h);
   FileClose(h);

   EventLockRelease();
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
   if(!g_auditInitialized)
      AuditLogInit();

   if(symbol == "")
      symbol = _Symbol;

   if(!EventLockAcquire())
   {
      g_audit_dropped++;
      Print("[AUDIT] DROP | simple | ", symbol,
            " | dropped=", g_audit_dropped);
      return;
   }

   int h = AuditOpenDecisionLog();

   if(h == INVALID_HANDLE)
   {
      EventLockRelease();

      LogError(
         "AuditLog: falha ao abrir audit_log.csv",
         "Code=" + IntegerToString(GetLastError())
      );

      return;
   }

   AuditEnsureDecisionHeader(h);

   FileWrite(
      h,

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

   FileFlush(h);
   FileClose(h);

   EventLockRelease();
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
   if(!g_auditInitialized)
      AuditLogInit();

   if(symbol == "")
      symbol = _Symbol;

   if(!EventLockAcquire())
   {
      g_audit_dropped++;
      Print("[AUDIT] DROP | trade_result | ", symbol,
            " | dropped=", g_audit_dropped);
      return;
   }

   int h = AuditOpenDecisionLog();

   if(h == INVALID_HANDLE)
   {
      EventLockRelease();

      LogError(
         "AuditLog: falha ao abrir audit_log.csv",
         "Code=" + IntegerToString(GetLastError())
      );

      return;
   }

   AuditEnsureDecisionHeader(h);

   FileWrite(
      h,

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

   FileFlush(h);
   FileClose(h);

   EventLockRelease();
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
      if(!AuditLogSaveRecords())
      {
         Print("[AUDIT] BUFFER FULL | flush pendente | entrada preservada em memoria");
         return;
      }
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

bool AuditLogSaveRecords()
{
   if(!g_auditInitialized)
      return false;

   if(g_auditRecordCount <= 0)
      return true;

   // F4: serializa a escrita do full_audit.csv (compartilhado entre
   // instancias). O lock cobre open->(header)write->flush->close.
   if(!EventLockAcquire())
   {
      g_audit_dropped++;
      Print("[AUDIT] DROP | SaveRecords | records=", g_auditRecordCount,
            " | dropped=", g_audit_dropped);
      return false;
   }

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
      EventLockRelease();

      LogError(
         "AuditLog: erro ao abrir full_audit.csv",
         "Code=" + IntegerToString(GetLastError())
      );

      return false;
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

   EventLockRelease();

   // Registros persistidos - libera o buffer (ETAPA 6)
   g_auditRecordCount = 0;
   return true;
}

//==================================================
// FLUSH (ETAPA 6)
//==================================================

void AuditLogFlush()
{
   AuditLogSaveRecords();
}

//==================================================
// SUMMARY (ETAPA 6 / F4)
//==================================================

string AuditLogSummary()
{
   return StringFormat(
      "AuditLog | DecisionLog=%s | Records=%d | File=%s | Status=%s | Dropped=%d",
      (g_auditInitialized ? "ON" : "OFF"),
      g_auditRecordCount,
      AUDIT_FULL_FILE,
      g_auditInitialized ? "READY" : "OFF",
      g_audit_dropped
   );
}

//==================================================
// FECHA
//==================================================

void AuditLogClose()
{
   AuditLogSaveRecords();

   g_auditInitialized = false;

   LogSystem("AuditLog finalizado");
}

//==================================================
// STATUS
//==================================================

bool AuditLogIsReady()
{
   return g_auditInitialized;
}

//==================================================

#endif // AUDITLOG_MQH
