// XAU_AI_PRO v1.2.9
#ifndef ADX_MQH
#define ADX_MQH

#include "../Core/Config.mqh"
#include "SymbolDataReady.mqh"   // v1.2.152 - P1.113

//==================================================
// ADX INDICATOR
// XAU_AI_PRO
//==================================================

int adxHandle = INVALID_HANDLE;
double adxBuffer[];

//==================================================
// MÉTRICAS ADX (F4/20.15)
// adx_unavailable_count: nº de lecturas en las que el
//   ADX no estaba disponible (warm-up/INVALID_HANDLE/err 4807-4073)
//   -> el consumidor hace SKIP (fail-open).
// adx_valid_count: nº de lecturas con valor ADX válido y > 0.
// Si unavailable_count se mantiene ALTO en operación normal,
// indica un problema persistente del indicador (y el fail-open
// lo estaría enmascarando). Reset en InitADX.
//==================================================

int g_adxUnavailable = 0;
int g_adxValid       = 0;

//==================================================
// v1.2.96 (03/11/2026) - P1.85: CACHE DE HANDLE POR SIMBOLO
//
// MEDIDO no journal de 03/11 as 22:34-22:37, com v1.2.95:
//   [SCANNER] RESUMO | simbolos=107..123 | ADX(sem/ok)=294/0
// Zero leituras boas de ADX em cinco minutos seguidos, com o modulo
// dizendo [ADX] INIT OK. A causa estava aqui: a versao multi-simbolo
// chamava iADX() e IndicatorRelease() na MESMA leitura. O MT5 calcula
// o indicador de forma assincrona, logo BarsCalculated() de um handle
// recem-criado e 0 e a funcao devolvia -1.0 SEMPRE - e deitava o
// handle fora antes de ele aquecer. Resultado: o scan de ~110 simbolos
// nunca teve ADX, e o filtro ficava em fail-open permanente sem que
// ninguem visse a causa.
//
// O handle passa a ser criado UMA vez por simbolo e reutilizado. Sem
// isso nao ha como o indicador aquecer. O teto existe para nao crescer
// sem limite se a lista de simbolos mudar.
//==================================================
#define ADX_SYMBOL_CACHE 256

string g_adxCacheSymbol[ADX_SYMBOL_CACHE];
int    g_adxCacheHandle[ADX_SYMBOL_CACHE];
int    g_adxCacheCount = 0;

int ADXSymbolHandle(string symbol)
{
   for(int i = 0; i < g_adxCacheCount; i++)
      if(g_adxCacheSymbol[i] == symbol)
         return g_adxCacheHandle[i];

   if(g_adxCacheCount >= ADX_SYMBOL_CACHE)
      return INVALID_HANDLE;

   // v1.2.152 - P1.113: handle so nasce com a serie do simbolo provada.
   XAI_WaitSeriesReady(symbol, (ENUM_TIMEFRAMES)Period());

   int handle = iADX(symbol, (ENUM_TIMEFRAMES)Period(), ADXPeriod);

   if(handle == INVALID_HANDLE)
      return INVALID_HANDLE;

   g_adxCacheSymbol[g_adxCacheCount] = symbol;
   g_adxCacheHandle[g_adxCacheCount] = handle;
   g_adxCacheCount++;

   return handle;
}

//==================================================
// v1.2.152 (05/11/2026) - P1.113: CACHE AUTOLIMPAVEL
//
// MEDIDO no journal as 23:16:40 de 04/11, build v1.2.151: SETE pares
// (GBPUSD, USDJPY, AUDUSD, USDCAD, NZDUSD, USDCHF, USDCNH) devolveram o
// MESMO ADX=33.77 e o MESMO RSI=82.72 no mesmo segundo, e o ATR devolvido
// era o do OURO (29.454290) num par cotado a 1.34881. Nao existe mercado em
// que sete instrumentos tenham o ADX igual ao centesimo: o handle por
// simbolo nasceu enquanto a serie pedida ainda nao existia e ficou preso a
// serie de OUTRO instrumento. Como o handle nunca saia da cache, o simbolo
// nunca sarava e ficava sem ADX durante horas.
//
// A leitura provada como contaminada passa a deitar fora a entrada da
// cache, para a leitura seguinte criar um handle novo.
//==================================================
void ADXCacheDrop(string symbol)
{
   for(int i = 0; i < g_adxCacheCount; i++)
     {
      if(g_adxCacheSymbol[i] != symbol)
         continue;

      if(g_adxCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_adxCacheHandle[i]);

      for(int j = i; j < g_adxCacheCount - 1; j++)
        {
         g_adxCacheSymbol[j] = g_adxCacheSymbol[j + 1];
         g_adxCacheHandle[j] = g_adxCacheHandle[j + 1];
        }

      g_adxCacheCount--;
      g_adxCacheSymbol[g_adxCacheCount] = "";
      g_adxCacheHandle[g_adxCacheCount] = INVALID_HANDLE;

      return;
     }
}
void ADXReleaseSymbolHandles()
{
   for(int i = 0; i < g_adxCacheCount; i++)
      if(g_adxCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_adxCacheHandle[i]);

   g_adxCacheCount = 0;
}

