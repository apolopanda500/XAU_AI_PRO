// XAU_AI_PRO v1.2.0
#ifndef ADAPTIVEWEIGHTS_MQH
#define ADAPTIVEWEIGHTS_MQH

//==================================================
// ADAPTIVE AI WEIGHTS ENGINE v1.2.0
//==================================================

struct AdaptiveWeights
{
   double Trend;
   double Momentum;
   double Strength;
   double Market;
   double Execution;
};

AdaptiveWeights AIWeights =
{
   0.30,
   0.25,
   0.20,
   0.15,
   0.10
};

//==================================================

double ClampWeight(double value,double minValue=0.05,double maxValue=0.60)
{
   if(value<minValue)
      return minValue;

   if(value>maxValue)
      return maxValue;

   return value;
}

//==================================================

void NormalizeWeights()
{
   double total=
      AIWeights.Trend+
      AIWeights.Momentum+
      AIWeights.Strength+
      AIWeights.Market+
      AIWeights.Execution;

   if(total<=0.0)
      return;

   AIWeights.Trend/=total;
   AIWeights.Momentum/=total;
   AIWeights.Strength/=total;
   AIWeights.Market/=total;
   AIWeights.Execution/=total;
}

//==================================================

void ResetWeights()
{
   AIWeights.Trend     =0.30;
   AIWeights.Momentum  =0.25;
   AIWeights.Strength  =0.20;
   AIWeights.Market    =0.15;
   AIWeights.Execution =0.10;

   NormalizeWeights();
}

//==================================================

void AdjustWeights(
   double winRate,
   double drawdown,
   double profitFactor,
   double avgSlippage,
   double volatilityScore
)
{
   //----------------------------------------
   // WIN RATE
   //----------------------------------------

   if(winRate<35.0)
   {
      AIWeights.Trend+=0.05;
      AIWeights.Execution+=0.03;
      AIWeights.Momentum-=0.03;
   }
   else
   if(winRate<50.0)
   {
      AIWeights.Trend+=0.02;
      AIWeights.Execution+=0.01;
   }
   else
   if(winRate>70.0)
   {
      AIWeights.Momentum+=0.03;
      AIWeights.Strength+=0.02;
      AIWeights.Trend-=0.02;
   }

   //----------------------------------------
   // DRAWDOWN
   //----------------------------------------

   if(drawdown>10)
   {
      AIWeights.Execution+=0.04;
      AIWeights.Market+=0.03;
      AIWeights.Momentum-=0.03;
   }

   //----------------------------------------
   // PROFIT FACTOR
   //----------------------------------------

   if(profitFactor>2.0)
      AIWeights.Strength+=0.02;

   //----------------------------------------
   // SLIPPAGE
   //----------------------------------------

   if(avgSlippage>20)
   {
      AIWeights.Execution+=0.03;
      AIWeights.Market+=0.02;
   }

   //----------------------------------------
   // VOLATILITY
   //----------------------------------------

   if(volatilityScore>80)
   {
      AIWeights.Market+=0.04;
      AIWeights.Execution+=0.02;
   }

   //----------------------------------------
   // LIMITS
   //----------------------------------------

   AIWeights.Trend=
      ClampWeight(AIWeights.Trend);

   AIWeights.Momentum=
      ClampWeight(AIWeights.Momentum);

   AIWeights.Strength=
      ClampWeight(AIWeights.Strength);

   AIWeights.Market=
      ClampWeight(AIWeights.Market);

   AIWeights.Execution=
      ClampWeight(AIWeights.Execution);

   NormalizeWeights();

   PrintFormat(
      "[AI] Trend %.2f | Momentum %.2f | Strength %.2f | Market %.2f | Execution %.2f",
      AIWeights.Trend,
      AIWeights.Momentum,
      AIWeights.Strength,
      AIWeights.Market,
      AIWeights.Execution
   );
}

//==================================================

double GetTrendWeight()
{
   return AIWeights.Trend;
}

double GetMomentumWeight()
{
   return AIWeights.Momentum;
}

double GetStrengthWeight()
{
   return AIWeights.Strength;
}

double GetMarketWeight()
{
   return AIWeights.Market;
}

double GetExecutionWeight()
{
   return AIWeights.Execution;
}

AdaptiveWeights GetWeights()
{
   return AIWeights;
}

#endif