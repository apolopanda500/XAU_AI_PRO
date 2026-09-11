// XAU_AI_PRO v1.2.0
#ifndef PATHMANAGER_MQH
#define PATHMANAGER_MQH

//==================================================
// PATH MANAGER
//==================================================

string DataPath      = "";
string FilesPath     = "";
string DatasetPath   = "";
string PredictionPath= "";
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

   PredictionPath =
      FilesPath +
      "Data\\prediction.json";

   ModelPath =
      FilesPath +
      "Data\\model.pkl";

   Print("==============================");
   Print("PATH MANAGER");
   Print("DATA PATH      : ",DataPath);
   Print("FILES PATH     : ",FilesPath);
   Print("DATASET PATH   : ",DatasetPath);
   Print("PREDICTION PATH: ",PredictionPath);
   Print("MODEL PATH     : ",ModelPath);
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

string GetPredictionPath()
{
   return PredictionPath;
}

string GetModelPath()
{
   return ModelPath;
}

#endif