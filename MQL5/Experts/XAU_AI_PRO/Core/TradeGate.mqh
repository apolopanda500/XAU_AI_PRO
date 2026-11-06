//+------------------------------------------------------------------+
//| TradeGate.mqh                                                    |
//| XAU_AI_PRO - P1.61: fonte unica de verdade para negociar ou nao  |
//| Antes desta versao tres sitios respondiam a mesma pergunta com   |
//| criterios diferentes. Este ficheiro e o unico avaliador.         |
//+------------------------------------------------------------------+
#ifndef XAI_TRADE_GATE_MQH
#define XAI_TRADE_GATE_MQH

// P1.61 (v1.2.75). MEDIDO em 02/11/2026 no journal das 16 charts:
//   portao de OnTick (XAU_AI_PRO.mq5) -> barrava as 16 ordens e escrevia
//                                       'ALGO TRADING OFF' a cada 60s desde
//                                       06:05:05.800 (primeiro registo do dia);
//   ProductionChecklist item 2        -> PASS  (TERMINAL && CONTA);
//   ValidationChecklist item 13       -> BLOCKED (EA && TERMINAL);
//   terminal_get_info                 -> experts_trade_allowed = true.
// As tres leituras eram do mesmo instante. O botao Algoritmos estava LIGADO;
// o que estava desligado era a permissao do PROPRIO EA (MQL_TRADE_ALLOWED).
// P1.62 (v1.2.76) - CAUSA MEDIDA, HIPOTESE REJEITADA. O primeiro suspeito
// (template com expertmode sem o bit de trade) foi testado e NAO explica nada:
//   02/11 01:00 e 02:00 -> o EA negociou normalmente (log do terminal);
//   06:05:05.056        -> USDSGD recarregado apos recompilar; 0,7s depois vem
//                          o primeiro [TRADE BLOCK] do dia;
//   08:14:18-19         -> os 16 templates com expertmode=5 reaplicados e o bit
//                          continuou 0 em todos;
//   08:15:28            -> chart nova (USDDKK M30) anexada por API, sem
//                          template nenhum: tambem MQL_TRADE_ALLOWED=0;
//   08:16               -> o proprio chart, ao gravar template, escreve
//                          expertmode=0;
//   08:18               -> os .chr do perfil ativo tambem ja estavam a 0.
// Conclusao: expertmode de .tpl/.chr NAO e a permissao do programa. Este bit
// so se religa pela janela de propriedades do EA (caixa de negociacao
// algoritmica) ou por reanexacao manual pela GUI. O portao passa a dizer isso.
// P1.64 (v1.2.78) - MEDIDO no codigo: Evaluate() lia os quatro bits de
// PERMISSAO mas nunca TERMINAL_CONNECTED, por isso um terminal sem ligacao
// devolvia TG_OK (trading permitido) enquanto as checklists escreviam
// terminal desconectado. E os tres sitios que testavam o bit escreviam tres
// frases diferentes para o mesmo bit. Passa a existir TG_DISCONNECTED,
// testado ANTES dos outros quatro, e os tres sitios leem esta fonte.
// P1.65 (v1.2.79) - corrigida a frase de TG_MQL_OFF. A anterior mandava o
// operador a uma "caixa de negociacao algoritmica das propriedades do EA", que
// nao e o sitio medido: as 09:00 o terminal tinha experts_trade_allowed=true e
// TERMINAL_TRADE_ALLOWED=1, portanto o botao do terminal estava LIGADO e o que
// falta e o bit por programa. A frase passa a separar MEDIDO de HIPOTESE.
// P1.88 (v1.2.98) - MEDIDO em 03/11/2026 00:00:44-45 (journal do terminal e do EA):
// enquanto ESTE grafico (XAUUSD,M15) imprimia MQL_TRADE_ALLOWED=0, o grafico
// USDSEK,H1 executou 'SELL 0.13 USDCAD | Ticket 11205908727 | Result SUCCESS'
// (Retcode=10009) e o proprio XAUUSD registou '[STATE] USDCAD -> POSITION_OPEN'.
// Logo o bit NAO e do .ex5 nem da conta: e POR GRAFICO (uma instancia de EA).
// A frase de P1.65 dizia "por programa" e mandava religar o botao do terminal,
// que ja estava LIGADO - instrucao que nao podia resultar. Duas correcoes:
//  (1) a frase nomeia o sitio certo (propriedades do EA daquele grafico) e e curta;
//  (2) como a execucao e DELEGADA a uma instancia (PipelineIsMaster), o veredicto
//      das checklists passa a ser o da SUITE (EvaluateSuite) e nao o desta
//      instancia - era isso que reprovava 16/17 com a suite a negociar.
#ifndef SUITE_HEARTBEAT_TTL_SEC
   #define SUITE_HEARTBEAT_TTL_SEC 180
#endif
enum ETradeGate
{
   TG_OK           = 0,   // as tres permissoes ligadas
   TG_TERMINAL_OFF = 1,   // botao 'Algoritmos' do terminal OFF
   TG_ACCOUNT_OFF  = 2,   // conta/broker sem permissao de negociacao
   TG_MQL_OFF      = 3,   // o proprio EA sem permissao de negociacao
   TG_EXPERT_OFF   = 4,   // o broker nao permite negociacao por EA nesta conta
   TG_DISCONNECTED = 5    // sem ligacao ao servidor de negociacao (P1.64)
};

