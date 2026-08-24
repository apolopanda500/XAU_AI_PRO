//+------------------------------------------------------------------+
//| RecoveryManager.mqh                                              |
//| XAU_AI_PRO                                                      |
//| Auto Recovery System                                            |
//+------------------------------------------------------------------+

#ifndef RECOVERY_MANAGER_MQH
#define RECOVERY_MANAGER_MQH

#include "../Core/Config.mqh"   // RequireAIJSON (input) + config global


//==================================================
// ENUM STATUS
//==================================================

enum RecoveryStatus
{
   RECOVERY_OK=0,
   RECOVERY_DEGRADED=1,
   RECOVERY_CRITICAL=2,
   RECOVERY_FAILED=3
};


//==================================================
// MODULE HEALTH
//==================================================

struct ModuleHealth
{
   string   name;
   bool     healthy;
   int      failures;
   datetime last_check;
   datetime last_failure;
   string   error_message;
};


//==================================================
// RECOVERY MANAGER
//==================================================

class CRecoveryManager
{
private:

   static ModuleHealth m_modules[];

   static int m_module_count;

   static bool m_initialized;

   static datetime m_last_check;

   static int m_check_interval_sec;


   //================================================
   // INTERNAL
   //================================================

   static void InitializeModule(
      int index,
      string name
   );

   static bool CheckAI();

   static bool CheckBroker();

   static bool CheckIndicators();

   static bool CheckDataset();

   static bool CheckJSON();

   static bool CheckMemory();


public:

   static void Init();

   static void Run();

   static RecoveryStatus GetStatus();

   static string GetHealthSummary();

   static bool IsModuleHealthy(
      const string name
   );

   static void ReportModuleStatus(
      const string name,
      bool healthy,
      const string error=""
   );

   static void LogHealth();
};


//==================================================
// STATIC DEFINITIONS
//==================================================

ModuleHealth CRecoveryManager::m_modules[];

int CRecoveryManager::m_module_count=0;

bool CRecoveryManager::m_initialized=false;

datetime CRecoveryManager::m_last_check=0;

int CRecoveryManager::m_check_interval_sec=30;


//==================================================
// INITIALIZE MODULE
//==================================================

void CRecoveryManager::InitializeModule(
   int index,
   string name
)
{
   if(index<0)
      return;

   if(index>=ArraySize(m_modules))
      return;


   m_modules[index].name=
      name;

   m_modules[index].healthy=
      true;

   m_modules[index].failures=
      0;

   m_modules[index].last_check=
      0;

   m_modules[index].last_failure=
      0;

   m_modules[index].error_message=
      "";
}


//==================================================
// INIT
//==================================================

void CRecoveryManager::Init()
{
   if(m_initialized)
      return;


   ArrayResize(
      m_modules,
      6
   );


   m_module_count=6;


   InitializeModule(
      0,
      "AI"
   );

   InitializeModule(
      1,
      "Indicators"
   );

   InitializeModule(
      2,
      "Broker"
   );

   InitializeModule(
      3,
      "Dataset"
   );

   InitializeModule(
      4,
      "JSON"
   );

   InitializeModule(
      5,
      "Memory"
   );


   m_last_check=
      0;

   m_initialized=
      true;


   Print(
      "[RECOVERY] RecoveryManager initialized"
   );
}


//==================================================
// CHECK AI
//==================================================

bool CRecoveryManager::CheckAI()
{
   // v1.2.0 fix: JSON opcional (RequireAIJSON=false) ou no tester
   if(!RequireAIJSON)
      return true;
   if(MQLInfoInteger(MQL_TESTER)!=0)
      return true;

   string fileName=
      "Data\\prediction_" +
      _Symbol +
      ".json";


   return FileIsExist(
      fileName,
      0
   );
}


//==================================================
// CHECK BROKER
//==================================================

bool CRecoveryManager::CheckBroker()
{
   bool connected=
      (
         TerminalInfoInteger(
            TERMINAL_CONNECTED
         )!=0
      );


   bool tradeAllowed=
      (
         AccountInfoInteger(
            ACCOUNT_TRADE_ALLOWED
         )!=0
      );


   return(
      connected &&
      tradeAllowed
   );
}


//==================================================
// CHECK INDICATORS
//==================================================

bool CRecoveryManager::CheckIndicators()
{
   bool connected=
      (
         TerminalInfoInteger(
            TERMINAL_CONNECTED
         )!=0
      );


   if(!connected)
      return false;


   // Verificação básica.
   // A validação detalhada dos handles
   // continua nos módulos individuais.

   return true;
}


//==================================================
// CHECK DATASET
//==================================================

bool CRecoveryManager::CheckDataset()
{
   return FileIsExist(
      "Data\\dataset.csv",
      0
   );
}


//==================================================
// CHECK JSON
//==================================================

bool CRecoveryManager::CheckJSON()
{
   return CheckAI();
}


//==================================================
// CHECK MEMORY
//==================================================

bool CRecoveryManager::CheckMemory()
{
   int limit=
      MQLInfoInteger(
         MQL_MEMORY_LIMIT
      );


   int used=
      MQLInfoInteger(
         MQL_MEMORY_USED
      );


   if(limit<=0)
      return true;


   // Limite de segurança:
   // 80% da memória permitida.

   double usage=
      (
         (double)used /
         (double)limit
      )
      *100.0;


   if(usage>=80.0)
   {
      Print(
         "[RECOVERY] Memory usage high | ",
         DoubleToString(
            usage,
            2
         ),
         "%"
      );

      return false;
   }


   return true;
}


