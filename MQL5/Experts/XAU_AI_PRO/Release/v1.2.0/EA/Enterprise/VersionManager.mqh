// XAU_AI_PRO v1.2.0 - VersionManager v2.0 (ETAPA 10)
// Versao padronizada, build date, registro do estado dos modulos.
// SEM auto-update: atualizacao somente controlada/manual (seguranca).
#ifndef VERSION_MANAGER_MQH
#define VERSION_MANAGER_MQH

#define EA_VERSION_STRING "1.2.0"

struct VersionInfo
{
   string version;
   string build_date;
   string author;
   string changes;
   bool   stable;
};

class CVersionManager
{
private:
   static VersionInfo m_current;
   static bool     m_initialized;
   static bool     m_auto_update;
   static int      m_module_count;
   static string   m_modules[32];
   static string   m_module_state[32];
   static void RegisterModule(const string name, const string state);
public:
   static void Init();
   static void RegisterModules();
   static void CheckForUpdates();            // sem auto-update: apenas informativo
   static bool DownloadUpdate(const string version);   // bloqueado (seguranca)
   static void SetAutoUpdate(bool enable);   // forca false
   static string GetCurrentVersion();
   static VersionInfo GetVersionInfo();
   static string GetModulesSummary();
   static string GetStatus();
   static void LogStatus();
};

VersionInfo CVersionManager::m_current;
bool CVersionManager::m_initialized = false;
bool CVersionManager::m_auto_update = false;
int  CVersionManager::m_module_count = 0;
string CVersionManager::m_modules[32];
string CVersionManager::m_module_state[32];

void CVersionManager::Init()
{
   if(m_initialized) return;
   m_initialized = true;

   m_current.version    = EA_VERSION_STRING;
   m_current.build_date = TimeToString(TimeCurrent(), TIME_DATE);
   m_current.author     = "XAU_AI_PRO Team";
   m_current.changes    = "v1.2.0 - ETAPA 10: consolidacao final (ConfigManager, VersionManager, BackupManager, NotificationCenter)";
   m_current.stable     = true;

   Print("[VERSION] v", m_current.version, " | build ", m_current.build_date);
}

void CVersionManager::RegisterModule(const string name, const string state)
{
   if(m_module_count < 32)
   {
      m_modules[m_module_count]      = name;
      m_module_state[m_module_count] = state;
      m_module_count++;
   }
}

void CVersionManager::RegisterModules()
{
   if(!m_initialized) Init();
   m_module_count = 0;

   RegisterModule("ConfigManager",   "OK");
   RegisterModule("VersionManager",  "OK");
   RegisterModule("RiskEngine",      "OK");
   RegisterModule("ExecutionEngine", "OK");
   RegisterModule("AIEngine",        "OK");
   RegisterModule("ReplayEngine",    "OK");
   RegisterModule("BackupManager",   "OK");
   RegisterModule("BacktestAnalyzer","OK");
   RegisterModule("BenchmarkEngine", "OK");
   RegisterModule("NotificationCenter","OK");
   RegisterModule("HealthMonitor",   "OK");
   RegisterModule("AuditLog",        "OK");
   RegisterModule("ProductionChecklist","OK");
   RegisterModule("ValidationChecklist","OK");
   RegisterModule("NewsFilter",      "OK (calendario MT5)");

   Print("[VERSION] Modulos registrados: ", m_module_count);
}

void CVersionManager::CheckForUpdates()
{
   if(!m_initialized) Init();
   // SEM auto-update: atualizacao somente manual/controlada.
   Print("[VERSION] Auto-update DESATIVADO por seguranca. Atualizacao somente manual/controlada.");
}

bool CVersionManager::DownloadUpdate(const string version)
{
   Print("[VERSION] Download de update BLOQUEADO (auto-update desativado).");
   return false;
}

void CVersionManager::SetAutoUpdate(bool enable)
{
   m_auto_update = false; // forca desativado (seguranca)
   Print("[VERSION] Auto-update permanece DESATIVADO (seguranca).");
}

string CVersionManager::GetCurrentVersion() { return EA_VERSION_STRING; }

VersionInfo CVersionManager::GetVersionInfo()
{
   if(!m_initialized) Init();
   return m_current;
}

string CVersionManager::GetModulesSummary()
{
   string s = "";
   for(int i = 0; i < m_module_count; i++)
      s += m_modules[i] + "=" + m_module_state[i] + (i < m_module_count-1 ? "; " : "");
   return s;
}

string CVersionManager::GetStatus()
{
   if(!m_initialized) Init();
   return StringFormat("v%s | Build=%s | Stable=%s | AutoUpdate=OFF | Modulos=%d",
      m_current.version, m_current.build_date,
      m_current.stable ? "Yes" : "No", m_module_count);
}

void CVersionManager::LogStatus()
{
   Print("[VERSION] ", GetStatus());
   if(m_module_count > 0)
      Print("[VERSION] Modulos: ", GetModulesSummary());
}

#endif // VERSION_MANAGER_MQH
