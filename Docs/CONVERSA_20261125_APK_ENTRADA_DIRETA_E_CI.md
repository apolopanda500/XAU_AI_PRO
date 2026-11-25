# 25/11/2026 - APK entra direto no app, CI do Android e migrate para charts v5

Regra de leitura: o comando vence qualquer numero escrito aqui.

## 1. O que mudou

### Entrada direta no APK

- `frontend/src/components/auth/UserSessionGate.tsx`: em mobile e desktop
  devolve o app direto. `LoginScreen`, `FirstRunWizard` e
  `MobileBiometricLock` nao sao usados no gate.
- `frontend/src/components/MT5AccountsPanel.tsx`: unico passo deixado para o
  operador - sincronizar a conta MT5 aberta no PC. Usa `lib/connections`
  (`detectTerminal`, `saveExchange`, `connectionAction`), as mesmas rotas do
  `ConnectionSettings`: `/api/status`, `/api/connections`. Nao pede senha.
- `frontend/src/components/SettingsCore.tsx`: bloco morto do
  `/api/mt5/auto-login` (404 no gateway 9027) substituido pelo painel acima.
- `frontend/src/components/MobileCommandCenter.tsx` e o teste removidos:
  componente orfa, rotas `/api/mobile/command` e `/api/mobile/control` nao
  existem no gateway.
- `frontend/src-tauri/tauri.conf.json`: `resources: []` - os recursos
  `core/xau-ai-pro-core.exe` e `bridge/**/*` foram para
  `tauri.windows.conf.json`. No Android eles nao existiam e causavam
  `resource path 'core/xau-ai-pro-core.exe' doesn't exist`.
- `frontend/.env.production`: URL e token embutidos para o build. Nenhum dos
  dois e impresso em log, commit ou resposta. O gateway continua fail-closed:
  sem token responde 401.

### Correcoes do CI Android (em cadeia, cada uma medida)

| Run | Falha medida | Causa | Correcao |
|---|---|---|---|
| `45540107567` | `Library artifact not found ... armv7-linux-androideabi/release/libxau_ai_pro_desktop_lib.so` | `CARGO_TARGET_DIR` relativo: o cargo compilava o ARMv7 e terminava com `Finished release`, mas escrevia o `.so` em outro caminho quando o Gradle chamava o Tauri | `CARGO_TARGET_DIR` absoluto no `env` do job (`$GITHUB_WORKSPACE/Temp/cargo-target`) e NDK 28.2.13676358 fixado |
| `45541901654` | `Found version mismatched Tauri packages` | Merges do Dependabot subiram crates Rust `tauri 2.12.7` / `tauri-plugin-notification 2.8.1`, mas deixaram os pacotes npm em `2.11.1` / `2.4.0` | Dependabot seguinte (`487ee916`) alinhou o npm para `@tauri-apps/api 2.12.5`, `plugin-notification 2.8.1`, `cli 2.12.6`; meu commit redundante foi descartado no rebase |
| `45545644746` | `error[E0308]` em `core/src/market/state.rs:63`: `Message::Text` espera `Utf8Bytes`, recebe `String` | bump do `axum 0.8.9` pelo Dependabot | `Message::Text(text.into())` no `push_text` |

O mesmo `E0308` derrubou os workflows `Rust`, `CI` e `Validacao e Empacotamento`
do commit `487ee916`; a correcao acima cobre os quatro. O build Android
`45546286652` fechou **success em 10m35s**.

### Testes Python que so falhavam no CI (corrigido em `5d7809d`)

Os 5 testes `test_ai_inference.py` reprovados nos workflows `ci`,
`Validacao e Empacotamento` e `XAU AI PRO - validacao universal` exigem
artefatos `MULTI_*` treinados, que nao vao no git. Executados localmente nos
mesmos nos antes da correcao: **8 passed** - o checkout do runner e que nao
tem o catalogo. A suite ja tem `skipif` por ausencia de catalogo para outras
classes; estes 5 ficaram de fora e receberam o mesmo guard.

Medido depois: com o catalogo real, `test_ai_inference.py` da **91 passed**;
com `XAU_MODELOS_DIR` apontado para diretorio vazio, os 5 marcados dao
**5 skipped** (prova negativa de que o guard funciona). O workflow `Rust` no
commit `64d5dca` fechou **success** apos a correcao do axum.

### Outras correcoes da suite

- `tests/test_risk_gate.py`: caso negativo agora usa `spread: 401`, alinhado a
  decisao do dono de 23/11 (`max_spread=400`).
- `frontend/src/components/RobotTabs.test.tsx`: 1 montagem de grafico so na
  aba Operacao, 0 nas demais (decisao `8ee8a00e`).
- `backend/{binance,bybit,mexc,okx}_execution.py`: `stop_loss`/`take_profit`
  aceitos e ignorados onde a corretora nao suporta, conforme o contrato do
  router universal. O MT5 aplica.
- `mt5-gateway.spec`: `hiddenimports` dos 7 modulos antes ausentes no bundle.
- `.gitignore`: `*.bak_*` ignorado - backup que a suite gera antes de
  reescrever modelos nao pode entrar no git.

### Migracao para lightweight-charts 5.3.0 (esta rodada)

MEDIDO: o `node_modules` local estava em `4.2.3`, mas o `package-lock.json`
fixa `5.3.0` - `npm ci` confirmou. O CI sempre usou a versao do lockfile, por
isso o typecheck do run `45546743177` reprovou com `addHistogramSeries is not
a function` e os testes de grafico falharam. Nao foi opcao fixar a versao
antiga: a migracao foi feita na API da versao instalada.

- `PriceChart.tsx` e `GraficoIndicador.tsx`: `addSeries(definicao, opcoes)` com
  `CandlestickSeries`, `LineSeries`, `AreaSeries` e `HistogramSeries`.
- Marcadores: `createSeriesMarkers(series, pontos)` substituiu
  `series.setMarkers(...)`. O plugin fica em `marcadoresRef` e e recriado
  quando o tipo de grafico troca a serie — senao o sinal ficaria preso na
  serie antiga.
- Os 5 dubles de teste exportam as definicoes e escolhem a serie por
  IDENTIDADE; definicao desconhecida lanca erro. Prova negativa: passar
  `LineSeries` onde o codigo pede candle reprova, em vez de desenhar a serie
  errada calado.
- `RobotTabs.test.tsx`: o caso dos presets espera `ticketComPadrao11()`
  antes de ler `sl_preco`/`tp_preco`. O corpo so contem esses campos depois
  que o efeito do 1:1 escreveu o status; esperar so o botao era a corrida
  que produzia `expected NaN to be close to 4136.46`. A trava continua
  exigindo os mesmos numeros — so a espera mudou.
