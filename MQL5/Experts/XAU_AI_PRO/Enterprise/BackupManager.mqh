//+------------------------------------------------------------------+
//|                                               BackupManager.mqh  |
//|                                  Backup Manager System v2.0      |
//|                                            XAU_AI_PRO v1.2.0     |
//+------------------------------------------------------------------+
// ETAPA 7 - DATA RECOVERY & BACKUP
//
// Correcoes vs v1:
//  1. WILDCARDS: FileCopy() NAO expande *.set/*.json/*.db/*.log.
//     O v2 expande os padroes com FileFindFirst/FileFindNext nos
//     roots COMMON (Common\Files) e LOCAL (MQL5\Files).
//  2. CAMINHO: o Dataset/DataLogger/AI gravam no diretorio LOCAL,
//     enquanto AuditLog/Statistics/TradeLogger gravam no COMMON.
//     O v2 procura nos DOIS roots e registra a origem de cada
//     arquivo para restaurar no lugar certo.
//  3. VALIDACAO DE SUCESSO REAL: RunBackup() so retorna true se
//     houve copia REALMENTE realizada e validada (destino existe,
//     tamanho > 0 e tamanho == origem). "FileCopy retornou true"
//     NAO e suficiente.
//  4. MANIFESTO: cada snapshot grava manifest.txt mapeando cada
//     arquivo de backup -> path original + root + tamanho.
//  5. RESTAURACAO: Restore() (item) e RestoreAll() (ultimo
//     snapshot) usam o manifesto e validam a restauracao.
//  6. IDENTIFICACAO: GetLatestBackupPath()/GetLastSnapshot()
//     localizam o snapshot mais recente (timestamp no nome).
//  7. LIMPEZA: CleanupOldBackups() remove snapshots antigos
//     mantendo apenas BackupMaxKeep, recursivamente.
//+------------------------------------------------------------------+

#ifndef BACKUP_MANAGER_MQH
#define BACKUP_MANAGER_MQH

#include "../Core/Config.mqh"

//==================================================
// BACKUP RECORD - arquivo copiado (manifesto)
//==================================================

struct BackupRecord
{
   string name;        // nome do item (ex: "Predictions")
   string origPath;    // path original relativo ao root
   int    origRoot;    // 0 = LOCAL (MQL5\Files), FILE_COMMON = COMMON
   string backupFile;  // arquivo dentro do snapshot
   long   size;        // tamanho original em bytes
};

//==================================================
// BACKUP ITEM
//==================================================

struct BackupItem
{
   string   name;
   string   path;      // pode conter wildcard no ultimo segmento
   datetime last_backup;
   bool     success;
   int      files_copied;
};

//==================================================
// BACKUP MANAGER
//==================================================

class CBackupManager
{
private:

   static BackupItem   m_items[];
   static int          m_item_count;
   static bool         m_initialized;
   static string       m_backup_dir;
   static int          m_max_backups;
   static int          m_lastCopied;
   static int          m_lastFailed;
   static string       m_lastSnapshot;

   static BackupRecord m_records[];
   static int          m_recordCount;

   static int  LastIndexOf(string s, ushort ch);
   static long FileSizeOf(string path, int root);
   static int  ExpandPattern(string pattern, int root, BackupRecord &out[], int maxOut, string itemName);
   static bool BackupFile(string src, int srcRoot, long srcSize, string dst);
   static bool AlreadyBackedUp(string origPath, int origRoot);
   static bool WriteManifest(string snapshotPath, string timestamp);
   static bool ReadManifest(string snapshotPath, BackupRecord &recs[]);
   static bool RestoreRecord(BackupRecord &rec);
   static void DeleteFolderRecursive(string folderPath);
   static void CleanupOldBackups();

public:

   static void Init();

   static void AddItem(
      string name,
      string path
   );

   static bool RunBackup();

   static bool Restore(
      const string name,
      const string backup_file
   );

   static bool RestoreAll();

   static void PurgeBackups();

   static void ResetItems();

   static datetime GetLastBackup(
      const string name
   );

   static string GetStatus();

   static void LogStatus();

   //------------------------------------------------
   // ETAPA 7 - novos acessores
   //------------------------------------------------

   static string GetLatestBackupPath();
   static string GetLastSnapshot();
   static int    GetLastFilesCopied();
   static int    GetLastFilesFailed();
};


//==================================================
// STATIC MEMBERS
//==================================================

