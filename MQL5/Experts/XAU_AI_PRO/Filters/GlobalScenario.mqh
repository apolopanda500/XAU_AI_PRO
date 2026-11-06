// XAU_AI_PRO v1.2.22
#ifndef GLOBALSCENARIO_MQH
#define GLOBALSCENARIO_MQH

//==================================================
// CENARIO GLOBAL - CLASSE DE ATIVO, SESSAO E CORRELACAO
// (v1.2.22 - 29/10/2026)
//
// Pedido do dono: "adaptar o EA para todos os tipos de cenarios globais".
// A v1.2.21 respondeu "que TIPO de mercado e este" (tendencia/lateral/
// volatilidade). Faltavam as duas perguntas que so existem quando o EA roda
// em MUITOS ativos ao mesmo tempo - que e o caso aqui: 16 graficos.
//
// FALHA 1 (medida): CORRELACAO NAO EXISTE NO PROJETO.
//   Dos 16 graficos, quase todos sao pares contra o dolar
//   (USDCLP, USDCOP, USDSEK, USDJPY, USDCHF, USDCZK, USDCAD, USDCNH,
//    AUDUSD, NZDUSD, GBPUSD, USDBRL, USDRUB, USDSGD).
//   `MaxOpenPositions=50` e um teto de CONTAGEM, nao de risco: com 50 vagas o
//   EA pode comprar dolar em USDJPY, USDCHF, USDCAD, USDCNH, USDSEK... ao
//   mesmo tempo. Isso nao sao 5 operacoes: e UMA aposta no dolar com 5x o
//   tamanho. Quando o dolar vira, as 5 perdem juntas e o limite de perda
//   diaria e atingido por um unico movimento.
//   `EnableManualExposureGuard` (PositionManager) protege apenas o MESMO
//   simbolo com posicao MANUAL. Nao olha moeda, nem direcao, nem correlacao.
//   `CPortfolioManager` mede exposicao total, nao exposicao POR MOEDA.
//
// FALHA 2 (medida): A JANELA DE SESSAO E DE OURO, EM HORA DE SERVIDOR.
//   `TradeStartHour..TradeEndHour` e `AvoidHoursList="0,20"` foram calibrados
//   em ai_feedback.csv com 402 trades de XAUUSD. Aplicar essa janela a USDJPY,
//   USDCNH ou USDBRL e herdar uma medicao de outro ativo. Pior: hora de
//   SERVIDOR muda com o horario de verao do broker, entao a mesma janela
//   cobre horas diferentes ao longo do ano. Aqui a sessao passa a ser lida em
//   GMT (TimeGMT), que nao depende do broker nem de DST.
//
// O QUE ESTA CAMADA FAZ (e o que ela NAO faz):
//   * classifica o ativo (metal, major, minor, exotico, indice, cripto);
//   * reduz o LOTE conforme a sessao, por classe de ativo;
//   * VETA a entrada quando ela aumentaria a exposicao numa moeda que ja esta
//     carregada no mesmo sentido, acima de um teto EM DINHEIRO.
//
// Ela nunca aumenta lote (todos os fatores <= 1.0) e nunca desliga protecao.
// O veto e de CORRELACAO, nao de direcao: comprar EURUSD e comprar GBPUSD sao
// ambas "USD curto" e contam juntas; comprar USDJPY e o oposto e nao conta.
//==================================================

#include "../Core/Config.mqh"

enum ENUM_ASSET_CLASS
{
   ASSET_UNKNOWN = 0,   // nao classificado (ficha incompleta)
   ASSET_METAL   = 1,   // XAU, XAG, ouro/prata
   ASSET_MAJOR   = 2,   // USD + moeda G8 (EURUSD, USDJPY, ...)
   ASSET_MINOR   = 3,   // cruz das majors (EURGBP, AUDNZD, ...)
   ASSET_EXOTIC  = 4,   // par com moeda fora do G8 (USDTRY, USDBRL, ...)
   ASSET_INDEX   = 5,   // indice / CFD sem perna de moeda
   ASSET_CRYPTO  = 6    // cripto
};

