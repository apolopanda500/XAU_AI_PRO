// XAU_AI_PRO v1.2.0
#ifndef PATHMANAGER_MQH
#define PATHMANAGER_MQH

//==================================================
// PATH MANAGER
//==================================================

string DataPath      = "";
string FilesPath     = "";
string DatasetPath   = "";
string ModelPath     = "";

//==================================================
// INIT
//==================================================

bool InitPathManager()
{
   DataPath =
      TerminalInfoString(
         TERMINAL_DATA_PATH
      );

   FilesPath =
      DataPath +
      "\\MQL5\\Files\\";

   DatasetPath =
      FilesPath +
      "Data\\dataset.csv";

   // Predicao por simbolo (prediction_<SYMBOL>.json) - padrao real do pipeline.
   // O caminho exato depende do simbolo; aqui guardamos apenas o prefixo,
   // pois o AIConnector monta o nome completo (prediction_XAUUSD.json etc).
   ModelPath =
      FilesPath +
      "Python\\models\\";

   Print("==============================");
   Print("PATH MANAGER");
   Print("DATA PATH      : ",DataPath);
   Print("FILES PATH     : ",FilesPath);
   Print("DATASET PATH   : ",DatasetPath);
   Print("MODELS PATH    : ",ModelPath);
   Print("==============================");

   return true;
}

//==================================================
// GETTERS
//==================================================

string GetFilesPath()
{
   return FilesPath;
}

string GetDatasetPath()
{
   return DatasetPath;
}

string GetModelPath()
{
   return ModelPath;
}

#endif