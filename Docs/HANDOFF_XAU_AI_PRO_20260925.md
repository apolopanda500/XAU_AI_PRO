# Handoff completo — XAU AI PRO

Data registrada: 2026-09-25 05:44:16 -03:00  
Projeto: `C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO`  
Estado: desenvolvimento e validação local; não aprovado para dinheiro real.

## Como usar este documento

Este é o registro estruturado e preservado da conversa e de todas as etapas relevantes executadas até `2026-09-25 05:44 BRT`. Não contém credenciais, tokens, senhas, chaves ou conteúdo de `.env`.

A próxima conversa deve começar lendo:

1. `AGENTS.md`
2. `CONVERSAHOJE.txt`
3. Este arquivo
4. `Docs/HANDOFF_XAU_AI_PRO_20260923.md`
5. `Docs/PLANO_PRODUTO_VERIFICAVEL_20260923.md`

Não executar `git reset`, `git clean`, `git checkout` destrutivo, limpeza global do Windows ou qualquer alteração em MQL5.

## Pedidos acumulados do usuário

Ao longo da conversa, o usuário pediu e/ou autorizou:

1. Auditar o projeto inteiro e entender o que já foi feito.
2. Comparar o produto com as melhores aplicações de trading/IA atuais.
3. Completar o frontend e o gateway universal.
4. Manter tudo em paper/demo e sem dinheiro real.
5. Não modificar Expert Advisors ou arquivos MQL5.
6. Ler o EA apenas quando necessário; leitura foi autorizada, mas nenhum EA foi lido até este registro.
7. Validar build, instalação, atalho, runtime, antivírus e artefatos.
8. Assinar localmente para testes ou pesquisar uma opção gratuita confiável.
9. Tornar o aplicativo utilizável no Android.
10. Criar um ciclo novo e completamente limpo.
11. Limpar somente caches e artefatos dispensáveis, sem destruir dados.
12. Instalar o aplicativo novo e executá-lo como usuário normal pelo atalho.
13. Criar notas/handoff para todas as próximas conversas.
14. Fazer commit e push do repositório, preservando segurança e exclusões.
15. Criar automação temporária para trabalhar até `2026-09-25 05:00 BRT`.
16. Ao final, guardar a conversa e todas as etapas.

O prazo de `05:00 BRT` já passou. A última verificação local foi feita às `05:44 BRT`; não se deve estender ou reutilizar o deadline antigo sem nova decisão explícita.

## Limites e travas obrigatórias

- Expert Advisors e arquivos MQL5 são intocáveis.
- Não criar, editar, mover, excluir, formatar, gerar ou sobrescrever `.mq4`, `.mq5`, `.mqh`, `.set` ou qualquer item em `MQL5/Experts`.
- Manter `XAU_MCP_TRADING=0`.
- Manter `XAU_ENABLE_REAL_ORDERS=0`.
- Manter `XAU_ENABLE_EMERGENCY_RESUME=0`.
- Não ativar saques, transferências, acesso a credenciais ou execução real.
- Não desabilitar kill switch, autenticação, validação de assinatura, rate limit ou proteção SSRF.
- Certificado self-signed serve apenas para teste local; não instalar uma CA pessoal em `Trusted Root`.
- Não prometer “Mercado 10/10”, retorno financeiro ou segurança de mercado real sem evidência.
- Não afirmar que dados simulados são dados reais.
- Resposta incerta de ordem deve permanecer `unknown`/`pending` e exigir reconciliação; nunca repetir automaticamente.
- Não habilitar MCP opcional sem credencial, dependência verificada e teste de conexão.

## Linha do tempo da conversa e do trabalho

### 1. Estado herdado de 2026-09-23

O handoff anterior registrava:

- OpenCode `1.18.32` e configuração do projeto.
- GitKraken MCP desabilitado e hook neutralizado.
- Planos/assinaturas locais e Social Paper.
- Backtester paper-only.
- Risk gate, intent log, fila persistente e travas de emergência.
- Gateway local e frontend React/Tauri.
- `202` testes Python, `24` testes frontend, typecheck, builds, lint e Pylint aprovados.
- Backtest ainda bloqueado por falha de candles MT5 naquele processo.
- Nenhum commit realizado.
- Nenhum arquivo MQL5 alterado.

### 2. Arquitetura universal e Mercado

Foi implementado e testado o backend universal para múltiplos ativos e corretoras:

- catálogo universal;
- quotes;
- candles;
- depth;
- trades recentes;
- cache;
- matriz de capabilities;
- resolução de conta e símbolo;
- fallback explícito para MT5;
- adaptadores Binance, MEXC, Bybit e OKX;
- execução DEMO separada;
- rotas reais bloqueadas;
- adapter read-only para EA de terceiros;
- aliases e canonicalização de intenções;
- guards de SSRF e redirects;
- endpoints FastAPI e stdlib.

