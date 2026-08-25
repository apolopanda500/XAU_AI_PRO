// XAU_AI_PRO v1.2.0
#ifndef SYMBOLMANAGER_MQH
#define SYMBOLMANAGER_MQH

#include "../Core/Config.mqh"

//==================================================
// SYMBOL STORAGE
//==================================================

string ActiveSymbols[];

//--------------------------------------------------
// ESTADO DE SINCRONIZACAO (v1.2.0)
// Quando o terminal inicia, os simbolos ainda nao
// estao sincronizados. Antes isso fazia o OnInit
// falhar com code 1 / symbol synchronization timeout.
// Agora a resolucao e adiada e tentada de novo
// em OnTick/OnTimer (UpdateSymbolManager).
//--------------------------------------------------
bool SymbolsPending     = false;   // ha simbolos aguardando sincronizacao
bool SymbolsResolved    = false;   // resolucao concluida com sucesso
datetime LastSymbolRetry= 0;       // throttle do retry
int  SymbolRetryCount   = 0;       // retries do episodio atual (cap anti-loop v1.2.1)

// Maximo de retries de sincronizacao antes de desistir e liberar o
// pipeline com os simbolos ja resolvidos. 12 x 5s = ~60s de tolerancia
// no boot; simbolos inexistentes na corretora (ex.: US30/US500/USTEC)
// nao devem travar o EA para sempre.
#define SYMBOL_RETRY_MAX 12

//==================================================
// HELPERS
//==================================================

bool IsSymbolTradeable(string symbol)
{
   if(symbol == "")
      return false;

   ResetLastError();

   if(!SymbolSelect(symbol, true))
   {
      // 4301 = simbolo realmente desconhecido.
      // Qualquer outro erro (ex.: 4106, 4801) normalmente
      // significa que o simbolo ainda nao sincronizou.
      // v1.2.1: NAO seta mais SymbolsPending aqui. Candidatos
      // de fallback inexistentes (US30/US500/USTEC e sufixos
      // testados em ResolveBrokerSymbol) geram erros != 4301
      // a cada init/retry e travavam o OnTick antes do
      // RunTradePipeline. A pendencia real de boot continua
      // detectada pelo Market Watch vazio (ResolveBrokerSymbol)
      // e pelos fallbacks do _Symbol na InitSymbolManager.
      return false;
   }

   long tradeMode = SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE);
   if(tradeMode == SYMBOL_TRADE_MODE_DISABLED)
   {
      Print("SYMBOL MANAGER | Trade disabled | ", symbol);
      return false;
   }

   if(tradeMode == SYMBOL_TRADE_MODE_CLOSEONLY)
   {
      Print("SYMBOL MANAGER | Close-only mode | ", symbol);
      return false;
   }

   return true;
}

string NormalizeInputSymbol(string symbol)
{
   StringTrimLeft(symbol);
   StringTrimRight(symbol);

   // Remove sufixo "c" apenas para casos conhecidos (contas cent/raw)
   string knownCent[] = {"XAUUSDc", "BTCUSDc", "ETHUSDc", "EURUSDc", "GBPUSDc", "USDJPYc"};
   for(int i = 0; i < ArraySize(knownCent); i++)
   {
      if(StringCompare(symbol, knownCent[i], false) == 0)
         return StringSubstr(symbol, 0, StringLen(symbol) - 1);
   }

   return symbol;
}

//==================================================
// RESOLVE BROKER SYMBOL
//==================================================