enum ENUM_SESSION_BUCKET
{
   SESSION_CLOSED = 0,  // fim de semana
   SESSION_ASIA   = 1,  // 00-07 GMT
   SESSION_LONDON = 2,  // 07-12 GMT
   SESSION_NY     = 3,  // 12-21 GMT (inclui o cruzamento Londres/NY)
   SESSION_LATE   = 4   // 21-24 GMT (depois do fecho de NY)
};

//==================================================
// NOME LEGIVEL
//==================================================
string AssetClassToString(ENUM_ASSET_CLASS c)
{
   if(c == ASSET_METAL)  return("METAL");
   if(c == ASSET_MAJOR)  return("MAJOR");
   if(c == ASSET_MINOR)  return("MINOR");
   if(c == ASSET_EXOTIC) return("EXOTICO");
   if(c == ASSET_INDEX)  return("INDICE");
   if(c == ASSET_CRYPTO) return("CRIPTO");

   return("DESCONHECIDO");
}

string SessionBucketToString(ENUM_SESSION_BUCKET s)
{
   if(s == SESSION_ASIA)   return("ASIA");
   if(s == SESSION_LONDON) return("LONDRES");
   if(s == SESSION_NY)     return("NOVA_IORQUE");
   if(s == SESSION_LATE)   return("POS_NY");

   return("FECHADO");
}

//==================================================
// MOEDAS DE REFERENCIA (liquidez alta)
//
// Usado so para separar major/minor de exotico. A lista e de MOEDAS, nao de
// pares, porque e a moeda que define liquidez: EURGBP e minor, EURTRY e
// exotico.
//==================================================
bool CurrencyIsG8(const string c)
{
   if(c == "usd") return(true);
   if(c == "eur") return(true);
   if(c == "gbp") return(true);
   if(c == "jpy") return(true);
   if(c == "chf") return(true);
   if(c == "aud") return(true);
   if(c == "nzd") return(true);
   if(c == "cad") return(true);

   return(false);
}

//==================================================
// PERNAS DO SIMBOLO (base e cotacao)
//
// Lidas da FICHA do simbolo, nunca do nome. Nome de simbolo tem sufixo de
// broker (`EURUSD.b`, `EURUSD#`, `EURUSDm`) e qualquer parsing de string
// quebra nele - o mesmo erro que ja quebrou o mapa de spread em 08/10/2026.
//==================================================
bool SymbolLegs(string symbol, string &base, string &quote)
{
   base  = "";
   quote = "";

   if(symbol == "")
      symbol = _Symbol;

   base  = SymbolInfoString(symbol, SYMBOL_CURRENCY_BASE);
   quote = SymbolInfoString(symbol, SYMBOL_CURRENCY_PROFIT);

   StringToLower(base);
   StringToLower(quote);

   if(base == "" || quote == "")
      return(false);

   return(true);
}