- `tests/test_chaos_persistence.py`: `monkeypatch` congela
  `mobile_control.time` no teste de rajada concorrente. `gerado_em` e
  `int(time())`: 20 respostas que cruzam um segundo legitimo eram diferentes
  por ruido. A igualdade integral das 20 respostas NAO foi afrouxada. O novo
  teste `01b` prova o contrario: com relogios diferentes o payload muda, e
  so em `gerado_em` — se outra campo tambem variasse, ele reprova.

## 2. Numeros medidos

| Medicao | Resultado |
|---|---|
| `npx tsc --noEmit` (pos-migracao v5) | **EXIT=0**, 0 erros |
| `npx vitest run` (pos-migracao v5, lockfile 5.3.0) | **90 arquivos, 1049 testes passed** em 77,25s |
| `test_chaos_persistence.py` isolado, 3 rodadas seguidas | **4 passed** em cada rodada |
| `npx vitest run` (no run `45546743177`, codigo v4 + lib v5) | 4 falhas: 3x `addHistogramSeries is not a function`, 1x `NaN` |
| `cargo fmt --all -- --check` (pos-correcao axum) | **OK** |
| `test_ai_inference.py` (catalogo real / vazio) | **91 passed** / **5 skipped** nas provas negativas |
| Suite Python completa (antes desta rodada) | **1630 passed, 2 skipped, 9 warnings** em 541,62s |
| Artefato/spec (`test_bundle_gateway_artefato.py`, `test_spec_gateway.py`, `test_artefato_congelado.py`) | **27 passed** em 31,18s |
| `scripts/sync_version.py --check` | **Todos alinhados**, versao `1.2.191` |
| PyInstaller rebuild | **exit 0**; `mt5-gateway.exe` 28.949.497 bytes |
| Hash do bundle (`dist` vs `frontend/src-tauri/bridge`) | **SHA256 identicos** |
| Tunel com token (`/api/health`, `/api/status`, `/api/connections`) | **HTTP 200 nas 3**; sem token, **401** |
| Build Android `45546286652` | **success em 10m35s** |
| Artefato Android | `app-universal-release-unsigned.apk`, **39,2 MB**, SHA256 comecando em `1AF0FF0609805BEB` |
| APK instalado no QA (`R9XY1016R6V`) | `com.xau_ai_pro.desktop`, `versionName=1.2.191`, `versionCode=1002191`, `targetSdk=37`; assinado com chave debug local |
| Limpeza Windows (`limpeza_segura.ps1 -Apply -DebugCache`) | 2 passagens; 1o removeu `frontend/src-tauri/NONE`; 2o "Nenhum temporario" |
| Disco C: apos limpeza | **1,98 GB livres** |

## 3. Estado do terminal medido (ninguem foi desligado)

- `MetaEditor64.exe` PID `13116`, desde 24/11 19:26:37.
- `metatester64.exe` PID `7604`, desde 25/11 00:39:02 - backtest ativo.
- `terminal64.exe` PID `4256`, desde 25/11 00:43:41.
- Gateway: PID `7396`, `127.0.0.1:9027`. Nenhuma destas sessoes foi encerrada
  por esta sessao.
- Celular fisico conectado: `R9XY1016R6V` (`SM_A057M`), Android 15. O
  emulador `emulator-5554` nao aparece mais na lista do `adb devices`.
- QA no aparelho: app abre direto, sem login/URL/conta do app. Abas
  `Operacao`, `Modelos`, `Risco`, `Operacoes` medidas por `uiautomator dump`.
  Em `Configuracoes > Conexoes & Corretoras`: `CONTA MT5`, o texto "Nenhuma
  senha e enviada pelo celular...", contas vinculadas e botoes
  `Sincronizar MT5` / `Usar esta conta`.
- ATENCAO: o gateway reporta `terminal_connected=false`,
  `mt5_connected=false`, `account=null` e `ea_heartbeat.live=false` com
  `age_sec≈1040`. A sessao MT5 do PC precisa ser reabastecida pelo operador
  para o forward real. Nao foi mexida nesta sessao.

## 4. O que ainda NAO foi feito

- Commit/push das correcoes v5 e dos testes; acompanhar todos os workflows
  do novo commit ate verde. Os runs do commit `236a035`: `45546743177`
  (validacao universal) e `45546743320` (Validacao e Empacotamento)
  falharam; `CodeQL`, `Security Checks`, `Pylint`, `CI`, `ci` e `Rust`
  fecharam success.
- Reconstruir o APK apos a correcao v5: o APK instalado para QA foi compilado
  com a dependencia 5.3.0 mas com chamadas de API v4, entao o grafico pode
  estar quebrado. Repetir instalacao limpa e varredura de telas, com atencao
  especial a candles/volume/indicadores.
- Confirmar com o operador a forma de assinatura definitiva do APK (o QA usou
  chave debug do Android SDK) e reabastecer a sessao MT5 para forward real.
- Deploy final do `.ex5`: nenhuma mudanca MQL5 nesta rodada, entao nao ha
  `.ex5` novo para publicar. Atualizacao de modelos/backtest continua manual
  (equipes alfa/delta encerraram com `Free usage limit reached`). Nenhum
  parametro de risco foi alterado.
- Publicacao no MQL5 CodeBase: **nao autorizada**.

## 5. Cuidados para o proximo ciclo

- Quick tunnel e temporario: se o `cloudflared` reiniciar e trocar a URL, o
  APK tem de ser reconstruido com o novo `VITE_API_BASE`.
- Nao publicar tokens, DSNs ou conteudo de `.env` em log/commit/resposta.
- Nao fechar `terminal64.exe` nem `metatester64.exe` enquanto o backtest roda.
- Antes de `git status` travar: `limpeza_segura.ps1 -Apply -DebugCache`, sem
  `-BuildArtifacts` com build no ar.
- O working tree traz 3 arquivos `.bak_*` versionados deletados pela limpeza
  (`XAU_AI_PRO.ex5.bak_15h40`, `vite.config.ts.bak_20261113`,
  `start_gateway_autostart.cmd.bak_20261117`). Nao foram incluidos neste
  commit; decisao pendente do operador.

## 6. Ciclo 2 — selos, imagens e transporte (25/11/2026)

Espacos separados por decisao do dono: `Temp/opencode/qa-android/ciclo2/antes`
guarda a medida com o APK antigo; `.../ciclo2/depois` recebe a medida depois da
instalacao limpa. Nenhum dos dois diretorios foi limpo entre as passagens.

### Antes (APK 1.2.191 instalado, fonte ja em correcao)

