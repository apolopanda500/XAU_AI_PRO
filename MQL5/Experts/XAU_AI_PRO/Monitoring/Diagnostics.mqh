// XAU_AI_PRO v1.2.0
#ifndef DIAGNOSTICS_MQH
#define DIAGNOSTICS_MQH

#include "../Core/Config.mqh"
#include "../AI/AIClient.mqh"
#include "Logger.mqh"
#include "HealthMonitor.mqh"
#include "../Core/PerformanceAnalyzer.mqh"

#include "../Indicators/VolatilityFilter.mqh"
#include "../Indicators/ADX.mqh"
#include "../Indicators/RSI.mqh"

//==================================================
// XAU_AI_PRO - DIAGNOSTICS PRO
// Multi-Symbol / Python / JSON / Dataset
//==================================================

struct DiagnosticResult
{
   string name;
   bool   passed;
   string detail;
};

DiagnosticResult g_diagnostics[];


//==================================================
// ADICIONA RESULTADO
//==================================================

void DiagnosticsAdd(
   int &index,
   string name,
   bool passed,
   string detail=""
)
{
   ArrayResize(
      g_diagnostics,
      index + 1
   );

   g_diagnostics[index].name   = name;
   g_diagnostics[index].passed = passed;
   g_diagnostics[index].detail = detail;

   index++;
}


//==================================================
// DIAGNOSTICO PRINCIPAL
//==================================================

bool DiagnosticsRun()
{
   ArrayResize(
      g_diagnostics,
      0
   );

   int idx = 0;

   LogSystem(
      "Iniciando diagnostico completo..."
   );


//==================================================
// BROKER / TERMINAL
//==================================================

   bool brokerOK = true;
   string brokerDetail = "";

   if(!TerminalInfoInteger(
         TERMINAL_CONNECTED
      ))
   {
      brokerOK = false;
      brokerDetail =
         "Terminal nao conectado";
   }
   else
   {
      double bid =
         SymbolInfoDouble(
            _Symbol,
            SYMBOL_BID
         );

      if(bid <= 0.0)
      {
         brokerOK = false;
         brokerDetail =
            "Sem cotacao valida do simbolo";
      }
   }

   DiagnosticsAdd(
      idx,
      "Broker",
      brokerOK,
      brokerDetail
   );


//==================================================
// CONTA
//==================================================

   bool accountOK = true;
   string accountDetail = "";

   long accountNumber =
      AccountInfoInteger(
         ACCOUNT_LOGIN
      );

   if(accountNumber <= 0)
   {
      accountOK = false;
      accountDetail =
         "Conta nao identificada";
   }

   DiagnosticsAdd(
      idx,
      "Conta",
      accountOK,
      accountDetail
   );


//==================================================
// PERMISSOES
//==================================================

   bool permOK = true;
   string permDetail = "";

   if(!TerminalInfoInteger(
         TERMINAL_TRADE_ALLOWED
      ))
   {
      permOK = false;
      permDetail =
         "Trading nao permitido pelo terminal";
   }

   DiagnosticsAdd(
      idx,
      "Permissoes",
      permOK,
      permDetail
   );


//==================================================
// SIMBOLO
//==================================================

   bool symbolOK = true;
   string symbolDetail = "";

   if(!SymbolSelect(
         _Symbol,
         true
      ))
   {
      symbolOK = false;
      symbolDetail =
         "Simbolo nao disponivel";
   }

   double symbolPoint =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_POINT
      );

   if(symbolPoint <= 0.0)
   {
      symbolOK = false;

      if(symbolDetail == "")
         symbolDetail =
            "SYMBOL_POINT invalido";
   }

   DiagnosticsAdd(
      idx,
      "Simbolo",
      symbolOK,
      symbolDetail
   );


