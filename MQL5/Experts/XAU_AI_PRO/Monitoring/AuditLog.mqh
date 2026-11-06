// XAU_AI_PRO v1.2.9
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

//==================================================
// v1.2.40 (30/10/2026) - P1.13: ROTACAO POR TAMANHO DO DECISION LOG
//
// MEDIDO em 30/10: Common\Files\audit_log.csv com 68 MB (69 979 KB as 22:28),
// a crescer ~1 linha por decisao, por simbolo e por ciclo, com 16 instancias a
// escrever no mesmo ficheiro. O BackupManager copia o ficheiro INTEIRO em cada
// snapshot: 10 snapshots x 78,8 MB = 787 MB em Common\Files\XAU_AI_PRO\Backups.
// O disco desta maquina ja abortou um backtest com 0,37 GB livres - este log
// sem limite e a maior fonte de crescimento nao controlada que resta.
//
// REGRA: antes de abrir para escrita, se o ficheiro passou de AuditLogMaxSizeMb,
// passa a audit_log_prev.csv (substituindo a geracao anterior) e o novo comeca
// vazio com header. Nada do que ja foi gravado e apagado; o limite efectivo e
// 2 x AuditLogMaxSizeMb. AuditLogMaxSizeMb=0 desliga a rotacao.
//==================================================

#define AUDIT_DECISION_FILE "audit_log.csv"
#define AUDIT_DECISION_PREV "audit_log_prev.csv"
// v1.2.109 (03/11/2026): tentativas de abertura dos ficheiros de auditoria e
// ultimo erro de abertura (lido por AuditReportOpenFailure).
#define AUDIT_OPEN_RETRIES 3

int g_audit_open_last_error = 0;

void AuditRotateDecisionLogIfNeeded()
{
   if(AuditLogMaxSizeMb <= 0)
      return;

   ResetLastError();

   int hs = FileOpen(
      AUDIT_DECISION_FILE,
      FILE_COMMON | FILE_READ | FILE_BIN | FILE_SHARE_READ | FILE_SHARE_WRITE
   );

   if(hs == INVALID_HANDLE)
      return;

   ulong sizeBytes = (ulong)FileSize(hs);
   FileClose(hs);

   ulong capBytes = (ulong)AuditLogMaxSizeMb * 1048576;

   if(sizeBytes < capBytes)
      return;

   // A gravacao corre sob EventLock; se a rotacao falhar, o aviso sai no maximo
   // 1x/hora para nao substituir o spam que esta correccao veio cortar.
   static datetime s_lastRotateLog = 0;

   FileDelete(AUDIT_DECISION_PREV, FILE_COMMON);

   bool moved = FileMove(
      AUDIT_DECISION_FILE,
      FILE_COMMON,
      AUDIT_DECISION_PREV,
      FILE_COMMON | FILE_REWRITE
   );

   if(s_lastRotateLog == 0 || (TimeCurrent() - s_lastRotateLog) >= 3600)
     {
      PrintFormat("[AUDIT] rotacao do decision log | MB=%.1f | limite=%d MB | %s | erro=%d",
                  (double)sizeBytes / 1048576.0,
                  AuditLogMaxSizeMb,
                  (moved ? "OK: geracao anterior em audit_log_prev.csv" : "FALHOU ao mover"),
                  GetLastError());
      s_lastRotateLog = TimeCurrent();
     }
}

// Abre audit_log.csv (FILE_COMMON) com handle novo. Retorna handle ou INVALID_HANDLE.
int AuditOpenDecisionLog()
{
   ResetLastError();

   // v1.2.40 (30/10/2026) - P1.13: rotacao por tamanho antes de abrir.
   AuditRotateDecisionLogIfNeeded();

   int h = INVALID_HANDLE;

   // v1.2.109 (03/11/2026): 5004 = ERR_CANNOT_OPEN_FILE medido no journal para
   // audit_log.csv. Com varias instancias a abrir o mesmo ficheiro FILE_COMMON no
   // mesmo ciclo, a abertura colide com a rotacao (FileMove) de outra instancia.
   // O open repete antes de desistir; o caminho, a rotacao por tamanho e as flags
   // de partilha ficam como estavam.
   for(int tentativa = 0; tentativa < AUDIT_OPEN_RETRIES; tentativa++)
   {
      h = FileOpen(
         AUDIT_DECISION_FILE,
         FILE_COMMON |
         FILE_READ |
         FILE_WRITE |
         FILE_CSV |
         FILE_ANSI |
         FILE_SHARE_READ |
         FILE_SHARE_WRITE,
         ','
      );

      if(h != INVALID_HANDLE)
         return h;

      g_audit_open_last_error = GetLastError();

      // Janela de conflito e de milissegundos: cede o escalonamento e repete.
      Sleep(10);
   }

   return INVALID_HANDLE;
}

