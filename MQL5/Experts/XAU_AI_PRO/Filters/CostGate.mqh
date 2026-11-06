//+------------------------------------------------------------------+
//| CostGate.mqh                                                     |
//| Trava de CUSTO por operacao: spread + comissao vs alvo em US$    |
//| XAU_AI_PRO v1.2.25                                               |
//+------------------------------------------------------------------+

#ifndef COST_GATE_MQH
#define COST_GATE_MQH

#include "../Core/Config.mqh"
#include "../Monitoring/DiagGate.mqh"

//==================================================
// POR QUE ESTE MODULO EXISTE (v1.2.25)
//==================================================
// PESQUISA em 29/10/2026 (indice publico MQL5, artigos em portugues):
//   "Gerenciador de riscos para trading algoritmico" (artigo 14634,
//   Aleksandr Seredin) trata de normalizacao de risco, INTERFACE PARA STOP
//   CURTO, CONTROLE DE SLIPPAGE em ordens abertas e CONTROLE DE SPREAD na
//   abertura de posicoes. A licao util para este projeto e a comparacao:
//   custo de entrada medido CONTRA o resultado esperado da operacao.
//
// O QUE O PROJETO JA TINHA
// ------------------------
// `MaxSpreadPct = 0.6` limita o spread como PORCENTAGEM DO PRECO. Isso impede
// spread absurdo, mas nao responde a pergunta que decide se a operacao vale a
// pena: "quanto do meu alvo o custo vai comer?".
//
// MEDIDO no desenho desta versao com os numeros reais da conta:
//   - alvo tipico desta conta: LadderTpUsd = 10 USD (escada em dolares, v1.2.69);
//   - lote minimo de um exotico como USDRUB: 1.0;
//   - spread normal de exotico em abertura de sessao: ~150-300 pontos.
// Em simbolo assim o custo de ida e volta pode passar de 5 USD, ou seja 25%
// do alvo de 20 USD - a operacao precisa acertar MAIS que o normal so para
// empatar. Nada no projeto media isso. `MaxSpreadPct` de 0,6% aprovava.
//
// O QUE ESTE MODULO FAZ
// ---------------------
// Converte spread e comissao em DOLARES usando tick size / tick value (a
// mesma matematica ja usada em Management/MoneyLadder.mqh) e compara com:
//   - o ALVO da entrada, em dolares  -> MaxCostPctOfTarget;
//   - o RISCO da entrada, em dolares -> MaxCostPctOfRisk (opcional).
//
// Nao e filtro de preco, e filtro de ECONOMIA: a mesma entrada com o mesmo
// sinal pode ser boa no ouro e ruim num exotico de spread largo.
//
// O QUE ESTE MODULO NAO FAZ
// -------------------------
// - Nao inclui SWAP. Swap e custo de POSICAO (depende de quantas noites), nao
//   de entrada, e a escada em dolares fecha no mesmo dia na maioria dos casos.
// - Nao mexe em lote nem em alvo. So aprova ou recusa, com motivo medido.
// - Sem leitura de spread (simbolo sem tick) ele NAO bloqueia: "sem tick" nao
//   e evidencia de custo alto, e o preco de entrada invalido ja barra a ordem
//   logo abaixo em ExecutionEngine.
//==================================================

#define COST_LOG_MAX_SIMBOLOS 64

string   g_costLogSimbolo[COST_LOG_MAX_SIMBOLOS];
datetime g_costLogQuando[COST_LOG_MAX_SIMBOLOS];
int      g_costLogQuantos = 0;

//==================================================
// THROTTLE DO DIAGNOSTICO
//==================================================
// Uma linha por simbolo a cada `CostGateLogSec`. O gate roda em toda tentativa
// de entrada; sem throttle o journal viraria uma parede de [COST] OK.
//==================================================

bool CostLogAllowed(const string symbol, const int segundos)
{
   if(segundos <= 0)
      return(true);

   datetime agora = TimeCurrent();

   for(int i = 0; i < g_costLogQuantos; i++)
   {
      if(g_costLogSimbolo[i] == symbol)
      {
         if(agora - g_costLogQuando[i] < segundos)
            return(false);

         g_costLogQuando[i] = agora;

         return(true);
      }
   }

   if(g_costLogQuantos >= COST_LOG_MAX_SIMBOLOS)
      return(false);

   g_costLogSimbolo[g_costLogQuantos] = symbol;
   g_costLogQuando[g_costLogQuantos]  = agora;
   g_costLogQuantos++;

   return(true);
}