class CTradeGate
{
public:
   static bool Mql()      { return(MQLInfoInteger(MQL_TRADE_ALLOWED) != 0); }
   static bool Terminal() { return(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0); }
   static bool Account()  { return(AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) != 0); }
   static bool Expert()   { return(AccountInfoInteger(ACCOUNT_TRADE_EXPERT) != 0); }
   static bool Connected(){ return(TerminalInfoInteger(TERMINAL_CONNECTED) != 0); }

   // Ordem do diagnostico: primeiro a causa que o operador ve a olho (botao),
   // depois a conta, por fim a permissao do proprio programa.
   static ETradeGate Evaluate()
   {
      // P1.64: sem ligacao nao existe negociacao possivel.
      if(!Connected())
         return(TG_DISCONNECTED);
      if(!Terminal())
         return(TG_TERMINAL_OFF);
      if(!Account())
         return(TG_ACCOUNT_OFF);
      if(!Expert())
         return(TG_EXPERT_OFF);
      if(!Mql())
         return(TG_MQL_OFF);
      return(TG_OK);
   }

   static bool Ok() { return(Evaluate() == TG_OK); }

   // P1.88 (v1.2.98): veredicto ao nivel da SUITE.
   // A execucao e delegada a uma instancia (PipelineIsMaster). Se ESTA instancia
   // nao tem o bit mas outra tem e esta a bater o coracao do pipeline, a suite
   // consegue negociar. As causas que a delegacao NAO resolve (ligacao, terminal,
   // conta, broker) continuam a ser devolvidas tal como estao.
   static bool SuitePermitted()
   {
      if(Ok())
         return(true);
      string keyBeat = "XAI_PRO_PIPE_MASTER_"
                     + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN))
                     + "_T";
      if(!GlobalVariableCheck(keyBeat))
         return(false);
      datetime ultimo = (datetime)GlobalVariableGet(keyBeat);
      return((TimeLocal() - ultimo) < SUITE_HEARTBEAT_TTL_SEC);
   }

   static ETradeGate EvaluateSuite()
   {
      ETradeGate local = Evaluate();
      if(local == TG_OK)
         return(TG_OK);
      if(local == TG_DISCONNECTED || local == TG_TERMINAL_OFF
         || local == TG_ACCOUNT_OFF  || local == TG_EXPERT_OFF)
         return(local);
      // TG_MQL_OFF: pode estar apenas nesta instancia; a suite continua apta.
      if(SuitePermitted())
         return(TG_OK);
      return(local);
   }

   // Nota para o journal: quem esta a executar quando esta instancia nao pode.
   static string SuiteNote()
   {
      if(Ok())
         return("local");
      string key     = "XAI_PRO_PIPE_MASTER_"
                     + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
      string keyBeat = key + "_T";
      if(!GlobalVariableCheck(keyBeat))
         return("suite sem heartbeat de pipeline");
      datetime ultimo = (datetime)GlobalVariableGet(keyBeat);
      long     idade  = (long)(TimeLocal() - ultimo);
      long     dono   = GlobalVariableCheck(key) ? (long)GlobalVariableGet(key) : 0;
      return("suite via mestre=" + IntegerToString(dono)
             + " idade=" + IntegerToString(idade) + "s");
   }

   static string DescribeSuite(ETradeGate st)
   {
      if(st == TG_OK && !Ok())
         return("Trading permitido pela SUITE (delegado: " + SuiteNote() + ") | "
                + "este grafico: " + Cause(Evaluate()) + " | " + Bits());
      return(Describe(st));
   }

   // Valores crus: o operador ve os tres bits, nao uma interpretacao.
   static string Bits()
   {
      string b = "MQL_TRADE_ALLOWED=";
      b += (Mql() ? "1" : "0");
      b += " TERMINAL_TRADE_ALLOWED=";
      b += (Terminal() ? "1" : "0");
      b += " ACCOUNT_TRADE_ALLOWED=";
      b += (Account() ? "1" : "0");
      b += " ACCOUNT_TRADE_EXPERT=";
      b += (Expert() ? "1" : "0");
      b += " TERMINAL_CONNECTED=";
      b += (Connected() ? "1" : "0");
      return(b);
   }

   static string Cause(ETradeGate st)
   {
      if(st == TG_DISCONNECTED)
         return("Trading barrado pela LIGACAO: TERMINAL_CONNECTED=0 - terminal sem ligacao ao servidor de negociacao");
      if(st == TG_TERMINAL_OFF)
         return("Trading barrado pelo TERMINAL: botao 'Algoritmos' OFF (Ferramentas > Opcoes > Expert Advisors)");
      if(st == TG_ACCOUNT_OFF)
         return("Trading barrado pela CONTA: o broker nao permite negociacao nesta conta");
      if(st == TG_EXPERT_OFF)
         return("Trading barrado pelo BROKER: ACCOUNT_TRADE_EXPERT=0 - a conta nao tem permissao de negociacao por Expert Advisor");
      if(st == TG_MQL_OFF)
         return("PROGRAMA sem permissao: MQL_TRADE_ALLOWED=0 (bit POR GRAFICO; terminal e conta OK, a suite pode negociar). Religar em F7 > Comum > 'Permitir negociacao algoritmica'");
      return("Trading permitido");
   }

   static string Describe(ETradeGate st)
   {
      return(Cause(st) + " | " + Bits());
   }
};

#endif // XAI_TRADE_GATE_MQH