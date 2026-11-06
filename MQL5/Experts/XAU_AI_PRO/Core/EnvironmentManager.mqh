// XAU_AI_PRO v1.2.9
#ifndef ENVIRONMENTMANAGER_MQH
#define ENVIRONMENTMANAGER_MQH

//==================================================
// ENVIRONMENT MANAGER
//==================================================

bool IsTester=false;
bool IsOptimization=false;
bool IsVisualMode=false;
bool IsRealAccount=false;
bool IsDemoAccount=false;

//==================================================
// INIT
//==================================================

bool InitEnvironment()
{

   IsTester=
      MQLInfoInteger(MQL_TESTER);

   IsOptimization=
      MQLInfoInteger(MQL_OPTIMIZATION);

   IsVisualMode=
      MQLInfoInteger(MQL_VISUAL_MODE);

   IsRealAccount=
      AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL;

   IsDemoAccount=
      AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO;

   if(LogInicioDetalhe()) Print("[ENV] tester=",(IsTester?"1":"0")," otimizacao=",(IsOptimization?"1":"0"),
         " visual=",(IsVisualMode?"1":"0")," conta_real=",(IsRealAccount?"1":"0"),
         " conta_demo=",(IsDemoAccount?"1":"0"));

   return true;

}

//==================================================
// GETTERS
//==================================================

bool InTester()
{
   return IsTester;
}

bool InOptimization()
{
   return IsOptimization;
}

bool InVisual()
{
   return IsVisualMode;
}

bool IsReal()
{
   return IsRealAccount;
}

bool IsDemo()
{
   return IsDemoAccount;
}

#endif