// XAU_AI_PRO v1.2.0 - ConfigManager v2.0 (ETAPA 10)
// Persistencia REAL de perfis em FILE_COMMON (XAU_AI_PRO\Profiles\<nome>.cfg),
// validacao de parametros, perfil ativo controlado pelo EA.
// MQL5: structs com string NAO podem ser copiadas/retornadas por valor.
#ifndef CONFIG_MANAGER_MQH
#define CONFIG_MANAGER_MQH

#define CONFIG_DIR "XAU_AI_PRO\\Profiles\\"

enum ConfigProfile
{
   PROFILE_SCALPING = 0,
   PROFILE_SWING,
   PROFILE_CONSERVATIVE,
   PROFILE_AGGRESSIVE,
   PROFILE_FTMO,
   PROFILE_PROP,
   PROFILE_REAL
};

struct ConfigSet
{
   string name;
   double lot_size;
   double stop_loss;
   double take_profit;
   double trailing_stop;
   double max_daily_loss;
   double max_daily_dd;
   int    max_trades_per_day;
   double risk_per_trade;
   double ai_weight;
   double min_confidence;
   bool   use_break_even;
   bool   use_trailing;
   bool   use_dynamic_lot;
};

class CConfigManager
{
private:
   static ConfigSet     m_profiles[7];
   static bool          m_initialized;
   static ConfigProfile m_current_profile;
   static bool ValidateProfile(int idx, string &err);
   static void FillDefault(int idx, string name, double lot, double sl, double tp,
                           double trail, double mdl, double mdd, int mtpd,
                           double rpt, double aiw, double mconf,
                           bool be, bool tr, bool dl);
public:
   static void Init();
   static bool SetProfile(ConfigProfile profile);
   static ConfigProfile GetCurrentProfile();
   static string GetCurrentProfileName();
   static void GetProfile(ConfigProfile profile, ConfigSet &out);
   static bool SaveProfile(ConfigProfile profile);
   static bool LoadProfile(ConfigProfile profile);
   static bool ExportProfile(const string filename);
   static bool ImportProfile(const string filename, ConfigProfile profile);
   static string GetStatus();
   static void LogStatus();
};

ConfigSet CConfigManager::m_profiles[7];
bool CConfigManager::m_initialized = false;
ConfigProfile CConfigManager::m_current_profile = PROFILE_CONSERVATIVE;

//--------------------------------------------------
// HELPERS (globais, sem static - MQL5)
//--------------------------------------------------
string CFG_ProfilePath(int idx, string name)
{
   return CONFIG_DIR + name + ".cfg";
}

bool CFG_FileSizePositive(string path)
{
   if(!FileIsExist(path, FILE_COMMON)) return false;
   int h = FileOpen(path, FILE_COMMON | FILE_READ | FILE_BIN);
   if(h == INVALID_HANDLE) return false;
   ulong sz = FileSize(h);
   FileClose(h);
   return (sz > 0);
}

//--------------------------------------------------
void CConfigManager::FillDefault(int idx, string name, double lot, double sl, double tp,
                                 double trail, double mdl, double mdd, int mtpd,
                                 double rpt, double aiw, double mconf,
                                 bool be, bool tr, bool dl)
{
   m_profiles[idx].name               = name;
   m_profiles[idx].lot_size           = lot;
   m_profiles[idx].stop_loss          = sl;
   m_profiles[idx].take_profit        = tp;
   m_profiles[idx].trailing_stop      = trail;
   m_profiles[idx].max_daily_loss     = mdl;
   m_profiles[idx].max_daily_dd       = mdd;
   m_profiles[idx].max_trades_per_day = mtpd;
   m_profiles[idx].risk_per_trade     = rpt;
   m_profiles[idx].ai_weight          = aiw;
   m_profiles[idx].min_confidence     = mconf;
   m_profiles[idx].use_break_even     = be;
   m_profiles[idx].use_trailing       = tr;
   m_profiles[idx].use_dynamic_lot    = dl;
}

