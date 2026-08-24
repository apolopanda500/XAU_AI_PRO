// XAU_AI_PRO v1.2.0
#ifndef REPLAYENGINE_MQH
#define REPLAYENGINE_MQH

#include "../Core/Config.mqh"
#include "Logger.mqh"

//==================================================
// REPLAY ENGINE v2.0 (ETAPA 7)
//==================================================
// Reproduz decisoes/eventos historicos do XAU_AI_PRO
// usando os dados registrados, SEM interferir na
// execucao real.
//
// SEPARACAO ABSOLUTA REPLAY vs LIVE:
//  - Enquanto o replay esta ativo (ReplayEngineIsActive),
//    o EA deve bloquear a abertura de trades reais.
//    Use ReplayEngineBlocksLiveTrading() como guarda.
//  - O replay e SOMENTE LEITURA: nunca envia ordens,
//    nunca modifica posicoes, nunca altera o dataset.
//
// FONTES DE DADOS (compatibilidade com o pipeline):
//  - DECISOES  : Data\trades_dataset.csv (Dataset.mqh export, 19 col)
//  - OHLC/TICK : Data\dataset.csv        (DataLogger.mqh, 15 col)
//  - AUDITORIA : Data\full_audit.csv     (AuditLog.mqh, 16 col, sep ';')
//
// CAMINHO (FILE_COMMON + fallback local):
//  O Dataset.mqh e o DataLogger.mqh gravam no diretorio
//  LOCAL do terminal (MQL5\Files\Data), enquanto o
//  AuditLog grava no COMMON (Common\Files\Data).
//  O replay procura cada arquivo primeiro em FILE_COMMON
//  e depois no diretorio local, logando a origem.
//==================================================

#define REPLAY_COLS_DECISIONS 19
#define REPLAY_COLS_OHLC      15
#define REPLAY_COLS_AUDIT     16

//==================================================
// MODO DE REPLAY
//==================================================

enum ENUM_REPLAY_MODE
{
   REPLAY_MODE_DECISIONS = 0,   // trades_dataset.csv
   REPLAY_MODE_OHLC      = 1,   // dataset.csv (DataLogger)
   REPLAY_MODE_AUDIT     = 2    // full_audit.csv (AuditLog)
};

//==================================================
// ESTRUTURAS DE SAIDA
//==================================================

struct ReplayOHLC
{
   datetime time;
   string   symbol;
   double   open;
   double   high;
   double   low;
   double   close;
   double   volume;
   double   spread;
   double   atr;
   double   adx;
   double   rsi;
   double   kci_vd;
   double   kci_main;
   double   kdi_plus;
   double   kdi_minus;
};

struct ReplayAuditRecord
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

//==================================================
// ESTADO GLOBAL
//==================================================

int             g_replayHandle     = INVALID_HANDLE;
bool            g_replayActive     = false;
int             g_replayLine       = 0;
string          g_replayFile       = "";
ENUM_REPLAY_MODE g_replayMode      = REPLAY_MODE_DECISIONS;
string          g_replaySymbolFilter = "";
int             g_replayRecordsRead = 0;
int             g_replaySkipped     = 0;
int             g_replayHeaderCols  = 0;

//==================================================
// HELPERS PRIVADOS
//==================================================

// Abre o arquivo procurando primeiro em FILE_COMMON,
// depois no diretorio local (MQL5\Files).
int ReplayOpenBest(
   string path,
   char   sep
)
{
   ResetLastError();

   if(FileIsExist(path, FILE_COMMON))
   {
      int h = FileOpen(
         path,
         FILE_COMMON |
         FILE_READ |
         FILE_CSV |
         FILE_ANSI,
         sep
      );

      if(h != INVALID_HANDLE)
      {
         g_replayFile = "[COMMON] " + path;
         return h;
      }
   }

   ResetLastError();

   if(FileIsExist(path))
   {
      int h = FileOpen(
         path,
         FILE_READ |
         FILE_CSV |
         FILE_ANSI,
         sep
      );

      if(h != INVALID_HANDLE)
      {
         g_replayFile = "[LOCAL] " + path;
         return h;
      }
   }

   return INVALID_HANDLE;
}

