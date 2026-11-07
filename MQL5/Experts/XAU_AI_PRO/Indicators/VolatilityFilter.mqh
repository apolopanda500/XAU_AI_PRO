// XAU_AI_PRO v1.2.9
#ifndef VOLATILITYFILTER_MQH
#define VOLATILITYFILTER_MQH

#include "SymbolDataReady.mqh"   // v1.2.152 - P1.113


//==================================================
// VOLATILITY FILTER PRO (ATR)
//==================================================


#define VOLATILITY_ATR_PERIOD 14
// v1.2.151 - P1.112: teto de plausibilidade do ATR em percentagem do
// proprio preco. Nenhum simbolo desta lista passa de 2% (ouro ~0.7%, FX
// ~0.1%), logo 5% so pode ser leitura de OUTRO instrumento.
#define ATR_MAX_PLAUSIBLE_PCT 5.0


//==================================================
// HANDLE
//==================================================

int volatilityATRHandle = INVALID_HANDLE;

double volatilityATRBuffer[];

//==================================================
// v1.2.149 (05/11/2026) - P1.108: CACHE DE HANDLE ATR POR SIMBOLO
//
// MEDIDO no journal do expert as 22:39:42 de 04/11, build v1.2.148:
//   [DATA] SEM LEITURA | USDSEK | ATR=0.000000 | ADX=42.12 | RSI=42.99
//   [DATA] SEM LEITURA | USDCNH | ATR=0.000000 | ADX=23.78 | RSI=43.21
// ADX e RSI chegaram com valor real e o ATR chegou a zero no MESMO candle.
// A causa estava aqui: a versao multi-simbolo chamava iATR() e
// IndicatorRelease() na MESMA leitura. O MT5 calcula o indicador de forma
// assincrona, logo o primeiro CopyBuffer de um handle recem-criado pode
// devolver 0 barras - e a funcao deitava o handle fora antes de ele
// aquecer. E exactamente o defeito que o P1.85 corrigiu no ADX (v1.2.96)
// e que ficou por corrigir no ATR.
//
// Efeito medido do ATR a zero: (a) o candle NAO e gravado no dataset,
// porque o [DATA] SEM LEITURA regressa antes do FileWrite, portanto os
// simbolos que nao sao o do grafico nunca chegaram ao CSV; (b) em
// Core/ExecutionEngine.mqh:943 o armPts cai para StoplessArmMinPoints e a
// simulacao de RR corre com um R de 30 pontos em vez do R real do par, um
// fail-open no portao MinSimulationRR.
//
// O handle passa a ser criado UMA vez por simbolo e reutilizado. Sem isso
// nao ha como o indicador aquecer.
//==================================================
#define ATR_SYMBOL_CACHE 256

string g_atrCacheSymbol[ATR_SYMBOL_CACHE];
int    g_atrCacheHandle[ATR_SYMBOL_CACHE];
int    g_atrCacheCount = 0;

//==================================================
// v1.2.156 (05/11/2026) - P1.117: A QUEDA DA ENTRADA ENVENENADA
//
// MEDIDO no reload do perfil XAI_P216_LIVE as 13:53:25.943 de 05/11, uma
// linha por grafico em 240 ms:
//   [ATR] SEM LEITURA | XAUUSD | CopyBuffer sem barras | barsCalc=-1 | erro=4807
//   [ATR] SEM LEITURA | USDSEK | CopyBuffer sem barras | barsCalc=-1 | erro=4807
//   (idem USDJPY, USDCHF, NZDUSD, USDCNH, AUDUSD, GBPUSD, USDSGD, USDCAD,
//    USDCZK, USDBRL, USDRUB)
// Seguidamente, 12 linhas
//   [ATR] LEITURA SUSPEITA | <par> | ATR=22.068570 | grafico=<par> | devolvido=0.0
// com o ATR do OURO a subir 0.107 em 32 s: uma unica serie a evoluir, lida
// por todos os graficos.
//
// Causa: o ATRCacheDrop() do P1.113 foi escrito e NUNCA chamado. O handle
// envenenado ficava na cache para sempre, a guarda de plausibilidade
// devolvia 0.0 em cada leitura e o simbolo nunca sarava.
//
// A correcao nao pode ser "chamar sempre que a leitura e suspeita": um par
// cronicamente mal servido entraria num ciclo criar/libertar e voltaria ao
// defeito do P1.108 (handle deitado fora antes de aquecer, ATR a zero e
// candle fora do dataset). A queda leva um portao por simbolo de 60 s: a
// primeira suspeita deita a entrada fora, as seguintes dentro dessa janela
// apenas devolvem 0.0 e deixam o handle novo aquecer.
//==================================================
#define ATR_DROP_GATE_SEC 60

string   g_atrDropSymbol[ATR_SYMBOL_CACHE];
datetime g_atrDropStamp[ATR_SYMBOL_CACHE];
int      g_atrDropCount = 0;

