// XAU_AI_PRO v1.2.9 - MARKET PULSE (volume + velocidade do preco)
#ifndef MARKETPULSE_MQH
#define MARKETPULSE_MQH

#include "../Core/Config.mqh"
#include "../Indicators/VolatilityFilter.mqh"

//==================================================
// REGIME DE MOVIMENTO (29/10/2026)
//==================================================
// Pedido do dono: quando ha VOLUME e o preco corre, o EA tem que EXECUTAR
// RAPIDO — abrir, deixar a tendencia confirmar e SAIR no lucro. Quando o
// volume e normal, ele espera o preco andar e trava o stop na entrada ou
// acima dela.
//
// Este modulo responde UMA pergunta: "o mercado esta em disparada AGORA?"
//   volume     -> ticks da vela atual / media das ultimas PulseVolumeLookback
//   velocidade -> |close[1] - close[1+PulseVelocityBars]| medido em ATRs
//
// Regra de ouro: sem dado (mercado fechado, historico curto, ATR zero) o
// resultado e PULSE_NORMAL. "Nao sei" NUNCA vira "disparada" — o modo rapido
// mexe em lote e em saida, entao ele so liga com medicao real.
enum ENUM_PULSE_REGIME
{
   PULSE_NORMAL  = 0,   // volume/velocidade normais: modo paciente
   PULSE_FAST    = 1,   // volume alto + preco rapido: modo rapido
   PULSE_EXTREME = 2    // disparada forte: modo rapido com lote reduzido
};

string PulseRegimeName(ENUM_PULSE_REGIME r)
{
   if(r == PULSE_EXTREME)
      return("EXTREMO");

   if(r == PULSE_FAST)
      return("RAPIDO");

   return("NORMAL");
}

//==================================================
// VOLUME RELATIVO (x vezes a media)
//==================================================
double PulseVolumeRatio(string symbol)
{
   int lookback = (PulseVolumeLookback > 2) ? PulseVolumeLookback : 20;

   long vol[];
   ArraySetAsSeries(vol, true);

   int copied = CopyTickVolume(symbol, PERIOD_CURRENT, 0, lookback + 1, vol);

   if(copied < 5)
      return(0.0);

   double soma = 0.0;
   int    n    = 0;

   for(int i = 1; i < copied; i++)
   {
      soma += (double)vol[i];
      n++;
   }

   if(n <= 0 || soma <= 0.0)
      return(0.0);

   double media = soma / (double)n;
   double atual = (double)vol[0];

   // Vela atual sem tick ainda: usa a ultima fechada em vez de zero.
   if(atual <= 0.0)
      atual = (double)vol[1];

   if(media <= 0.0)
      return(0.0);

   return(atual / media);
}

//==================================================
// VELOCIDADE DO PRECO (em ATRs)
//==================================================
double PulseVelocityATR(string symbol)
{
   double atr = GetATR(symbol);

   if(atr <= 0.0)
      return(0.0);

   int barras = (PulseVelocityBars > 0) ? PulseVelocityBars : 3;

   double close[];
   ArraySetAsSeries(close, true);

   int preciso = barras + 2;

   if(CopyClose(symbol, PERIOD_CURRENT, 0, preciso, close) < preciso)
      return(0.0);

   double deslocamento = MathAbs(close[1] - close[1 + barras]);

   return(deslocamento / atr);
}

//==================================================
// REGIME ATUAL
//==================================================
ENUM_PULSE_REGIME GetMarketPulse(string symbol, double &volRatioOut, double &velOut)
{
   volRatioOut = 0.0;
   velOut      = 0.0;

   if(!EnableMarketPulse)
      return(PULSE_NORMAL);

   if(symbol == "")
      return(PULSE_NORMAL);

   volRatioOut = PulseVolumeRatio(symbol);
   velOut      = PulseVelocityATR(symbol);

   if(volRatioOut <= 0.0 || velOut <= 0.0)
      return(PULSE_NORMAL);

   double pisoVolume     = (PulseVolumeSpikeMult  > 0.0) ? PulseVolumeSpikeMult  : 1.8;
   double pisoVelocidade = (PulseVelocityATRMult  > 0.0) ? PulseVelocityATRMult  : 0.6;
   double fatorExtremo   = (PulseExtremeFactor    > 1.0) ? PulseExtremeFactor    : 1.8;

   bool volumeAlto    = (volRatioOut >= pisoVolume);
   bool velocidadeAlta = (velOut >= pisoVelocidade);

   if(!volumeAlto || !velocidadeAlta)
      return(PULSE_NORMAL);

   if(velOut >= pisoVelocidade * fatorExtremo && volRatioOut >= pisoVolume * fatorExtremo)
      return(PULSE_EXTREME);

   return(PULSE_FAST);
}

//==================================================
// RESUMO PARA LOG
//==================================================
string MarketPulseSummary(string symbol)
{
   double volR = 0.0;
   double velA = 0.0;

   ENUM_PULSE_REGIME reg = GetMarketPulse(symbol, volR, velA);

   return(StringFormat("Regime=%s | Volume=x%.2f | Velocidade=%.2fatr",
                       PulseRegimeName(reg), volR, velA));
}

#endif
