//+------------------------------------------------------------------+
//| KillSwitch.mqh                                                   |
//| XAU_AI_PRO - F2.1 do PLANO_10_10 (bloqueante para conta real)    |
//+------------------------------------------------------------------+
// PROBLEMA QUE ESTE FICHEIRO FECHA
// ---------------------------------
// MEDIDO em 06/11/2026: busca por 'KillSwitch|Halt|Freeze|Panic|
// EmergencyStop' em toda a arvore do EA devolvia ZERO ocorrencias. O
// PLANO_10_10 (F2.1) exige "kill switch manual e automatico: 1 clique/palavra
// para fechar tudo; testado" e o GATE F2 e bloqueante para conta real. Ou seja:
// o projecto nao podia ir a conta real por falta deste mecanismo, e nao por
// falta de sinais.
//
// Os gates existentes NAO substituem este interruptor:
//   * CTradeGate  -> permissoes (terminal/conta/programa). Nao e uma decisao
//                    do operador, e uma condicao externa.
//   * AutoTrade   -> input do grafico, exige reconfigurar o EA no grafico.
//   * CircuitBreaker / SafetyManager / EquityProtection -> reagem a CONDICOES
//                    (falhas, perda diaria, drawdown). Nenhum responde a
//                    "para tudo agora" por ordem humana.
//
// DUAS VIAS, PORQUE UMA SO NAO CHEGA
// ----------------------------------
// 1) MANUAL, persistente: existe ou nao existe o ficheiro
//      <terminal>\MQL5\Files\XAU_AI_PRO\KILL_SWITCH.flag
//    O conteudo decide a gravidade:
//      * qualquer conteudo (ou vazio)  -> bloqueia ENTRADAS, mantem posicoes
//      * conteudo com FECHAR ou CLOSE  -> bloqueia ENTRADAS e FECHA tudo
//    Apagar o ficheiro rearma. O estado sobrevive a reinicio do EA, que e o
//    que se quer num interruptor de emergencia.
// 2) AUTOMATICO, em memoria: CKillSwitch::ArmarAutomatico(motivo). Fica
//    armado ate o EA reiniciar. Nao escreve ficheiro de proposito: um
//    lockout PERSISTENTE escrito por automatismo, com um bug, deixaria o
//    sistema parado sem ninguem perceber por que. Quem quiser persistencia
//    escreve o ficheiro a mao - as duas vias nao se confundem.
//
// PORQUE TAMBEM NO OnTimer
// ------------------------
// MEDIDO em 06/11/2026 23:59:58 (hora do servidor): o mercado fechou a sexta e
// o journal do EA parou as 18:58:59 locais. Sem tick nao ha OnTick, logo um
// kill switch que so vivesse no OnTick estaria MORTO exactamente quando o
// operador mais precisa dele (fim de semana, simbolo congelado, servidor em
// baixo). O EA ja tem EventSetTimer(30) e o OnTimer corre sem ticks, portanto
// a sonda corre la tambem. Isto cobre tambem o F2.9 (deteccao de freeze).
//+------------------------------------------------------------------+
#ifndef XAI_KILL_SWITCH_MQH
#define XAI_KILL_SWITCH_MQH

// Ficheiro-sinal, relativo a MQL5\Files (sandbox do terminal).
#ifndef XAI_KS_FILE
   #define XAI_KS_FILE "XAU_AI_PRO\\KILL_SWITCH.flag"
#endif
// Sonda ao disco no maximo 1x a cada 3 s (OnTick pode chegar a muitas por
// segundo; ler um ficheiro por tick seria desperdicio garantido).
#ifndef XAI_KS_CACHE_SEC
   #define XAI_KS_CACHE_SEC 3
#endif
// Entre tentativas de fechar posicoes: 10 s. Evita martelar o servidor.
#ifndef XAI_KS_RETRY_SEC
   #define XAI_KS_RETRY_SEC 10
#endif
// Repeticao da linha de estado no journal.
#ifndef XAI_KS_LOG_SEC
   #define XAI_KS_LOG_SEC 300
#endif