BackupItem CBackupManager::m_items[];

int CBackupManager::m_item_count = 0;

bool CBackupManager::m_initialized = false;

string CBackupManager::m_backup_dir = "";

int CBackupManager::m_max_backups = 10;

int CBackupManager::m_lastCopied = 0;

int CBackupManager::m_lastFailed = 0;

string CBackupManager::m_lastSnapshot = "";

BackupRecord CBackupManager::m_records[];

int CBackupManager::m_recordCount = 0;


//==================================================
// HELPERS PRIVADOS
//==================================================

int CBackupManager::LastIndexOf(
   string s,
   ushort ch
)
{
   int len = StringLen(s);

   for(int i = len - 1; i >= 0; i--)
   {
      if(StringGetCharacter(s, i) == ch)
         return i;
   }

   return -1;
}

// Tamanho real do arquivo (abre e mede).
long CBackupManager::FileSizeOf(
   string path,
   int root
)
{
   ResetLastError();

   int h = FileOpen(
      path,
      FILE_READ |
      FILE_BIN |
      root
   );

   if(h == INVALID_HANDLE)
      return 0;

   long size = (long)FileSize(h);
   FileClose(h);

   return size;
}

// Expande um padrao (com ou sem wildcard) em um root.
// Preenche out[] com registros BackupRecord.
// Retorna o numero de arquivos encontrados.
int CBackupManager::ExpandPattern(
   string pattern,
   int root,
   BackupRecord &out[],
   int maxOut,
   string itemName
)
{
   int count = 0;

   int last = LastIndexOf(pattern, '\\');

   string dir = "";
   string fname = pattern;

   if(last >= 0)
   {
      dir   = StringSubstr(pattern, 0, last + 1);
      fname = StringSubstr(pattern, last + 1);
   }

   bool hasWildcard =
      (StringFind(fname, "*") >= 0 ||
       StringFind(fname, "?") >= 0);

   //----------------------------------------------
   // Arquivo exato (sem wildcard)
   //----------------------------------------------

   if(!hasWildcard)
   {
      if(FileIsExist(pattern, root))
      {
         if(count < maxOut)
         {
            out[count].name      = itemName;
            out[count].origPath  = pattern;
            out[count].origRoot  = root;
            out[count].backupFile= "";
            out[count].size      = FileSizeOf(pattern, root);
            count++;
         }
      }

      return count;
   }

   //----------------------------------------------
   // Wildcard: FileFindFirst no diretorio
   //----------------------------------------------

   ResetLastError();

   string foundName;

   long search = FileFindFirst(
      dir + fname,
      foundName,
      root
   );

   if(search == INVALID_HANDLE)
      return count;

   do
   {
      int nlen = StringLen(foundName);

      // Diretorios retornam com barra final no MQL5 - pula
      if(
         nlen > 0 &&
         StringGetCharacter(foundName, nlen - 1) != '\\'
      )
      {
         if(count < maxOut)
         {
            out[count].name      = itemName;
            out[count].origPath  = dir + foundName;
            out[count].origRoot  = root;
            out[count].backupFile= "";
            out[count].size      = FileSizeOf(dir + foundName, root);
            count++;
         }
      }
   }
   while(FileFindNext(search, foundName));

   FileFindClose(search);

   return count;
}

// Copia UM arquivo com VALIDACAO DE SUCESSO REAL.
bool CBackupManager::BackupFile(
   string src,
   int srcRoot,
   long srcSize,
   string dst
)
{
   if(
      StringFind(src, "*") >= 0 ||
      StringFind(src, "?") >= 0
   )
   {
      Print("[BACKUP] Wildcard nao expandido: ", src);
      return false;
   }

   if(!FileIsExist(src, srcRoot))
   {
      Print("[BACKUP] Origem nao encontrada: ", src);
      return false;
   }

   //----------------------------------------------
   // Copia
   //----------------------------------------------

   ResetLastError();

   bool copied = FileCopy(
      src,
      srcRoot,
      dst,
      FILE_COMMON
   );

   if(!copied)
   {
      Print(
         "[BACKUP] Falha na copia: ",
         src,
         " -> ",
         dst,
         " | Erro=",
         GetLastError()
      );

      return false;
   }

   //----------------------------------------------
   // Validacao real (FileCopy true NAO basta)
   //----------------------------------------------

   if(!FileIsExist(dst, FILE_COMMON))
   {
      Print("[BACKUP] Copia reportada OK mas destino NAO existe: ", dst);
      return false;
   }

   long dstSize = FileSizeOf(dst, FILE_COMMON);

   if(dstSize <= 0)
   {
      Print("[BACKUP] Destino vazio (0 bytes): ", dst);
      return false;
   }

   if(srcSize > 0 && dstSize != srcSize)
   {
      Print(
         "[BACKUP] Tamanho divergente: ",
         src,
         " (",
         srcSize,
         ") -> ",
         dst,
         " (",
         dstSize,
         ")"
      );

      return false;
   }

   return true;
}