// Le o cabecalho (primeira linha) e conta as colunas.
// Retorna o numero de colunas lidas.
int ReplaySkipHeader(
   int expectedCols
)
{
   int cols = 0;

   if(g_replayHandle == INVALID_HANDLE)
      return 0;

   while(
      !FileIsEnding(g_replayHandle) &&
      !FileIsLineEnding(g_replayHandle)
   )
   {
      FileReadString(g_replayHandle);
      cols++;

      if(cols > 64)
         break;
   }

   g_replayHeaderCols = cols;

   if(cols != expectedCols)
   {
      LogWarning(
         "ReplayEngine: cabecalho com ",
         IntegerToString(cols),
         " colunas (esperado ",
         IntegerToString(expectedCols),
         ")"
      );
   }

   return cols;
}

// Normaliza simbolo para comparacao (case-insensitive).
bool ReplaySymbolMatches(
   string symbol
)
{
   if(g_replaySymbolFilter == "")
      return true;

   string s = symbol;
   string f = g_replaySymbolFilter;

   StringToUpper(s);
   StringToUpper(f);

   if(s == f)
      return true;

   if(StringFind(s, f) >= 0)
      return true;

   return false;
}

//==================================================
// INIT - DECISOES (Dataset.mqh export)
//==================================================

bool ReplayEngineInit(
   string datasetFile = ""
)
{
   // Fechar replay anterior
   if(g_replayHandle != INVALID_HANDLE)
   {
      FileClose(g_replayHandle);
      g_replayHandle = INVALID_HANDLE;
   }

   g_replayActive      = false;
   g_replayLine        = 0;
   g_replayRecordsRead = 0;
   g_replaySkipped     = 0;
   g_replayMode        = REPLAY_MODE_DECISIONS;
   g_replaySymbolFilter= ReplaySymbolFilter;

   if(datasetFile == "")
      datasetFile = ReplayDatasetFile;

   ResetLastError();

   g_replayHandle = ReplayOpenBest(
      datasetFile,
      ','
   );

   if(g_replayHandle == INVALID_HANDLE)
   {
      LogError(
         "ReplayEngine: falha ao abrir dataset (COMMON e LOCAL). Erro: ",
         IntegerToString(GetLastError())
      );

      return false;
   }

   //================================================
   // PULAR CABECALHO (19 colunas)
   //================================================

   ReplaySkipHeader(REPLAY_COLS_DECISIONS);

   g_replayLine = 1;
   g_replayActive = true;

   LogSystem(
      "ReplayEngine inicializado (DECISOES). Origem: ",
      g_replayFile
   );

   return true;
}

//==================================================
// INIT - OHLC (DataLogger.mqh)
//==================================================

bool ReplayEngineOpenOHLC(
   string ohlcFile = ""
)
{
   if(g_replayHandle != INVALID_HANDLE)
   {
      FileClose(g_replayHandle);
      g_replayHandle = INVALID_HANDLE;
   }

   g_replayActive      = false;
   g_replayLine        = 0;
   g_replayRecordsRead = 0;
   g_replaySkipped     = 0;
   g_replayMode        = REPLAY_MODE_OHLC;
   g_replaySymbolFilter= ReplaySymbolFilter;

   if(ohlcFile == "")
      ohlcFile = ReplayOHLCFile;

   ResetLastError();

   g_replayHandle = ReplayOpenBest(
      ohlcFile,
      ','
   );

   if(g_replayHandle == INVALID_HANDLE)
   {
      LogError(
         "ReplayEngine: falha ao abrir OHLC. Erro: ",
         IntegerToString(GetLastError())
      );

      return false;
   }

   ReplaySkipHeader(REPLAY_COLS_OHLC);

   g_replayLine = 1;
   g_replayActive = true;

   LogSystem(
      "ReplayEngine inicializado (OHLC). Origem: ",
      g_replayFile
   );

   return true;
}