//==================================================
// CLASSE DO ATIVO
//==================================================
ENUM_ASSET_CLASS AssetClassOf(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   string base  = "";
   string quote = "";

   if(!SymbolLegs(symbol, base, quote))
      return(ASSET_UNKNOWN);

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

   if(point <= 0.0)
      return(ASSET_UNKNOWN);

   // Cripto: o caminho do simbolo diz.
   string path = SymbolInfoString(symbol, SYMBOL_PATH);
   StringToLower(path);

   if(StringFind(path, "crypto") >= 0 || StringFind(path, "cripto") >= 0)
      return(ASSET_CRYPTO);

   // Metal: base XAU/XAG/XPT/XPD (ISO 4217 dos metais preciosos).
   if(base == "xau" || base == "xag" || base == "xpt" || base == "xpd")
      return(ASSET_METAL);

   // Indice/CFD: base igual a cotacao. Se as pernas sao iguais nao ha
   // correlacao de moeda a proteger - fica INDICE para o log explicar.
   if(base == quote)
      return(ASSET_INDEX);

   // Forex: as duas pernas tem 3 letras.
   if(StringLen(base) == 3 && StringLen(quote) == 3)
   {
      // Ter USD na perna NAO basta para ser major. MEDIDO no journal em
      // 29/10/2026 22:21: a primeira versao classificou USDSEK, USDCNH e
      // USDBRL como MAJOR so porque a perna base era `usd`. Sao EXOTICOS: a
      // liquidez quem define e a OUTRA moeda, nao o dolar. O rotulo errado
      // desligava a reducao de lote de exotico fora das sessoes liquidas.
      if(base == "usd" || quote == "usd")
      {
         string outra = (base == "usd") ? quote : base;

         return(CurrencyIsG8(outra) ? ASSET_MAJOR : ASSET_EXOTIC);
      }

      if(CurrencyIsG8(base) && CurrencyIsG8(quote))
         return(ASSET_MINOR);

      return(ASSET_EXOTIC);
   }

   // Cripto negociada contra USD (BTCUSD, ETHUSD): base com 3+ letras e
   // desconhecida na lista de moedas.
   if(StringLen(base) > 3 && !CurrencyIsG8(base))
      return(ASSET_CRYPTO);

   return(ASSET_UNKNOWN);
}

//==================================================
// SESSAO ATUAL EM GMT
//
// Fonte: TimeGMT(), nao TimeCurrent(). A hora do servidor do broker muda com
// o horario de verao dele; GMT nao. A janela de Londres e de NY e a mesma em
// janeiro e em julho, para qualquer broker.
//
// Fronteiras (UTC, aproximadas - sao janelas de liquidez, nao de relogio):
//   00-07 Asia | 07-12 Londres | 12-21 Nova Iorque | 21-24 pos-NY
//==================================================
ENUM_SESSION_BUCKET SessionBucketNow()
{
   MqlDateTime tm;

   TimeToStruct(TimeGMT(), tm);

   if(tm.day_of_week == 0 || tm.day_of_week == 6)
      return(SESSION_CLOSED);

   if(tm.hour < 7)
      return(SESSION_ASIA);

   if(tm.hour < 12)
      return(SESSION_LONDON);

   if(tm.hour < 21)
      return(SESSION_NY);

   return(SESSION_LATE);
}

//==================================================
// FATOR DE LOTE POR SESSAO + CLASSE
//
// Nunca maior que 1.0. O piso (SessionLotFloor) existe para a sessao nunca
// zerar o lote por conta propria: quem decide nao operar e a validacao, com
// motivo escrito no journal. Um lote zero silencioso viraria "lote invalido"
// e o dono nao saberia por que.
//==================================================
double SessionLotFactor(string symbol="")
{
   if(!EnableSessionLotAdaptation)
      return(1.0);

   if(symbol == "")
      symbol = _Symbol;

   ENUM_SESSION_BUCKET b = SessionBucketNow();
   ENUM_ASSET_CLASS    c = AssetClassOf(symbol);

   double f = 1.0;

   if(b == SESSION_ASIA)
      f = SessionLotAsia;
   else if(b == SESSION_LONDON)
      f = SessionLotLondon;
   else if(b == SESSION_NY)
      f = SessionLotNY;
   else if(b == SESSION_LATE)
      f = SessionLotLate;
   else
      f = SessionLotClosed;

   // Exotico/minor fora das sessoes liquidas: o spread abre e a profundidade
   // fecha. A reducao e ADICIONAL, nao substituta.
   if((c == ASSET_EXOTIC || c == ASSET_MINOR) &&
      (b == SESSION_ASIA || b == SESSION_LATE))
   {
      f *= SessionLotExoticOffHours;
   }

   if(f <= 0.0)
      f = SessionLotFloor;

   if(f < SessionLotFloor)
      f = SessionLotFloor;

   if(f > 1.0)
      f = 1.0;

   return(f);
}

