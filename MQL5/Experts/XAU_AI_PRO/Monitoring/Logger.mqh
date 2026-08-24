// XAU_AI_PRO v1.2.0
#ifndef LOGGER_MQH
#define LOGGER_MQH

#include "../Core/Config.mqh"

//==================================================
// XAU_AI_PRO — ENTERPRISE LOGGER
//==================================================
// Níveis:
// INFO
// WARNING
// ERROR
// AI
// TRADE
// SYSTEM
//
// Recursos:
// - Log em arquivo
// - Log no Journal para erros/avisos
// - Controle de nível mínimo
// - Rotação automática
// - Proteção contra handle inválido
// - Flush controlado
// - Suporte multi-símbolo
//==================================================


//==================================================
// CONFIGURAÇÃO
//==================================================

#define LOGGER_FILE_NAME       "XAU_AI_PRO.log"
#define LOGGER_BACKUP_NAME     "XAU_AI_PRO.log.old"

#define LOGGER_MAX_FILE_SIZE   (10 * 1024 * 1024)


//==================================================
// NÍVEIS
//==================================================

enum ENUM_LOG_LEVEL
{
   LOG_LEVEL_INFO = 0,
   LOG_LEVEL_WARNING = 1,
   LOG_LEVEL_ERROR = 2,
   LOG_LEVEL_AI = 3,
   LOG_LEVEL_TRADE = 4,
   LOG_LEVEL_SYSTEM = 5
};


//==================================================
// ESTADO GLOBAL
//==================================================

int loggerHandle = INVALID_HANDLE;

ENUM_LOG_LEVEL g_logMinLevel = LOG_LEVEL_INFO;

bool LoggerReady = false;

ulong LoggerMessages = 0;

datetime LoggerStartTime = 0;


//==================================================
// NOME DO NÍVEL
//==================================================

string LogLevelPrefix(ENUM_LOG_LEVEL level)
{
   switch(level)
   {
      case LOG_LEVEL_INFO:
         return "[INFO]";

      case LOG_LEVEL_WARNING:
         return "[WARNING]";

      case LOG_LEVEL_ERROR:
         return "[ERROR]";

      case LOG_LEVEL_AI:
         return "[AI]";

      case LOG_LEVEL_TRADE:
         return "[TRADE]";

      case LOG_LEVEL_SYSTEM:
         return "[SYSTEM]";
   }

   return "[UNKNOWN]";
}


//==================================================
// ABRIR LOGGER
//==================================================

bool LoggerOpen()
{
   ResetLastError();

   loggerHandle = FileOpen(
      LOGGER_FILE_NAME,
      FILE_READ |
      FILE_WRITE |
      FILE_TXT |
      FILE_ANSI |
      FILE_SHARE_READ |
      FILE_SHARE_WRITE |
      FILE_COMMON
   );

   if(loggerHandle == INVALID_HANDLE)
   {
      Print(
         "[LOGGER ERROR] Falha ao abrir arquivo. Erro=",
         GetLastError()
      );

      LoggerReady = false;

      return false;
   }


   FileSeek(
      loggerHandle,
      0,
      SEEK_END
   );


   LoggerReady = true;

   return true;
}


//==================================================
// INICIALIZAÇÃO
//==================================================

bool LoggerInit()
{
   LoggerStartTime = TimeCurrent();

   LoggerMessages = 0;

   LoggerReady = false;

   loggerHandle = INVALID_HANDLE;


   if(!LoggerOpen())
      return false;


   if(FileSize(loggerHandle) == 0)
   {
      FileWrite(
         loggerHandle,
         "=============================================="
      );

      FileWrite(
         loggerHandle,
         "XAU_AI_PRO ENTERPRISE LOGGER"
      );

      FileWrite(
         loggerHandle,
         "Start: ",
         TimeToString(
            LoggerStartTime,
            TIME_DATE | TIME_SECONDS
         )
      );

      FileWrite(
         loggerHandle,
         "=============================================="
      );

      FileFlush(loggerHandle);
   }


   LoggerWrite(
      LOG_LEVEL_SYSTEM,
      "Logger inicializado"
   );


   return true;
}


