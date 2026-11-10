// XAU_AI_PRO v1.2.9
#ifndef MARKETSCANNER_MQH
#define MARKETSCANNER_MQH

#include "../Core/Config.mqh"
#include "../Core/SignalCore.mqh"
#include "../Core/ValidationEngine.mqh"
#include "../Core/DecisionEngine.mqh"
#include "../Core/ExecutionEngine.mqh"
#include "../Core/PositionManager.mqh"
#include "../AI/AIEngine.mqh"

//==================================================
// F3 v1.2.2 - LATCH GLOBAL POR VELA
// 1 decisao por vela fechada por simbolo, independente
// do processo/instancia. Chave GlobalVariable:
// XAI_PRO_LATCH_<symbol>_<bar_time>
// (substitui o array em memoria g_tradedSignals[],
//  que era local a cada instancia do EA)
//==================================================

#define LATCH_PREFIX "XAI_PRO_LATCH_"

//==================================================
// INTERVALO MINIMO ENTRE OPERACOES DO MESMO SIMBOLO
//
// O latch "1 operacao por vela" usa a vela do grafico
// mestre (PERIOD_CURRENT). Num grafico M1 ele libera nova
// entrada no MESMO simbolo a cada minuto, mesmo quando o
// sinal vem do H1. Este intervalo nao depende do timeframe
// do grafico: vale por simbolo, por conta, e sobrevive a
// recarga porque fica em GlobalVariable.
// 0 = desligado.
//==================================================
input int MinSecondsBetweenTradesPerSymbol = 300;

#define LASTTRADE_PREFIX "XAI_PRO_LASTTRADE_"

string LastTradeKey(string symbol)
{
   return LASTTRADE_PREFIX + symbol + "_" +
      IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
}

void MarkSymbolTraded(string symbol)
{
   if(symbol=="")
      return;

   GlobalVariableSet(LastTradeKey(symbol),(double)TimeCurrent());
}

bool SymbolTradeCooldownActive(string symbol,int &restante)
{
   restante=0;

   if(MinSecondsBetweenTradesPerSymbol<=0 || symbol=="")
      return false;

   string key=LastTradeKey(symbol);

   if(!GlobalVariableCheck(key))
      return false;

   datetime last=(datetime)GlobalVariableGet(key);

   if(last<=0)
      return false;

   int passado=(int)(TimeCurrent()-last);

   if(passado<0)
      return false;   // relogio do servidor voltou: nao trava

   restante=MinSecondsBetweenTradesPerSymbol-passado;

   return(restante>0);
}

string LatchKey(string symbol, datetime barTime)
{
   return LATCH_PREFIX + symbol + "_" + IntegerToString((long)barTime);
}

bool AlreadyTradedThisBar(string symbol, datetime barTime)
{
   if(barTime <= 0)
      return false;
   return GlobalVariableCheck(LatchKey(symbol, barTime));
}

void MarkTradedBar(string symbol, datetime barTime)
{
   if(barTime <= 0)
      return;
   GlobalVariableSet(LatchKey(symbol, barTime), (double)barTime);

   // Cleanup: remove chaves antigas do MESMO simbolo (evita acumulo)
   string prefix = LATCH_PREFIX + symbol + "_";
   string current = LatchKey(symbol, barTime);
   for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
   {
      string name = GlobalVariableName(i);
      if(StringFind(name, prefix, 0) == 0 && name != current)
         GlobalVariableDel(name);
   }
}

//==================================================
// v1.2.39 (30/10/2026) - P1.3 rodada 6: AGREGACAO DO SCANNER
//
// MEDIDO em 30/10 (v1.2.32): [SCANNER] = 15 348 linhas no journal do dia, das
// quais 15 108 num UNICO grafico - o mestre que varre os 11 simbolos de
// Symbols. O piso do desenho era grande demais: cada gate que barrava um
// simbolo reimprimia a mesma linha 1x/minuto, por simbolo.
//
// A partir daqui o scanner NAO imprime por simbolo: acumula o motivo e emite
// UMA linha de resumo por minuto e por instancia. O detalhe por simbolo
// continua disponivel com EnableVerboseDebug=true (fora do Strategy Tester).
// Se nada acontecer, o resumo sai no maximo 1x/15 min - so para provar que o
// pipeline esta vivo.
//==================================================