//==================================================
// RISCO NOMINAL DE UMA ENTRADA
//
// Usado como estimativa do risco da entrada PROPOSTA. Nao usa
// RiscoPorTradeUsd() porque aquela funcao ja desconta o envelope aberto: aqui
// queremos o risco CHEIO que a entrada pretende ocupar.
//==================================================
double GlobalNominalRiskUsd()
{
   double risco = RiskPerTradeUsd;

   if(RiskPerTradePercent > 0.0)
   {
      double b = AccountInfoDouble(ACCOUNT_BALANCE);

      if(b > 0.0)
         risco = b * RiskPerTradePercent / 100.0;
   }

   return(risco > 0.0 ? risco : 0.0);
}

//==================================================
// RISCO (MOEDA DA CONTA) DE UMA POSICAO ABERTA
//
// Mesma matematica de RiscoAbertoUSD() em Core/Config.mqh: distancia
// entrada->SL convertida por TICK_VALUE/TICK_SIZE. Posicao SEM stop continua
// ocupando o envelope e e medida pelo risco nominal configurado - sem isso
// toda entrada stopless somaria zero e o teto nunca encheria.
//==================================================
double GlobalPositionRiskUsd(const double open, const double vol, const double sl, const long type)
{
   if(open <= 0.0 || vol <= 0.0)
      return(0.0);

   string sym = PositionGetString(POSITION_SYMBOL);

   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   double tv    = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts    = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);

   if(point <= 0.0 || tv <= 0.0 || ts <= 0.0)
      return(GlobalNominalRiskUsd());

   double ref = sl;

   if(ref <= 0.0)
   {
      if(StopLossPoints <= 0)
         return(GlobalNominalRiskUsd());

      double d = (double)StopLossPoints * point;
      ref = (type == POSITION_TYPE_BUY) ? (open - d) : (open + d);
   }

   double pontos = MathAbs(open - ref) / point;

   return((tv / ts) * point * pontos * vol);
}

//==================================================
// EXPOSICAO POR MOEDA E SENTIDO
//
// dir = +1 -> a moeda esta LONGA | dir = -1 -> a moeda esta CURTA.
//
// Comprar EURUSD = EUR longo e USD curto. Vender EURUSD = o inverso.
// Comprar USDJPY = USD longo e JPY curto.
// Entao "comprar EURUSD" e "comprar GBPUSD" somam em USD CURTO - que e
// exatamente o risco real, e o que `MaxOpenPositions` nunca mediu.
//==================================================
double CurrencyRiskUsd(const string ccy, const int dir)
{
   if(ccy == "" || dir == 0)
      return(0.0);

   double total = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);

      if(tk == 0 || !PositionSelectByTicket(tk))
         continue;

      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      string sym = PositionGetString(POSITION_SYMBOL);
      string b   = "";
      string q   = "";

      if(!SymbolLegs(sym, b, q))
         continue;

      if(b == q)              // indice / CFD sem perna de moeda
         continue;

      long   type   = PositionGetInteger(POSITION_TYPE);
      bool   compra = (type == POSITION_TYPE_BUY);
      double risco  = GlobalPositionRiskUsd(PositionGetDouble(POSITION_PRICE_OPEN),
                                            PositionGetDouble(POSITION_VOLUME),
                                            PositionGetDouble(POSITION_SL),
                                            type);

      if(risco <= 0.0)
         continue;

      if(b == ccy)
      {
         int d = compra ? 1 : -1;

         if(d == dir)
            total += risco;
      }
      else if(q == ccy)
      {
         int d = compra ? -1 : 1;

         if(d == dir)
            total += risco;
      }
   }

   return(total);
}

