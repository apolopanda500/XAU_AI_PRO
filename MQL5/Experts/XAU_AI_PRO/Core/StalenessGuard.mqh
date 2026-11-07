#ifndef __XAI_STALENESS_GUARD_MQH__
#define __XAI_STALENESS_GUARD_MQH__
//+------------------------------------------------------------------+
//|                                            Core/StalenessGuard.mqh|
//|                XAU_AI_PRO - F2.9: cotacao velha nao opera         |
//+------------------------------------------------------------------+
// F2.9 do PLANO_10_10 (fase F2, BLOQUEANTE para conta real):
//   "Deteccao de desconexao/freeze | ultima cotacao velha -> nao opera"
//
// DUAS DECISOES ESTAO GRAVADAS AQUI (D-029 e D-064):
//
// 1) RELOGIO. A referencia e TimeTradeServer(), a MESMA escala de MqlTick.time,
//    com TimeCurrent() apenas como recurso final. TimeCurrent() congela quando
//    o feed morre: medir um relogio parado contra outro relogio parado da
//    sempre idade ~0, ou seja dava "cotacao fresca" exactamente no freeze que
//    este guarda existe para apanhar.
//
// 2) LIMITE. Nao e uma constante escondida no codigo: vem das inputs
//    EnableStaleDataGuard / MaxSymbolTickAgeSec (Core/Config.mqh), que ja eram
//    a fonte de verdade do SymbolDataFresh() do MarketScanner. Duas respostas
//    diferentes para a mesma pergunta era o defeito. O OnInit chama
//    CStalenessGuard::Configurar() e o valor passa a ser UM so em todo o EA.
//    Sem essa chamada (por exemplo num script de medicao) fica o valor de
//    recurso XAI_STALE_MAX_SEC.

// Valor de recurso: quando ninguem chamou Configurar() e como limite minimo
// aceitavel quando a input chega a zero.
#ifndef XAI_STALE_MAX_SEC
   #define XAI_STALE_MAX_SEC 120
#endif

// Estado deste programa compilado. Prefixo g_xaiStale para nao colidir com
// nenhuma global do EA.
bool g_xaiStaleAtivo  = true;
int  g_xaiStaleLimite = XAI_STALE_MAX_SEC;

class CStalenessGuard
  {
public:
   // Chamado uma vez no OnInit. limiteSegundos <= 0 mantem o valor de recurso.
   static void Configurar(const bool ativo, const int limiteSegundos)
     {
      g_xaiStaleAtivo = ativo;

      if(limiteSegundos > 0)
         g_xaiStaleLimite = limiteSegundos;
     }

   static bool Ativo()
     {
      return(g_xaiStaleAtivo);
     }

   static int Limite()
     {
      return(g_xaiStaleLimite);
     }

   // Idade do ultimo tick em segundos. -1 = nao foi possivel medir.
   static int IdadeSegundos(const string symbol)
     {
      if(symbol == "")
         return(-1);

      MqlTick cotacao;

      if(!SymbolInfoTick(symbol, cotacao))
         return(-1);

      if(cotacao.time <= 0)
         return(-1);

      datetime agora = TimeTradeServer();

      if(agora <= 0)
         agora = TimeCurrent();

      if(agora <= 0)
         return(-1);

      long idade = (long)agora - (long)cotacao.time;

      if(idade < 0)
         idade = 0;   // carimbo no futuro: feed adiantado, nao e motivo de veto

      return((int)idade);
     }

   // Fail-closed: sem leitura de tick tambem nao opera.
   static bool CotacaoVelha(const string symbol)
     {
      if(!g_xaiStaleAtivo)
         return(false);   // a input desligou a verja: nao veta

      if(g_xaiStaleLimite <= 0)
         return(false);

      int idade = IdadeSegundos(symbol);

      if(idade < 0)
         return(true);

      return(idade > g_xaiStaleLimite);
     }

   static string Diagnostico(const string symbol)
     {
      int idade = IdadeSegundos(symbol);

      if(idade < 0)
         return(StringFormat("%s | sem leitura de tick (SymbolInfoTick falhou) | limite=%ds", symbol, g_xaiStaleLimite));

      return(StringFormat("%s | idade=%ds | limite=%ds", symbol, idade, g_xaiStaleLimite));
     }
  };

#endif // __XAI_STALENESS_GUARD_MQH__