//==================================================
// ESCRITA PRINCIPAL
//==================================================

void LoggerWrite(
   ENUM_LOG_LEVEL level,
   string message,
   string param1 = "",
   string param2 = "",
   string param3 = "",
   string param4 = ""
)
{

   //===============================================
   // FILTRO DE NÍVEL
   //===============================================

   if(level < g_logMinLevel)
      return;


   //===============================================
   // LOGGER NÃO DISPONÍVEL
   //===============================================

   if(!LoggerReady)
   {
      Print(
         "[LOGGER OFFLINE] ",
         LogLevelPrefix(level),
         " ",
         message
      );

      return;
   }


   if(loggerHandle == INVALID_HANDLE)
   {
      LoggerReady = false;

      Print(
         "[LOGGER ERROR] Handle inválido"
      );

      return;
   }


   //===============================================
   // ROTACIONAMENTO
   //===============================================

   LoggerRotate();


   if(!LoggerReady)
      return;


   //===============================================
   // DADOS
   //===============================================

   string timestamp =
      TimeToString(
         TimeCurrent(),
         TIME_DATE | TIME_SECONDS
      );


   string symbol = _Symbol;


   string line =
      timestamp +
      " | " +
      LogLevelPrefix(level) +
      " | " +
      symbol +
      " | " +
      message;


   //===============================================
   // PARÂMETROS
   //===============================================

   if(param1 != "")
      line += " | " + param1;

   if(param2 != "")
      line += " | " + param2;

   if(param3 != "")
      line += " | " + param3;

   if(param4 != "")
      line += " | " + param4;


   //===============================================
   // ESCREVER
   //===============================================

   FileWrite(
      loggerHandle,
      line
   );


   LoggerMessages++;


   //===============================================
   // FLUSH
   //===============================================

   FileFlush(
      loggerHandle
   );


   //===============================================
   // JOURNAL
   //===============================================

   if(
      level == LOG_LEVEL_WARNING ||
      level == LOG_LEVEL_ERROR ||
      level == LOG_LEVEL_TRADE
   )
   {
      Print(line);
   }
}


//==================================================
// INFO
//==================================================

void LogInfo(
   string msg,
   string p1 = "",
   string p2 = "",
   string p3 = "",
   string p4 = ""
)
{
   LoggerWrite(
      LOG_LEVEL_INFO,
      msg,
      p1,
      p2,
      p3,
      p4
   );
}


//==================================================
// WARNING
//==================================================

void LogWarning(
   string msg,
   string p1 = "",
   string p2 = "",
   string p3 = "",
   string p4 = ""
)
{
   LoggerWrite(
      LOG_LEVEL_WARNING,
      msg,
      p1,
      p2,
      p3,
      p4
   );
}


//==================================================
// ERROR
//==================================================

void LogError(
   string msg,
   string p1 = "",
   string p2 = "",
   string p3 = "",
   string p4 = ""
)
{
   LoggerWrite(
      LOG_LEVEL_ERROR,
      msg,
      p1,
      p2,
      p3,
      p4
   );
}


//==================================================
// AI
//==================================================

void LogAI(
   string msg,
   string p1 = "",
   string p2 = "",
   string p3 = "",
   string p4 = ""
)
{
   LoggerWrite(
      LOG_LEVEL_AI,
      msg,
      p1,
      p2,
      p3,
      p4
   );
}


//==================================================
// TRADE
//==================================================

void LogTrade(
   string msg,
   string p1 = "",
   string p2 = "",
   string p3 = "",
   string p4 = ""
)
{
   LoggerWrite(
      LOG_LEVEL_TRADE,
      msg,
      p1,
      p2,
      p3,
      p4
   );
}


//==================================================
// SYSTEM
//==================================================

void LogSystem(
   string msg,
   string p1 = "",
   string p2 = "",
   string p3 = "",
   string p4 = ""
)
{
   LoggerWrite(
      LOG_LEVEL_SYSTEM,
      msg,
      p1,
      p2,
      p3,
      p4
   );
}