// Dedup: mesmo path+root ja copiado neste snapshot?
bool CBackupManager::AlreadyBackedUp(
   string origPath,
   int origRoot
)
{
   for(int i = 0; i < m_recordCount; i++)
   {
      if(m_records[i].origRoot == origRoot)
      {
         if(StringCompare(m_records[i].origPath, origPath) == 0)
            return true;
      }
   }

   return false;
}

// Grava manifest.txt com o mapeamento completo do snapshot.
// Formato TXT linha-a-linha (sep '|') - robusto ao alinhamento.
bool CBackupManager::WriteManifest(
   string snapshotPath,
   string timestamp
)
{
   string manifestFile = snapshotPath + "manifest.txt";

   int h = FileOpen(
      manifestFile,
      FILE_COMMON |
      FILE_READ |
      FILE_WRITE |
      FILE_TXT |
      FILE_ANSI
   );

   if(h == INVALID_HANDLE)
   {
      Print("[BACKUP] Manifesto: erro ao abrir | Erro=", GetLastError());
      return false;
   }

   FileWrite(h, "#XAU_AI_PRO_BACKUP_MANIFEST|v2");
   FileWrite(h, "created|" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
   FileWrite(h, "snapshot|" + timestamp);
   FileWrite(h, "ea|XAU_AI_PRO v1.2.0");
   FileWrite(h, "files|" + IntegerToString(m_recordCount));

   for(int i = 0; i < m_recordCount; i++)
   {
      string line =
         "F|" +
         m_records[i].name + "|" +
         IntegerToString(m_records[i].origRoot) + "|" +
         m_records[i].origPath + "|" +
         m_records[i].backupFile + "|" +
         IntegerToString(m_records[i].size);

      FileWrite(h, line);
   }

   FileFlush(h);
   FileClose(h);

   return true;
}

// Le o manifest.txt de um snapshot em recs[].
// Le LINHA INTEIRA (FILE_TXT) e faz StringSplit por '|'.
bool CBackupManager::ReadManifest(
   string snapshotPath,
   BackupRecord &recs[]
)
{
   string manifestFile = snapshotPath + "manifest.txt";

   if(!FileIsExist(manifestFile, FILE_COMMON))
      return false;

   int h = FileOpen(
      manifestFile,
      FILE_COMMON |
      FILE_READ |
      FILE_TXT |
      FILE_ANSI
   );

   if(h == INVALID_HANDLE)
      return false;

   int n = 0;
   ArrayResize(recs, 0);

   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);

      string parts[];
      int count = StringSplit(line, '|', parts);

      if(count >= 6 && parts[0] == "F")
      {
         n++;
         ArrayResize(recs, n);

         recs[n - 1].name       = parts[1];
         recs[n - 1].origRoot   = (int)StringToInteger(parts[2]);
         recs[n - 1].origPath   = parts[3];
         recs[n - 1].backupFile = parts[4];
         recs[n - 1].size       = (long)StringToInteger(parts[5]);
      }
   }

   FileClose(h);

   return (n > 0);
}