| Medicao | Resultado medido |
|---|---|
| `npx tsc --noEmit` | **EXIT=0**, 0 erros (`ciclo2/antes/tsc.txt`) |
| `npx vitest run` (suíte completa) | **93 arquivos, 1059 testes passed** em 341,57s, **EXIT=0** (`vitest.txt`) |
| `.venv\Scripts\python.exe -m pytest -q tests` | **1631 passed, 2 skipped, 9 warnings** em 372,15s, **EXIT=0** (`pytest.txt`) |
| Classes com `selo` no fonte casadas por `[class*="selo"]` | **12**; so **4** eram chips (`boleta-selo`, `boleta-selo-armado`, `boleta-selo-leitura`, `mc-selo`) |
| Classes sequestradas pela regra de chip | **8**: `confianca-selo`, `selo-marca`, `selo-desenvolvedor`, `selo-nome`, `selo-versao`, `selo-rotulo`, `selo-nome-dev`, `selo-contato` |
| Efeito da regra | `display:inline-flex`, `white-space:nowrap`, `flex-shrink:0`, `overflow:hidden` no cabecalho que precisa de `flex-wrap:wrap` |
| Imagem do topo no APK (XML) | `[28,36][123,131]` — 95x95 px fisicos = 34 CSS px |
| Carimbo do rodape no APK (XML) | `[244,931][362,1050]` — 118x119 px fisicos = 44 CSS px |
| Amostra de pixels da marca em Configuracao | desvio padrao **65,3 / 66,7 / 66,5**, **1012** cores, borda **17,4** — bitmap carregado, nao caixa vazia |
| Cabecalho do APK antes do rebuild | `WS Offline` em todas as telas, com gateway HTTP ativo |
| Separador em `Conexoes & Corretoras` | `&middot;` literal corrigido no fonte para `·`, ainda pendente de rebuild |

O cabecalho de "Confianca & Responsavel" aparece inteiro no dump antes do
build (`XAU AI PRO`, `v1.2.191`, `DESENVOLVIDO POR`, `Henrique de Carvalho` e os
dois contatos). O defeito e estrutural e depende da largura: o curinga retira o
`flex-wrap` do container e impede a quebra em telas mais estreitas. Por isso a
correcao e um seletor explicito, nao um ajuste de pixel numa captura.

### Correcoes aplicadas antes do build

- `frontend/src/theme/design_system_10_10.css`: `[class*="selo"]` e
  `[class*="badge"]` substituidos por `.badge`, `.chip`, `.pill`,
  `.status-pill`, `.symbol-badge`, `.mc-selo`, `.boleta-selo`.
- `frontend/src/theme/design_system_10_10.test.ts`: prova negativa com o CSS
  antigo (o detector TEM de reprovar o curinga), prova de que o CSS real nao
  tem curinga de selo/badge e de que os quatro chips continuam sem vazamento.
- `frontend/src/components/Sidebar.tsx`: `width`/`height`, `decoding="async"` e
  `draggable={false}` nas duas imagens da marca; `Sidebar.test.tsx` trava os
  atributos. Sem dimensoes o navegador reserva 0x0 e o texto salta.
- `frontend/src/components/MT5AccountsPanel.tsx` e teste proprio: separador
  `·` no lugar de `&middot;`.
- `frontend/src/hooks/useMarketWebSocket.ts` e `TopNav.tsx`: sem WS
  configurado nao abre socket e o chip diz `HTTP`, nao `WS Offline`.

### Depois (medido apos build e instalacao limpa)

| Medicao | Depois |
|---|---|
| Commit `4a3e0e83` / workflows | **9 workflows success**, inclusive Android, CI, validacao universal, Rust, Pylint, CodeQL e Security |
| Build Android `45569094436` | **success em 10m54s** |
| Artefato / APK aberto | `XAU_AI_PRO-Android-APK`, 15.983.103 B compactado; unsigned 41.161.747 B; assinado debug **41.224.774 B** |
| SHA-256 (unsigned / assinado) | `BA9442DC…D91EF1A` / `921DB1A0…BE8BD4A4` |
| Versao instalada | `versionName=1.2.191`, `versionCode=1002191`, `targetSdk=37` |
| Instalacao limpa | `adb uninstall` + `adb install` → **Success**; SELF-TEST de assinatura OK (`C=US, O=Android, CN=Android Debug`) |
| Chip de transporte | **`HTTP`** em Operacao, Modelos, Risco, Operacoes, Carteira, Historico, Calendario, Sistema, Configuracoes, Conexoes e Confianca. **`WS Offline` = 0 ocorrencias** |
| Separador em Conexoes | `&middot;` literal **ausente**; U+00B7 (`·`) **presente** — `420750145 · XMGlobal-MT5 17 · Michele Dos Santos` |
| Imagens da marca | mesmos bounds `[28,36][123,131]` e `[244,931][362,1050]`; mesma amostra de pixels (95x95, desvio 65,3/66,7/66,5, 1012 cores; 118x119, desvio 43,9/48,0/49,7, 977 cores) — a mudanca e reserva de layout, nao cosmética |
| Cabecalho de Confianca | e-mail de **32 → 40 px** de altura; telefone de **34 → 42 px**; nome, versao e contatos presentes, sem corte |
| Logcat do app | nenhum `Uncaught`, `TypeError`, `FATAL EXCEPTION` ou erro de recurso; apenas ruido de frame rate do WebView |
| Conta no app | `Conta 420750145 @ XMGlobal-MT5 17 vinculada e escolhida para o app. Nenhuma ordem foi enviada.` |

As capturas ficam em `ciclo2/depois` (`operacao`, `config`, `confianca`,
`conexoes`, `modelos`, `risco`, `operacoes`, `carteira`, `historico`,
`calendario`, `sistema`), uma para cada tela varrida. O comparador
`ciclo2/compara.py` le os dois diretorios e reproduz a tabela acima a partir
dos XML e PNG, sem depender de leitura visual.

Nenhuma ordem foi enviada, nenhum parametro de risco foi alterado, nenhum
`Ligar IA`/automacao/`Aplicar limites ao motor` foi acionado. Gateway,
backtests e forward continuam de pe. Medido no fim: gateway PID `7396` em
`127.0.0.1:9027`, terminal PID `15936` em `127.0.0.1:9001`, quatro
`metatester64`/`MetaTester64`, `MetaEditor64` PID `13116`. O PID do terminal
mudou duas vezes durante a sessao (`9468 → 10536 → 15936`) sem acao desta
sessao; se o operador nao reiniciou o MT5, o motivo precisa ser apurado antes
de confiar na continuidade do forward.

### Tres decisoes resolvidas (autorizadas e recomendadas pelo operador)

