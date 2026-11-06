//+------------------------------------------------------------------+
//|  AccountLogGate.mqh                                              |
//|  v1.2.86 (02/11/2026) - P1.73                                    |
//|  Janela de impressao por CONTA, em vez de por GRAFICO.           |
//+------------------------------------------------------------------+
//  MEDIDO (journal de 02/11/2026, 16 graficos com o mesmo EA):
//  depois do P1.72 cada instancia passou a imprimir a MESMA linha
//  1x/hora, o que da 16 linhas/hora por tag - o journal continuava a
//  repetir texto identico so porque ha 16 graficos. O throttle certo
//  nao e o tempo de cada grafico, e o tempo da CONTA.
//
//  Este modulo guarda a hora do ultimo print de cada tag num ficheiro
//  comum (FILE_COMMON): a primeira instancia que chega escreve, as
//  outras calam-se. Nao decide nada sobre trading - so decide se a
//  linha volta a sair no journal.
//
//  REGRA DE SEGURANCA: se o ficheiro comum falhar (bloqueado, disco,
//  permissao), devolve SEMPRE true. Um erro de log nunca pode esconder
//  informacao.
//+------------------------------------------------------------------+
#ifndef __ACCOUNT_LOG_GATE_MQH__
#define __ACCOUNT_LOG_GATE_MQH__

//+------------------------------------------------------------------+
//| v1.2.104 (03/11/2026) - P1.94                                    |
//| JANELA DE SESSAO: informacao que pertence a CONTA (versao,       |
//| corretora, caminhos, configuracao, diagnosticos, checklist) sai  |
//| UMA vez por sessao - nao uma vez por grafico e nao uma vez por   |
//| rajada de reload.                                                |
//| Em tester o gate e ignorado: cada passe tem de poder registar o  |
//| proprio retrato e o ficheiro FILE_COMMON e partilhado.           |
//+------------------------------------------------------------------+
#define LOG_JANELA_SESSAO_SEC 43200

bool LogSessaoPodeImprimir(const string tag)
  {
   if(MQLInfoInteger(MQL_TESTER))
      return(true);

   return(AccountLogGatePodeImprimir("sess_" + tag, LOG_JANELA_SESSAO_SEC));
  }

//+------------------------------------------------------------------+
//| Devolve true se esta instancia deve imprimir a tag agora.        |
//| tag       : nome curto e estavel (ex. "tradeblock", "session")   |
//| janelaSeg : segundos minimos entre dois prints da MESMA tag      |
//+------------------------------------------------------------------+
bool AccountLogGatePodeImprimir(const string tag,const int janelaSeg)
  {
   if(janelaSeg<=0)
      return(true);

   // P1.102 (05/11/2026): o TESTER partilha esta pasta FILE_COMMON com a
   // producao e escrevia aqui o tempo SIMULADO do backtest. MEDIDO: o ficheiro
   // Common\Files\XAU_AI_PRO\loggate_ai_stale.bin continha 2026-09-09 20:00:00
   // enquanto o terminal vivia 2026-11-04 21:14. Com um valor no PASSADO,
   // "agora >= ultimo + janela" e sempre verdade, logo o throttle por conta
   // deixava de filtrar: duas linhas [AI] PREDICAO VENCIDA com 20 s de
   // diferenca na mesma instancia (21:09:52 e 21:10:12) apesar da janela de
   // 3600 s, e 129 linhas/dia antes do P2.00. No tester cada passe tem o seu
   // proprio journal e nao ha conta partilhada a proteger, por isso o gate
   // devolve SEMPRE true e deixa de escrever no ficheiro comum. A producao
   // recupera o throttle de 1x/hora por tag e por conta.
   if(MQLInfoInteger(MQL_TESTER))
      return(true);

   string nome="XAU_AI_PRO\\loggate_"+tag+".bin";
      // P2.05: os 15 graficos do terminal abrem o MESMO ficheiro de gate em
   // threads diferentes. Sem partilha declarada a segunda abertura pode
   // devolver INVALID_HANDLE e o gate cai no fail-open, o que devolve
   // SEMPRE true e desliga o throttle por conta.
   int h=FileOpen(nome,FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE)
     {
      // Fail-open continua a ser a regra (erro de log nunca suprime),
      // mas deixa de ser invisivel: no maximo 1 linha por hora por
      // instancia, com a tag, a janela e o codigo do erro.
      static datetime s_ultimoAvisoFail=0;
      datetime agoraFail=MQLInfoInteger(MQL_TESTER) ? TimeCurrent() : TimeLocal();
      int errFail=GetLastError();
      if(s_ultimoAvisoFail==0 || agoraFail>=s_ultimoAvisoFail+3600)
        {
         s_ultimoAvisoFail=agoraFail;
         Print("[DIAG] LOGGATE falhou | tag=",tag," | janela=",janelaSeg," | err=",errFail," | fail-open: linha desta chamada nao foi filtrada");
        }
      return(true);                     // falha de ficheiro NUNCA suprime
     }

   datetime agora = MQLInfoInteger(MQL_TESTER) ? TimeCurrent() : TimeLocal();
   datetime ultimo=0;

   if(FileSize(h)>=(int)sizeof(long))
     {
      if(FileSeek(h,0,SEEK_SET))
         ultimo=(datetime)FileReadLong(h);
     }

   // agora < ultimo = hora do servidor recuou (reconexao/rollover):
   // trata como desconhecido e deixa passar uma vez.
   bool pode=(ultimo==0 || agora>=ultimo+janelaSeg || agora<ultimo);

   if(pode)
     {
      FileSeek(h,0,SEEK_SET);
      FileWriteLong(h,(long)agora);
     }

   FileClose(h);
   return(pode);
  }

//+------------------------------------------------------------------+
//| v1.2.92 (02/11/2026) - P1.79                                    |
//| Retrato de ARRANQUE: o primeiro grafico do reload escreve o      |
//| bloco inteiro, os outros ficam calados. Cache por instancia: a   |
//| janela e avaliada UMA vez, no primeiro uso. 120 s (nao 3600)     |
//| porque colapsa a rajada do reload e um reinicio isolado 5 min    |
//| depois volta a imprimir o retrato.                              |
//+------------------------------------------------------------------+
bool LogInicioDetalhe()
  {
   static int cache = -1;

   if(cache < 0)
      cache = (MQLInfoInteger(MQL_TESTER) || AccountLogGatePodeImprimir("inicio_detalhe", LOG_JANELA_SESSAO_SEC)) ? 1 : 0;

   return(cache == 1);
  }

#endif // __ACCOUNT_LOG_GATE_MQH__