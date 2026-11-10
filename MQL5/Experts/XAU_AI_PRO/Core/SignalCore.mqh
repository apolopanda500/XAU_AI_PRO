// XAU_AI_PRO v1.2.9
#ifndef SIGNALCORE_MQH
#define SIGNALCORE_MQH

#include "../Core/Config.mqh"
#include "../Indicators/SymbolDataReady.mqh"   // v1.2.161 - P1.123

//==================================================
// v1.2.161 (05/11/2026) - P1.123: CACHE DE HANDLES DO SINAL
//
// MEDIDO no journal de 05/11 (v1.2.159), grafico mestre USDCNH, em 24 horas:
//   [TREND] LEITURA SUSPEITA | AUDUSD | EMA=44.60460 | bid=0.69415
//   [TREND] LEITURA SUSPEITA | USDJPY | EMA=44.60460 | bid=157.78500
//   [TREND] LEITURA SUSPEITA | GBPUSD | EMA=44.60460 | bid=1.34477
//   [TREND] LEITURA SUSPEITA | USDCAD | EMA=44.60460 | bid=1.39972
//   [TREND] LEITURA SUSPEITA | EURUSD | EMA=44.60460 | bid=1.12255
// O MESMO valor 44.60460 em cinco simbolos dentro da mesma hora - e a serie
// 26.80 -> 29.23 -> 31.51 -> 33.82 -> 44.60 -> 51.61 ao longo do dia - nao e
// a EMA200 de nenhum par cotado entre 0.69 e 157: e o buffer de OUTRO tipo de
// indicador (familia 0-100, RSI/ADX).
//
// A causa e o churn de handles deste arquivo. Cada chamada de GetSignal cria
// TRES handles (iMA x2 + iRSI) e liberta-os no mesmo instante, para cada um
// dos 11 simbolos, a cada ciclo de scan: ~33 criacoes/destroicoes por ciclo.
// O terminal reaproveita os slots numericos libertados e um handle de vida
// longa (EMA de tendencia, ADX, ATR - todos em cache desde a P1.85/P1.108/
// P1.113) passa a apontar para o slot de um indicador de outro tipo.
//
// Com a EMA de tendencia a devolver lixo, `ScenarioTrendGate` responde
// "contramao" a TODOS os sinais. Medido nas 24 horas: 13 sinais BUY, 28 SELL,
// 60 linhas "[SCANNER] SIGNAL OK" e ZERO entradas.
//
// Correcao: os tres handles do sinal passam a nascer UMA vez por simbolo e a
// ser reutilizados (mesmo desenho que ja funciona no ADX, no ATR e na EMA de
// tendencia), com descarte da entrada quando a copia falhar, para o par sarar
// sozinho. Nenhum limite, regra de entrada/saida, lote, alvo, stop, spread ou
// RR muda: a regra do sinal e exactamente a mesma.
//==================================================
#define SIG_CACHE_MAX 64

string g_sigCacheSymbol[SIG_CACHE_MAX];
int    g_sigCacheFast[SIG_CACHE_MAX];
int    g_sigCacheSlow[SIG_CACHE_MAX];
int    g_sigCacheRsi[SIG_CACHE_MAX];
int    g_sigCacheCount = 0;

bool SignalCacheFind(string symbol, int &idx)
{
   idx = -1;

   for(int i = 0; i < g_sigCacheCount; i++)
      if(g_sigCacheSymbol[i] == symbol)
        {
         idx = i;
         return true;
        }

   return false;
}