| Decisao | Antes | Depois (medido) |
|---|---|---|
| Dataset MT5 | `SIMBOLOS` so com `XAUUSD`; `GOLD` nunca exportado e `MULTI_METALS` aprendeu com 384 barras de um simbolo que o grafico nao executa | Commit separado `6cc5e53` publicado em `origin/main` com `GOLD`, `BTCUSD`, `ETHUSD`. Ausente na corretora e ignorado com mensagem, nunca inventado. |
| Assinatura do APK | debug key do SDK (`CN=Android Debug`), SHA `921DB1A0.BE8BD4A4` | Keystore de release dedicada `C:\Users\Micro\.android\xau-ai-pro-release.jks`, alias `xau-ai-pro`, RSA 2048, validade 10000 dias; senha aleatoria em `xau-ai-pro-release.key` com ACL restrita (nunca impressa). APK `qa-android/ciclo2/assinado/app-universal-release.apk`, SHA-256 `8A493028...7428C2`, `apksigner verify`: **Verifies**, v2=true, v3=true, 1 signer, DN `CN=XAU AI PRO`. `versionCode=1002191`, `versionName=1.2.191` inalterados. `adb uninstall` + `adb install` **Success**. |
| Heartbeat oscilante | `/api/status` com `ea_heartbeat.symbol` alternando entre `EURUSD`, `GOLD`, `BTCUSD`; TopNav alternava `no gráfico · EURUSD 5` / `no gráfico · GOLD 5` | `Integration/EAHeartbeat.mqh` (copia canonica **e** embutida): `symbol="FLEET"`, `timeframe=0`, com `writer_symbol`/`writer_timeframe` aditivos. Separacao do tester intacta. `pytest tests/test_heartbeat_frota.py`: **3 passed** (inclui prova negativa: o formato antigo com `_Symbol` reprova). `pytest tests/test_mql5_compila.py`: **2 passed** no MetaEditor64. |

Keystore/senha ficam FORA do repositorio e nao sao registrados em log, commit
ou mensagem. Se o operador ja tiver uma keystore corporativa, basta substituir
o caminho e o alias na proxima assinatura; o APK atual e valido para uso e
instalacao, mas nao tera a mesma identidade de um keystore oficial futura.

### Ainda pendente (acao do operador, nao automatizada neste ambiente)

- **Reanexar os EAs no MT5** para que o `.ex5` recompilado passe a gravar o
  novo formato. O codigo compilou, mas o heartbeat lido agora ainda e o dos
  EAs antigos: sem reanexacao nao ha medicao pos disponivel. Nao ha ferramenta
  MCP de reanexacao nesta sessao e `backend/chart_attach.py` corretamente se
  recusa a gravar `.chr` com `terminal64.exe` aberto (PID `15936`), para nao
  derrubar o forward. Feche apenas os graficos e reanexe os mesmos EAs com as
  mesmas entradas, sem tocar em `Ligar IA`, automacao, limites ou ordens.
- Depois da reanexacao, conferir `/api/status`: `ea_heartbeat.symbol` deve ser
  `FLEET` e `writer_symbol` deve mostrar o ultimo grafico, sem oscilacao no
  `symbol`.
- Relink da conta `420750145 @ XMGlobal-MT5 17` no APK recem-instalado via
  `Sincronizar MT5` (acao segura, ja usada neste ciclo). Nenhuma ordem foi
  enviada.

## 7. Ciclo 3 — heartbeat em producao e trava da copia canonica (25/11/2026)

### Antes

| Medicao | Resultado medido |
|---|---|
| `ea_heartbeat.symbol` em `/api/status` | oscilava `ETHUSD → EURUSD → GOLD`; `writer_symbol` ausente |
| `.ex5` canonico | `2026-11-25 05:41`, enquanto o fonte canonico era das `05:48` |
| `pytest tests/test_mql5_compila.py` | **2 passed**, verde com o EA de producao defasado — o teste compilava so a copia embutida |
| Gateway local | porta `9027` sem listener (PID antigo morto na reinicializacao externa) |
| Tunel rapido antigo | `signals-llc-illustrations-viewer.trycloudflare.com` nao resolvia; URL morta embutida no APK assinado |

### Correcoes aplicadas

- `tests/test_mql5_compila.py`: `EA = CANONICA if CANONICA.is_file() else EMBUTIDA`,
  onde `CANONICA = RAIZ.parents[1]/"Experts"/"XAU_AI_PRO"/"XAU_AI_PRO.mq5"`.
  Nova guarda `test_ex5_canonico_nao_esta_defasado` compara o mtime do `.ex5`
  contra o `.mq5` e todos os `.mqh` includes, com prova negativa
  (`test_prova_negativa_detecta_ex5_defasado`: include mais novo reprova,
  binario recompilado volta a passar).
- Compilacao explicita da copia canonica no MetaEditor64.

### Depois (medido)

| Medicao | Resultado medido |
|---|---|
| MetaEditor64 na canonica | **`Result: 0 errors, 0 warnings`**; `XAU_AI_PRO.ex5` com mtime `2026-11-25 14:09:42`, 1.137.470 bytes |
| `pytest -q tests/test_mql5_compila.py` | **4 passed** (antes: 2), incluindo a prova negativa do `.ex5` defasado. A prova negativa era **flaky**: igualava o mtime do `.ex5` ao do `.mq5`, mas o `.mqh` e escrito logo depois e ora casava, ora nao, na granularidade do sistema. Corrigido para usar `_fonte_mais_recente(ea)`; `pytest -q tests/test_mql5_compila.py tests/test_heartbeat_frota.py`: **7 passed** |
| `pytest -q tests/test_heartbeat_frota.py` | **3 passed** (prova negativa do formato antigo com `_Symbol`) |
| Gateway local | `start_gateway.bat` sem `real`: PID `13188` listening em `127.0.0.1:9027`; nenhuma porta de execucao armada |
| `/api/health` | `ok=true`, `source=mt5_gateway`, `gateway_build=xau-ai-pro-1.2.191-universal-20261113` |
| `/api/status` as `17:18:39` | `schema=ea-heartbeat.v1`, `symbol=FLEET`, `writer_symbol=EURUSD`, `timeframe=0`, `writer_timeframe=5`, `live=true`, `age_sec=0.2`, `state=RUNNING`, `write_count=172` |
| Conta lida | `420750145 @ XMGlobal-MT5 17`, `Michele Dos Santos`, `balance=9.92`, `equity=15.06`, `mode=REAL`, `account_confirmed=false` — somente leitura, nenhuma ordem |
| Commit `375af7bd` | **8 workflows `completed success`**: validacao universal, `ci`, `CI`, Rust, Security, Pylint, Validacao e Empacotamento, CodeQL |
| Emulador | `emulator-5554` online; APK assinado instalado com `Success` (`adb uninstall` + `install`) |