#define SCAN_BUCKETS      8
#define SCAN_SILENT_SEC   900

enum ENUM_SCAN_BUCKET
  {
   SCAN_CANOPEN = 0,
   SCAN_JA_NEGOCIADO,
   SCAN_COOLDOWN,
   SCAN_STALE,        // v1.2.94 - P1.82: preco morto (feed parado)
   SCAN_NO_SIGNAL,
   SCAN_DIR_HIST,
   SCAN_ALLOW_TRADE,
   SCAN_EXEC_FAIL
  };

string   g_scanNome[SCAN_BUCKETS] = {"CanOpen","JaNegociado","Cooldown","Stale","NoSignal","DirHist","AllowTrade","ExecFail"};
int      g_scanQtd[SCAN_BUCKETS];
int      g_scanSimbolos  = 0;
int      g_scanSinais    = 0;
int      g_scanTrades    = 0;
datetime g_scanJanela    = 0;
datetime g_scanSilencio  = 0;

//==================================================
// v1.2.94 (02/11/2026) - P1.82: PROVA NO RESUMO
// Ultimo valor publicado de cada contador, para o resumo mostrar o
// DELTA da janela (e nao um acumulado que so cresce e nao diz nada).
//==================================================
int      g_scanAdxUPub      = 0;
int      g_scanAdxVPub      = 0;
int      g_scanSigNoReadPub = 0;
int      g_scanSigNeutroPub = 0;

void ScanBlock(ENUM_SCAN_BUCKET bucket, string symbol, string detalhe="")
{
   int i = (int)bucket;

   if(i >= 0 && i < SCAN_BUCKETS)
      g_scanQtd[i]++;

   if(!EnableVerboseDebug || MQLInfoInteger(MQL_TESTER))
      return;

   // v1.2.81 (02/11/2026) - P1.68: medido 18 532 linhas [SCANNER] BLOCK no
   // Logs de 02/11 (13,4 por cento do journal do dia), sempre o MESMO
   // desfecho pelo mesmo simbolo a cada ciclo. O [SCANNER] RESUMO ja
   // publica a contagem por balde a cada minuto, logo o detalhe so precisa
   // de sair quando o desfecho daquele simbolo MUDA, com heartbeat de 30 min.
   const int SCAN_MEMO = 64;
   static string   memoSim[64];
   static int      memoBalde[64];
   static datetime memoHora[64];
   static int      memoN = 0;

   datetime agoraScan = TimeLocal();
   int pos = -1;
   for(int k = 0; k < memoN; k++)
      if(memoSim[k] == symbol)
        {
         pos = k;
         break;
        }
   if(pos < 0)
     {
      if(memoN < SCAN_MEMO)
        {
         pos = memoN;
         memoN++;
        }
      else
         pos = 0;
      memoSim[pos]   = symbol;
      memoBalde[pos] = -1;
      memoHora[pos]  = 0;
     }

   // P2.07: MEDIDO em 03/11 na janela estavel 08:09:37 a 08:41:06 com a
   // v1.2.118: [SCANNER] 25 linhas em 31 min era a familia mais cara, e as
   // rajadas vinham TODAS do heartbeat de 30 min - 6 a 8 simbolos com o
   // MESMO desfecho normal escreviam em fila no mesmo ciclo (08:39:44).
   // O [SCANNER] RESUMO ja publica a contagem por balde em cada janela,
   // logo o heartbeat por simbolo nao acrescenta nada aos baldes NORMAIS:
   // estes passam a sair apenas quando o desfecho MUDA. So os baldes de
   // excecao (AllowTrade, ExecFail) mantem heartbeat, porque um deles parado
   // ha meia hora e informacao: o EA podia estar a tentar entrar.
   bool bucketNormal = (bucket == SCAN_CANOPEN || bucket == SCAN_JA_NEGOCIADO ||
                        bucket == SCAN_COOLDOWN || bucket == SCAN_STALE ||
                        bucket == SCAN_NO_SIGNAL || bucket == SCAN_DIR_HIST);

   bool desfechoMudou = (memoBalde[pos] != i);
   bool heartbeatScan = (!bucketNormal && (memoHora[pos] == 0 || (agoraScan - memoHora[pos]) >= 1800));

   if(!desfechoMudou && !heartbeatScan)
      return;

   // v1.2.95 (02/11/2026) - P1.83: o memo acima e POR INSTANCIA, e existem
   // 16 graficos. MEDIDO no journal de 02/11: 18 577 linhas [SCANNER] BLOCK
   // (9,9% do dia) porque cada grafico republicava o desfecho do MESMO
   // simbolo. A janela passa a ser por CONTA: o mesmo (simbolo, balde) sai
   // no maximo 1x/30 min no total. O [SCANNER] RESUMO continua a publicar
   // a contagem por balde, logo nenhuma informacao de decisao se perde.
   if(i >= 0 && i < SCAN_BUCKETS)
      if(!AccountLogGatePodeImprimir("scanblock_" + symbol + "_" + g_scanNome[i], 1800))
         return;

   // P2.07: o memo so avanca DEPOIS do portao. Antes avancava primeiro, logo
   // uma mudanca de desfecho abafada pela janela de 30 min nunca mais era
   // tentada e o simbolo ficava invisivel ate o estado voltar a mudar.
   memoBalde[pos] = i;
   memoHora[pos]  = agoraScan;

   Print("[SCANNER] BLOCK | ", (i >= 0 && i < SCAN_BUCKETS ? g_scanNome[i] : "?"),
         " | ", symbol, detalhe);
}