//==================================================
// v1.2.157 (05/11/2026) - P1.118: O HANDLE QUE NUNCA AQUECE
//
// MEDIDO no reload de 05/11 as 15:12:30-15:12:33, build v1.2.156: os treze
// graficos escrevem [ATR] SEM LEITURA | <par> | CopyBuffer sem barras |
// barsCalc=-1 | erro=4807 - aquecimento normal, e por isso o P1.108 proibe
// libertar o handle nesta ramo. O que NAO estava previsto e o que veio
// depois: as 15:14:25 o mestre (USDCNH) ainda publicava
// [CENARIO] XAUUSD | ATR%=sem leitura e as 15:14:47
// [CENARIO] USDCNH | ATR%=sem leitura - o proprio simbolo do grafico, mais de
// dois minutos depois do arranque. As 15:18:10 a sonda XAI_AtrDiag, no MESMO
// grafico USDCNH H1, leu os dois com um handle novo: XAUUSD copy=1
// atr=22.476429 atrPct=0.5485 bars=60369 e USDCNH copy=1 atr=0.002087
// atrPct=0.0313 bars=66887. A serie existe e o dado esta la; o handle em
// cache e que nunca aqueceu.
//
// Este caminho devolve 0.0 sem valor nenhum, logo a guarda de plausibilidade
// do P1.112 nunca o ve e o ATRCacheDrop do P1.117 nunca dispara: o par fica
// sem ATR para sempre, que era exactamente o sintoma a fechar.
//
// A correcao respeita o P1.108: NAO se liberta no primeiro CopyBuffer falhado.
// Marca-se o instante da primeira falha por simbolo e, se a MESMA leitura
// continuar a falhar ATR_STALE_RECREATE_SEC (180 s) depois, a entrada sai da
// cache uma vez e o simbolo ganha um handle novo. Uma leitura com exito
// limpa a marca, portanto um handle que aquece tarde nunca e deitado fora.
//==================================================
#define ATR_STALE_RECREATE_SEC 180

string   g_atrStaleSymbol[ATR_SYMBOL_CACHE];
datetime g_atrStaleSince[ATR_SYMBOL_CACHE];
int      g_atrStaleCount = 0;

int ATRStaleSlot(string symbol)
{
   for(int i = 0; i < g_atrStaleCount; i++)
      if(g_atrStaleSymbol[i] == symbol)
         return i;

   if(g_atrStaleCount >= ATR_SYMBOL_CACHE)
      return -1;

   g_atrStaleSymbol[g_atrStaleCount] = symbol;
   g_atrStaleSince[g_atrStaleCount] = TimeCurrent();
   g_atrStaleCount++;

   return g_atrStaleCount - 1;
}

bool ATRStaleExpired(string symbol)
{
   int slot = ATRStaleSlot(symbol);
   if(slot < 0)
      return false;

   if(TimeCurrent() - g_atrStaleSince[slot] < ATR_STALE_RECREATE_SEC)
      return false;

   g_atrStaleSince[slot] = TimeCurrent();
   return true;
}

void ATRStaleClear(string symbol)
{
   int slot = ATRStaleSlot(symbol);
   if(slot < 0)
      return;

   g_atrStaleSince[slot] = TimeCurrent();
}

bool ATRCacheDropAllowed(string symbol)
{
   datetime agora = TimeCurrent();

   for(int i = 0; i < g_atrDropCount; i++)
      if(g_atrDropSymbol[i] == symbol)
        {
         if(agora - g_atrDropStamp[i] < ATR_DROP_GATE_SEC)
            return false;

         g_atrDropStamp[i] = agora;
         return true;
        }

   if(g_atrDropCount >= ATR_SYMBOL_CACHE)
      return false;

   g_atrDropSymbol[g_atrDropCount] = symbol;
   g_atrDropStamp[g_atrDropCount] = agora;
   g_atrDropCount++;

   return true;
}

//==================================================
// v1.2.169 (05/11/2026) - P1.132: A IDENTIDADE DO HANDLE DO ATR
//
// MEDIDO no journal do expert de 05/11 entre as 22:10:48 e as 22:11:06, com
// get_expert_journal sobre 47 registos: o MESMO handle=10 serve XAUUSD,
// USDJPY, USDSEK, USDCNH, USDCAD, AUDUSD, USDCZK, USDCHF, GBPUSD, USDSGD e
// NZDUSD; barsCalc=60374 em todos (que e exactamente Bars(XAUUSD,H1)) contra
// barrasSerie 100016 / 72098 / 66894; e o valor devolvido e o mesmo
// ATR=34.857860 em oito pares cujos precos vao de 0.5594 (NZDUSD) a 157.8
// (USDJPY). A guarda de plausibilidade do P1.112 faz o que promete e devolve
// 0.0 ("[ATR] LEITURA SUSPEITA ... ATR%=2487.31"), mas nao pode mudar a
// identidade da serie: ATRCacheDrop + IndicatorRelease + iATR devolvem o
// MESMO handle 10. Foi por isso que as "auto-curas" do P1.113/P1.117/P1.122
// falharam tres vezes - recriar nao desliga o handle da serie errada.
//
// Correcao em tres partes, nenhuma delas a mexer em limites, lote, alvo,
// stop, spread, RR, regra de entrada/saida ou parametro de risco:
//  (1) O handle deixa de ser a unica fonte. Passa a haver um ATR calculado
//      da PROPRIA serie do simbolo (CopyRates + True Range + suavizacao de
//      Wilder, a mesma formula do iATR), que nao depende de handle nenhum.
//  (2) Cada leitura com sucesso e conferida contra esse valor, no maximo uma
//      vez por ATR_VERIFY_SEC por simbolo. Diferenca acima de
//      ATR_IDENTITY_TOL_PCT por cento significa que o handle responde por
//      outra serie: publica-se [ATR] IDENTIDADE ERRADA com os dois valores e
//      devolve-se o valor da serie certa, em vez do ATR do ouro.
//  (3) Depois de ATR_IDENTITY_MAX_FAIL falhas provadas no mesmo build, o
//      simbolo deixa de pedir handles e passa a usar sempre o calculo da
//      serie propria. E fail-closed: sem leitura devolve 0.0, nunca um valor
//      de outro instrumento.
//==================================================
#define ATR_IDENTITY_MAX_FAIL  2
#define ATR_IDENTITY_TOL_PCT   25.0
#define ATR_VERIFY_SEC         300
#define ATR_4807_DROP_SEC      900

