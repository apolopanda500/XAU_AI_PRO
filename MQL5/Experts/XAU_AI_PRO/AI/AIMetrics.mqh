// XAU_AI_PRO v1.3.1 - ETAPA 7: METRICAS DE IA
// Tracking em memoria de accuracy / precision / recall /
// directional accuracy a partir do LogAIFeedback.
// NAO altera decisao: apenas observabilidade.

#ifndef AIMETRICS_MQH
#define AIMETRICS_MQH

//==================================================
// CONTADORES (por simbolo simples; escala pequena)
//==================================================

int g_aiTotal       = 0;   // total de previsoes avaliadas
int g_aiCorrect     = 0;   // direcao correta (profit>0)
int g_aiWrong       = 0;   // direcao errada (profit<=0)
int g_aiTruePos     = 0;   // previu BUY e ganhou
int g_aiFalsePos    = 0;   // previu BUY e perdeu
int g_aiTrueNeg     = 0;   // previu SELL e ganhou
int g_aiFalseNeg    = 0;   // previu SELL e perdeu

//==================================================
// REGISTRAR RESULTADO (chamado no fechamento)
//==================================================
// signalPrev: sinal que a IA indicou (1 buy / -1 sell)
// profit    : resultado da trade
//==================================================

void AIMetricsRegister(int signalPrev, double profit)
{
   g_aiTotal++;

   bool win = (profit > 0.0);

   if(win)                    g_aiCorrect++;
   else                       g_aiWrong++;

   if(signalPrev == 1)
   {
      if(win) g_aiTruePos++;
      else    g_aiFalsePos++;
   }
   else if(signalPrev == -1)
   {
      if(win) g_aiTrueNeg++;
      else    g_aiFalseNeg++;
   }
}

//==================================================
// ACCURACY (correcao direcional sobre o total)
//==================================================

double AIM_Accuracy()
{
   if(g_aiTotal <= 0) return 0.0;
   return (double)g_aiCorrect / (double)g_aiTotal * 100.0;
}

//==================================================
// PRECISION (das previsoes BUY, quantas venceram)
//==================================================

double AIM_Precision()
{
   int totalPos = g_aiTruePos + g_aiFalsePos;
   if(totalPos <= 0) return 0.0;
   return (double)g_aiTruePos / (double)totalPos * 100.0;
}

//==================================================
// RECALL (dos trades que a IA sinalizou, cobertura)
//==================================================

double AIM_Recall()
{
   int relevant = g_aiTruePos + g_aiFalseNeg;
   if(relevant <= 0) return 0.0;
   return (double)g_aiTruePos / (double)relevant * 100.0;
}

//==================================================
// RESET (por sessao / treino novo)
//==================================================

void AIM_Reset()
{
   g_aiTotal    = 0;
   g_aiCorrect  = 0;
   g_aiWrong    = 0;
   g_aiTruePos  = 0;
   g_aiFalsePos = 0;
   g_aiTrueNeg  = 0;
   g_aiFalseNeg = 0;
}

//==================================================
// SUMMARY (log)
//==================================================

void AIM_LogSummary()
{
   PrintFormat(
     "[AIM] Total=%d | Acc=%.2f%% | Precision=%.2f%% | Recall=%.2f%% | TP=%d FP=%d TN=%d FN=%d",
     g_aiTotal, AIM_Accuracy(), AIM_Precision(), AIM_Recall(),
     g_aiTruePos, g_aiFalsePos, g_aiTrueNeg, g_aiFalseNeg
   );
}

#endif