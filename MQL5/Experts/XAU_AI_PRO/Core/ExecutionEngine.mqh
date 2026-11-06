// XAU_AI_PRO v1.2.52
#ifndef EXECUTIONENGINE_MQH
#define EXECUTIONENGINE_MQH

#include "../Core/Config.mqh"
#include "../Core/StateMachine.mqh"   // v1.4.0 (Etapa 4): StateSet/STATE_*
#include "../Core/OrderManager.mqh"
#include "../Core/RiskEngine.mqh"
#include "../Core/RiskCenter.mqh"       // ETAPA 15.5: gate unificado de risco
#include "../Core/PositionManager.mqh"
#include "../Core/TradeController.mqh"
#include "../Core/SymbolValidator.mqh"
#include "../Management/DailyRisk.mqh"
#include "../Management/PortfolioManager.mqh"
#include "../AI/AIEngine.mqh"
#include "../Enterprise/SmartExecution.mqh"
#include "../Enterprise/SimulationEngine.mqh"
#include "../Filters/NewsFilter.mqh"        // OPERAR NOTICIA (29/10/2026)
#include "../Filters/MarketScenario.mqh"   // v1.2.21: cenario global
#include "../Filters/GlobalScenario.mqh"    // v1.2.22: classe de ativo + sessao GMT + correlacao
#include "../Filters/CostGate.mqh"          // v1.2.25: custo (spread+comissao) vs alvo em US$
#include "../Filters/MarketIntelligence.mqh" // v1.3: ajuste de lote por inteligencia de mercado
#include "../Indicators/MarketPulse.mqh"     // VOLUME + VELOCIDADE (29/10/2026)
#include "../Enterprise/Telemetry.mqh"   // ETAPA 15.6.3: contadores reais
#include "../Monitoring/EventEmitter.mqh" // ETAPA 15.6.1/15.6.2: event stream (canonico)

//==================================================
// EXECUTION ENGINE
//==================================================

//==================================================
// NOTA DE CONVICCAO DO SINAL (29/10/2026)
//==================================================
// UMA nota (0..4) governa LOTE e ALVO. Ela junta as duas condicoes pedidas:
// "acima da metade de confianca" (GetAIConfidence) e "tendencia clara" (ADX).
// ADX indisponivel devolve -1 no warm-up e NAO sobe a nota: "nao sei" nunca
// e "tendencia clara".
int ConvictionGrade(double conf, double adx)
{
   if(conf >= DynConfElite  && adx >= DynADXStrong) return(4);
   if(conf >= DynConfStrong && adx >= DynADXStrong) return(3);
   if(conf >= DynConfClear  && adx >= DynADXClear)  return(2);
   if(conf >= DynConfBase)                          return(1);
   return(0);
}

string ConvictionGradeName(int grade)
{
   if(grade >= 4) return("ELITE");
   if(grade == 3) return("FORTE");
   if(grade == 2) return("CLARA");
   if(grade == 1) return("BASE");
   return("FRACA");
}

double LotFactorForGrade(int grade)
{
   if(!EnableDynamicLot)
      return(1.0);

   if(grade >= 4) return(DynLotFactorElite);
   if(grade == 3) return(DynLotFactorStrong);
   if(grade == 2) return(DynLotFactorClear);
   if(grade == 1) return(DynLotFactorBase);
   return(DynLotFactorMin);
}

double TargetFactorForGrade(int grade)
{
   if(!EnableAdaptiveTargets)
      return(RewardRatio);

   if(grade >= 4) return(DynTPFactorElite);
   if(grade == 3) return(DynTPFactorStrong);
   if(grade == 2) return(DynTPFactorClear);
   if(grade == 1) return(DynTPFactorBase);
   return(DynTPFactorMin);
}

