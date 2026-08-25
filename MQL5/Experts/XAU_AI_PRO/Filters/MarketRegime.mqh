// XAU_AI_PRO v1.2.0
#ifndef MARKETREGIME_MQH
#define MARKETREGIME_MQH

//==================================================
// MARKET REGIME (SUBSTITUTO do antigo MarketAnalyzer)
//
// ANTES (orfaos): MarketRegime.mqh criava handles
// iMA proprios (MarketMAFastPeriod/MarketMASlowPeriod)
// duplicando FastEMA/SlowEMA e TrendFilter, com guard
// errado (MARKETANALYZER_MQH).
//
// AGORA: camada de leitura de regime SEM handles e SEM
// inputs proprios. Reutiliza os modulos ativos:
//   - TrendFilter  -> direcao (EMA200 H1, multi-symbol)
//   - VolatilityFilter (ATR) -> volatilidade
//   - ADX          -> forca da tendencia
//==================================================

#include "../Core/Config.mqh"
#include "../Filters/TrendFilter.mqh"
#include "../Indicators/VolatilityFilter.mqh"
#include "../Indicators/ADX.mqh"

//==================================================
// REGIME ENUM
//==================================================

enum MarketRegimeType
{
   REGIME_NONE       = 0,
   REGIME_TREND_UP   = 1,
   REGIME_TREND_DOWN = -1
};

//==================================================
// DIRECAO DA TENDENCIA (via TrendFilter - EMA200 H1)
//==================================================

MarketRegimeType GetMarketRegime(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   if(TrendBuy(symbol))
      return REGIME_TREND_UP;

   if(TrendSell(symbol))
      return REGIME_TREND_DOWN;

   return REGIME_NONE;
}

//==================================================
// FORCA DA TENDENCIA (via ADX)
//==================================================

bool IsStrongTrend(string symbol="", double minADX=20.0)
{
   if(symbol=="")
      symbol=_Symbol;

   double adx = GetADX(symbol);

   if(adx < 0.0)
      return false;

   return (adx >= minADX);
}

//==================================================
// VOLATILIDADE (ATR como % do preco)
// Percentual do preco -> comparavel entre simbolos
// (ouro, FX, indices, crypto), diferente de pontos fixos.
//==================================================

double MarketVolatilityPercent(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   double atr = GetATR(symbol);
   double price = SymbolInfoDouble(symbol, SYMBOL_BID);

   if(atr <= 0.0 || price <= 0.0)
      return -1.0;

   return (atr / price) * 100.0;
}

//==================================================
// VOLATILIDADE SAUDAVEL (dentro da faixa)
// default: ATR entre 0.05% e 2.0% do preco
//==================================================

bool IsHealthyVolatility(string symbol="", double minPct=0.05, double maxPct=2.0)
{
   if(symbol=="")
      symbol=_Symbol;

   double vol = MarketVolatilityPercent(symbol);

   if(vol < 0.0)
      return false;

   return (vol >= minPct && vol <= maxPct);
}

//==================================================
// QUALIDADE DE MERCADO
// Tendencia presente + volatilidade saudavel
// (equivalente funcional do antigo IsGoodMarket)
//==================================================

bool IsGoodMarket(string symbol="")
{
   if(symbol=="")
      symbol=_Symbol;

   if(GetMarketRegime(symbol) == REGIME_NONE)
      return false;

   if(!IsHealthyVolatility(symbol))
      return false;

   return true;
}

//==================================================
// NOME LEGIVEL
//==================================================

string MarketRegimeToString(MarketRegimeType regime)
{
   if(regime == REGIME_TREND_UP)
      return "TREND_UP";

   if(regime == REGIME_TREND_DOWN)
      return "TREND_DOWN";

   return "RANGING";
}

#endif