string   g_atrIdSymbol[ATR_SYMBOL_CACHE];
int      g_atrIdFail[ATR_SYMBOL_CACHE];
bool     g_atrIdRatesOnly[ATR_SYMBOL_CACHE];
datetime g_atrIdStamp[ATR_SYMBOL_CACHE];
datetime g_atrIdDrop[ATR_SYMBOL_CACHE];
int      g_atrIdCount = 0;

int ATRIdentitySlot(string symbol)
{
   for(int i = 0; i < g_atrIdCount; i++)
      if(g_atrIdSymbol[i] == symbol)
         return i;

   if(g_atrIdCount >= ATR_SYMBOL_CACHE)
      return -1;

   g_atrIdSymbol[g_atrIdCount] = symbol;
   g_atrIdFail[g_atrIdCount] = 0;
   g_atrIdRatesOnly[g_atrIdCount] = false;
   g_atrIdStamp[g_atrIdCount] = 0;
   g_atrIdDrop[g_atrIdCount] = 0;
   g_atrIdCount++;

   return g_atrIdCount - 1;
}

bool ATRRatesOnly(string symbol)
{
   int slot = ATRIdentitySlot(symbol);
   if(slot < 0)
      return false;

   return g_atrIdRatesOnly[slot];
}

bool ATRIdentityShouldVerify(string symbol)
{
   int slot = ATRIdentitySlot(symbol);
   if(slot < 0)
      return false;

   datetime agora = TimeCurrent();
   if(g_atrIdStamp[slot] > 0 && agora - g_atrIdStamp[slot] < ATR_VERIFY_SEC)
      return false;

   g_atrIdStamp[slot] = agora;
   return true;
}

void ATRIdentityClear(string symbol)
{
   int slot = ATRIdentitySlot(symbol);
   if(slot < 0)
      return;

   g_atrIdFail[slot] = 0;
}

void ATRIdentityFail(string symbol, double doHandle, double daSerie)
{
   int slot = ATRIdentitySlot(symbol);
   if(slot < 0)
      return;

   // Um falso positivo nao pode matar o handle para sempre: so a falha
   // repetida no mesmo build muda o simbolo para o calculo da serie.
   if(g_atrIdFail[slot] < ATR_IDENTITY_MAX_FAIL)
      g_atrIdFail[slot]++;

   // v1.2.173 - P1.137: FALHA PROVADA REVERIFICA JA NA LEITURA SEGUINTE.
   //
   // A marca de ATR_VERIFY_SEC existe para nao pagar um CopyRates em cada
   // leitura. Mas depois de o desvio ser PROVADO, manter a marca significa
   // continuar a entregar ao pipeline o valor do handle errado durante os
   // 300 s seguintes - que e exactamente o que o P1.132 quis fechar. Com a
   // marca a zero a leitura seguinte volta a conferir e, apos
   // ATR_IDENTITY_MAX_FAIL falhas provadas (2 leituras), o simbolo cai em
   // rates-only, em vez de esperar 10 minutos. Nenhum limite, lote, alvo,
   // stop, spread, preco, RR ou regra de entrada ou de saida e tocado.
   g_atrIdStamp[slot] = 0;

   if(g_atrIdFail[slot] >= ATR_IDENTITY_MAX_FAIL)
      g_atrIdRatesOnly[slot] = true;

   if(AccountLogGatePodeImprimir("atr_identidade_" + symbol + "_" + IntegerToString((long)__DATETIME__), 3600))
      Print("[ATR] IDENTIDADE ERRADA | ", symbol,
            " | doHandle=", DoubleToString(doHandle, 6),
            " | daSerie=", DoubleToString(daSerie, 6),
            " | falhas=", IntegerToString(g_atrIdFail[slot]),
            " | usaHandleAgora=", (g_atrIdRatesOnly[slot] ? "NAO" : "SIM"),
            " | grafico=", _Symbol);
}

void ATRIdentityReset()
{
   g_atrIdCount = 0;
}

// v1.2.172 - P1.135: handle recusado (4807) passa a ser RECRIADO.
//
// MEDIDO no B-031b (job 20260801_20261105, 06/11): o terminal responde
// erro=4807 (ERR_INDICATOR_WRONG_HANDLE) e barsCalc=-1 ao MESMO handle em
// todos os ticks, com barrasSerie=barrasGrafico e serieSync=1. Um handle que
// o terminal declara ERRADO nao aquece com o tempo: ao contrario do ramo de
// 'sem barras' do P1.108/P1.113, onde esperar e o comportamento certo, aqui
// esperar deixa o simbolo dependente da serie para sempre. O P1.134 garante
// que o ATR nao fica cego; este garante que o handle primario volta a existir.
//
// Carimbo por simbolo limita a recriacao a 1x/ATR_4807_DROP_SEC, para um
// terminal que recusa sempre nao ser bombardeado com iATR no tester.
// Nenhum limite, lote, alvo, stop, spread, preco, regra de entrada ou de
// saida muda: muda apenas QUANDO a entrada da cache e descartada.
bool ATRDropShouldForce(string symbol)
{
   int slot = ATRIdentitySlot(symbol);
   if(slot < 0)
      return false;

   datetime agora = TimeCurrent();
   if(g_atrIdDrop[slot] > 0 && agora - g_atrIdDrop[slot] < ATR_4807_DROP_SEC)
      return false;

   g_atrIdDrop[slot] = agora;
   return true;
}