//==================================================
// LOTE DINAMICO (29/10/2026) - NAO existe lote fixo
//==================================================
// O lote e o MENOR entre:
//   (a) o lote de referencia (risco permitido para a distancia StopLossPoints)
//       multiplicado pela faixa de conviccao / forca da tendencia;
//   (b) o teto por operacao MaxRiskPerTradePercentCap do saldo.
// Devolve 0 quando nao ha lote valido: quem chama recusa a entrada.
double CalculateDynamicLot(
   string symbol,
   int    signal,
   int    slRefPoints,
   double slowFactor,
   double &confOut,
   double &adxOut,
   int    &gradeOut
)
{
   confOut  = GetAIConfidence(signal, symbol);
   adxOut   = GetADX(symbol);
   gradeOut = ConvictionGrade(confOut, adxOut);

   double baseLot = CalculateLotByRiskAuto(symbol, slRefPoints);

   if(baseLot <= 0.0)
   {
      Print("[TRADE] BLOQUEADA | ", symbol,
            " | lote de referencia invalido (risco/escala)");
      return(0.0);
   }

   double factor = LotFactorForGrade(gradeOut);

   if(slowFactor > 0.0)
      factor *= slowFactor;

   double lot = baseLot * factor;

   //--------------------------------------------------
   // v1.3: AJUSTE DE LOTE POR INTELIGÊNCIA DE MERCADO
   // Reduz o lote quando o mercado tem baixa inteligencia
   // (fora de sessao, proximo de fechamento, evento proximo).
   //--------------------------------------------------
   double intelLotFactor = GetIntelligenceLotFactor();
   if(intelLotFactor < 1.0)
   {
      lot = lot * intelLotFactor;
      Print(
         "[INTEL LOT] ", symbol,
         " | fator=", DoubleToString(intelLotFactor, 2),
         " | lote=", DoubleToString(lot, 3)
      );
   }

   // Teto de risco POR OPERACAO: a faixa de conviccao pode pedir 2x/3x/4x o
   // lote de referencia. Este teto impede que "muita confianca" vire, sozinha,
   // uma aposta que estoura o dia.
   if(MaxRiskPerTradePercentCap > 0.0)
   {
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      double perLot  = RiscoEmDinheiroDaOrdem(symbol, 1.0, (double)slRefPoints);

      if(balance > 0.0 && perLot > 0.0)
      {
         double capLot = (balance * MaxRiskPerTradePercentCap / 100.0) / perLot;

         if(lot > capLot)
         {
            Print("LOT CAP | ", symbol,
                  " | teto por operacao ", DoubleToString(MaxRiskPerTradePercentCap, 2),
                  "% = ", DoubleToString(capLot, 3),
                  " lotes | faixa pedia ", DoubleToString(lot, 3));
            lot = capLot;
         }
      }
   }

   //--------------------------------------------------
   // TETO DE RISCO REAL (v1.2.26)
   // O teto percentual acima usa `slRefPoints` (300 pts), mas a escada de
   // saida arma o stop a 1R, que costuma ser MUITO menor. Aqui o lote e
   // capado pela distancia que o stop realmente vai usar. Sem isto, um
   // NZDUSD de 0,60 lotes com stop de 5 pts custou -20,92 USD em 29/10/2026.
   //--------------------------------------------------
   if(MaxRiskPerTradeUsd > 0.0)
   {
      double oneRPoints = NoiseDistancePointsForRisk(symbol);

      if(oneRPoints > 0.0)
      {
         double perLotReal = RiscoEmDinheiroDaOrdem(symbol, 1.0, oneRPoints);

         if(perLotReal > 0.0)
         {
            double capReal = MaxRiskPerTradeUsd / perLotReal;

            if(lot > capReal)
            {
               // v1.2.57 (P1.34): esta linha nao tinha portao nenhum. MEDIDO:
               // 2 233 linhas no journal do backtest. O cap (lot = capReal)
               // acontece SEMPRE; so o texto passa a sair 1x/hora.
               if(DiagGateAllow(symbol, "LOT_CAP", "REAL", 3600))
               PrintFormat("LOT CAP REAL | %s | 1R=%.0f pts | perda no stop com %.3f lotes = %.2f USD > teto %.2f | lote -> %.3f",
                           symbol, oneRPoints, lot, lot * perLotReal, MaxRiskPerTradeUsd, capReal);
               lot = capReal;
            }
         }
      }
   }

   double step   = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);

   if(step <= 0.0)
      step = minLot;

   if(step > 0.0)
      lot = MathFloor(lot / step + 1e-8) * step;

   if(maxLot > 0.0 && lot > maxLot)
      lot = maxLot;

   if(lot < minLot - 1e-8)
   {
      if(!AllowMinLotOverride)
      {
         Print("EXECUTION BLOCK | LOT MIN | ", symbol,
               " | Lot=", DoubleToString(lot, 3),
               " | Min=", DoubleToString(minLot, 3));
         return(0.0);
      }

      // v1.2.57 (P1.34): o desfecho era lot|minLot e ambos variam por
      // candidato, o que anulava o portao. MEDIDO: 147 241 linhas desta
      // mensagem no journal do backtest. Desfecho estavel "FORCA_MIN";
      // o lote forcado (lot = minLot) e o aviso de risco continuam iguais.
      if(DiagGateAllow(symbol, "LOT_MIN", "FORCA_MIN", 3600))
      Print("EXECUTION WARNING | FORCA LOTE MINIMO | ", symbol,
            " | Lot=", DoubleToString(lot, 3),
            " | Min=", DoubleToString(minLot, 3),
            " | Risco real excede o configurado");
      lot = minLot;
   }

   // v1.2.57 (P1.34): o desfecho era ConvictionGradeName+lot, e o lote muda a
   // cada candidato - logo o portao nunca via repeticao. MEDIDO no journal do
   // backtest (5 077 002 linhas): 177 619 linhas desta mensagem, o maior
   // emissor unico que sobrou. O desfecho passou a ser a GRADE (conjunto
   // pequeno e estavel) e os numeros continuam a sair no texto.
   if(DiagGateAllow(symbol, "LOTE_DIN",
            ConvictionGradeName(gradeOut), 14400))
   Print("EXECUTION: LOTE DINAMICO | ", symbol,
         " | Conviccao=", ConvictionGradeName(gradeOut),
         " | Conf=", DoubleToString(confOut, 1),
         " | ADX=", DoubleToString(adxOut, 1),
         " | Fator=", DoubleToString(factor, 2),
         " | Base=", DoubleToString(baseLot, 3),
         " | Final=", DoubleToString(lot, 3));

   return(lot);
}

input double MinRewardRatio          = 0.55;  // piso de RR por operacao (era 0.0 = sem piso)
input double EffectiveRiskWarnFactor = 1.5;

