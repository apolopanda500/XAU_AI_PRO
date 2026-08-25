// XAU_AI_PRO v1.2.0
#ifndef PORTFOLIO_MANAGER_MQH
#define PORTFOLIO_MANAGER_MQH

#include "../Core/Config.mqh"

class CPortfolioManager
{
private:
static int    m_open_positions;
static double m_total_exposure;
static bool   m_initialized;

public:
static bool Init();

static bool CanOpen(string symbol);

static double CurrentPortfolioRisk();

static double SymbolRisk(string symbol);

static double TotalExposure();

static int OpenPositions();

static void Update();

static void LogPortfolio();
};

int    CPortfolioManager::m_open_positions = 0;
double CPortfolioManager::m_total_exposure = 0.0;
bool   CPortfolioManager::m_initialized = false;

bool CPortfolioManager::Init()
{
m_open_positions = 0;
m_total_exposure = 0.0;
m_initialized = true;

Update();

Print("[PORTFOLIO] PortfolioManager initialized");

return true;
}

bool CPortfolioManager::CanOpen(string symbol)
{
if(!m_initialized)
Init();

Update();

if(symbol == "")
return false;

int max_pos = MaxOpenPositions;

if(max_pos <= 0)
return false;

if(m_open_positions >= max_pos)
return false;

return true;
}

double CPortfolioManager::CurrentPortfolioRisk()
{
if(!m_initialized)
Init();

double balance =
AccountInfoDouble(
ACCOUNT_BALANCE
);

if(balance <= 0.0)
return 0.0;

double exposure =
MathAbs(m_total_exposure);

return(
exposure /
balance *
100.0
);
}

double CPortfolioManager::SymbolRisk(string symbol)
{
if(symbol == "")
return 0.0;

double profit = 0.0;

for(int i = PositionsTotal() - 1; i >= 0; i--)
{
ulong ticket =
PositionGetTicket(i);


  if(ticket == 0)
     continue;

  if(!PositionSelectByTicket(ticket))
     continue;

  if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
     continue;

  if(PositionGetString(POSITION_SYMBOL) != symbol)
     continue;

  profit +=
     PositionGetDouble(
        POSITION_PROFIT
     );


}

return profit;
}

double CPortfolioManager::TotalExposure()
{
if(!m_initialized)
Init();

return m_total_exposure;
}

int CPortfolioManager::OpenPositions()
{
if(!m_initialized)
Init();

return m_open_positions;
}

void CPortfolioManager::Update()
{
if(!m_initialized)
{
m_initialized = true;
}

m_open_positions = 0;
m_total_exposure = 0.0;

for(int i = PositionsTotal() - 1; i >= 0; i--)
{
ulong ticket =
PositionGetTicket(i);


  if(ticket == 0)
     continue;

  if(!PositionSelectByTicket(ticket))
     continue;

  if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
     continue;

  m_open_positions++;

  m_total_exposure +=
     PositionGetDouble(
        POSITION_PROFIT
     );


}
}

void CPortfolioManager::LogPortfolio()
{
Update();

PrintFormat(
"[PORTFOLIO] Open=%d | Exposure=%.2f | Risk=%.2f%%",
m_open_positions,
m_total_exposure,
CurrentPortfolioRisk()
);
}

#endif
