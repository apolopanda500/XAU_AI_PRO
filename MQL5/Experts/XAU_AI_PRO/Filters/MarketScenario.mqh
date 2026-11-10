// XAU_AI_PRO v1.2.22
#ifndef MARKETSCENARIO_MQH
#define MARKETSCENARIO_MQH

//==================================================
// CENARIO GLOBAL (v1.2.21 - 29/10/2026)
//
// Pedido do dono: "adaptar o EA para todos os tipos de cenarios globais".
//
// O que existia antes desta camada:
//   * `TrendFilter` era BINARIO: preco acima da EMA200 H1 = so compra, abaixo
//     = so vende. Com `EnableTrendFilter=true` qualquer sinal contra a
//     tendencia era VETADO, sempre, em qualquer mercado.
//   * MEDIDO no journal em 29/10/2026 (21:55): as duas unicas entradas do dia
//     morreram exatamente ali -
//       EURUSD Signal=-1 -> VALIDATION: TREND SELL
//       USDCHF Signal=1  -> VALIDATION: TREND BUY
//     Nao era falta de sinal: era veto binario num mercado sem tendencia.
//   * `MarketRegime` ja sabia dizer TREND_UP / TREND_DOWN / RANGING, mas
//     NINGUEM usava essa leitura para decidir. Existia e nao servia.
//
// O que esta camada faz: classifica o cenario (tendencia forte, tendencia
// fraca, lateral, volatilidade) e ADAPTA tres coisas, em vez de vetar:
//   1) o GATE de tendencia: contra-tendencia passa a ser permitida, com
//      tamanho menor, quando o cenario e LATERAL;
//   2) o LOTE: cada cenario tem seu proprio fator;
//   3) o ALVO: cenario volatil entrega mais amplitude, lateral entrega menos.
//
// Regra de ouro desta camada: ela NUNCA aumenta risco acima do que o envelope
// (`MaxTotalRiskPercent`) e nunca desliga uma protecao. Ela so REDUZ lote e,
// no maximo, permite uma entrada que antes era vetada - com lote menor.
// Sem leitura de ADX (warm-up) o rigor antigo e mantido: contramao veta.
//==================================================

#include "../Core/Config.mqh"
#include "../Filters/MarketRegime.mqh"

enum ENUM_MARKET_SCENARIO
{
   SCENARIO_UNKNOWN      = 0,   // sem leitura (warm-up, erro de indicador)
   SCENARIO_TREND_STRONG = 1,   // ADX >= ScenarioADXStrong
   SCENARIO_TREND_WEAK   = 2,   // ADX entre fraco e forte
   SCENARIO_RANGING      = 3,   // ADX < ScenarioADXWeak
   SCENARIO_VOLATILE     = 4    // ATR% do preco acima do teto
};

//==================================================
// NOME LEGIVEL
//==================================================
string ScenarioToString(ENUM_MARKET_SCENARIO s)
{
   if(s == SCENARIO_TREND_STRONG) return "TENDENCIA_FORTE";
   if(s == SCENARIO_TREND_WEAK)   return "TENDENCIA_FRACA";
   if(s == SCENARIO_RANGING)      return "LATERAL";
   if(s == SCENARIO_VOLATILE)     return "VOLATILIDADE_ALTA";

   return "SEM_LEITURA";
}

