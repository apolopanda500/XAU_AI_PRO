//+------------------------------------------------------------------+
//| Monitoring/DiagGate.mqh                                          |
//| XAU_AI_PRO v1.2.153 (05/11/2026) - P1.17/P1.25/P1.114             |
//+------------------------------------------------------------------+
// PORTEIRO DE DIAGNOSTICO DO JOURNAL
//
// NAO decide nada, nao bloqueia trade, nao toca em risco nem em
// execucao. Decide apenas se uma linha de DIAGNOSTICO repetitiva
// volta a ser escrita no journal.
//
// ----------------------------------------------------------------
// PORQUE EXISTE (medido, nao estimado)
// ----------------------------------------------------------------
// Journal do backtest 7702617382101217572 (real ticks, XAUUSD M15
// com 11 simbolos), ficheiro Tester\logs\20261031.log:
//
//   842 277 112 bytes | ~3 050 000 linhas
//
// Distribuicao das tags (amostra de 24 MB / 91 143 linhas):
//
//   41,0%  sem tag  (RISK CALC USD, EXECUTION: LOTE DINAMICO,
//                    EXECUTION: SEM STOP NA ENTRADA,
//                    EXECUTION WARNING FORCA LOTE MINIMO,
//                    EXECUTION: SIMULACAO BLOQUEADA)
//   32,7%  [STATE]   997 000 linhas
//   24,5%  [RISK]    746 000 linhas
//    0,40% [SCANNER]  12 100 linhas  <-- alvo do P1.3
//
// Ou seja: o P1.3 (agregacao do scanner) optimizava 0,40% do
// volume. Os 98,2% restantes vinham de reavaliacoes por tick com
// desfecho IDENTICO - o simbolo era rejeitado sempre pelo mesmo
// motivo e com os mesmos numeros, e o bloco voltava inteiro ao
// journal em cada tick.
//
// Exemplo medido (ciclo repetido, valores iguais tick apos tick):
//   [STATE] USDCAD | SIMULATING -> SIGNAL_GENERATED
//   [STATE] USDCAD | SIGNAL_GENERATED -> VALIDATING
//   [STATE] USDCAD | VALIDATING -> RISK_CHECK
//   [RISK]  risco EFETIVO acima do pedido | pedido=0.75 ...
//   EXECUTION: SIMULACAO BLOQUEADA | Razao=Low probability ...
//
// ----------------------------------------------------------------
// CRITERIO
// ----------------------------------------------------------------
// Uma linha (simbolo + tag) so volta a sair quando o DESFECHO muda.
// Se o desfecho se mantiver, a linha e suprimida. `heartbeatSec`
// (opcional) forca uma saida periodica como prova de vida.
//
// O estado operacional nunca se perde: mudanca de desfecho sai na
// hora, e o primeiro desfecho de cada simbolo sai sempre.
//
// Em caso de duvida o portao LIBERTA (devolve true): uma tabela
// cheia ou um estado inconsistente nunca devem esconder journal.
//
// v1.2.153 - P1.114: tabela cheia passou a EVACUAR a chave usada ha
// mais tempo, em vez de desligar o portao ate ao fim da sessao. Medido
// pelo DiagGateSelfTest: a partir da 256a chave o portao devolvia true
// a tudo, e o journal voltava a crescer sem que nada o dissesse.
//+------------------------------------------------------------------+

#ifndef DIAG_GATE_MQH
#define DIAG_GATE_MQH

// Capacidade: 1 entrada por (simbolo + tag). 11 simbolos x ~8 tags
// de diagnostico = 88 entradas tipicas. 256 da folga larga.
#define DIAG_GATE_MAX 256

// P1.25: desfechos distintos lembrados por janela. Um ciclo de estados tem
// tipicamente 3..6 arestas (SIGNAL_GENERATED/VALIDATING/RISK_CHECK/SIMULATING
// /EXECUTION_READY/POSITION_OPEN). 8 cobre o ciclo inteiro com folga; quando
// enche, o desfecho mais antigo e esquecido (nunca se esconde um desfecho novo
// da janela corrente por falta de espaco).
#define DIAG_GATE_SEEN 8