//==================================================
// INIT - AUDITORIA (AuditLog full_audit.csv)
//==================================================

bool ReplayEngineOpenAudit(
   string auditFile = ""
)
{
   if(g_replayHandle != INVALID_HANDLE)
   {
      FileClose(g_replayHandle);
      g_replayHandle = INVALID_HANDLE;
   }

   g_replayActive      = false;
   g_replayLine        = 0;
   g_replayRecordsRead = 0;
   g_replaySkipped     = 0;
   g_replayMode        = REPLAY_MODE_AUDIT;
   g_replaySymbolFilter= ReplaySymbolFilter;

   if(auditFile == "")
      auditFile = ReplayAuditFile;

   ResetLastError();

   g_replayHandle = ReplayOpenBest(
      auditFile,
      ';'
   );

   if(g_replayHandle == INVALID_HANDLE)
   {
      LogError(
         "ReplayEngine: falha ao abrir auditoria. Erro: ",
         IntegerToString(GetLastError())
      );

      return false;
   }

   ReplaySkipHeader(REPLAY_COLS_AUDIT);

   g_replayLine = 1;
   g_replayActive = true;

   LogSystem(
      "ReplayEngine inicializado (AUDITORIA). Origem: ",
      g_replayFile
   );

   return true;
}

//==================================================
// PRÓXIMO REGISTRO - DECISOES
// (assinatura mantida da v1 para compatibilidade)
// Registros vazios, com timestamp invalido ou de outro
// simbolo (filtro) sao pulados automaticamente.
//==================================================