//==================================================
// v1.2.94 (02/11/2026) - P1.82: PROVA DE "SEM LEITURA"
//
// MEDIDO no journal: o defeito do ADX nao era o valor, era o SILENCIO.
// O dono do pipeline (grafico USDCHF) lia ADX=0.0 e o modulo nao
// imprimia uma unica linha - o veto parecia um filtro a funcionar.
// Uma linha por hora e por simbolo basta para provar que existe e por
// que existe, sem encher o journal.
//==================================================
void ADXLogNoRead(string symbol, string motivo)
{
   static string   sim[];
   static datetime hora[];

   datetime agora = TimeCurrent();
   int      idx   = -1;

   for(int i = 0; i < ArraySize(sim); i++)
      if(sim[i] == symbol)
        {
         idx = i;
         break;
        }

   if(idx < 0)
     {
      idx = ArraySize(sim);
      ArrayResize(sim, idx + 1);
      ArrayResize(hora, idx + 1);
      sim[idx]  = symbol;
      hora[idx] = 0;
     }

   if(hora[idx] != 0 && (agora - hora[idx]) < 3600)
      return;

   hora[idx] = agora;

   if(AccountLogGatePodeImprimir("adxsem_" + symbol, 21600)) Print("[ADX] SEM LEITURA | ", symbol, " | ", motivo, " | tratado como neutro (fail-open)");   // P1.90: 1x/6h por CONTA e por simbolo
}

//==================================================
// v1.2.175 (06/11/2026) - P2: HANDLE DE ADX QUE NUNCA AQUECE
//
// MEDIDO no journal de 06/11 as 15:22:00, grafico USDCNH H1, build v1.2.174:
//   [ADX] SEM LEITURA | USDCNH | CopyBuffer failed | Error=4807 |
//   BarsCalculated=-1 | tratado como neutro (fail-open)
// O P1.91 acertou em tentar o CopyBuffer quando BarsCalculated devolve -1,
// mas o handle criado nesta MESMA leitura ainda nao tem uma barra calculada:
// o MT5 calcula o indicador de forma assincrona. A linha dizia "tratado como
// neutro", que sugere evento passageiro, e a cache por simbolo do P1.85
// NUNCA deitava fora uma entrada que nao aquecesse - logo um handle recusado
// ficava preso ate ao fim da sessao e aquele simbolo ficava sem ADX para
// sempre, com o veto do ADX_OK a ser fail-open silencioso. E a mesma
// assinatura do [ATR] HANDLE MORTO (P1.118) e do 4807 do ATR (P1.135).
//
// Correcao minima, so de leitura de indicador:
// (1) a primeira falha sem barras de cada simbolo passa a ser datada;
// (2) se a MESMA falha durar ADX_STALE_RECREATE_SEC (120 s), a entrada sai
//     da cache e a leitura seguinte cria handle novo, com uma linha
//     [ADX] HANDLE MORTO que publica o erro e as barras calculadas;
// (3) uma leitura com exito limpa a marca, logo o caminho normal nao muda;
// (4) a linha publica se o handle e NOVO (a aquecer) ou se ja falhou antes,
//     para a mensagem deixar de sugerir que o caso e sempre passageiro.
// Nenhum limite, lote, alvo, stop, spread, preco, regra de entrada ou de
// saida, ou parametro de risco foi alterado: muda de ONDE vem o ADX quando o
// handle nao serve e a partir de quando se tenta outro handle.
//==================================================
#define ADX_STALE_RECREATE_SEC 120