//==================================================
// DETECCAO
//
// Fonte unica: ADX (forca) + ATR% do preco (volatilidade) - as duas medidas
// que ja existem no projeto e que sao comparaveis entre ouro, forex, indices
// e cripto porque a volatilidade e lida em PERCENTUAL do preco, nunca em
// pontos crus.
//
// A volatilidade vem PRIMEIRO: mercado em disparada e um cenario proprio,
// mesmo com ADX alto - nele o tamanho tem que cair, nao a direcao importar.
//==================================================
ENUM_MARKET_SCENARIO MarketScenarioDetect(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   double volPct = MarketVolatilityPercent(symbol);

   // Volatilidade indisponivel devolve -1.0: "nao sei" nao classifica como
   // cenario de risco, senao o EA reduziria lote por falha de leitura.
   if(ScenarioVolPctMax > 0.0 && volPct > 0.0 && volPct >= ScenarioVolPctMax)
      return(SCENARIO_VOLATILE);

   double adx = GetADX(symbol);

   // ADX <= 0 = indisponivel. Nao inventa cenario.
   // MEDIDO em 29/10/2026 22:14 no journal: o simbolo do grafico mestre
   // apareceu com "ADX=0.0" (handle ainda aquecendo) e a leitura anterior
   // (`adx < 0.0`) classificava 0.0 como LATERAL - ou seja, "sem leitura"
   // virava permissao de contra-tendencia. Zero nao e lateral: e ausencia
   // de dado, e ausencia de dado nao libera nada.
   if(adx <= 0.0)
      return(SCENARIO_UNKNOWN);

   if(adx >= ScenarioADXStrong)
      return(SCENARIO_TREND_STRONG);

   if(adx >= ScenarioADXWeak)
      return(SCENARIO_TREND_WEAK);

   return(SCENARIO_RANGING);
}

//==================================================
// FATOR DE LOTE POR CENARIO
//
// Nunca maior que 1.0 neste desenho: o cenario pode REDUZIR o tamanho, mas a
// escala para cima continua sendo responsabilidade do lote dinamico por
// conviccao (CalculateDynamicLot). Duas fontes somando escala para cima seria
// multiplicar risco sem medir.
//==================================================
double ScenarioLotFactor(string symbol="")
{
   if(!EnableScenarioAdaptation)
      return(1.0);

   ENUM_MARKET_SCENARIO s = MarketScenarioDetect(symbol);

   if(s == SCENARIO_VOLATILE)     return(ScenarioLotVolatile);
   if(s == SCENARIO_RANGING)      return(ScenarioLotRanging);
   if(s == SCENARIO_TREND_WEAK)   return(ScenarioLotWeak);
   if(s == SCENARIO_TREND_STRONG) return(ScenarioLotStrong);

   return(1.0);
}

//==================================================
// FATOR DE ALVO POR CENARIO
//
// Em disparada o preco percorre mais: alvo mais largo evita sair no primeiro
// respiro. Em mercado lateral o preco volta: alvo mais curto evita devolver o
// lucro. Os dois sao MULTIPLICADORES do alvo adaptativo por conviccao, e o
// resultado continua limitado por MinTargetPoints/MaxTargetPoints.
//==================================================
double ScenarioTargetFactor(string symbol="")
{
   if(!EnableScenarioAdaptation)
      return(1.0);

   ENUM_MARKET_SCENARIO s = MarketScenarioDetect(symbol);

   if(s == SCENARIO_VOLATILE)
      return(ScenarioTargetVolatile > 0.0 ? ScenarioTargetVolatile : 1.0);

   if(s == SCENARIO_RANGING)
      return(ScenarioTargetRanging > 0.0 ? ScenarioTargetRanging : 1.0);

   return(1.0);
}