bool ReplayEngineNextLine(
   datetime &recordTime,
   string &symbol,
   ENUM_TIMEFRAMES &timeframe,
   int &signal,
   double &price,
   double &volume,
   double &spread,
   double &atr,
   double &adx,
   double &rsi,
   double &volatility,
   double &trend,
   double &aiScore,
   double &aiProbability,
   double &executionScore,
   double &sl,
   double &tp,
   double &profit,
   bool &result
)
{
   while(true)
   {
      if(g_replayHandle == INVALID_HANDLE || !g_replayActive)
         return false;

      if(g_replayMode != REPLAY_MODE_DECISIONS)
      {
         LogError(
            "ReplayEngine: NextLine requer modo DECISOES"
         );
         return false;
      }

      if(FileIsEnding(g_replayHandle))
      {
         LogSystem(
            "ReplayEngine: fim do dataset | lidos=",
            IntegerToString(g_replayRecordsRead),
            " | pulados=",
            IntegerToString(g_replaySkipped),
            " | origem=" + g_replayFile
         );

         ReplayEngineClose();
         return false;
      }

      //----------------------------------------------
      // LEITURA DOS 19 CAMPOS
      //----------------------------------------------

      string timeValue      = FileReadString(g_replayHandle);
      string symbolValue    = FileReadString(g_replayHandle);
      string timeframeValue = FileReadString(g_replayHandle);
      string signalValue    = FileReadString(g_replayHandle);
      string priceValue     = FileReadString(g_replayHandle);
      string volumeValue    = FileReadString(g_replayHandle);
      string spreadValue    = FileReadString(g_replayHandle);
      string atrValue       = FileReadString(g_replayHandle);
      string adxValue       = FileReadString(g_replayHandle);
      string rsiValue       = FileReadString(g_replayHandle);
      string volatilityValue= FileReadString(g_replayHandle);
      string trendValue     = FileReadString(g_replayHandle);
      string aiScoreValue   = FileReadString(g_replayHandle);
      string aiProbabilityValue = FileReadString(g_replayHandle);
      string executionScoreValue = FileReadString(g_replayHandle);
      string slValue        = FileReadString(g_replayHandle);
      string tpValue        = FileReadString(g_replayHandle);
      string profitValue    = FileReadString(g_replayHandle);
      string resultValue    = FileReadString(g_replayHandle);

      g_replayLine++;

      //----------------------------------------------
      // VALIDACAO - linha vazia
      //----------------------------------------------

      if(
         timeValue == "" &&
         symbolValue == "" &&
         signalValue == ""
      )
      {
         LogWarning(
            "ReplayEngine: registro vazio na linha ",
            IntegerToString(g_replayLine)
         );
         continue;
      }

      //----------------------------------------------
      // TIME
      //----------------------------------------------

      recordTime = StringToTime(timeValue);

      if(recordTime <= 0)
      {
         LogWarning(
            "ReplayEngine: timestamp invalido na linha ",
            IntegerToString(g_replayLine),
            " | valor='",
            timeValue,
            "'"
         );
         continue;
      }

      //----------------------------------------------
      // SYMBOL + filtro
      //----------------------------------------------

      symbol = symbolValue;

      if(!ReplaySymbolMatches(symbol))
      {
         g_replaySkipped++;
         continue;
      }

      //----------------------------------------------
      // TIMEFRAME
      //----------------------------------------------

      timeframe = PERIOD_CURRENT;

      if(timeframeValue == "PERIOD_M1")   timeframe = PERIOD_M1;
      else if(timeframeValue == "PERIOD_M2")  timeframe = PERIOD_M2;
      else if(timeframeValue == "PERIOD_M3")  timeframe = PERIOD_M3;
      else if(timeframeValue == "PERIOD_M5")  timeframe = PERIOD_M5;
      else if(timeframeValue == "PERIOD_M10") timeframe = PERIOD_M10;
      else if(timeframeValue == "PERIOD_M15") timeframe = PERIOD_M15;
      else if(timeframeValue == "PERIOD_M30") timeframe = PERIOD_M30;
      else if(timeframeValue == "PERIOD_H1")  timeframe = PERIOD_H1;
      else if(timeframeValue == "PERIOD_H4")  timeframe = PERIOD_H4;
      else if(timeframeValue == "PERIOD_D1")  timeframe = PERIOD_D1;

      //----------------------------------------------
      // NUMERICOS
      //----------------------------------------------

      signal          = (int)StringToInteger(signalValue);
      price           = StringToDouble(priceValue);
      volume          = StringToDouble(volumeValue);
      spread          = StringToDouble(spreadValue);
      atr             = StringToDouble(atrValue);
      adx             = StringToDouble(adxValue);
      rsi             = StringToDouble(rsiValue);
      volatility      = StringToDouble(volatilityValue);
      trend           = StringToDouble(trendValue);
      aiScore         = StringToDouble(aiScoreValue);
      aiProbability   = StringToDouble(aiProbabilityValue);
      executionScore  = StringToDouble(executionScoreValue);
      sl              = StringToDouble(slValue);
      tp              = StringToDouble(tpValue);
      profit          = StringToDouble(profitValue);

      //----------------------------------------------
      // RESULTADO
      //----------------------------------------------

      StringToLower(resultValue);

      result = (
         resultValue == "true" ||
         resultValue == "1"
      );

      g_replayRecordsRead++;

      return true;
   }

   return false;
}

//==================================================
// PRÓXIMO REGISTRO - OHLC (DataLogger)
//==================================================