// ATR da propria serie do simbolo: True Range + suavizacao de Wilder.
// Nao usa handle, logo nao pode ficar ligado a serie de outro instrumento.
double ATRFromRates(string symbol, ENUM_TIMEFRAMES tf, int period)
{
   if(period < 1)
      return 0.0;

   MqlRates rates[];
   // v1.2.173 - P1.137: A JANELA DE AQUECIMENTO ERA CURTA DE MAIS.
   //
   // MEDIDO no journal do expert a 06/11 as 14:11:29, logo depois do reload
   // do perfil: [ATR] IDENTIDADE ERRADA | XAUUSD | doHandle=15.890000 |
   // daSerie=22.774173 e, no mesmo segundo, USDSGD | doHandle=0.000350 |
   // daSerie=0.000511. Os dois desvios sao o MESMO racio (0.698 e 0.685) em
   // instrumentos sem relacao nenhuma (ouro com duas casas, SGD com seis).
   // Um handle preso noutra serie - que e o que o P1.132 procura - devolve o
   // ATR do OURO dentro de um par de FX: racios de milhares, nunca 0.69. Um
   // racio constante em simbolos diferentes e vies de CALCULO, nao troca de
   // identidade; a comparacao do P1.132 estava a medir o aquecimento DESTA
   // funcao em vez da identidade do handle.
   //
   // Causa: period*3+3 = 45 barras dao apenas 31 iteracoes de Wilder depois
   // da semente SMA, logo o peso que resta a semente e (13/14)^31 = 10% e o
   // valor depende do troco de 45 barras atras, nao do presente. O iATR usa a
   // serie inteira e esta convergido. Numa sessao em que a volatilidade subiu,
   // a semente antiga puxa o resultado para baixo do real; com o ATR a subir
   // depressa, a semente puxa para cima - que e a direcao medida (daSerie >
   // doHandle nos dois simbolos).
   //
   // Com period*20+10 = 290 barras o residuo da semente e (13/14)^275 ~ 1e-9,
   // portanto a funcao passa a devolver o Wilder CONVERGIDO, que e a definicao
   // do ATR e o que o handle devolve. Nenhum limite, lote, alvo, stop, spread,
   // preco, RR, regra de entrada ou de saida muda: muda o valor de um
   // indicador que estava a ser calculado com aquecimento insuficiente.
   int need = period * 20 + 10;
   int copied = CopyRates(symbol, tf, 0, need, rates);
   if(copied < period + 2)
      return 0.0;

   // CopyRates sem ArraySetAsSeries ordena do mais antigo para o mais novo.
   double soma = 0.0;
   for(int i = 1; i <= period; i++)
     {
      double fechoAnterior = rates[i - 1].close;
      double tr = MathMax(rates[i].high - rates[i].low,
                          MathMax(MathAbs(rates[i].high - fechoAnterior),
                                  MathAbs(rates[i].low - fechoAnterior)));
      soma += tr;
     }

   double atr = soma / (double)period;

   for(int i = period + 1; i < copied; i++)
     {
      double fechoAnterior = rates[i - 1].close;
      double tr = MathMax(rates[i].high - rates[i].low,
                          MathMax(MathAbs(rates[i].high - fechoAnterior),
                                  MathAbs(rates[i].low - fechoAnterior)));
      atr = (atr * (period - 1) + tr) / (double)period;
     }

   return atr;
}

int ATRSymbolHandle(string symbol)
{
   for(int i = 0; i < g_atrCacheCount; i++)
      if(g_atrCacheSymbol[i] == symbol)
         return g_atrCacheHandle[i];

   if(g_atrCacheCount >= ATR_SYMBOL_CACHE)
      return INVALID_HANDLE;

   // v1.2.152 - P1.113: o handle so nasce depois de a serie do simbolo
   // existir. Antes, um handle criado com a serie ainda por construir ficava
   // ligado a serie do GRAFICO para sempre (medido: ATR do ouro em 7 pares).
   XAI_WaitSeriesReady(symbol, (ENUM_TIMEFRAMES)Period());

   int handle = iATR(symbol, (ENUM_TIMEFRAMES)Period(), VOLATILITY_ATR_PERIOD);

   if(handle == INVALID_HANDLE)
      return INVALID_HANDLE;

   g_atrCacheSymbol[g_atrCacheCount] = symbol;
   g_atrCacheHandle[g_atrCacheCount] = handle;
   g_atrCacheCount++;

   return handle;
}

