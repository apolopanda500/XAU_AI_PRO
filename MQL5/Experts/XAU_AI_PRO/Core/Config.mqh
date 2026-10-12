// XAU_AI_PRO v1.2.0
#ifndef CONFIG_MQH
#define CONFIG_MQH

//==================================================
// GERAL
//==================================================
input bool   AutoTrade          = true;
input long   MagicNumber        = 2026001;
input string TradeComment       = "XAU_AI_PRO";

//==================================================
// FONTE DA IA
//==================================================
// `AIConnector.mqh` Historically lia `Data\prediction_<SIMBOLO>.json`. Medido em
// 05/10/2026: essa pasta NAO EXISTE na maquina — o backend responde por HTTP e
// nunca escreve arquivo. Resultado: o EA rodava sem sinal nenhum, e nao havia
// log de erro porque a ausencia de arquivo e um caminho previsto.
//
// AIUseGateway=true passa a chamar o proprio backend, que e a FONTE DE VERDADE
// dos 25 modelos publicados. O arquivo continua disponivel como fallback: se o
// gateway estiver fora do ar, `AIUseGateway` volta a true sozinho no proximo
// ciclo, e o arquivo so e lido se a tentativa HTTP falhar.
//
// A URL tem que estar AUTORIZADA em
// Ferramentas > Opcoes > Expert Advisors > "Allow WebRequest for listed URL".
// Sem isso o MT5 devolve -401 e o EA registra "gateway recusou" uma vez por
// minuto no log — e segue operando pela leitura de arquivo.
input bool   AIUseGateway       = true;
input string AIGatewayUrl       = "http://127.0.0.1:9001/api/ai/predict";
input string AIGatewayToken     = "";
// Segundos entre uma consulta e outra. 15 s alinha com o ciclo do motor e com
// a leitura de latencia: mais rapido e consumo sem ganho, mais lento e o EA
// age sobre previsao velha.
input int    AIPollSeconds      = 15;
// Tempo maximo de espera da resposta HTTP.
//
// MEDIDO em 05/10/2026, nos 25 modelos validados pela rota real:
//   primeiro acesso ao par   2096 ms   (carrega o `.pkl` do disco)
//   acesso seguinte          144 ms   (o `_CACHE` do backend segura)
//   pior caso no lote        450 ms   (apos o cache aquecer)
//
// O limite e 15 s, e nao 5: em disco frio o carregamento do artefato passa de
// 2 s, e um timeout curto faria o EA cair no fallback de arquivo — que tambem
// nao existe — justamente na primeira consulta, que e a que importa.
//
// NINGUM TIMEOUT PODE SER MENOR QUE O CUSTO REAL. Cortar o tempo para "ir
// mais rapido" troca um sinal atrasado por um sinal ausente.
input int    AIRequestTimeoutMs = 15000;

//==================================================
// RISCO
//==================================================
input bool   UseRiskManagement  = true;
input double LotSize            = 0.01;
input double RiskPercent        = 1.0;

input double MaxDailyLossPercent= 5.0;
input double MaxDrawdownPercent = 15.0;
input double MinEquityPercent   = 10.0;  // Equity minima (% do balance) para operar

input double MinFreeMargin      = 10.0;  // Margem livre minima (moeda da conta)

input int    MaxTradesPerDay    = 20;
input int    MaxOpenPositions   = 5;

// v1.3.0 (Etapa 3): quando o risco configurado exige lote abaixo do
// minimo do broker. true = opera no minimo (comportamento antigo,
// risco real maior que o configurado). false = estrito, bloqueia.
input bool   AllowMinLotOverride = true;