int CurrencyTradesOnSide(const string ccy, const int dir)
{
   if(ccy == "" || dir == 0)
      return(0);

   int total = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);

      if(tk == 0 || !PositionSelectByTicket(tk))
         continue;

      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      string sym = PositionGetString(POSITION_SYMBOL);
      string b   = "";
      string q   = "";

      if(!SymbolLegs(sym, b, q))
         continue;

      if(b == q)
         continue;

      bool compra = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);

      if(b == ccy && (compra ? 1 : -1) == dir)
         total++;
      else if(q == ccy && (compra ? -1 : 1) == dir)
         total++;
   }

   return(total);
}

//==================================================
// GUARDA DE CORRELACAO
//
// Testa as DUAS pernas do simbolo proposto. Se qualquer uma delas ja esta
// carregada no mesmo sentido acima do teto, a entrada e vetada.
//
// Dois tetos, porque os dois erros acontecem:
//   * MaxCorrelatedTrades      -> contagio de CONTAGEM (5 pares iguais);
//   * MaxCorrelatedRiskPercent -> contagio de TAMANHO em dinheiro.
// Qualquer um dos dois zerado desliga aquela checagem.
//
// `reason` sempre sai preenchida: o scanner escreve no journal.
//==================================================
bool CurrencyExposureGuard(string symbol, int signal, string &reason)
{
   reason = "";

   if(!EnableCurrencyExposureGuard)
      return(true);

   if(signal == 0)
      return(true);

   if(symbol == "")
      symbol = _Symbol;

   string base  = "";
   string quote = "";

   if(!SymbolLegs(symbol, base, quote))
      return(true);

   if(base == quote)
      return(true);

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);

   if(balance <= 0.0)
      return(true);

   double cap  = (MaxCorrelatedRiskPercent > 0.0)
                 ? balance * MaxCorrelatedRiskPercent / 100.0
                 : 0.0;
   double novo = GlobalNominalRiskUsd();
   int    dir  = (signal == 1) ? 1 : -1;

   for(int k = 0; k < 2; k++)
   {
      string ccy  = (k == 0) ? base : quote;
      int    lado = (k == 0) ? dir : -dir;

      if(ccy == "")
         continue;

      int    qtd   = CurrencyTradesOnSide(ccy, lado);
      double atual = CurrencyRiskUsd(ccy, lado);

      if(MaxCorrelatedTrades > 0 && qtd >= MaxCorrelatedTrades)
      {
         reason = "CORRELACAO | " + ccy + (lado > 0 ? " LONGA" : " CURTA") +
                  " ja tem " + IntegerToString(qtd) + " posicoes (teto " +
                  IntegerToString(MaxCorrelatedTrades) + ")";
         return(false);
      }

      if(cap > 0.0 && (atual + novo) > cap)
      {
         reason = "CORRELACAO | " + ccy + (lado > 0 ? " LONGA" : " CURTA") +
                  " risco " + DoubleToString(atual, 2) +
                  " + " + DoubleToString(novo, 2) +
                  " > teto " + DoubleToString(cap, 2);
         return(false);
      }
   }

   return(true);
}