//==================================================
// PYTHON / JSON (hardening ETAPA 14)
//==================================================

   bool pythonOK = true;
   string pythonDetail = "";

   string predFile =
      "Data\\prediction_" +
      _Symbol +
      ".json";

   // ETAPA 14 (hardening): em modo sem IA obrigatoria
   // (RequireAIJSON=false) a ausencia de prediction_*.json
   // e o normal (backtest/forward sem pipeline Python).
   // Nao deve gerar FALHA de diagnostico (falso positivo).
   int predHandle =
      FileOpen(
         predFile,
         FILE_READ |
         FILE_ANSI
      );

   if(RequireAIJSON && predHandle == INVALID_HANDLE)
   {
      pythonOK = false;

      pythonDetail =
         "Prediction JSON nao encontrado: " +
         predFile;
   }
   else
   if(!RequireAIJSON && predHandle == INVALID_HANDLE)
   {
      pythonDetail =
         "RequireAIJSON=false (verificacao informativa)";
   }
   else
   {
      string content =
         FileReadString(
            predHandle
         );

      FileClose(
         predHandle
      );

      if(StringLen(content) == 0)
      {
         pythonOK = false;

         pythonDetail =
            "Prediction JSON vazio";
      }
      else
      {
         if(
            StringFind(
               content,
               "{"
            ) < 0 ||
            StringFind(
               content,
               "}"
            ) < 0
         )
         {
            pythonOK = false;

            pythonDetail =
               "Prediction JSON sem estrutura basica";
         }
      }
   }

   DiagnosticsAdd(
      idx,
      "Python",
      pythonOK,
      pythonDetail
   );


//==================================================
// JSON
//==================================================

   bool jsonOK = true;
   string jsonDetail = "";

   // ETAPA 14 (hardening): mesma regra do bloco Python.
   int jsonHandle =
      FileOpen(
         predFile,
         FILE_READ |
         FILE_ANSI
      );

   if(RequireAIJSON && jsonHandle == INVALID_HANDLE)
   {
      jsonOK = false;

      jsonDetail =
         "Arquivo JSON ausente";
   }
   else
   if(!RequireAIJSON && jsonHandle == INVALID_HANDLE)
   {
      jsonDetail =
         "RequireAIJSON=false (verificacao informativa)";
   }
   else
   {
      string jsonContent =
         FileReadString(
            jsonHandle
         );

      FileClose(
         jsonHandle
      );

      if(StringLen(jsonContent) < 2)
      {
         jsonOK = false;

         jsonDetail =
            "JSON vazio ou incompleto";
      }
      else
      {
         int openPos =
            StringFind(
               jsonContent,
               "{"
            );

         int closePos =
            StringFind(
               jsonContent,
               "}"
            );

         if(
            openPos < 0 ||
            closePos < 0 ||
            closePos <= openPos
         )
         {
            jsonOK = false;

            jsonDetail =
               "Estrutura JSON invalida";
         }
      }
   }

   DiagnosticsAdd(
      idx,
      "JSON",
      jsonOK,
      jsonDetail
   );


//==================================================
// DATASET CSV
//==================================================

   bool csvOK = true;
   string csvDetail = "";

   string datasetFile =
      "Data\\dataset.csv";

   // ETAPA 14 (hardening): se EnableDataset=false a ausencia
   // de dataset.csv e esperada; nao deve ser FALHA.
   int csvHandle =
      FileOpen(
         datasetFile,
         FILE_READ |
         FILE_ANSI
      );

   if(EnableDataset && csvHandle == INVALID_HANDLE)
   {
      csvOK = false;

      csvDetail =
         "dataset.csv nao encontrado";
   }
   else
   if(!EnableDataset && csvHandle == INVALID_HANDLE)
   {
      csvDetail =
         "EnableDataset=false (verificacao informativa)";
   }
   else
   {
      ulong csvSize =
         FileSize(
            csvHandle
         );

      if(csvSize == 0)
      {
         csvOK = false;

         csvDetail =
            "dataset.csv vazio";
      }

      FileClose(
         csvHandle
      );
   }

   DiagnosticsAdd(
      idx,
      "CSV",
      csvOK,
      csvDetail
   );


//==================================================
// INDICADORES
//==================================================

   bool indicatorsOK = true;
   string indicatorsDetail = "";

   double atr =
      GetATR(
         _Symbol
      );

   double adx =
      GetADX(
         _Symbol
      );

   double rsi =
      GetRSI(
         _Symbol
      );

   if(atr <= 0.0)
   {
      indicatorsOK = false;

      indicatorsDetail +=
         "ATR invalido; ";
   }

   if(adx < 0.0)
   {
      indicatorsOK = false;

      indicatorsDetail +=
         "ADX invalido; ";
   }

   if(rsi < 0.0 || rsi > 100.0)
   {
      indicatorsOK = false;

      indicatorsDetail +=
         "RSI invalido; ";
   }

   DiagnosticsAdd(
      idx,
      "Indicadores",
      indicatorsOK,
      indicatorsDetail
   );