void SignalCacheDrop(string symbol)
{
   int idx;

   if(!SignalCacheFind(symbol, idx))
      return;

   if(g_sigCacheFast[idx] != INVALID_HANDLE)
      IndicatorRelease(g_sigCacheFast[idx]);

   if(g_sigCacheSlow[idx] != INVALID_HANDLE)
      IndicatorRelease(g_sigCacheSlow[idx]);

   if(g_sigCacheRsi[idx] != INVALID_HANDLE)
      IndicatorRelease(g_sigCacheRsi[idx]);

   for(int j = idx; j < g_sigCacheCount - 1; j++)
     {
      g_sigCacheSymbol[j] = g_sigCacheSymbol[j + 1];
      g_sigCacheFast[j]   = g_sigCacheFast[j + 1];
      g_sigCacheSlow[j]   = g_sigCacheSlow[j + 1];
      g_sigCacheRsi[j]    = g_sigCacheRsi[j + 1];
     }

   g_sigCacheCount--;
   g_sigCacheSymbol[g_sigCacheCount] = "";
   g_sigCacheFast[g_sigCacheCount]   = INVALID_HANDLE;
   g_sigCacheSlow[g_sigCacheCount]   = INVALID_HANDLE;
   g_sigCacheRsi[g_sigCacheCount]    = INVALID_HANDLE;
}