//==================================================
// LINHA GLOBAL PARA O JOURNAL
//
// Responde "em que mundo este EA esta operando agora": classe do ativo,
// sessao em GMT e quanto de cada moeda ja esta carregado. Throttle de 5 min
// por simbolo: este dado muda devagar, e o journal ja tem volume demais.
//==================================================
void GlobalScenarioLog(string symbol, string contexto="")
{
   if(!EnableGlobalScenarioLog)
      return;

   if(symbol == "")
      symbol = _Symbol;

   static string   ultimoSim[64];
   static datetime ultimoTs[64];
   static int      usados = 0;

   datetime agora = TimeCurrent();
   int slot = -1;

   for(int i = 0; i < usados; i++)
   {
      if(ultimoSim[i] != symbol)
         continue;

      if((agora - ultimoTs[i]) < 3600)
         return;

      slot = i;
      break;
   }

   if(slot < 0)
   {
      if(usados >= 64)
         return;

      slot = usados;
      ultimoSim[usados] = symbol;
      usados++;
   }

   ultimoTs[slot] = agora;

   // P2.01 (03/11/2026): a linha [GLOBAL] saia uma vez por simbolo a cada
   // 5 minutos, ou seja 11 linhas por ciclo e ~3 000 por dia com 15 graficos
   // a percorrer a mesma lista. Classe, sessao, fator de lote e exposicao
   // mudam devagar; passa a 1x/hora por CONTA e por simbolo.
   if(!AccountLogGatePodeImprimir("global_" + symbol, 3600))
      return;

   string base  = "";
   string quote = "";
   SymbolLegs(symbol, base, quote);

   double rBase  = (base  == "") ? 0.0 : MathMax(CurrencyRiskUsd(base, 1), CurrencyRiskUsd(base, -1));
   double rQuote = (quote == "") ? 0.0 : MathMax(CurrencyRiskUsd(quote, 1), CurrencyRiskUsd(quote, -1));

   Print("[GLOBAL] ", symbol,
         " | classe=", AssetClassToString(AssetClassOf(symbol)),
         " | sessao=", SessionBucketToString(SessionBucketNow()),
         " GMT=", TimeToString(TimeGMT(), TIME_MINUTES),
         " | lote x", DoubleToString(SessionLotFactor(symbol), 2),
         " | exp ", base, "=", DoubleToString(rBase, 2),
         " | ", quote, "=", DoubleToString(rQuote, 2),
         " | teto=", DoubleToString(MaxCorrelatedRiskPercent, 2), "%",
         (contexto == "" ? "" : " | " + contexto));
}

//==================================================
// HORAS PROIBIDAS EM GMT (v1.2.23 - 29/10/2026)
//
// O PROBLEMA MEDIDO
// `AvoidHoursList="0,20"` foi calibrada em hora de SERVIDOR, com evidencia de
// ai_feedback.csv (402 trades). Duas coisas estavam erradas nisso:
//
// 1) O NUMERO NAO QUER DIZER O QUE ELE ACHA QUE QUER.
//    Este servidor esta em GMT+2 (medido em 29/10/2026 22:23 local:
//    TimeGMT=01:23, servidor=03:23). Entao "hora 0 do servidor" = GMT 22
//    (depois do fecho de NY, liquidez fina - banir faz sentido) e
//    "hora 20 do servidor" = GMT 18, que e MEIO DA SESSAO DE NOVA IORQUE.
//    Para ouro, o prejuizo medido na hora 20 pode ser deriva de fim de NY;
//    para EURUSD e GBPUSD, GMT 18 e o melhor horario do dia. Banir isso em
//    11 pares e transportar uma medicao de outro ativo e de outra sessao.
//
// 2) O NUMERO ANDA COM O HORARIO DE VERAO DO BROKER.
//    MetaQuotes-Demo esta em GMT+2 no inverno e GMT+3 no verao. A MESMA lista
//    "0,20" bane GMT 22/18 no inverno e GMT 21/17 no verao. A regra nao
//    descreve um horario de mercado: descreve um ponteiro de relogio do
//    broker. Em janeiro e em julho ela protege momentos diferentes.
//
// A CORRECAO
// A lista passa a ser escrita em GMT, que nao depende de broker nem de DST.
// O padrao "18,22" e o EQUIVALENTE CONGELADO do que a lista antiga fazia
// hoje (GMT+2), para nao mudar o comportamento no dia da atualizacao. Quem
// quiser refinar por classe usa `AvoidHoursByClass` com evidencia propria -
// o padrao e vazio, ou seja: nenhuma regra nova e inventada aqui.
//
// `EnableAvoidHoursGMT=false` volta ao comportamento antigo (hora de
// servidor) sem apagar nada.
//==================================================

//==================================================
// HORA GMT ATUAL
//==================================================
int GmtHourNow()
{
   MqlDateTime tm;

   TimeToStruct(TimeGMT(), tm);

   return(tm.hour);
}