datetime ADXNoBarTrack(const string symbol,const bool limpar)
  {
   static string   sim[];
   static datetime desde[];

   int idx = -1;

   for(int i = 0; i < ArraySize(sim); i++)
      if(sim[i] == symbol)
        {
         idx = i;
         break;
        }

   if(limpar)
     {
      if(idx >= 0)
         desde[idx] = 0;
      return 0;
     }

   if(idx < 0)
     {
      idx = ArraySize(sim);
      ArrayResize(sim, idx + 1);
      ArrayResize(desde, idx + 1);
      sim[idx]   = symbol;
      desde[idx] = 0;
     }

   datetime anterior = desde[idx];

   if(anterior == 0)
      desde[idx] = TimeLocal();   // primeira falha deste simbolo

   return anterior;
  }

//==================================================
// INIT
//==================================================

bool InitADX()
{
   if(adxHandle != INVALID_HANDLE)
      IndicatorRelease(adxHandle);

   // v1.2.96 - P1.85: a cache multi-simbolo e indexada por simbolo, mas o
   // timeframe entra na criacao do handle (PERIOD_CURRENT). Numa mudanca de
   // timeframe os handles antigos responderiam com o periodo errado, logo
   // a cache e limpa em toda inicializacao.
   ADXReleaseSymbolHandles();

   adxHandle = iADX(
      _Symbol,
      PERIOD_CURRENT,
      ADXPeriod
   );

   if(adxHandle == INVALID_HANDLE)
   {
      Print(
         "[ADX] INIT ERROR | Symbol=",
         _Symbol,
         " | Error=",
         GetLastError()
      );

      return false;
   }

   ArrayResize(adxBuffer, 3);
   ArraySetAsSeries(adxBuffer, true);

   g_adxUnavailable = 0;
   g_adxValid       = 0;

   if(LogSessaoPodeImprimir("adx_init_" + _Symbol))
   Print(
      "[ADX] INIT OK | Symbol=",
      _Symbol,
      " | Period=",
      ADXPeriod
   );

   return true;
}

//==================================================
// GET CURRENT ADX
// F4/20.15 §3: retorna -1.0 (sentinel "indisponivel")
// quando o indicador nao esta pronto (INVALID_HANDLE,
// warm-up com poucos dados, CopyBuffer err 4807/4073).
// Consumidores tratam valor negativo como neutro/skip.
//==================================================

double GetADXInstance()
{
   if(adxHandle == INVALID_HANDLE)
   {
      g_adxUnavailable++;
      return -1.0;
   }

   // Warm-up: dados insuficientes para o ADX ficar estable
   if(Bars(_Symbol, PERIOD_CURRENT) < ADXPeriod * 3)
   {
      g_adxUnavailable++;
      return -1.0;
   }

   // v1.2.94 - P1.82: o handle pode existir e ainda nao ter barras
   // calculadas. BarsCalculated responde isso sem gastar CopyBuffer e sem
   // depender de adivinhar o codigo de erro.
   int calculadas = BarsCalculated(adxHandle);

   if(calculadas > 0 && calculadas < ADXPeriod * 3)   // v1.2.154 P1.115: com menos de 3x o periodo o ADX sai inflado (83.12 medido em USDCNH/USDSEK). P1.91: -1 NAO e warm-up, e impasse -> tentar CopyBuffer
   {
      g_adxUnavailable++;
      ADXLogNoRead(_Symbol, "BarsCalculated=" + IntegerToString(calculadas));

      return -1.0;
   }

   ResetLastError();

   int copied = CopyBuffer(
      adxHandle,
      0,
      0,
      1,
      adxBuffer
   );

   if(copied != 1)
   {
      int err = GetLastError();

      // 4807 = indicador aún no inicializado; 4073 = serie no encontrada
      // v1.2.94 - P1.82: qualquer outra falha tambem e AUSENCIA de leitura.
      // Antes caia em 0.0 sem imprimir nada e o ADX_OK tratava esse 0.0
      // como valor real -> veto silencioso (medido no grafico USDCHF).
      g_adxUnavailable++;
      ADXLogNoRead(_Symbol, "CopyBuffer failed | Error=" + IntegerToString(err) + " | BarsCalculated=" + IntegerToString(calculadas));

      return -1.0;
   }

   double value = adxBuffer[0];

   if(value <= 0.0)
   {
      g_adxUnavailable++;
      ADXLogNoRead(_Symbol, "ADX=" + DoubleToString(value, 2));

      return -1.0;
   }

   g_adxValid++;

   return value;
}

//==================================================
// MULTI SYMBOL
//==================================================