//==================================================
// SPREAD ATUAL EM PONTOS
//==================================================

double CostSpreadPoints(const string symbol)
{
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double pt  = SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(ask <= 0.0 || bid <= 0.0 || pt <= 0.0)
      return(0.0);

   double pontos = (ask - bid) / pt;

   return(pontos > 0.0 ? pontos : 0.0);
}

//==================================================
// PONTOS -> DOLARES (mesma matematica do MoneyLadder)
//==================================================
// USD = (distancia_em_preco / tick_size) * tick_value * volume
// O `point` do simbolo nao e o `tick_size` em todos os brokers (ex.: ponto
// 0,001 com tick 0,01), por isso a conversao passa por preco antes do tick.
//==================================================

double CostPointsToUsd(const string symbol, const double volume, const double points)
{
   if(volume <= 0.0 || points <= 0.0)
      return(0.0);

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double ts    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tv    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);

   if(tv <= 0.0)
      tv = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   if(point <= 0.0 || ts <= 0.0 || tv <= 0.0)
      return(0.0);

   double distancia = points * point;

   return((distancia / ts) * tv * volume);
}

//==================================================
// DOLARES -> PONTOS (inverso, para dizer o alvo minimo)
//==================================================

double CostUsdToPoints(const string symbol, const double volume, const double usd)
{
   if(volume <= 0.0 || usd <= 0.0)
      return(0.0);

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double ts    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tv    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);

   if(tv <= 0.0)
      tv = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   if(point <= 0.0 || ts <= 0.0 || tv <= 0.0)
      return(0.0);

   double distancia = (usd * ts) / (tv * volume);

   return(distancia / point);
}

//==================================================
// CUSTO DE IDA E VOLTA EM DOLARES
//==================================================
// O spread ja e o custo de entrar e sair pela pior ponta (paga-se ask e
// devolve-se bid). A comissao entra por lote, como cobrada pelo broker.
//==================================================

double CostUsdOfTrade(const string symbol, const double volume)
{
   if(volume <= 0.0)
      return(0.0);

   double spreadUsd = CostPointsToUsd(symbol, volume, CostSpreadPoints(symbol));
   double commUsd   = CommissionPerLotUsd * volume;

   return(spreadUsd + commUsd);
}

//==================================================
// ALVO MINIMO QUE PAGA O CUSTO
//==================================================
// Alvo (em pontos) a partir do qual o custo ja representa no maximo
// `MaxCostPctOfTarget` porcento do alvo. Serve de diagnostico: mostra ao dono
// qual alvo aquele simbolo precisaria para o custo ser aceitavel.
//==================================================

double CostMinViableTargetPoints(const string symbol, const double volume)
{
   double custo = CostUsdOfTrade(symbol, volume);

   if(custo <= 0.0)
      return(0.0);

   double pct = (MaxCostPctOfTarget > 0.0 ? MaxCostPctOfTarget : 20.0);
   double alvoUsd = custo * 100.0 / pct;

   return(CostUsdToPoints(symbol, volume, alvoUsd));
}

//==================================================
// GATE
//==================================================
// `targetPoints` = distancia do alvo da entrada (tpPontos)
// `riskPoints`   = distancia de referencia do risco (slRefPontos)
// Devolve false com `reason` preenchido quando o custo come o alvo demais.
//==================================================