A pendencia de reanexacao do ciclo 2 ficou **resolvida sem intervencao manual
desta sessao**: o heartbeat em producao passou a gravar `FLEET` com
`writer_symbol` logo apos a compilacao da copia canonica. A medicao vence a
suposicao anterior; nao se deve reanexar nada so para "seguir o plano" quando
o dado ja mostra o formato novo no grafico.

### Novo tunnel medido

O quick tunnel antigo nao resolvia mais. O novo aponta para
`127.0.0.1:9027` e foi medido **antes** de embutir a URL no APK:

| Medicao | Resultado |
|---|---|
| `GET /api/health` com `Authorization: Bearer` | **HTTP 200**, `ok=true`, `source=mt5_gateway`, build `1.2.191` |
| `GET /api/status` com token | `schema=ea-heartbeat.v1`, `symbol=FLEET`, `writer_symbol=BTCUSD`, `timeframe=0`, `writer_timeframe=5`, `live=true`, `age_sec=0.9`, conta `420750145 @ XMGlobal-MT5 17`, `mode=REAL`, `confirmed=false` |
| `GET /api/health` sem token | **HTTP 401** — prova negativa, fail-closed intacto |

`frontend/.env.production`: somente a linha `VITE_API_BASE` foi trocada; o token
permanece o mesmo e nao foi lido nem impresso em nenhum passo. Quick tunnel e
temporario por definicao: se a URL trocar, o APK fica cego mesmo com gateway
local sao, e sera preciso rebuildar.

### Pendente neste ciclo

- Commit/push de `tests/test_mql5_compila.py`, `frontend/.env.production` e
  desta secao em `origin/main`.
- Rebuild, assinatura com `xau-ai-pro-release.jks` e reinstalacao no emulador;
  QA das 11 telas com capturas em `qa-android/emulador` (espaco separado de
  `ciclo2/antes` e `ciclo2/depois`).
- `Sincronizar MT5` no emulador para religar `420750145 @ XMGlobal-MT5 17`,
  sem tocar em `Ligar IA`, automacao, limites ou ordens.

## 8. Emulador — antes do rebuild com a URL nova

Espaco separado: `Temp/opencode/qa-android/emulador/antes` (nao misturado com
`ciclo2/antes`, `ciclo2/depois` nem `ciclo3/assinado`). App aberto no
`emulator-5554`, PID `5179`, com o APK assinado que ainda traz a URL morta.

| Medicao | Antes (URL antiga) |
|---|---|
| Chip de transporte | `Gateway por HTTP polling; nenhum servidor WebSocket configurado.` — sem `WS Offline` |
| Cabecalho `AI` | `Inativo` |
| Cabecalho `EA` | **`sem leitura`** — o gateway local esta sao, mas o app aponta para hostname que nao resolve |
| Robo | `Sem par escolhido`, `sem corretora`, `Reconectando.`, `Parado` |
| Modelos | `Nao foi possivel ler os modelos.` |
| Logcat filtrado (`ERR_`, `net::`, `FATAL EXCEPTION`, `trycloudflare`) | nenhuma linha — a falha e silenciosa na UI, sem erro de JS |

E a prova negativa que faltava: gateway `ok=true` com heartbeat `live=true`,
tunel novo `200` com token e `401` sem token, e ainda assim o app instalado
mostra `EA: sem leitura`. O defecto e a URL embutida, nao o gateway nem o EA.
O helper `qa-emulador.ps1` teve um erro de sintaxe descoberto aqui
(`$_.content-desc` interpretado como subtracao); corrigido para
`$_.'content-desc'` antes de qualquer captura.

## 9. Emulador — depois do rebuild da URL (medido antes da correção da nav)

Mesmo espaco `emulador/depois`, APK `ciclo3/assinado` instalado com
`uninstall` + `install` **Success**; assinatura `Verifies`, v2/v3 true, 1
signer `CN=XAU AI PRO`, SHA-256 `60381EBC…4FD391`, 41.224.774 bytes.

| Tela | Depois (URL nova) | Antes (URL morta) |
|---|---|---|
| Operacao | `EA: no gráfico · FLEET`, `Gateway HTTP`, `Parado`, `Gateway por HTTP polling` sem `WS Offline` | `EA: sem leitura`, `Reconectando.` |
| Modelos | `8 artefatos`, `17 de 17 períodos podem operar` | `Nao foi possivel ler os modelos.` |
| Operações (terminal ao vivo) | `saldo 9,92`, `patrimônio 15,06` lidos do gateway | sem leitura |
| Carteira | `Ao vivo · 17:51:42`, `Contas conectadas 1/1`, `MT5 · Conectada · 9,92` | sem corretora |
| Histórico | `REGISTRO UNIVERSAL`, `Exibindo 21` | — |
| Calendário | `101 eventos`, `Atualizado 17:52:55` | — |
| Sistema | `Gateway respondendo`, `Latência 470 ms`, `Mobile ativo` | — |

Nenhum `Uncaught`, `TypeError`, `FATAL EXCEPTION` ou `net::` no logcat do app.
Nenhuma ordem, `Ligar IA`, automacao ou limite de risco foi acionado.

### Defeito descoberto no QA: Configurações inalcançável no telefone

MEDIDO no `emulator-5554` (720px): `@media (max-width:768px)` esconde o
`.sidebar`, e `MobileBottomNav` tinha apenas 5 itens — `robot`, `portfolio`,
`history`, `calendar`, `system`. `settings` ficou **fora** da navegação, e
`Configurações → Conexões & Corretoras` (onde o dono vincula a conta MT5)
ficou inalcançável no APK. O comentario do CSS afirmava que "a barra inferior
ja cobre todas as abas" — estava errado e foi corrigido junto.

Correcao aplicada:

- `frontend/src/components/MobileBottomNav.tsx`: 6 itens, com
  `{ id: 'settings', label: 'Config', icon: '🔧' }`; `ITEMS` renomeado para
  `MOBILE_NAV_ITEMS` e exportado, `gridTemplateColumns` acompanha o tamanho.
- `frontend/src/theme/global.css`: comentário do `@media (max-width:768px)`
  atualizado com a medição.
- `frontend/src/components/MobileBottomNav.test.tsx`: 3 testes, incluindo
  **prova negativa** (a lista antiga de 5 itens nao contém `settings` e o
  predicado TEM de reprovar) e o clique em `Config` mudando `activeTab`.