//==================================================
// LIMITE DE SPREAD — EM PORCENTAGEM DO PRECO (08/10/2026)
//==================================================
// MEDIDO na conta 391773676 (XMGlobal-MT5 14), terminal aberto, com o EA
// operando BTCUSD H4:
//
//   simbolo   point    spread_preco   spread_pts   limite de 50 pts =   bloqueia?
//   BTCUSD    0.01        40,00000       4000,0           0,50000        SIM
//   ETHUSD    0.01         3,00000        300,0           0,50000        SIM
//   USDSEK    0.00001      0,01550       1579,0           0,00050        SIM
//   GOLD      0.01         0,57000         57,0           0,50000        SIM
//   USDCNH    0.0001       0,00430         43,0           0,00500        nao
//   EURUSD    0.00001      0,00019         19,0           0,00050        nao
//
// 4 de 12 simbolos BLOQUEADOS com spread NORMAL. E o OURO, por 57 contra 50:
// um limite em pontos crus e fragil ate no metal que da nome ao projeto.
//
// A CAUSA: `point` varia mil vezes entre um forex e o BTCUSD. "50 pontos"
// vale $5,00 no BTCUSD e $0,0005 no EURUSD. O mesmo numero nao pode servir
// as duas coisas.
//
// A CAUSA SEGUNDA: o mapa por simbolo nao ACERTAVA para nenhum dos tres que
// ele nomeava. Os nomes tinham `#` no fim (`GOLD#:350`) e a comparacao e
// `StringCompare(sym, symbol, false)` com `symbol = _Symbol`, que e `GOLD` —
// sem `#`. Entao o mapa caia sempre no fallback. (O `CircuitBreaker.mqh:153`
// ja tinha um comentario sobre isso; o comentario estava certo e o codigo
// continuou errado.)
//
// A CORRECAO: o limite passa a ser PORCENTAGEM DO PRECO, e o
// `GetMaxSpread` continua devolvendo PONTOS — derivados do preco e do `point`
// do proprio simbolo. Entao os SEIS lugares que comparam
// (`SymbolValidator:123`, `ValidationEngine:90`, `SpreadFilter:91` e `:145`,
// `SmartExecution:334` e `:341`) nao mudam uma linha, e a unidade do broker
// deixa de importar.
//
// FOLGA MEDIDA com 0,6% de fallback (spread real em % do preco):
//   USDSEK 0,158% -> 3,8x   ETHUSD 0,121% -> 5,0x   USDCNH 0,064% -> 9,4x
//   BTCUSD 0,049% -> 12,3x  NZDUSD 0,055% -> 10,8x  GOLD 0,014% -> 43,6x
// Todos passam, e o mais apertado ainda tem 3,8x antes de a trava fechar.
input double MaxSpreadPct       = 0.6;
// Limites POR SIMBOLO, tambem em porcentagem. Formato "SIMBOLO:pct".
// Sem `#`: o nome e o que o terminal escreve, e `_Symbol` nao tem sufixo.
// Simbolos nao listados usam MaxSpreadPct.
input string MaxSpreadPctBySymbol = "";

//==================================================
// GET MAX SPREAD PCT — a porcentagem do simbolo
//==================================================
double GetMaxSpreadPct(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   string list = MaxSpreadPctBySymbol;
   StringTrimLeft(list);
   StringTrimRight(list);
   if(list != "")
   {
      string entries[];
      int n = StringSplit(list, ',', entries);
      for(int i = 0; i < n; i++)
      {
         string kv[];
         int k = StringSplit(entries[i], ':', kv);
         if(k == 2)
         {
            string sym = kv[0];
            StringTrimLeft(sym);
            StringTrimRight(sym);
            string val = kv[1];
            StringTrimLeft(val);
            StringTrimRight(val);
            // Comparacao sem `#`: `_Symbol` nunca tem sufixo, e era exatamente
            // o sufixo que fazia o mapa nunca casar (medido acima).
            if(StringCompare(sym, symbol, false) == 0)
            {
               double pct = StringToDouble(val);
               if(pct > 0.0)
                  return pct;
            }
         }
      }
   }
   return(MaxSpreadPct > 0.0 ? MaxSpreadPct : 0.6);
}

//==================================================
// GET MAX SPREAD — em PONTOS, derivado do preco
//==================================================
// A UNIDADE CONTINUA SENDO PONTO, porque os seis leitores ja comparam com
// `spread = (ask-bid)/point`. O que muda e de onde o numero vem: em vez de
// "50 pontos" escrito a mao, e a porcentagem do preco convertida no `point`
// daquele simbolo.
double GetMaxSpread(string symbol="")
{
   if(symbol == "")
      symbol = _Symbol;

   double pct = GetMaxSpreadPct(symbol);
   if(pct <= 0.0)
      return(50.0);

   double ask  = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

   // Sem ficha do simbolo nao ha preco nem point: nao se chora o limite, e
   // nao se inventa um numero. O fallback e a mesma 50 pontos de antes.
   if(point <= 0.0)
      return(50.0);
   if(ask <= 0.0)
      ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask <= 0.0)
      return(50.0);

   double limitePreco = ask * pct / 100.0;
   double limitePts   = limitePreco / point;
   if(limitePts <= 0.0)
      return(50.0);

   // Teto e piso em PONTOS, para o limite nao virar absurdo em nenhum dos
   // extremos: 1 ponto no minimo (nunca "spread 0"), e 100.000 no maximo.
   if(limitePts < 1.0)
      return(1.0);
   if(limitePts > 100000.0)
      return(100000.0);
   return(limitePts);
}
input int    Slippage           = 5;

