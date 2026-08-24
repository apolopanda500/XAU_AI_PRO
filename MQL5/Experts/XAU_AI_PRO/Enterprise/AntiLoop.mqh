//+------------------------------------------------------------------+
//|                                                    AntiLoop.mqh |
//|                                  Smart Execution Engine - AntiLoop|
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+

#ifndef ANTI_LOOP_MQH
#define ANTI_LOOP_MQH

//+------------------------------------------------------------------+
//| Loop Detection State                                             |
//+------------------------------------------------------------------+
struct LoopState
{
   int    open_count;        // Contador de ordens abertas
   int    close_count;       // Contador de ordens fechadas
   datetime last_open_time;  // Última abertura
   datetime last_close_time; // Último fechamento
   bool   loop_detected;     // Loop detectado
   int    loop_warnings;     // Contador de warnings
};

class CAntiLoop
{
private:
   static LoopState m_state;
   static int       m_max_cycles_per_minute; // Máximo de ciclos por minuto
   static int       m_window_seconds;        // Janela de tempo para detecção
   
public:
   static void Init();
   static void RecordOpen();
   static void RecordClose();
   static bool IsLoopDetected();
   static bool CanTrade();
   static void Reset();
   static string GetLoopStatus();
   static void LogStatus();
};

LoopState CAntiLoop::m_state;
int CAntiLoop::m_max_cycles_per_minute = 5;    // Máximo 5 ciclos por minuto
int CAntiLoop::m_window_seconds = 60;          // Janela de 60 segundos

void CAntiLoop::Init()
{
   ZeroMemory(m_state);
   Print("[ANTILOOP] AntiLoop initialized");
}

void CAntiLoop::RecordOpen()
{
   datetime now = TimeCurrent();
   
   // Reseta se passou da janela
   if(now - m_state.last_open_time > m_window_seconds)
   {
      m_state.open_count = 0;
   }
   
   m_state.open_count++;
   m_state.last_open_time = now;
   
   // Detecta loop
   if(m_state.open_count >= m_max_cycles_per_minute)
   {
      m_state.loop_detected = true;
      m_state.loop_warnings++;
      PrintFormat("[ANTILOOP] LOOP DETECTADO! %d aberturas em %d segundos",
                  m_state.open_count, m_window_seconds);
   }
}

void CAntiLoop::RecordClose()
{
   datetime now = TimeCurrent();
   
   if(now - m_state.last_close_time > m_window_seconds)
   {
      m_state.close_count = 0;
   }
   
   m_state.close_count++;
   m_state.last_close_time = now;
}

bool CAntiLoop::IsLoopDetected()
{
   return m_state.loop_detected;
}

bool CAntiLoop::CanTrade()
{
   // Não trade se loop detectado
   if(m_state.loop_detected)
   {
      // Reseta após 2 minutos sem loop
      if(TimeCurrent() - m_state.last_open_time > 120)
      {
         m_state.loop_detected = false;
         m_state.open_count = 0;
         Print("[ANTILOOP] Loop resetado, trading liberado");
      }
      return false;
   }
   
   // Verifica se está dentro do limite
   datetime now = TimeCurrent();
   if(now - m_state.last_open_time < m_window_seconds)
   {
      if(m_state.open_count >= m_max_cycles_per_minute)
         return false;
   }
   else
   {
      m_state.open_count = 0;
   }
   
   return true;
}

void CAntiLoop::Reset()
{
   ZeroMemory(m_state);
}

string CAntiLoop::GetLoopStatus()
{
   if(m_state.loop_detected)
      return StringFormat("LOOP DETECTADO | Aberturas: %d | Warnings: %d",
                          m_state.open_count, m_state.loop_warnings);
   return StringFormat("NORMAL | Aberturas: %d/%d",
                       m_state.open_count, m_max_cycles_per_minute);
}

void CAntiLoop::LogStatus()
{
   PrintFormat("[ANTILOOP] %s", GetLoopStatus());
}

#endif // ANTI_LOOP_MQH