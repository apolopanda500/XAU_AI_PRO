// XAU_AI_PRO v1.2.9
#ifndef DIAGNOSTICS_MQH
#define DIAGNOSTICS_MQH

#include "../Core/Config.mqh"
#include "../AI/AIClient.mqh"
#include "Logger.mqh"
#include "HealthMonitor.mqh"
#include "../Core/PerformanceAnalyzer.mqh"
#include "../Core/TradeGate.mqh"   // P1.63: veredito unico de negociacao

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
// LEITURA INTEGRAL DE ARQUIVO (v1.2.15)
//
// FileReadString sem comprimento le APENAS a primeira linha. Um prediction_*.json
// formatado (com quebras) chegava ao teste como "*{" e reprovava Python/JSON no
// diagnostico por engano. Aqui o arquivo vem inteiro, com FILE_SHARE_* porque
// varias instancias do EA abrem o mesmo arquivo.
//==================================================
string DiagnosticsReadWholeFile(string name)
{
   // v1.2.73: leitura em MODO BINARIO. Em FILE_TXT o FileReadString para no fim
   // da linha, mesmo com comprimento explicito: de um prediction_*.json formatado
   // chegava apenas "{" - a chave de fechamento nunca era vista e o diagnostico
   // reprovava um arquivo valido ("sem estrutura basica").
   int h = FileOpen(name,
               FILE_READ | FILE_BIN |
               FILE_SHARE_READ | FILE_SHARE_WRITE);

   if(h == INVALID_HANDLE)
      return("");

   ulong size = FileSize(h);
   string out = "";

   if(size > 0)
   {
      int wanted = (int)MathMin((double)size, 65536.0);
      uchar bytes[];
      ArrayResize(bytes, wanted);

      int lidos = (int)FileReadArray(h, bytes, 0, wanted);

      if(lidos > 0)
         out = CharArrayToString(bytes, 0, lidos, CP_UTF8);
   }

   FileClose(h);

   return(out);
}