//==================================================
// ORDER RETRY v1.2.0
// Parametros centralizados de retry de ordens.
//==================================================
input int    RetryMaxAttempts       = 5;
input int    RetryBaseDelayMs       = 100;
input double RetryDelayMultiplier   = 2.0;
input int    RetryMaxDelayMs        = 2000;
input int    RetryMaxSlippage       = 50;
input int    RetrySlippageIncrement = 2;


//==================================================
// STOP
//==================================================
input int StopLossPoints        = 300;
input int TakeProfitPoints      = 600;

//----------------------------------------------
// RISCO por operacao em DINHEIRO (decisao do dono, 08/10/2026)
//----------------------------------------------
// MEDIDO na conta 391773676: `StopLossPoints=300` e PONTOS CRUOS, e ponto nao
// e dinheiro. No GOLD (point 0,01) dava US$ 3,00; no EURUSD (point 0,00001)
// dava US$ 3,00 tambem; no USDJPY daria US$ 20 e no BTCUSD US$ 0,03. Um
// numero so, quatro riscos diferentes.
//
// E o pior: US$ 3,00 contra um orcamento diario de 5% de US$ 12,13 = US$ 0,61.
// Uma operacao estouraria o limite diario inteiro, que foi exatamente o que
// aconteceu: SELL 0,01 GOLD @ 4152,43 com stop em 4155,43 (+3,00), tocado.
//
// Aqui o risco e em DOLARES e vale para todos os simbolos. `RewardRatio = 1.0`
// deixa alvo e stop iguais (2 por 2, 3 por 3); 2.0 volta ao 1:2 antigo.
// Os inputs em PONTOS continuam existindo como caminho de fuga: se
// `RiskPerTradeUsd <= 0` eles voltam a valer, entao nenhum controle fica sem
// consumidor.
input double RiskPerTradeUsd     = 2.0;   // risco do STOP por operacao, em moeda da conta
input double RewardRatio         = 1.0;   // alvo = risco x isto. 1.0 = 1:1

//==================================================
// BREAK EVEN
//==================================================
input bool EnableBreakEven      = true;
input int  BreakEvenTrigger     = 80;
input int  BreakEvenOffset      = 10;

//==================================================
// TRAILING
//==================================================
input bool   EnableTrailingATR  = true;
input double ATRMultiplier      = 1.2;

//==================================================
// PARCIAL
//==================================================
// `PartialTrigger` esta em PONTOS do input original. MEDIDO 05/10/2026: 150
// pontos e 0,17% no BTCUSD (86.439) e 1,5% no EURUSD (1,125) — a mesma
// configuracao e uma distancia智能 em um ativo e colada em outro. E a mesma
// armadilha do `XAUUSD`/`GOLD`: o numero e o mesmo, o significado nao.
//
// `PartialTriggerInATR=true` passa a medir em MULTIPLOS DE ATR, que e a
// unica escala que significa a mesma coisa em metais, forex e cripto.
// `false` mantem o comportamento antigo em pontos.
input bool   EnablePartialClose = true;
input int    PartialTrigger     = 150;
input double PartialPercent     = 30.0;
input bool   PartialTriggerInATR = true;
// Quando `PartialTriggerInATR`, este e o multiplicador de ATR que substitui
// `PartialTrigger`. 1,0 = fecha a parte quando o preco percorre 1 ATR a
// favor. Medido: em BTCUSD (ATR ~2.500) isso e 1 ATR; em EURUSD (ATR ~0,006)
// e 0,006 — a mesma leitura de volatilidade, nao a mesma distancia bruta.
input double PartialTriggerATRMult = 1.0;