// Restaura UM registro com validacao.
bool CBackupManager::RestoreRecord(
   BackupRecord &rec
)
{
   if(!FileIsExist(rec.backupFile, FILE_COMMON))
   {
      Print("[BACKUP] Restore: backup ausente: ", rec.backupFile);
      return false;
   }

   //------------------------------------------------
   // FileCopy() NAO sobrescreve arquivos existentes
   // (erro 5020). Remove o destino antes de copiar.
   //------------------------------------------------

   if(FileIsExist(rec.origPath, rec.origRoot))
   {
      ResetLastError();

      if(!FileDelete(rec.origPath, rec.origRoot))
      {
         Print(
            "[BACKUP] Restore: nao foi possivel remover destino: ",
            rec.origPath,
            " | Erro=",
            GetLastError()
         );

         return false;
      }
   }

   ResetLastError();

   bool ok = FileCopy(
      rec.backupFile,
      FILE_COMMON,
      rec.origPath,
      rec.origRoot
   );

   if(!ok)
   {
      Print(
         "[BACKUP] Restore falhou: ",
         rec.backupFile,
         " -> ",
         rec.origPath,
         " | Erro=",
         GetLastError()
      );

      return false;
   }

   if(!FileIsExist(rec.origPath, rec.origRoot))
   {
      Print("[BACKUP] Restore: destino ausente: ", rec.origPath);
      return false;
   }

   long sz = FileSizeOf(rec.origPath, rec.origRoot);

   if(rec.size > 0 && sz != rec.size)
   {
      Print(
         "[BACKUP] Restore: tamanho divergente: ",
         rec.origPath,
         " (",
         sz,
         "/",
         rec.size,
         ")"
      );

      return false;
   }

   Print(
      "[BACKUP] Restaurado: ",
      rec.name,
      " | ",
      rec.origPath
   );

   return true;
}

// Apaga uma pasta recursivamente (arquivos + subpastas).
// FileFindFirst/Next retornam pastas com '\' no final.
void CBackupManager::DeleteFolderRecursive(
   string folderPath
)
{
   string foundName;

   long search = FileFindFirst(
      folderPath + "*",
      foundName,
      FILE_COMMON
   );

   if(search != INVALID_HANDLE)
   {
      do
      {
         int nlen = StringLen(foundName);

         if(
            nlen > 0 &&
            StringGetCharacter(foundName, nlen - 1) == '\\'
         )
         {
            // subpasta -> recursao
            DeleteFolderRecursive(folderPath + foundName);
         }
         else
         {
            FileDelete(folderPath + foundName, FILE_COMMON);
         }
      }
      while(FileFindNext(search, foundName));

      FileFindClose(search);
   }

   FolderDelete(folderPath, FILE_COMMON);
}

// Remove snapshots antigos mantendo apenas m_max_backups.
void CBackupManager::CleanupOldBackups()
{
   string names[];

   string foundName;

   long search = FileFindFirst(
      "XAU_AI_PRO\\Backups\\*",
      foundName,
      FILE_COMMON
   );

   if(search == INVALID_HANDLE)
      return;

   do
   {
      int nlen = StringLen(foundName);

      if(
         nlen > 0 &&
         StringGetCharacter(foundName, nlen - 1) == '\\'
      )
      {
         string folder = StringSubstr(foundName, 0, nlen - 1);

         if(StringFind(folder, "backup_") == 0)
         {
            int n = ArraySize(names);
            ArrayResize(names, n + 1);
            names[n] = folder;
         }
      }
   }
   while(FileFindNext(search, foundName));

   FileFindClose(search);

   int total = ArraySize(names);

   if(total <= m_max_backups)
      return;

   //----------------------------------------------
   // Ordena crescente (timestamp no nome = lexicografico)
   //----------------------------------------------

   for(int i = 0; i < total - 1; i++)
   {
      for(int j = i + 1; j < total; j++)
      {
         if(StringCompare(names[j], names[i]) < 0)
         {
            string tmp = names[i];
            names[i]    = names[j];
            names[j]    = tmp;
         }
      }
   }

   int toDelete = total - m_max_backups;

   for(int i = 0; i < toDelete; i++)
   {
      Print("[BACKUP] Removendo snapshot antigo: ", names[i]);
      DeleteFolderRecursive(m_backup_dir + names[i] + "\\");
   }
}


//==================================================
// INIT
//==================================================

void CBackupManager::Init()
{
   if(m_initialized)
      return;

   //------------------------------------------------
   // Inicializa estado ANTES de AddItem()
   // evita recursao Init() -> AddItem() -> Init()
   //------------------------------------------------

   m_initialized = true;

   m_item_count = 0;

   m_max_backups = BackupMaxKeep;

   m_lastCopied = 0;
   m_lastFailed = 0;
   m_lastSnapshot = "";

   m_backup_dir = "XAU_AI_PRO\\Backups\\";

   ArrayResize(m_items, 32);
   ArrayResize(m_records, 1024);
   m_recordCount = 0;

   //------------------------------------------------
   // Itens padrao (COMMON + LOCAL sao varridos)
   //------------------------------------------------

   AddItem("Config",      "Config\\*.set");
   AddItem("Dataset",     "Data\\dataset.csv");
   AddItem("Predictions", "Data\\*.json");
   AddItem("Logs",        "Logs\\*.log");
   AddItem("Database",    "Data\\*.db");
   AddItem("Audit",       "audit_log.csv");
   AddItem("FullAudit",   "Data\\full_audit.csv");
   AddItem("Stats",       "xau_ai_pro_summary.csv");
   AddItem("TradeHistory","trade_history.csv");

   Print(
      "[BACKUP] BackupManager inicializado | Items=",
      m_item_count,
      " | MaxKeep=",
      m_max_backups
   );
}


