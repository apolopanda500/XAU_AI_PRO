// XAU_AI_PRO v1.2.0
#ifndef BROKERINFO_MQH
#define BROKERINFO_MQH

//==================================================
// BROKER INFORMATION
//==================================================

string BrokerName      = "";
string BrokerCompany   = "";
string BrokerServer    = "";
string BrokerCurrency  = "";

bool InitBrokerInfo()
{
   BrokerName =
      AccountInfoString(
         ACCOUNT_COMPANY
      );

   BrokerCompany =
      TerminalInfoString(
         TERMINAL_COMPANY
      );

   BrokerServer =
      AccountInfoString(
         ACCOUNT_SERVER
      );

   BrokerCurrency =
      AccountInfoString(
         ACCOUNT_CURRENCY
      );

   Print("==============================");
   Print("BROKER INFORMATION");
   Print("Company  : ",BrokerName);
   Print("Terminal : ",BrokerCompany);
   Print("Server   : ",BrokerServer);
   Print("Currency : ",BrokerCurrency);
   Print("==============================");

   return true;
}

string GetBrokerName()
{
   return BrokerName;
}

string GetBrokerServer()
{
   return BrokerServer;
}

string GetBrokerCurrency()
{
   return BrokerCurrency;
}

#endif