//==================================================
// TP QUE SO APROXIMA (05/10/2026)
//==================================================
// MEDIDO: o SL se movia (`TrailingStopATR`), o parcial fechava
// (`PartialClose`), mas o TP NUNCA se mexia. O alvo ficava no numero original
// enquanto o preco ia e voltava — e o "quase la e voltou" que o operador
//relsse ao vivo na conta real.
//
// POR QUE SO APROXIMA, E NAO PERSEGUE
// ------------------------------------
// Se o TP perseguisse o preco como o SL, uma oscilacao contra moveria os DOIS
// para baixo, e o alvo que estava quase alcancado se afastaria junto. Com
// `ApproximatesOnly`, o TP so chega mais perto: um degrau que ja foi
// alcancado nunca recua. O preco pode ter recuperado, mas o alvo continua
// valendo — e um alvo que recua deixa de ser alvo.
input bool   EnableDynamicTP     = true;
// Multiplos de ATR que o TP avanca a cada vez. 0,5 = passos curtos e
// frequentes (mais modificacoes); 2,0 = passos largos e raros.
input double TPAproxStepATRMult  = 1.0;
// Fração do caminho ate o TP original que o TP pode ter andado. 1.0 = pode
// chegar no alvo original. Abaixo disso, para antes — util quando o alvo
// original era longe demais.
input double TPAproxMaxFraction  = 1.0;

//==================================================
// FILTROS
//==================================================
input bool EnableSpreadFilter      = true;
input bool EnableSessionFilter     = false;
input bool EnableTrendFilter       = true;
input bool EnableVolatilityFilter  = false;
input bool EnableADXFilter         = true;
input bool EnableMTFConfirmation   = false;
input bool EnableNewsFilter        = false;
input bool EnableAIFilter          = true;

//==================================================
// NEWS FILTER v1.3.0 (Etapa 6)
// Economic Calendar nativo MQL5 com estados
// NEWS_CLEAR/WARNING/BLOCK/ACTIVE, throttle de
// 60s e filtro por moeda.
// NewsCurrencies vazio = auto-derivacao pelo simbolo
// (XAUUSD->USD, EURUSD->EUR+USD). Lista manual tem
// prioridade sobre a auto-derivacao.
//==================================================
input string NewsCurrencies        = "";
input int    NewsImpactThreshold   = 2;        // 1=low, 2=medium, 3=high
input int    NewsMinutesBefore     = 30;
input int    NewsMinutesAfter      = 30;


//==================================================
// IA
//==================================================
input double MinAIConfidence    = 50.0;

//==================================================
// IA - AUTORIDADE DE SINAL (05/10/2026)
//==================================================
// MEDIDO em 05/10/2026: o `AIEngine` lia `AI_BuyProbability` e
// `AI_SellProbability`, que o backend NAO publica — a rota
// `/api/ai/predict` devolve `prob_buy`/`prob_sell` (0.0 no payload
// canonico) e, sobretudo, um `signal` TEXTUAL ("BUY", "SELL",
// "NEUTRAL", "STRONG_BUY"). O `AI_Signal` nunca era lido para decidir.
//
// Resultado: a IA era so veto e redutor de lote, e o sinal de compra e
// venda vinha do tecnico (EMA+RSI). Ligando isto, a IA passa a DECIDIR —
// que e o que o dono pediu ("a IA pode fazer tudo").
//
// false (padrao) = comportamento anterior: IA veta, tecnico decide. È a
// opcao segura e a que estava valendo antes desta mudanca.
input bool   AIHasSignalAuthority = false;

// Minimo de score para a IA ASSUMIR a decisao, separado do veto.
// `MinAIConfidence` e o piso do veto; este e o piso para mandar.
// 75 = o mesmo valor que `GetCombinedSignal` ja usava para dar autoridade
// a IA sobre o tecnico — o numero nao e novo, so passa a ter nome.
input double AIAuthorityMinScore  = 75.0;

//==================================================
// IA - JSON (v1.2.0)
//==================================================
// RequireAIJSON=false (padrao): o arquivo
// prediction_<SYMBOL>.json e opcional. Quando ausente,
// o AIEngine usa o fallback local (indicadores/score).
// Necessario para backtest, pois o pipeline Python
// nao roda dentro do Strategy Tester.
// RequireAIJSON=true: exige o JSON do pipeline Python
// para liberar o simbolo (modo producao estrito).
//
// MEDIDO 05/10/2026: com `false`, o EA opera MESMO SEM IA — que e o
// oposto de "operar guiado por IA". Quem quer a IA no comando liga isto.
input bool   RequireAIJSON      = false;

//==================================================
// RISCO - STOP LOSS OBRIGATORIO (05/10/2026)
//==================================================
// MEDIDO na conta real 391773676: uma posicao aberta no MT5 com
// `sl = 0.0` e TP 86.584,30. Sem protecao, uma queda de 2% no BTCUSD
// levava o equity de 11,63 para -5,65 — STOP OUT.
//
// O backend ja recusava ("Stop Loss calculou zero", `auto_engine.py`),
// mas o EA nao: `ExecutionEngine.mqh` calculava o SL e, se o resultado
// fosse 0, seguia com a ordem. Este input fecha essa diferenca.
//
// true = recusa ordem sem SL. Nao existe caso em que desligar seja
// seguro com dinheiro real; existe para backtest, onde o SL as vezes e
// calculado depois.
input bool   RequireStopLoss     = true;