// P1.106 (04/11/2026): o delta ADX/SIG podia sair NEGATIVO quando o modulo de
// indicadores recriava os contadores no reattach (Handle/CopyBuffer) enquanto
// o baseline publicado pelo scanner sobrevivia. MEDIDO no journal as
// 18:13:56: "[SCANNER] RESUMO ... ADX(sem/ok)=-2951/-29135". Um delta negativo
// nao tem leitura possivel; passa a 0. O baseline e reescrito logo abaixo com
// o valor atual, logo so a linha daquela janela era afetada.
int MaxInt0(int v)
{
   return(v < 0 ? 0 : v);
}

void ScanFlush(datetime now)
{
   if(g_scanSimbolos <= 0)
     {
      g_scanJanela = now;
      return;
     }

   int    totalBloqueios = 0;
   string partes         = "";

   for(int i = 0; i < SCAN_BUCKETS; i++)
     {
      totalBloqueios += g_scanQtd[i];

      if(g_scanQtd[i] > 0)
         partes += (partes == "" ? "" : " ") + g_scanNome[i] + "=" + IntegerToString(g_scanQtd[i]);
     }

   // v1.2.102 (P1.90): bloqueio por simbolo e o estado NORMAL de um ciclo sem
   // sinal (a lista Symbols tem 11 simbolos e o mercado nao da 11 entradas por
   // minuto). Antes, "bloqueios > 0" desligava o silencio e o RESUMO saia a
   // cada ciclo (~60 s) em 15 graficos. Agora o ciclo so e ruidoso quando ha
   // sinal ou trade; caso contrario fala de SCAN_SILENT_SEC em SCAN_SILENT_SEC.
   // P2.06: fecha o retrato [CENARIO] do ciclo (uma linha em vez de 11).
   ScenarioSnapFlush();

   bool silencioso = (g_scanSinais == 0 && g_scanTrades == 0);

   //--------------------------------------------------
   // v1.2.94 - P1.82: sem leitura de ADX e sem leitura de sinal sao os
   // dois modos de falha que estavam invisiveis. Passam a sair aqui, em
   // delta da janela, num unico bloco curto.
   //--------------------------------------------------
   int adxU = ADXGetUnavailableCount();
   int adxV = ADXGetValidCount();
   int sigN = SignalNoReadCount();
   int sigR = SignalNeutralCount();

   string prova = " | ADX(sem/ok)=" + IntegerToString(MaxInt0(adxU - g_scanAdxUPub)) + "/" + IntegerToString(MaxInt0(adxV - g_scanAdxVPub)) +
                  " | SIG(sem/neutro)=" + IntegerToString(MaxInt0(sigN - g_scanSigNoReadPub)) + "/" + IntegerToString(MaxInt0(sigR - g_scanSigNeutroPub));

   // P2.01 (03/11/2026): com sinal ou trade o RESUMO saia a CADA ciclo - o
   // USDCNH escreveu 4 linhas em 4 minutos (~60/hora) e o retrato era o do
   // ciclo anterior. Passa a exigir tambem a janela por CONTA de
   // SCAN_SILENT_SEC, logo no maximo 1 linha/15 min por conta em vez de uma
   // por instancia e por ciclo. O caminho silencioso mantem-se igual.
   bool falarAgora = (!silencioso || g_scanSilencio == 0 || (now - g_scanSilencio) >= SCAN_SILENT_SEC);

   // P1.2336: publica a janela inteira ou nao publica nada; o relogio do
   // ciclo (g_scanJanela) continua a avancar em todos os ciclos, porque e
   // ele que marca os 60 s entre varreduras.
   bool publicouResumo = false;

   if(falarAgora && AccountLogGatePodeImprimir("scan_resumo", SCAN_SILENT_SEC))
     {
      Print("[SCANNER] RESUMO | visitas=", g_scanSimbolos,
            " | sinais=", g_scanSinais,
            " | trades=", g_scanTrades,
            " | bloqueios=", totalBloqueios,
            (partes == "" ? "" : " | " + partes),
            prova);

      publicouResumo = true;

      g_scanSilencio = now;

      // P2.01: os contadores publicados so avancam quando a linha sai, para o
      // delta (ADX sem/ok, SIG sem/neutro) continuar a ser o do intervalo que
      // foi realmente impresso e nao o de um ciclo suprimido.
      g_scanAdxUPub      = adxU;
      g_scanAdxVPub      = adxV;
      g_scanSigNoReadPub = sigN;
      g_scanSigNeutroPub = sigR;
     }

   //--------------------------------------------------
   // v1.2.188 (08/11/2026) - P1.2336
   // A JANELA PUBLICADA TEM DE SER A JANELA CONTADA.
   // Antes estes contadores eram zerados em TODOS os ciclos (~60 s), mas a
   // linha so saia quando o portao por conta a deixava passar (15 min).
   // Resultado medido pelo DELTA: 7 429 janelas com trades=0 enquanto o dia
   // tinha 34 deals reais - publicava-se o ultimo ciclo, nao o intervalo
   // anunciado na propria linha. Passam a ser zerados APENAS quando a linha
   // sai. So contadores de journal: nada aqui decide entrada, saida, lote,
   // alvo, stop, spread, preco ou parametro de risco.
   //--------------------------------------------------
   if(publicouResumo)
     {
      for(int i = 0; i < SCAN_BUCKETS; i++)
      g_scanQtd[i] = 0;

   g_scanSimbolos = 0;
   g_scanSinais   = 0;
      g_scanTrades   = 0;
     }
   g_scanJanela   = now;
}

