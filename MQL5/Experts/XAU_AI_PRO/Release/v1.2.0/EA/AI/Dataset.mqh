// XAU_AI_PRO v1.2.0
#ifndef DATASET_MQH
#define DATASET_MQH

//==================================================
// XAU_AI_PRO ENTERPRISE DATASET
// v1.2.0 — Ring Buffer + Export seguro
//==================================================

#define MAX_DATASET 100000

//==================================================
// ESTRUTURA
//==================================================

struct TradeData
{
   datetime time;

   string symbol;

   ENUM_TIMEFRAMES timeframe;

   int signal;

   double price;
   double volume;
   double spread;

   double atr;
   double adx;
   double rsi;

   double volatility;
   double trend;

   double ai_score;
   double ai_probability;

   double execution_score;

   double sl;
   double tp;

   double profit;

   bool result;
};

//==================================================
// MEMÓRIA
//==================================================

static TradeData Dataset[];

static int DatasetCount      = 0;
static int DatasetWriteIndex = 0;
static int LastDatasetIndex  = -1;

//==================================================
// INIT
//==================================================

void DatasetInit()
{
   ArrayResize(Dataset, MAX_DATASET);

   DatasetCount      = 0;
   DatasetWriteIndex = 0;
   LastDatasetIndex  = -1;
}

//==================================================
// PRÓXIMO SLOT
//==================================================

int DatasetNext()
{
   int index = DatasetWriteIndex;

   DatasetWriteIndex++;

   if(DatasetWriteIndex >= MAX_DATASET)
      DatasetWriteIndex = 0;

   if(DatasetCount < MAX_DATASET)
      DatasetCount++;

   return index;
}

//==================================================
// ADICIONAR REGISTRO
//==================================================

int AddToDataset(
   string symbol,
   ENUM_TIMEFRAMES tf,
   int signal,
   double price,
   double volume,
   double spread,
   double atr,
   double adx,
   double rsi,
   double volatility,
   double trend,
   double aiScore,
   double aiProb,
   double executionScore,
   double sl,
   double tp
)
{
   int id = DatasetNext();

   Dataset[id].time = TimeCurrent();

   Dataset[id].symbol = symbol;
   Dataset[id].timeframe = tf;

   Dataset[id].signal = signal;

   Dataset[id].price = price;
   Dataset[id].volume = volume;

   Dataset[id].spread = spread;

   Dataset[id].atr = atr;
   Dataset[id].adx = adx;
   Dataset[id].rsi = rsi;

   Dataset[id].volatility = volatility;
   Dataset[id].trend = trend;

   Dataset[id].ai_score = aiScore;
   Dataset[id].ai_probability = aiProb;

   Dataset[id].execution_score = executionScore;

   Dataset[id].sl = sl;
   Dataset[id].tp = tp;

   Dataset[id].profit = 0.0;
   Dataset[id].result = false;

   LastDatasetIndex = id;

   return id;
}

//==================================================
// ATUALIZA RESULTADO
//==================================================

void UpdateDatasetResult(
   int index,
   double profit
)
{
   if(index < 0)
      return;

   if(index >= MAX_DATASET)
      return;

   Dataset[index].profit = profit;

   Dataset[index].result = (profit > 0.0);
}

//==================================================
// TOTAL DE REGISTROS
//==================================================

int DatasetTotal()
{
   return DatasetCount;
}

//==================================================
// WIN RATE
//==================================================

double DatasetWinRate()
{
   if(DatasetCount <= 0)
      return 0.0;

   int wins = 0;

   for(int i = 0; i < DatasetCount; i++)
   {
      if(Dataset[i].result)
         wins++;
   }

   return NormalizeDouble(
      (double)wins * 100.0 / (double)DatasetCount,
      2
   );
}

//==================================================
// MÉDIA DE PROFIT
//==================================================