string ResolveBrokerSymbol(string symbol)
{
   StringTrimLeft(symbol);
   StringTrimRight(symbol);

   if(symbol == "")
   {
      Print("SYMBOL MANAGER | Empty symbol requested");
      return "";
   }

   string baseSymbol = NormalizeInputSymbol(symbol);

   string candidates[];
   ArrayResize(candidates, 16);

   candidates[0]  = symbol;
   candidates[1]  = baseSymbol;
   candidates[2]  = baseSymbol + "c";
   candidates[3]  = baseSymbol + ".";
   candidates[4]  = baseSymbol + "#";
   candidates[5]  = baseSymbol + "m";
   candidates[6]  = baseSymbol + "micro";
   candidates[7]  = baseSymbol + ".pro";
   candidates[8]  = baseSymbol + "_i";
   candidates[9]  = baseSymbol + ".cash";
   candidates[10] = baseSymbol + ".r";
   candidates[11] = "";
   candidates[12] = "";
   candidates[13] = "";
   candidates[14] = "";
   candidates[15] = "";

   if(baseSymbol == "XAUUSD")
   {
      candidates[11] = "GOLD";
      candidates[12] = "GOLD#";
      candidates[13] = "XAUUSDm";
      candidates[14] = "XAUUSDmicro";
      candidates[15] = "XAUUSD.pro";
   }
   else
   if(baseSymbol == "BTCUSD")
   {
      candidates[11] = "BTCUSD#";
      candidates[12] = "BTCUSDm";
      candidates[13] = "BTCUSDmicro";
      candidates[14] = "BTCUSD.pro";
      candidates[15] = "BTCUSD.cash";
   }
   else
   if(baseSymbol == "ETHUSD")
   {
      candidates[11] = "ETHUSD#";
      candidates[12] = "ETHUSDm";
      candidates[13] = "ETHUSDmicro";
      candidates[14] = "ETHUSD.pro";
      candidates[15] = "ETHUSD.cash";
   }

   for(int i = 0; i < ArraySize(candidates); i++)
   {
      if(candidates[i] == "")
         continue;

      if(IsSymbolTradeable(candidates[i]))
      {
         Print("SYMBOL MANAGER | Resolved: ", symbol, " -> ", candidates[i]);
         return candidates[i];
      }
   }

   // Fallback 1: match exato no Market Watch
   int total = SymbolsTotal(true);
   for(int i = 0; i < total; i++)
   {
      string broker = SymbolName(i, true);

      if(StringCompare(broker, symbol, false) == 0 ||
         StringCompare(broker, baseSymbol, false) == 0)
      {
         if(IsSymbolTradeable(broker))
         {
            Print("SYMBOL MANAGER | Exact match: ", symbol, " -> ", broker);
            return broker;
         }
      }
   }

   // Fallback 2: match parcial (mais permissivo, mas logado)
   // v1.2.1: protecao para Market Watch vazio (boot/sincronizacao pendente)
   if(total <= 0)
   {
      Print("SYMBOL MANAGER | Market Watch vazio (sincronizacao pendente) | ", symbol);
      SymbolsPending = true;
      return "";
   }
   for(int i = 0; i < total; i++)
   {
      string broker = SymbolName(i, true);

      if(StringFind(broker, baseSymbol, 0) == 0)
      {
         if(IsSymbolTradeable(broker))
         {
            Print("SYMBOL MANAGER | Partial match: ", symbol, " -> ", broker);
            return broker;
         }
      }
   }

   Print("SYMBOL MANAGER | Symbol not found: ", symbol);
   return "";
}

//==================================================
// INIT
//==================================================

bool SymbolAlreadyActive(string symbol)
{
   int total = ArraySize(ActiveSymbols);
   for(int i = 0; i < total; i++)
   {
      if(StringCompare(ActiveSymbols[i], symbol, false) == 0)
         return true;
   }
   return false;
}