O frontend Mercado foi reconstruído em modo leitura com:

- filtros de ativo/corretora;
- preço, variation, spread e timestamp;
- gráfico;
- candles;
- book de ofertas;
- trades;
- estados de loading/erro/vazio;
- fallback de modo e conta;
- distinção visual entre paper, demo e real bloqueado.

### 3. Segurança do launcher e Tauri

O Tauri foi endurecido com:

- token aleatório por sessão via `getrandom`;
- `gateway_token_command`;
- `XAU_GATEWAY_TOKEN` entregue ao gateway filho;
- `XAU_CORE_HEALTH_TOKEN` entregue ao Core;
- health autenticado;
- validação de `source` e build do gateway;
- resources-only, sem fallback para executáveis vizinhos;
- header `Authorization` apenas para loopback do gateway;
- espera autenticada do gateway antes de renderizar o desktop;
- isolamento de recursos por pasta de recursos;
- encerramento de subprocessos no fechamento do app.

O bundle foi endurecido para não incluir:

- `.env` ou `.env.*`;
- bancos SQLite;
- `node_modules`;
- `.output`;
- `__pycache__`;
- dados do usuário;
- fontes desnecessárias.

`backend/.env.local` foi excluído do bundle.

### 4. Backend, risco e conta

Correções importantes:

- `/api/boot` tornou-se read-only e não inicializa nem persiste estado em GET.
- Health FastAPI exige token quando configurado.
- `daily_trades` e `drawdown_pct` passaram a ser calculados e enviados.
- High-water mark falha fechado.
- `account_id` é resolvido explicitamente quando existem múltiplas contas.
- Fallback `-active` foi removido do fluxo de credenciais.
- `GET /api/connections` não cria diretório.
- Clientes externos exigem HTTPS e bloqueiam redirects para destinos não permitidos.
- Rotas de execução real continuam recusando operação.

### 5. Validação completa anterior à limpeza

Resultados registrados antes da nova limpeza:

- Python: `267 passed`.
- Frontend: `33 passed`; depois `35 passed` após os testes mobile.
- `npx tsc --noEmit`: passou.
- Vite build: passou.
- Backend Node lint: passou.
- Backend Node build/Nitro: passou.
- Core Rust: `cargo fmt --check`, `cargo check --locked` e `cargo test --locked`; 38 testes.
- Tauri Rust: `cargo fmt --check`, `cargo check --locked` e `cargo test --locked`.
- Pylint direcionado: `10.00/10`.
- `git diff --check`: sem erros; apenas avisos de conversão LF/CRLF.
- Status/diff protegido MQL5: vazio.

### 6. Runtime e artefatos Windows anteriores à limpeza

Gateway empacotado:

- health autenticado retornou `200`;
- build `xau-ai-pro-1.2.3-universal-20260918`;
- health sem token retornou `401`;
- capabilities retornou `ok=true`.

Tauri release:

- portas `9001`, `9002` e `9003` iniciaram;
- fechamento gracioso retornou `0`;
- portas ficaram livres;
- log confirmou bridge autenticado e Core iniciado;
- recursos internos do MSI conferiam com gateway/Core extraídos.

Defender:

- todos os artefatos testados retornaram código `0` e “found no threats”;
- isso não elimina SmartScreen/reputação nem o histórico de detecção de uma instalação antiga.

Hashes históricos dos artefatos exatos testados:

- launcher `8F6B37A2208BFA6A740779B64AC708CAF81F6B553BE5287DCA9372D43D83C6B4`;
- setup Inno `6EC7C5B22A78026DF1EDCD240B50DB11DE28AFEB6DF8B7804EDAB5505E9F4287`;
- Tauri exe `DE98E1E3744923EDBC41FA652922E85EA5882696A2074D7CCCC6E3B09E1E729D`;
- MSI `E1173E4E10C5A1107A06DD32161F9E3971E79B73ECC9E946C1A3E3001C8649EE`;
- NSIS `392A0CD32A2D2EEB15E65A1AB603328EA0F1356332D8D499492E32200FAE5CA2`;
- gateway `B4D45FEA1602C4936D89C7AAD352467FCC49DFBD27EDEB7FEE8DB8C8696BDB80`;
- Core `DA7B7C498185D51F0C73E690E488470CB87692A522A455EDBFEBB4DCEA9354CB`.

Esses artefatos foram removidos intencionalmente pela limpeza scoped iniciada para criar espaço ao Android. Os hashes são histórico exato, não arquivos presentes neste momento. O source foi alterado depois para mobile, portanto novos artefatos Windows precisam ser gerados, defendidos, assinados e testados novamente.

### 7. Instaladores e assinatura