//==================================================
// GATE DE TENDENCIA ADAPTATIVO
//
// Substitui o veto binario do `TrendFilter` quando
// `EnableAdaptiveTrendGate=true`.
//
// Regras, na ordem em que sao avaliadas:
//   1) sinal ALINHADO com a EMA200 H1 -> permitido (como sempre foi);
//   2) sem leitura de ADX             -> VETA contra-tendencia (mantem rigor);
//   3) ADX >= ScenarioCounterTrendMaxADX -> VETA (tendencia formada, ir contra
//      e brigar com fluxo);
//   4) cenario VOLATILE               -> VETA (disparada contra a tendencia e o
//      pior lugar do dia para tamanho pequeno);
//   5) resto (LATERAL / tendencia fraca) -> PERMITE, com lote reduzido por
//      ScenarioLotFactor.
//
// `reason` sempre sai preenchida: o journal passa a explicar a decisao.
//==================================================
bool ScenarioTrendGate(string symbol, int signal, string &reason)
{
   reason = "";

   if(signal == 0)
   {
      reason = "sem signal";
      return(false);
   }

   if(symbol == "")
      symbol = _Symbol;

   bool alinhado = (signal == 1) ? TrendBuy(symbol) : TrendSell(symbol);

   if(alinhado)
   {
      reason = "alinhado com EMA200";
      return(true);
   }

   //==================================================
   // Q-079 = B (07/11/2026, decisao do DONO): FOLGA DE 1 ATR
   //
   // MEDIDO em 05/11/2026 (D-079): 1576 sinais, 1576 entraram em
   // AllowTradeEx e 0 passaram; 58,5% dos vetos amostrados eram TREND.
   // O sinal exige EMA50>EMA200 + RSI<45 (pullback fundo) e este portao
   // exigia bid>EMA200(H1): no pullback fundo o bid fura a EMA200 H1 por
   // pouco e o portao lia contramao - o EA vetava o sinal que a regra
   // procura. Quanto melhor o pullback pela regra, mais certo o veto.
   //
   // A folga NAO apaga a guarda: ela isenta SO o teste da EMA200 (D-086,
   // v1.2.187). O veto de tendencia formada (ScenarioCounterTrendMaxADX)
   // vale tambem DENTRO da banda; acima de ScenarioTrendAtrSlack ATR de
   // distancia continua a ser contramao e segue as regras abaixo (ADX e
   // cenario). Sem leitura de EMA, de ATR ou de ADX, o rigor antigo fica
   // intacto.
   //==================================================
   if(!EnableAdaptiveTrendGate)
   {
      reason = "contramao vetada (EnableAdaptiveTrendGate=false)";
      return(false);
   }

   // v1.2.187 - D-086: o ADX passou a ser lido ANTES da folga Q-079/B.
   // A folga isenta apenas o teste da EMA200; o veto de tendencia formada
   // (ScenarioCounterTrendMaxADX) continua valendo DENTRO da banda.
   double adx = GetADX(symbol);

   // ADX <= 0 = sem leitura: mantem o rigor antigo (contramao veta).
   if(adx <= 0.0)
   {
      reason = "contramao vetada | ADX indisponivel";
      return(false);
   }

   // v1.2.186 - P1.2338: a folga so vale quando o ATR lido e do MESMO timeframe
   // da EMA de referencia (`TrendTF`, H1). `GetATR(symbol)` usa
   // `(ENUM_TIMEFRAMES)Period()`, ou seja o periodo do GRAFICO: num grafico M5
   // a folga compararia 1 ATR de M5 com uma distancia medida em H1 e valeria
   // uma fraccao do que o parametro diz. Sem coincidencia de timeframe nao se
   // aplica folga - fica o rigor antigo.
   if(ScenarioTrendAtrSlack > 0.0 && Period() == TrendTF)
   {
      double emaRef = 0.0;
      double bidRef = SymbolInfoDouble(symbol, SYMBOL_BID);
      double atrRef = GetATR(symbol);

      if(GetTrendEMA(emaRef, symbol) && bidRef > 0.0 && atrRef > 0.0)
      {
         double folga = ScenarioTrendAtrSlack * atrRef;

         if(MathAbs(bidRef - emaRef) <= folga)
         {
            // v1.2.187 - D-086: a folga isenta so o teste da EMA200; o veto
            // de tendencia formada continua valendo DENTRO da banda.
            if(adx < ScenarioCounterTrendMaxADX)
            {
               reason = "contramao dentro da folga de " +
                        DoubleToString(ScenarioTrendAtrSlack, 2) +
                        " ATR | dist=" + DoubleToString(bidRef - emaRef, 5) +
                        " | ATR=" + DoubleToString(atrRef, 5) +
                        " | Q-079/B | ADX=" + DoubleToString(adx, 1);
               return(true);
            }
         }
      }
   }

   // Daqui para baixo: sinal CONTRA a tendencia de referencia.

   ENUM_MARKET_SCENARIO s = MarketScenarioDetect(symbol);

   if(adx >= ScenarioCounterTrendMaxADX)
   {
      reason = "contramao vetada | tendencia formada | ADX=" + DoubleToString(adx, 1) +
               " >= " + DoubleToString(ScenarioCounterTrendMaxADX, 1);
      return(false);
   }

   if(s == SCENARIO_VOLATILE)
   {
      reason = "contramao vetada | volatilidade alta | ATR%=" +
               DoubleToString(MarketVolatilityPercent(symbol), 2);
      return(false);
   }

   reason = "contramao PERMITIDA | cenario " + ScenarioToString(s) +
            " | ADX=" + DoubleToString(adx, 1) +
            " | lote x" + DoubleToString(ScenarioLotFactor(symbol), 2);

   return(true);
}

