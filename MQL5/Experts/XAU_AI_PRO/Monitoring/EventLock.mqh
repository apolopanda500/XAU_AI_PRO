//+------------------------------------------------------------------+
//|                                              EventLock.mqh       |
//|                               F4 - Lock global de escrita        |
//|                                            XAU_AI_PRO v1.2.2     |
//+------------------------------------------------------------------+
// F4 - LOCK GLOBAL DE ESCRITA
//
// Serializa a escrita concorrente em arquivos compartilhados do
// terminal (forward_test_events.csv, full_audit.csv, audit_log.csv).
// Usado pelas 11 instancias do EA (1 por grafico/simbolo) e por
// qualquer modulo que grave eventos/auditoria.
//
// Mecanismo: GlobalVariable do terminal + GlobalVariableSetOnCondition
// (CAS atomico) + TTL anti-orfao. O lock NAO e a serializacao em si:
// a serializacao acontece quando o escritor mantem o lock durante
// TODO o ciclo seek->write->flush. Nenhuma outra variavel global.
//
// PRINCIPIO: nunca bloqueia/interrompe a execucao por mais de ~20ms
// (EV_LOCK_RETRIES x 1ms). Se nao conseguir, retorna false e o
// chamador decide (conta drop, nunca corrompe o arquivo).

#ifndef EVENT_LOCK_MQH
#define EVENT_LOCK_MQH

#define EV_LOCK_NAME        "XAI_PRO_EVENT_LOCK"
#define EV_LOCK_TTL_SEC     2
#define EV_LOCK_RETRIES     20

double g_ev_lock_token      = 0.0;   // token desta instancia (0 = livre)
int    g_ev_lock_contention = 0;    // tentativas extras necessarias (contencao)
int    g_ev_lock_timeouts   = 0;    // aquisicoes que falharam (drop / skip)

//--------------------------------------------------
// TOKEN UNICO DESTA INSTANCIA
//--------------------------------------------------
double EventLockBuildToken()
{
   double token = (double)ChartID();
   token += ((double)(GetTickCount() % 1000000)) / 1000000.0;

   if(token <= 0.0)
      token = 1.0 + ((double)(GetTickCount() % 1000000)) / 1000000.0;

   return token;
}

//--------------------------------------------------
// ACQUIRE - CAS atomico + TTL anti-orfao
//--------------------------------------------------
bool EventLockAcquire()
{
   datetime touched = 0;
   double token = EventLockBuildToken();
   g_ev_lock_token = 0.0;

   // Garante existencia da var (idempotente entre instancias)
   if(!GlobalVariableCheck(EV_LOCK_NAME))
      GlobalVariableSet(EV_LOCK_NAME, 0.0);

   for(int attempt = 0; attempt < EV_LOCK_RETRIES; attempt++)
     {
      // Tenta obter o lock (0 -> token unico) de forma atomica
      if(GlobalVariableSetOnCondition(EV_LOCK_NAME, token, 0.0))
        {
         g_ev_lock_token = token;
         if(attempt > 0)
            g_ev_lock_contention++;
         return true;
        }

      // Lock preso por outra instancia: verifica TTL anti-orfao
      double cur = GlobalVariableGet(EV_LOCK_NAME);
      touched = GlobalVariableTime(EV_LOCK_NAME);
      if(cur > 0.0 && touched > 0 && (TimeCurrent() - touched) > EV_LOCK_TTL_SEC)
        {
         if(GlobalVariableSetOnCondition(EV_LOCK_NAME, token, cur))
           {
            g_ev_lock_token = token;
            if(attempt > 0)
               g_ev_lock_contention++;
            return true;
           }
        }

      if(attempt < EV_LOCK_RETRIES - 1)
         Sleep(1);
     }

   g_ev_lock_timeouts++;
   return false;
}

//--------------------------------------------------
// RELEASE - libera somente com o token desta instancia
//--------------------------------------------------
void EventLockRelease()
{
   if(g_ev_lock_token <= 0.0)
      return;

   GlobalVariableSetOnCondition(EV_LOCK_NAME, 0.0, g_ev_lock_token);
   g_ev_lock_token = 0.0;
}

//--------------------------------------------------
// STATS - para observabilidade (EventSummary etc.)
//--------------------------------------------------
string EventLockStats()
{
   return StringFormat("Lock | contention=%d | timeouts=%d",
                       g_ev_lock_contention,
                       g_ev_lock_timeouts);
}

#endif // EVENT_LOCK_MQH