double GetADX(string symbol)
{
   // v1.2.150 - P1.109: sem atalho para o handle da instancia.
   if(symbol == "")
      symbol = _Symbol;

   if(!SymbolSelect(symbol, true))
   {
      Print("[ADX] SymbolSelect failed: ", symbol);
      g_adxUnavailable++;
      return -1.0;
   }
   // v1.2.152 - P1.113: sem serie provada nao ha leitura (SymbolDataReady.mqh).
   if(!XAI_SymbolDataReady(symbol))
   {
      g_adxUnavailable++;
      return -1.0;
   }

   // Warm-up: datos insuficientes para el ADX quede estable
   if(Bars(symbol, PERIOD_CURRENT) < ADXPeriod * 3)
   {
      g_adxUnavailable++;
      return -1.0;
   }

   int handle = ADXSymbolHandle(symbol);

   if(handle == INVALID_HANDLE)
   {
      Print(
         "[ADX] Handle error | ",
         symbol,
         " | Error=",
         GetLastError()
      );

      g_adxUnavailable++;
      return -1.0;
   }

   // v1.2.94 - P1.82: mesmo critério do _Symbol - sem barras calculadas
   // nao ha leitura, e sem leitura nao ha veto.
   int calculadas = BarsCalculated(handle);

   if(calculadas > 0 && calculadas < ADXPeriod * 3)   // v1.2.154 P1.115: com menos de 3x o periodo o ADX sai inflado (83.12 medido em USDCNH/USDSEK). P1.91: -1 NAO e warm-up, e impasse -> tentar CopyBuffer
   {
      g_adxUnavailable++;
      ADXLogNoRead(symbol, "BarsCalculated=" + IntegerToString(calculadas));

      // v1.2.96 - P1.85: o handle NAO e libertado. Era exactamente essa
      // libertacao que impedia o aquecimento e mantinha o ADX em -1.0
      // para sempre. O handle fica em cache e e reutilizado na volta.
      return -1.0;
   }

   double buffer[];

   ArraySetAsSeries(buffer, true);

   ResetLastError();

   int copied = CopyBuffer(
      handle,
      0,
      0,
      1,
      buffer
   );

   double result = 0.0;

   if(copied == 1)
   {
      ADXNoBarTrack(symbol, true);   // v1.2.175 - P2: aqueceu, a marca de falha cai

      result = buffer[0];

      // v1.2.152 - P1.113: o ADX nao passa de 100. Um valor acima disso e
      // leitura de outro instrumento, logo entra no caminho do 0.0 e o
      // handle sai da cache.
      if(result > 100.0)
      {
         g_adxUnavailable++;
         ADXLogNoRead(symbol, "ADX impossivel=" + DoubleToString(result, 2));
         ADXCacheDrop(symbol);
         result = -1.0;
      }
      else if(result > 0.0)
         g_adxValid++;
      else
      {
         // v1.2.94 - P1.82: 0.0 e ausencia de leitura, nao "ADX calmo".
         // Era exactamente aqui que o dono do pipeline se perdia.
         g_adxUnavailable++;
         ADXLogNoRead(symbol, "ADX=" + DoubleToString(result, 2));

         result = -1.0;
      }
   }
   else
   {
      int err = GetLastError();

      g_adxUnavailable++;
      // v1.2.175 - P2: handle que nao aquece tem prazo. Sem isto a entrada
      // ficava na cache para sempre e o simbolo nunca voltava a ter ADX.
      datetime desdeAntes = ADXNoBarTrack(symbol, false);

      if(desdeAntes > 0 && TimeLocal() >= desdeAntes + ADX_STALE_RECREATE_SEC)
        {
         ADXCacheDrop(symbol);

         if(AccountLogGatePodeImprimir("adx_handle_morto_" + symbol, 3600))
            Print("[ADX] HANDLE MORTO | ", symbol,
                  " | sem barras ha ", IntegerToString((int)(TimeLocal() - desdeAntes)), " s",
                  " | erro=", IntegerToString(err),
                  " | barsCalc=", IntegerToString(calculadas),
                  " | entrada removida da cache | grafico=", _Symbol);
        }
      else
         if(desdeAntes == 0 && AccountLogGatePodeImprimir("adx_handle_novo_" + symbol, 21600))
            Print("[ADX] HANDLE NOVO | ", symbol,
                  " | erro=", IntegerToString(err),
                  " | barsCalc=", IntegerToString(calculadas),
                  " | handle criado nesta leitura: indicador a aquecer, sem valor por agora (fail-open) | grafico=", _Symbol);

      ADXLogNoRead(symbol, "CopyBuffer failed | Error=" + IntegerToString(err) + " | BarsCalculated=" + IntegerToString(calculadas));

      result = -1.0;
   }

   // v1.2.152 - P1.113: valor indistinguivel do valor do simbolo do grafico
   // e a assinatura medida da contaminacao. A leitura e recusada e o handle
   // sai da cache para o simbolo poder sarar.
   if(symbol != _Symbol && result > 0.0)
     {
      double adxDoGrafico = GetADX(_Symbol);

      if(XAI_LeituraDeOutroSimbolo(result, adxDoGrafico))
        {
         g_adxUnavailable++;

         if(AccountLogGatePodeImprimir("adx_outro_sim_" + symbol, 3600))
            Print("[ADX] VALOR DE OUTRO SIMBOLO | ", symbol,
                  " | ADX=", DoubleToString(result, 2),
                  " | grafico=", _Symbol,
                  " | devolvido=-1.0");

         ADXCacheDrop(symbol);

         return -1.0;
        }
     }
   // v1.2.96 - P1.85: sem IndicatorRelease aqui. O handle vive no cache
   // por simbolo; libertar a cada leitura era a causa do ADX nunca aquecer.
   return result;
}

