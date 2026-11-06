// XAU_AI_PRO v1.2.9
#ifndef RSI_MQH
#define RSI_MQH

#include "../Core/Config.mqh"
#include "SymbolDataReady.mqh"   // v1.2.152 - P1.113

//==================================================
// RSI
//==================================================

int rsiHandle = INVALID_HANDLE;

//==================================================
// v1.2.96 (03/11/2026) - P1.86: CACHE DE HANDLE POR SIMBOLO
//
// Mesma causa medida no ADX (P1.85): a versao multi-simbolo chamava
// iRSI() e IndicatorRelease() na mesma leitura. O scan percorre ~110
// simbolos por minuto, logo eram ~110 handles criados e destruidos por
// minuto - e um handle recem-criado pode nao ter serie pronta. O handle
// passa a ser criado uma vez por simbolo e reutilizado.
//==================================================
#define RSI_SYMBOL_CACHE 256

string g_rsiCacheSymbol[RSI_SYMBOL_CACHE];
int    g_rsiCacheHandle[RSI_SYMBOL_CACHE];
int    g_rsiCacheCount = 0;

int RSISymbolHandle(string symbol)
{
   for(int i = 0; i < g_rsiCacheCount; i++)
      if(g_rsiCacheSymbol[i] == symbol)
         return g_rsiCacheHandle[i];

   if(g_rsiCacheCount >= RSI_SYMBOL_CACHE)
      return INVALID_HANDLE;

   // v1.2.152 - P1.113: handle so nasce com a serie do simbolo provada.
   XAI_WaitSeriesReady(symbol, (ENUM_TIMEFRAMES)Period());

   int handle = iRSI(symbol, (ENUM_TIMEFRAMES)Period(), RSIPeriod, PRICE_CLOSE);

   if(handle == INVALID_HANDLE)
      return INVALID_HANDLE;

   g_rsiCacheSymbol[g_rsiCacheCount] = symbol;
   g_rsiCacheHandle[g_rsiCacheCount] = handle;
   g_rsiCacheCount++;

   return handle;
}

//==================================================
// v1.2.152 (05/11/2026) - P1.113: CACHE AUTOLIMPAVEL
//
// MEDIDO no journal as 23:16:40 de 04/11, build v1.2.151: SETE pares
// devolveram o MESMO RSI=82.72 no mesmo segundo, ao lado do MESMO ADX=33.77
// e do ATR do OURO. O handle por simbolo nasceu enquanto a serie pedida
// ainda nao existia e ficou preso a serie de outro instrumento; como nunca
// saia da cache, o simbolo ficava a ler o RSI errado indefinidamente.
// A leitura provada como contaminada passa a deitar fora a entrada.
//==================================================
void RSICacheDrop(string symbol)
{
   for(int i = 0; i < g_rsiCacheCount; i++)
     {
      if(g_rsiCacheSymbol[i] != symbol)
         continue;

      if(g_rsiCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_rsiCacheHandle[i]);

      for(int j = i; j < g_rsiCacheCount - 1; j++)
        {
         g_rsiCacheSymbol[j] = g_rsiCacheSymbol[j + 1];
         g_rsiCacheHandle[j] = g_rsiCacheHandle[j + 1];
        }

      g_rsiCacheCount--;
      g_rsiCacheSymbol[g_rsiCacheCount] = "";
      g_rsiCacheHandle[g_rsiCacheCount] = INVALID_HANDLE;

      return;
     }
}
void RSIReleaseSymbolHandles()
{
   for(int i = 0; i < g_rsiCacheCount; i++)
      if(g_rsiCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_rsiCacheHandle[i]);

   g_rsiCacheCount = 0;
}

//==================================================
// INIT
//==================================================

bool InitRSI()
{
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);

   // v1.2.96 - P1.86: a cache multi-simbolo e indexada por simbolo, mas o
   // timeframe entra na criacao do handle (PERIOD_CURRENT). Numa mudanca de
   // timeframe os handles antigos responderiam com o periodo errado, logo
   // a cache e limpa em toda inicializacao (mesma regra do InitADX).
   RSIReleaseSymbolHandles();

   rsiHandle = iRSI(
      _Symbol,
      PERIOD_CURRENT,
      RSIPeriod,
      PRICE_CLOSE
   );

   if(rsiHandle == INVALID_HANDLE)
   {
      Print(
         "[RSI] INIT ERROR | Error=",
         GetLastError()
      );

      return false;
   }

   if(LogInicioDetalhe()) Print(
      "[RSI] INIT OK | Period=",
      RSIPeriod
   );

   return true;
}

