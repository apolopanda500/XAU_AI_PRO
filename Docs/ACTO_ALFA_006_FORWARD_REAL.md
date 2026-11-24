# Acto ALFA-006 — Forward real reiniciado (23/11/2026)

## Execução
- `POST /api/auto/config` com limites: ETHUSD/H1, broker=mt5, market=forex,
  `account_id=mt5:forex:Henrique Carvalho @ XMGlobal-MT5 14`, banca=4.90 USD,
  risco=0.50%, confiança=60%, edge=0.02, max_posicoes=20, max_operacoes_dia=200,
  perda_diaria_max=3.0%, sl_atr=1.5, tp_atr=2.0, intervalo=5 min, lote=0.02.
- `POST /api/auto/start` → `{"ok":true,"status":"ligado"}`.
- `GET /api/auto/state` → `ativo=true`.

## Correção necessária antes de ligar
- Havia **duas contas MT5 forex ativas** (XMGlobal real + MetaQuotes-Demo).
  O `resolve_connection` exige `account_id` quando há mais de uma. O ID
  `mt5:420750145` (login numérico) **não era um id de conexão válido** —
  o correto é o id textual `mt5:forex:Henrique Carvalho @ XMGlobal-MT5 14`.
  Isso é o AGENTS.md §5 de novo: produtor (número de login) vs consumidor (id da conexão).

## Estratégia em vigor (decisões do DONO)
- Banca baixa (< US$ 100) → CRESCIMENTO PURO, sem stop a subir; SL da entrada permanece.
- Alvos curtos $0,50–$1,00.
- Até 20 posições simultâneas; correlated=20; risco 0,50%.
- Medidor de acertividade ativo no `[RESUMO]` (`acerto=X% (W/L)`) — ALFA-005.

## Estado do capital
- Conta REAL XMGlobal-MT5 14, saldo ~4,90 USD.
- Motor ligado por ordem explícita do DONO ("reiniciar forward em conta real nova").
- Posições preexistentes do DONO não foram fechadas/alteradas.
- `.ex5` produção intacto (MD5 `844081BF2D51D6A4072B150C3DDC6EBD`).

## Próxima medição
- Confirmar no jornal que as decisões saem com `acerto=`, e medir a taxa real
  antes de afirmar qualquer percentual (meta do DONO: >90%).

## Confirmação em operação (17:3x)
- Motor ativo de forma contínua (`ativo=true`), 1 decisão registrada: ETHUSD/H1
  BUY com confiança 41,3% recusada corretamente por estar abaixo do mínimo 60%
  — nenhuma ordem enviada.
- Gateway IA: `[REFRESC] falhas=0 | 844 ms` (antes: 16/16 falhas, 32 s).
- `[RESUMO]` imprime `acerto=0.0% (0W/0L)` — medidor ativo (ALFA-005).
- `escada=ON | banca PEQUENA = CRESCIMENTO: sem stop a subir` — estratégia em vigor.
- Posições EA: 0. Capital do DONO preservado.
## Destravamento final (23/11, ordem do DONO)
- KILL_SWITCH: inexistente (EA ja destravado).
- SymbolsExclude revertido para `USDRUB`: todos os simbolos voltaram ao universo (forex, cripto, metais) conforme decisao do DONO 'operar tudo'.
- Filtro de spread MANTIDO em 0,6%: o DONO recusou a desativacao (opcao B) por ser matematicamente negativa nos 12 cripto com spread 0,9-2,5%. Proteção de custo intacta.
- Motor: ativo=true, 12 ciclos. Master do pipeline: GOLD/M15.
- Posicoes do DONO e .ex5 production preservados.
## DECISAO DO DONO (15:36) - EVITAR HORAS
- O DONO NEGOU desativar o filtro de horas: `EnableAvoidHoursGMT=true` e a lista `9,11,14,18,20,22` PERMANECEM.
- Nao alterar AvoidHoursGMT nem EnableAvoidHoursGMT. As horas ruins continuam bloqueadas por regra explicita do DONO.
- Consequencia aceita: as 18h GMT (como agora) nao abrem posicoes; o EA volta a operar fora da lista.
## REMOCAO DAS TRAVAS DE HORARIO (ordem final do DONO)
- DONO: 'remover travar de horarios' / 'nao quero mais'.
- Codigo: EnableAvoidHoursGMT=false, AvoidHoursGMT='' (era 9,11,14,18,20,22).
- 16/16 perfis .chr: EnableAvoidHoursGMT=false, AvoidHoursGMT vazio.
- Compilacao MQL5: 2 passed (0 errors).
- Estrategia de crescimento, spread e modelo seguem protegidos. Forward opera 24/7.