bool ReplayEngineNextOHLC(
   ReplayOHLC &r
)
{
   while(true)
   {
      if(g_replayHandle == INVALID_HANDLE || !g_replayActive)
         return false;

      if(g_replayMode != REPLAY_MODE_OHLC)
      {
         LogError(
            "ReplayEngine: NextOHLC requer modo OHLC"
         );
         return false;
      }

      if(FileIsEnding(g_replayHandle))
      {
         LogSystem(
            "ReplayEngine: fim do OHLC | lidos=",
            IntegerToString(g_replayRecordsRead),
            " | origem=" + g_replayFile
         );

         ReplayEngineClose();
         return false;
      }

      //----------------------------------------------
      // LEITURA DOS 15 CAMPOS
      //----------------------------------------------

      string timeValue  = FileReadString(g_replayHandle);
      string symbolValue= FileReadString(g_replayHandle);
      string openValue  = FileReadString(g_replayHandle);
      string highValue  = FileReadString(g_replayHandle);
      string lowValue   = FileReadString(g_replayHandle);
      string closeValue = FileReadString(g_replayHandle);
      string volValue   = FileReadString(g_replayHandle);
      string spreadValue= FileReadString(g_replayHandle);
      string atrValue   = FileReadString(g_replayHandle);
      string adxValue   = FileReadString(g_replayHandle);
      string rsiValue   = FileReadString(g_replayHandle);
      string kciVdValue = FileReadString(g_replayHandle);
      string kciMainValue= FileReadString(g_replayHandle);
      string kdiPlusValue= FileReadString(g_replayHandle);
      string kdiMinusValue= FileReadString(g_replayHandle);

      g_replayLine++;

      //----------------------------------------------
      // VALIDACOES
      //----------------------------------------------

      r.time = StringToTime(timeValue);

      if(r.time <= 0)
      {
         LogWarning(
            "ReplayEngine: timestamp invalido no OHLC linha ",
            IntegerToString(g_replayLine)
         );
         continue;
      }

      r.symbol = symbolValue;

      if(!ReplaySymbolMatches(r.symbol))
      {
         g_replaySkipped++;
         continue;
      }

      r.open   = StringToDouble(openValue);
      r.high   = StringToDouble(highValue);
      r.low    = StringToDouble(lowValue);
      r.close  = StringToDouble(closeValue);
      r.volume = StringToDouble(volValue);
      r.spread = StringToDouble(spreadValue);
      r.atr    = StringToDouble(atrValue);
      r.adx    = StringToDouble(adxValue);
      r.rsi    = StringToDouble(rsiValue);
      r.kci_vd= StringToDouble(kciVdValue);
      r.kci_main = StringToDouble(kciMainValue);
      r.kdi_plus = StringToDouble(kdiPlusValue);
      r.kdi_minus= StringToDouble(kdiMinusValue);

      // Estrutura OHLC invalida? pula
      if(
         r.open <= 0.0 ||
         r.high <= 0.0 ||
         r.low  <= 0.0 ||
         r.close <= 0.0 ||
         r.high < r.low
      )
      {
         LogWarning(
            "ReplayEngine: OHLC invalido na linha ",
            IntegerToString(g_replayLine)
         );
         continue;
      }

      g_replayRecordsRead++;

      return true;
   }

   return false;
}

//==================================================
// PRÓXIMO REGISTRO - AUDITORIA (AuditLog)
//==================================================

