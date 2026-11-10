// XAU_AI_PRO v1.2.9
#ifndef DECISIONENGINE_MQH
#define DECISIONENGINE_MQH

#include "../Core/Config.mqh"
#include "../Core/SignalCore.mqh"
#include "../Core/ValidationEngine.mqh"
#include "../Filters/GlobalScenario.mqh"   // v1.2.22: correlacao de moeda + sessao GMT
#include "../Filters/MarketIntelligence.mqh" // v1.3: inteligencia de mercado (sessoes, calendario, fechamento, score)

#include "../Indicators/RSI.mqh"
#include "../Indicators/ADX.mqh"

#include <KCI\\KCI_Volatility_Distance.mqh>
#include <KCI\\KCI_Directional_Matrix.mqh>

#include "../AI/AIEngine.mqh"

// v1.2.10: memoria de aprendizado persistente (historico real)
#include "../AI/LearningHistory.mqh"

//==================================================
// DECISION ENGINE
// MULTI SYMBOL
//==================================================

double MarketScore=0.0;

//==================================================
// v1.2.97 (03/11/2026) - P1.86: PORTA DE THROTTLE LOCAL
//
// Motivo medido (journal de 02/11, 23:20-23:24, v1.2.93): as linhas
// "[WARMUP]" e "SCORE CALCULATED" saiam 1x/min por simbolo e "SCORE
// CALCULATED" saia SEM TAG. Com o ADX em "sem leitura" o aviso de warm-up
// nunca parava, porque nunca ficava pronto. Esta porta abafa por
// (simbolo + tag) sem mexer em decisao, score, filtro ou ordem.
//
// Implementacao local de proposito: DecisionEngine.mqh e incluido antes do
// Monitoring/DiagGate.mqh no MarketScanner, por isso nao depende da ordem
// dos #include.
//==================================================

#define DECLOG_MAX 64

string   g_decLogKey[DECLOG_MAX];
datetime g_decLogAt[DECLOG_MAX];
int      g_decLogCount = 0;

bool DecisionLogDue(const string symbol, const string tag, const int seconds)
{
   const string key = symbol + "|" + tag;
   datetime     now = (datetime)TimeLocal();

   for(int i = 0; i < g_decLogCount; i++)
   {
      if(g_decLogKey[i] != key)
         continue;

      if(seconds > 0 && (now - g_decLogAt[i]) < seconds)
         return false;

      g_decLogAt[i] = now;
      return true;
   }

   if(g_decLogCount >= DECLOG_MAX)
      return true;

   g_decLogKey[g_decLogCount] = key;
   g_decLogAt[g_decLogCount]  = now;
   g_decLogCount++;

   return true;
}

//==================================================
// NOTA POR SIMBOLO
//==================================================
// O `MarketScore` global guarda apenas o ULTIMO simbolo avaliado. Com 11
// simbolos no pipeline, o `OnTradeTransaction` registrava no forward log o
// score de outro ativo — dois lados do mesmo dado discordando (AGENTS.md §5).
// Aqui a nota passa a ter dono: o simbolo que a gerou.
string g_msSymbols[];
double g_msValues[];

void SetMarketScore(string symbol, double score)
{
   if(symbol == "")
      return;

   for(int i = 0; i < ArraySize(g_msSymbols); i++)
   {
      if(g_msSymbols[i] == symbol)
      {
         g_msValues[i] = score;
         return;
      }
   }

   int n = ArraySize(g_msSymbols);
   ArrayResize(g_msSymbols, n + 1);
   ArrayResize(g_msValues, n + 1);
   g_msSymbols[n] = symbol;
   g_msValues[n] = score;
}

double GetMarketScoreFor(string symbol)
{
   for(int i = 0; i < ArraySize(g_msSymbols); i++)
   {
      if(g_msSymbols[i] == symbol)
         return(g_msValues[i]);
   }

   return(0.0);
}


//==================================================
// MARKET SCORE
//==================================================

