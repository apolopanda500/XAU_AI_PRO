// XAU_AI_PRO v1.2.9
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

   if(LogInicioDetalhe()) { Print("[PATH] data=",DataPath); }
   if(LogInicioDetalhe()) Print("[PATH] files=",FilesPath," | dataset=",DatasetPath,
         " | prediction=",PredictionPath," | model=",ModelPath);

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