//==================================================
// v1.2.152 (05/11/2026) - P1.113: CACHE AUTOLIMPAVEL
//
// A cache por simbolo do P1.108 resolveu o aquecimento, mas guardava para
// sempre o PRIMEIRO handle criado para cada simbolo. Se esse handle nasceu
// enquanto a serie do par ainda nao existia no terminal, ele responde com a
// serie de OUTRO instrumento e nunca mais e substituido - foi exactamente
// isso que manteve o ATR do OURO (29.454290) a ser devolvido em GBPUSD,
// USDJPY, AUDUSD, USDCAD, NZDUSD, USDCHF e USDCNH depois do reload das
// 23:16:40 de 04/11, e que deixou esses pares sem ATR (e sem candle no
// dataset) durante horas.
//
// A leitura invalida passa a deitar fora a entrada da cache, para a leitura
// seguinte criar um handle novo e o simbolo poder sarar sem reiniciar o
// terminal.
//==================================================
void ATRCacheDrop(string symbol)
{
   for(int i = 0; i < g_atrCacheCount; i++)
     {
      if(g_atrCacheSymbol[i] != symbol)
         continue;

      if(g_atrCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_atrCacheHandle[i]);

      for(int j = i; j < g_atrCacheCount - 1; j++)
        {
         g_atrCacheSymbol[j] = g_atrCacheSymbol[j + 1];
         g_atrCacheHandle[j] = g_atrCacheHandle[j + 1];
        }

      g_atrCacheCount--;
      g_atrCacheSymbol[g_atrCacheCount] = "";
      g_atrCacheHandle[g_atrCacheCount] = INVALID_HANDLE;

      return;
     }
}

void ATRReleaseSymbolHandles()
{
   for(int i = 0; i < g_atrCacheCount; i++)
      if(g_atrCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_atrCacheHandle[i]);

   g_atrCacheCount = 0;
}



//==================================================
// INIT
//==================================================

bool InitATR()
{

   // v1.2.149 - P1.108: a cache e indexada por simbolo mas o timeframe entra
   // na criacao do handle (PERIOD_CURRENT), logo os handles antigos
   // responderiam com o periodo errado numa mudanca de timeframe.
   ATRReleaseSymbolHandles();

   volatilityATRHandle =
      iATR(
         _Symbol,
         PERIOD_CURRENT,
         VOLATILITY_ATR_PERIOD
      );


   if(volatilityATRHandle == INVALID_HANDLE)
   {
      Print("Erro criando ATR");
      return false;
   }


   ArraySetAsSeries(
      volatilityATRBuffer,
      true
   );


   return true;

}



//==================================================
// GET ATR
//==================================================

double GetATRInstance()
{

   if(volatilityATRHandle == INVALID_HANDLE)
      return 0.0;



   if(
      CopyBuffer(
         volatilityATRHandle,
         0,
         0,
         3,
         volatilityATRBuffer
      ) <= 0
   )
      return 0.0;



   return NormalizeDouble(
      volatilityATRBuffer[0],
      _Digits
   );

}


//==================================================
// v1.2.155 (05/11/2026) - P1.116: o ATR sem leitura nao dizia PORQUE
//
// MEDIDO no journal do expert as 23:45-23:51 de 04/11, build v1.2.154, master
// USDCNH H1: as linhas [CENARIO] do ciclo saem com ATR% real em nove simbolos
// (EURUSD 0.12, GBPUSD 0.10, USDJPY 0.12, NZDUSD 0.17, USDCAD 0.10, USDCHF
// 0.15) e com "ATR%=sem leitura" exactamente em XAUUSD e USDCNH. No MESMO
// segundo, a sonda Scripts/XAI_AtrDiag.mq5 executada no grafico USDCNH H1 as
// 23:50:44 leu ATR nos dois: XAUUSD atr=29.543571 atrPct=0.7145 barsCalc=60353
// copy=1; USDCNH atr=0.002889 atrPct=0.0433 barsCalc=66871 copy=1; err=0.
// A serie existe, o simbolo esta sincronizado e o indicador aquece, logo o
// zero vem do getter do EA - e nao podia ser nomeado porque GetATR(string)
// tem TRES saidas silenciosas que devolvem 0.0 sem escrever nada: serie nao
// provada (XAI_SymbolDataReady), handle invalido e CopyBuffer sem barras.
// O ADX tem ADXLogNoRead desde o P1.91; o ATR nao tinha equivalente, e foi
// por isso que este defeito atravessou varios ciclos de medicao sem nome.
// Esta funcao NAO altera valor nenhum: publica o motivo em 1 linha por
// simbolo por hora por CONTA, com o handle e as barras calculadas, para a
// proxima medicao dizer QUAL dos tres ramos dispara. Nenhum limite, lote,
// alvo, stop, spread, preco, regra de entrada ou de saida, ou parametro de
// risco e tocado: muda o texto de um diagnostico que antes nao existia.
// v1.2.159 - P1.121: a chave do portao leva a marca de COMPILACAO, senao o
// ficheiro de Common\Files gravado por um build antigo calava o build novo.
//==================================================
void ATRLogNoRead(string symbol, string motivo)
  {
   // P1.133: o contador sobrevive ao throttle - a linha diz QUANTAS vezes
   // o ramo disparou, nao so que disparou. Sem isto, com o gate a filtrar,
   // a frequencia do defeito ficaria invisivel no journal.
   static int s_ocorrSemLeitura = 0;
   s_ocorrSemLeitura++;
   if(!AccountLogGatePodeImprimir("atr_no_read_" + symbol + "_" + IntegerToString((long)__DATETIME__), 3600))
      return;

   Print("[ATR] SEM LEITURA | ", symbol,
         " | ", motivo,
         " | ocorrencias_instancia=", IntegerToString(s_ocorrSemLeitura),
         " | grafico=", _Symbol);
  }