bool ExecuteTrade(string symbol,int signal)
{
   if(symbol=="")
      return false;

   if(signal==0)
      return false;

   if(!CanTrade(symbol))
   {
      Print("EXECUTION FAIL | CanTrade=false | symbol=",symbol);
      Print("  - LastTradeTime=",LastTradeTime," | Now=",TimeCurrent());
      EventTradeRejected(symbol, "cooldown entre trades", "CAN_TRADE=false");
      return false;
   }

   if(!CanOpenPosition(symbol))
   {
      Print("EXECUTION FAIL | CanOpenPosition=false | symbol=",symbol);
      EventTradeRejected(symbol, "posicao aberta ou limite de posicoes",
                         "POSITION_LIMIT");
      return false;
   }

    // v1.4.0 (Etapa 4): risco verificado
    StateSet(symbol, STATE_RISK_CHECK);

    // Verificar limite diario
    if(!CanTradeToday())
    {
       Print("EXECUTION: Limite diario atingido");
       EventRiskBlock(symbol, "limite diario de trades atingido");
       return false;
    }

    //==================================================
    // RISK CENTER — GATE UNIFICADO (ETAPA 15.5)
    //==================================================
    // RiskCenter.mqh existia mas NAO era chamado no fluxo
    // de execução. As checagens eram feitas de forma
    // espalhada: CanTradeToday() aqui, CSafetyManager::
    // CheckAll() no OnTick, EquityProtection no OnTick.
    //
    // Agora o RiskCenter é o gate ÚNICO e OBRIGATÓRIO
    // para novas entradas. Ele consolida em ordem
    // determinística:
    //   1. DAILY_LOSS      — perda diária vs limite
    //   2. DAILY_DRAWDOWN  — drawdown vs limite
    //   3. MAX_TRADES_PER_DAY — contagem de trades
    //   4. FREE_MARGIN     — margem livre mínima
    //   5. TOTAL_EXPOSURE  — exposição total
    //
    // Fail-closed: se qualquer leitura falhar, bloqueia.
    string riskReason = "";
    if(!RiskAllowEntry(symbol, riskReason))
    {
       Print("EXECUTION: RISK CENTER BLOCK | ", symbol, " | Motivo=", riskReason);
       EventRiskBlock(symbol, "RiskCenter bloqueou: " + riskReason);
       return false;
    }

   //==================================================
   // NOTICIA + REGIME DE MERCADO (29/10/2026)
   //==================================================
   // Noticia deixou de ser apenas bloqueio: NewsTradeAllow devolve os
   // multiplicadores do evento (lote menor, referencia e alvo maiores) ou
   // barra a entrada quando o modo e BLOCK.
   double newsLotFactor = 1.0;
   double newsRiskMult  = 1.0;
   double newsTPMult    = 1.0;
   double newsMinConf   = 0.0;
   string newsReason    = "";
   bool   emNoticia     = false;

   if(!NewsTradeAllow(symbol, newsLotFactor, newsRiskMult, newsTPMult, newsReason))
   {
      Print("[TRADE] BLOQUEADA | ", symbol, " | noticia | ", newsReason);
      EventRiskBlock(symbol, "noticia: " + newsReason);
      return false;
   }

   if(newsReason != "")
   {
      emNoticia   = true;
      // v1.2.98 (03/11/2026) - P1.88: o piso de confianca da noticia nao pode
      // ser MAIOR que o piso normal de entrada (MinAIConfidence). Medido: no
      // journal de 02/11 o EA pedia Conf >= 70 durante a noticia enquanto a
      // propria IA entregava 51-67 de rotina — a noticia desligava o EA mesmo
      // com sinal aprovado no score e no ADV AI. A protecao real do modo
      // noticia e o lote x0.35 e a referencia x1.6, que continuam aplicados.
      newsMinConf = NewsTradeMinConf;
      if(MinAIConfidence > 0.0 && newsMinConf > MinAIConfidence)
         newsMinConf = MinAIConfidence;

      // v1.2.97 (03/11/2026) - P1.86: a mesma noticia reimprimia este bloco a
      // cada ciclo de 6 s por simbolo. Passa a 1x/30 min por simbolo.
      if(DiagGateAllow(symbol, "NEWS_MODE", newsReason, 1800))
      Print("[TRADE] MODO NOTICIA | ", symbol,
            " | ", newsReason,
            " | Lote x", DoubleToString(newsLotFactor, 2),
            " | Referencia x", DoubleToString(newsRiskMult, 2),
            " | Alvo x", DoubleToString(newsTPMult, 2));
   }

   // Distancia de REFERENCIA da entrada: dimensiona o lote, cobra o orcamento
   // do dia e define o alvo. Na noticia ela e alargada porque o evento anda
   // mais que o mercado normal.
   double slBase = (double)StopLossPoints;

   if(newsRiskMult > 1.0 && slBase > 0.0)
      slBase *= newsRiskMult;

   // REGIME DE MERCADO: volume alto + preco correndo = modo rapido.
   double pulseVol = 0.0;
   double pulseVel = 0.0;
   ENUM_PULSE_REGIME pulseRegime = GetMarketPulse(symbol, pulseVol, pulseVel);

   if(pulseRegime != PULSE_NORMAL)
      Print("EXECUTION: REGIME RAPIDO | ", symbol,
            " | Regime=", PulseRegimeName(pulseRegime),
            " | Volume x", DoubleToString(pulseVol, 2),
            " | Velocidade ", DoubleToString(pulseVel, 2), " ATR");

   //==================================================
   // LOTE DINAMICO (29/10/2026) - SEM lote fixo
   //==================================================
   // Meta de lucro do dia: depois de batida, ou para de abrir, ou reduz o
   // lote. O freio olha LucroRealizadoHojeUSD() (deals FECHADOS do EA), nao
   // posicao aberta.
   double slowFactor = 1.0;
   double metaDia    = EnableDailyProfitTarget ? DailyTargetEffectiveUsd() : 0.0;

   if(EnableDailyProfitTarget && metaDia > 0.0)
   {
      double lucroHoje = LucroRealizadoHojeUSD();
      double pctMeta   = MathMin(MathMax(DailyProfitSlowPercent, 0.0), 100.0);
      double meta      = metaDia * pctMeta / 100.0;

      if(meta > 0.0 && lucroHoje >= meta)
      {
         if(DailyProfitStopTrading)
         {
            Print("EXECUTION: META DIARIA BATIDA | ", symbol,
                  " | Lucro=", DoubleToString(lucroHoje, 2),
                  " | Meta=", DoubleToString(metaDia, 2),
                  " | novas entradas bloqueadas ate o proximo dia");
            EventRiskBlock(symbol, "meta diaria de lucro batida");
            return false;
         }

         slowFactor = (DailyProfitSlowLotFactor > 0.0) ? DailyProfitSlowLotFactor : 1.0;

         static datetime ultimoAvisoMeta = 0;

         if(TimeCurrent() - ultimoAvisoMeta >= 300)
         {
            ultimoAvisoMeta = TimeCurrent();
            Print("EXECUTION: META DIARIA BATIDA | desacelerando | Lucro=",
                  DoubleToString(lucroHoje, 2),
                  " | Fator de lote=", DoubleToString(slowFactor, 2));
         }
      }
   }

   // Noticia reduz o lote; disparada EXTREMA reduz mais (spike e o pior lugar
   // do dia para tamanho grande).
   slowFactor *= newsLotFactor;

   if(pulseRegime == PULSE_EXTREME && PulseFastLotFactor > 0.0)
      slowFactor *= PulseFastLotFactor;

   // APRENDIZADO (v1.2.14): par/direcao/hora com historico ruim reduz o LOTE.
   // Nunca veta a entrada - o dono pediu "corrigir tudo" sem bloqueios indevidos.
   double learnLot = LearningLotPenalty(symbol, signal)
                   * LearningHourLotPenalty(symbol);

   if(learnLot < 1.0)
   {
      slowFactor *= learnLot;

      // v1.2.52 (P1.29): medido em 31/10/2026 no run actual do backtest:
      // 13 228 linhas desta mensagem (1,07%), sem portao nenhum. A chave do
      // desfecho e o proprio fator de lote - e o valor que reduz o lote e o
      // unico que interessa acompanhar; o resumo do historico muda a cada
      // trade e nao pode servir de chave. slowFactor fica FORA do portao.
      if(DiagGateAllow(symbol, "APRENDIZADO", DoubleToString(learnLot, 2), 14400))
         Print("EXECUTION: APRENDIZADO | ", symbol,
               " | lote x", DoubleToString(learnLot, 2),
               " | ", LearningSymbolSummary(symbol));
   }

   // CENARIO GLOBAL (v1.2.21): o TIPO de mercado define o TAMANHO.
   // Lateral e volatilidade reduzem; tendencia forte mantem. Nunca aumenta
   // (fatores <= 1.0), entao o envelope de risco continua sendo o teto.
   double cenarioLot = ScenarioLotFactor(symbol);
   string cenarioNome = ScenarioToString(MarketScenarioDetect(symbol));

   if(cenarioLot < 1.0)
   {
      slowFactor *= cenarioLot;

      static datetime ultimoAvisoCenario = 0;

      if(TimeCurrent() - ultimoAvisoCenario >= 300)
      {
         ultimoAvisoCenario = TimeCurrent();
         Print("EXECUTION: CENARIO | ", symbol,
               " | ", cenarioNome,
               " | lote x", DoubleToString(cenarioLot, 2),
               " | alvo x", DoubleToString(ScenarioTargetFactor(symbol), 2));
      }
   }
   // SESSAO GLOBAL (v1.2.22): a mesma estrategia nao tem o mesmo tamanho na
   // Asia e no cruzamento Londres/NY. A sessao vem em GMT (nao em hora de
   // servidor) e o efeito e SO no lote - reduzir liquidez nao deve vetar.
   double sessaoLot = SessionLotFactor(symbol);

   if(sessaoLot < 1.0)
   {
      slowFactor *= sessaoLot;

      static datetime ultimoAvisoSessao = 0;

      if(TimeCurrent() - ultimoAvisoSessao >= 300)
      {
         ultimoAvisoSessao = TimeCurrent();
         Print("EXECUTION: SESSAO | ", symbol,
               " | ", SessionBucketToString(SessionBucketNow()),
               " GMT | classe ", AssetClassToString(AssetClassOf(symbol)),
               " | lote x", DoubleToString(sessaoLot, 2));
      }
   }

   double aiConfidence = 0.0;
   double adxNow       = 0.0;
   int    conviction   = 0;
   int    slRefPts     = (int)MathRound(slBase);
   double lot = CalculateDynamicLot(symbol, signal, slRefPts,
                                    slowFactor, aiConfidence, adxNow, conviction);

   if(lot <= 0.0)
   {
      Print("EXECUTION: LOTE INVALIDO | ", symbol,
            " | motivo acima (risco/escala)");
      EventTradeRejected(symbol, "lote invalido (bloqueio de risco)", "INVALID_LOT");
      return false;
   }

   // v1.2.37 P1.10: REAL GUARD - exposicao SEM stop no mesmo simbolo.
   // A regra do dono e entrar sem stop e armar depois. Numa conta real,
   // varias posicoes nuas ao mesmo tempo multiplicam a exposicao sem limite
   // definido; o guarda limita a quantidade (RealGuardMaxUnarmedPositions,
   // default 1). Em demo/backtest a funcao devolve sempre false.
   if(RealGuardUnarmedExposureBlocked(symbol))
   {
      PrintFormat("[REAL GUARD] ENTRADA BLOQUEADA | %s | posicoes sem stop=%d | limite=%d",
                  symbol, RealGuardCountUnarmedPositions(symbol), RealGuardMaxUnarmedPositions);

      EventTradeRejected(symbol, "exposicao sem stop acima do limite do guarda real", "REAL_GUARD_UNARMED");
      return false;
   }

   //==================================================
   // TETO DE RISCO REAL COM O LOTE FINAL (v1.2.27 - 30/10/2026)
   //==================================================
   // P0.3: o cap de `MaxRiskPerTradeUsd` da v1.2.26 vive DENTRO de
   // CalculateDynamicLot, ANTES do arredondamento por step e do FORCAR LOTE
   // MINIMO. Duas consequencias medidas em 30/10/2026:
   //   1) nenhuma linha "LOT CAP REAL" apareceu no backtest de 3 meses -
   //      o cap nunca foi provado, apenas existia no codigo;
   //   2) quando o lote cai no minimo do simbolo o risco VOLTA a subir sem
   //      ninguem recalcular nada (era o caso do aviso FORCA LOTE MINIMO).
   // Aqui o risco e medido com o LOTE FINAL e com a distancia que o stop
   // realmente usa: 1R da armadura na entrada sem stop, ou o SL de verdade
   // quando a entrada leva stop. Toda ordem passa a declarar o proprio risco
   // em USD ANTES do envio - numero, nao confianca.
   double oneRDist = NoiseDistancePointsForRisk(symbol);

   if(!EnableStoplessEntry && slRefPts > 0)
      oneRDist = (double)slRefPts;

   if(MaxRiskPerTradeUsd > 0.0 && oneRDist > 0.0)
   {
      double perLot1R = RiscoEmDinheiroDaOrdem(symbol, 1.0, oneRDist);

      if(perLot1R > 0.0)
      {
         double riscoFinal = perLot1R * lot;
         string ajuste     = "DENTRO_DO_TETO";

         if(riscoFinal > MaxRiskPerTradeUsd * 1.02)
         {
            double capLot = MaxRiskPerTradeUsd / perLot1R;
            double stepL  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
            double minL   = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);

            if(stepL <= 0.0)
               stepL = minL;

            if(stepL > 0.0)
               capLot = MathFloor(capLot / stepL + 1e-8) * stepL;

            if(capLot > 0.0 && capLot >= minL - 1e-8)
            {
               PrintFormat("[RISK] TETO REAL APLICADO | %s | lote %.3f -> %.3f | R=%.0f pts | risco %.2f -> %.2f USD | teto %.2f USD",
                           symbol, lot, capLot, oneRDist, riscoFinal,
                           capLot * perLot1R, MaxRiskPerTradeUsd);

               lot        = capLot;
               riscoFinal = lot * perLot1R;
               ajuste     = "REDUZIDO";
            }
            else
            {
               // Nem o lote MINIMO cabe no teto. Decidir, nao avisar (P1.4).
               if(RealGuardBlockOnMinLot())
               {
                  PrintFormat("[RISK] MIN_LOT_EXCEEDS_RISK_CAP | %s | lote minimo %.3f | R=%.0f pts | risco %.2f USD > teto %.2f USD | entrada BLOQUEADA",
                              symbol, minL, oneRDist, minL * perLot1R, MaxRiskPerTradeUsd);

                  EventTradeRejected(symbol,
                                     "risco do lote minimo excede o teto por operacao",
                                     "MIN_LOT_EXCEEDS_RISK_CAP");
                  return false;
               }

               PrintFormat("[RISK] MIN_LOT_EXCEEDS_RISK_CAP | %s | lote minimo %.3f | R=%.0f pts | risco %.2f USD > teto %.2f USD | liberado (BlockWhenMinLotExceedsRiskCap=false)",
                           symbol, minL, oneRDist, minL * perLot1R, MaxRiskPerTradeUsd);

               ajuste = "MIN_LOT_LIBERADO";
            }
         }

         // v1.2.58 (P1.35): o desfecho era ajuste|riscoFinal e o risco muda a
         // cada candidato, por isso o portao nunca via repeticao. MEDIDO no
         // journal do backtest (5 120 234 linhas): 179 619 linhas desta
         // mensagem. O desfecho passou a ser o AJUSTE (estado pequeno e
         // estavel) e o risco continua a sair no texto.
         if(DiagGateAllow(symbol, "RISCO_REAL", ajuste, 14400))
         PrintFormat("[RISK] RISCO REAL DA ORDEM | %s | %s | lote=%.3f | R=%.0f pts | risco=%.2f USD | teto=%.2f USD | %.1f%% do teto",
                     symbol, ajuste, lot, oneRDist, riscoFinal, MaxRiskPerTradeUsd,
                     (MaxRiskPerTradeUsd > 0.0 ? 100.0 * riscoFinal / MaxRiskPerTradeUsd : 0.0));
      }
   }

   // NOTICIA exige conviccao ACIMA DA METADE e tendencia clara: em evento o
   // mercado engana duas vezes (spike e retorno). Sem as duas leituras, o EA
   // fica de fora em vez de adivinhar.
   if(emNoticia && NewsTradeMode != NEWS_TRADE_FULL)
   {
      if(newsMinConf > 0.0 && aiConfidence < newsMinConf)
      {
         Print("[TRADE] BLOQUEADA | ", symbol,
               " | noticia sem conviccao | Conf=", DoubleToString(aiConfidence, 1),
               " < ", DoubleToString(newsMinConf, 1));
         EventTradeRejected(symbol, "noticia sem conviccao minima", "NEWS_CONFIDENCE");
         return false;
      }

      // v1.2.97 (03/11/2026) - P1.86: ADX AUSENTE nao e tendencia fraca.
      // Indicators/ADX.mqh devolve -1.0 como sentinel "sem leitura" e o resto
      // do EA trata esse caso como neutro (fail-open). Este gate era o unico
      // ponto que convertia a AUSENCIA de dado em veto PERMANENTE: medido em
      // 02/11 23:20 (v1.2.93), XAUUSD era rejeitado 3x/minuto com
      // "ADX=-1.0 < 35.0" durante as 5 h que antecederam um evento de calendario.
      // Regra nova: so veta quando existe leitura E ela e fraca.
      double newsADXMin = (NewsTrendMinADX > 0.0 ? NewsTrendMinADX : DynADXClear);
      // v1.2.98 (03/11/2026) - P1.89: NewsTrendMinADX (18.0) substitui o piso
      // de tendencia clara (35.0) neste veto: ouro vive entre ADX 18 e 30.
         if(NewsTradeTrendOnly && adxNow > 0.0 && adxNow < newsADXMin)
         {
         if(DiagGateAllow(symbol, "NEWS_NO_TREND", "FRACO", 1800))
         Print("[TRADE] BLOQUEADA | ", symbol,
               " | noticia sem tendencia clara | ADX=", DoubleToString(adxNow, 1),
               " < ", DoubleToString(newsADXMin, 1));
         EventTradeRejected(symbol, "noticia sem tendencia clara", "NEWS_NO_TREND");
         return false;
      }
   }

   //------------------------------------------------
   // DELEGAR PARA SMART EXECUTION
   //------------------------------------------------

   ExecRequest req;
   req.symbol  = symbol;
   req.volume  = lot;
   req.magic   = MagicNumber;
   req.comment = TradeComment;
   req.sl      = 0.0;   // entrada sem stop: SL e armado depois, no lucro
   req.tp      = 0.0;

   // Calcular preco de entrada
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(point <= 0.0)
      point = _Point;

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   //----------------------------------------------
   // Distancias de SL/TP: em DINHEIRO quando pedido, em PONTOS senao
   //----------------------------------------------
   // MEDIDO 08/10/2026 na conta 391773676: `StopLossPoints=300` valia US$ 3,00
   // no GOLD e US$ 3,00 no EURUSD, US$ 20 no USDJPY e US$ 0,03 no BTCUSD.
   // Um numero so, quatro riscos diferentes — e US$ 3,00 contra um orcamento
   // diario de US$ 0,61. Decisao do dono: risco por operacao em DOLARES, com
   // alvo simetrico. A formula mora em `DistanciaPontosParaRiscoUSD`.
   //
   // Se a distancia em dinheiro nao pode ser calculada (falta point ou
   // contrato), cai nos inputs em PONTOS em vez de mandar ordem sem
   // protecao. Zero aqui e "nao sei", e "nao sei" tem saida.
   double slPontos = (double)StopLossPoints;
   double tpPontos = (double)TakeProfitPoints;

   // ALVO VARIAVEL (29/10/2026): multiplo da distancia de referencia pela nota
   // de conviccao. Alvo curto na duvida, longo na certeza.
   if(EnableAdaptiveTargets)
   {
      tpPontos = slBase * TargetFactorForGrade(conviction);

      // v1.2.21: o cenario tambem define a AMPLITUDE do alvo. Em disparada o
      // preco percorre mais (alvo x1.15) e em lateral ele volta (x0.90). O
      // resultado continua limitado por MinTargetPoints/MaxTargetPoints
      // logo abaixo.
      double cenarioAlvo = ScenarioTargetFactor(symbol);

      if(cenarioAlvo > 0.0 && MathAbs(cenarioAlvo - 1.0) > 0.0001)
         tpPontos *= cenarioAlvo;

      // Noticia abre o alvo: o evento entrega mais amplitude que o normal.
      if(newsTPMult > 1.0)
         tpPontos *= newsTPMult;

      if(tpPontos < (double)MinTargetPoints)
         tpPontos = (double)MinTargetPoints;

      if(MaxTargetPoints > 0 && tpPontos > (double)MaxTargetPoints)
         tpPontos = (double)MaxTargetPoints;
   }

   // ENVELOPE DE RISCO (29/10/2026): RiscoPorTradeUsd() devolve 0 quando a soma
   // do risco das posicoes abertas ja atingiu MaxTotalRiskPercent. Entrada
   // recusada com motivo, em vez de stop calculado com risco inexistente.
   double riscoTrade = RiscoPorTradeUsd();

   if(riscoTrade <= 0.0)
   {
      Print("[TRADE] BLOQUEADA | ", symbol,
            " | envelope de risco aberto cheio | MaxTotalRiskPercent=",
            DoubleToString(MaxTotalRiskPercent, 2),
            " | aberto=", DoubleToString(RiscoAbertoUSD(), 2),
            " | saldo=", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
            " | teto_usd=", DoubleToString(MaxTotalRiskOpenUsd, 2));
      EventTradeRejected(symbol, "envelope de risco aberto cheio", "RISK_ENVELOPE_FULL");
      return false;
   }

   if(riscoTrade > 0.0)
   {
      // 29/10/2026: o LOTE ja foi dimensionado por CalculateLotByRiskAuto para
      // que ESTA distancia (StopLossPoints) valha RiskPerTradeUsd. Deduzir a
      // distancia de volta do lote (risco/lote) devolvia 5 pontos quando o lote
      // era 0,41 - stop de 0,5 pip, dentro do spread.
      double slUSD = slBase;

      // MEDIDO 23/10/2026: quando a distancia em dinheiro nao podia ser
      // calculada, este bloco caia CALADO para os pontos do input. O risco
      // configurado deixava de valer sem ninguem saber. "Nao sei" tem saida:
      // bloqueia e diz o motivo.
      if(slUSD <= 0.0)
      {
         Print("[TRADE] BLOQUEADA | ", symbol,
               " | risco em US$ configurado mas a distancia em pontos nao pode ser calculada",
               " | tick_value=", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE), 5),
               " | tick_size=", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE), 5),
               " | point=", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_POINT), 5));
         EventTradeRejected(symbol, "distancia de risco nao calculavel", "RISK_DISTANCE_UNKNOWN");
         return false;
      }

      slPontos = slUSD;

      // O alvo NAO sai mais de RewardRatio fixo: com EnableAdaptiveTargets
      // ele ja veio calculado pela nota de conviccao, acima.
      if(!EnableAdaptiveTargets)
         tpPontos = slPontos * RewardRatio;

      if(tpPontos <= 0.0)
         tpPontos = 0.0;
   }

   //------------------------------------------------
   // ENTRADA SEM STOP (29/10/2026)
   //------------------------------------------------
   // slRefPontos e a distancia usada para DIMENSIONAR o lote e para cobrar o
   // orcamento do dia. Com EnableStoplessEntry o SL nao vai na ordem: ele e
   // armado depois, quando o preco andar a favor (Management/BreakEven.mqh).
   if(MinRewardRatio>0.0 && slPontos>0.0)
   {
      double alvoMinimo=slPontos*MinRewardRatio;

      if(tpPontos<alvoMinimo)
      {
         // v1.2.51 (P1.27): medido em 31/10/2026 no journal do tester: 58 310
         // linhas desta mensagem num unico run (1,39% do output) e sem portao
         // nenhum. O desfecho e TP|alvo, a mesma forma que o RR_ENTRADA ja
         // usava; enquanto o stop nao muda, o alvo calculado tambem nao.
         // v1.2.58 (P1.35): o desfecho era tp|alvoMinimo, ambos recalculados
         // por candidato (nota de conviccao e cenario), por isso o portao
         // nunca abafava. MEDIDO: 147 612 linhas no journal do backtest.
         // Desfecho estavel "ALVO_MIN"; os pontos continuam no texto.
         if(DiagGateAllow(symbol, "ALVO_RR", "ALVO_MIN", 14400))
            Print("[RISK] alvo elevado para respeitar o RR minimo | ",symbol,
                  " | RR_min=",DoubleToString(MinRewardRatio,2),
                  " | TP=",DoubleToString(tpPontos,0)," -> ",DoubleToString(alvoMinimo,0)," pts");

         tpPontos=alvoMinimo;
      }
   }

   double slRefPontos = slPontos;

   if(EnableStoplessEntry)
   {
      slPontos = 0.0;
      if(DiagGateAllow(symbol, "SEM_STOP",
               DoubleToString(tpPontos, 0) + "|" + DoubleToString(slRefPontos, 0), 14400))
      Print("EXECUTION: SEM STOP NA ENTRADA | ", symbol,
            " | risco de referencia=", DoubleToString(slRefPontos, 0), " pts",
            " | alvo=", DoubleToString(tpPontos, 0), " pts");
   }

   if(signal == 1) // BUY
   {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(symbol, SYMBOL_ASK);

      if(slPontos > 0.0)
         req.sl = NormalizeDouble(req.price - (slPontos * point), digits);

      if(tpPontos > 0.0)
         req.tp = NormalizeDouble(req.price + (tpPontos * point), digits);
   }
   else if(signal == -1) // SELL
   {
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(symbol, SYMBOL_BID);

      if(slPontos > 0.0)
         req.sl = NormalizeDouble(req.price + (slPontos * point), digits);

      if(tpPontos > 0.0)
         req.tp = NormalizeDouble(req.price - (tpPontos * point), digits);
   }
   else
   {
      return false;
   }

   //==================================================
   // v1.2.25 - TRAVA DE CUSTO (spread + comissao) vs ALVO
   //--------------------------------------------------
   // Roda depois de lote, alvo e risco de referencia ja estarem definidos e
   // ANTES de qualquer envio. Se o custo come mais que `MaxCostPctOfTarget`
   // do alvo, a entrada e recusada com o numero na cara - nao com um generico
   // "spread alto".
   string motivoCusto = "";

   if(!CostGateCheck(symbol, lot, tpPontos,
                     (slRefPontos > 0.0 ? slRefPontos : slPontos), motivoCusto))
   {
      // v1.2.54 (31/10/2026) - P1.31: esta linha repetia, sem o detalhe, o que o
      // CostGate acabara de imprimir ([COST] BLOQUEADO com o MESMO motivo) - o
      // mesmo evento duas vezes, 78 606 pares no ultimo run (12,2% do output).
      // O desfecho por simbolo passa a 1 linha por 4 h. A rejeicao em si nao
      // mudou: EventTradeRejected e o return false continuam a acontecer sempre.
      if(DiagGateAllow(symbol, "CUSTO_BLOQ", "BLOQUEADO", 14400))
         Print("EXECUTION: CUSTO BLOQUEADO | ", symbol, " | ", motivoCusto);
      EventTradeRejected(symbol, motivoCusto, "COST_TOO_HIGH");
      return false;
   }

   // RISCO EM DINHEIRO x ORCAMENTO DO DIA (23/10/2026)
   //==================================================
   // O risco desta entrada e comparado com o orcamento que o proprio sistema
   // usa para parar (`MaxDailyLossPercent` do saldo). Sem esta comparacao, um
   // `RiskPerTradeUsd` maior que o orcamento faz UMA operacao estourar o dia.
   // Com entrada sem stop o risco continua medido pela distancia de REFERENCIA,
   // senao o orcamento do dia viraria uma comparacao com zero.
   double riscoUSD = RiscoEmDinheiroDaOrdem(symbol, lot,
                       (slRefPontos > 0.0 ? slRefPontos : slPontos));
   string motivoOrcamento = "";

   if(!RiscoCabeNoOrcamento(riscoUSD, motivoOrcamento))
   {
      Print("EXECUTION: RISCO BLOQUEADO | ", symbol, " | ", motivoOrcamento);
      EventRiskBlock(symbol, motivoOrcamento);
      return false;
   }

   //==================================================
   //==================================================
   // RISCO PEDIDO x RISCO EFETIVO (29/10/2026)
   //==================================================
   // `RiscoPorTradeUsd()` e o risco que o input pede. `riscoUSD` e o risco
   // que a ordem REALMENTE carrega com o lote e o stop escolhidos. Os dois
   // divergem quando o lote cai no minimo do simbolo: o risco real passa a
   // ser o do lote minimo, nao o do input. Aqui a divergencia fica visivel
   // em vez de silenciosa.
   double riscoPedido=RiscoPorTradeUsd();

   if(riscoPedido>0.0 && riscoUSD>0.0)
   {
      double fatorRisco=riscoUSD/riscoPedido;

      if(fatorRisco>=EffectiveRiskWarnFactor)
         if(DiagGateAllow(symbol, "RISK_EFETIVO",
                  DoubleToString(riscoUSD, 2) + "|" + DoubleToString(lot, 3), 14400))
         Print("[RISK] risco EFETIVO acima do pedido | ",symbol,
               " | pedido=",DoubleToString(riscoPedido,2),
               " | efetivo=",DoubleToString(riscoUSD,2),
               " | fator=",DoubleToString(fatorRisco,2),
               " | lot=",DoubleToString(lot,3),
               " | stop=",DoubleToString(slRefPontos,0)," pts",
               " | ajuste RiskPerTradePercent/StopLossPoints se nao for isso");
   }

   // RR realizado desta entrada (alvo / stop de referencia)
   if(slRefPontos>0.0 && tpPontos>0.0)
      if(DiagGateAllow(symbol, "RR_ENTRADA",
               DoubleToString(slRefPontos, 0) + "|" + DoubleToString(tpPontos, 0), 14400))
      Print("[RISK] RR da entrada | ",symbol,
            " | TP=",DoubleToString(tpPontos,0)," pts",
            " | SL=",DoubleToString(slRefPontos,0)," pts",
            " | RR=",DoubleToString(tpPontos/slRefPontos,2));

   // STOP LOSS OBRIGATORIO (05/10/2026)
   //==================================================
   // MEDIDO na conta real 391773676: posicao aberta no MT5 com `sl = 0.0`
   // e TP 86.584,30. Sem protecao, uma queda de 2% no BTCUSD levava o
   // equity de 11,63 para -5,65 — STOP OUT, nao apenas perda.
   //
   // As linhas acima so calculam o SL quando `StopLossPoints > 0`. Com zero,
   // `req.sl` fica 0.0 e a ordem SAI MESMO ASSIM. O backend ja recusava
   // ("Stop Loss calculou zero", `auto_engine.py`); o EA nao recusava.
   // Essa era a diferenca entre os dois caminhos de ordem.
   //
   // A ordem do teste importa: `req.sl <= 0` cobre os dois casos, o SL
   // desligado E o SL calculado em zero por falta de espaco de preco.
   if(RequireStopLoss && req.sl <= 0.0 && !EnableStoplessEntry)
     {
      Print("[TRADE] BLOQUEADA | ", symbol,
            " | stop loss obrigatorio e o SL calculado e ",
            DoubleToString(req.sl, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)),
            " | ative StopLossPoints>0 ou desmarque RequireStopLoss");
      return false;
     }

   if(req.price <= 0.0)
   {
      Print("EXECUTION: PRECO INVALIDO | ", symbol);
      EventTradeRejected(symbol, "preco de entrada invalido", "INVALID_PRICE");
      return false;
   }

   //------------------------------------------------
   // v1.4.0 (Etapa 4): simulacao
   StateSet(symbol, STATE_SIMULATING);

   // SIMULATION - Pre-execucao
   // Avalia a operacao antes de envia-la ao broker.
   // Fase de SIMULATION do pipeline v1.2.0.
   //------------------------------------------------
   CSimulationEngine::Init();   // idempotente

   // A simulacao mede risco/recompensa. Numa entrada sem stop ela recebe a
   // distancia de REFERENCIA, senao RR = 0 e toda entrada seria reprovada.
   //
   // v1.2.16 - O R DA SIMULACAO NUMA ENTRADA SEM STOP E A ARMADURA
   // ---------------------------------------------------------------
   // MEDIDO no Strategy Tester em 29/10/2026 (XAUUSD M15):
   //   EXECUTION: SIMULACAO BLOQUEADA | Razao=Low expected profit | Prob=0.66 | RR=0.50
   // em praticamente todo sinal. A causa era a escala: com entrada sem stop a
   // simulacao recebia `StopLossPoints` (300 pts) como risco, mas o stop REAL
   // desta estrategia nasce na ARMADURA (ATR x StoplessArmATRMult, piso
   // StoplessArmMinPoints) - bem mais perto que 300 pts. Comparar um alvo de
   // 150 pts contra um risco de 300 pts da RR 0,50 e, com probabilidade 0,66,
   // EP = 0,66*0,50 - 0,34 = -0,01: reprovado por aritmetica, nunca por
   // qualidade do sinal.
   //
   // Com `EnableStoplessEntry`, o R usado aqui passa a ser a distancia em que
   // a operacao VIRA ZERO A ZERO. Nunca maior que a referencia: o envelope de
   // risco continua mandando.
   double slRefSim = slRefPontos;

   if(EnableStoplessEntry && slRefPontos > 0.0)
     {
      double atrArm = GetATR(symbol);
      double armPts = (atrArm > 0.0) ? (atrArm * StoplessArmATRMult / point) : 0.0;

      if(armPts < (double)StoplessArmMinPoints)
         armPts = (double)StoplessArmMinPoints;

      if(armPts > 0.0 && armPts < slRefSim)
         slRefSim = armPts;
     }

   double slSimulacao = req.sl;

   if(slSimulacao <= 0.0 && slRefSim > 0.0)
      slSimulacao = NormalizeDouble(
         (signal == 1) ? (req.price - slRefSim * point)
                       : (req.price + slRefSim * point), digits);

   SimulationResult simResult =
      CSimulationEngine::Evaluate(
         symbol,
         req.type,
         lot,
         req.price,
         slSimulacao,
         req.tp,
         aiConfidence
      );

   if(!CSimulationEngine::ShouldExecute(simResult))
   {
      if(DiagGateAllow(symbol, "SIM_BLOCK",
               simResult.reason + "|" + DoubleToString(simResult.probability_success, 2) + "|" + DoubleToString(simResult.risk_reward, 2), 3600))
      Print(
         "EXECUTION: SIMULACAO BLOQUEADA | ",
         symbol,
         " | Signal=",
         signal,
         " | Razao=",
         simResult.reason,
         " | Prob=",
         DoubleToString(simResult.probability_success,2),
         " | RR=",
         DoubleToString(simResult.risk_reward,2),
         " | R_sim=",
         DoubleToString(slRefSim,0),
         " pts"
      );

      EventTradeRejected(symbol, simResult.reason, "SIM_BLOCKED");

      return false;
   }

   Print(
      "EXECUTION: SIMULACAO APROVADA | ",
      symbol,
      " | Prob=",
      DoubleToString(simResult.probability_success,2),
      " | RR=",
      DoubleToString(simResult.risk_reward,2)
   );
   // v1.4.0 (Etapa 4): pronto para executar
   StateSet(symbol, STATE_EXECUTION_READY);

   //--------------------------------------------------
   // PORTAO FINAL DO SIMBOLO (v1.2.65 - P1.51)
   //--------------------------------------------------
   // MEDIDO em 02/11/2026 sobre 104 ficheiros .mq5/.mqh: a ValidateSymbol de
   // Core\SymbolValidator.mqh tinha 1 definicao e ZERO chamadas. O simbolo
   // nunca era perguntado se estava sincronizado (lacuna 1 da secao 45), se a
   // sessao aceitava ordens, nem se ask/bid eram cotacoes reais: o lote era
   // validado inline e o resto ficava para o broker recusar sem explicacao.
   // Toda a entrada passa a ser filtrada AQUI, com motivo escrito no journal.
   string symbolReject = "";
   double slGuardPts   = (slRefPts > 0 ? (double)slRefPts : 0.0);

   if(!ValidateSymbol(symbol, lot, slGuardPts, symbolReject))
   {
      Print("EXECUTION BLOCK | SYMBOL | ", symbol,
            " | Lot=", DoubleToString(lot, 3),
            " | SL=", DoubleToString(slGuardPts, 0),
            " | Motivo=", symbolReject);

      EventTradeRejected(symbol,
                         "simbolo reprovado na validacao final: " + symbolReject,
                         "SYMBOL_INVALID");
      return false;
   }
   ulong ticket = 0;
   ExecResult execResult = CSmartExecution::OpenPosition(req, ticket);

   if(execResult == EXEC_SUCCESS)
   {
      RegisterTrade();
      RegisterDailyTrade();
      CTelemetry::RecordTradeOpen();   // ETAPA 15.6.3: contador real

      EventTradeApproved(symbol,
                         (signal == 1 ? "BUY" : "SELL"),
                         DoubleToString(lot, 2));

      // v1.4.0 (Etapa 4): executando
      StateSet(symbol, STATE_EXECUTING);

      Print(
         "TRADE EXECUTADO | ",
         symbol,
         " | SIGNAL=",
         signal,
         " | LOT=",
         DoubleToString(lot,2),
         " | Ticket=",
         IntegerToString(ticket)
      );

      return true;
   }
   else
   {
      // O `retcode` e o unico campo que diz POR QUE o broker recusou. Sem
      // ele, os 4.246 BROKER_ERROR do forward test tinham uma unica mensagem
      // ("Erro de broker") e a taxa de 3,4 erros por ciclo nao era
      // diagnosticavel: sabia-se que falhou, nunca por que.
      //
      // Os dois codigos sao necessarios e significam coisas diferentes:
      // `retcode` vem do SERVIDOR do broker (10004 = requote, 10006 =
      // rejeitado) e `GetLastError()` vem da API local (134 = sem margem,
      // 4108 = ordem invalida). O servidor pode recusar por politica
      // enquanto a API estava correta.
      //
      // COMO PEGAR O retcode (03/10/2026)
      // ----------------------------------
      // `OrderSendResult()` NAO EXISTE em MQL5 — nao e funcao da linguagem e
      // nao de `Trade.mqh`. A linha `uint erroBroker = (uint)OrderSendResult();`
      // foi introduzida no commit dbdce10 e nunca compilou:
      //
      //   ExecutionEngine.mqh(278,31) : error 256: undeclared identifier 'OrderSendResult'
      //   Result: 2 errors, 3 warnings
      //
      // Nao havia `.ex5` no repositorio para revelar isso: o EA estava
      // quebrado desde entao e a suite Python nao compila MQL5.
      //
      // A forma correta neste ponto do codigo e `GetLastError()`. O
      // `MqlTradeResult` com o `retcode` do servidor vive dentro de
      // `CSmartExecution::ExecuteOrder`, que e `private`; o `ExecResult`
      // devolvido por `OpenPosition` aqui e um enum local que nao carrega o
      // retcode. Entao este ponto registra o codigo da API, que e 134 =
      // "Not enough money" — exatamente o `EXEC_NO_MARGIN` medido.
      int  erroApi = GetLastError();

      // O `EXEC_NO_MARGIN` mapeia para o erro 134 da API do MT5
      // (TRADE_RETCODE_ERROR / ERROR_TRADE_NOT_ENOUGH_MONEY). Traduzir aqui
      // deixa o log do broker legivel sem inventar um retcode de servidor.
      string causaBroker;
      if(execResult == EXEC_NO_MARGIN)
         causaBroker = StringFormat(
            "margem insuficiente (erro_api=%d, sem_margem=%d)",
            erroApi, 134);
      else if(execResult == EXEC_SPREAD_TOO_HIGH)
         causaBroker = StringFormat("spread alto demais (erro_api=%d)", erroApi);
      else
         causaBroker = StringFormat("erro_api=%d", erroApi);

      string motivo = causaBroker;

      Print(
         "ERRO EXECUCAO | ",
         symbol,
         " | Signal=",
         signal,
         " | Result=",
         EnumToString(execResult),
         " | CAUSA=",
         motivo,
         " | ERRO_API=",
         erroApi
      );

      // A causa vai no campo `reason`, que e o que o log e a tela leem. Era
      // aqui que a informacao se perdia: o evento saia com o motivo vazio
      // e o forward test so conseguia contar falhas, nunca explica-las.
      EventBrokerError(EnumToString(execResult) + " | " + motivo);

      return false;
   }
}

//==================================================
// COMPATIBILIDADE
//==================================================

bool ExecuteTrade(int signal)
{
   return ExecuteTrade(
      _Symbol,
      signal
   );
}

#endif