// Cria (uma vez) os tres handles do simbolo. Devolve false se o terminal
// ainda nao conseguiu cria-los: nesse caso nada fica na cache e a leitura
// seguinte tenta outra vez.
bool SignalEnsureHandles(string symbol)
{
   int idx;

   if(SignalCacheFind(symbol, idx))
      return (g_sigCacheFast[idx] != INVALID_HANDLE &&
              g_sigCacheSlow[idx] != INVALID_HANDLE &&
              g_sigCacheRsi[idx]  != INVALID_HANDLE);

   if(g_sigCacheCount >= SIG_CACHE_MAX)
      return false;

   // Handle so nasce com a serie do simbolo provada (padrao P1.113).
   XAI_WaitSeriesReady(symbol, (ENUM_TIMEFRAMES)Period());

   int hFast = iMA(symbol, PERIOD_CURRENT, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   int hSlow = iMA(symbol, PERIOD_CURRENT, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   int hRsi  = iRSI(symbol, PERIOD_CURRENT, RSIPeriod, PRICE_CLOSE);

   if(hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE || hRsi == INVALID_HANDLE)
     {
      if(hFast != INVALID_HANDLE) IndicatorRelease(hFast);
      if(hSlow != INVALID_HANDLE) IndicatorRelease(hSlow);
      if(hRsi  != INVALID_HANDLE) IndicatorRelease(hRsi);
      return false;
     }

   idx = g_sigCacheCount;

   g_sigCacheSymbol[idx] = symbol;
   g_sigCacheFast[idx]   = hFast;
   g_sigCacheSlow[idx]   = hSlow;
   g_sigCacheRsi[idx]    = hRsi;
   g_sigCacheCount++;

   return true;
}

//==================================================
// SIGNAL CORE (baseline v1.2.0 restaurado)
// Revertido do backup v1.2.0 (24/08 17:36 -> cache de
// handles causou 'Falha ao copiar RSI' e travou sinais).
// Comportamento restaurado: handles criados, copiados e
// liberados a CADA chamada (como na versao que operava).
// Stubs SignalCoreInit/ReleaseSignalHandles mantidos
// apenas para compatibilidade com OnInit/OnDeinit.
//==================================================

// Chamado no OnInit: o timeframe entra na identidade do handle, logo a cache
// e limpa em toda inicializacao (padrao do ADX desde a P1.85).
void SignalCoreInit()
{
   ReleaseSignalHandles();
}

// Chamado no OnDeinit: liberta os handles que ficaram em cache.
void ReleaseSignalHandles()
{
   for(int i = 0; i < g_sigCacheCount; i++)
     {
      if(g_sigCacheFast[i] != INVALID_HANDLE)
         IndicatorRelease(g_sigCacheFast[i]);

      if(g_sigCacheSlow[i] != INVALID_HANDLE)
         IndicatorRelease(g_sigCacheSlow[i]);

      if(g_sigCacheRsi[i] != INVALID_HANDLE)
         IndicatorRelease(g_sigCacheRsi[i]);
     }

   g_sigCacheCount = 0;
}

//==================================================
// v1.2.94 (02/11/2026) - P1.82: DESFECHO DO SINAL
//
// Ate aqui todos os caminhos de GetSignal devolviam o MESMO 0: handle
// invalido, copia falhada, historico vazio e "a regra nao pediu entrada".
// Medido no journal de 02/11: 13 293 varreduras NoSignal no dia, sem uma
// unica pista de qual dos quatro motivos era. Passa a haver dois
// contadores, publicados no [SCANNER] RESUMO:
//   g_sigNoRead  -> nao foi possivel LER (handle/copia/historico)
//   g_sigNeutral -> leu tudo e a REGRA nao pediu entrada
// Sem leitura e mercado sem setup sao doencas diferentes.
//==================================================
int g_sigNoRead  = 0;
int g_sigNeutral = 0;

int SignalNoReadCount()
{
   return g_sigNoRead;
}

int SignalNeutralCount()
{
   return g_sigNeutral;
}

int GetSignal()
{
   return GetSignal(_Symbol);
}

//==================================================
// MULTI SYMBOL
//==================================================

int GetSignal(string symbol)
{
   // v1.2.93 (02/11/2026) - P1.80: MEDIDO no journal de 02/11 as 20:23 - as
   // duas unicas linhas SEM TAG que restavam eram as do sinal ('USDBRL SIGNAL
   // BUY | RSI[1]=37.31'), e o throttle era um static UNICO partilhado por
   // todos os simbolos: o primeiro simbolo que passava gastava a vez do
   // minuto e os outros ficavam invisiveis no journal. Passa a throttle POR
   // SIMBOLO e a tag [SIGNAL], para o journal fechar em 0 linhas anonimas e
   // cada simbolo poder dizer se gerou sinal. Diagnostico apenas: nenhum
   // return, limite, lote, alvo ou regra de entrada muda.
   static string   sigLogSymbols[];
   static datetime sigLogTimes[];
   datetime logNow = TimeCurrent();
   bool logOnce = false;
   int sigIdx = -1;

   for(int si = 0; si < ArraySize(sigLogSymbols); si++)
     {
      if(sigLogSymbols[si] == symbol)
        {
         sigIdx = si;
         break;
        }
     }

   if(sigIdx < 0)
     {
      sigIdx = ArraySize(sigLogSymbols);
      ArrayResize(sigLogSymbols, sigIdx + 1);
      ArrayResize(sigLogTimes, sigIdx + 1);
      sigLogSymbols[sigIdx] = symbol;
      sigLogTimes[sigIdx] = 0;
     }

   if(logNow - sigLogTimes[sigIdx] >= 60)
     {
      sigLogTimes[sigIdx] = logNow;
      logOnce = true;
     }

   if(symbol=="")
      return 0;

   // v1.2.161 - P1.123: handles do sinal em cache por simbolo (uma criacao,
   // nenhuma libertacao durante a sessao). Antes: iMA x2 + iRSI criados e
   // libertados a cada chamada, ~33 slots reciclados por ciclo de scan, o que
   // desalinhava os handles de vida longa (EMA de tendencia, ADX, ATR).
   int sigCacheIdx = -1;

   if(!SignalEnsureHandles(symbol) || !SignalCacheFind(symbol, sigCacheIdx))
   {
      g_sigNoRead++;

      if(logOnce)
         Print("[SIGNAL] SEM LEITURA | ", symbol, " | handles do sinal indisponiveis");

      return 0;
   }

   int emaFastHandle   = g_sigCacheFast[sigCacheIdx];
   int emaSlowHandle   = g_sigCacheSlow[sigCacheIdx];
   int signalRSIHandle = g_sigCacheRsi[sigCacheIdx];

   // Valida handles
   if(emaFastHandle==INVALID_HANDLE || emaSlowHandle==INVALID_HANDLE || signalRSIHandle==INVALID_HANDLE)
   {
      g_sigNoRead++;
      SignalCacheDrop(symbol);

      if(logOnce)
         Print("[SIGNAL] SEM LEITURA | ", symbol, " | handle do sinal invalido");

      return 0;
   }

   double fast[];
   double slow[];
   double rsi[];

   ArrayResize(fast,3);
   ArrayResize(slow,3);
   ArrayResize(rsi,3);

   ArraySetAsSeries(fast,true);
   ArraySetAsSeries(slow,true);
   ArraySetAsSeries(rsi,true);

   // Copiar buffers
   bool copyOK=true;

   ResetLastError();

   if(CopyBuffer(emaFastHandle,0,0,3,fast)<=0)
   {
      // P2.17 (03/11/2026): 4022/aquecimento nao e falta de dado. A MT5
      // calcula o indicador de forma assincrona depois de cada reload e o
      // valor sai no ciclo seguinte; a linha passa a dizer qual dos dois
      // casos e, em 1x/hora por CONTA e por simbolo (eram 15 instancias).
      int errEmaFast = GetLastError();
      int calcEmaFast = BarsCalculated(emaFastHandle);

      if(AccountLogGatePodeImprimir("signosem_" + symbol + "_ema_fast", 3600))
         Print("[SIGNAL] SEM LEITURA | ", symbol, " | ",
               (calcEmaFast < 3 ? "EMA Fast em aquecimento (MT5 calcula apos reload)" : "falha ao copiar EMA Fast"),
               " | BarsCalc=", calcEmaFast, " | Error=", errEmaFast,
               " | aviso 1x/hora por conta e simbolo");

      copyOK=false;
   }

   ResetLastError();

   if(CopyBuffer(emaSlowHandle,0,0,3,slow)<=0)
   {
      // P2.17 (03/11/2026): 4022/aquecimento nao e falta de dado. A MT5
      // calcula o indicador de forma assincrona depois de cada reload e o
      // valor sai no ciclo seguinte; a linha passa a dizer qual dos dois
      // casos e, em 1x/hora por CONTA e por simbolo (eram 15 instancias).
      int errEmaSlow = GetLastError();
      int calcEmaSlow = BarsCalculated(emaSlowHandle);

      if(AccountLogGatePodeImprimir("signosem_" + symbol + "_ema_slow", 3600))
         Print("[SIGNAL] SEM LEITURA | ", symbol, " | ",
               (calcEmaSlow < 3 ? "EMA Slow em aquecimento (MT5 calcula apos reload)" : "falha ao copiar EMA Slow"),
               " | BarsCalc=", calcEmaSlow, " | Error=", errEmaSlow,
               " | aviso 1x/hora por conta e simbolo");

      copyOK=false;
   }

   ResetLastError();

   if(CopyBuffer(signalRSIHandle,0,0,3,rsi)<=0)
   {
      // P2.17 (03/11/2026): 4022/aquecimento nao e falta de dado. A MT5
      // calcula o indicador de forma assincrona depois de cada reload e o
      // valor sai no ciclo seguinte; a linha passa a dizer qual dos dois
      // casos e, em 1x/hora por CONTA e por simbolo (eram 15 instancias).
      int errRsi = GetLastError();
      int calcRsi = BarsCalculated(signalRSIHandle);

      if(AccountLogGatePodeImprimir("signosem_" + symbol + "_rsi", 3600))
         Print("[SIGNAL] SEM LEITURA | ", symbol, " | ",
               (calcRsi < 3 ? "RSI em aquecimento (MT5 calcula apos reload)" : "falha ao copiar RSI"),
               " | BarsCalc=", calcRsi, " | Error=", errRsi,
               " | aviso 1x/hora por conta e simbolo");

      copyOK=false;
   }

   // v1.2.161 - P1.123: os handles NAO sao libertados aqui. Sem leitura, a
   // entrada da cache e descartada para o par sarar na leitura seguinte.
   if(!copyOK)
   {
      SignalCacheDrop(symbol);
      g_sigNoRead++;
      return 0;
   }

   // Logica de sinal v1.21 - vela FECHADA (indice 1) + pullback com reversao
   // BUY: tendencia de alta M15 (EMA50>EMA200) + RSI fechou <45 (pullback) + RSI virando p/ cima
   // SELL: tendencia de baixa M15 (EMA50<EMA200) + RSI fechou >55 (rally) + RSI virando p/ baixo
   // P2.01 (03/11/2026): a MESMA linha era escrita a cada minuto enquanto o
   // sinal persistia - o USDCNH escreveu "[SIGNAL] SELL | RSI[1]=74.26" as
   // 07:03, 07:04, 07:05 e 07:06. O sinal nao mudou, o RSI nao mudou. A
   // classificacao fica identica (o return e o mesmo 1/-1); muda apenas
   // QUANDO a linha vai para o journal: na mudanca de direcao e, no maximo,
   // 1x/hora por CONTA e por simbolo.
   //==================================================
   // v1.2.192 - P1.3515 (09/11/2026): GUARDA DE PLAUSIBILIDADE DO SINAL
   //
   // MEDIDO no backtest do Tester (2026.08.08-2026.11.08, XAUUSD H1):
   //   "[SIGNAL] NEUTRO | XAUUSD | tendencia=ALTA |
   //    EMA50=31.14 EMA200=0.00 | RSI[1]=64.03 RSI[2]=66.78"
   // com XAUUSD a ~4000 USD. CopyBuffer devolvia SUCESSO, mas os handles em
   // cache (v1.2.161) ja nao apontavam para as EMAs do simbolo: a serie lida
   // vinha em escala de oscilador (familia 0-100, RSI/ADX) e a lenta devolvia
   // 0.00. Consequencia: fast[1] > slow[1] sempre verdadeiro -> SELL nunca
   // dispara; RSI nunca abaixo de 45 -> BUY nunca dispara. Medido em 3 meses:
   // 845 varreduras, 845 NoSignal, 0 sinais. Uma EMA de preco tem de estar
   // perto do bid do proprio simbolo; se nao estiver, a cache e descartada e
   // o sinal e relido com handles temporarios. Sem esta guarda o EA fica mudo
   // e nenhuma variante de risco/gate faz o sinal disparar.
   //==================================================
   {
      double bidRef = SymbolInfoDouble(symbol, SYMBOL_BID);

      if(bidRef > 0.0)
      {
         bool fastLixo = (fast[1] <= 0.0 || (MathAbs(fast[1] - bidRef) / bidRef) > 0.25);
         bool slowLixo = (slow[1] <= 0.0 || (MathAbs(slow[1] - bidRef) / bidRef) > 0.25);

         if(fastLixo || slowLixo)
         {
            // Cache suspeita: descartar e reler com handles novos (uma vez).
            SignalCacheDrop(symbol);

            int hFastTmp = iMA(symbol, PERIOD_CURRENT, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
            int hSlowTmp = iMA(symbol, PERIOD_CURRENT, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);

            bool releu = false;

            if(hFastTmp != INVALID_HANDLE && hSlowTmp != INVALID_HANDLE)
            {
               double fTmp[];
               double sTmp[];

               ArrayResize(fTmp, 3);
               ArrayResize(sTmp, 3);
               ArraySetAsSeries(fTmp, true);
               ArraySetAsSeries(sTmp, true);

               if(CopyBuffer(hFastTmp, 0, 0, 3, fTmp) > 0 &&
                  CopyBuffer(hSlowTmp, 0, 0, 3, sTmp) > 0 &&
                  fTmp[1] > 0.0 && sTmp[1] > 0.0 &&
                  (MathAbs(fTmp[1] - bidRef) / bidRef) <= 0.25 &&
                  (MathAbs(sTmp[1] - bidRef) / bidRef) <= 0.25)
               {
                  fast[1] = fTmp[1];
                  fast[2] = fTmp[2];
                  slow[1] = sTmp[1];
                  slow[2] = sTmp[2];
                  releu = true;
               }
            }

            if(hFastTmp != INVALID_HANDLE)
               IndicatorRelease(hFastTmp);

            if(hSlowTmp != INVALID_HANDLE)
               IndicatorRelease(hSlowTmp);

            if(!releu)
            {
               g_sigNoRead++;

               if(AccountLogGatePodeImprimir("signolixo_" + symbol, 600))
                  Print("[SIGNAL] SEM LEITURA | ", symbol,
                        " | series de EMA implausiveis | EMAfast=", DoubleToString(fast[1], _Digits),
                        " | EMAslow=", DoubleToString(slow[1], _Digits),
                        " | bid=", DoubleToString(bidRef, _Digits),
                        " | cache DESCARTADO");

               return 0;
            }
         }
      }
   }

   int sinalLocal = 0;   // D-141: filtro "metade forte" revertido - era impossivel (BUY pedia RSI<45 e >50)

   if(fast[1]>slow[1] && rsi[1]<RSIPullbackBuy && rsi[1]>rsi[2])
      sinalLocal = 1;
   else if(fast[1]<slow[1] && rsi[1]>RSIPullbackSell && rsi[1]<rsi[2])
      sinalLocal = -1;

   if(sinalLocal != 0)
   {
      static string   dirSim[64];
      static int      dirVal[64];
      static datetime dirTs[64];
      static int      dirN = 0;

      int idxDir = -1;

      for(int di = 0; di < dirN; di++)
         if(dirSim[di] == symbol)
           {
            idxDir = di;
            break;
           }

      if(idxDir < 0 && dirN < 64)
        {
         idxDir = dirN;
         dirSim[idxDir] = symbol;
         dirVal[idxDir] = 0;
         dirN++;
        }

      bool imprimirSinal = false;

      if(idxDir >= 0)
        {
         datetime agoraSinal = TimeCurrent();

         if(dirVal[idxDir] != sinalLocal)
            imprimirSinal = true;
         else if((agoraSinal - dirTs[idxDir]) >= 3600 &&
                 AccountLogGatePodeImprimir("sig_dir_" + symbol, 3600))
            imprimirSinal = true;

         if(imprimirSinal)
           {
            dirVal[idxDir] = sinalLocal;
            dirTs[idxDir]  = agoraSinal;
           }
        }

      if(logOnce && imprimirSinal)
         Print(sinalLocal > 0 ? "[SIGNAL] BUY | " : "[SIGNAL] SELL | ",
               symbol, " | RSI[1]=", DoubleToString(rsi[1], 2));

      return sinalLocal;
   }

   //--------------------------------------------------
   // v1.2.94 (02/11/2026) - P1.82: chegou aqui, o simbolo FOI lido e a
   // regra e que nao pediu entrada. 1 linha/15 min por simbolo (11
   // simbolos = 44/hora) para provar leitura viva sem encher o journal.
   //--------------------------------------------------
   g_sigNeutral++;

   static string   neuSim[];
   static datetime neuHora[];

   int nIdx = -1;

   for(int ni = 0; ni < ArraySize(neuSim); ni++)
      if(neuSim[ni] == symbol)
        {
         nIdx = ni;
         break;
        }

   if(nIdx < 0)
     {
      nIdx = ArraySize(neuSim);
      ArrayResize(neuSim, nIdx + 1);
      ArrayResize(neuHora, nIdx + 1);
      neuSim[nIdx]  = symbol;
      neuHora[nIdx] = 0;
     }

   // P2.02: o NEUTRO saia 1x/15 min em CADA grafico, com tendencia, EMA50,
   // EMA200 e RSI iguais nos 15 graficos. Passa a 1x/hora por simbolo e por
   // CONTA (sig_neu_): e estado, nao evento, e o mesmo mercado para todos.
   if(neuHora[nIdx] == 0 || (logNow - neuHora[nIdx]) >= 3600)
     {
      if(!AccountLogGatePodeImprimir("sig_neu_" + symbol, 3600))
         return 0;

      neuHora[nIdx] = logNow;

      int dg = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

      if(dg <= 0)
         dg = 5;

      Print("[SIGNAL] NEUTRO | ", symbol,
            " | tendencia=", (fast[1] > slow[1] ? "ALTA" : "BAIXA"),
            " | EMA50=", DoubleToString(fast[1], dg),
            " EMA200=", DoubleToString(slow[1], dg),
            " | RSI[1]=", DoubleToString(rsi[1], 2),
            " RSI[2]=", DoubleToString(rsi[2], 2),
            " | pede: BUY RSI<", DoubleToString(RSIPullbackBuy, 1), " e a subir",
            " | SELL RSI>", DoubleToString(RSIPullbackSell, 1), " e a descer");
     }

   return 0;
}

#endif