//==================================================
// v1.2.28 (30/10/2026) - P1.5: WARM-UP DOS INDICADORES
//
// O que a medicao mostrou: `GetRSI()` devolve 0.0 e `GetADX()` devolve
// -1.0 enquanto a serie esta a aquecer (Indicators/RSI.mqh e
// Indicators/ADX.mqh). Esses valores NAO sao medidas: sao ausencia de
// medida.
//
// Nenhum deles dava bonus por engano: em `CalculateMarketScore` as
// condicoes `rsi>30` e `adx>=MinimumADX` sao falsas com 0.0 e -1.0, e no
// `GetAIConfidence` (AI/AIEngine.mqh) acontece o mesmo. Ou seja: o score
// ja era fail-closed. O que faltava era o CONTRARIO de um numero novo -
// faltava o journal dizer que aqueles 0,00 eram "sem leitura" e nao
// "leitura fraca". Sem isso, um score de 85 com RSI e ADX a zero
// confundia-se com um mercado neutro medido.
//
// Esta funcao responde a pergunta que faltava e serve de base para o
// gate de warm-up que as proximas versoes podem querer impor.
//==================================================

bool IndicatorsReady(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   // Folga do maior periodo em uso no score (EMA lenta 200, ADX 14 x3,
   // RSI 14 x3). Abaixo disto o ADX ainda entrega 0.0 e o RSI 0.0.
   int minimo = (int)MathMax(SlowEMA, (double)(ADXPeriod * 3));
   minimo = (int)MathMax((double)minimo, (double)(RSIPeriod * 3));

   if(Bars(symbol, PERIOD_CURRENT) < minimo)
      return false;

   if(GetRSI(symbol) <= 0.0)
      return false;

   if(GetADX(symbol) <= 0.0)
      return false;

   return true;
}