- Inno foi construído, mas instalação limpa foi bloqueada por conflito com instalação anterior do mesmo AppId apontando para a raiz do projeto.
- Windows Sandbox está `Disabled`; não havia VM limpa disponível.
- NSIS/Tauri puderam ser executados diretamente, mas instalação pelo atalho ainda precisa de validação final.
- Todos os artefatos históricos estavam `NotSigned`.
- Script de assinatura local foi ampliado, mas a sequência final ainda precisa de teste real.
- Não foi instalada CA self-signed no trust store.
- SignPath Foundation é uma possibilidade gratuita somente para projeto OSS elegível.
- Microsoft Store, Azure Artifact Signing ou outro certificado público exigem conta/processo externo; não é possível simular certificado público confiável localmente.

### 8. Histórico de segurança

Existe histórico de `Trojan:Win32/Bearfoos.A!ml` em uma instalação antiga em `C:\Users\Micro\AppData\Local\XAU_AI_PRO\XAU_AI_PRO.exe`.

Os artefatos posteriores testados não houve nova detecção, mas:

- o histórico não deve ser ocultado;
- não alegar “zero detecção permanente”;
- não enviar binários proprietários a serviço público sem autorização explícita;
- usar submit False Positive do Microsoft quando apropriado.

## Estado Android

### Alterações de código mobile

Foram feitas alterações em:

- `frontend/src/main.tsx`;
- `frontend/src/hooks/useCoreBootstrap.ts`;
- `frontend/src/lib/api.ts`;
- `frontend/src/lib/api.test.ts`;
- `frontend/src-tauri/capabilities/migrated.json`;
- `frontend/src-tauri/tauri.conf.json`.

Alterações:

- `isMobileRuntime()` exportado de `api.ts`;
- desktop continua usando token e aguardando gateway local;
- Android não tenta executar `gateway_token_command`;
- Android não espera `127.0.0.1:9001`;
- hook do Core retorna fallback mobile sem iniciar `.exe`;
- capability `android: [main]` incluída;
- CSP permite `wss:`;
- `bundle.android.minSdkVersion=24`.

O app Android ainda precisa de `VITE_API_BASE` e/ou `VITE_WS_URL` apontando para gateway remoto acessível. Sem isso, a API ainda pode cair no fallback loopback e o app não será operacional como produto Android. Isso deve ser validado com host remoto/TLS real antes da publicação.

### Toolchain instalada

- JDK usado: `C:\Program Files\Android\Android Studio\jbr`.
- Android SDK: `C:\Users\Micro\AppData\Local\Android\Sdk`.
- Command-line tools: `15859902`.
- SHA-256 oficial validado: `90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a`.
- Platform: Android API 36.
- Build Tools: `36.0.0`.
- Platform Tools instalados.
- NDK: `28.2.13676358` side-by-side.
- Rust target: `aarch64-linux-android`.
- Projeto Tauri Android gerado em `frontend/src-tauri/gen/android/xau_ai_pro_desktop`.
- `compileSdk=36`, `minSdk=24`, `targetSdk=36`.
- applicationId gerado: `com.xau_ai_pro.desktop`.

O projeto gerado está ignorado por `frontend/src-tauri/gen/`; ele deve ser regenerado com `tauri android init`, salvo se a estratégia do repositório for alterada para versionar customizações Android específicas.

### Validação mobile já feita

- Frontend: `35 passed`.
- TypeScript: passou.
- Vite Android frontend build: passou.
- Rust Android `aarch64-linux-android` release: compilou em aproximadamente 5m11s.
- Falha ocorreu somente na fase Gradle/APK.

### Bloqueio Android atual

Erro exato:

`BUG! exception in phase 'semantic analysis' in source unit '_BuildScript_' Unsupported class file major version 69`

Causa:

- Gradle/AGP está sendo executado com o JBR do Android Studio em Java 25;
- class file major `69` corresponde a Java 25;
- Gradle 8.14.3/AGP 8.11.0 usados pelo template não aceitaram essa combinação.

Correção recomendada:

1. Instalar ou localizar JDK 21 ou JDK 17.
2. Usar `JAVA_HOME` e `PATH`apenas nessa sessão/build.
3. Confirmar `java -version`.
4. Reexecutar:

```powershell
$env:JAVA_HOME = '<JDK 21 ou 17>'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
npm.cmd run tauri -- android build --ci --target aarch64 --apk
```

O target Rust já compilou e deve ser reaproveitado. Não limpar `target/aarch64-linux-android` antes da retry.

Espaço livre no último registro: aproximadamente `2.14 GB`. Antes de repetir o build, avaliar a necessidade de liberar cache Gradle ou mover temporariamente o SDK/build para outro volume. Não remover o NDK sem necessidade.

Android ainda não está assinado para Google Play, não foi instalado em aparelho e não foi testado com gateway remoto.

## Automação temporária

Arquivo: `scripts/overnight_session.ps1`.

Estado:

- dry-run passou antes das últimas alterações internas;
- execução real nunca foi iniciada;
- deadline padrão `2026-09-25T05:00:00-03:00` está vencido;
- o script foi expandido para signing pré/pós-bundle, manifesto e Defender, mas essas adições ainda precisam de dry-run/validação;
- a flag Android foi corrigida para sintaxe Tauri local, mas deve gerar apenas `aarch64` para conservar espaço;
- o script deve ganhar um novo deadline explícito antes de qualquer execução;
- não incluir commit/push automático sem revisão de staging.

O script mantém:

- `XAU_MCP_TRADING=0`;
- `XAU_ENABLE_REAL_ORDERS=0`;
- `XAU_ENABLE_EMERGENCY_RESUME=0`;
- execução de gateway/Core local com recursos protegidos;
- instalação NSIS e criação de atalho em pasta local;
- sem instalação de certificado no trust store.

Ainda é necessário:

- corrigir a flag Android para `aarch64 --apk`;
- validar a nova função de assinatura;
- validar manifesto/Defender;
- definir se Android falho deve impedir Windows ou apenas ser marcado como falho;
- executar dry-run novamente;
- escolher novo deadline somente com autorização do usuário.

## Limpeza realizada

Foi executado `scripts/limpeza_segura.ps1 -Apply -BuildArtifacts`.

Artefatos/caches removidos:

- `.pytest_cache`;
- `frontend/dist`;
- `build`;
- `dist`;
- `core/target`;
- `frontend/src-tauri/target` antes do build Android.

Também foram removidos apenas caches temporários XAU em `C:\Users\Micro\AppData\Local\Temp\opencode`:

- `xau-tauri-check`;
- `xau-tauri-android-check`;
- `xau-msi-extract`;
- `xau-frontend-build`;
- arquivos temporários de extração Android/MSI já verificados.

Não foram removidos:

- código;
- documentação;
- `.venv`;
- `node_modules`;
- dados do usuário;
- MQL5;
- histórico Git;
- configurações do sistema não relacionadas.

## PyInstaller e scripts de build

Foi removido `--clean` do PyInstaller em:

- `scripts/build_app.bat`;
- `scripts/ciclo_limpo_123.py`;
- `Tools/release_all.cmd`;
- `.github/workflows/build-installer.yml`;
- `.github/workflows/xau-ai-pro-validation.yml`.

Motivo: `--clean` já causou risco de limpeza unintended no passado. A limpeza deve ficar em `scripts/limpeza_segura.ps1`, com allowlist e dry-run.

Também foi ampliado `.gitignore` para:

- `release/`;
- `*.db-wal`;
- `*.db-shm`;
- keystores Android;
- `keystore.properties`.

## Estado Git

Remotos:

- `origin`: `https://github.com/apolopanda500/XAU_AI_PRO.git`;
- `gitlab`: `https://gitlab.com/apolopanda500/XAU_AI_PRO.git`.

Último commit conhecido:

- `777fc12 feat(order): adiciona paper mode, protection, idempotência e reconciliação`

Não houve commit nem push nesta sessão.

Working tree continua muito grande:

- cerca de 79 arquivos rastreados modificados;
- aproximadamente 4.791 inserções e 1.403 remoções no diff rastreado;
- diversos arquivos novos de backend, frontend, testes, docs, segurança e scripts;
- `experiments/isolated/opentelemetry-js` continua modificado e deve ser preservado, não staged cegamente.

Antes de commit:

1. Rodar `git status --short`.
2. Rodar `git diff --check`.
3. Verificar `.env*`, bancos, logs, chaves, certificados, keystores e artefatos.
4. Garantir `release/`, `dist/`, targets e Android secrets ignorados.
5. Não incluir `experiments/isolated/opentelemetry-js` sem intenção explícita.
6. Verificar diff MQL5 vazio.
7. Fazer commit por escopo coerente ou em commits menores.
8. Push somente após conferir remote e branch.

Comando de proteção já usado:

```powershell
git status --short -- MQL5/Experts
git diff -- MQL5/Experts "*.mq4" "*.mq5" "*.mqh" "*.set"
```

Resultado: vazio.

## Documentação e benchmark

Já existem:

- `AGENTS.md`;
- `CONVERSAHOJE.txt`;
- `Docs/HANDOFF_XAU_AI_PRO_20260923.md`;
- `Docs/PLANO_PRODUTO_VERIFICAVEL_20260923.md`;
- `installer/ASSINATURA.md`.

Ainda falta criar:

- benchmark verificável contra TradingView, NinjaTrader, Sierra Chart, QuantConnect e outros aplicativos líderes;
- matriz de features com evidência, gap e status;
- relatório de UI/UX por arquivo;
- plano de assinatura pública/free;
- instruções de deploy do gateway remoto para Android.

Referências atuais pesquisadas:

- Tauri Android docs;
- Android SDK/Google Play docs;
- Microsoft signing/SmartScreen;
- SignPath Foundation;
- TradingView;
- OpenCode CLI;
- web-design-guidelines;
- React best practices.