// Janela usada quando o chamador pede heartbeatSec = 0 (silencio total antigo).
// Sem janela, um ciclo voltaria a escrever em cada tick: e exactamente o defeito
// que este patch corrige. 60 s mantem o journal legivel sem esconder mudanca.
#define DIAG_GATE_WINDOW_DEFAULT 60

struct DiagGateEntry
{
   string   key;                    // "SIMBOLO|TAG"
   string   outcome;                // ultimo desfecho registado
   datetime last;                   // quando esse desfecho foi registado
   string   seen[DIAG_GATE_SEEN];   // P1.25: desfechos JA vistos nesta janela
   int      seenCount;              // quantos desses estao preenchidos
   datetime windowStart;            // P1.25: inicio da janela corrente
   datetime lastUse;                // v1.2.153: ultima chamada (eviccao LRU)
};

DiagGateEntry g_diagGate[DIAG_GATE_MAX];
int           g_diagGateCount      = 0;
long          g_diagGateSuppressed = 0;   // linhas evitadas (auditoria)
long          g_diagGateEvicted    = 0;   // v1.2.153: chaves evacuadas por tabela cheia
datetime      g_diagGateLastEvictNotice = 0;   // v1.2.153: throttle do aviso de tabela cheia

//+------------------------------------------------------------------+
//| Procura a entrada de "simbolo|tag". -1 quando nao existe.        |
//+------------------------------------------------------------------+
int DiagGateFind(const string key)
{
   for(int i = 0; i < g_diagGateCount; i++)
   {
      if(g_diagGate[i].key == key)
         return i;
   }

   return -1;
}

//+------------------------------------------------------------------+
//| v1.2.153 - P1.114: indice da chave usada ha mais tempo.           |
//| -1 quando a tabela esta vazia. Nunca esconde journal: quem chama  |
//| evacua, insere a chave nova e devolve true.                       |
//+------------------------------------------------------------------+
int DiagGateEvictLRU()
{
   if(g_diagGateCount <= 0)
      return(-1);

   int      vitima     = 0;
   datetime maisAntigo = g_diagGate[0].lastUse;

   for(int i = 1; i < g_diagGateCount; i++)
   {
      if(g_diagGate[i].lastUse < maisAntigo)
      {
         maisAntigo = g_diagGate[i].lastUse;
         vitima     = i;
      }
   }

   return(vitima);
}