//==================================================
// v1.2.94 (02/11/2026) - P1.82: FRESCURA DE DADOS POR SIMBOLO
//
// MEDIDO no journal de 02/11: o USDBRL tinha o feed parado desde 30/10
// 20:00 e ainda assim gerou 1 771 dos 1 839 sinais do dia - 96,3 por
// cento de todo o ruido do pipeline. O RSI[1]=37.31 era literalmente o
// mesmo numero as 05:05, 05:31, 20:13, 20:56 e 20:57. Um preco que nao
// se mexeu nao e um setup: e um dado morto, e nenhuma dessas leituras
// podia virar operacao.
//
// A verja olha o ultimo TICK (o preco vivo) e nao a barra: uma barra H1
// pode abrir normalmente com uma sessao inteira sem cotacao.
//==================================================
bool SymbolDataFresh(string symbol, string &motivo)
{
   motivo = "";

   if(!EnableStaleDataGuard)
      return true;

   if(symbol == "")
     {
      motivo = "simbolo vazio";
      return false;
     }

   if(!SymbolSelect(symbol, true))
     {
      motivo = "fora do Market Watch";
      return false;
     }

   datetime barra0 = iTime(symbol, PERIOD_CURRENT, 0);

   if(barra0 <= 0)
     {
      motivo = "sem historico";
      return false;
     }

   MqlTick cotacao;

   if(!SymbolInfoTick(symbol, cotacao) || cotacao.time <= 0)
     {
      motivo = "sem tick";
      return false;
     }

   // v1.2.179 (07/11/2026) - D-029/D-064: o relogio de referencia passa a ser o
   // do SERVIDOR (mesma escala de MqlTick.time), com TimeCurrent() so como
   // recurso final. TimeCurrent() congela sem ticks: ao fim de semana ficava
   // parado no carimbo do ultimo tick e dava idade ~0, ou seja "cotacao fresca"
   // exactamente no freeze que esta verja existe para apanhar. O limite NAO
   // muda: continua a ser MaxSymbolTickAgeSec.
   datetime agoraStale = TimeTradeServer();

   if(agoraStale <= 0)
      agoraStale = TimeCurrent();

   int idade = (int)((long)agoraStale - (long)cotacao.time);

   if(idade < 0)
      idade = 0;   // carimbo no futuro: feed adiantado, nao e motivo de veto

   if(MaxSymbolTickAgeSec > 0 && idade > MaxSymbolTickAgeSec)
     {
      motivo = "preco morto | ultimo tick ha " + IntegerToString(idade) + "s";
      return false;
     }

   return true;
}

