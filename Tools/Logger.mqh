#ifndef LOGGER_MQH
#define LOGGER_MQH

//==================================================
// LOGGER PROFISSIONAL - FASE 8.1
//
// API:
//   LogInit(filename, rotateDaily, maxSizeMB)
//   LogSetLevel(minLevel)
//   LogSetOutput(output)
//   Log(level, module, message)
//   LogDebug/Info/Warn/Error/AI/Trade/System
//   LogFlush() / LogClose()
//
// Formato:
//   [YYYY-MM-DD HH:MM:SS.mmm] [LEVEL ] [Module] message
//
// Compilacao condicional: se ENABLE_PROFESSIONAL_LOGGING=0,
// todas as funcoes viram no-op (zero overhead).
//==================================================

#ifndef ENABLE_PROFESSIONAL_LOGGING
   #define ENABLE_PROFESSIONAL_LOGGING 1
#endif

#if ENABLE_PROFESSIONAL_LOGGING == 1

enum ENUM_LOG_LEVEL
{
   LOG_DEBUG  = 0,
   LOG_INFO   = 1,
   LOG_WARN   = 2,
   LOG_ERROR  = 3,
   LOG_AI     = 4,
   LOG_TRADE  = 5,
   LOG_SYSTEM = 6
};

enum ENUM_LOG_OUTPUT
{
   LOG_OUT_FILE  = 0,
   LOG_OUT_PRINT = 1,
   LOG_OUT_BOTH  = 2
};

int    g_logHandle          = INVALID_HANDLE;
int    g_logMinLevel        = LOG_INFO;
int    g_logOutput          = LOG_OUT_BOTH;
string g_logFileName        = "XAU_AI_PRO.log";
string g_logBaseName        = "XAU_AI_PRO";
string g_logFolder          = "Logs";
int    g_logMaxSizeBytes    = 10 * 1024 * 1024;
bool   g_logRotateDaily     = true;
string g_logCurrentDate     = "";
bool   g_logInitialized     = false;
int    g_logRotateCount     = 0;
int    g_logFlushCounter    = 0;
int    g_logFlushInterval   = 20;

void   LogWriteRaw(string line);
string LogLevelToString(ENUM_LOG_LEVEL level);
string LogTimestamp();
void   LogCheckRotation();
bool   LogRotateFile();

bool LogInit(string filename="XAU_AI_PRO.log",
             bool rotateDaily=true,
             int maxSizeMB=10)
{
   if(g_logInitialized)
      return true;

   g_logBaseName = filename;
   int dotPos = StringFind(filename, ".", 0);
   if(dotPos > 0)
      g_logBaseName = StringSubstr(filename, 0, dotPos);

   g_logFileName     = filename;
   g_logRotateDaily  = rotateDaily;
   g_logMaxSizeBytes = maxSizeMB * 1024 * 1024;
   if(g_logMaxSizeBytes < 1024)
      g_logMaxSizeBytes = 1024;

   g_logFolder      = "Logs";
   g_logCurrentDate = TimeToString(TimeCurrent(), TIME_DATE);
   g_logHandle      = INVALID_HANDLE;
   g_logInitialized = true;
   g_logRotateCount = 0;

   string header = "==== XAU_AI_PRO LOGGER STARTED " +
                   TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) +
                   " ====";
   LogWriteRaw(header);
   LogInfo("Logger", "Logger inicializado: " + filename +
          " | rotateDaily=" + (rotateDaily ? "true" : "false") +
          " | maxSizeMB=" + IntegerToString(maxSizeMB));
   return true;
}

void LogSetLevel(ENUM_LOG_LEVEL minLevel) { g_logMinLevel = (int)minLevel; }
void LogSetOutput(ENUM_LOG_OUTPUT output) { g_logOutput   = (int)output;  }

string LogTimestamp()
{
   MqlDateTime tm;
   TimeToStruct(TimeLocal(), tm);
   return StringFormat("%04d-%02d-%02d %02d:%02d:%02d",
                       tm.year, tm.mon, tm.day,
                       tm.hour, tm.min, tm.sec);
}

string LogLevelToString(ENUM_LOG_LEVEL level)
{
   switch(level)
   {
      case LOG_DEBUG:  return "DEBUG";
      case LOG_INFO:   return "INFO ";
      case LOG_WARN:   return "WARN ";
      case LOG_ERROR:  return "ERROR";
      case LOG_AI:     return "AI   ";
      case LOG_TRADE:  return "TRADE";
      case LOG_SYSTEM: return "SYSTEM";
      default:         return "?????";
   }
}