//==================================================
// ALTERAR NÍVEL MÍNIMO
//==================================================

void LoggerSetLevel(
   ENUM_LOG_LEVEL level
)
{
   g_logMinLevel = level;
}


//==================================================
// RETORNA NÍVEL ATUAL
//==================================================

ENUM_LOG_LEVEL LoggerGetLevel()
{
   return g_logMinLevel;
}


//==================================================
// ESTADO
//==================================================

bool LoggerIsReady()
{
   return LoggerReady &&
          loggerHandle != INVALID_HANDLE;
}


//==================================================
// QUANTIDADE DE MENSAGENS
//==================================================

ulong LoggerMessageCount()
{
   return LoggerMessages;
}


//==================================================
// TAMANHO DO ARQUIVO
//==================================================

ulong LoggerFileSize()
{
   if(!LoggerIsReady())
      return 0;

   return FileSize(
      loggerHandle
   );
}


//==================================================
// ROTACIONAMENTO
//==================================================

void LoggerRotate()
{
   if(!LoggerIsReady())
      return;

   ulong size =
      FileSize(
         loggerHandle
      );

   if(size < LOGGER_MAX_FILE_SIZE)
      return;


   if(size < LOGGER_MAX_FILE_SIZE)
      return;


   //===============================================
   // FECHAR ARQUIVO ATUAL
   //===============================================

   FileFlush(
      loggerHandle
   );

   FileClose(
      loggerHandle
   );

   loggerHandle = INVALID_HANDLE;

   LoggerReady = false;


   //===============================================
   // APAGAR BACKUP ANTIGO
   //===============================================

   ResetLastError();

   FileDelete(
      LOGGER_BACKUP_NAME,
      FILE_COMMON
   );


   //===============================================
   // MOVER LOG ATUAL PARA BACKUP
   //===============================================

   ResetLastError();

   bool moved =
      FileMove(
         LOGGER_FILE_NAME,
         FILE_COMMON,
         LOGGER_BACKUP_NAME,
         FILE_COMMON | FILE_REWRITE
      );


   if(!moved)
   {
      Print(
         "[LOGGER WARNING] Falha ao rotacionar log. Erro=",
         GetLastError()
      );
   }


   //===============================================
   // ABRIR NOVO LOG
   //===============================================

   if(!LoggerOpen())
   {
      Print(
         "[LOGGER ERROR] Não foi possível reabrir logger após rotação."
      );

      return;
   }


   FileSeek(
      loggerHandle,
      0,
      SEEK_END
   );


   FileWrite(
      loggerHandle,
      "=============================================="
   );

   FileWrite(
      loggerHandle,
      "XAU_AI_PRO LOGGER — NOVO ARQUIVO"
   );

   FileWrite(
      loggerHandle,
      "Time: ",
      TimeToString(
         TimeCurrent(),
         TIME_DATE | TIME_SECONDS
      )
   );

   FileWrite(
      loggerHandle,
      "=============================================="
   );


   FileFlush(
      loggerHandle
   );
}


//==================================================
// FECHAMENTO
//==================================================

void LoggerClose()
{

   if(loggerHandle != INVALID_HANDLE)
   {
      LoggerWrite(
         LOG_LEVEL_SYSTEM,
         "Logger finalizado"
      );


      FileFlush(
         loggerHandle
      );


      FileClose(
         loggerHandle
      );
   }


   loggerHandle = INVALID_HANDLE;

   LoggerReady = false;
}


//==================================================
// TESTE DO LOGGER
//==================================================

void LoggerTest()
{
   LogInfo(
      "Teste INFO"
   );

   LogWarning(
      "Teste WARNING"
   );

   LogError(
      "Teste ERROR"
   );

   LogAI(
      "Teste AI"
   );

   LogTrade(
      "Teste TRADE"
   );

   LogSystem(
      "Teste SYSTEM"
   );
}


#endif