//==================================================
// GET RSI
//==================================================

double GetRSIInstance()
{
   if(rsiHandle == INVALID_HANDLE)
      return 0.0;

   double buffer[];

   ArraySetAsSeries(buffer, true);

   ResetLastError();

   if(CopyBuffer(
      rsiHandle,
      0,
      0,
      1,
      buffer
   ) != 1)
   {
      return 0.0;
   }

   if(buffer[0] <= 0.0 || buffer[0] >= 100.0)
      return 0.0;

   return buffer[0];
}

//==================================================
// MULTI SYMBOL
//==================================================

double GetRSI(string symbol)
{
   // v1.2.150 - P1.109: sem atalho para o handle da instancia.
   if(symbol == "")
      symbol = _Symbol;

   if(!SymbolSelect(symbol, true))
      return 0.0;

   // v1.2.152 - P1.113: sem serie provada nao ha leitura (SymbolDataReady.mqh).
   if(!XAI_SymbolDataReady(symbol))
      return 0.0;

   int handle = RSISymbolHandle(symbol);

   if(handle == INVALID_HANDLE)
      return 0.0;

   double buffer[];

   ArraySetAsSeries(buffer, true);

   double result = 0.0;

   if(CopyBuffer(
      handle,
      0,
      0,
      1,
      buffer
   ) == 1)
   {
      result = buffer[0];

      // v1.2.28 (30/10/2026) - P1.5: mesmo criterio da versao de um
      // simbolo (linhas acima). 0.0 e 100.0 sao o que o iRSI entrega
      // quando a serie ainda nao tem dados suficientes; sem esta linha um
      // simbolo em aquecimento devolvia 100.0 como se fosse medida e o
      // resto do codigo nao tinha como distinguir.
      if(result <= 0.0 || result >= 100.0)
         result = 0.0;
   }

   // v1.2.152 - P1.113: valor indistinguivel do valor do simbolo do grafico
   // e a assinatura medida da contaminacao. A leitura e recusada e o handle
   // sai da cache para o simbolo poder sarar.
   if(symbol != _Symbol && result > 0.0)
     {
      double rsiDoGrafico = GetRSI(_Symbol);

      if(XAI_LeituraDeOutroSimbolo(result, rsiDoGrafico))
        {
         if(AccountLogGatePodeImprimir("rsi_outro_sim_" + symbol, 3600))
            Print("[RSI] VALOR DE OUTRO SIMBOLO | ", symbol,
                  " | RSI=", DoubleToString(result, 2),
                  " | grafico=", _Symbol,
                  " | devolvido=0.0");

         RSICacheDrop(symbol);

         return 0.0;
        }
     }
   // v1.2.96 - P1.86: handle vive no cache por simbolo; libertar aqui
   // devolvia o indicador ao estado "sem serie" em cada leitura.
   return result;
}

//==================================================
// BUY
//==================================================

//==================================================
// v1.2.150 (05/11/2026) - P1.109: RSI DO SIMBOLO DO GRAFICO
//==================================================
double GetRSI()
{
   return GetRSI(_Symbol);
}



bool RSI_OK_Buy()
{
   double rsi = GetRSI();

   if(rsi <= 0.0)
      return false;

   return (rsi < 70.0);
}

//==================================================
// BUY MULTI SYMBOL
//==================================================

bool RSI_OK_Buy(string symbol)
{
   double rsi = GetRSI(symbol);

   if(rsi <= 0.0)
      return false;

   return (rsi < 70.0);
}

//==================================================
// SELL
//==================================================

bool RSI_OK_Sell()
{
   double rsi = GetRSI();

   if(rsi <= 0.0)
      return false;

   return (rsi > 30.0);
}

//==================================================
// SELL MULTI SYMBOL
//==================================================

bool RSI_OK_Sell(string symbol)
{
   double rsi = GetRSI(symbol);

   if(rsi <= 0.0)
      return false;

   return (rsi > 30.0);
}

//==================================================
// RELEASE
//==================================================

void ReleaseRSI()
{
   if(rsiHandle != INVALID_HANDLE)
   {
      IndicatorRelease(rsiHandle);
      rsiHandle = INVALID_HANDLE;
   }

   // v1.2.96 - P1.86: os handles do scan multi-simbolo vivem na cache; sem
   // esta linha ficavam abertos ate o terminal fechar.
   RSIReleaseSymbolHandles();
}

#endif