bool CostGateCheck(const string symbol,
                   const double volume,
                   const double targetPoints,
                   const double riskPoints,
                   string &reason)
{
   reason = "";

   if(!EnableCostGate)
      return(true);

   if(symbol == "" || volume <= 0.0)
      return(true);

   double spreadPts = CostSpreadPoints(symbol);

   if(spreadPts <= 0.0)
   {
      // Sem tick nao ha o que medir. Nao e evidencia de custo alto: a ordem
      // sera barrada adiante por preco invalido se realmente nao houver preco.
      if(CostLogAllowed(symbol, CostGateLogSec))
         Print("[COST] sem leitura de spread | ", symbol,
               " | custo nao medido, entrada segue");

      return(true);
   }

   double custo    = CostUsdOfTrade(symbol, volume);
   double alvoUsd  = CostPointsToUsd(symbol, volume, targetPoints);
   double riscoUsd = CostPointsToUsd(symbol, volume, riskPoints);

   if(alvoUsd <= 0.0)
   {
      // Entrada sem alvo definido: nao ha razao alvo/custo para julgar.
      if(CostLogAllowed(symbol, CostGateLogSec))
         Print("[COST] alvo nao medivel | ", symbol,
               " | alvo=", DoubleToString(targetPoints, 0), " pts",
               " | custo=", DoubleToString(custo, 2), " US$ | entrada segue");

      return(true);
   }

   double pctAlvo  = (custo / alvoUsd) * 100.0;
   double pctRisco = (riscoUsd > 0.0 ? (custo / riscoUsd) * 100.0 : 0.0);

   bool bloqueiaAlvo  = (MaxCostPctOfTarget > 0.0 && pctAlvo > MaxCostPctOfTarget);
   bool bloqueiaRisco = (MaxCostPctOfRisk > 0.0 && riscoUsd > 0.0 && pctRisco > MaxCostPctOfRisk);

   if(bloqueiaAlvo || bloqueiaRisco)
   {
      double alvoMin = CostMinViableTargetPoints(symbol, volume);

      string parteRisco = "";

      if(bloqueiaRisco)
         parteRisco = StringFormat(" e %.1f%% do risco (%.2f US$)", pctRisco, riscoUsd);

      reason = StringFormat("custo %.2f US$ = %.1f%% do alvo (%.2f US$)%s | alvo minimo para pagar o custo: %.0f pts",
                            custo, pctAlvo, alvoUsd, parteRisco, alvoMin);

      // v1.2.54 (31/10/2026) - P1.31: este bloqueio e reavaliado a cada passagem
      // e o texto muda a cada tick (custo, percentagem e alvo sao numeros), logo
      // nao pode ser chave de portao. A chave passa a ser o MODO de bloqueio
      // (alvo, risco ou ambos) - um estado pequeno e estavel, o mesmo criterio
      // que o P1.28 usou na VIA RAPIDA, cujo volume tambem varia a cada tick.
      // Medido antes: 64 494 + 14 112 linhas desta forma no ultimo run.
      string modoBloq = (bloqueiaAlvo && bloqueiaRisco ? "ALVO+RISCO"
                                                       : (bloqueiaRisco ? "RISCO" : "ALVO"));

      if(DiagGateAllow(symbol, "COST_BLOCK", modoBloq, 14400))
         Print("[COST] BLOQUEADO | ", symbol, " | ", reason,
               " | lote=", DoubleToString(volume, 3),
               " | spread=", DoubleToString(spreadPts, 1), " pts",
               " | alvo=", DoubleToString(targetPoints, 0), " pts",
               " | limites: alvo ", DoubleToString(MaxCostPctOfTarget, 1), "% / risco ",
               DoubleToString(MaxCostPctOfRisk, 1), "%");

      return(false);
   }

   if(CostLogAllowed(symbol, CostGateLogSec))
      Print("[COST] OK | ", symbol,
            " | custo=", DoubleToString(custo, 2), " US$ = ",
            DoubleToString(pctAlvo, 1), "% do alvo",
            " | spread=", DoubleToString(spreadPts, 1), " pts",
            " | comissao=", DoubleToString(CommissionPerLotUsd * volume, 2), " US$",
            " | alvo=", DoubleToString(targetPoints, 0), " pts");

   return(true);
}

//==================================================
// RESUMO PARA O OPERADOR
//==================================================
// Texto curto do custo atual, sem decidir nada. Usado em diagnostico.
//==================================================

string CostGateSummary(const string symbol, const double volume, const double targetPoints)
{
   if(symbol == "" || volume <= 0.0)
      return("custo: sem dados");

   double custo = CostUsdOfTrade(symbol, volume);
   double alvo  = CostPointsToUsd(symbol, volume, targetPoints);

   if(alvo <= 0.0)
      return(StringFormat("custo: %.2f US$ (alvo nao medivel)", custo));

   return(StringFormat("custo: %.2f US$ = %.1f%% do alvo | alvo minimo %.0f pts",
                       custo, (custo / alvo) * 100.0,
                       CostMinViableTargetPoints(symbol, volume)));
}

#endif
