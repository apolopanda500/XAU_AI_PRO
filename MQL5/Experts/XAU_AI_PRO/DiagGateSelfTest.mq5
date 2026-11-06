//+------------------------------------------------------------------+
//| DiagGateSelfTest.mq5                                             |
//| XAU_AI_PRO v1.2.42 - P1.17 | v1.2.153 - P1.114                   |
//+------------------------------------------------------------------+
// AUTO-TESTE DO PORTAO DE DIAGNOSTICO
//
// NAO NEGOCEIA. Nao cria, modifica nem fecha ordem ou posicao.
// Nao le conta, nao le risco, nao depende de simbolo. Exercita
// apenas DiagGateAllow()/DiagGateSummary(), que sao funcoes puras
// sobre uma tabela global em memoria.
//
// Motivo: o portao foi compilado no EA mas nunca executou. Se
// suprimir a primeira ocorrencia, ou suprimir mudanca de desfecho,
// todas as medicoes seguintes do journal ficam invalidas. Este
// script prova o comportamento antes de confiar nele.
//
// v1.2.153 - P1.114: A ORDEM DOS BLOCOS E PARTE DO TESTE.
// MEDIDO a 04/11 21:30 no journal do expert: o resultado saia
// "[DIAGGATE-TEST] fim | chaves=256 | suprimidas=4 | falhas=4 |
// REPROVADO", com C2 (ciclo repetido suprime 1/2/3) a devolver true e
// C3 (3000 repeticoes -> 0 linhas) a devolver 3000 linhas. Nao era o
// portao a falhar a supressao: era o TESTE a medir um portao desligado,
// porque o bloco A8 (300 chaves) enchia as 256 vagas e o codigo antigo,
// com a tabela cheia, devolvia true a TODA a chave nova. O bloco que
// enche a tabela passa para o FIM (bloco F) e passa a medir o contrato
// novo: a tabela cheia evacua a chave usada ha mais tempo, a chave nova
// sai (nada e escondido) e o portao continua a abafar.
//
// Esperado: 4 supressoes no bloco A (A2, A4, A5, A7); o ciclo C escreve
// 3 arestas e suprime as 3 seguintes e as 3000 voltas seguintes; o bloco
// F prova que a tabela cheia nao desliga o portao.
//+------------------------------------------------------------------+
#property description "Auto-teste de Monitoring/DiagGate.mqh (P1.17/P1.25/P1.114). Nao negoceia."
#property version     "1.002"

#include "Monitoring/DiagGate.mqh"

int g_falhas = 0;

//+------------------------------------------------------------------+
void Check(const string nome, const bool obtido, const bool esperado)
{
   bool ok = (obtido == esperado);
   if(!ok)
      g_falhas++;

   Print("[DIAGGATE-TEST] ", (ok ? "OK   " : "FALHA"), " | ", nome,
         " | obtido=", (obtido ? "true" : "false"),
         " | esperado=", (esperado ? "true" : "false"));
}