//==================================================
// FILTER
// F4/20.15 §3: ADX indisponible (negativo) -> fail-open
// (retorna true = neutro, no bloquea). Solo bloquea
// cuando hay un valor valido por debajo del minimo.
//==================================================

//==================================================
// v1.2.150 (05/11/2026) - P1.109: ADX DO SIMBOLO DO GRAFICO
//
// Pela mesma medicao do ATR (ver VolatilityFilter.mqh): o handle
// criado em OnInit devolveu o ADX de OUTRO par no reload do perfil,
// e o handle por simbolo, criado em runtime, sempre devolveu o certo.
//==================================================
double GetADX()
{
   return GetADX(_Symbol);
}



bool ADX_OK()
{
   double adx = GetADX();

   // v1.2.94 - P1.82: sem leitura NAO e "ADX fraco". O sentinel e negativo
   // (ou zero, que agora tambem vira -1.0) e o filtro fica neutro. Antes o
   // 0.0 silencioso passava por aqui e vetava por ser 0.0 < MinimumADX:
   // um dado que faltava virava uma opiniao sobre o mercado.
   if(adx <= 0.0)
      return true;

   return (adx >= MinimumADX);
}

//==================================================
// MULTI SYMBOL FILTER
//==================================================

bool ADX_OK(string symbol)
{
   if(symbol == "")
      symbol = _Symbol;

   double adx = GetADX(symbol);

   // v1.2.94 - P1.82: mesma regra do ADX_OK() de _Symbol - sem leitura
   // o filtro e neutro.
   if(adx <= 0.0)
      return true;

   return (adx >= MinimumADX);
}

//==================================================
// STRENGTH
//==================================================

double GetADXStrength(string symbol = "")
{
   double adx = GetADX(symbol);

   if(adx <= 0.0)
      return 0.0;

   if(adx >= 40.0)
      return 100.0;

   if(adx >= 30.0)
      return 80.0;

   if(adx >= 25.0)
      return 65.0;

   if(adx >= MinimumADX)
      return 50.0;

   if(adx >= MinimumADX * 0.8)
      return 30.0;

   return 0.0;
}

//==================================================
// GETTERS ADX (F4/20.15)
//==================================================

int ADXGetUnavailableCount()
{
   return g_adxUnavailable;
}

int ADXGetValidCount()
{
   return g_adxValid;
}

string ADXMetricsSummary()
{
   return StringFormat(
      "ADX | sem_leitura=%d | valid=%d",
      g_adxUnavailable,
      g_adxValid
   );
}

//==================================================
// RELEASE
//==================================================

void ReleaseADX()
{
   if(adxHandle != INVALID_HANDLE)
   {
      IndicatorRelease(adxHandle);
      adxHandle = INVALID_HANDLE;
   }

   // v1.2.96 - P1.85: libertar tambem os handles por simbolo criados
   // pelo scan multi-simbolo (cache em ADXSymbolHandle).
   ADXReleaseSymbolHandles();

   ArrayFree(adxBuffer);
}

#endif