//==================================================
// DIAGNOSTICO DE MERCADO EM SO LEITURA (P1.83 / v1.2.95)
//==================================================
// MEDIDO em 02/11/2026 21:50:33: o grafico dono do pipeline foi recarregado
// (template XAI_P182_OWNER) e voltou com MQL_TRADE_ALLOWED=0. O OnTick desse
// grafico - e o de todas as instancias - sai no portao de negociacao ANTES do
// pipeline, por isso o journal ficou 5 minutos em silencio absoluto: zero
// [SCANNER], zero [CENARIO], zero [SIGNAL], zero [ADX]. Sem visibilidade a
// unica leitura possivel era "o EA nao opera", e as provas novas da v1.2.94
// (SCAN_STALE, ADX sem leitura, sinal neutro) nunca chegavam a correr.
// Esta rotina e o scan minimo, SO DE LEITURA: mede frescura do tick, ADX e
// sinal de cada simbolo e publica UMA linha por 5 minutos por conta. Nao
// chama CanOpenPosition, nao chama ExecuteTrade, nao grava latch, nao mexe em
// cooldown, nao toca em risco, SL, TP nem lote. Nao decide nada.
void ReadOnlyScanTick(int portaoCodigo)
{
   datetime agora = TimeLocal();

   string chave = "XAI_PRO_DIAGSCAN_" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));

   if(GlobalVariableCheck(chave))
     {
      datetime marca = (datetime)GlobalVariableGet(chave);

      if(marca > 0 && (agora - marca) < 300)
         return;
     }

   GlobalVariableSet(chave, (double)agora);

   int    total      = TotalSymbols();
   int    frescos    = 0;
   int    stale      = 0;
   int    adxOk      = 0;
   int    adxSem     = 0;
   int    comprados  = 0;
   int    vendidos   = 0;
   int    neutros    = 0;
   int    semLeitura = 0;
   string staleTxt   = "";
   string sinalTxt   = "";

   for(int i = 0; i < total; i++)
     {
      string sym = GetTradeSymbol(i);

      if(sym == "")
         continue;

      string motivo = "";

      if(!SymbolDataFresh(sym, motivo))
        {
         stale++;

         if(StringLen(staleTxt) < 90)
           {
            string curto = motivo;

            StringReplace(curto, " | ", " ");

            if(StringLen(curto) > 32)
               curto = StringSubstr(curto, 0, 32);

            staleTxt += (staleTxt == "" ? "" : ", ") + sym + "(" + curto + ")";
           }

         continue;
        }

      frescos++;

      double adx = GetADX(sym);

      if(adx <= 0.0)
         adxSem++;
      else
         adxOk++;

      int antes = SignalNoReadCount();
      int sig   = GetSignal(sym);

      if(sig == 0)
        {
         if(SignalNoReadCount() > antes)
            semLeitura++;
         else
            neutros++;
        }
      else
        {
         if(sig > 0)
            comprados++;
         else
            vendidos++;

         if(StringLen(sinalTxt) < 90)
            sinalTxt += (sinalTxt == "" ? "" : ", ") + sym + (sig > 0 ? " BUY" : " SELL");
        }
     }

   Print("[DIAGSCAN] portao do grafico=FECHADO | codigo=", IntegerToString(portaoCodigo), " | suite=", (CTradeGate::EvaluateSuite() == TG_OK ? "ABERTA" : "FECHADA"),
         " | simbolos=", IntegerToString(total),
         " | frescos=", IntegerToString(frescos),
         " | stale=", IntegerToString(stale), (staleTxt == "" ? "" : " [" + staleTxt + "]"),
         " | ADX(ok/sem)=", IntegerToString(adxOk), "/", IntegerToString(adxSem),
         " | sinais=", IntegerToString(comprados + vendidos), (sinalTxt == "" ? "" : " [" + sinalTxt + "]"),
         " | neutros=", IntegerToString(neutros),
         " | sem_leitura=", IntegerToString(semLeitura),
         " | modo=SO LEITURA nesta instancia (o grafico dono e que envia)");
}