//==================================================
// ADD ITEM
//==================================================

void CBackupManager::AddItem(
   string name,
   string path
)
{
   if(!m_initialized)
   {
      m_initialized = true;
      m_item_count  = 0;
      ArrayResize(m_items, 32);
      m_backup_dir  = "XAU_AI_PRO\\Backups\\";
      m_max_backups = BackupMaxKeep;
   }

   if(m_item_count >= ArraySize(m_items))
   {
      Print("[BACKUP] Limite de itens atingido");
      return;
   }

   m_items[m_item_count].name         = name;
   m_items[m_item_count].path         = path;
   m_items[m_item_count].last_backup  = 0;
   m_items[m_item_count].success      = false;
   m_items[m_item_count].files_copied = 0;

   m_item_count++;
}


//==================================================
// RUN BACKUP
//==================================================

bool CBackupManager::RunBackup()
{
   if(!m_initialized)
      Init();

   m_lastCopied   = 0;
   m_lastFailed   = 0;
   m_lastSnapshot = "";
   m_recordCount  = 0;

   //----------------------------------------------
   // Timestamp seguro para nome de pasta
   //----------------------------------------------

   MqlDateTime dt;

   // TimeLocal() (relogio real) para que o nome do snapshot
   // reflita a ORDEM REAL DE CRIACAO. TimeCurrent() no tester
   // retorna o tempo SIMULADO e quebraria a ordenacao.
   TimeToStruct(TimeLocal(), dt);

   string timestamp = StringFormat(
      "%04d%02d%02d_%02d%02d%02d",
      dt.year,
      dt.mon,
      dt.day,
      dt.hour,
      dt.min,
      dt.sec
   );

   string backup_path =
      m_backup_dir +
      "backup_" +
      timestamp +
      "\\";

   //----------------------------------------------
   // Criar hierarquia de diretorios (nivel a nivel)
   //----------------------------------------------

   ResetLastError();

   if(!FolderCreate("XAU_AI_PRO", FILE_COMMON))
   {
      Print("[BACKUP] Falha criando XAU_AI_PRO | Erro=", GetLastError());
      return false;
   }

   ResetLastError();

   if(!FolderCreate("XAU_AI_PRO\\Backups", FILE_COMMON))
   {
      Print("[BACKUP] Falha criando Backups | Erro=", GetLastError());
      return false;
   }

   ResetLastError();

   if(!FolderCreate(backup_path, FILE_COMMON))
   {
      Print("[BACKUP] Falha criando snapshot: ", backup_path, " | Erro=", GetLastError());
      return false;
   }

   //----------------------------------------------
   // Processamento dos itens
   //----------------------------------------------

   bool all_ok = true;

   for(int i = 0; i < m_item_count; i++)
   {
      m_items[i].success      = false;
      m_items[i].files_copied = 0;

      BackupRecord sources[];
      ArrayResize(sources, 512);

      int found = 0;

      // Procura nos DOIS roots: COMMON e LOCAL
      found += ExpandPattern(
         m_items[i].path,
         FILE_COMMON,
         sources,
         512,
         m_items[i].name
      );

      found += ExpandPattern(
         m_items[i].path,
         0,
         sources,
         512,
         m_items[i].name
      );

      if(found == 0)
      {
         Print(
            "[BACKUP] Item sem arquivos: ",
            m_items[i].name,
            " | ",
            m_items[i].path
         );

         continue;   // estado normal (ex: Logs vazio) - nao e falha de copia
      }

      int seq = 0;

      for(int j = 0; j < found; j++)
      {
         // Dedup COMMON/LOCAL
         if(AlreadyBackedUp(sources[j].origPath, sources[j].origRoot))
            continue;

         seq++;

         string destination =
            backup_path +
            m_items[i].name +
            "_" +
            IntegerToString(seq) +
            "_" +
            timestamp +
            ".bak";

         if(
            BackupFile(
               sources[j].origPath,
               sources[j].origRoot,
               sources[j].size,
               destination
            )
         )
         {
            // registra no manifesto
            if(m_recordCount >= ArraySize(m_records))
               ArrayResize(m_records, ArraySize(m_records) + 1024);

            m_records[m_recordCount].name       = m_items[i].name;
            m_records[m_recordCount].origPath   = sources[j].origPath;
            m_records[m_recordCount].origRoot   = sources[j].origRoot;
            m_records[m_recordCount].backupFile = destination;
            m_records[m_recordCount].size       = sources[j].size;
            m_recordCount++;

            m_items[i].files_copied++;
            m_lastCopied++;
         }
         else
         {
            m_lastFailed++;
            all_ok = false;
         }
      }

      if(m_items[i].files_copied > 0)
      {
         m_items[i].last_backup = TimeCurrent();
         m_items[i].success     = true;
      }
      else
      {
         m_items[i].success = false;
         all_ok = false;
      }
   }

   //----------------------------------------------
   // Manifesto
   //----------------------------------------------

   if(m_lastCopied > 0)
   {
      if(!WriteManifest(backup_path, timestamp))
      {
         Print("[BACKUP] Falha ao escrever manifesto");
         all_ok = false;
      }
      else
      {
         m_lastSnapshot = backup_path;
      }
   }

   //----------------------------------------------
   // Limpeza
   //----------------------------------------------

   CleanupOldBackups();

   //----------------------------------------------
   // Resultado: sucesso = copia REAL validada, sem falhas
   //----------------------------------------------

   if(all_ok && m_lastCopied > 0)
   {
      Print(
         "[BACKUP] Backup concluido com sucesso | arquivos=",
         m_lastCopied,
         " | snapshot=",
         backup_path
      );

      return true;
   }

   Print(
      "[BACKUP] Backup com problemas | copiados=",
      m_lastCopied,
      " | falhas=",
      m_lastFailed,
      " | snapshot=",
      backup_path
   );

   return false;
}