//+------------------------------------------------------------------+
void OnStart()
{
   Print("[DIAGGATE-TEST] inicio | TimeCurrent=", TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
         " | DIAG_GATE_MAX=", DIAG_GATE_MAX, " | DIAG_GATE_SEEN=", DIAG_GATE_SEEN);

   // v1.2.153: a contabilidade e lida por DELTA desta marca, para a ordem dos
   // blocos poder mudar sem invalidar a conta.
   long suprimidasInicio = g_diagGateSuppressed;

   //--------------------------------------------- A1..A7: regra basica
   // A1 - primeiro desfecho de cada simbolo/tag sai sempre.
   Check("A1 primeiro desfecho sai", DiagGateAllow("XAUUSD", "TESTE", "estado-A", 0), true);

   // A2 - mesmo desfecho, sem heartbeat: suprime.
   Check("A2 desfecho igual suprime", DiagGateAllow("XAUUSD", "TESTE", "estado-A", 0), false);

   // A3 - desfecho MUDOU: sai na hora (sinal operacional).
   Check("A3 desfecho novo sai", DiagGateAllow("XAUUSD", "TESTE", "estado-B", 0), true);

   // A4 - heartbeat pedido mas ainda nao venceu: suprime.
   Check("A4 heartbeat nao vencido suprime", DiagGateAllow("XAUUSD", "TESTE", "estado-B", 3600), false);

   // A5 - heartbeat 0 (silencio total) continua a suprimir.
   Check("A5 heartbeat 0 suprime", DiagGateAllow("XAUUSD", "TESTE", "estado-B", 0), false);

   // A6 - a chave e por SIMBOLO: outro simbolo com o mesmo desfecho sai.
   Check("A6 outro simbolo sai", DiagGateAllow("EURUSD", "TESTE", "estado-B", 0), true);

   // A7 - e o segundo do novo simbolo suprime (chave independente).
   Check("A7 outro simbolo suprime no repeteco", DiagGateAllow("EURUSD", "TESTE", "estado-B", 0), false);

   //--------------------------------------------- A9: contabilidade
   // Suprimidas esperadas neste bloco: A2, A4, A5, A7 = 4.
   Check("A9 contador de suprimidas == 4", (g_diagGateSuppressed - suprimidasInicio) == 4, true);

   //--------------------------------------------- A10: resumo
   string s = DiagGateSummary();
   Print("[DIAGGATE-TEST] resumo -> ", s);
   Check("A10 resumo tem prefixo", StringFind(s, "[DIAGGATE]") == 0, true);
   Check("A10 resumo conta suprimidas", StringFind(s, "linhas suprimidas=4") > 0, true);

   //--------------------------------------------- C1..C4: CICLO (P1.25)
   // O defeito medido: SIGNAL_GENERATED -> VALIDATING -> RISK_CHECK -> ...
   // Cada aresta difere da anterior, logo o portao antigo libertava todas.
   Check("C1 ciclo aresta 1 sai",  DiagGateAllow("CICLO", "STATE", "A -> B", 14400), true);
   Check("C1 ciclo aresta 2 sai",  DiagGateAllow("CICLO", "STATE", "B -> C", 14400), true);
   Check("C1 ciclo aresta 3 sai",  DiagGateAllow("CICLO", "STATE", "C -> A", 14400), true);

   Check("C2 ciclo repetido suprime 1", DiagGateAllow("CICLO", "STATE", "A -> B", 14400), false);
   Check("C2 ciclo repetido suprime 2", DiagGateAllow("CICLO", "STATE", "B -> C", 14400), false);
   Check("C2 ciclo repetido suprime 3", DiagGateAllow("CICLO", "STATE", "C -> A", 14400), false);

   // C3 - 1000 voltas ao ciclo na mesma janela: nenhuma linha nova.
   int libertadas = 0;
   for(int volta = 0; volta < 1000; volta++)
   {
      if(DiagGateAllow("CICLO", "STATE", "A -> B", 14400)) libertadas++;
      if(DiagGateAllow("CICLO", "STATE", "B -> C", 14400)) libertadas++;
      if(DiagGateAllow("CICLO", "STATE", "C -> A", 14400)) libertadas++;
   }
   Check("C3 3000 repeticoes do ciclo -> 0 linhas", libertadas == 0, true);

   // C4 - aresta NOVA dentro da janela continua a sair (nada de esconder
   // sinal operacional por causa da memoria do ciclo).
   Check("C4 aresta nova na mesma janela sai", DiagGateAllow("CICLO", "STATE", "C -> EXECUTION_READY", 14400), true);

   //--------------------------------------------- F: TABELA CHEIA (P1.114)
   // Este bloco corre no FIM, de proposito: enche a tabela e a partir daqui
   // todas as chaves sao novas. O contrato medido e (a) nunca esconder uma
   // chave nova e (b) nunca desligar o portao por a tabela estar cheia.
   long evacuacoesInicio = g_diagGateEvicted;
   int  totalChaves      = DIAG_GATE_MAX + 50;

   Print("[DIAGGATE-TEST] bloco F | encher a tabela com ", totalChaves, " chaves");

   int permitidas = 0;
   for(int i = 0; i < totalChaves; i++)
   {
      if(DiagGateAllow("S" + IntegerToString(i), "CHEIO", "x", 0))
         permitidas++;
   }

   Check("F1 tabela cheia nao esconde chave nova", permitidas == totalChaves, true);
   Check("F2 tabela fica saturada em DIAG_GATE_MAX", g_diagGateCount == DIAG_GATE_MAX, true);
   Check("F3 evacuacoes contadas", (g_diagGateEvicted - evacuacoesInicio) >= (totalChaves - DIAG_GATE_MAX), true);

   // F4/F5 - o ponto do P1.114: cheia, o portao continua a abafar.
   Check("F4 chave nova apos tabela cheia sai", DiagGateAllow("NOVO", "CHEIO", "x", 0), true);
   Check("F5 mesma chave logo depois SUPRIME", DiagGateAllow("NOVO", "CHEIO", "x", 0), false);

   // F6/F7 - custo assumido da eviccao: a chave evacuada sai mais uma vez.
   // O bloco A e o bloco C ja tinham chaves na tabela, logo a vitima da
   // eviccao nao e S0: e a chave usada ha mais tempo. Em vez de a supor,
   // descobre-se por inspeccao - medido a 04/11 23:42, o teste antigo exigia
   // S0 e acusava FALHA com o codigo correcto, porque S0 nunca saiu.
   int ausente = -1;
   for(int i = 0; i < totalChaves; i++)
   {
      if(DiagGateFind("S" + IntegerToString(i) + "|CHEIO") < 0)
      {
         ausente = i;
         break;
      }
   }
   Check("F6 existe chave evacuada fora da tabela", ausente >= 0, true);

   if(ausente >= 0)
   {
      string chaveEvacuada = "S" + IntegerToString(ausente);
      Print("[DIAGGATE-TEST] chave evacuada medida -> ", chaveEvacuada);
      Check("F6 chave evacuada volta a sair uma vez", DiagGateAllow(chaveEvacuada, "CHEIO", "x", 0), true);
      Check("F7 e volta a suprimir no repeteco", DiagGateAllow(chaveEvacuada, "CHEIO", "x", 0), false);
   }

   // F8 - auditoria visivel: o resumo publica as evacuacoes.
   string s2 = DiagGateSummary();
   Print("[DIAGGATE-TEST] resumo final -> ", s2);
   Check("F8 resumo publica evacuacoes", StringFind(s2, "evacuacoes=") > 0, true);

   //--------------------------------------------- veredicto
   Print("[DIAGGATE-TEST] fim | chaves=", g_diagGateCount,
         " | suprimidas=", g_diagGateSuppressed,
         " | evacuacoes=", g_diagGateEvicted,
         " | falhas=", g_falhas,
         " | ", (g_falhas == 0 ? "APROVADO" : "REPROVADO"));
}
//+------------------------------------------------------------------+