double CalculateMarketScore(
   int signal,
   string symbol=""
)
{
   if(signal==0)
      return 0.0;


   if(symbol=="")
      symbol=_Symbol;


   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastLogTime = 0;
   datetime logNow = TimeCurrent();
   bool logOnce = (logNow - lastLogTime >= 60);

   // v1.2.28 (30/10/2026) - P1.5: marca se as leituras existem. Nao altera
   // nenhuma parcela do score (as condicoes de RSI/ADX ja falhavam com 0.0
   // e -1.0); serve para o journal distinguir "sem leitura" de "leitura
   // fraca" e para a proxima versao poder impor um gate de warm-up.
   bool indicadoresProntos = IndicatorsReady(symbol);

   if(logOnce && !indicadoresProntos && DecisionLogDue(symbol, "WARMUP", 3600))
     {
      PrintFormat("[WARMUP] %s | RSI=%.2f | ADX=%.2f | barras=%d | score SEM bonus de RSI/ADX",
                  symbol, GetRSI(symbol), GetADX(symbol), Bars(symbol, PERIOD_CURRENT));
     }
   if(logOnce)
      lastLogTime = logNow;


   //================================================
   // BASE SCORE
   //================================================

   // v1.2.184 (P1.138) - G3: sem base arbitraria. Base 50 + EMA 20 + RSI 15 +
   // ADX 15 = 100.00 antes da IA e do KCI, logo MinMarketScore=65.0 nunca
   // filtrava nada (162/162 amostras em TOTAL=100.00). Ver normalizacao no fim.
   double score=0.0;


   //================================================
   // EMA TREND STRENGTH
   //================================================

   int emaFastHandle=
      iMA(
         symbol,
         PERIOD_CURRENT,
         FastEMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );


   int emaSlowHandle=
      iMA(
         symbol,
         PERIOD_CURRENT,
         SlowEMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );


   double emaStrength=0.0;


   if(
      emaFastHandle!=INVALID_HANDLE &&
      emaSlowHandle!=INVALID_HANDLE
   )
   {
      double fastBuf[];
      double slowBuf[];


      ArrayResize(
         fastBuf,
         3
      );


      ArrayResize(
         slowBuf,
         3
      );


      ArraySetAsSeries(
         fastBuf,
         true
      );


      ArraySetAsSeries(
         slowBuf,
         true
      );


      int fastCopied=
         CopyBuffer(
            emaFastHandle,
            0,
            0,
            3,
            fastBuf
         );


      int slowCopied=
         CopyBuffer(
            emaSlowHandle,
            0,
            0,
            3,
            slowBuf
         );


      if(
         fastCopied>0 &&
         slowCopied>0
      )
      {
         if(
            signal==1 &&
            fastBuf[0]>slowBuf[0]
         )
         {
            emaStrength=20.0;
         }
         else
         if(
            signal==-1 &&
            fastBuf[0]<slowBuf[0]
         )
         {
            emaStrength=20.0;
         }


         score+=emaStrength;
      }
   }


   //================================================
   // RELEASE EMA HANDLES
   //================================================

   if(
      emaFastHandle!=INVALID_HANDLE
   )
   {
      IndicatorRelease(
         emaFastHandle
      );
   }


       emaFastHandle=INVALID_HANDLE;  // v1.2.1-crashfix: invalidate after release
   if(
      emaSlowHandle!=INVALID_HANDLE
   )
   {
      IndicatorRelease(
         emaSlowHandle
      );
   }


       emaSlowHandle=INVALID_HANDLE;  // v1.2.1-crashfix: invalidate after release
   //================================================
   // RSI QUALITY
   //================================================

   double rsi=
      GetRSI(
         symbol
      );


   double rsiQuality=0.0;


   if(
      rsi>30.0 &&
      rsi<70.0
   )
   {
      rsiQuality=15.0;
   }
   else
   if(
      rsi>20.0 &&
      rsi<80.0
   )
   {
      rsiQuality=10.0;
   }


   score+=rsiQuality;


   //================================================
   // ADX QUALITY
   //================================================

   double adx=
      GetADX(
         symbol
      );


   double adxQuality=0.0;


   if(
      adx>=MinimumADX
   )
   {
      adxQuality=15.0;
   }
   else
   if(
      adx>=MinimumADX*0.8
   )
   {
      adxQuality=10.0;
   }


   score+=adxQuality;

   //================================================
   // KCI DIRECTIONAL QUALITY
   //================================================

   double kci_main=0.0, kdi_plus=0.0, kdi_minus=0.0;
   GetKCIDirectionalMatrix(symbol, PERIOD_CURRENT, kci_main, kdi_plus, kdi_minus, KCI_DX_BasePeriod, KCI_DX_ZScorePeriod, KCI_DX_Sensitivity);

   double kciQuality=0.0;

   if(signal==1 && kdi_plus>kdi_minus && kci_main>KCI_DX_MainThreshold)
   {
      kciQuality=10.0;
   }
   else
   if(signal==-1 && kdi_minus>kdi_plus && kci_main>KCI_DX_MainThreshold)
   {
      kciQuality=10.0;
   }

   score+=kciQuality;


   //================================================
   // KCI VOLATILITY FILTER
   //================================================

   double kci_vd=GetKCIVolatilityDistance(symbol, PERIOD_CURRENT, KCI_VD_Period, 0);

   double kciVolQuality=0.0;

   if(kci_vd>0.0 && kci_vd<=(GetATR(symbol)*0.5))
   {
      kciVolQuality=5.0;
   }

   score+=kciVolQuality;


   //================================================
   // AI CONFIDENCE
   //================================================

   double aiConfidence=
      GetAIConfidence(
         signal,
         symbol
      );


   score+=
      (
         aiConfidence*
         0.50
      );


   //================================================
   // LIMIT SCORE
   //================================================

   // v1.2.184 (P1.138) - GATE_REAL G3: o total passa a ser a FRACAO dos pontos
   // possiveis, em escala 0..100, em vez de uma soma com base arbitraria.
   // Maximo real = 20 (EMA) + 15 (RSI) + 15 (ADX) + 10 (KCI dir) + 5 (KCI vol)
   // + 50 (IA a 100%) = 115. Nenhuma parcela mudou de peso relativo; muda a
   // escala em que `MinMarketScore` (65.0) e comparado.
   const double maxScorePoints=115.0;
   double scorePoints=score;

   score=
      100.0*
      score/
      maxScorePoints;

   if(score>100.0)
      score=100.0;


   if(score<0.0)
      score=0.0;


   MarketScore=
      NormalizeDouble(
         score,
         2
      );

   SetMarketScore(symbol, MarketScore);

   //================================================
   // v1.2.10 - APRENDIZADO PELO HISTORICO REAL
   // O score passa a considerar o desempenho real do
   // simbolo (operacoes manuais + operacoes do EA),
   // restaurado de Data\XAU_AI_PRO_learning.csv.
   // Por padrao o aprendizado so incentiva (boost>=1).
   //================================================

   double learnedScore=LearningAdjustedScore(symbol,signal,MarketScore);

   if(learnedScore!=MarketScore)
   {
      if(logOnce)
         Print(
            "[LEARN] score ajustado | Symbol=",
            symbol,
            " | Score=",
            DoubleToString(MarketScore,2),
            " -> ",
            DoubleToString(learnedScore,2),
            " | ",
            LearningSymbolSummary(symbol),
            " | HORA_FACTOR=",
            DoubleToString(LearningHourScoreFactor(symbol),2)   // v1.2.35 P1.6: efeito da hora no score
         );

      MarketScore=NormalizeDouble(learnedScore,2);

      SetMarketScore(symbol, MarketScore);
   }


   //================================================
   // LOG (1x por minuto)
   //================================================

   // v1.2.97 (P1.86): 1x/15 min por simbolo e com tag [SCORE] - antes saia
   // 1x/min SEM TAG (linha orfa no journal, dificil de filtrar).
   if(logOnce && DecisionLogDue(symbol, "SCORE", 900))
      Print(
         "[SCORE] CALCULATED | Symbol=",
         symbol,
         " | Signal=",
         signal,
         " | EMA=",
         DoubleToString(
            emaStrength,
            2
         ),
         " | RSI=",
         DoubleToString(
            rsiQuality,
            2
         ),
         " | ADX=",
         DoubleToString(
            adxQuality,
            2
         ),
         " | AI=",
         DoubleToString(
            aiConfidence*0.50,
            2
         ),
         " | WARMUP=",
         (indicadoresProntos ? "NAO" : "SIM"),
         " | PTS=",
         DoubleToString(
            scorePoints,
            2
         ),
         " | TOTAL=",
         DoubleToString(
            MarketScore,
            2
         )
      );


   return MarketScore;
}


