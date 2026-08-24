// XAU_AI_PRO v1.2.0
#ifndef TIMEFRAMEMANAGER_MQH
#define TIMEFRAMEMANAGER_MQH

//==========================================
// TIMEFRAME MANAGER
//==========================================

ENUM_TIMEFRAMES TF_Entry;
ENUM_TIMEFRAMES TF_Trend;
ENUM_TIMEFRAMES TF_Filter;

bool InitTimeFrames()
{
   TF_Entry = PERIOD_M15;
   TF_Trend = PERIOD_H1;
   TF_Filter = PERIOD_H4;

   return true;
}

ENUM_TIMEFRAMES GetEntryTF()
{
   return TF_Entry;
}

ENUM_TIMEFRAMES GetTrendTF()
{
   return TF_Trend;
}

ENUM_TIMEFRAMES GetFilterTF()
{
   return TF_Filter;
}

string TimeFrameToString(ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
   }

   return "UNKNOWN";
}

#endif