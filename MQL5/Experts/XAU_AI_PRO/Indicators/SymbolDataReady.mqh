// XAU_AI_PRO v1.2.152
#ifndef SYMBOLDATAREADY_MQH
#define SYMBOLDATAREADY_MQH

//==================================================
// v1.2.152 (05/11/2026) - P1.113: PORTEIRO DE SERIE POR SIMBOLO
//
// MEDIDO no journal do expert as 23:16:40 de 04/11, build v1.2.151, nos
// graficos recem-carregados do reload:
//   [ATR] LEITURA SUSPEITA | GBPUSD | ATR=29.454290 | preco=1.34881 | ATR%=2183.72 | grafico=GBPUSD | devolvido=0.0
//   [DATA] SEM LEITURA | GBPUSD | ATR=0.000000 | ADX=33.77 | RSI=82.72
//   [DATA] SEM LEITURA | USDJPY | ATR=0.000000 | ADX=33.77 | RSI=82.72
//   [DATA] SEM LEITURA | AUDUSD | ATR=0.000000 | ADX=33.77 | RSI=82.72
//   [DATA] SEM LEITURA | USDCAD | ATR=0.000000 | ADX=33.77 | RSI=82.72
//   [DATA] SEM LEITURA | NZDUSD | ATR=0.000000 | ADX=33.77 | RSI=82.72
//   [DATA] SEM LEITURA | USDCHF | ATR=0.000000 | ADX=33.77 | RSI=82.72
//   [DATA] SEM LEITURA | USDCNH | ATR=0.000000 | ADX=33.77 | RSI=82.72
// SETE pares diferentes com o MESMO ADX (33.77) e o MESMO RSI (82.72) no
// mesmo segundo, e o ATR do OURO (29.454290) lido num par cotado a 1.34881.
// Nao existe mercado em que sete instrumentos distintos tenham o ADX igual
// ao centesimo: o que existe e um handle de indicador a devolver a serie de
// OUTRO simbolo enquanto a serie pedida ainda nao esta construida.
//
// Este ficheiro nao corrige o terminal. Faz tres coisas:
//  (1) XAI_SymbolDataReady recusa a leitura quando nao consegue provar que
//      a serie do simbolo pedido existe (sincronizada e com barras);
//  (2) XAI_LeituraDeOutroSimbolo / XAI_ValoresIndistinguiveis detectam o caso
//      em que o valor lido para um simbolo estrangeiro e indistinguivel do
//      valor do simbolo do grafico, que e a assinatura medida da contaminacao;
//  (3) XAI_WaitSeriesReady espera pela serie ANTES de criar o handle, que e
//      a origem medida do defeito.
// Em todos os casos o consumidor recebe "sem leitura" - nunca um numero com
// aparencia de verdade. Mesma filosofia do P1.112 (ATR impossivel).
//==================================================

bool XAI_SymbolDataReady(string symbol, ENUM_TIMEFRAMES timeframe = PERIOD_CURRENT)
{
   if(symbol == "")
      symbol = _Symbol;

   // O simbolo do grafico tem serie por definicao: o grafico existe.
   if(symbol == _Symbol)
      return true;

   if(timeframe == PERIOD_CURRENT)
      timeframe = (ENUM_TIMEFRAMES)Period();

   if(!SymbolSelect(symbol, true))
      return false;

   if(!SymbolIsSynchronized(symbol))
      return false;

   long sincronizada = 0;

   if(!SeriesInfoInteger(symbol, timeframe, SERIES_SYNCHRONIZED, sincronizada))
      return false;

   if(sincronizada == 0)
      return false;

   return (Bars(symbol, timeframe) > 0);
}

//==================================================
// Duas leituras do MESMO indicador, em dois simbolos diferentes, iguais ao
// bit sao contaminacao e nao coincidencia. O limiar e folgado (1e-9) para
// apanhar tambem arredondamentos do terminal.
//==================================================
bool XAI_LeituraDeOutroSimbolo(double valorDoSimbolo, double valorDoGrafico)
{
   if(valorDoSimbolo <= 0.0 || valorDoGrafico <= 0.0)
      return false;

   return (MathAbs(valorDoSimbolo - valorDoGrafico) < 0.000000001);
}

//==================================================
// v1.2.152 (05/11/2026) - P1.113: ESPERA PELA SERIE ANTES DO HANDLE
//
// O handle de um simbolo estrangeiro nasce ligado a serie que existir no
// instante da criacao. Se a serie do par ainda nao estiver construida, o
// terminal responde com a serie do GRAFICO e essa ligacao sobrevive ate o
// handle ser libertado - e a assinatura medida na v1.2.151 depois do reload
// do perfil (ATR do ouro em sete pares).
// Criar o handle so depois de provar que existe serie no timeframe tira a
// causa, em vez de tratar o sintoma.
//
// Sleep e proibido em indicadores, logo a espera so corre em EA e script.
// O tempo maximo e curto (400 ms) e acontece no maximo uma vez por simbolo,
// na criacao do handle - nunca na leitura.
//==================================================
bool XAI_WaitSeriesReady(string symbol, ENUM_TIMEFRAMES timeframe = PERIOD_CURRENT, int maxMs = 400)
{
   if(symbol == "")
      symbol = _Symbol;

   if(timeframe == PERIOD_CURRENT)
      timeframe = (ENUM_TIMEFRAMES)Period();

   if(symbol == _Symbol)
      return (Bars(symbol, timeframe) > 0);

   int waited = 0;

   while(true)
     {
      if(SymbolSelect(symbol, true))
        {
         long sincronizada = 0;

         if(SeriesInfoInteger(symbol, timeframe, SERIES_SYNCHRONIZED, sincronizada) && sincronizada != 0)
            if(Bars(symbol, timeframe) > 0)
               return true;
        }

      if(waited >= maxMs)
         return false;

      if(MQLInfoInteger(MQL_PROGRAM_TYPE) == PROGRAM_INDICATOR)
         return false;

      Sleep(20);
      waited += 20;
     }
}

//==================================================
// v1.2.152 - P1.113: MESMO VALOR EM DOIS SIMBOLOS
//
// Dois indicadores com o mesmo valor em dois simbolos diferentes, ao limite
// da precisao, nao sao coincidencia: e a assinatura medida da contaminacao.
// A tolerancia e relativa (1e-5) porque os dois valores chegam por
// arredondamentos diferentes - medido, ATR 29.454290 (estrangeiro) contra
// 29.454286 (do grafico), que uma tolerancia absoluta de 1e-9 nao via.
//==================================================
bool XAI_ValoresIndistinguiveis(double a, double b)
{
   if(a <= 0.0 || b <= 0.0)
      return false;

   double escala = MathMax(MathAbs(a), MathAbs(b));

   return (MathAbs(a - b) <= escala * 0.00001);
}

#endif