void CConfigManager::Init()
{
   if(m_initialized) return;
   m_initialized = true;

   FillDefault(PROFILE_SCALPING,    "Scalping",     0.01, 50, 100, 25, 200, 3.0, 20, 0.5, 0.7, 75, true,  true,  true);
   FillDefault(PROFILE_SWING,       "Swing",        0.02, 100, 200, 50, 500, 5.0, 10, 1.0, 0.6, 65, true,  true,  true);
   FillDefault(PROFILE_CONSERVATIVE,"Conservative", 0.01, 80, 160, 40, 300, 3.0, 5,  0.5, 0.5, 80, true,  false, true);
   FillDefault(PROFILE_AGGRESSIVE,  "Aggressive",   0.05, 30, 90, 15, 1000,10.0,50, 2.0, 0.8, 50, false, true,  true);
   FillDefault(PROFILE_FTMO,        "FTMO",         0.01, 100, 200, 50, 1000,10.0,10, 1.0, 0.6, 70, true,  true,  false);
   FillDefault(PROFILE_PROP,        "Prop Firm",    0.01, 80, 160, 40, 500, 5.0, 10, 0.5, 0.6, 75, true,  true,  false);
   FillDefault(PROFILE_REAL,        "Real Account", 0.02, 100, 200, 50, 500, 5.0, 10, 1.0, 0.6, 70, true,  true,  true);

   Print("[CONFIG] ConfigManager v2.0 inicializado | perfis=", 7);
}

//--------------------------------------------------
// VALIDACAO
//--------------------------------------------------
bool CConfigManager::ValidateProfile(int idx, string &err)
{
   err = "";
   if(m_profiles[idx].lot_size <= 0.0)                       { err = "lot_size invalido"; return false; }
   if(m_profiles[idx].stop_loss <= 0.0)                      { err = "stop_loss invalido"; return false; }
   if(m_profiles[idx].take_profit <= 0.0)                    { err = "take_profit invalido"; return false; }
   if(m_profiles[idx].max_daily_loss <= 0.0)                 { err = "max_daily_loss invalido"; return false; }
   if(m_profiles[idx].max_daily_dd <= 0.0 || m_profiles[idx].max_daily_dd > 100.0) { err = "max_daily_dd invalido"; return false; }
   if(m_profiles[idx].max_trades_per_day <= 0)               { err = "max_trades_per_day invalido"; return false; }
   if(m_profiles[idx].risk_per_trade <= 0.0 || m_profiles[idx].risk_per_trade > 10.0) { err = "risk_per_trade invalido"; return false; }
   if(m_profiles[idx].min_confidence < 0.0 || m_profiles[idx].min_confidence > 100.0) { err = "min_confidence invalido"; return false; }
   return true;
}

//--------------------------------------------------
// PERFIL ATIVO
//--------------------------------------------------
bool CConfigManager::SetProfile(ConfigProfile profile)
{
   if(!m_initialized) Init();
   if(profile < 0 || profile >= 7) return false;
   string err;
   if(!ValidateProfile((int)profile, err))
   {
      Print("[CONFIG] Perfil rejeitado: ", err);
      return false;
   }
   m_current_profile = profile;
   Print("[CONFIG] Perfil ativo: ", GetCurrentProfileName());
   return true;
}

ConfigProfile CConfigManager::GetCurrentProfile() { return m_current_profile; }

string CConfigManager::GetCurrentProfileName()
{
   if(!m_initialized) Init();
   return m_profiles[(int)m_current_profile].name;
}

void CConfigManager::GetProfile(ConfigProfile profile, ConfigSet &out)
{
   if(!m_initialized) Init();
   if(profile >= 0 && profile < 7)
      out = m_profiles[(int)profile];   // referencia de saida (permitido)
   else
      out = m_profiles[PROFILE_CONSERVATIVE];
}