- `npx vitest run src/components/MobileBottomNav.test.tsx`: **3 passed**;
  `npx tsc --noEmit`: **0 erros** (0 bytes de saida);
  `npx vitest run` completo: **94 arquivos, 1062 testes passed** em 361,45s
  (antes: 93 arquivos, 1059 testes — +1 arquivo, +3 testes).

## 10. Ciclo 4 — o 6º botão fora da viewport (25/11/2026)

Build `45671660269` concluído em **11m34s**; APK assinado com a keystore
definitiva, `Verifies` v2/v3 true, 1 signer `CN=XAU AI PRO`, `versionCode
1002191`, SHA-256 `3CBCE671…CE15CF`, instalado no `emulator-5554` com
`uninstall` + `install` **Success**.

### Antes (APK do ciclo 4, grid `repeat(6, 1fr)`)

| Medicao | Resultado medido |
|---|---|
| DOM | `Config` existe e é `clickable=true` |
| Bounds do `Config` | **`[0,0][0,0]`** — botão não layoutado, fora da viewport |
| Tap em `(660,1194)` | continua em `Sistema` |
| Tap em `(705,1194)` | continua em `Sistema` |
| Bundle local (`App-B0takEzs.js`) | `gridTemplateColumns: repeat(${Ba.length}, 1fr)`, `Ba` com 6 itens |

Causa: `1fr` tem `min-width:auto`. Com 6 itens em 720px, o conteúdo
(`font-size 11`, rótulos longos, `gap:4`, `padding:6px`) força a coluna mínima
e o sexto botão é empurrado para fora. O teste de clique passava no jsdom porque
jsdom não faz layout — o defeito só apareceu no aparelho.

### Correção aplicada

- `MobileBottomNav.tsx`: `MOBILE_NAV_GRID` exportado com
  `repeat(${MOBILE_NAV_ITEMS.length}, minmax(0, 1fr))`, usado pelo componente e
  importado pelo teste (o teste não repete a string); `gap: 2` e
  `padding: '6px 4px …'`, botão com `padding: '8px 2px'`.
- `MobileBottomNav.test.tsx`: 5 testes, com **prova negativa** de
  `repeat(6, 1fr)`; `afterEach(cleanup)` explícito porque o vitest roda sem
  `globals`; normalização `0px → 0` porque o jsdom reescreve `minmax(0,1fr)`.
- `npx vitest run src/components/MobileBottomNav.test.tsx`: **5 passed**;
  `npx tsc --noEmit`: **0 erros**; `npm run build`: OK. O bundle
  `App-DJiOaT-n.js` contém `Va=repeat(${Ba.length}, minmax(0, 1fr))` e `Ba`
  com 6 itens (conferido por leitura do bundle, não por suposição).
- `npx vitest run` completo: **94 arquivos, 1064 testes passed** em 370,80s
  (antes: 94 arquivos, 1062 testes — +2 testes).

## 11. Ciclo 5 — APK final, `Config` tocável e MT5 vinculado (25/11/2026)

Commit `284b94bd` publicado em `origin/main`. Build Android final
`45677084995` concluído em **10m35s** (`success`); artefato baixado, assinado
com a keystore definitiva (`Verifies`, v2/v3 true, 1 signer `CN=XAU AI PRO`,
`versionCode 1002191`, `versionName 1.2.191`, 41.224.774 bytes, SHA-256
`C34CFCCC…CBD96DBC`) e instalado no `emulator-5554` com `uninstall` + `install`
**Success**.

### Antes e depois do 6º botão, medido no aparelho

| Medicao | Antes (ciclo 4) | Depois (ciclo 5) |
|---|---|---|
| Bounds de `Config` | `[0,0][0,0]` | **`[596,1122][712,1267]`** |
| Tap em `(654,1194)` | continuava em `Sistema` | abre `CONFIGURAÇÕES` |
| Grid no bundle | `repeat(${Ba.length}, 1fr)` | `repeat(${Ba.length}, minmax(0, 1fr))` |

O helper `qa-emulador.ps1` tambem foi endurecido: ignora nos com bounds
`[0,0][0,0]`, que era exatamente o que escondia o botao fora da viewport.

### Navegação e vinculação, medidas no APK final

- `Config` -> `Conexões & Corretoras` -> `Sincronizar MT5`: em retrato, o painel
  fica abaixo da nav vertical, por isso foi preciso rolar até o botao aparecer
  com bounds `[170,775][511,866]`. Tap em `(340,820)` produziu
  **`MT5 sincronizado: 420750145 @ XMGlobal-MT5 17. Conexão registrada como as
  demais e marcada como conta ativa.`** A linha da conta passou a mostrar
  `Em uso`. Nenhuma ordem foi enviada.
- `Confiança & Responsável` abriu com `DESENVOLVIDO POR`,
  `O QUE ESTE APP NUNCA FAZ` e `Build: XAU AI PRO v1.2.191 · Windows · conta
  conectada agora: 420750145 · Michele Dos Santos`.
- Abas `Operar`, `Carteira`, `Histórico`, `Calendário`, `Sistema` e `Config`
  varridas uma a uma, todas renderizando.
- Nuance de medicao: o uiautomator devolve o `title` do `<span>` em vez do
  texto interno. Por isso o chip `HTTP` nao aparece no XML; por CDP
  (`Runtime.evaluate` no WebView) mediu-se `innerText="HTTP"`, `title="Gateway
  por HTTP polling; nenhum servidor WebSocket configurado."`, `visivel=true`,
  `EA: no gráfico · FLEET` e `WS Offline=false`. O app segue sem socket aberto.

### Estado do sistema após o QA

- `logcat -t 3000` filtrado por `Uncaught|TypeError|ReferenceError|ERR_|net::|FATAL
  EXCEPTION`: **0 erros**.
- Tunel: `/api/health` **200 com token** e **401 sem token** (prova negativa);
  `/api/status` com `schema=ea-heartbeat.v1`, `symbol=FLEET`,
  `writer_symbol=Nvidia`, `writer_timeframe=5`, `live=true`, `age_sec=0.3`,
  conta `420750145 @ XMGlobal-MT5 17`, `mode=REAL`, `confirmed=false`.
- Processos intactos: `terminal64` 1, `metatester64`/`MetaTester64` 4,
  `cloudflared` 2. Gateway local escutando em `127.0.0.1:9027`.
- Nao foram acionados `Ligar IA`, automacao, `Aplicar limites ao motor`,
  parametro de risco, compra ou venda. O painel permaneceu `Parado`.

## 12. Ciclo 6 - URL estavel e APK no celular fisico (25/11/2026)

O dominio pai `xau-gateway-tunnel.com` custava USD 11,17/ano e foi recusado.
Caminho escolhido pelo dono: **Proxy Worker gratuito**.