//+------------------------------------------------------------------+
//| Devolve true quando a linha de diagnostico pode ser escrita.     |
//|                                                                  |
//| symbol       : simbolo a que a linha se refere                   |
//| tag          : identificador curto do bloco ("STATE", "RISK"...) |
//| outcome      : desfecho. Igual ao anterior = linha suprimida.    |
//| heartbeatSec : 0 = so na mudanca de desfecho. >0 = tambem sai    |
//|                uma vez a cada N segundos, como prova de vida.    |
//+------------------------------------------------------------------+
bool DiagGateAllow(const string symbol, const string tag,
                   const string outcome, const int heartbeatSec = 0)
{
   const string key = symbol + "|" + tag;

   // P1.25: relogio que avanca sempre. TimeCurrent() e a hora do ultimo tick
   // (ver P1.24); com o mercado fechado a janela do heartbeat nunca vencia.
   datetime now     = (datetime)TimeLocal();
   int      janela  = (heartbeatSec > 0 ? heartbeatSec : DIAG_GATE_WINDOW_DEFAULT);

   int idx = DiagGateFind(key);

   // Primeira vez deste simbolo/tag: registra sempre.
   if(idx < 0)
   {
      // v1.2.153 (05/11/2026) - P1.114: MEDIDO pelo auto-teste
      // (DiagGateSelfTest.mq5, reprovado em C2 e C3 a 04/11 21:30): depois de
      // a tabela encher, o portao devolvia true a TODA a chave nova e ficava
      // desligado ate ao fim da sessao - o bloco C, que mede ciclos, passou a
      // medir um portao inexistente (3000 linhas em vez de 0). Agora liberta-se
      // a vaga da chave usada ha mais tempo: a chave nova continua a sair (nada
      // e escondido) e o portao continua a abafar as repeticoes.
      if(g_diagGateCount >= DIAG_GATE_MAX)
      {
         int vitima = DiagGateEvictLRU();

         if(vitima < 0)
            return(true);   // fail-open: erro do portao nunca esconde journal

         g_diagGateEvicted++;

         if(g_diagGateEvicted == 1 || (now - g_diagGateLastEvictNotice) >= 3600)
         {
            g_diagGateLastEvictNotice = now;
            Print("[DIAGGATE] tabela cheia | chaves=", g_diagGateCount,
                  " | libertei a chave usada ha mais tempo | evacuacoes=", g_diagGateEvicted,
                  " | o portao continua a abafar");
         }

         idx = vitima;
      }
      else
      {
         idx = g_diagGateCount;
         g_diagGateCount++;
      }

      g_diagGate[idx].key         = key;
      g_diagGate[idx].outcome     = outcome;
      g_diagGate[idx].last        = now;
      g_diagGate[idx].lastUse     = now;
      g_diagGate[idx].windowStart = now;
      g_diagGate[idx].seenCount   = 1;
      g_diagGate[idx].seen[0]     = outcome;

      return(true);
   }

   // v1.2.153 - P1.114: recencia para a eviccao. Uma chave que continua a ser
   // consultada nunca e a evacuada.
   g_diagGate[idx].lastUse = now;

   //--------------------------------------------------------------
   // P1.25: janela vencida -> recomeca a memoria de desfechos.
   //--------------------------------------------------------------
   if((now - g_diagGate[idx].windowStart) >= janela)
   {
      g_diagGate[idx].windowStart = now;
      g_diagGate[idx].last        = now;
      g_diagGate[idx].outcome     = outcome;
      g_diagGate[idx].seenCount   = 1;
      g_diagGate[idx].seen[0]     = outcome;

      return(true);
   }

   //--------------------------------------------------------------
   // P1.25: o desfecho ja foi escrito NESTA janela. E aqui que morre o
   // ciclo: A -> B -> C -> A -> B -> C passava inteiro porque cada aresta
   // difere da ANTERIOR; difere da anterior nao quer dizer que seja nova.
   //--------------------------------------------------------------
   for(int s = 0; s < g_diagGate[idx].seenCount; s++)
   {
      if(g_diagGate[idx].seen[s] == outcome)
      {
         g_diagGateSuppressed++;

         g_diagGate[idx].outcome = outcome;

         return(false);
      }
   }

   // Desfecho NOVO dentro da janela: e o sinal operacional, sai na hora.
   int slot = g_diagGate[idx].seenCount;

   if(slot >= DIAG_GATE_SEEN)
   {
      // Memoria cheia: esquece o mais antigo (posicao 0) e desloca.
      for(int k = 1; k < DIAG_GATE_SEEN; k++)
         g_diagGate[idx].seen[k - 1] = g_diagGate[idx].seen[k];

      slot = DIAG_GATE_SEEN - 1;
   }
   else
      g_diagGate[idx].seenCount++;

   g_diagGate[idx].seen[slot] = outcome;
   g_diagGate[idx].outcome    = outcome;
   g_diagGate[idx].last       = now;

   return(true);
}

//+------------------------------------------------------------------+
//| Uma linha de auditoria: quanto journal este portao evitou.       |
//+------------------------------------------------------------------+
string DiagGateSummary()
{
   return("[DIAGGATE] " + IntegerToString(g_diagGateCount) +
          " chaves activas | linhas suprimidas=" +
          IntegerToString(g_diagGateSuppressed) +
          " | evacuacoes=" + IntegerToString(g_diagGateEvicted) +
          " | janelas=" + IntegerToString(DIAG_GATE_WINDOW_DEFAULT) + "s/" +
          IntegerToString(DIAG_GATE_SEEN) + " desfechos");
}

#endif // DIAG_GATE_MQH
//+------------------------------------------------------------------+