//==================================================
// IA - STALENESS (ETAPA 15.3)
// Idade maxima aceita para o timestamp_utc do
// prediction JSON, em segundos. 0 = verificacao
// desativada. Previsao mais antiga que o limite
// e tratada como INDISPONIVEL (o AIEngine cai no
// fallback local ou bloqueia, conforme politica).
// Padrao 900s = 15 min (~3 candles M5).
//==================================================
input int    MaxPredictionAgeSec = 900;

//==================================================
// KCI v1.2.0
// Parametros centralizados dos indicadores KCI.
//==================================================
input int    KCI_VD_Period        = 14;
input int    KCI_DX_BasePeriod    = 9;
input int    KCI_DX_ZScorePeriod  = 30;
input double KCI_DX_Sensitivity   = 1.5;
input double KCI_DX_MainThreshold = 30.0;


//==================================================
// SESSAO
//==================================================
input int TradeStartHour        = 0;
input int TradeEndHour          = 24;

//==================================================
// INDICADORES
//==================================================
input int FastEMA               = 50;
input int SlowEMA               = 200;

input int RSIPeriod             = 14;

//==================================================
// SINAL PULLBACK v1.2.0
// Niveis de RSI (vela fechada) para entrada por pullback:
//  - BUY  exige RSI fechado ABAIXO de RSIPullbackBuy  (dip na tendencia de alta)
//  - SELL exige RSI fechado ACIMA  de RSIPullbackSell (rally na tendencia de baixa)
// Valores 40/60 = mais seletivo (menos sinais, maior qualidade)
// Valores 45/55 = moderado (padrao)
// Valores 50/50 = comportamento antigo (muito permissivo)
//==================================================
input double RSIPullbackBuy     = 45.0;
input double RSIPullbackSell    = 55.0;

input int ATRPeriod             = 14;
input int ADXPeriod             = 14;

input double MinimumADX         = 18.0;

//==================================================
// SCHEDULER v1.2.0
// Agendador interno: intervalo de execucao + shutdown de fim de semana.
//==================================================
input bool   EnableScheduler       = true;
input int    SchedulerIntervalSec  = 60;
input bool   EnableWeekendShutdown = true;

//==================================================
// DATABASE / TELEMETRY v1.2.0
// Integracao com DatabaseManager,
// TradeLogger e Statistics.
//==================================================
input bool   EnableDatabase        = false;
input string DatabasePath          = "XAU_AI_PRO.db";
input bool   EnableTelemetry       = true;


//==================================================
// DATASET
//==================================================
input bool EnableDataset        = true;
input bool SaveDatasetCSV       = true;
input bool EnableBacktestLog    = true;

//==================================================
// DASHBOARD
//==================================================
input bool EnableDashboard      = true;
input bool EnableLogs           = true;
input bool DebugTradeDecision   = true;

//==================================================
// MONITORING & AUDITORIA (ETAPA 6)
// HealthMonitor absorveu o WatchDog (heartbeat dos
// modulos ATR/ADX/RSI/AI/PYTHON/CSV/JSON).
// AuditLog absorveu o FullAudit (registro estruturado
// de entrada/saida por ticket em Data\full_audit.csv).
//==================================================
input bool EnableHealthMonitor   = true;   // HealthMonitor + WatchDog integrado
input int  HealthCheckInterval   = 60;     // segundos entre health checks completos
input int  HealthWatchdogInterval= 120;    // segundos sem heartbeat para contar falha (liveness)
input int  HealthPipelineProgressTimeout= 0;  // 0 = auto (2x cadencia da vela, min WatchdogInterval)
input bool EnableAuditLog        = true;   // Auditoria (decisoes + full audit)
input bool EnableDiagnostics     = true;   // Diagnostico completo no OnInit