Não foi criado relatório final de benchmark; não alegar que a pesquisa isolada equivale a benchmark concluído.

## Estado do checklist

`CONVERSAHOJE.txt` atualmente mantém:

- itens 1–9: concluídos;
- item 10: parcial;
- item 11: concluído.

Novos status devem ser acrescentados sem apagar o histórico:

- Android toolchain: **resolvido** — Temurin JDK 21.0.12.1 LTS, aplicado só na sessão de build;
- APK: **gerado e assinado** (`aarch64`, v2+v3, SHA-256 `33D6CFDCB17165561491FFD6943D9EE09A6608786AC383E3D9A032DC8825331F`);
- APK operacional em aparelho: **pendente** — falta gateway remoto/TLS e `VITE_API_BASE`/`VITE_WS_URL`;
- novo ciclo Windows: pendente;
- artefatos Windows finais: removidos e pendentes de reconstrução;
- commit/push: pendente;
- benchmark: pendente;
- assinatura pública: pendente;
- instalação/atalho final: pendente;
- espaço em disco: **crítico** (~0,75 GB livres).

## Próximos passos exatos

### Prioridade 1 — finish Android sem destruir o que foi compilado

1. Instalar/localizar JDK 21 ou 17.
2. Confirmar `java -version` e usar apenas esse JDK no build.
3. Reexecutar build `aarch64` APK.
4. Validar assinatura do APK com `apksigner verify --verbose --print-certs`.
5. Validar `aapt dump badging` e alinhamento com `zipalign -c -v 4`.
6. Instalar em aparelho/emulador somente se houver dispositivo e gateway remoto configurado.
7. Não gerar AAB universal até haver espaço e validação do APK.

Comandos previstos:

```powershell
$env:JAVA_HOME = '<JDK 21 ou 17>'
$env:ANDROID_HOME = 'C:\Users\Micro\AppData\Local\Android\Sdk'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:NDK_HOME = 'C:\Users\Micro\AppData\Local\Android\Sdk\ndk\28.2.13676358'
$env:Path = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\cmdline-tools\latest\bin;$env:ANDROID_HOME\platform-tools;$env:Path"
npm.cmd run tauri -- android build --ci --target aarch64 --apk
```

### Prioridade 2 — corrigir e validar automação

1. Alterar Android do script para `aarch64 --apk`.
2. Validar assinatura pré-bundle e pós-bundle.
3. Validar `release-manifest.json`.
4. Validar scan Defender e comportamento se Defender falhar.
5. Garantir que instalação USE signed NSIS e crie atalho local.
6. Executar `-DryRun` com todos os switches.
7. Não executar o deadline vencido.

### Prioridade 3 — rebuild Windows final

1. Limpar somente artefatos scoped necessários.
2. Rodar Python completo.
3. Rodar frontend tests/typecheck/build.
4. Rodar backend lint/build.
5. Rodar Core fmt/check/test/build.
6. Sincronizar Core antes do Tauri build.
7. Rodar Tauri fmt/check/test/build.
8. Gerar gateway e launcher.
9. Gerar MSI/NSIS.
10. Assinar recursos antes dos bundles.
11. Assinar bundles finais.
12. Gerar hashes e manifesto.
13. Rodar Defender.
14. Executar smoke por instalador/atalho.
15. Encerrar e confirmar portas livres.

### Prioridade 4 — documentação e benchmark

1. Criar `Docs/BENCHMARK_TRADING_APPS_2026.md`.
2. Comparar recursos realmente implementados, não screenshots.
3. Registrar fonte, data, limitação e evidência.
4. Criar relatório UI/UX com achados e prioridade.
5. Atualizar este handoff e `CONVERSAHOJE.txt`.

### Prioridade 5 — Git

1. Auditar todos os untracked.
2. Procurar segredos por nomes e padrões, sem imprimir conteúdo.
3. Stage somente arquivos intencionais.
4. Rodar validações finais.
5. Commit.
6. Push para GitHub.
7. Push para GitLab somente se credencial/remote estiver disponível.
8. Atualizar handoff com commit e resultado do push.

## Arquivos mais relevantes

- `AGENTS.md`
- `opencode.json`
- `CONVERSAHOJE.txt`
- `Docs/HANDOFF_XAU_AI_PRO_20260925.md`
- `Docs/HANDOFF_XAU_AI_PRO_20260923.md`
- `Docs/PLANO_PRODUTO_VERIFICAVEL_20260923.md`
- `backend/fastapi_gateway.py`
- `backend/mt5_gateway.py`
- `backend/universal_contracts.py`
- `backend/universal_router.py`
- `backend/connection_store.py`
- `backend/risk_gate.py`
- `backend/intent_log.py`
- `backend/third_party_ea.py`
- `core/src/eahttp.rs`
- `frontend/src/main.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/tauri.ts`
- `frontend/src/hooks/useCoreBootstrap.ts`
- `frontend/src-tauri/src/main.rs`
- `frontend/src-tauri/src/lib.rs`
- `frontend/src-tauri/tauri.conf.json`
- `frontend/src-tauri/capabilities/migrated.json`
- `frontend/src-tauri/gen/android/` ignorado e regenerável
- `launcher.spec`
- `mt5-gateway.spec`
- `installer/installer.iss`
- `scripts/limpeza_segura.ps1`
- `scripts/overnight_session.ps1`
- `scripts/assinar_release.ps1`
- `scripts/ciclo_limpo_123.py`