bool InitSymbolManager()
{
   ArrayResize(ActiveSymbols, 0);

   if(!EnableMultiSymbol)
   {
      ArrayResize(ActiveSymbols, 1);

      // Tenta resolver o simbolo do grafico para a convencao da corretora.
      // Se nao encontrar um tradeable, usa _Symbol diretamente.
      string resolved = ResolveBrokerSymbol(_Symbol);
      if(resolved != "" && IsSymbolTradeable(resolved))
      {
         ActiveSymbols[0] = resolved;
         Print("SYMBOL MANAGER | Single-symbol mode mapped: ", _Symbol, " -> ", resolved);
      }
      else
      {
         ActiveSymbols[0] = _Symbol;
         if(!IsSymbolTradeable(ActiveSymbols[0]))
         {
            // Nao e fatal: o simbolo pode ainda nao estar sincronizado.
            // O retry (UpdateSymbolManager) tenta de novo em OnTick/OnTimer.
            Print("SYMBOL MANAGER | _Symbol ainda nao negociavel (pendente): ", ActiveSymbols[0]);
            SymbolsPending = true;
         }
         Print("SYMBOL MANAGER | Single-symbol mode: ", ActiveSymbols[0]);
      }

      return true;
   }

   string temp[];
   int count = StringSplit(Symbols, ',', temp);

   if(count <= 0)
   {
      ArrayResize(ActiveSymbols, 1);
      ActiveSymbols[0] = _Symbol;

      if(!IsSymbolTradeable(ActiveSymbols[0]))
      {
         Print("SYMBOL MANAGER | _Symbol ainda nao negociavel (pendente): ", ActiveSymbols[0]);
         SymbolsPending = true;
      }

      Print("SYMBOL MANAGER | Fallback single-symbol mode: ", ActiveSymbols[0]);
      return true;
   }

   Print("=== SYMBOL MANAGER INITIALIZING ===");
   Print("SYMBOL MANAGER | Configured symbols: ", count);

   if(EnableVerboseDebug)
   {
      Print("SYMBOL MANAGER | Market Watch list:");
      int total = SymbolsTotal(true);
      for(int i = 0; i < total; i++)
      {
         string brokerSymbol = SymbolName(i, true);
         Print("  [", i, "] ", brokerSymbol);
      }
   }

   for(int i = 0; i < count; i++)
   {
      string symbol = ResolveBrokerSymbol(temp[i]);

      if(symbol == "")
         continue;

      if(SymbolAlreadyActive(symbol))
      {
         Print("SYMBOL MANAGER | Duplicate ignored: ", symbol);
         continue;
      }

      int size = ArraySize(ActiveSymbols);
      ArrayResize(ActiveSymbols, size + 1);
      ActiveSymbols[size] = symbol;

      Print("SYMBOL MANAGER | Active symbol registered: ", symbol);
   }

   Print("=== SYMBOL MANAGER INITIALIZED ===");
   Print("SYMBOL MANAGER | Total active symbols: ", ArraySize(ActiveSymbols));

   for(int i = 0; i < ArraySize(ActiveSymbols); i++)
   {
      Print("  [", i, "] ", ActiveSymbols[i]);
   }

   if(ArraySize(ActiveSymbols) == 0)
   {
      Print("SYMBOL MANAGER | WARNING: No symbols resolved, using _Symbol: ", _Symbol);
      ArrayResize(ActiveSymbols, 1);
      ActiveSymbols[0] = _Symbol;

      if(!IsSymbolTradeable(ActiveSymbols[0]))
      {
         // Nao e fatal: apenas sinaliza que a sincronizacao esta pendente.
         Print("SYMBOL MANAGER | WARNING: _Symbol ainda nao negociavel (pendente): ", ActiveSymbols[0]);
         SymbolsPending = true;
      }
   }

   return true;
}

//==================================================
// UPDATE (RETRY) - SIMBOLOS PENDENTES
// Chamado em OnTick/OnTimer enquanto SymbolsPending.
// Reexecuta a resolucao com throttle para nao travar
// o OnInit nem inundar o log quando o terminal inicia
// antes da sincronizacao dos simbolos.
//==================================================

bool UpdateSymbolManager()
{
   if(!SymbolsPending)
      return true;

   datetime now = TimeCurrent();

   if(now - LastSymbolRetry < 5)
      return false;

   LastSymbolRetry  = now;
   SymbolRetryCount++;

   //--------------------------------------------------
   // CAP ANTI-LOOP (v1.2.1)
   // Se apos SYMBOL_RETRY_MAX tentativas algum simbolo
   // continuar sem sincronizar (ex.: US30/US500/USTEC
   // inexistentes na corretora), desiste da pendencia e
   // libera o pipeline com os simbolos ja resolvidos.
   // Sem isso o OnTick retorna antes do RunTradePipeline
   // para sempre e o EA nunca avalia sinais.
   //--------------------------------------------------
   if(SymbolRetryCount >= SYMBOL_RETRY_MAX)
   {
      SymbolsPending   = false;
      SymbolsResolved  = true;
      SymbolRetryCount = 0;
      Print("SYMBOL MANAGER | WARNING: sincronizacao nao concluida apos ",
            SYMBOL_RETRY_MAX, " tentativas. Liberando operacao com ",
            ArraySize(ActiveSymbols), " simbolo(s) ativo(s).");
      return true;
   }

   Print("SYMBOL MANAGER | Retentando sincronizacao de simbolos (",
         SymbolRetryCount, "/", SYMBOL_RETRY_MAX, ")...");

   SymbolsPending = false;
   InitSymbolManager();

   if(!SymbolsPending)
   {
      SymbolsResolved  = true;
      SymbolRetryCount = 0;
      Print("SYMBOL MANAGER | Simbolos sincronizados com sucesso (", ArraySize(ActiveSymbols), ")");
   }

   return !SymbolsPending;
}

//==================================================
// STATUS
//==================================================

bool AreSymbolsReady()
{
   return !SymbolsPending;
}

//==================================================
// TOTAL
//==================================================

int TotalSymbols()
{
   return ArraySize(ActiveSymbols);
}

//==================================================
// GET SYMBOL
//==================================================

string GetTradeSymbol(int index)
{
   if(index < 0 || index >= ArraySize(ActiveSymbols))
      return "";

   return ActiveSymbols[index];
}

//==================================================
// RELEASE
//==================================================

void ReleaseSymbolManager()
{
   ArrayFree(ActiveSymbols);
}

#endif