struct XAI_KillSwitchState
{
   bool     ativo;            // entradas bloqueadas
   bool     fecharTudo;       // pedido de fecho total (ficheiro)
   int      estadoAntes;      // 0=desconhecido, 1=LIVRE, 2=ARMADO (publica transicoes)
   datetime ultimaSonda;
   datetime ultimoLog;
   datetime ultimaTentativa;
   int      fechados;         // posicoes fechadas pelo interruptor nesta sessao
   bool     autoArmado;       // via automatica (memoria)
   string   motivoAuto;
};

XAI_KillSwitchState g_ks;
CTrade              g_ksTrade;   // instancia propria: nao herda estado do trade global

class CKillSwitch
{
private:
   //--- le o ficheiro-sinal e actualiza o estado (fail-safe para o lado seguro)
   static void SondarFicheiro()
   {
      g_ks.ultimaSonda = TimeLocal();
      g_ks.ativo       = false;
      g_ks.fecharTudo  = false;

      if(!FileIsExist(XAI_KS_FILE))
         return;

      g_ks.ativo      = true;
      g_ks.fecharTudo = true;   // enquanto nao provar o contrario, assume o pior

      int h = FileOpen(XAI_KS_FILE, FILE_READ | FILE_TXT | FILE_ANSI |
                       FILE_SHARE_READ | FILE_SHARE_WRITE);
      if(h == INVALID_HANDLE)
         return;                // sem leitura: mantem fechar_tudo=true

      string txt = "";
      while(!FileIsEnding(h))
         txt += FileReadString(h) + " ";
      FileClose(h);

      StringToUpper(txt);
      g_ks.fecharTudo = (StringFind(txt, "FECHAR") >= 0 ||
                         StringFind(txt, "CLOSE")  >= 0);
   }

   //--- publica a TRANSICAO de estado (LIVRE <-> ARMADO), so quando muda.
   //    F2.1 v1.2.177: MEDIDO em 06/11/2026 que a versao anterior publicava o
   //    estado no arranque e repetia a linha ARMADO a cada 300 s, mas NAO
   //    publicava NADA quando o operador APAGAVA o ficheiro. Quem desarmava o
   //    interruptor nao tinha como confirmar no journal que o pedido foi lido:
   //    o silencio ficava ambiguo entre "rearmei" e "o EA nao viu". Como o
   //    PLANO_10_10 F2.1 exige o interruptor TESTADO, a falta desta linha
   //    tornava o teste impossivel de fechar sem reiniciar o EA. A transicao e
   //    publicada uma vez, sem throttle, porque transicao e rara; a repeticao
   //    periodica do estado continua a cargo do Verificar.
   static void PublicarTransicao()
   {
      int estado = (g_ks.ativo ? 2 : 1);
      if(estado == g_ks.estadoAntes)
         return;

      bool primeira    = (g_ks.estadoAntes == 0);
      g_ks.estadoAntes = estado;

      // A primeira observacao coincide com a linha de arranque do OnInit;
      // nao duplicamos no journal.
      if(primeira)
         return;

      if(estado == 2)
         Print("[KILL SWITCH] ARMADO | ficheiro=", XAI_KS_FILE,
               " | origem=MANUAL",
               " | fechar_tudo=", (g_ks.fecharTudo ? "SIM" : "NAO"),
               " | entradas BLOQUEADAS (apagar o ficheiro para rearmar)");
      else
         Print("[KILL SWITCH] REARMADO | ficheiro=", XAI_KS_FILE,
               " | estado=LIVRE | entradas LIBERTADAS");

      g_ks.ultimoLog = TimeLocal();  // o aviso periodico espera o seu intervalo
   }

   //--- sonda o ficheiro e publica a transicao correspondente
   static void Sondar()
   {
      SondarFicheiro();
      PublicarTransicao();
   }