| Item | Medido |
|---|---|
| URL estavel do app | `https://xau-gw-proxy.rickjax123.workers.dev` |
| Binding do Worker | `UPSTREAM_BASE` -> `https://staying-better-hours-johnny.trycloudflare.com` |
| Conta/ID do Worker | `03071acfcc40e9b53fa953e22d15942c` / `98be257b621a4fb9bf96a22df4d3d3cc` |
| Versao publicada | `f3b028d8-0d19-4414-9e2f-b17e9bbd3e6b` |
| `/api/health` | **200 com token**, **401 sem token** (prova negativa) |
| Tunel morto | quick tunnel antigo `separated-chuck...` devolvia `Unauthorized: Tunnel not found`; PID 1280 ainda tenta reconectar, PID 9024 atende |
| Unico `.env.production` alterado | `VITE_API_BASE` apontando para o Worker |
| Commit publicado | `aab1d63` (`build(android): apontar gateway para proxy estavel workers.dev`) |
| Build Android | `45699872259`, `success`, ~10m07s |
| APK assinado | `Verifies`, v2/v3 true, 1 signer `CN=XAU AI PRO`, RSA 2048, `versionCode 1002191`, `versionName 1.2.191`, 41.224.774 bytes |
| SHA-256 do APK | `0EAF6949902A430BFAE2347968A895E45005D4BE74598C50A07B56358B1B267D` |
| Celular fisico `R9XY1016R6V` | APK antigo removido, logcat limpo, APK novo instalado e aberto; abre direto, sem login, chip `HTTP`, `EA: no grafico · FLEET`, `Parado`, **0 erros** relevantes no logcat |

O Worker antigo `xau-ai-pro` continua sendo so o frontend estatico e nao foi
alterado. O gateway local segue em `127.0.0.1:9027` (PID 13188) e o Worker
fala com ele pelo tunel; nenhuma senha ou token foi impresso.

## 13. Ciclo 7 - todos os mercados MT5 e a causa dos selos quebrados (25/11/2026)

### 13.1 "so esta lendo uma conta, quero tudo junto"

MEDIDO no APK 1.2.191: `Sincronizar MT5` chamava `saveExchange` uma unica vez,
com `marketsFor('mt5')[0]`. O backend ja aceita os nove mercados
(`backend/broker_registry.py::MT5_MARKETS`) e `connection_store.resolve_connection`
trata sessao MT5 como valida em todos eles; o frontend era que registrava so um.

Mudanca:

- `frontend/src/lib/sincronizarMt5.ts` (novo): `sincronizarMercadosMt5()` le a
  sessao uma vez, registra e testa os nove mercados no mesmo caminho das outras
  conexoes (`detectTerminal`, `saveExchange`, `connectionAction(id,'test')`).
  Falha isolada vira `falhas` no relatorio e nao apaga os outros. Nenhum mercado
  registrado = erro, nunca relatorio de sucesso. Nenhuma ordem e enviada.
- `MT5AccountsPanel`: botao unico `Sincronizar MT5 (todos os mercados)`;
  preserva o ID ativo anterior quando ele continua existindo; mostra
  `9/9 mercados registrados (...)` e `Nenhuma ordem foi enviada.`
- `ConnectionSettings`: usa o mesmo helper; o `<select>` passa a escolher so
  qual mercado fica **ativo**, nao quais mercados sao cadastrados.
- ID gravado e `broker:market:nome` (`lib/connections.ts`), distinto por
  mercado; conferido no backend (`connection_service._gravar`).

Validacao: `npx tsc --noEmit` EXIT=0; 3 arquivos focados **27 testes passed**;
provas negativas (mercado fora do catalogo nao entra, falha isolada dita na
tela, nenhum registrado nao gera sucesso).

### 13.2 "os selos e imagens do xa ai pro continuam bugado"

Causa **medida**, sem suposicao:

| Medicao | Antes | Depois da causa |
|---|---|---|
| Entradas no APK | so `assets/tauri.conf.json`, `assets/dexopt/*`, `res/*.png`, libs | os PNGs do frontend nao estao no APK |
| Conteudo do `lib/arm64-v8a/libxau_ai_pro_desktop_lib.so` | `/index.html`, `/favicon.ico`, `/assets/App-*.js`, `/assets/index-*.js|css` | **nenhum** `/xau-ai-pro-mark.png`, `/xau-ai-pro-quantum-cover.png`, `/favicon.png` |
| `frontend/public/` no PC | 3 PNGs presentes (1254x1254; 2.155.508, 2.155.508, 2.291.309 bytes) | desktop parecia certo |
| `git ls-files frontend/public` | so `index.html` | os 3 PNGs ignorados por `.gitignore:191-192` |

O checkout limpo do CI nao tinha os PNGs; `npm run build` gerava `dist` sem
eles e o Tauri os omitia do embed. No PC os arquivos existiam, por isso o
defeito so aparecia no APK. Correcao: remover as duas regras de ignore,
versionar os 3 PNGs e travar com `tests/test_assets_frontend.py` (2 testes,
inclusive prova negativa de que `Docs/branding/*.png` continua ignorado).

Nuance de medicao: `?` e `\\u0007` vistos no console do PowerShell eram
artefato de encoding cp1252, **nao defeito do app**. O XML do uiautomator
contem `\\U0001f916` (🤖) corretamente.

### 13.3 Validacao completa e publicacao

| Comando | Resultado |
|---|---|
| `npx tsc --noEmit` | **EXIT=0** |
| `npx vitest run` | **95 arquivos, 1073 testes passed**, EXIT=0 |
| `npm run build` | **EXIT=0**, 214 modulos, 1,28s |
| `.venv\Scripts\python.exe -m pytest -q tests` | **1636 passed, 2 skipped, 9 warnings**, EXIT=0 |
| `pytest -q tests/test_assets_frontend.py` | **2 passed** |
| Commit / push | `56d7f6b` em `origin/main` |
| Build Android | `45704662419` disparado |

### 13.4 Estado medido e o que nao foi feito

- Processos intactos: `terminal64` 1, `metatester64`/`MetaTester64` 4,
  `cloudflared` 3, gateway em `127.0.0.1:9027` (PID 13188) e terminal em
  `127.0.0.1:9001` (PID 13516).
- No celular fisico o cabecalho mostrou `EA: RUNNING · sem sinal ha 142s`;
  o app segue sem socket WebSocket e com chip `HTTP`.
- Conta REAL lida: `420750145 @ XMGlobal-MT5 17`, `mode=REAL`,
  `confirmed=false`. **Nenhuma ordem foi enviada.**
- Nao foram acionados `Ligar IA`, automacao, `Aplicar limites ao motor`,
  parametro de risco, compra ou venda.
