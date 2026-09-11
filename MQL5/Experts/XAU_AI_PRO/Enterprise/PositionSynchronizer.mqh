//+------------------------------------------------------------------+
//|                                         PositionSynchronizer.mqh |
//|                                  Smart Execution Engine - Sync   |
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+

#ifndef POSITION_SYNCHRONIZER_MQH
#define POSITION_SYNCHRONIZER_MQH

#include "../Core/Config.mqh"

//+------------------------------------------------------------------+
//| Position Info                                                    |
//+------------------------------------------------------------------+
struct PositionInfo
{
   ulong  ticket;
   ENUM_POSITION_TYPE type;
   double volume;
   double price_open;
   double sl;
   double tp;
   datetime time;
   string magic_comment;
};

class CPositionSynchronizer
{
private:
   static PositionInfo m_positions[];
   static int          m_position_count;
   static datetime     m_last_sync_time;
   static bool         m_initialized;
   
   static bool IsEAPosition(ulong ticket);

public:
   static void Init();
   static void Synchronize();
   static int  GetTotalPositions();
   static int  GetTerminalPositions();   // F4: total EA (magic) no terminal inteiro
   static int  GetEAPositions();
   static int  GetManualPositions();
   static PositionInfo GetPosition(ulong ticket);
   static bool HasConflicts();
   static void LogPositions();
};

PositionInfo CPositionSynchronizer::m_positions[];
int CPositionSynchronizer::m_position_count = 0;
datetime CPositionSynchronizer::m_last_sync_time = 0;
bool CPositionSynchronizer::m_initialized = false;

void CPositionSynchronizer::Init()
{
   ArrayResize(m_positions, 0);
   m_position_count = 0;
   m_initialized = true;
   Print("[SYNC] PositionSynchronizer initialized");
}

bool CPositionSynchronizer::IsEAPosition(ulong ticket)
{
   // Verifica se a posição tem magic number ou comentário do EA.
   // SELECIONA o ticket antes de ler propriedades (bom prática MQL5).
   if(!PositionSelectByTicket(ticket))
      return false;

   ulong magic = (ulong)PositionGetInteger(POSITION_MAGIC);
   string comment = PositionGetString(POSITION_COMMENT);
   
   return (magic == (ulong)MagicNumber || 
           StringFind(comment, "XAU_AI_PRO") >= 0);
}

void CPositionSynchronizer::Synchronize()
{
   if(!m_initialized) Init();
   
   datetime now = TimeCurrent();
   if(now - m_last_sync_time < 5) return; // Sync a cada 5 segundos no máximo
   
   ArrayResize(m_positions, 0);
   m_position_count = 0;
   
   int total = PositionsTotal();
   ArrayResize(m_positions, total);
   
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL) == Symbol())
      {
         PositionInfo pos;
         pos.ticket = ticket;
         pos.type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         pos.volume = PositionGetDouble(POSITION_VOLUME);
         pos.price_open = PositionGetDouble(POSITION_PRICE_OPEN);
         pos.sl = PositionGetDouble(POSITION_SL);
         pos.tp = PositionGetDouble(POSITION_TP);
         pos.time = (datetime)PositionGetInteger(POSITION_TIME);
         pos.magic_comment = PositionGetString(POSITION_COMMENT);
         
         m_positions[m_position_count++] = pos;
      }
   }
   
   ArrayResize(m_positions, m_position_count);
   m_last_sync_time = now;
}

int CPositionSynchronizer::GetTerminalPositions()
{
   // F4: conta posicoes EA (magic) do terminal INTEIRO, ao vivo.
   // Nao depende do cache por-simbolo do grafico nem do throttle de
   // 5s -> elimina o "Positions: 0 total" enganoso quando ha posicao
   // em outro simbolo ou quando o cache esta desatualizado.
   if(!m_initialized) Synchronize();

   int count = 0;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(IsEAPosition(ticket)) count++;
   }
   return count;
}

int CPositionSynchronizer::GetTotalPositions()
{
   if(!m_initialized) Synchronize();
   return m_position_count;
}

int CPositionSynchronizer::GetEAPositions()
{
   if(!m_initialized) Synchronize();
   int count = 0;
   for(int i = 0; i < m_position_count; i++)
   {
      if(IsEAPosition(m_positions[i].ticket))
         count++;
   }
   return count;
}

int CPositionSynchronizer::GetManualPositions()
{
   if(!m_initialized) Synchronize();
   return m_position_count - GetEAPositions();
}

PositionInfo CPositionSynchronizer::GetPosition(ulong ticket)
{
   PositionInfo empty;
   ZeroMemory(empty);
   if(!m_initialized) Synchronize();
   for(int i = 0; i < m_position_count; i++)
   {
      if(m_positions[i].ticket == ticket)
         return m_positions[i];
   }
   return empty;
}

bool CPositionSynchronizer::HasConflicts()
{
   if(!m_initialized) Synchronize();
   
   // Verifica se há posições manuais abertas
   int manual = GetManualPositions();
   return (manual > 0);
}

void CPositionSynchronizer::LogPositions()
{
   PrintFormat("[SYNC] Total: %d | EA: %d | Manual: %d",
               m_position_count, GetEAPositions(), GetManualPositions());
   
   for(int i = 0; i < m_position_count; i++)
   {
      string type = (m_positions[i].type == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      PrintFormat("  #%d %s %.2f @ %.5f | SL: %.5f | TP: %.5f | %s",
                  m_positions[i].ticket, type, m_positions[i].volume,
                  m_positions[i].price_open, m_positions[i].sl, m_positions[i].tp,
                  IsEAPosition(m_positions[i].ticket) ? "EA" : "Manual");
   }
}

#endif // POSITION_SYNCHRONIZER_MQH