   //--- fecha todas as posicoes do EA (mesmo magic), com throttle
   static void FecharTudo(const long magic)
   {
      if(g_ks.ultimaTentativa > 0 &&
         (TimeLocal() - g_ks.ultimaTentativa) < XAI_KS_RETRY_SEC)
         return;

      g_ks.ultimaTentativa = TimeLocal();

      g_ksTrade.SetExpertMagicNumber((ulong)magic);
      g_ksTrade.SetDeviationInPoints(50);

      int total = PositionsTotal();
      int feitos = 0;

      for(int i = total - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);   // selecciona a posicao i
         if(ticket == 0)
            continue;
         if((long)PositionGetInteger(POSITION_MAGIC) != magic)
            continue;                           // nao e deste EA

         string sym = PositionGetString(POSITION_SYMBOL);

         if(g_ksTrade.PositionClose(ticket))
           {
            feitos++;
            if(AccountLogGatePodeImprimir("killswitch_fecho_" + sym, XAI_KS_LOG_SEC))
               Print("[KILL SWITCH] POSICAO FECHADA | ", sym,
                     " | ticket=", (string)ticket,
                     " | retcode=", IntegerToString(g_ksTrade.ResultRetcode()),
                     " | ", g_ksTrade.ResultComment());
           }
         else
           {
            // P0 medido em 06/11: com MQL_TRADE_ALLOWED=0 o fecho TAMBEM e
            // recusado. Nao escondemos isso: sem esta linha o operador
            // acreditava que o interruptor tinha fechado o que nao fechou.
            if(AccountLogGatePodeImprimir("killswitch_falha_" + sym, XAI_KS_LOG_SEC))
               Print("[KILL SWITCH] FALHA AO FECHAR | ", sym,
                     " | ticket=", (string)ticket,
                     " | retcode=", IntegerToString(g_ksTrade.ResultRetcode()),
                     " | ", g_ksTrade.ResultComment(),
                     " | MQL_TRADE_ALLOWED=", IntegerToString(MQLInfoInteger(MQL_TRADE_ALLOWED)));
           }
      }

      g_ks.fechados += feitos;

      if(feitos > 0 && AccountLogGatePodeImprimir("killswitch_total", XAI_KS_LOG_SEC))
         Print("[KILL SWITCH] FECHO CONCLUIDO | posicoes fechadas=", IntegerToString(feitos),
               " | total nesta sessao=", IntegerToString(g_ks.fechados));
   }

public:
   //--- ha pedido de paragem? (manual ou automatico)
   static bool Ativo()
   {
      if(g_ks.autoArmado)
         return(true);

      if(g_ks.ultimaSonda == 0 ||
         (TimeLocal() - g_ks.ultimaSonda) >= XAI_KS_CACHE_SEC)
         Sondar();

      return(g_ks.ativo);
   }

   //--- via automatica (em memoria, sobrevive ate reiniciar o EA)
   static void ArmarAutomatico(const string motivo)
   {
      if(g_ks.autoArmado)
         return;

      g_ks.autoArmado = true;
      g_ks.motivoAuto = motivo;
      g_ks.estadoAntes = 2;   // coerencia: o estado publicado passa a ARMADO

      Print("[KILL SWITCH] ARMADO AUTOMATICAMENTE | motivo=", motivo,
            " | entradas BLOQUEADAS ate reiniciar o EA");
   }

   //--- veredicto unico. Devolve true quando as entradas devem parar.
   //    fechar = autoriza o fecho de posicoes quando pedido.
   static bool Verificar(const long magic, const bool fechar)
   {
      if(!Ativo())
         return(false);

      if(fechar && (g_ks.autoArmado || g_ks.fecharTudo))
         FecharTudo(magic);

      if(g_ks.ultimoLog == 0 ||
         (TimeLocal() - g_ks.ultimoLog) >= XAI_KS_LOG_SEC)
        {
         g_ks.ultimoLog = TimeLocal();
         Print("[KILL SWITCH] ARMADO | ficheiro=", XAI_KS_FILE,
               " | origem=", (g_ks.autoArmado ? "AUTOMATICO:" + g_ks.motivoAuto : "MANUAL"),
               " | fechar_tudo=", ((g_ks.autoArmado || g_ks.fecharTudo) ? "SIM" : "NAO"),
               " | fechadas_sessao=", IntegerToString(g_ks.fechados),
               " | entradas BLOQUEADAS (apagar o ficheiro para rearmar)");
        }

      return(true);
   }

   //--- texto para painel/journal de arranque
   static string Estado()
   {
      if(!Ativo())
         return("LIVRE (sem " + XAI_KS_FILE + ")");

      return(StringFormat("ARMADO | origem=%s | fechar_tudo=%s | fechadas=%d",
                          (g_ks.autoArmado ? "AUTOMATICO" : "MANUAL"),
                          ((g_ks.autoArmado || g_ks.fecharTudo) ? "SIM" : "NAO"),
                          g_ks.fechados));
   }
};

#endif // XAI_KILL_SWITCH_MQH
//+------------------------------------------------------------------+