//==================================================
// v1.2.118 - P2.06: RETRATO INICIAL AGREGADO
//
// MEDIDO em 03/11/2026, master USDCNH: a primeira observacao de cada
// simbolo depois do reload publicava 11 linhas [CENARIO] em 4,4 s
// (07:31:00.438 a 07:31:04.816) para a MESMA foto de mercado - 236
// linhas no dia, a familia mais cara depois de GLOBAL/AI.
//
// Uma primeira observacao nao e uma mudanca de estado. Os simbolos
// passam a ser acumulados e publicados como UMA linha de retrato no
// fim do ciclo (ScenarioSnapFlush, chamada pelo scanner), 1x/hora por
// CONTA. A mudanca REAL de cenario continua a sair na hora, por
// simbolo e sem filtro, e o [CENARIO] heartbeat por simbolo nao muda.
// Nenhum limite, regra de entrada ou de saida, lote, spread, alvo,
// precificacao ou parametro de risco e tocado aqui.
//==================================================
#define SCENARIO_SNAP_MAX 16

string g_scenarioSnap[SCENARIO_SNAP_MAX];
int    g_scenarioSnapN = 0;

//+------------------------------------------------------------------+
//| Esvazia o acumulador do retrato inicial numa unica linha.        |
//| Chamada pelo scanner no fim de cada ciclo. Sem pendentes nao     |
//| imprime nada. Se a janela por CONTA negar, o buffer e limpo na   |
//| mesma: o dado e estado repetido, nao um evento.                  |
//+------------------------------------------------------------------+
void ScenarioSnapFlush()
{
   if(g_scenarioSnapN <= 0)
      return;

   string corpo = "";

   for(int i = 0; i < g_scenarioSnapN; i++)
      corpo += (i == 0 ? "" : " | ") + g_scenarioSnap[i];

   int n = g_scenarioSnapN;
   g_scenarioSnapN = 0;

   if(AccountLogGatePodeImprimir("cenario_snap", 3600))
      Print("[CENARIO] RETRATO | simbolos=", n, " | ", corpo);
}

//==================================================
// P2.18 (03/11/2026): LEITURA SEM SENTINELA
//
// MEDIDO no journal do expert as 22:32:56, no reload: a linha [CENARIO] de
// EURUSD saiu com "ADX=20.6 | ATR%=-1.00". O -1.00 nao e volatilidade, e o
// sentinela de "sem leitura" de MarketVolatilityPercent(); o mesmo vale para
// ADX <= 0. O codigo sempre tratou os dois corretamente (volPct > 0.0 e
// adx <= 0.0), mas o journal publicava o sentinela como se fosse medida, e um
// valor negativo de volatilidade nao pode ser lido de duas maneiras.
// As duas funcoes abaixo traduzem o sentinela para texto; nenhuma deteccao,
// factor de lote, factor de alvo ou leitura de indicador muda.
//==================================================
string ScenarioADXStr(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   double adx = GetADX(symbol);

   if(adx <= 0.0)
      return("sem leitura");

   return(DoubleToString(adx, 1));
}

string ScenarioAtrPctStr(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   double volPct = MarketVolatilityPercent(symbol);

   if(volPct < 0.0)
      return("sem leitura(atr=" + DoubleToString(GetATR(symbol), 6) + ",bid=" + DoubleToString(SymbolInfoDouble(symbol, SYMBOL_BID), 6) + ")");   // v1.2.158 - P1.120: nomeia a causa em vez de a esconder

   return(DoubleToString(volPct, 2));
}