//==================================================
// PROCESS SYMBOL
//==================================================

void ProcessSymbol(string symbol)
{
   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   // v1.2.10: throttle POR SIMBOLO. O static unico era compartilhado por
   // todos os simbolos, entao apenas UM logava por minuto e os outros 10
   // ficavam invisiveis - foi o que mascarou o conflito IA x tecnico em 29/10.
   static string   scanLogSymbols[];
   static datetime scanLogTimes[];
   static datetime scanInfoTimes[];   // v1.2.27: cache de 1 hora para linhas de progresso

   datetime now = TimeCurrent();

   // v1.2.39 - P1.3 rodada 6: fecha a janela de 60 s do resumo do scanner ANTES
   // de contar o simbolo atual, para o resumo sair 1x/minuto por instancia.
   if(g_scanJanela == 0)
      g_scanJanela = now;
   else
     {
      if((now - g_scanJanela) >= 60)
         ScanFlush(now);
     }

   g_scanSimbolos++;

   int scanIdx = -1;

   for(int si = 0; si < ArraySize(scanLogSymbols); si++)
     {
      if(scanLogSymbols[si] == symbol)
        {
         scanIdx = si;
         break;
        }
     }

   if(scanIdx < 0)
     {
      scanIdx = ArraySize(scanLogSymbols);
      ArrayResize(scanLogSymbols, scanIdx + 1);
      ArrayResize(scanLogTimes, scanIdx + 1);
      ArrayResize(scanInfoTimes, scanIdx + 1);
      scanLogSymbols[scanIdx] = symbol;
      scanLogTimes[scanIdx] = 0;
      scanInfoTimes[scanIdx] = 0;
     }

   bool logOnce = (now - scanLogTimes[scanIdx] >= 60);

   if(logOnce)
      scanLogTimes[scanIdx] = now;

   // v1.2.27 (30/10/2026) - P1.3: START e POSITION CHECK OK sao progresso puro
   // (2 linhas por simbolo por ciclo; com 11 simbolos passa de 1300 linhas por
   // hora). Passam a 1x/hora por simbolo. Os BLOCK continuam 1x/minuto.
   bool logInfo = (now - scanInfoTimes[scanIdx] >= 3600);

   if(logInfo)
      scanInfoTimes[scanIdx] = now;

   if(symbol=="")
   {
      if(logOnce)
         Print(
            "[SCANNER] BLOCK | Empty symbol"
         );

      return;
   }


   // P2.00: 11 simbolos por ciclo a dizer "START" nao acrescenta nada ao
   // [CENARIO]/[SIGNAL]/[SCANNER] BLOCK; passa a 1x/h por CONTA e simbolo.
   if(logInfo && AccountLogGatePodeImprimir("scan_start_" + symbol, 3600))
      Print(
         "[SCANNER] START | ",
         symbol
      );


   //================================================
   // POSITION LIMIT
   //================================================

   if(!CanOpenPosition(symbol))
   {
      ScanBlock(SCAN_CANOPEN, symbol);

      return;
   }


   //================================================
   // LATCH v1.2.0/F3 - 1 operacao por vela fechada
   //================================================

   datetime signalBar = iTime(symbol, PERIOD_CURRENT, 1);

   if(signalBar > 0 && AlreadyTradedThisBar(symbol, signalBar))
   {
      ScanBlock(SCAN_JA_NEGOCIADO, symbol);

      return;
   }

   // P2.00: a linha "POSITION CHECK OK" dizia apenas que o simbolo ainda nao
   // tinha sido bloqueado. O desfecho real ja sai com o simbolo e o motivo em
   // [SCANNER] BLOCK / [CENARIO] / [SIGNAL]; a linha foi removida.


   //================================================
   // v1.2.94 - P1.82: FRESCURA DO PRECO
   // Antes do latch, do cenario e do sinal: se o preco esta morto, nao
   // ha o que classificar nem o que ler. Tambem poupa a criacao de um
   // handle de ADX por chamada para um feed que nao cotou nada.
   //================================================

   string staleWhy = "";

   if(!SymbolDataFresh(symbol, staleWhy))
   {
      ScanBlock(SCAN_STALE, symbol, " | " + staleWhy);

      return;
   }


   //================================================
   // CENARIO GLOBAL (v1.2.21): diz, uma vez por minuto por simbolo, em que
   // tipo de mercado o EA esta operando (ADX, ATR%, tendencia) e o que ele
   // decidiu fazer a respeito (fator de lote e de alvo). Somente leitura.
   ScenarioLog(symbol);
   GlobalScenarioLog(symbol);   // v1.2.22: classe de ativo + sessao GMT + exposicao por moeda

   //================================================
   int cooldownRestante=0;

   if(SymbolTradeCooldownActive(symbol,cooldownRestante))
   {
      ScanBlock(SCAN_COOLDOWN, symbol, " | faltam=" + IntegerToString(cooldownRestante) + "s");

      return;
   }

   // SIGNAL
   //================================================

   int signal=
      GetCombinedSignal(
         symbol
      );


   if(signal==0)
   {
      // v1.2.33 (30/10/2026) - P1.3 rodada 5: "No Signal" e o desfecho NORMAL de
      // um simbolo sem setup; saia 1x/minuto por simbolo. Medido em 17:30-17:35
      // da v1.2.32: 5 linhas por simbolo em 5 min = ~660/hora so deste caso.
      // Passa a 1x/hora por simbolo (logInfo), junto com o SCANNER START. Os
      // outros BLOCK (CanOpenPosition, AllowTrade, direcao bloqueada, intervalo
      // minimo, Execution Failed) continuam 1x/minuto: esses sim sao excecao.
      ScanBlock(SCAN_NO_SIGNAL, symbol);

      return;
   }


   g_scanSinais++;

   // v1.2.92 (02/11/2026) - P1.79: MEDIDO no journal de 02/11 as 20:16 - o
   // MESMO simbolo com o MESMO sinal imprimia a cada ciclo (USDBRL Signal=1
   // de 6 em 6 segundos, 116 linhas numa janela de 4 000). Passa a sair
   // quando o sinal MUDA e, no maximo, 1x/30 min por simbolo como prova de
   // vida. Nenhum limite, decisao ou return foi tocado: muda so a impressao.
   if(EnableVerboseDebug && !MQLInfoInteger(MQL_TESTER) &&
      DiagGateAllow(symbol, "SCAN_SIGNAL", "S" + IntegerToString(signal), 1800))
      Print("[SCANNER] SIGNAL OK | ", symbol, " | Signal=", signal);


   //================================================
   // v1.4.0 (Etapa 4): sinal gerado
   // Direcao historicamente ruim (opcional, ver LearningHistory):
   // o boost do aprendizado nunca reduz o score por padrao, mas aqui a
   // entrada pode ser barrada de verdade nessa direcao.
   if(LearningDirectionBlocked(symbol,signal))
   {
      ScanBlock(SCAN_DIR_HIST, symbol, " | Signal=" + IntegerToString(signal) + " |" + DirSummary(symbol));

      return;
   }

   StateSet(symbol, STATE_SIGNAL_GENERATED);

   // VALIDATION + SCORE/DECISION + VETO IA (ETAPA 14)
   // AllowTrade() engloba ValidateTrade() + CalculateMarketScore()
   // (score minimo) + FinalAIAllow() (veto avancado da IA).
   // Fix ETAPA 14: antes o caminho critico chamava apenas
   // ValidateTrade(), deixando MarketScore sempre 0.0 e o
   // filtro de score/veto IA fora do fluxo real de execucao.
   //================================================

   // v1.2.20 (29/10/2026): motiva o veto. Antes o log dizia apenas
   // "AllowTrade (Validation/Score/IA)" e nao revelava QUAL gate barrou.
   // Agora sai o motivo exato: VALIDATION: <checagem>, NEWS: <motivo>,
   // SCORE <medido> < MinMarketScore ou ADV AI. Apenas diagnostico.
   string allowWhy="";

   if(
      !AllowTradeEx(
         signal,
         symbol,
         allowWhy
      )
   )
   {
      ScanBlock(SCAN_ALLOW_TRADE, symbol, " | Signal=" + IntegerToString(signal) + " | Motivo=" + allowWhy);

      return;
   }


   // v1.2.97 (03/11/2026) - P1.86: MEDIDO no journal de 02/11 as 23:20-23:24
   // (v1.2.93): o MESMO simbolo aprovado reimprimia esta linha a cada ciclo
   // de 6 s (XAUUSD sozinho: ~10 linhas/min, texto identico). Passa a sair
   // 1x/30 min por simbolo como prova de vida; nenhuma decisao muda.
   if(EnableVerboseDebug && !MQLInfoInteger(MQL_TESTER) &&
      DiagGateAllow(symbol, "SCAN_APPROVED", "OK", 1800))
      Print("[SCANNER] VALIDATION+SCORE OK | ", symbol);


   //================================================
   // v1.4.0 (Etapa 4): validacao aprovada
   StateSet(symbol, STATE_VALIDATING);

   // EXECUTION
   //================================================

   if(
      !ExecuteTrade(
         symbol,
         signal
      )
   )
   {
      ScanBlock(SCAN_EXEC_FAIL, symbol, " | Signal=" + IntegerToString(signal));

      return;
   }


   // v1.2.0/F3 - marca a vela como negociada (evita reentrada)
   if(signalBar > 0)
      MarkTradedBar(symbol, signalBar);

   // trava por TEMPO, independente do timeframe do grafico mestre
   MarkSymbolTraded(symbol);

   g_scanTrades++;

   Print("[SCANNER] TRADE SUCCESS | ", symbol, " | Signal=", signal);
}

#endif