- Perguntas que continuam com o dono: (1) confirmar formalmente a conta REAL
  antes de qualquer operacao; (2) se algum outro selo/imagem especifico ainda
  parece errado, indicar qual tela e qual elemento, porque os PNGs do frontend
  agora estao versionados e a proxima instalacao tera que medir o embed.

## 14. Ciclo 8 - o APK novo prova os selos, e o terminal some (25/11/2026)

### 14.1 Build, assinatura e embed

| Item | Antes (ciclo 6) | Depois (ciclo 7) |
|---|---|---|
| Build | `45699872259`, `success` | `45704662419`, `success` em **9m0s**, `headSha 56d7f6b` |
| APK assinado | 41.224.774 bytes | **58.919.494 bytes** |
| SHA-256 | `0EAF6949...B267D` | `7DA834B621D4BD815349FB92CB0EA9018FC9FAE8A7595AAF14C360F636D5A60B` |
| Assinatura | v2/v3 true, 1 signer `CN=XAU AI PRO`, RSA 2048 | v2/v3 true, 1 signer `CN=XAU AI PRO`, RSA 2048 |
| `lib/arm64-v8a/libxau_ai_pro_desktop_lib.so` | 10.720.208 bytes | **15.143.352 bytes** (+4.423.144) |
| `/xau-ai-pro-mark.png` no `.so` | **0 ocorrencias** | **1 ocorrencia** (offset 936.653) |
| `/xau-ai-pro-quantum-cover.png` no `.so` | **0** | **1** (offset 3.981.091) |
| `/favicon.png` no `.so` | **0** | **1** (offset 3.981.079) |
| `/index.html`, `/assets/App-*` no `.so` | presentes | presentes (inalterados) |

O artefato do CI e o upload-artifact v7, nome `XAU_AI_PRO-Android-APK`.
A senha da keystore foi passada por variavel de ambiente (`env:` do
`apksigner`), nunca por linha de comando, log ou mensagem — o arquivo
`.key` nao termina em newline e `--ks-pass file:` devolvia
`end of file reached`. Nenhuma senha foi impressa.

### 14.2 Prova no aparelho (CDP no emulador, uiautomator no fisico)

No `emulator-5554`, com CDP ligado (`webview_devtools_remote_14453`), o DOM
mediu:

- `document.title = "XAU AI PRO - Trading Desk"`, `location.href =
  https://tauri.localhost/`, 400 nos, texto real da tela.
- `document.images`: duas entradas de `/xau-ai-pro-mark.png`, ambas
  `complete=true`, `naturalWidth=1254`, `naturalHeight=1254`.
- `performance.getEntriesByType('resource')`: `/xau-ai-pro-mark.png`
  **200** (duas vezes) e `/xau-ai-pro-quantum-cover.png` **200**.
- `getComputedStyle(app-shell).backgroundImage` contem
  `url("https://tauri.localhost/xau-ai-pro-quantum-cover.png")`.

Ou seja: **logo, capa e favicon deixaram de estar quebrados**. Os `?` vistos
no console do PowerShell seguem sendo artefato de cp1252; o XML do
uiautomator contem `U+1F916` (🤖) e os textos "O QUE ESTE APP NUNCA FAZ",
"Saque e transferencia nao existem.", "Execucao real desligada por padrao."
corretamente. Nao ha mais imagem ausente para apontar.

No celular fisico `R9XY1016R6V` o APK foi instalado com `uninstall` +
`install` **Success**, aberto direto no app, e as telas `Operar`, `Carteira`,
`Histórico`, `Calendário`, `Sistema`, `Config`, `Conexões & Corretoras` e
`Confiança & Responsável` foram varridas: 33 a 70 nos por tela, **0 erros**
de JS/rede no logcat (filtro por PID do app). O app segue em `HTTP`, sem
socket WebSocket. O CDP nao existe no fisico; por isso a prova de imagem
foi feita no emulador com o **mesmo APK assinado**.

### 14.3 O bloqueio da sincronizacao: nao e o helper

MEDIDO em `/api/status` (gateway local `127.0.0.1:9027` **e** Worker estavel):
`terminal_connected=false`, `account` vazio. O app replica isso na tela
("Nenhuma conta logada no terminal"). No XML do botao:
`Sincronizar MT5 (todos os mercados)` com **`enabled="false"`** — o
componente desabilita quando `!detectada` (`MT5AccountsPanel.tsx:137`).
O clique por coordenadas, portanto, nao chama `sincronizarMercadosMt5`:
nao e falha do helper, e pre-condicao ausente.

Causa do `terminal_connected=false`, medida: **`terminal64.exe nao esta mais
rodando`**. O ultimo registro do journal do MT5 e de **18:26:30**
(`[LEARN] historico verificado ...`), e a porta `127.0.0.1:9001` esta livre.
Antes do QA o mesmo par estava vivo (`terminal64` PID 13516 / porta 9001).
Os 4 `metatester64`/`MetaTester64` (backtest) e os 3 `cloudflared` seguem
intactos; o gateway segue em `9027` (PID 13188). Nenhum comando desta sessao
encerrou o terminal: as acoes foram `git`, `adb`, `gh`, `npm`, `pytest` e
leituras de API. Nao ha auditoria do Windows (`Event ID 4689`) para dizer
quem o fechou.

Antes disso, baseline em `/api/connections`: 6 conexoes, apenas 4 mercados
MT5 distintos (`forex`, `metals`, `indices`, `crypto-futures`). Depois do QA
a contagem nao mudou — prova de que **nenhum mercado foi registrado sem
sessao**, como o helper exige. A prova positiva de `9/9 mercados registrados`
fica condicionada a `terminal_connected=true`.

### 14.4 Estado e perguntas ao dono

- Nao foram acionados `Ligar IA`, automacao, `Aplicar limites ao motor`,
  parametro de risco, compra ou venda. Nenhuma ordem foi enviada.
- Gateway estavel respondeu `/api/health` **200** com token durante todo o
  ciclo; o Worker antigo `xau-ai-pro` continua so frontend estatico.
- Perguntas:
  1. O `terminal64.exe` foi fechado de proposito? Posso reabri-lo (sem tocar
     nos 4 backtests) para restaurar o forward e permitir a prova de
     `9/9 mercados registrados`? Reabrir nao reanexa o EA ao grafico — isso
     precisa de acao explicita no terminal.
  2. Confirmo formalmente a conta REAL `420750145 @ XMGlobal-MT5 17`
     (`mode=REAL`, `confirmed=false`) antes de qualquer operacao?
  3. Algum selo ou imagem especifica ainda parece errada? Se sim, qual tela e
     qual elemento — porque os tres PNGs agora estao no `.so` e carregam 200.