double DatasetAverageProfit()
{
   if(DatasetCount <= 0)
      return 0.0;

   double total = 0.0;

   for(int i = 0; i < DatasetCount; i++)
      total += Dataset[i].profit;

   return NormalizeDouble(
      total / (double)DatasetCount,
      2
   );
}

//==================================================
// MÉDIA AI SCORE
//==================================================

double DatasetAverageAIScore()
{
   if(DatasetCount <= 0)
      return 0.0;

   double total = 0.0;

   for(int i = 0; i < DatasetCount; i++)
      total += Dataset[i].ai_score;

   return NormalizeDouble(
      total / (double)DatasetCount,
      2
   );
}

//==================================================
// EXPORT CSV
//==================================================

void ExportDatasetCSV()
{
   int total = MathMin(
      DatasetCount,
      MAX_DATASET
   );

   if(total <= 0)
   {
      Print("Dataset vazio. Nada para exportar.");
      return;
   }

   int file = FileOpen(
      "Data\\trades_dataset.csv",
      FILE_WRITE |
      FILE_CSV |
      FILE_ANSI
   );

   if(file == INVALID_HANDLE)
   {
      Print(
         "Dataset: erro ao abrir CSV. Code: ",
         GetLastError()
      );

      return;
   }

   //================================================
   // HEADER
   //================================================

   FileWrite(
      file,
      "Time",
      "Symbol",
      "Timeframe",
      "Signal",
      "Price",
      "Volume",
      "Spread",
      "ATR",
      "ADX",
      "RSI",
      "Volatility",
      "Trend",
      "AIScore",
      "AIProbability",
      "ExecutionScore",
      "SL",
      "TP",
      "Profit",
      "Result"
   );

   //================================================
   // DADOS
   //================================================

   for(int i = 0; i < total; i++)
   {
      FileWrite(
         file,

         TimeToString(
            Dataset[i].time,
            TIME_DATE | TIME_SECONDS
         ),

         Dataset[i].symbol,

         EnumToString(
            Dataset[i].timeframe
         ),

         Dataset[i].signal,

         DoubleToString(
            Dataset[i].price,
            _Digits
         ),

         DoubleToString(
            Dataset[i].volume,
            2
         ),

         DoubleToString(
            Dataset[i].spread,
            2
         ),

         DoubleToString(
            Dataset[i].atr,
            2
         ),

         DoubleToString(
            Dataset[i].adx,
            2
         ),

         DoubleToString(
            Dataset[i].rsi,
            2
         ),

         DoubleToString(
            Dataset[i].volatility,
            2
         ),

         DoubleToString(
            Dataset[i].trend,
            2
         ),

         DoubleToString(
            Dataset[i].ai_score,
            2
         ),

         DoubleToString(
            Dataset[i].ai_probability,
            4
         ),

         DoubleToString(
            Dataset[i].execution_score,
            2
         ),

         DoubleToString(
            Dataset[i].sl,
            _Digits
         ),

         DoubleToString(
            Dataset[i].tp,
            _Digits
         ),

         DoubleToString(
            Dataset[i].profit,
            2
         ),

         Dataset[i].result
      );
   }

   FileFlush(file);
   FileClose(file);

   Print(
      "Dataset exportado: ",
      total,
      " registros"
   );
}

//==================================================
// LIMPAR DATASET
//==================================================

void ClearDataset()
{
   DatasetCount      = 0;
   DatasetWriteIndex = 0;
   LastDatasetIndex  = -1;

   ArrayResize(
      Dataset,
      MAX_DATASET
   );

   for(int i = 0; i < MAX_DATASET; i++)
   {
      ZeroMemory(
         Dataset[i]
      );
   }
}

//==================================================
// ÚLTIMO REGISTRO
//==================================================

int DatasetLastIndex()
{
   return LastDatasetIndex;
}

//==================================================
// DATASET PRONTO
//==================================================

bool DatasetIsReady()
{
   return (
      DatasetCount > 0 &&
      LastDatasetIndex >= 0
   );
}

#endif