//==================================================
// RESTORE (item individual, via manifesto do snapshot)
//==================================================

bool CBackupManager::Restore(
   const string name,
   const string backup_file
)
{
   if(!m_initialized)
      Init();

   if(!FileIsExist(backup_file, FILE_COMMON))
   {
      Print("[BACKUP] Backup nao encontrado: ", backup_file);
      return false;
   }

   // Pasta do snapshot = caminho ate a ultima barra
   string snapshotPath = backup_file;

   int last = LastIndexOf(snapshotPath, '\\');

   if(last >= 0)
      snapshotPath = StringSubstr(snapshotPath, 0, last + 1);

   BackupRecord recs[];

   if(!ReadManifest(snapshotPath, recs))
   {
      Print("[BACKUP] Manifesto nao encontrado em: ", snapshotPath);
      return false;
   }

   bool any   = false;
   bool allOk = true;

   for(int i = 0; i < ArraySize(recs); i++)
   {
      if(recs[i].name != name)
         continue;

      any = true;

      if(!RestoreRecord(recs[i]))
         allOk = false;
   }

   if(!any)
   {
      Print("[BACKUP] Nenhum arquivo do item no manifesto: ", name);
      return false;
   }

   return allOk;
}


//==================================================
// RESTORE ALL (ultimo snapshot)
//==================================================

bool CBackupManager::RestoreAll()
{
   if(!m_initialized)
      Init();

   string latest = GetLatestBackupPath();

   if(latest == "")
   {
      Print("[BACKUP] Nenhum snapshot encontrado para restaurar");
      return false;
   }

   BackupRecord recs[];

   if(!ReadManifest(latest, recs))
   {
      Print("[BACKUP] Manifesto ausente/corrompido em: ", latest);
      return false;
   }

   if(ArraySize(recs) == 0)
   {
      Print("[BACKUP] Manifesto vazio em: ", latest);
      return false;
   }

   bool allOk = true;

   for(int i = 0; i < ArraySize(recs); i++)
   {
      if(!RestoreRecord(recs[i]))
         allOk = false;
   }

   Print(
      "[BACKUP] RestoreAll: ",
      allOk ? "OK" : "COM FALHAS",
      " | snapshot=",
      latest
   );

   return allOk;
}


//==================================================
// LATEST BACKUP PATH
//==================================================