//==================================================
// LISTA "h1,h2,h3" -> contem a hora?
//==================================================
bool HourInCsvList(const int hour, const string list)
{
   string src = list;

   StringTrimLeft(src);
   StringTrimRight(src);
   StringToLower(src);

   if(src == "" || src == "off" || src == "none")
      return(false);

   string parts[];
   int n = StringSplit(src, ',', parts);

   for(int i = 0; i < n; i++)
   {
      string p = parts[i];
      StringTrimLeft(p);
      StringTrimRight(p);

      if(p == "")
         continue;

      int h = (int)StringToInteger(p);

      if(h < 0 || h > 23)
         continue;

      if(h == hour)
         return(true);
   }

   return(false);
}

//==================================================
// REGRA POR CLASSE: "METAL:22,23;EXOTICO:21,22,23"
//
// Formato proposital: a classe vem ANTES das horas, porque a pergunta certa e
// "que horas sao ruins PARA ESTE TIPO DE ATIVO", nao "que horas sao ruins".
// Classe sem regra nao herda a de outra: herda a lista geral.
//==================================================
bool HourInClassListGmt(const string classe, const int hour)
{
   string src = AvoidHoursByClass;

   StringTrimLeft(src);
   StringTrimRight(src);

   if(src == "")
      return(false);

   string regras[];
   int n = StringSplit(src, ';', regras);

   for(int i = 0; i < n; i++)
   {
      string regra = regras[i];
      StringTrimLeft(regra);
      StringTrimRight(regra);

      if(regra == "")
         continue;

      string kv[];
      int k = StringSplit(regra, ':', kv);

      if(k != 2)
         continue;

      string nome = kv[0];
      StringTrimLeft(nome);
      StringTrimRight(nome);
      StringToUpper(nome);

      string alvo = classe;
      StringToUpper(alvo);

      if(StringCompare(nome, alvo, false) != 0)
         continue;

      return(HourInCsvList(hour, kv[1]));
   }

   return(false);
}

//==================================================
// HORA PROIBIDA - versao global
//
// Substitui `IsAvoidedHour()` (SessionFilter) no ValidationEngine. A antiga
// continua existindo no projeto e continua sendo usada quando
// `EnableAvoidHoursGMT=false`, para o dono poder voltar atras em um clique.
//==================================================
bool IsAvoidedHourGlobal(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   if(!EnableAvoidHoursGMT)
   {
      // Legado: hora de SERVIDOR, que deriva com o DST do broker.
      MqlDateTime tm;
      TimeToStruct(TimeCurrent(), tm);

      return(HourInCsvList(tm.hour, AvoidHoursList));
   }

   int hourGmt = GmtHourNow();

   if(HourInCsvList(hourGmt, AvoidHoursGMT))
      return(true);

   return(HourInClassListGmt(AssetClassToString(AssetClassOf(symbol)), hourGmt));
}

// Texto para o journal: diz QUAL regra barrou e em que fuso, senao o dono
// volta a nao saber se o veto veio do relogio do broker ou do mercado.
string AvoidedHourDetail(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   if(!EnableAvoidHoursGMT)
   {
      MqlDateTime tm;
      TimeToStruct(TimeCurrent(), tm);

      return("servidor=" + IntegerToString(tm.hour) + "h | lista=" + AvoidHoursList);
   }

   int hourGmt = GmtHourNow();
   string classe = AssetClassToString(AssetClassOf(symbol));

   if(HourInCsvList(hourGmt, AvoidHoursGMT))
      return("GMT=" + IntegerToString(hourGmt) + "h | lista=" + AvoidHoursGMT);

   if(HourInClassListGmt(classe, hourGmt))
      return("GMT=" + IntegerToString(hourGmt) + "h | regra da classe " + classe);

   return("GMT=" + IntegerToString(hourGmt) + "h | classe " + classe);
}

#endif