//==================================================
// LINHA DE CENARIO PARA O JOURNAL
//
// v1.2.22: deixou de repetir. MEDIDO no journal em 29/10/2026: a mesma linha
// de XAUUSD saiu identica as 22:14, 22:15 e 22:16 (ADX=29.4, ATR%=0.36,
// TREND_DOWN, lote x1.00). O throttle era so de TEMPO (60s por simbolo), entao
// um cenario que nao mudou ocupava o journal de 60 em 60 segundos e empurrava
// para fora o que importava.
//
// Agora a linha sai quando o cenario MUDA (assinatura = cenario + regime +
// fatores, exatamente o que decide lote e alvo), e um heartbeat a cada 15 min
// prova que a leitura continua viva. Throttle antes de medir, como antes: o
// scanner varre 11 simbolos por ciclo e medir para descartar e custo sem
// informacao.
//==================================================
void ScenarioLog(string symbol, string contexto="")
{
   if(!EnableScenarioLog)
      return;

   if(symbol == "")
      symbol = _Symbol;

   static string   ultimoSim[64];
   static string   ultimaAssinatura[64];
   static datetime ultimoTs[64];
   static int      usados = 0;

   datetime agora = TimeCurrent();
   int slot = -1;

   for(int i = 0; i < usados; i++)
   {
      if(ultimoSim[i] != symbol)
         continue;

      slot = i;
      break;
   }

   if(slot < 0)
   {
      if(usados >= 64)
         return;

      slot = usados;
      ultimoSim[usados] = symbol;
      usados++;
   }

   // Piso de tempo: nunca mais de uma linha por minuto por simbolo, mesmo que
   // o cenario oscile na fronteira do ADX.
   if(ultimoTs[slot] > 0 && (agora - ultimoTs[slot]) < 60)
      return;

   ENUM_MARKET_SCENARIO s   = MarketScenarioDetect(symbol);
   MarketRegimeType     reg = GetMarketRegime(symbol);
   double               lot = ScenarioLotFactor(symbol);
   double               tgt = ScenarioTargetFactor(symbol);

   string assinatura = IntegerToString((int)s) + "|" +
                       IntegerToString((int)reg) + "|" +
                       DoubleToString(lot, 2) + "|" +
                       DoubleToString(tgt, 2);

   bool mudou = (ultimaAssinatura[slot] != assinatura);
   // P2.02: o heartbeat era de 15 min por INSTANCIA, logo 15 graficos davam
   // 15 linhas iguais por hora. Passa a 1x/hora por CONTA e por simbolo. O que
   // MUDOU (classe, regime, factor de lote e factor de alvo) sai na hora.
   bool heartbeat = (ultimoTs[slot] > 0 && (agora - ultimoTs[slot]) >= 3600);

   if(!mudou && !heartbeat)
      return;

   // P2.06: a primeira observacao desta instancia (o reload esvazia o cache)
   // nao e mudanca de estado - e o MESMO retrato a repetir-se por simbolo.
   // Passa a acumular no buffer e a sair numa unica linha no fim do ciclo
   // (ScenarioSnapFlush), 1x/hora por CONTA. O cache fica actualizado aqui,
   // logo a proxima mudanca REAL sai na hora e sem filtro.
   if(mudou && ultimoTs[slot] == 0)
     {
      ultimaAssinatura[slot] = assinatura;
      ultimoTs[slot]         = agora;

      if(g_scenarioSnapN < SCENARIO_SNAP_MAX)
        {
         g_scenarioSnap[g_scenarioSnapN] = symbol + " " + ScenarioToString(s) +
                                           " ADX=" + ScenarioADXStr(symbol) +
                                           " ATR%=" + ScenarioAtrPctStr(symbol) +
                                           " " + MarketRegimeToString(reg) +
                                           " lote x" + DoubleToString(lot, 2) +
                                           " alvo x" + DoubleToString(tgt, 2);
         g_scenarioSnapN++;
        }

      return;
     }

   if(!mudou && !AccountLogGatePodeImprimir("cenario_hb_" + symbol, 3600))
      return;

   ultimaAssinatura[slot] = assinatura;
   ultimoTs[slot]         = agora;

   Print("[CENARIO] ", symbol,
         " | ", ScenarioToString(s),
         " | ADX=", ScenarioADXStr(symbol),
         " | ATR%=", ScenarioAtrPctStr(symbol),
         " | tendencia=", MarketRegimeToString(reg),
         " | lote x", DoubleToString(lot, 2),
         " | alvo x", DoubleToString(tgt, 2),
         (mudou ? "" : " | heartbeat"),
         (contexto == "" ? "" : " | "+contexto));
}

#endif