// v1.2.109 (03/11/2026): aviso de falha de abertura dos logs de auditoria no
// maximo 1x/hora. A falha continua visivel, mas deixa de gerar uma linha ERROR
// por ciclo e por simbolo nas 17 instancias.
void AuditReportOpenFailure(string alvo)
{
   static datetime s_lastOpenFailLog = 0;

   if(s_lastOpenFailLog != 0 && (TimeCurrent() - s_lastOpenFailLog) < 3600)
      return;

   s_lastOpenFailLog = TimeCurrent();

   LogError(
      "AuditLog: falha ao abrir " + alvo,
      "Code=" + IntegerToString(g_audit_open_last_error) +
      " | aviso 1x/hora | 5004 = ficheiro ocupado por outra instancia"
   );
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

   // v1.2.109 (03/11/2026): EV_LOCK_TIMEOUT medido no journal em 01/11. O header
   // NAO e critico - cada gravacao chama AuditEnsureDecisionHeader() sob lock -
   // portanto o lock e tentado algumas vezes e, se continuar ocupado, o aviso sai
   // no maximo 1x/hora em vez de um ERROR por inicializacao.
   bool hdrSobLock = false;

   for(int tentativaHeader = 0; tentativaHeader < AUDIT_OPEN_RETRIES; tentativaHeader++)
   {
      if(!EventLockAcquire())
      {
         Sleep(5);
         continue;
      }

      int h = AuditOpenDecisionLog();

      if(h != INVALID_HANDLE)
      {
         AuditEnsureDecisionHeader(h);
         FileClose(h);
      }
      else
         AuditReportOpenFailure("audit_log.csv (header)");

      EventLockRelease();

      hdrSobLock = true;
      break;
   }

   if(!hdrSobLock)
   {
      static datetime s_lastHeaderLockLog = 0;

      if(s_lastHeaderLockLog == 0 || (TimeCurrent() - s_lastHeaderLockLog) >= 3600)
      {
         s_lastHeaderLockLog = TimeCurrent();

         Print("[AUDIT] header adiado | lock ocupado (EV_LOCK_TIMEOUT) | aviso 1x/hora |",
               " o header e criado na 1a gravacao");
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

      AuditReportOpenFailure("audit_log.csv");

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

      AuditReportOpenFailure("audit_log.csv");

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

      AuditReportOpenFailure("audit_log.csv");

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

   int handle = INVALID_HANDLE;

   // v1.2.109 (03/11/2026): mesma correccao do decision log. Repetir a abertura
   // antes de perder o lote gravado (5004 = ERR_CANNOT_OPEN_FILE medido em
   // audit_log.csv). Destino, delimitador e header ficam inalterados.
   for(int tentativaFull = 0; tentativaFull < AUDIT_OPEN_RETRIES; tentativaFull++)
   {
      handle = FileOpen(
         AUDIT_FULL_FILE,
         FILE_READ |
         FILE_WRITE |
         FILE_CSV |
         FILE_ANSI |
         FILE_SHARE_READ |
         FILE_SHARE_WRITE,
         ';'
      );

      if(handle != INVALID_HANDLE)
         break;

      g_audit_open_last_error = GetLastError();

      // Janela de conflito e de milissegundos: cede o escalonamento e repete.
      Sleep(10);
   }

   if(handle == INVALID_HANDLE)
   {
      EventLockRelease();

      AuditReportOpenFailure("full_audit.csv");

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
