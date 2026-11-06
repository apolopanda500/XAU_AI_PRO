// XAU_AI_PRO v1.2.9
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

// v1.2.95 (02/11/2026) - P1.83: o nome passa a ser POR INSTANCIA.
// MEDIDO no journal de 02/11: 1 366 linhas "[LOGGER OFFLINE]" porque
// LoggerInit() nunca era chamado. Ligar o logger no OnInit sem mudar o
// nome criaria 16 escritores no MESMO ficheiro comum (FILE_COMMON). Cada
// grafico passa a ter o seu: XAU_AI_PRO_<SIMBOLO>_<PERIODO>.log. O journal
// deixa de ter o aviso e o arquivo de cada grafico fica legivel.
string g_loggerFile   = "";
string g_loggerBackup = "";

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

   string nome = (g_loggerFile == "" ? LOGGER_FILE_NAME : g_loggerFile);

   loggerHandle = FileOpen(
      nome,
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

   // v1.2.95 (02/11/2026) - P1.83: fecha um handle anterior (recompilacao
   // recarrega o EA e OnInit volta a correr) e monta o nome POR GRAFICO.
   if(loggerHandle != INVALID_HANDLE)
   {
      FileFlush(loggerHandle);
      FileClose(loggerHandle);
   }

   loggerHandle = INVALID_HANDLE;

   string simbolo = _Symbol;
   StringReplace(simbolo, "\\", "_");
   StringReplace(simbolo, "/", "_");
   StringReplace(simbolo, "#", "_");
   StringReplace(simbolo, ".", "_");

   g_loggerFile   = "XAU_AI_PRO_" + simbolo + "_" + IntegerToString((int)Period()) + ".log";
   g_loggerBackup = g_loggerFile + ".old";


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

   // v1.2.32 (30/10/2026) - P1.3 rodada 4. MEDIDO na v1.2.31, janela
   // 17:30:00-17:35:00 (5 min, 16 graficos, 585 linhas): 95 linhas
   // "[LOGGER OFFLINE]" = ~1 140/hora, o maior emissor que sobrou.
   // A causa nao e o volume de eventos, e estrutural: LoggerInit() NAO e
   // chamado em lugar nenhum do EA (busca recursiva em 30/10/2026), entao
   // LoggerReady e sempre false e TODO LogInfo/LogWarning/LogError deste
   // modulo cai neste fallback. Inicializar um arquivo compartilhado a partir
   // de 16 graficos e decisao separada (16 escritores no mesmo FILE_COMMON,
   // ver PENDENCIAS_20261030.md secao 12). Enquanto ela nao for tomada, o
   // fallback sai 1x/10 min com o contador de registros descartados: o
   // operador continua sabendo que o logger esta fora e quanta informacao
   // esta sendo perdida, sem uma linha por registro.
   // v1.2.59 (P1.40): a janela deste aviso media tempo de MODELO.
   //
   // MEDIDO no segmento v1.2.58 do journal do tester (264 303 linhas):
   // 9 188 linhas [LOGGER OFFLINE], 3,48 por cento de todo o output - passou
   // a ser o MAIOR emissor unico depois de P1.25 a P1.35. O throttle de
   // 600 s existia desde a v1.2.32, mas contava sobre TimeCurrent(), que no
   // Strategy Tester e o relogio acelerado da serie de precos: 3 meses de
   // modelo passam em minutos de execucao real, logo "600 s" disparava
   // milhares de vezes. E o espelho exacto do defeito do P1.24, onde a
   // mesma confusao congelava o watchdog com o mercado fechado.
   //
   // A janela passou a TimeLocal() (600 s -> 3600 s).
   //
   // v1.2.60 (P1.42): a justificacao escrita na primeira versao dizia que
   // TimeLocal() seria "relogio de parede" e isso NAO e verdade no tester.
   // MEDIDO no run 7703264373217955650 (v1.2.59): os avisos saem com tempo de
   // MODELO exactamente de hora a hora (01:03, 02:03 ... 15:03) enquanto o
   // relogio do computador andou ~2 min 36 s. Ou seja o Strategy Tester
   // virtualiza TAMBEM o TimeLocal(); so TimeCurrent() (mercado) e o relogio
   // simulado ja era sabido, agora sabe-se que sao os dois.
   //
   // O ganho e real e medido: 3,48 % -> 0,54 % do output (9 188 -> 15 linhas
   // numa amostra de 2 774). Mas vem de alargar a janela de tempo de MODELO,
   // nao de trocar de relogio. A frase "1 linha por hora" continua verdadeira
   // em PRODUCAO (onde TimeLocal() e o relogio do computador) e passa a ser
   // falsa no tester - por isso o texto deixou de prometer "relogio de
   // parede" e diz apenas o intervalo.
   //
   // A causa raiz NAO e o volume: LoggerInit() nunca e chamado em nenhum
   // ficheiro do EA, por isso LoggerReady e sempre false e todo o LogInfo/
   // LogWarning/LogError deste modulo cai aqui. Iniciar um ficheiro comum
   // partilhado por 17 graficos e decisao separada (PENDENCIAS, secao 12) e
   // nao foi tomada aqui. Enquanto o logger estiver fora, o operador
   // continua a saber disso e de quantos registos se perdem.
   if(!LoggerReady)
   {
      // v1.2.61 (P1.43): este fallback tinha UMA janela para todos os niveis,
      // por isso um INFO que chegasse primeiro consumia a vez e um ERROR
      // esperava a hora seguinte - ou nunca saia.
      //
      // MEDIDO em 01/11/2026 sobre as amostras que o proprio fallback imprime:
      // producao 654 amostras (16 de nivel ERROR "HealthMonitor: timeout de
      // tick", 638 SYSTEM "Statistics inicializado"); tester 19 448 amostras
      // (17 843 INFO "HEALTH OK", 1 233 ERROR "timeout de tick", 303 TRADE,
      // 64 SYSTEM). O unico registo de nivel ERROR do modulo - o proprio erro
      // que o operador precisa de ver - era o que estava a ser abafado.
      //
      // Agora ha DUAS janelas de 3600 s independentes: uma para WARNING/ERROR
      // e outra para os restantes niveis. O volume fica limitado por
      // construcao a mais 1 linha por hora por instancia no pior caso, e o
      // contador de abafados continua em cada linha, para que nada se perca em
      // silencio.
      //
      // O enum ENUM_LOG_LEVEL nao ordena por gravidade (SYSTEM=5, INFO=0, mas
      // SYSTEM e o menos grave), por isso a classificacao e por IGUALDADE
      // explicita - a mesma forma que a linha 390 deste ficheiro ja usa.
      static datetime s_lastOfflineLog     = 0;
      static datetime s_lastOfflineImp     = 0;
      static long     s_offlineDropped     = 0;
      static long     s_offlineDroppedImp  = 0;

      bool     importante = (level == LOG_LEVEL_WARNING || level == LOG_LEVEL_ERROR);
      datetime offlineNow = TimeLocal();

      if(importante)
        {
         s_offlineDroppedImp++;

         if(s_lastOfflineImp == 0 || (offlineNow - s_lastOfflineImp) >= 3600)
           {
            s_lastOfflineImp = offlineNow;
            Print("[LOGGER OFFLINE] ", LogLevelPrefix(level), " ", message,
                  " | LoggerInit() nao chamado | descartados importantes=",
                  IntegerToString(s_offlineDroppedImp), " | aviso 1x/3600 s");
            s_offlineDroppedImp = 0;
           }

         return;
        }

      s_offlineDropped++;

      if(s_lastOfflineLog == 0 || (offlineNow - s_lastOfflineLog) >= 3600)
        {
         s_lastOfflineLog = offlineNow;
         Print("[LOGGER OFFLINE] ", LogLevelPrefix(level), " ", message,
               " | LoggerInit() nao chamado | descartados=",
               IntegerToString(s_offlineDropped), " | aviso 1x/3600 s");
         s_offlineDropped = 0;
        }

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
      (g_loggerBackup == "" ? LOGGER_BACKUP_NAME : g_loggerBackup),
      FILE_COMMON
   );


   //===============================================
   // MOVER LOG ATUAL PARA BACKUP
   //===============================================

   ResetLastError();

   bool moved =
      FileMove(
         (g_loggerFile == "" ? LOGGER_FILE_NAME : g_loggerFile),
         FILE_COMMON,
         (g_loggerBackup == "" ? LOGGER_BACKUP_NAME : g_loggerBackup),
         FILE_COMMON | FILE_REWRITE
      );


   if(!moved)
   {
      // P2.23 (04/11/2026): a rotacao falhava a cada minuto e o log crescia
      // sem limite. MEDIDO no Strategy Tester (XAUUSD H1, 01/09 a 01/11/2026,
      // v1.2.131): 36 MB de log e "[LOGGER WARNING] Falha ao rotacionar log.
      // Erro=5004" 1x por minuto simulado. O rename do ficheiro comum nao se
      // concretiza enquanto o agente escreve, e como o tamanho nunca voltava a
      // zero a condicao de rotacao era verdadeira outra vez no minuto seguinte.
      // Correcao: o aviso sai 1x por hora (e estado, nao evento) e o ficheiro
      // atual e TRUNCADO, para o tamanho voltar a zero. O conteudo anterior
      // perde-se porque o backup nao foi atualizado - e o mal menor face a um
      // log de tamanho ilimitado, que em conta real enche o disco do terminal.
      // Nenhuma regra de entrada, saida, lote, alvo, stop ou risco muda: muda
      // o tamanho e a frequencia de uma linha de diagnostico.
      int rotErr = GetLastError();

      int truncHandle =
         FileOpen(
            (g_loggerFile == "" ? LOGGER_FILE_NAME : g_loggerFile),
            FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON
         );

      bool truncated = (truncHandle != INVALID_HANDLE);

      if(truncated)
         FileClose(truncHandle);

      static datetime rotWarnTs = 0;
      datetime rotNow = TimeLocal();

      if(rotWarnTs == 0 || (rotNow - rotWarnTs) >= 3600)
      {
         rotWarnTs = rotNow;

         Print(
            "[LOGGER WARNING] Falha ao rotacionar log. Erro=", rotErr,
            " | fallback=", (truncated ? "log atual truncado" : "sem truncagem"),
            " | 1 aviso por hora"
         );
      }
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