//--------------------------------------------------
// PERSISTENCIA (FILE_COMMON) - formato chave=valor
//--------------------------------------------------
bool CConfigManager::SaveProfile(ConfigProfile profile)
{
   if(!m_initialized) Init();
   if(profile < 0 || profile >= 7) return false;

   string err;
   if(!ValidateProfile((int)profile, err)) { Print("[CONFIG] Save rejeitado: ", err); return false; }

   string path = CFG_ProfilePath((int)profile, m_profiles[(int)profile].name);
   int h = FileOpen(path, FILE_COMMON | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) { Print("[CONFIG] Falha ao abrir p/ escrita: ", path); return false; }

   FileWrite(h, "name=" + m_profiles[(int)profile].name);
   FileWrite(h, "lot_size=" + DoubleToString(m_profiles[(int)profile].lot_size, 4));
   FileWrite(h, "stop_loss=" + DoubleToString(m_profiles[(int)profile].stop_loss, 2));
   FileWrite(h, "take_profit=" + DoubleToString(m_profiles[(int)profile].take_profit, 2));
   FileWrite(h, "trailing_stop=" + DoubleToString(m_profiles[(int)profile].trailing_stop, 2));
   FileWrite(h, "max_daily_loss=" + DoubleToString(m_profiles[(int)profile].max_daily_loss, 2));
   FileWrite(h, "max_daily_dd=" + DoubleToString(m_profiles[(int)profile].max_daily_dd, 2));
   FileWrite(h, "max_trades_per_day=" + IntegerToString(m_profiles[(int)profile].max_trades_per_day));
   FileWrite(h, "risk_per_trade=" + DoubleToString(m_profiles[(int)profile].risk_per_trade, 2));
   FileWrite(h, "ai_weight=" + DoubleToString(m_profiles[(int)profile].ai_weight, 2));
   FileWrite(h, "min_confidence=" + DoubleToString(m_profiles[(int)profile].min_confidence, 2));
   FileWrite(h, "use_break_even=" + (m_profiles[(int)profile].use_break_even ? "1" : "0"));
   FileWrite(h, "use_trailing=" + (m_profiles[(int)profile].use_trailing ? "1" : "0"));
   FileWrite(h, "use_dynamic_lot=" + (m_profiles[(int)profile].use_dynamic_lot ? "1" : "0"));
   FileClose(h);

   if(!CFG_FileSizePositive(path))
   {
      Print("[CONFIG] Save: validacao falhou para ", path);
      return false;
   }
   Print("[CONFIG] Perfil salvo: ", path);
   return true;
}

bool CConfigManager::LoadProfile(ConfigProfile profile)
{
   if(!m_initialized) Init();
   if(profile < 0 || profile >= 7) return false;

   string path = CFG_ProfilePath((int)profile, m_profiles[(int)profile].name);
   if(!FileIsExist(path, FILE_COMMON)) return false;

   int h = FileOpen(path, FILE_COMMON | FILE_READ | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return false;

   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);
      string parts[];
      if(StringSplit(line, '=', parts) == 2)
      {
         string k = parts[0], v = parts[1];
         if(k == "lot_size")            m_profiles[(int)profile].lot_size = StringToDouble(v);
         else if(k == "stop_loss")      m_profiles[(int)profile].stop_loss = StringToDouble(v);
         else if(k == "take_profit")    m_profiles[(int)profile].take_profit = StringToDouble(v);
         else if(k == "trailing_stop")  m_profiles[(int)profile].trailing_stop = StringToDouble(v);
         else if(k == "max_daily_loss") m_profiles[(int)profile].max_daily_loss = StringToDouble(v);
         else if(k == "max_daily_dd")   m_profiles[(int)profile].max_daily_dd = StringToDouble(v);
         else if(k == "max_trades_per_day") m_profiles[(int)profile].max_trades_per_day = (int)StringToInteger(v);
         else if(k == "risk_per_trade") m_profiles[(int)profile].risk_per_trade = StringToDouble(v);
         else if(k == "ai_weight")      m_profiles[(int)profile].ai_weight = StringToDouble(v);
         else if(k == "min_confidence") m_profiles[(int)profile].min_confidence = StringToDouble(v);
         else if(k == "use_break_even") m_profiles[(int)profile].use_break_even = (v == "1");
         else if(k == "use_trailing")   m_profiles[(int)profile].use_trailing = (v == "1");
         else if(k == "use_dynamic_lot")m_profiles[(int)profile].use_dynamic_lot = (v == "1");
      }
   }
   FileClose(h);

   string err;
   if(!ValidateProfile((int)profile, err))
   {
      Print("[CONFIG] Load: perfil corrompido (", err, ") - mantendo default");
      return false;
   }
   Print("[CONFIG] Perfil carregado: ", path);
   return true;
}