//==================================================
// RUN
//==================================================

void CRecoveryManager::Run()
{
   if(!m_initialized)
      Init();


   datetime now=
      TimeCurrent();


   if(
      m_last_check>0 &&
      (
         now-
         m_last_check
      )<
      m_check_interval_sec
   )
   {
      return;
   }


   m_last_check=
      now;


   //================================================
   // AI
   //================================================

   bool aiOK=
      CheckAI();


   ReportModuleStatus(
      "AI",
      aiOK,
      aiOK
      ?
      ""
      :
      "prediction file missing"
   );


   //================================================
   // BROKER
   //================================================

   bool brokerOK=
      CheckBroker();


   ReportModuleStatus(
      "Broker",
      brokerOK,
      brokerOK
      ?
      ""
      :
      "Connection or trading disabled"
   );


   //================================================
   // INDICATORS
   //================================================

   bool indicatorsOK=
      CheckIndicators();


   ReportModuleStatus(
      "Indicators",
      indicatorsOK,
      indicatorsOK
      ?
      ""
      :
      "Terminal connection unavailable"
   );


   //================================================
   // DATASET
   //================================================

   bool datasetOK=
      CheckDataset();


   ReportModuleStatus(
      "Dataset",
      datasetOK,
      datasetOK
      ?
      ""
      :
      "dataset.csv missing"
   );


   //================================================
   // JSON
   //================================================

   bool jsonOK=
      CheckJSON();


   ReportModuleStatus(
      "JSON",
      jsonOK,
      jsonOK
      ?
      ""
      :
      "Prediction JSON missing"
   );


   //================================================
   // MEMORY
   //================================================

   bool memoryOK=
      CheckMemory();


   ReportModuleStatus(
      "Memory",
      memoryOK,
      memoryOK
      ?
      ""
      :
      "MQL5 memory usage above safe threshold"
   );


   //================================================
   // LOG
   //================================================

   LogHealth();
}


//==================================================
// GET STATUS
//==================================================

RecoveryStatus CRecoveryManager::GetStatus()
{
   if(!m_initialized)
      return RECOVERY_OK;


   int critical=
      0;


   int totalFailures=
      0;


   for(
      int i=0;
      i<m_module_count;
      i++
   )
   {
      if(
         !m_modules[i].healthy
      )
      {
         totalFailures++;


         if(
            m_modules[i].name==
            "Broker"
         )
         {
            critical++;
         }


         if(
            m_modules[i].name==
            "AI"
         )
         {
            critical++;
         }
      }
   }


   if(critical>0)
      return RECOVERY_CRITICAL;


   if(totalFailures>0)
      return RECOVERY_DEGRADED;


   return RECOVERY_OK;
}


//==================================================
// HEALTH SUMMARY
//==================================================

string CRecoveryManager::GetHealthSummary()
{
   if(!m_initialized)
      return "RecoveryManager not initialized";


   string summary=
      "=== RECOVERY STATUS ===\n";


   for(
      int i=0;
      i<m_module_count;
      i++
   )
   {
      string status=
         m_modules[i].healthy
         ?
         "OK"
         :
         "FAIL";


      summary+=
         StringFormat(
            "  %s: %s | Failures: %d | Error: %s\n",
            m_modules[i].name,
            status,
            m_modules[i].failures,
            m_modules[i].error_message
         );
   }


   string overall=
      EnumToString(
         GetStatus()
      );


   summary+=
      StringFormat(
         "Overall: %s",
         overall
      );


   return summary;
}


//==================================================
// MODULE HEALTH
//==================================================

bool CRecoveryManager::IsModuleHealthy(
   const string name
)
{
   if(!m_initialized)
      return true;


   for(
      int i=0;
      i<m_module_count;
      i++
   )
   {
      if(
         m_modules[i].name==
         name
      )
      {
         return(
            m_modules[i].healthy
         );
      }
   }


   return true;
}


//==================================================
// REPORT MODULE STATUS
//==================================================

void CRecoveryManager::ReportModuleStatus(
   const string name,
   bool healthy,
   const string error=""
)
{
   if(!m_initialized)
      return;


   for(
      int i=0;
      i<m_module_count;
      i++
   )
   {
      if(
         m_modules[i].name==
         name
      )
      {
         datetime now=
            TimeCurrent();


         m_modules[i].last_check=
            now;


         //================================================
         // FAILED
         //================================================

         if(!healthy)
         {
            m_modules[i].healthy=
               false;


            m_modules[i].failures++;


            m_modules[i].last_failure=
               now;


            m_modules[i].error_message=
               error;


            PrintFormat(
               "[RECOVERY] %s FAILED: %s",
               name,
               error
            );
         }


         //================================================
         // RECOVERED
         //================================================

         else
         {
            if(
               !m_modules[i].healthy &&
               m_modules[i].failures>0
            )
            {
               PrintFormat(
                  "[RECOVERY] %s recovered after %d failures",
                  name,
                  m_modules[i].failures
               );
            }


            m_modules[i].healthy=
               true;


            m_modules[i].failures=
               0;


            m_modules[i].error_message=
               "";
         }


         break;
      }
   }
}


//==================================================
// LOG HEALTH
//==================================================

void CRecoveryManager::LogHealth()
{
   Print(
      "[RECOVERY]\n",
      GetHealthSummary()
   );
}


//==================================================
// END
//==================================================

#endif