// XAU_AI_PRO v1.2.0
#ifndef AILEARNINGMEMORY_MQH
#define AILEARNINGMEMORY_MQH

//==================================================
// AI LEARNING MEMORY v1.2.0
// XAU_AI_PRO ENTERPRISE
//==================================================

struct AILearningState
{
   string   symbol;

   int      totalTrades;
   int      wins;
   int      losses;

   int      consecutiveWins;
   int      consecutiveLosses;

   double   lastConfidence;
   double   lastScore;

   double   learningWeight;
   double   memoryStrength;

   datetime lastUpdate;
};

static AILearningState g_AIMemory[];

//==================================================

int FindLearningIndex(string symbol)
{
   for(int i=0;i<ArraySize(g_AIMemory);i++)
   {
      if(g_AIMemory[i].symbol==symbol)
         return i;
   }

   return -1;
}

//==================================================

void InitLearningMemory(string symbol)
{
   if(symbol=="")
      symbol=_Symbol;

   if(FindLearningIndex(symbol)>=0)
      return;

   int size=ArraySize(g_AIMemory);

   ArrayResize(g_AIMemory,size+1);

   g_AIMemory[size].symbol=symbol;
   g_AIMemory[size].totalTrades=0;
   g_AIMemory[size].wins=0;
   g_AIMemory[size].losses=0;
   g_AIMemory[size].consecutiveWins=0;
   g_AIMemory[size].consecutiveLosses=0;
   g_AIMemory[size].lastConfidence=0.0;
   g_AIMemory[size].lastScore=0.0;
   g_AIMemory[size].learningWeight=1.0;
   g_AIMemory[size].memoryStrength=0.0;
   g_AIMemory[size].lastUpdate=TimeCurrent();
}

//==================================================

double ClampMemory(double value)
{
   if(value>25.0)
      return 25.0;

   if(value<-25.0)
      return -25.0;

   return value;
}

//==================================================

void StoreExperience(
   string symbol,
   int signal,
   double confidence,
   bool result
)
{
   if(symbol=="")
      symbol=_Symbol;

   InitLearningMemory(symbol);

   int id=FindLearningIndex(symbol);

   if(id<0)
      return;

   g_AIMemory[id].totalTrades++;
   g_AIMemory[id].lastConfidence=confidence;
   g_AIMemory[id].lastUpdate=TimeCurrent();

   if(result)
   {
      g_AIMemory[id].wins++;
      g_AIMemory[id].consecutiveWins++;
      g_AIMemory[id].consecutiveLosses=0;

      g_AIMemory[id].memoryStrength+=1.0;
   }
   else
   {
      g_AIMemory[id].losses++;
      g_AIMemory[id].consecutiveLosses++;
      g_AIMemory[id].consecutiveWins=0;

      g_AIMemory[id].memoryStrength-=1.0;
   }

   g_AIMemory[id].memoryStrength=
      ClampMemory(g_AIMemory[id].memoryStrength);

   double winrate=0.0;

   if(g_AIMemory[id].totalTrades>0)
      winrate=
         (double)g_AIMemory[id].wins/
         g_AIMemory[id].totalTrades;

   g_AIMemory[id].learningWeight=
      0.70+(winrate*0.60);

   Print(
      "[AI MEMORY] ",
      symbol,
      " WR=",
      DoubleToString(winrate*100.0,1),
      "% MEM=",
      DoubleToString(g_AIMemory[id].memoryStrength,2)
   );
}

//==================================================

double MemoryBoost(string symbol)
{
   if(symbol=="")
      symbol=_Symbol;

   int id=FindLearningIndex(symbol);

   if(id<0)
      return 1.0;

   double mem=g_AIMemory[id].memoryStrength;

   if(mem>=20.0)
      return 1.25;

   if(mem>=15.0)
      return 1.18;

   if(mem>=10.0)
      return 1.12;

   if(mem>=5.0)
      return 1.06;

   if(mem<=-20.0)
      return 0.70;

   if(mem<=-15.0)
      return 0.80;

   if(mem<=-10.0)
      return 0.88;

   if(mem<=-5.0)
      return 0.94;

   return 1.0;
}

//==================================================

double ApplyMemoryBoost(string symbol,double score)
{
   double boosted=
      score*
      MemoryBoost(symbol);

   if(boosted>100.0)
      boosted=100.0;

   if(boosted<0.0)
      boosted=0.0;

   return boosted;
}

//==================================================

double GetLearningWeight(string symbol)
{
   if(symbol=="")
      symbol=_Symbol;

   int id=FindLearningIndex(symbol);

   if(id<0)
      return 1.0;

   return g_AIMemory[id].learningWeight;
}

//==================================================

double GetMemoryStrength(string symbol)
{
   if(symbol=="")
      symbol=_Symbol;

   int id=FindLearningIndex(symbol);

   if(id<0)
      return 0.0;

   return g_AIMemory[id].memoryStrength;
}

//==================================================

double GetAIWinRate(string symbol)
{
   if(symbol=="")
      symbol=_Symbol;

   int id=FindLearningIndex(symbol);

   if(id<0)
      return 0.0;

   if(g_AIMemory[id].totalTrades==0)
      return 0.0;

   return
      100.0*
      g_AIMemory[id].wins/
      g_AIMemory[id].totalTrades;
}

#endif