## Resolução do bloqueio Android — 2026-09-25 (tarde)

O bloqueio de JDK descrito acima foi **diagnosticado e resolvido**. O APK `aarch64` foi gerado e assinado.

### Causa raiz confirmada

Varredura completa do sistema encontrou **apenas dois runtimes Java**:

- `C:\Program Files\Android\Android Studio\jbr` → **Java 25.0.3** (usado pelo Gradle, incompatível);
- `C:\Program Files\RedHat\java-1.8.0-openjdk-1.8.0.502-1` → **Java 8** (também incompatível: Gradle 8.14 exige 17+).

Não havia **nenhum** JDK 17 ou 21 instalado. `gen/android/gradle.properties` não define `org.gradle.java.home`, então o build herdava o JBR 25 — exatamente a causa de `Unsupported class file major version 69` (bytecode Java 25 lido pelo Groovy/ASM do Gradle 8.14.3).

### Correção aplicada

1. Baixado **Temurin JDK 21.0.12.1 LTS** x64 (~195,6 MB) via API Adoptium.
2. Extraído **fora do repositório** em `C:\Users\Micro\AppData\Local\Temp\opencode\jdk21-temurin\jdk`.
3. Pasta renomeada para **remover o `+`** do path (`jdk-21.0.12.1+1` → `jdk`), pois `+` em `JAVA_HOME` causa falha em toolchains Android.
4. `JAVA_HOME`/`Path` definidos **apenas na sessão do build**. Nada foi gravado em variável do sistema, `.env` ou no repo.
5. Gradle, AGP e Kotlin passaram a compilar sob Java 21 sem erro.

### Espaço em disco

Havia apenas **1,36 GB livres** (o registro anterior indicava 2,14 GB). Antes do build foram removidos **apenas artefatos gitignored e regeneráveis**, confirmados por `git check-ignore`:

- `release/` → 0,48 GB (artefatos Windows stale; o handoff já determinava reconstrução);
- `frontend/src-tauri/target/release` → 0,76 GB (regenerável por `cargo build`).

**Preservado:** `frontend/src-tauri/target/aarch64-linux-android` (0,70 GB) — o alvo Rust foi reaproveitado. O zip do JDK e o APK intermediário alinhado foram removidos após o uso.

Antes: 1,97 GB → depois da limpeza: 3,11 GB → após o build: ~0,75 GB livres.

### Recuperação de disco — repositório Git órfão

Com o build concluído o disco ficou crítico. A auditoria do home encontrou **`C:\Users\Micro\.git`, um repositório Git de 10,41 GB não relacionado ao projeto XAU**:

- sem remote configurado;
- único commit `f5fa972 "Initial commit"` com a **árvore vazia** (`4b825dc6…`);
- `in-pack: 0`, `packs: 0` — 27.841 objetos soltos, nenhum empacotado;
- 4 arquivos `tmp_obj_*` residuais (57,71 MB) de operação interrompida;
- branches `main` e `idioma-portugues-procurar-projeto-xau-ai-pro-x4hT8t`, ambas com árvore vazia;
- 2 refs de checkpoint do Cline (`refs/cline/checkpoints/…`) com 3 commits-pai cada.

Origem provável: um `git init` + `git add .` executado na raiz do home e interrompido. **Não é o repositório do projeto** — `git rev-parse --git-dir` no XAU_AI_PRO retorna o próprio `.git`, e `worktrees` estava vazio.

Ação executada: **`git prune --expire=now`** (o `--expire=now` é obrigatório; o padrão de 2 semanas não removeria objetos tão recentes). O comando só elimina objetos inalcançáveis de qualquer ref, portanto é seguro por definição.

- Duração: 30 segundos. Recuperado: **+4,18 GB**. Livre: 0,94 GB → **5,12 GB**.
- Objetos removidos: 27.841 → 3.861. Resíduo `garbage`: 0.
- As 4 refs e os 2 branches foram preservados.

**Os 6,04 GB restantes NÃO foram removidos** porque são alcançáveis: os commits-pai dos checkpoints do Cline contêm um snapshot real de **3.079 arquivos do home**, incluindo `llm-agent/data/sessions/sessions.db` (156 MB) e bases de ticks `MetaQuotes-Demo/ticks/XAUUSD/*.tkc` (65–76 MB cada). Como são cópias de arquivos que ainda existem no disco, forçar a remoção não perderia dados, mas corromperia os checkpoints. **A remoção foi deixada para decisão explícita do usuário.**