//==================================================
// REPLAY & BACKUP (ETAPA 7)
// ReplayEngine: reproduz decisoes/eventos historicos
// sem interferir na execucao real (REPLAY != LIVE).
// BackupManager: snapshots em FILE_COMMON + local,
// com wildcards, manifesto e restauracao validada.
//==================================================
input bool   EnableReplay          = false;  // REPLAY: reproduz historico, bloqueia trades reais
input string ReplayDatasetFile     = "Data\\trades_dataset.csv"; // decisoes (Dataset.mqh export)
input string ReplayOHLCFile        = "Data\\dataset.csv";        // OHLC/tick (DataLogger.mqh)
input string ReplayAuditFile       = "Data\\full_audit.csv";     // entradas/saidas (AuditLog.mqh)
input string ReplaySymbolFilter    = "";     // vazio = todos; ex: "XAUUSD" ou "GOLD#"
input bool   EnableBackupManager   = true;   // Backup automatico dos dados do EA
input int    BackupIntervalMinutes = 60;     // 0 = somente manual (OnInit)
input int    BackupMaxKeep         = 10;     // snapshots mantidos (limpeza automatica)

//==================================================
// BACKTEST ANALYZER & BENCHMARK (ETAPA 8)
// BacktestAnalyzer: registra cada trade do tester
// em BacktestReport.csv e calcula metricas (win rate,
// profit factor, drawdown, sharpe, expectativa).
// BenchmarkEngine: compara estrategias (Technical,
// AI, Hybrid, Ensemble) e elege a melhor.
//==================================================
input bool EnableBacktestAnalyzer = true;   // ANALISE: log + metricas de backtest
input bool EnableBenchmark        = true;   // BENCHMARK: comparacao de estrategias

//==================================================
// NOTIFICATION CENTER (ETAPA 9)
// Camada de observabilidade (Push nativo + Telegram).
// NUNCA bloqueia o trading: falha de notificacao apenas
// conta e registra, sem interferir no fluxo do EA.
//==================================================
input bool   EnableNotifications     = true;   // Central de notificacoes
input bool   NotifyPushEnabled       = true;   // Push nativo MT5 (SendNotification)
input string NotifyTelegramToken     = "";     // Token do bot Telegram (vazio = OFF)
input string NotifyTelegramChatID    = "";     // Chat ID do Telegram
input int    NotifyCooldownSec       = 30;     // cooldown entre mensagens (mesma categoria)
input int    NotifyMaxPerMinute      = 10;     // limite anti-spam global
input bool   NotifyTradeEvents       = true;   // notificar abertura/fechamento
input bool   NotifyErrors            = true;   // notificar erros
input bool   NotifyDrawdown          = true;   // notificar drawdown
input double NotifyDrawdownThreshold = 5.0;    // % minimo de drawdown para alertar
input bool   NotifyHealth            = true;   // notificar falha de HealthMonitor
input bool   NotifyCircuitBreaker    = true;   // notificar Circuit Breaker / SAFE
input bool   NotifyExecutionFailures = true;   // notificar rejeicoes de ordem

//==================================================
// MULTI SYMBOL
//==================================================
input bool EnableMultiSymbol    = true;

input string Symbols=
"XAUUSD,"    // Conta DEMO - nomes reais sem sufixo
"EURUSD,"
"GBPUSD,"
"USDJPY,"
"AUDUSD,"
"USDCAD,"
"NZDUSD,"
"USDCHF,"
"USDBRL,"
"USDSEK,"

"USDCNH";

//==================================================
// RISCO EM DINHEIRO -> DISTANCIA EM PONTOS
//==================================================
// Definicao UNICA do "quanto de preco corresponde a N dolares de risco" para
// um simbolo e um lote. `ExecutionEngine` e `OrderManager` consomem ISTA funcao.
//
// Se cada um dividisse por conta propria, um deles acabaria com um numero e o
// outro com outro — e o sintoma seria o mesmo que ja-investigamos: o cliente
// lendo um nome e o servidor entregando outra medida.
//
// `distancia = risco_usd / (contrato x volume x point)`
//
// `SYMBOL_TRADE_CONTRACT_SIZE` e propriedade DOUBLE, nao enum inteiro: no MT5 o
// tamanho de contrato pode ser fracionario, e o compilador rejeita com
// "cannot convert enum" quando ele e pedido como `SymbolInfoInteger`. Medido
// em 08/10/2026: e o primeiro erro que aparece ao compilar este trecho.
double DistanciaPontosParaRiscoUSD(
   string symbol,
   double volume,
   double risco_usd
)
{
   if(risco_usd <= 0.0 || volume <= 0.0)
      return(0.0);

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double contrato = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);

   if(point <= 0.0 || contrato <= 0.0)
      return(0.0);

   return(risco_usd / (contrato * volume * point));
}

//==================================================
// DEBUG - NAO ALTERE
//==================================================
input bool EnableVerboseDebug    = true;  // Logs detalhados para debug

#endif