bool ReplayEngineNextAuditRecord(
   ReplayAuditRecord &r
)
{
   while(true)
   {
      if(g_replayHandle == INVALID_HANDLE || !g_replayActive)
         return false;

      if(g_replayMode != REPLAY_MODE_AUDIT)
      {
         LogError(
            "ReplayEngine: NextAuditRecord requer modo AUDITORIA"
         );
         return false;
      }

      if(FileIsEnding(g_replayHandle))
      {
         LogSystem(
            "ReplayEngine: fim da auditoria | lidos=",
            IntegerToString(g_replayRecordsRead),
            " | origem=" + g_replayFile
         );

         ReplayEngineClose();
         return false;
      }

      //----------------------------------------------
      // LEITURA DOS 16 CAMPOS (sep ';')
      //----------------------------------------------

      string timeValue   = FileReadString(g_replayHandle);
      string ticketValue = FileReadString(g_replayHandle);
      string symbolValue = FileReadString(g_replayHandle);
      string priceValue  = FileReadString(g_replayHandle);
      string rsiValue    = FileReadString(g_replayHandle);
      string adxValue    = FileReadString(g_replayHandle);
      string atrValue    = FileReadString(g_replayHandle);
      string emaValue    = FileReadString(g_replayHandle);
      string spreadValue = FileReadString(g_replayHandle);
      string sessionValue= FileReadString(g_replayHandle);
      string aiSignalValue= FileReadString(g_replayHandle);
      string aiConfValue = FileReadString(g_replayHandle);
      string aiScoreValue= FileReadString(g_replayHandle);
      string entryReasonValue = FileReadString(g_replayHandle);
      string exitReasonValue  = FileReadString(g_replayHandle);
      string resultValue = FileReadString(g_replayHandle);

      g_replayLine++;

      //----------------------------------------------
      // VALIDACOES
      //----------------------------------------------

      r.time = StringToTime(timeValue);

      if(r.time <= 0)
      {
         LogWarning(
            "ReplayEngine: timestamp invalido na auditoria linha ",
            IntegerToString(g_replayLine)
         );
         continue;
      }

      r.ticket = (ulong)StringToInteger(ticketValue);

      r.symbol = symbolValue;

      if(!ReplaySymbolMatches(r.symbol))
      {
         g_replaySkipped++;
         continue;
      }

      r.price          = StringToDouble(priceValue);
      r.rsi            = StringToDouble(rsiValue);
      r.adx            = StringToDouble(adxValue);
      r.atr            = StringToDouble(atrValue);
      r.ema            = StringToDouble(emaValue);
      r.spread         = StringToDouble(spreadValue);
      r.session        = sessionValue;
      r.ai_signal      = aiSignalValue;
      r.ai_confidence  = StringToDouble(aiConfValue);
      r.ai_score       = StringToDouble(aiScoreValue);
      r.entry_reason   = entryReasonValue;
      r.exit_reason    = exitReasonValue;
      r.result         = StringToDouble(resultValue);

      g_replayRecordsRead++;

      return true;
   }

   return false;
}

//==================================================
// FECHAR REPLAY
//==================================================

void ReplayEngineClose()
{
   if(g_replayHandle != INVALID_HANDLE)
   {
      FileClose(g_replayHandle);
      g_replayHandle = INVALID_HANDLE;
   }

   g_replayActive = false;
   g_replayLine   = 0;

   LogSystem(
      "ReplayEngine finalizado"
   );
}

//==================================================
// STATUS
//==================================================

bool ReplayEngineIsActive()
{
   return g_replayActive;
}

// Guarda de seguranca para o EA: quando true, o modo
// REPLAY esta ativo e NENHUM trade real pode ser aberto.
bool ReplayEngineBlocksLiveTrading()
{
   return g_replayActive;
}

int ReplayEngineCurrentLine()
{
   return g_replayLine;
}

int ReplayEngineRecordsRead()
{
   return g_replayRecordsRead;
}

int ReplayEngineSkipped()
{
   return g_replaySkipped;
}

string ReplayEngineSource()
{
   return g_replayFile;
}

string ReplayEngineModeName()
{
   switch(g_replayMode)
   {
      case REPLAY_MODE_DECISIONS: return "DECISOES";
      case REPLAY_MODE_OHLC:      return "OHLC";
      case REPLAY_MODE_AUDIT:     return "AUDITORIA";
   }
   return "DESCONHECIDO";
}

//==================================================
// FILTRO DE SIMBOLO
//==================================================

void ReplayEngineSetSymbolFilter(
   string filter
)
{
   g_replaySymbolFilter = filter;
}

//==================================================
// RESET
//==================================================

void ReplayEngineReset()
{
   ReplayEngineClose();

   g_replayLine        = 0;
   g_replayRecordsRead = 0;
   g_replaySkipped     = 0;

   LogSystem(
      "ReplayEngine resetado"
   );
}

#endif