//--------------------------------------------------
// EXPORT / IMPORT (arquivo nomeado)
//--------------------------------------------------
bool CConfigManager::ExportProfile(const string filename)
{
   if(!m_initialized) Init();
   if(filename == "") return false;
   int idx = (int)m_current_profile;

   string path = CONFIG_DIR + filename;
   int h = FileOpen(path, FILE_COMMON | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return false;

   FileWrite(h, "profile=" + m_profiles[idx].name);
   FileWrite(h, "lot_size=" + DoubleToString(m_profiles[idx].lot_size, 4));
   FileWrite(h, "stop_loss=" + DoubleToString(m_profiles[idx].stop_loss, 2));
   FileWrite(h, "take_profit=" + DoubleToString(m_profiles[idx].take_profit, 2));
   FileWrite(h, "trailing_stop=" + DoubleToString(m_profiles[idx].trailing_stop, 2));
   FileWrite(h, "max_daily_loss=" + DoubleToString(m_profiles[idx].max_daily_loss, 2));
   FileWrite(h, "max_daily_dd=" + DoubleToString(m_profiles[idx].max_daily_dd, 2));
   FileWrite(h, "max_trades_per_day=" + IntegerToString(m_profiles[idx].max_trades_per_day));
   FileWrite(h, "risk_per_trade=" + DoubleToString(m_profiles[idx].risk_per_trade, 2));
   FileWrite(h, "ai_weight=" + DoubleToString(m_profiles[idx].ai_weight, 2));
   FileWrite(h, "min_confidence=" + DoubleToString(m_profiles[idx].min_confidence, 2));
   FileWrite(h, "use_break_even=" + (m_profiles[idx].use_break_even ? "1" : "0"));
   FileWrite(h, "use_trailing=" + (m_profiles[idx].use_trailing ? "1" : "0"));
   FileWrite(h, "use_dynamic_lot=" + (m_profiles[idx].use_dynamic_lot ? "1" : "0"));
   FileClose(h);
   return CFG_FileSizePositive(path);
}

bool CConfigManager::ImportProfile(const string filename, ConfigProfile profile)
{
   if(!m_initialized) Init();
   if(filename == "" || profile < 0 || profile >= 7) return false;

   string path = CONFIG_DIR + filename;
   if(!FileIsExist(path, FILE_COMMON)) return false;

   int h = FileOpen(path, FILE_COMMON | FILE_READ | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return false;

   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);
      string parts[];
      if(StringSplit(line, '=', parts) == 2)
      {
         string k = parts[0], v = parts[1];
         if(k == "lot_size")            m_profiles[(int)profile].lot_size = StringToDouble(v);
         else if(k == "stop_loss")      m_profiles[(int)profile].stop_loss = StringToDouble(v);
         else if(k == "take_profit")    m_profiles[(int)profile].take_profit = StringToDouble(v);
         else if(k == "trailing_stop")  m_profiles[(int)profile].trailing_stop = StringToDouble(v);
         else if(k == "max_daily_loss") m_profiles[(int)profile].max_daily_loss = StringToDouble(v);
         else if(k == "max_daily_dd")   m_profiles[(int)profile].max_daily_dd = StringToDouble(v);
         else if(k == "max_trades_per_day") m_profiles[(int)profile].max_trades_per_day = (int)StringToInteger(v);
         else if(k == "risk_per_trade") m_profiles[(int)profile].risk_per_trade = StringToDouble(v);
         else if(k == "ai_weight")      m_profiles[(int)profile].ai_weight = StringToDouble(v);
         else if(k == "min_confidence") m_profiles[(int)profile].min_confidence = StringToDouble(v);
         else if(k == "use_break_even") m_profiles[(int)profile].use_break_even = (v == "1");
         else if(k == "use_trailing")   m_profiles[(int)profile].use_trailing = (v == "1");
         else if(k == "use_dynamic_lot")m_profiles[(int)profile].use_dynamic_lot = (v == "1");
      }
   }
   FileClose(h);

   string err;
   if(!ValidateProfile((int)profile, err)) { Print("[CONFIG] Import rejeitado: ", err); return false; }
   Print("[CONFIG] Perfil importado: ", filename, " -> ", m_profiles[(int)profile].name);
   return true;
}

//--------------------------------------------------
// STATUS
//--------------------------------------------------
string CConfigManager::GetStatus()
{
   if(!m_initialized) Init();
   int idx = (int)m_current_profile;
   return StringFormat("Perfil: %s | Lot=%.2f | SL=%.0f | TP=%.0f | MaxDD=%.1f%% | Trades=%d",
      m_profiles[idx].name, m_profiles[idx].lot_size, m_profiles[idx].stop_loss,
      m_profiles[idx].take_profit, m_profiles[idx].max_daily_dd, m_profiles[idx].max_trades_per_day);
}

void CConfigManager::LogStatus() { Print("[CONFIG] ", GetStatus()); }

#endif // CONFIG_MANAGER_MQH