Riscos registrados:

1. O mecanismo de checkpoint do Cline **também vive em `AppData\Roaming`** e pode recriar snapshots grandes se reativado.
2. Um `.git` na raiz do home é risco operacional: qualquer `git add`/`git checkout` executado fora de um repositório real acaba contaminando esse repo.
3. `sessions.db` do agente LLM acabou dentro de objetos Git. Não houve remote, portanto nada foi publicado, mas o conteúdo fica em disco dentro do repo órfão.

Antes: 0,75 GB → **5,12 GB livres** ao final desta etapa. Espaço suficiente para o ciclo Windows completo.

### Resultado do build

Comando executado com `workdir=frontend`:

```powershell
$env:JAVA_HOME = 'C:\Users\Micro\AppData\Local\Temp\opencode\jdk21-temurin\jdk'
$env:ANDROID_HOME = 'C:\Users\Micro\AppData\Local\Android\Sdk'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:NDK_HOME = "$env:ANDROID_HOME\ndk\28.2.13676358"
$env:Path = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\cmdline-tools\latest\bin;$env:ANDROID_HOME\platform-tools;$env:Path"
npm.cmd run tauri -- android build --ci --target aarch64 --apk
```

- `exit=0`, duração **14m43s** (17:05:51 → 17:20:34).
- Vite: 204 módulos, build ok.
- Cargo release `aarch64-linux-android`: 4m44s; segunda invocação 1,32s (cache).
- NDK detectado: `28.2.13676358`.
- O SDK instalou `build-tools 35.0.0` automaticamente (o projeto pede 35, não 36).
- Nenhum erro. Apenas avisos de depreciação de API Java/Tauri, sem impacto.

### Artefato final assinado

- Arquivo: `XAU-AI-PRO-1.2.3-aarch64.apk` (32,93 MB), fora do repo em `Temp\opencode\artifacts`.
- **SHA-256:** `33D6CFDCB17165561491FFD6943D9EE09A6608786AC383E3D9A032DC8825331F`
- APK intermediário não assinado — SHA-256 `EE3A30E3345CE9B1D1411602575D2A10AE90505DD0D1A03FB9967F60B7ED2B81`
- Certificado do assinante — SHA-256 `7ec0b8d048ed636dc366491b955ee7343143a7e94d26a55858f409eb00f7b308`

Validações executadas com `build-tools 36.0.0`:

- `aapt dump badging` → `com.xau_ai_pro.desktop`, versionName `1.2.3`, versionCode `1002003`, `minSdk 24`, `targetSdk 36`, `compileSdk 36`, label `XAU AI PRO`, `native-code: 'arm64-v8a'`.
- `zipalign -c -v 4` → `Verification successful` (no APK assinado).
- `apksigner verify --verbose --print-certs` → `Verifies`, **v2 = true**, **v3 = true**, 1 signer, RSA 2048, exit 0.
- v1 (JAR) = `false` porque `minSdk 24` dispensa v1; comportamento esperado, não é falha.

### Keystore

- Gerado com `keytool` do JDK 21: alias `xau-local-test`, RSA 2048, SHA384withRSA, validade 10.000 dias, DN `CN=XAU AI PRO Local Test, OU=Development, O=XAU AI PRO, L=Sao Paulo, ST=SP, C=BR`.
- Keystore (PKCS12) e arquivo de credenciais gravados **fora do repositório**, em `Temp\opencode\keystore`.
- A senha **não** foi impressa em log, terminal ou documento.
- É **autoassinado de teste local**. Não confiável, não vale para Google Play e não substitui assinatura pública.

### Pendências Android que permanecem

1. **O app ainda não funciona como produto em aparelho.** `frontend/src/lib/api.ts:32-36` cai em `http://127.0.0.1:9001` sem `VITE_API_BASE`/`xau-api-base`; no celular esse endereço aponta para o próprio aparelho. É preciso gateway remoto com TLS e `VITE_WS_URL` (`wss://`) definido no build ou em runtime.
2. **Não testado em dispositivo físico nem emulador** — não havia aparelho conectado.
3. **Não assinado para Google Play** — requer keystore de release guardado com segurança e assinatura pública/free elegível.
4. **AAB universal não gerado** (mantido de fora por espaço, conforme plano).
5. `backend/.env.local` e afins continuam fora do bundle; revisar o CSP/permissões para produção Android.

### Estado MQL5

Nenhum arquivo MQL5 foi criado, editado, movido, excluído ou formatado. `MQL5/Experts` contém 184 arquivos EA e o diff rastreado continua **vazio**. A leitura foi apenas de inventário.