string CBackupManager::GetLatestBackupPath()
{
   string names[];

   string foundName;

   long search = FileFindFirst(
      "XAU_AI_PRO\\Backups\\*",
      foundName,
      FILE_COMMON
   );

   if(search == INVALID_HANDLE)
      return "";

   do
   {
      int nlen = StringLen(foundName);

      if(
         nlen > 0 &&
         StringGetCharacter(foundName, nlen - 1) == '\\'
      )
      {
         string folder = StringSubstr(foundName, 0, nlen - 1);

         if(StringFind(folder, "backup_") == 0)
         {
            int n = ArraySize(names);
            ArrayResize(names, n + 1);
            names[n] = folder;
         }
      }
   }
   while(FileFindNext(search, foundName));

   FileFindClose(search);

   if(ArraySize(names) == 0)
      return "";

   // Timestamp no nome = ordenacao lexicografica
   string latest = names[0];

   for(int i = 1; i < ArraySize(names); i++)
   {
      if(StringCompare(names[i], latest) > 0)
         latest = names[i];
   }

   return m_backup_dir + latest + "\\";
}


//==================================================
// LAST BACKUP (item)
//==================================================

datetime CBackupManager::GetLastBackup(
   const string name
)
{
   if(!m_initialized)
      Init();

   for(int i = 0; i < m_item_count; i++)
   {
      if(m_items[i].name == name)
         return m_items[i].last_backup;
   }

   return 0;
}


//==================================================
// STATUS
//==================================================

string CBackupManager::GetStatus()
{
   if(!m_initialized)
      Init();

   string status =
      "=== BACKUP MANAGER ===\n";

   status +=
      "Items: " +
      IntegerToString(m_item_count) +
      "\n";

   status +=
      "Directory: " +
      m_backup_dir +
      "\n";

   status +=
      "LastSnapshot: " +
      (m_lastSnapshot != "" ? m_lastSnapshot : "none") +
      "\n";

   status +=
      "LastRun: files=" +
      IntegerToString(m_lastCopied) +
      " failed=" +
      IntegerToString(m_lastFailed) +
      "\n";

   for(int i = 0; i < m_item_count; i++)
   {
      string last = "Never";

      if(m_items[i].last_backup > 0)
      {
         last = TimeToString(
            m_items[i].last_backup,
            TIME_DATE | TIME_SECONDS
         );
      }

      status += StringFormat(
         "%s: %s (%d) | Last: %s\n",
         m_items[i].name,
         m_items[i].success ? "OK" : "FAIL",
         m_items[i].files_copied,
         last
      );
   }

   return status;
}


//==================================================
// LOG STATUS
//==================================================

void CBackupManager::LogStatus()
{
   Print("[BACKUP] ", GetStatus());
}


//==================================================
// ACESSORES ETAPA 7
//==================================================

string CBackupManager::GetLastSnapshot()
{
   return m_lastSnapshot;
}

int CBackupManager::GetLastFilesCopied()
{
   return m_lastCopied;
}

int CBackupManager::GetLastFilesFailed()
{
   return m_lastFailed;
}

// Apaga TODOS os snapshots (uso manual/testes).
void CBackupManager::PurgeBackups()
{
   string names[];

   string foundName;

   long search = FileFindFirst(
      "XAU_AI_PRO\\Backups\\*",
      foundName,
      FILE_COMMON
   );

   if(search == INVALID_HANDLE)
      return;

   do
   {
      int nlen = StringLen(foundName);

      if(
         nlen > 0 &&
         StringGetCharacter(foundName, nlen - 1) == '\\'
      )
      {
         string folder = StringSubstr(foundName, 0, nlen - 1);

         if(StringFind(folder, "backup_") == 0)
         {
            int n = ArraySize(names);
            ArrayResize(names, n + 1);
            names[n] = folder;
         }
      }
   }
   while(FileFindNext(search, foundName));

   FileFindClose(search);

   for(int i = 0; i < ArraySize(names); i++)
   {
      Print("[BACKUP] Purge: removendo snapshot ", names[i]);
      DeleteFolderRecursive("XAU_AI_PRO\\Backups\\" + names[i] + "\\");
   }

   m_lastSnapshot = "";
}

// Zera os itens e registros (uso em testes/utilitarios).
void CBackupManager::ResetItems()
{
   m_item_count  = 0;
   m_recordCount = 0;
}


//==================================================
// END
//==================================================

#endif // BACKUP_MANAGER_MQH