//==================================================
// ESTRUTURA JSON - CRITERIO UNICO (v1.2.73)
// Os blocos Python e JSON do diagnostico usam ESTA funcao. Antes cada um testava
// as chaves a sua maneira e o MESMO arquivo podia receber dois veredictos
// diferentes nos dois blocos. Criterio: existe "{" e existe "}" depois dele.
//==================================================
bool DiagnosticsJsonStructureOK(string content)
{
   int openPos = StringFind(content, "{");

   if(openPos < 0)
      return(false);

   int closePos = StringFind(content, "}");

   if(closePos < 0 || closePos <= openPos)
      return(false);

   return(true);
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

   // P1.64: le a fonte unica (mesmo bit, mesma frase que as checklists)
   if(!CTradeGate::Connected())
   {
      brokerOK = false;
      brokerDetail =
         CTradeGate::Cause(TG_DISCONNECTED);
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

   // P1.63 (MEDIDO em 02/11 08:34): este bloco testava UM dos cinco bits
   // (TERMINAL_TRADE_ALLOWED) e o diagnostico imprimia "Permissoes: VERDE"
   // enquanto as 16 ordens eram barradas por MQL_TRADE_ALLOWED=0. O mesmo
   // dado, dois veredictos. Passa a ler a fonte unica (Core/TradeGate.mqh)
   // e a devolver a CAUSA, nao apenas o bit.
   ETradeGate permGate = CTradeGate::EvaluateSuite();   // P1.89: veredicto da suite, igual as checklists

   bool permOK = (permGate == TG_OK);

   // v1.2.89 (02/11/2026) - P1.76: a causa de TG_MQL_OFF tem ~900 caracteres
   // e saia 16x por arranque (30 linhas [DIAG] + [CRITICAL] na janela de
   // 1 200 linhas medida em 02/11 19:47). O codigo do portao identifica o
   // bit que falhou sem ambiguidade, e o texto completo continua a sair uma
   // vez por conta no [TRADE BLOCK].
   string permDetail = "";
   if(permGate != TG_OK)
      permDetail = "codigo=" + IntegerToString((int)permGate) +
                   " | causa completa em [TRADE BLOCK]";

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
   if(RequireAIJSON && !FileIsExist(predFile))
   {
      pythonOK = false;

      pythonDetail =
         "Prediction JSON nao encontrado: " +
         predFile;
   }
   else
   if(!RequireAIJSON && !FileIsExist(predFile))
   {
      pythonDetail =
         "RequireAIJSON=false (verificacao informativa)";
   }
   else
   {
      string content =
         DiagnosticsReadWholeFile(
            predFile
         );

      if(StringLen(content) == 0)
      {
         pythonOK = false;

         pythonDetail =
            "Prediction JSON vazio";
      }
      else
      {
         if(!DiagnosticsJsonStructureOK(content))
         {
            pythonOK = false;

            pythonDetail =
               "Prediction JSON sem estrutura basica (len=" +
               IntegerToString(StringLen(content)) + ")";
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
   if(RequireAIJSON && !FileIsExist(predFile))
   {
      jsonOK = false;

      jsonDetail =
         "Arquivo JSON ausente";
   }
   else
   if(!RequireAIJSON && !FileIsExist(predFile))
   {
      jsonDetail =
         "RequireAIJSON=false (verificacao informativa)";
   }
   else
   {
      string jsonContent =
         DiagnosticsReadWholeFile(
            predFile
         );

      if(StringLen(jsonContent) < 2)
      {
         jsonOK = false;

         jsonDetail =
            "JSON vazio ou incompleto";
      }
      else
      {
         if(!DiagnosticsJsonStructureOK(jsonContent))
         {
            jsonOK = false;

            jsonDetail =
               "Estrutura JSON invalida (len=" +
               IntegerToString(StringLen(jsonContent)) + ")";
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
   // v1.2.14: FILE_SHARE_* e obrigatorio aqui. Sem share, o MQL5 abre o CSV
   // em modo exclusivo e o arquivo aparece como "nao encontrado" sempre que
   // OUTRA instancia do EA o mantem aberto para escrita - falso positivo que
   // poluia o journal com [ERROR] Diagnostico a cada recarga.
   int csvHandle =
      FileOpen(
         datasetFile,
         FILE_READ |
         FILE_ANSI |
         FILE_SHARE_READ |
         FILE_SHARE_WRITE
      );

   if(csvHandle == INVALID_HANDLE)
   {
      if(FileIsExist(datasetFile))
      {
         csvOK = false;

         csvDetail =
            "dataset.csv existe mas nao abriu | err=" +
            IntegerToString(GetLastError());
      }
      else
      {
         // O dataset e CRIADO pelo EA (SaveDatasetCSV). Ausencia no init e o
         // estado inicial normal, nao falha: a escrita ja foi validada no
         // teste "Arquivos".
         csvDetail =
            (EnableDataset
             ? "dataset.csv sera criado pelo EA (SaveDatasetCSV)"
             : "EnableDataset=false (verificacao informativa)");
      }
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

   // v1.2.124 (03/11/2026) - P2.14: MEDIDO no journal de 03/11 as 06:57:39
   // (GBPUSD H1): o arranque imprimiu "[DIAG] FALHAS DETECTADAS" e a UNICA
   // reprovacao foi "[DIAG] FALHA | Indicadores | ADX invalido", no MESMO
   // reload em que "[DIAG] TODOS OS TESTES PASSARAM" saia noutro grafico.
   // Causa: GetATR/GetADX/GetRSI devolvem 0 ou -1 quando o handle EXISTE mas o
   // indicador ainda nao tem barras calculadas - BarsCalculated() == 0 no
   // OnInit, porque o MT5 calcula indicadores de forma assincrona - e este
   // check tratava "ainda a aquecer" como falha. O autoteste de arranque so
   // pode provar o HANDLE: invalido = falha real de criacao; valido com
   // leitura ainda ausente = aquecimento, e a ausencia de leitura em operacao
   // continua a ser reportada pelo watchdog do HealthMonitor e pelo
   // [DATA] SEM LEITURA. Nenhum limite, regra de entrada ou de saida, lote,
   // spread, alvo, precificacao ou parametro de risco muda.
   if(atr <= 0.0)
   {
      if(volatilityATRHandle == INVALID_HANDLE)
      {
         indicatorsOK = false;

         indicatorsDetail +=
            "ATR invalido (handle); ";
      }
      else
      {
         indicatorsDetail +=
            "ATR em aquecimento (init); ";
      }
   }

   if(adx < 0.0)
   {
      if(adxHandle == INVALID_HANDLE)
      {
         indicatorsOK = false;

         indicatorsDetail +=
            "ADX invalido (handle); ";
      }
      else
      {
         indicatorsDetail +=
            "ADX em aquecimento (init); ";
      }
   }

   if(rsi < 0.0 || rsi > 100.0)
   {
      if(rsiHandle == INVALID_HANDLE || rsi > 100.0)
      {
         indicatorsOK = false;

         indicatorsDetail +=
            "RSI invalido; ";
      }
      else
      {
         indicatorsDetail +=
            "RSI em aquecimento (init); ";
      }
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
      // v1.2.96 (03/11/2026) - P1.87: a pasta "Data" NAO existe dentro da
      // Common (so existe Files) e o FileOpen do MQL5 nao cria directorias.
      // O teste falhava sempre e imprimia "Sem permissao de escrita" com a
      // permissao boa. MEDIDO no arranque de 03/11 23:50: 6 falsos negativos
      // em 15 instancias. Pasta existente + nome por instancia para os 15
      // graficos nao disputarem o mesmo ficheiro.
      "Files\\XAU_AI_PRO\\diagnostics_test_" +
      _Symbol + "_" + IntegerToString(_Period) + ".tmp";

   int fileHandle =
      FileOpen(
         testFile,
         FILE_COMMON |
         FILE_WRITE |
         FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE
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

   // v1.2.107 (03/11/2026) - P1.97: a linha de erro dizia "FALHAS DETECTADAS"
   // e o journal mostrava apenas "Broker: VERDE": a lista das 11 checagens nao
   // chegava ao jornal e o operador ficava sem saber QUAL reprovou. Agora a
   // mensagem comeca pela contagem e lista SOMENTE o que reprovou, com o
   // detalhe de cada falha. Nao existe mais "FALHAS" sem nome de falha e nao
   // ha eco das checagens verdes. A tag de saude continua a cargo do
   // HealthMonitor: sao duas medidas diferentes (autoteste de arranque x
   // estado operacional) e o jornal passa a dizer qual delas reprovou.
   int    diagTotal  = ArraySize(g_diagnostics);
   int    diagFalhas = 0;
   string diagLista  = "";

   for(int d = 0; d < diagTotal; d++)
   {
      if(g_diagnostics[d].passed)
         continue;

      diagFalhas++;

      diagLista += (diagLista == "" ? "" : " | ");
      diagLista += g_diagnostics[d].name;

      if(g_diagnostics[d].detail != "")
         diagLista += "(" + g_diagnostics[d].detail + ")";
   }

   string diagVeredito =
      StringFormat("checagens=%d | falhas=%d | reprovou: %s",
                   diagTotal,
                   diagFalhas,
                   (diagLista == "" ? "nenhuma" : diagLista));

   if(allPassed)
   {
      LogSystem(
         "Diagnostico: TODOS OS TESTES PASSARAM"
      );
   }
   else
   {
      if(LogInicioDetalhe())
      {
         // v1.2.106 (P1.96): o detalhe vinha multi-linha e cada "\\n" virava
         // uma linha SEM TAG no journal (12 por arranque). Passa a 1 linha.
         string detalheUma = summary;
         StringReplace(detalheUma, "\r\n", " | ");   // P1.99: quebra REAL, nao barra invertida
         StringReplace(detalheUma, "\n", " | ");
         StringReplace(detalheUma, "\r", " | ");
         for(int k = 0; k < 8; k++)
            StringReplace(detalheUma, " |  | ", " | ");
         for(int k = 0; k < 8; k++)
            StringReplace(detalheUma, "| |", "|");
         LogError("Diagnostico: FALHAS DETECTADAS", diagVeredito);
      }
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
// FALHAS EM DETALHE (v1.2.14)
//
// O resumo era passado ao LogError apenas como argumento e nunca chegava ao
// journal: so aparecia 'FALHAS DETECTADAS (ver log)'. Sem o nome do teste,
// ninguem consegue corrigir. Cada reprovacao vira uma linha de journal.
//==================================================
void DiagnosticsPrintFailures()
{
   int n = ArraySize(g_diagnostics);

   for(int i = 0; i < n; i++)
   {
      if(g_diagnostics[i].passed)
         continue;

      Print("[DIAG] FALHA | ", g_diagnostics[i].name,
            (g_diagnostics[i].detail != "" ? " | " : " "),
            g_diagnostics[i].detail);
   }
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