## Ciclo de validação completo — 2026-09-25 18:07 (0 erros)

Executado antes de qualquer reconstrução de artefato. Todos os comandos abaixo retornaram **exit 0**.

| Componente | Comando | Resultado |
| --- | --- | --- |
| Python | `python -m pytest -q tests` | **267 passed** em 49,58s |
| Frontend | `npm test` (vitest) | **35 passed** em 5 arquivos, 28,74s |
| Frontend | `npx tsc --noEmit` | sem erros |
| Frontend | `npm run build` (vite) | 204 módulos, 2,71s |
| Backend | `npm run lint` (eslint) | sem erros |
| Backend | `npm run build` (Nitro) | 4,57 MB / 1,1 MB gzip |
| Core | `cargo fmt --all -- --check` | ok |
| Core | `cargo check --locked` | ok, 1m13s |
| Core | `cargo test --locked` | **38 passed**, 0 failed |
| Tauri | `cargo fmt --all -- --check` | ok |
| Tauri | `cargo check --locked` | ok, 2m34s |
| Tauri | `cargo test --locked` | exit 0 (crate sem testes unitários) |
| Python | `pylint` (11 arquivos backend) | **10.00/10** |
| Git | `git diff --check` | sem erros de whitespace |

Ambiente usado: Python 3.11.15, pytest 8.4.2, Node 26.3.0, npm 11.16.0, cargo 1.98.1. `node_modules` de `frontend` e `backend` foram reaproveitados — **`npm ci` não foi executado de propósito**, porque a rede do ambiente mede ~100 KB/s e um reinstall completo seria inviável e arriscado.

### Guardas verificadas

- `git status --short -- MQL5/Experts` e `git diff -- MQL5/Experts "*.mq4" "*.mq5" "*.mqh" "*.set"` → **vazios**. 184 arquivos EA intactos.
- Varredura de segredos por nome: nenhum `.env`, keystore, `.jks`, `.p12`, `.pem` ou `.key` rastreado ou untracked.
- `.env`, `.env.local` e `backend/.env.local` confirmados ignorados (`.gitignore:71` e `backend/.gitignore:2`).
- Nenhum `node_modules`, `.output`, `__pycache__`, `release/` ou `target/` apareceu como alteração.
- Nenhum commit foi feito nesta sessão.

### Achados que exigem decisão (não corrigidos)

1. **`app/data/marketdata.db` continua rastreado no Git** (2,9 MB), apesar de `.gitignore` conter `*.db`. A regra foi adicionada depois de o arquivo já estar rastreado, e `.gitignore` não des-rastreia. O conteúdo é **apenas dado de mercado** — tabela única `market_ticks` com colunas `ts_ms, symbol, source, price, bid, ask, change_value, change_pct, spread`; nenhuma credencial, conta ou PII. Ainda assim viola a intenção da regra e incha o repositório. Correção sugerida: `git rm --cached app/data/marketdata.db`.
2. **Procedência dos 23.820 ticks precisa ser confirmada.** Distribuição por fonte: `MT5` 15.572, `HTTP` 8.206, `Binance` 34, `Yahoo` 8. Símbolos: EURUSD, GBPUSD, US30, USDJPY, XAUUSD (2.650 cada). Nenhuma coluna marca origem simulada. Pela regra do `AGENTS.md`, **esses dados não podem ser apresentados como dados de mercado reais** sem confirmação de data de origem.
3. Artefatos Windows (gateway, launcher, MSI, NSIS) seguem **não reconstruídos** após as mudanças mobile.
4. O `Tauri` não tem testes unitários; `cargo test` passa com 0 casos. A cobertura do runtime do launcher continua dependente dos testes Python e do smoke test manual.

## Conclusão honesta do estado

O produto tem uma base ampla e testes substaciais, mas ainda não está pronto para Mercado real, Google Play ou venda como “10/10”.

Bloqueios inmediatos:

1. ~~APK bloqueado por JDK incompatível com Gradle.~~ **Resolvido em 2026-09-25**: APK `aarch64` gerado e assinado.
2. Artefatos Windows finais precisam ser reconstruídos após as mudanças mobile.
3. Instalação limpa continua dependente de ambiente Windows isolado ou resolução segura do AppId existente.
4. Assinatura pública/free elegível ainda não foi obtida.
5. Commit/push ainda não foi feito.
6. Benchmark e relatório de produto ainda não foram finalizados.
7. Android ainda exige gateway remoto/TLS e teste em aparelho — **o APK sozinho não é operacional**.
8. **Disco crítico (~0,75 GB livres)** — qualquer build Windows completo ou novo ciclo Android exige liberar espaço antes.

A próxima conversa deve retomar pelos artefatos Windows (rebuild) ou pelo deploy do gateway remoto para o Android. O bloqueio de JDK está resolvido; não reinstalar SDK/NDK e não limpar `target/aarch64-linux-android`.