double GetATR(string symbol)
{
   // v1.2.150 - P1.109: o simbolo do grafico deixa de usar o handle
   // criado em OnInit (ver a nota do wrapper GetATR() mais abaixo).
   if(symbol=="")
      symbol=_Symbol;

   // v1.2.152 - P1.113: sem serie provada nao ha leitura. O simbolo do
   // grafico passa sempre; um par estrangeiro so le depois de o terminal
   // declarar a serie sincronizada e com barras (ver SymbolDataReady.mqh).
   // v1.2.155 - P1.116: avaliar a prontidao UMA vez e publicar o motivo
   bool xaiSeriePronta = XAI_SymbolDataReady(symbol);
   if(!xaiSeriePronta)
      ATRLogNoRead(symbol, "serie do simbolo nao provada (XAI_SymbolDataReady=false)");
   if(!xaiSeriePronta)
      return 0.0;

   // Normaliza com os digitos do proprio simbolo (nao do chart),
   // senao ATR de pares com mais casas (ex: EURUSD, 5 digitos)
   // e arredondado a zero (NormalizeDouble(x,_Digits) com _Digits=2).
   int symbolDigits=(int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(symbolDigits<=0)
      symbolDigits=_Digits;

   // v1.2.149 - P1.108: handle por simbolo, em CACHE, e nunca libertado
   // na leitura. Era a libertacao imediata que impedia o aquecimento.
   // v1.2.169 - P1.132: simbolo cuja identidade foi provada errada
   // ATR_IDENTITY_MAX_FAIL vezes neste build deixa de pedir handles. O valor
   // continua a vir da propria serie, logo nao ha risco de ler outro
   // instrumento; sem leitura devolve 0.0 e o resto do pipeline trata o zero
   // como sempre tratou (fail-closed).
   if(ATRRatesOnly(symbol))
     {
      double atrSerie=ATRFromRates(symbol, (ENUM_TIMEFRAMES)Period(), VOLATILITY_ATR_PERIOD);
      if(atrSerie>0.0)
         return NormalizeDouble(atrSerie, symbolDigits);
     }

   int handle=ATRSymbolHandle(symbol);
   if(handle==INVALID_HANDLE)
     {
      ATRLogNoRead(symbol, "handle invalido (ATRSymbolHandle sem entrada na cache)");
      return 0.0;
     }
   // handle ja validado no bloco acima; verificacao duplicada removida.

   double buf[];
   ArraySetAsSeries(buf, true);

   double result=0.0;

   if(CopyBuffer(handle, 0, 0, 1, buf) > 0)
     {
      result=NormalizeDouble(buf[0], symbolDigits);
      ATRStaleClear(symbol);   // v1.2.157 - P1.118: aqueceu, zera a marca de falha

      // v1.2.169 - P1.132: a leitura do handle so vale se for a serie DESTE
      // simbolo. Uma vez por ATR_VERIFY_SEC confere-se contra o ATR calculado
      // da propria serie; desvio acima de ATR_IDENTITY_TOL_PCT e prova de
      // handle preso noutra serie (medido: ATR do ouro em oito pares). Nesse
      // caso devolve-se o valor da serie certa e conta-se a falha, em vez de
      // entregar ao pipeline o ATR de outro instrumento.
      if(ATRIdentityShouldVerify(symbol))
        {
         double atrDaSerie=ATRFromRates(symbol, (ENUM_TIMEFRAMES)Period(), VOLATILITY_ATR_PERIOD);
         if(atrDaSerie>0.0 && result>0.0)
           {
            double desvio=MathAbs(result-atrDaSerie)/atrDaSerie*100.0;
            if(desvio>ATR_IDENTITY_TOL_PCT)
              {
               ATRIdentityFail(symbol, result, atrDaSerie);
               result=NormalizeDouble(atrDaSerie, symbolDigits);
              }
            else
               ATRIdentityClear(symbol);
           }
        }
     }
   else
     {
      // v1.2.152 - P1.113: sem barras o handle CONTINUA na cache. Retira-lo
      // aqui seria repetir o defeito do P1.108: libertar durante o
      // aquecimento impede o indicador de aquecer.
      int copyErr=GetLastError();
      int barsCalcAgora=(int)BarsCalculated(handle);
      // v1.2.172 - P1.135: 4807 e handle ERRADO, nao handle a aquecer. Deita
      // fora a entrada da cache (no maximo 1x/ATR_4807_DROP_SEC por simbolo)
      // para a leitura seguinte criar handle novo. A serie do P1.134 continua
      // a servir o valor enquanto o handle nao volta.
      if(copyErr == 4807 && ATRDropShouldForce(symbol))
        {
         ATRCacheDrop(symbol);

         if(AccountLogGatePodeImprimir("atr_handle_recriado_" + symbol + "_" + IntegerToString((long)__DATETIME__), 3600))
            Print("[ATR] HANDLE RECRIADO | ", symbol,
                  " | erro=4807 (ERR_INDICATOR_WRONG_HANDLE) | barsCalc=", IntegerToString(barsCalcAgora),
                  " | entrada antiga removida da cache | grafico=", _Symbol);
        }


      // v1.2.171 - P1.134: um handle recusado nao pode cegar o ATR.
      // MEDIDO no B-031b a 06/11 00:26: no tester o handle 10 e recusado
      // pelo terminal (erro=4807, barsCalc=-1) em todos os ticks depois da
      // virada de dia simulada, com barrasSerie=barrasGrafico e serieSync=1.
      // O P1.132 so mandava ler a serie DEPOIS de ATR_IDENTITY_MAX_FAIL
      // falhas de IDENTIDADE, e essas so contam quando o CopyBuffer devolve
      // valor: com o handle sempre recusado o simbolo nunca chegava ao
      // rates-only e o ATR ficava em 0.0 para sempre (fail-closed). Aqui a
      // serie do proprio simbolo passa a ser a primeira alternativa quando
      // o handle falha, logo o ATR fica disponivel mesmo com handle morto.
      // Nenhum limite, lote, alvo, stop, spread, preco ou regra de entrada
      // ou de saida muda: muda de ONDE vem o ATR quando o handle nao serve.
      double atrDaSerieAgora=ATRFromRates(symbol, (ENUM_TIMEFRAMES)Period(), VOLATILITY_ATR_PERIOD);
      if(atrDaSerieAgora>0.0)
        {
         if(AccountLogGatePodeImprimir("atr_rates_ok_" + symbol + "_" + IntegerToString((long)__DATETIME__), 3600))
            Print("[ATR] SERIE OK | ", symbol,
                  " | atrSerie=", DoubleToString(atrDaSerieAgora, symbolDigits),
                  " | handleRecusado=", IntegerToString(handle),
                  " | barsCalc=", IntegerToString(barsCalcAgora),
                  " | erro=", IntegerToString(copyErr),
                  " | grafico=", _Symbol);
         return NormalizeDouble(atrDaSerieAgora, symbolDigits);
        }
      // v1.2.160 - P1.122: a falha passa a publicar a IDENTIDADE do handle.
      // MEDIDO no mestre USDCNH,H1 a 05/11 entre as 18:51:02 e as 19:07:18: a
      // MESMA instancia alterna [CENARIO] USDCNH | ATR%=0.03 (leitura boa) e
      // ATR%=sem leitura(atr=0.000000,bid=6.665560) a cada ~90 s, o que prova
      // que o handle deste simbolo nao esta morto - o "nunca aquece" do P1.119
      // descrevia mal o defeito. O que a linha nao dizia era QUAL das duas
      // causas: serie sem barras no terminal, ou handle ligado a serie de
      // OUTRO simbolo. barsCalc (do handle) ao lado de barrasSerie (da serie
      // pedida) separa os dois casos: iguais = handle certo, diferentes =
      // handle preso noutra serie. serieSync diz se o terminal considera a
      // serie sincronizada. Nenhum limite, lote, alvo, stop, spread, preco,
      // regra de entrada ou de saida, ou parametro de risco foi alterado.
      long xaiSerieSync=0;
      SeriesInfoInteger(symbol, (ENUM_TIMEFRAMES)Period(), SERIES_SYNCHRONIZED, xaiSerieSync);
      ATRLogNoRead(symbol, "CopyBuffer sem barras | barsCalc=" + IntegerToString(barsCalcAgora) + " | erro=" + IntegerToString(copyErr)
                   + " | handle=" + IntegerToString(handle)
                   + " | barrasSerie=" + IntegerToString(Bars(symbol, (ENUM_TIMEFRAMES)Period()))
                   + " | barrasGrafico=" + IntegerToString(Bars(_Symbol, (ENUM_TIMEFRAMES)Period()))
                   + " | serieSync=" + IntegerToString((int)xaiSerieSync)
                   + " | bid=" + DoubleToString(SymbolInfoDouble(symbol, SYMBOL_BID), symbolDigits));

      // v1.2.157 - P1.118: handle que NUNCA aquece. MEDIDO as 15:14:25 e
      // 15:14:47: XAUUSD e USDCNH ainda com ATR%=sem leitura mais de dois
      // minutos depois do arranque, enquanto uma sonda com handle novo leu os
      // dois (atrPct 0.5485 e 0.0313). Como este ramo devolve 0.0 sem valor,
      // a guarda de plausibilidade nao o ve e o ATRCacheDrop do P1.117 nunca
      // dispara. O P1.108 proibe deitar o handle fora no PRIMEIRO CopyBuffer
      // falhado; aqui so se deita fora quando a MESMA falha dura ha mais de
      // ATR_STALE_RECREATE_SEC, e uma leitura com exito limpa a marca.
      if(ATRStaleExpired(symbol) && ATRCacheDropAllowed(symbol))
        {
         ATRCacheDrop(symbol);

         if(AccountLogGatePodeImprimir("atr_handle_morto_" + symbol + "_" + IntegerToString((long)__DATETIME__), 3600))
            Print("[ATR] HANDLE MORTO | ", symbol,
                  " | sem barras ha ", IntegerToString(ATR_STALE_RECREATE_SEC), " s",
                  " | barsCalc=", IntegerToString(barsCalcAgora),
                  " | erro=", IntegerToString(copyErr),
                  " | entrada removida da cache | grafico=", _Symbol);
        }
      return 0.0;
     }

   // v1.2.149 - P1.108: handle NAO libertado aqui; fica na cache e e
   // libertado em ReleaseATR e em InitATR. Sem barras calculadas o
   // resultado e 0.0 e a leitura seguinte ja encontra o indicador quente.

   // v1.2.151 - P1.112: guarda de plausibilidade. MEDIDO a 22:46:55 de 04/11:
   // [CENARIO] USDJPY | VOLATILIDADE_ALTA | ADX=33.2 | ATR%=17.97 - o ATR do
   // OURO (28.39) lido num par de iene (158.354), 150x o ATR real (0.195).
   // Aqui o valor absurdo deixa de sair como se fosse leitura: devolve 0.0
   // (o consumidor trata como sem leitura, o mesmo caminho de quando o
   // indicador ainda aquece) e escreve uma linha com os DOIS simbolos, para
   // a proxima medicao dizer QUAL instancia le o par errado.
   if(result > 0.0)
     {
      double precoAtual = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(precoAtual > 0.0 && (result / precoAtual) * 100.0 > ATR_MAX_PLAUSIBLE_PCT)
        {
         if(AccountLogGatePodeImprimir("atr_absurdo_" + symbol + "_" + IntegerToString((long)__DATETIME__), 3600))
            Print("[ATR] LEITURA SUSPEITA | ", symbol,
                  " | ATR=", DoubleToString(result, 6),
                  " | preco=", DoubleToString(precoAtual, symbolDigits),
                  " | ATR%=", DoubleToString((result / precoAtual) * 100.0, 2),
                  " | grafico=", _Symbol,
                  " | handle=", IntegerToString(handle),
                  " | barsCalc=", IntegerToString(BarsCalculated(handle)),
                  " | barrasSerie=", IntegerToString(Bars(symbol, (ENUM_TIMEFRAMES)Period())),
                  " | barrasGrafico=", IntegerToString(Bars(_Symbol, (ENUM_TIMEFRAMES)Period())),
                  " | devolvido=0.0");

         // v1.2.152 - P1.113: valor impossivel = handle preso a serie de
         // outro instrumento. A entrada sai da cache e o simbolo sara na
         // leitura seguinte, com um handle novo (v1.2.156 - P1.117).
         // A queda e limitada a uma por simbolo a cada ATR_DROP_GATE_SEC
         // segundos, para nao repetir o defeito do P1.108 (handle libertado
         // antes de aquecer).
         if(ATRCacheDropAllowed(symbol))
            ATRCacheDrop(symbol);

         return 0.0;
        }
     }

   return result;
}



//==================================================
double GetATR()
{
   // v1.2.150 - P1.109: o simbolo do grafico passa a ler pela cache por
   // simbolo, tal como o GetADX e o GetRSI ja faziam. O handle unico criado
   // em OnInit sobrevivia ao reload do perfil e podia devolver a serie de
   // OUTRO par (medido a 22:46:55: [CENARIO] USDJPY | ADX=33.2 | ATR%=17.97,
   // que sao o ADX e o ATR do XAUUSD). A leitura antiga fica em
   // GetATRInstance() e so e usada se alguem a chamar de proposito.
   return GetATR(_Symbol);
}


// RELEASE
//==================================================

void ReleaseATR()
{

   ATRReleaseSymbolHandles();   // v1.2.149 - P1.108

   if(volatilityATRHandle != INVALID_HANDLE)
   {

      IndicatorRelease(
         volatilityATRHandle
      );


      volatilityATRHandle = INVALID_HANDLE;

   }

}



//==================================================
// ATR POINTS
//==================================================

double GetATRPoints()
{

   double atr =
      GetATR();


   if(atr <= 0)
      return 0;



   return(
      atr /
      _Point
   );

}



//==================================================
// VOLATILITY FILTER
//==================================================

bool GoodVolatility(
   double minATRPoints
)
{

   double points =
      GetATRPoints();


   if(points <= 0)
      return false;


   return(
      points >= minATRPoints
   );

}



//==================================================
// AI VOLATILITY SCORE
//==================================================

double GetVolatilityScore()
{

   double atrPoints =
      GetATRPoints();



   if(atrPoints >= 300)
      return 100;


   if(atrPoints >= 150)
      return 80;


   if(atrPoints >= 70)
      return 60;


   if(atrPoints >= 30)
      return 40;


   return 20;

}



//==================================================
// HIGH VOLATILITY
//==================================================

bool HighVolatility(
   double multiplier
)
{

   double atr =
      GetATR();


   if(atr <= 0)
      return false;



   double averageATR = 0;


   // v1.2.150 - P1.109: a media de 20 barras tem de vir do MESMO
   // handle que o valor comparado, senao compara dois simbolos.
   int hVol = ATRSymbolHandle(_Symbol);
   int copied = 0;

   if(hVol != INVALID_HANDLE)
      copied = CopyBuffer(
         hVol,
         0,
         1,
         20,
         volatilityATRBuffer
      );


   if(copied <= 0)
      return false;



   for(int i=0;i<copied;i++)
      averageATR += volatilityATRBuffer[i];


   averageATR /= copied;



   return(
      atr >=
      averageATR * multiplier
   );

}



//==================================================
// MARKET STATE
//==================================================

bool IsLowVolatility()
{

   return(
      GetATRPoints() < 30
   );

}



bool IsNormalVolatility()
{

   double p =
      GetATRPoints();


   return(
      p >= 30 &&
      p < 150
   );

}



bool IsExtremeVolatility()
{

   return(
      GetATRPoints() >= 300
   );

}



#endif