//==================================================
// SISTEMA
//==================================================

   bool systemOK = true;
   string systemDetail = "";

   long memory =
      TerminalInfoInteger(
         TERMINAL_MEMORY_PHYSICAL
      );

   if(memory <= 0)
   {
      systemOK = false;

      systemDetail =
         "Memoria fisica nao identificada";
   }

   DiagnosticsAdd(
      idx,
      "Sistema",
      systemOK,
      systemDetail
   );


//==================================================
// ARQUIVOS / ESCRITA
//==================================================

   bool filesOK = true;
   string filesDetail = "";

   string testFile =
      "Data\\diagnostics_test.tmp";

   int fileHandle =
      FileOpen(
         testFile,
         FILE_COMMON |
         FILE_WRITE |
         FILE_ANSI
      );

   if(fileHandle == INVALID_HANDLE)
   {
      filesOK = false;

      filesDetail =
         "Sem permissao de escrita";
   }
   else
   {
      FileWrite(
         fileHandle,
         "XAU_AI_PRO_DIAGNOSTIC_TEST"
      );

      FileFlush(
         fileHandle
      );

      FileClose(
         fileHandle
      );

      FileDelete(
         testFile, FILE_COMMON
      );
   }

   DiagnosticsAdd(
      idx,
      "Arquivos",
      filesOK,
      filesDetail
   );


//==================================================
// IA
//==================================================

   bool aiOK = true;
   string aiDetail = "";

   // ETAPA 14 (hardening): se EnableAIFilter=false o EA opera
   // sem IA; "AI Client nao conectado" nao e falha nesse modo.
   if(EnableAIFilter && !AIClientConnected())
   {
      aiOK = false;

      aiDetail =
         "AI Client nao conectado";
   }
   else
   if(!EnableAIFilter)
   {
      aiDetail =
         "EnableAIFilter=false (verificacao informativa)";
   }

   DiagnosticsAdd(
      idx,
      "IA",
      aiOK,
      aiDetail
   );


//==================================================
// RESULTADO FINAL
//==================================================

   bool allPassed = true;

   string summary = "";

   for(
      int i = 0;
      i < ArraySize(g_diagnostics);
      i++
   )
   {
      string status =
         g_diagnostics[i].passed
         ? "VERDE"
         : "VERMELHO";


      summary +=
         g_diagnostics[i].name +
         ": " +
         status;


      if(
         g_diagnostics[i].detail != ""
      )
      {
         summary +=
            " (" +
            g_diagnostics[i].detail +
            ")";
      }


      summary += "\n";


      if(
         !g_diagnostics[i].passed
      )
      {
         allPassed = false;
      }
   }


//==================================================
// LOG FINAL
//==================================================

   if(allPassed)
   {
      LogSystem(
         "Diagnostico: TODOS OS TESTES PASSARAM"
      );
   }
   else
   {
      LogError(
         "Diagnostico: FALHAS DETECTADAS",
         summary
      );
   }


   return allPassed;
}


//==================================================
// SUMMARY
//==================================================

string DiagnosticsGetSummary()
{
   string summary =
      "=== DIAGNOSTICS ===\n";


   for(
      int i = 0;
      i < ArraySize(g_diagnostics);
      i++
   )
   {
      string status =
         g_diagnostics[i].passed
         ? "OK"
         : "FALHA";


      summary +=
         g_diagnostics[i].name +
         ": " +
         status;


      if(
         g_diagnostics[i].detail != ""
      )
      {
         summary +=
            " - " +
            g_diagnostics[i].detail;
      }


      summary += "\n";
   }


   return summary;
}


//==================================================
// ALL PASSED
//==================================================

bool DiagnosticsAllPassed()
{
   for(
      int i = 0;
      i < ArraySize(g_diagnostics);
      i++
   )
   {
      if(
         !g_diagnostics[i].passed
      )
      {
         return false;
      }
   }


   return true;
}


#endif