void LogCheckRotation()
{
   if(!g_logInitialized)
      return;

   if(g_logRotateDaily)
   {
      string today = TimeToString(TimeCurrent(), TIME_DATE);
      if(today != g_logCurrentDate)
      {
         g_logCurrentDate = today;
         LogRotateFile();
         return;
      }
   }

   if(g_logHandle != INVALID_HANDLE)
   {
      long size = FileSize(g_logHandle);
      if(size > 0 && size >= g_logMaxSizeBytes)
         LogRotateFile();
   }
}

bool LogRotateFile()
{
   if(g_logHandle != INVALID_HANDLE)
   {
      FileClose(g_logHandle);
      g_logHandle = INVALID_HANDLE;
   }

   g_logRotateCount++;
   string newName = g_logBaseName + "_" +
                    TimeToString(TimeCurrent(), TIME_DATE) + "_" +
                    IntegerToString(g_logRotateCount) + ".log";

   string oldPath = g_logFolder + "\\" + g_logFileName;
   string newPath = g_logFolder + "\\" + newName;
   if(FileIsExist(oldPath))
      FileMove(oldPath, 0, newPath, FILE_REWRITE);

   return true;
}

void LogWriteRaw(string line)
{
   if(!g_logInitialized)
      return;

   LogCheckRotation();

   string fullPath = g_logFolder + "\\" + g_logFileName;
   g_logHandle = FileOpen(fullPath,
                          FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ,
                          '\n');

   if(g_logHandle == INVALID_HANDLE)
   {
      g_logHandle = FileOpen(g_logFileName,
                             FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,
                             '\n');
      if(g_logHandle == INVALID_HANDLE)
         return;
   }

   FileSeek(g_logHandle, 0, SEEK_END);
   FileWriteString(g_logHandle, line + "\n");

   g_logFlushCounter++;
   if(g_logFlushCounter >= g_logFlushInterval)
   {
      FileFlush(g_logHandle);
      g_logFlushCounter = 0;
   }

   FileClose(g_logHandle);
   g_logHandle = INVALID_HANDLE;
}

void Log(ENUM_LOG_LEVEL level, string module, string message)
{
   if(!g_logInitialized)
      LogInit();

   if((int)level < g_logMinLevel)
      return;

   string line = "[" + LogTimestamp() + "] [" +
                 LogLevelToString(level) + "] [" +
                 module + "] " + message;

   if(g_logOutput == LOG_OUT_FILE || g_logOutput == LOG_OUT_BOTH)
      LogWriteRaw(line);

   if(g_logOutput == LOG_OUT_PRINT || g_logOutput == LOG_OUT_BOTH)
      Print(line);

   if(level == LOG_ERROR)
      g_logFlushCounter = g_logFlushInterval;
}

void LogDebug(string module, string msg)  { Log(LOG_DEBUG,  module, msg); }
void LogInfo(string module, string msg)   { Log(LOG_INFO,   module, msg); }
void LogWarn(string module, string msg)   { Log(LOG_WARN,   module, msg); }
void LogError(string module, string msg)  { Log(LOG_ERROR,  module, msg); }
void LogAI(string module, string msg)     { Log(LOG_AI,     module, msg); }
void LogTrade(string module, string msg)  { Log(LOG_TRADE,  module, msg); }
void LogSystem(string module, string msg) { Log(LOG_SYSTEM, module, msg); }

void LogFlush()
{
   if(g_logHandle != INVALID_HANDLE)
   {
      FileFlush(g_logHandle);
      FileClose(g_logHandle);
      g_logHandle = INVALID_HANDLE;
   }
   g_logFlushCounter = 0;
}

void LogClose()
{
   if(!g_logInitialized)
      return;
   LogInfo("Logger", "Logger finalizado");
   LogFlush();
   g_logInitialized = false;
}

#else

enum ENUM_LOG_LEVEL { LOG_DEBUG=0, LOG_INFO=1, LOG_WARN=2, LOG_ERROR=3, LOG_AI=4, LOG_TRADE=5, LOG_SYSTEM=6 };
enum ENUM_LOG_OUTPUT { LOG_OUT_FILE=0, LOG_OUT_PRINT=1, LOG_OUT_BOTH=2 };
bool LogInit(string f="x", bool r=true, int m=10) { return true; }
void LogSetLevel(ENUM_LOG_LEVEL l) {}
void LogSetOutput(ENUM_LOG_OUTPUT o) {}
void Log(ENUM_LOG_LEVEL l, string m, string msg) {}
void LogDebug(string m, string msg) {}
void LogInfo(string m, string msg)  {}
void LogWarn(string m, string msg)  {}
void LogError(string m, string msg) {}
void LogAI(string m, string msg)    {}
void LogTrade(string m, string msg) {}
void LogSystem(string m, string msg) {}
void LogFlush() {}
void LogClose() {}

#endif

#endif
