// XAU_AI_PRO v1.2.0 - RISK CENTER (ETAPA 15.5)
#ifndef RISKCENTER_MQH
#define RISKCENTER_MQH

#include "../Core/Config.mqh"
#include "../Core/RiskHub.mqh"
#include "../Management/DailyRisk.mqh"
#include "../Enterprise/SafetyManager.mqh"

//==================================================
// RISK CONTROL CENTER
//
// FACHADA UNICA de decisao de risco para NOVAS
// ENTRADAS. Consolida as checagens espalhadas em
// uma ordem deterministica e retorna SEMPRE o
// PRIMEIRO motivo de bloqueio (rastreavel).
//
// Principios:
// 1. GetDrawdownPercent() (RiskHub) e a UNICA
//    fonte de drawdown do sistema.
// 2. Nenhuma regra duplicada: cada limite tem um
//    unico ponto de verificacao aqui.
// 3. Falha de leitura -> fail-closed (bloqueia).
// 4. Gestao de posicoes abertas NAO passa por
//    aqui (apenas novas entradas).
//
// Uso:
//    string reason="";
//    if(!RiskAllowEntry(symbol, reason))
//       Print("RISK BLOCK | ", reason);
//==================================================

//--------------------------------------------------
// RESULTADO DETALHADO (para observabilidade)
//--------------------------------------------------
struct RiskDecision
{
   bool   allowed;
   string reason;        // "" quando permitido
   double drawdown_pct;
   int    trades_today;
   double daily_loss_pct;
   double free_margin;
};

double RC_DailyLossPercent()
{
   double startBal = RiskHubGet("STARTBAL", 0.0);
   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);

   if(startBal <= 0.0 || balance < 0.0)
      return 0.0;

   double loss = (startBal - balance) / startBal * 100.0;
   return MathMax(loss, 0.0);
}

//--------------------------------------------------
// DECISAO COMPLETA (ordem deterministica)
//--------------------------------------------------

RiskDecision RiskEvaluate(string symbol)
{
   RiskDecision d;
   d.allowed       = false;
   d.reason        = "";
   d.drawdown_pct  = GetDrawdownPercent();
   d.trades_today  = GetDailyTradesCount();
   d.daily_loss_pct= RC_DailyLossPercent();
   d.free_margin   = AccountInfoDouble(ACCOUNT_MARGIN_FREE);

   //------------------------------------------------
   // 1. PERDA DIARIA (stop loss do dia)
   //------------------------------------------------
   if(!CSafetyManager::CheckDailyLoss())
   {
      d.reason="DAILY_LOSS";
      return d;
   }

   //------------------------------------------------
   // 2. DRAWDOWN DIARIO (vs peak - fonte unica)
   //------------------------------------------------
   if(!CSafetyManager::CheckDailyDrawdown())
   {
      d.reason="DAILY_DRAWDOWN";
      return d;
   }

   //------------------------------------------------
   // 3. NUMERO DE OPERACOES DO DIA
   //------------------------------------------------
   if(!CSafetyManager::CheckDailyTrades())
   {
      d.reason="MAX_TRADES_PER_DAY";
      return d;
   }

   //------------------------------------------------
   // 4. MARGEM LIVRE MINIMA
   //------------------------------------------------
   if(!CSafetyManager::CheckFreeMargin())
   {
      d.reason="FREE_MARGIN";
      return d;
   }

   //------------------------------------------------
   // 5. EXPOSICAO TOTAL
   //------------------------------------------------
   if(!CSafetyManager::CheckTotalExposure())
   {
      d.reason="TOTAL_EXPOSURE";
      return d;
   }

   d.allowed=true;
   return d;
}

//--------------------------------------------------
// GATE SIMPLIFICADO (compativel com fluxo atual)
//--------------------------------------------------

bool RiskAllowEntry(string symbol, string &reason)
{
   RiskDecision d=RiskEvaluate(symbol);
   reason=d.reason;
   return d.allowed;
}

//--------------------------------------------------
// SUMMARY PARA OBSERVABILIDADE / APP
//--------------------------------------------------

string RiskCenterSummary()
{
   RiskDecision d=RiskEvaluate("");

   return StringFormat(
      "[RISKCENTER] DD=%.2f%% | Trades=%d | LossDia=%.2f%% | FreeMargin=%.2f | %s",
      d.drawdown_pct,
      d.trades_today,
      d.daily_loss_pct,
      d.free_margin,
      (d.allowed ? "OPEN" : "BLOCKED:" + d.reason)
   );
}

#endif // RISKCENTER_MQH