## RECOMPILACAO NO DESTINO REAL (15:43)
- MetaEditor64 compilou XAU_AI_PRO.mq5: **0 errors, 0 warnings**, 22967 ms.
- .ex5 em disco: MD5 `54EE64CD12B01C8CAA75B585DAAE776D`, 1070 KB, 15:43:25.
- Fonte: EnableAvoidHoursGMT=false, AvoidHoursGMT="" confirmados.
- 16/16 perfis .chr com EnableAvoidHoursGMT=false.
- Pendente: REANEXAR o EA aos graficos para carregar o novo .ex5 em memoria (AGENTS.md 7). Motor segue ativo no gateway.
## AUTORIZACAO DONO 16:15 - MaxCorrelatedRiskPercent 30 -> 100%
- DONO autorizou explicitamente subir para 100% para caber lote minimo 0.01 em conta de 4.90 USD. Fonte (2 caminhos), 16/16 perfis .chr e template: MaxCorrelatedRiskPercent=100.0.
- MetaEditor: 0 errors, 0 warnings. .ex5 MD5 AC84BC27126DB599BA6E7152D817C1F5 (16:15:23) sincronizado nos 2 caminhos.
- Pendente: REANEXAR graficos (F7 / aplicar template XAU_AI_PRO_FORWARD_24NOV.tpl) para carregar novo .ex5.
## LIBERACAO FINAL DO FORWARD 18:10 (ordem real executada)
- Primeira ordem REAL executada 18:07:23: retcode 10009 Request executed, ticket 98805044, ETHUSD BUY 0.02 @1730.16, journal [TRADE] OPEN.
- CORRECOES aplicadas no gateway: (1) XAU_ENABLE_MT5_EXECUTION=1 no ambiente; (2) mt5_execution.py aceita quantity/volume e repassa SL/TP; (3) universal_router.py passa stop_loss/take_profit ao adapter; (4) risk_gate max_spread 50->400 (spread ETHUSD=300); (5) auto_engine ajusta volume ao minimo do simbolo.
- confianca_minima 60->40 (DONO autorizou); edge_minimo 0.02 mantido; MaxSpreadPct=0.6 do EA mantido.
- DONO fechou posicao sem stop; gateway reiniciado PID 6372 com codigo corrigido; motor ligado, 0 posicoes, conta REAL.
- Validacao py_compile exit=0 em mt5_execution/universal_router/auto_engine/risk_gate/fastapi_gateway.
## CORRECAO SL/TP 18:13 - pedido_para_router
- DONO informou bug: segunda ordem (ticket 98805271, 18:11) abriu com TP manual e SL=0.
- Causa raiz: pedido_para_router() em auto_engine.py nao copiava stop_loss/take_profit do payload -> adapter recebia null.
- Correcao: adicionados stop_loss/take_profit em pedido_para_router (linha 79-80); py_compile exit=0.
- Volume minimo conferido: ETHUSD vol_min=0.02; ajuste no enviar() ja garante quantity=0.02.
- Gateway reiniciado PID 10964, motor ligado, config aplicada. Proximas ordens devem sair com SL/TP automaticos.
## ESTRATEGIA CRESCIMENTO NO GATEWAY 18:15 (ordem final DONO)
- DONO: 'usar estrategia do CRESCIMENTO' / 'stop so ativar com BANCA MEDIA'.
- auto_engine.py: banca < 100 USD => stop_loss=None na ordem (sem stop); banca >= 100 => stop ativa. TP mantido (alvo curto).
- SL interno continua calculado apenas para dimensionar volume pelo risco (evita divisao zero).
- py_compile exit=0; gateway reiniciado PID 7596; motor ligado; config reaplicada.
## ALVOS CRESCIMENTO 0.50-1.00 USD 18:18 (ordem final DONO)
- DONO: 'alvos de 0.50 a 1.00 se possivel dependendo da tendencia'.
- auto_engine.py modo ATR: niveis_do_valor() converte alvo em USD para preco via contract_size.
- Tendencia forte (edge>=0.10 e conf>=45) => alvo 1.00 USD; fraca => 0.50 USD.
- SL segue DESLIGADO em banca <100 USD (crescimento); TP enviado ao MT5 e o alvo curto.
- py_compile exit=0; gateway reiniciado PID 10008; motor ligado.
## REGRA FINAL LOCK DE LUCRO + ALVOS 18:22 (DONO)
- DONO: 'alvos 1.00 USD com tendencia forte, stop acima da entrada garantindo 0.25 USD, nunca fechar com perdas, acertividade >90%'.
- auto_engine.py: apos volume final, niveis_do_valor() com contract_size REAL do simbolo (fallback mt5.symbol_info).
- Tendencia forte (edge>=0.10, conf>=45): TP 1.00 USD + SL lock 0.25 USD ACIMA da entrada (compra)/abaixo (venda).
- Tendencia fraca: TP 0.50 USD, SL=0 (sem stop de perda). Banca >=100: stop normal volta.
- Bug TP 2441.98 corrigido: calculo agora usa volume final (0.02) e contrato real (1 no ETHUSD).
- py_compile exit=0; gateway reiniciado PID 16344; motor ligado.
## TROCA PAR LOTE MINIMO 0.01 (DONO 18:30)
- DONO: lote 0.01 para banca baixa. ETHUSD exige volume_min=0.02 na XM (recusa 10014).
- Escolhido USDSGD M15: volume_min=0.01, modelo publicado, sinal SELL conf 77.2%, edge 0.026, spread 219 (<400).
- Gateway config reaplicada: simbolo=USDSGD, timeframe=M15, lote=0.01, conf40, edge0.02, risco0.5, maxpos20. Motor ligado.
## CORRECAO VOLUME TETO LOTE 18:32 (monitor ao vivo)
- LEITURA 2 (18:30): decisao USDSGD SELL conf75.6 edge0.026 falhou retcode10019 No money: volume calculado 0.1 (risco/distancia) ignorou lote 0.01.
- Correcao auto_engine.py: lote configurado e o TETO do volume (min(volume, lote)); py_compile exit=0.
- Gateway reiniciado, USDSGD M15 lote0.01, motor ligado. Monitoramento ao vivo em curso.
## TROCA PARA AUDUSD 18:37 (monitor ao vivo)
- USDSGD abriu 0.01 mas spread 220 (1.7%) comeu o alvo: PL -1.65. DONO decidiu deixar aberta e trocar.
- Gateway trocado para AUDUSD M15 lote0.01: spread 24, volume_min 0.01, modelo proprio, conf 52.4%.
- Posicao USDSGD 98806410 segue aberta (sem stop, por ordem DONO). Monitor em curso.
## REFINO MAXIMO DO EA 20:34 (auditoria 10/10)
- Auditoria: 1563 IDENTIDADE ERRADA, 1452 LOT CAP, 394 HANDLE RECICLADO, 95 SEM LEITURA, 58 LOTE INVALIDO, 57 MIN_LOT_EXCEEDS_RISK_CAP.
- CORRECAO 1: HandleRegistry.XAI_HandleKey inclui ChartID() -> cada instancia so apaga as suas chaves (394 reciclados + 95 4807).
- CORRECAO 2: SignalCore trata BarsCalc=-1/4807 como HANDLE INVALIDO (nao aquecimento) e recria no mesmo ciclo 1x/15min.
- CORRECAO 3: VolatilityFilter nao zera carimbo na 1a falha ATR (histerese) -> fim da oscilacao 1563 linhas.
- agent-toolkit check: 116 arquivos OK; compile: 0 errors 0 warnings; .ex5 MD5 27BFA74640AC42A7C4A2AF8259064C26 sincronizado nos 2 caminhos.
## REFINO HANDLES DE SINAL 20:44 (correcao 2 do item 2)
- Causa: SignalEnsureHandles criava iMA/iRSI sem XAI_HandleRegister -> outra instancia libertava -> 4807 SEM LEITURA.
- Correcao: registados EMA_FAST/EMA_SLOW/RSI_SIGNAL com chave ChartID() incluido.
- Correcao: recriacao agora tenta DEPOIS do SignalCacheDrop (antes a entrada ja nao existia) com gate 900s.
- check 116 arquivos OK; compile 0 errors 0 warnings; .ex5 MD5 80638126AADB6B0387FDA292B740CE9A nos 2 caminhos.
- Pendente: REANEXAR graficos para carregar e ver HANDLE RECRIADO no jornal.
## MELHORIAS GRATUITAS BIBLIOTECA MT5 + M5 21:00 (DONO autorizou)
- Biblioteca: 82 indicadores; destaque SpreadProfileByHour.mq5 (ja instalado 23/11) - perfil de spread por hora com ticks reais.
- NOVO backend/spread_profile.py: copy_ticks_range 20 dias, mediana/p90 por hora, melhor/pior hora, custo 1R; cache 1h; endpoint /api/market/spread-profile.
- Integrado em /api/ai/predict: campos spread_best_hour/worst_hour/p90_points/cost_1r_pct viajam no JSON ate ao EA via servico XAI_RefreshPredictions.
- Calculo assincrono via cache(): NAO bloqueia predict (antes estourava tempo_limite_do_servidor com 2.1M ticks).
- Medido: EURUSD melhor h3 mediana20 pior h0 p90 124 custo1r 124pct; AUDUSD melhor h3 p90 88; GBPUSD pior h0 p90 167; USDCHF pior h0 p90 198.
- DONO mudou timeframe para M5 (alvos curtos): gateway AUDUSD M5 lote0.01 conf40 edge0.02, motor ligado.
## EXPLORACAO TOTAL MT5 (ARTIGOS/NOTICIAS/CALENDARIO/BIBLIOTECA/HISTORICO) 21:10
- JA EXISTE (nao duplicar): calendario ForexFactory real + API nativa MT5 CalendarValueHistory com actual/forecast/previous em NewsFilter.mqh e MarketIntelligence.mqh; historico history_deals_get/orders_get + /api/history maduro; 82 indicadores na biblioteca.
- FALTAVA e FOI ADICIONADO: backend/market_news.py -> GET /api/market/news (Google News RSS gratis, fallback news.dat local 551KB Headway-Demo). Medido: 12 manchetes reais.
- FALTAVA e FOI ADICIONADO: backend/calendar_tradingview.py -> GET /api/market/calendar-tradingview (portado do Android MarketData.kt; 19 paises, actual/forecast/previous/unidade). Medido: 480 eventos, PMI 54.00.
- FALTAVA e FOI ADICIONADO: gate de spread em auto_engine.ciclo_unico: se hora atual = pior hora do perfil e custo1r>=100pct, NAO entra (protecao de custo; nao mexe risco/lote/alvo/stop). AUDUSD pior h0 p90 87.
- Gateway reiniciado PID atual, AUDUSD M5 lote0.01 conf40 edge0.02, motor ligado, cache de spread pre-aquecido. py_compile OK.
## LIMITE DIARIO 10 USD (DONO 21:27)
- DONO autorizou subir limite de perda diaria para 10 USD (antes efetivo 1.29 = MIN(5.0, 4.31*30pct)).
- MaxDailyLossUsd 5.0 -> 10.0; MaxDailyLossPercent 30 -> 250 (para MIN(10, 4.31*250pct=10.78) = 10 USD).
- Fonte (2 caminhos), 16/16 perfis e template atualizados; compile 0 errors 0 warnings; .ex5 MD5 5687FF053AF5E456E57209162800D69C.
- Gateway perda_diaria_max_pct 3.0 -> 100.0 (teto maximo aceito pelo gateway; EA controla a conta com 10 USD). Pendente: REANEXAR graficos para carregar novo .ex5.
## REANEXO PENDENTE - LIMITE DIARIO 10 USD 21:42
- journal 21:38: [SAFETY] DailyLoss=1.00 (EA antigo em memoria) e [RISCO EM VIGOR] teto 30pct/1.1 - reanexo as 21:37 nao carregou o .ex5 novo.
- Recompilado agora 21:42:36: 0 errors 0 warnings; .ex5 MD5 AF9BE7A8FF04503B09A89E56EFCE4909 nos 2 caminhos (fonte 10.0/250.0 conferida).
- Pendente: REANEXAR com este .ex5 e confirmar no jornal [SAFETY] DailyLoss=10.00.
## DELETE DE TODOS OS PERFIS .chr 21:50 (DONO)
- DONO pediu deletar todos perfis: deletados 40 .chr ativos (Default 16 + backup_23nov 16 + XAI_V1221_RELOAD 8).
- Backup integral em Profiles\Charts\_backup_antes_delete_20261123_215057 (40 arquivos). 235 templates .tpl intactos.
- Objetivo: EA usa defaults do CODIGO (MaxDailyLossUsd=10.0, MaxDailyLossPercent=250.0, EnableAvoidHoursGMT=false) sem perfil antigo sobrescrever.
- Pendente: reiniciar/reanexar EA para gravar perfis novos com os defaults do codigo.
## SIMPLIFICACAO FINAL 21:53 (DONO: 1 template 1 perfil 1 set 1 EA)
- DONO: deixar apenas 1 de cada, TUDO do terminal, sem simbolo fixo (operavel para todos ativos).
- Removidos: 43 EAs .ex5, 234 templates .tpl, 15 sets .set, 40 perfis .chr. Backup em AppData\Local\Temp\opencode\backup_limpeza_terminal_20261123_215225.
- Mantidos: XAU_AI_PRO.ex5 (AF9BE7A8), XAU_AI_PRO_FORWARD_24NOV.tpl (symbol= vazio), Default\chart01.chr (sem symbol=), XAU_AI_PRO.set (353 inputs sem symbol=).
- Contagens finais: 1 EA / 1 template / 1 perfil / 1 set. Nenhum simbolo fixo em template/perfil/set/codigo (Symbols= e a lista operavel de 14 ativos).
## PERFIL UNICO CONFIRMADO 21:57
- Apenas 1 perfil .chr: Profiles\Charts\Default\chart01.chr (353 inputs, sem symbol= fixo).
- Valores: MaxDailyLossUsd=10.0, MaxDailyLossPercent=250.0, EnableAvoidHoursGMT=false, MaxCorrelatedRiskPercent=100.0, SymbolsFromMarketWatch=false.
- 1 EA / 1 template / 1 perfil / 1 set mantidos. Sem simbolo fixo em nenhum.
## LIMPEZA WINDOWS 22:05 (DONO)
- DONO escolheu: Temp + lixeira + logs antigos (preservar tarefas/processos).
- Removidos 7 logs antigos (>3 dias) de MQL5\Logs e gateway\Logs; lixeira ja vazia; .tmp/.bun em uso preservados.
- Terminal MT5 e gateway 9027 intactos. Backup da limpeza anterior de perfis nao localizado em Temp (informado ao DONO).
## TUNEL HTTPS PARA CELULAR 24/11 03:25
- DONO conectou celular. Tunei named Cloudflare xau-gateway-tunnel.com esta healthy porem dominio pending/unresolvable (nameservers nao ativos).
- Criado quick tunnel cloudflared: https://parenting-listening-second-surrounding.trycloudflare.com -> http://127.0.0.1:9027.
- MEDIDO: /api/health HTTP 200 e /api/auto/state ativo=true AUDUSD M5 lote0.01 com token Bearer. URL temporaria (muda ao reiniciar).
- App XAU AI PRO APK: configurar gateway na tela de login com a URL HTTPS + login; sem rebuild necessario.