//==================================================
// ALLOW TRADE
//
// v1.2.20 (29/10/2026): AllowTrade ganhou uma versao COM MOTIVO
// (AllowTradeEx). Antes o scanner escrevia apenas
// "[SCANNER] BLOCK | AllowTrade (Validation/Score/IA)" e o dono nao sabia
// QUAL dos quatro gates barrou. Agora o journal diz o motivo exato, com o
// score medido quando ele for o culpado.
//==================================================

string g_allowBlockReason = "";   // ultimo motivo de veto neste grafico

bool AllowTradeEx(
   int signal,
   string symbol,
   string &reason
)
{
   reason="";

   if(signal==0)
   {
      reason="SIGNAL 0";
      return false;
   }


   if(symbol=="")
      symbol=_Symbol;


   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastAllowLog = 0;
   datetime allowNow = TimeCurrent();
   bool allowLogOnce = (allowNow - lastAllowLog >= 60);
   if(allowLogOnce)
      lastAllowLog = allowNow;


   //================================================
   // 1) VALIDACAO TECNICA
   //
   // ValidateTrade espera:
   // 1o = string symbol
   // 2o = int signal
   //
   // ValidateTrade registra o motivo real do veto em
   // g_validationLastBlock (ValidationEngine.mqh), por isso zeramos antes
   // para nao reportar um motivo antigo de outra chamada.
   //================================================

   g_validationLastBlock="";

   if(
      !ValidateTrade(
         symbol,
         signal
      )
   )
   {
      reason=
         "VALIDATION: "+
         ((g_validationLastBlock=="")?"sem detalhe":g_validationLastBlock);

      //--------------------------------------------------
      // v1.2.188 (08/11/2026) - P1.139
      // O PASSO 1 DO AllowTradeEx VETAVA EM SILENCIO.
      // MEDIDO (D-079/DELTA): 1 576 sinais no dia, 1 576 entraram em
      // AllowTradeEx e 0 passaram, e o passo da VALIDACAO era o unico dos
      // gates que devolvia false sem escrever a causa por inteiro - a razao
      // real do veto (TREND, SPREAD, AI, SESSION...) ficava so no contador
      // interno. Os passos 2 (NEWS) e 2c (MARKET INTEL) ja imprimiam
      // "DECISION BLOCKED"; este passa a imprimir o mesmo, com o motivo.
      // No maximo 1 linha por hora por CONTA e por simbolo+motivo, com o
      // motivo novo a sair na hora. A tag reusa ValidationGateTag (ja
      // saneada para nome de ficheiro, P2.15) com prefixo proprio, para nao
      // gastar a vez da linha [VALIDATION] BLOCK escrita pelo ValidateTrade.
      // So impressao: nenhum passo, condicao, limite, lote, alvo, stop,
      // spread, preco, regra de entrada ou de saida muda.
      //--------------------------------------------------
      string motivoVeto = (g_validationLastBlock == "" ? "sem detalhe" : g_validationLastBlock);

      if(AccountLogGatePodeImprimir("dblock_" + ValidationGateTag(symbol, motivoVeto), 3600))
         Print("DECISION BLOCKED | VALIDATION | Symbol=", symbol,
               " | Signal=", signal,
               " | Reason=", reason);

      return false;
   }


   //------------------------------------------------
   // 2) ETAPA 11 - NEWS FILTER: integracao explicita
   // Reforco a capa de noticias no DecisionEngine,
   // nao so via ValidateTrade. Nao bloqueia a gestao
   // de posicoes abertas (so novas entradas).
   //------------------------------------------------

   // v1.2.9 (29/10/2026): gate por simbolo. IsNewsBlocked() sem simbolo
   // consultava sempre o grafico mestre, e EnableNewsFilter=false desligava
   // o reforco mesmo com o modo "operar noticia" ativo.
   double newsLotF  = 1.0;
   double newsRiskF = 1.0;
   double newsTPF   = 1.0;
   string newsWhy   = "";

   if(NewsModuleActive() &&
      !NewsTradeAllow(symbol, newsLotF, newsRiskF, newsTPF, newsWhy))
   {
      g_newsBlockReason = GetNewsBlockDetail(symbol);

      reason=
         "NEWS: "+
         ((g_newsBlockReason=="")?newsWhy:g_newsBlockReason);

      if(allowLogOnce)
         Print(
            "DECISION BLOCKED | NEWS | Symbol=",
            symbol,
            " | Signal=",
            signal,
            " | Reason=",
            reason
         );

      NewsLogBlock();
      return false;
   }


   //------------------------------------------------
   // 2c) MARKET INTELLIGENCE: sessao, calendario, fechamento
   //------------------------------------------------

   string miReason = "";
   if(!IsMarketOpenForTrading(miReason))
   {
      reason = "MARKET INTEL: " + miReason;

      if(allowLogOnce)
         Print(
            "DECISION BLOCKED | MARKET INTEL | Symbol=",
            symbol,
            " | Signal=",
            signal,
            " | Reason=",
            reason
         );

      return false;
   }

   //------------------------------------------------
   // 2b) v1.2.22 - GUARDA DE CORRELACAO DE MOEDA
   //
   // Vem ANTES do score porque e um gate de CARTEIRA, nao de sinal: nao
   // adianta a entrada ter nota alta se ela seria a quinta aposta no mesmo
   // lado do dolar. O gate mais estrutural e avaliado primeiro.
   //
   // Sem isto, 16 graficos quase todos em USD permitiam comprar dolar cinco
   // vezes ao mesmo tempo e chamar isso de diversificacao.
   //------------------------------------------------

   string correlWhy = "";

   if(!CurrencyExposureGuard(symbol, signal, correlWhy))
   {
      reason = correlWhy;

      if(allowLogOnce)
         Print("DECISION BLOCKED | CORRELACAO | Symbol=", symbol,
               " / Signal=", signal, " | Reason=", reason);

      return false;
   }


   //------------------------------------------------
   // 3) SCORE MINIMO
   //------------------------------------------------

   double score=
      CalculateMarketScore(
         signal,
         symbol
      );


   if(
      // v1.2.186 - P1.2341 (D-088 #5): piso CONDICIONAL. Com leitura de IA
      // real continua MinMarketScore (65,0); sem IA vale MinMarketScoreNoAI
      // (default 45,0), porque as parcelas tecnicas somam no maximo 56,52 de
      // 100 e 65 nunca seria atingido sem o modelo.
      score<(AILeituraReal() ? MinMarketScore : MinMarketScoreNoAI)
   )
   {
      reason=
         "SCORE "+
         DoubleToString(score,2)+
         " < MinMarketScore "+
         DoubleToString(AILeituraReal() ? MinMarketScore : MinMarketScoreNoAI,2);

      if(allowLogOnce)
         Print(
            "DECISION BLOCKED | Symbol=",
            symbol,
            " | Score=",
            DoubleToString(
               score,
               2
            ),
            " | Min=",
            DoubleToString(
               (AILeituraReal() ? MinMarketScore : MinMarketScoreNoAI),
               2
            )
         );

      return false;
   }


   //------------------------------------------------
   // 4) v1.4.0 (Etapa 5): ADVANCED AI - veto final
   // A IA NAO tem autoridade absoluta: pode BLOQUEAR,
   // mas nunca cria sinal. Score ponderado (trend,
   // strength, spread, market, execution).
   //------------------------------------------------

   if(EnableAIFilter && !FinalAIAllow(signal, symbol))
   {
      reason=
         "ADV AI | Signal="+
         IntegerToString(signal);

      if(allowLogOnce)
         Print(
            "DECISION BLOCKED | ADV AI | Symbol=",
            symbol,
            " | Signal=",
            signal
         );

      return false;
   }

   return true;
}


// Compatibilidade: todo o projeto continua chamando AllowTrade().
// O motivo fica guardado em g_allowBlockReason para quem quiser detalhar.
bool AllowTrade(
   int signal,
   string symbol=""
)
{
   string reason="";

   bool ok=AllowTradeEx(signal,symbol,reason);

   g_allowBlockReason = (ok?"":reason);

   return ok;
}


//==================================================
// FINAL DECISION
//==================================================

int GetDecision(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;


   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastDecisionLog = 0;
   datetime decisionNow = TimeCurrent();
   bool decisionLogOnce = (decisionNow - lastDecisionLog >= 60);
   if(decisionLogOnce)
      lastDecisionLog = decisionNow;


   int signal=
      GetSignal(
         symbol
      );


   if(signal==0)
   {
      return 0;
   }


   if(
      !AllowTrade(
         signal,
         symbol
      )
   )
   {
      return 0;
   }


   if(decisionLogOnce)
      Print(
         "DECISION APPROVED | Symbol=",
         symbol,
         " | SIGNAL=",
         signal,
         " | SCORE=",
         DoubleToString(
            MarketScore,
            2
         )
      );


   return signal;
}


#endif

