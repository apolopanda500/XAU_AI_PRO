//+------------------------------------------------------------------+
//|                                                    Scheduler.mqh |
//|                                  Task Scheduler System           |
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+

#ifndef SCHEDULER_MQH
#define SCHEDULER_MQH

enum TaskFrequency { TASK_ONCE, TASK_DAILY, TASK_HOURLY, TASK_CUSTOM };

typedef void (*TaskCallback)();

struct ScheduledTask
{
   string        name;
   TaskFrequency frequency;
   int           hour;
   int           minute;
   datetime      last_run;
   datetime      next_run;
   bool          enabled;
   TaskCallback   callback;
};

class CScheduler
{
private:
   static ScheduledTask m_tasks[];
   static int           m_task_count;
   static bool          m_initialized;
public:
   static void Init();
   static void AddTask(string name, TaskFrequency freq, int hour, int minute, TaskCallback callback);
   static void Run();
   static void EnableTask(string name);
   static void DisableTask(string name);
   static void RemoveTask(string name);
   static int GetTaskCount();
   static string GetStatus();
   static void LogStatus();
};

ScheduledTask CScheduler::m_tasks[];
int CScheduler::m_task_count = 0;
bool CScheduler::m_initialized = false;

void CScheduler::Init()
{
   if(m_initialized) return;
   ArrayResize(m_tasks, 20);
   m_task_count = 0;
   m_initialized = true;
   Print("[SCHEDULER] Scheduler initialized");
}

void CScheduler::AddTask(string name, TaskFrequency freq, int hour, int minute, TaskCallback callback)
{
   if(!m_initialized) Init();
   if(m_task_count >= ArraySize(m_tasks)) return;
   
   ScheduledTask task;
   task.name = name;
   task.frequency = freq;
   task.hour = hour;
   task.minute = minute;
   task.last_run = 0;
   task.next_run = TimeCurrent();
   task.enabled = true;
   task.callback = callback;
   
   m_tasks[m_task_count++] = task;
}

void CScheduler::Run()
{
   if(!m_initialized) return;
   datetime now = TimeCurrent();
   
   for(int i = 0; i < m_task_count; i++)
   {
      if(!m_tasks[i].enabled) continue;
      if(now < m_tasks[i].next_run) continue;
      if(m_tasks[i].callback == NULL) continue;
      
      m_tasks[i].callback();
      m_tasks[i].last_run = now;
      
      // Calculate next run
      switch(m_tasks[i].frequency)
      {
         case TASK_ONCE:
            m_tasks[i].enabled = false;
            break;
         case TASK_DAILY:
            m_tasks[i].next_run = now + 86400;
            break;
         case TASK_HOURLY:
            m_tasks[i].next_run = now + 3600;
            break;
         case TASK_CUSTOM:
            {
               // Custom scheduling based on hour/minute
               datetime next = now + 60; // Next minute fallback
               m_tasks[i].next_run = next;
            }
            break;
      }
   }
}

void CScheduler::EnableTask(string name)
{
   for(int i = 0; i < m_task_count; i++)
   {
      if(m_tasks[i].name == name) { m_tasks[i].enabled = true; break; }
   }
}

void CScheduler::DisableTask(string name)
{
   for(int i = 0; i < m_task_count; i++)
   {
      if(m_tasks[i].name == name) { m_tasks[i].enabled = false; break; }
   }
}

void CScheduler::RemoveTask(string name)
{
   for(int i = 0; i < m_task_count; i++)
   {
      if(m_tasks[i].name == name)
      {
         ArrayRemove(m_tasks, i, 1);
         m_task_count--;
         break;
      }
   }
}

int CScheduler::GetTaskCount() { return m_task_count; }

string CScheduler::GetStatus()
{
   string s = StringFormat("Tasks: %d | ", m_task_count);
   for(int i = 0; i < m_task_count; i++)
   {
      s += StringFormat("%s(%s) ", m_tasks[i].name, m_tasks[i].enabled ? "ON" : "OFF");
   }
   return s;
}

void CScheduler::LogStatus() { Print("[SCHEDULER] " + GetStatus()); }

#endif // SCHEDULER_MQH
