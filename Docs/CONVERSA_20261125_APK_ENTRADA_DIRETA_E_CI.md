# 25/11/2026 — APK entra direto no app, CI do Android e estado medido

Regra de leitura: o comando vence qualquer número escrito aqui.

## 1. O que mudou

### Entrada direta no APK

- `frontend/src/components/auth/UserSessionGate.tsx`: em mobile e desktop
  devolve o app direto. `LoginScreen`, `FirstRunWizard` e
  `MobileBiometricLock` nao sao usados no gate.
- `frontend/src/components/MT5AccountsPanel.tsx`: unico passo deixado para o
  operador — sincronizar a conta MT5 aberta no PC. Usa `lib/connections`
  (`detectTerminal`, `saveExchange`, `connectionAction`), as mesmas rotas do
  `ConnectionSettings`: `/api/status`, `/api/connections`. Nao pede senha.
- `frontend/src/components/SettingsCore.tsx`: bloco morto do
  `/api/mt5/auto-login` (404 no gateway 9027) substituido pelo painel acima.
- `frontend/src/components/MobileCommandCenter.tsx` e o teste removidos:
  componente orfa, rotas `/api/mobile/command` e `/api/mobile/control` nao
  existem no gateway.
- `frontend/src-tauri/tauri.conf.json`: `resources: []` — os recursos
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
do commit `487ee916`; a correcao acima cobre os quatro.

### Testes Python que so falham no CI (diagnosticado, pendente)

Os 5 testes `test_ai_inference.py` reprovados nos workflows `ci`,
`Validacao e Empacotamento` e `XAU AI PRO - validacao universal` exigem
artefatos `MULTI_*` treinados, que nao vao no git. Executados localmente nos
mesmos nos: **8 passed** — o checkout do runner e que nao tem o catalogo. A
suite ja tem `skipif` por ausencia de catalogo para outras classes; estes 5
ficaram de fora e precisam do mesmo guard.

### Outras correcoes da suite

- `tests/test_risk_gate.py`: caso negativo agora usa `spread: 401`, alinhado a
  decisao do dono de 23/11 (`max_spread=400`).
- `frontend/src/components/RobotTabs.test.tsx`: 1 montagem de grafico so na
  aba Operacao, 0 nas demais (decisao `8ee8a00e`).
- `backend/{binance,bybit,mexc,okx}_execution.py`: `stop_loss`/`take_profit`
  aceitos e ignorados onde a corretora nao suporta, conforme o contrato do
  router universal. O MT5 aplica.
- `mt5-gateway.spec`: `hiddenimports` dos 7 modulos antes ausentes no bundle.
- `.gitignore`: `*.bak_*` ignorado — backup que a suite gera antes de
  reescrever modelos nao pode entrar no git.

## 2. Numeros medidos

| Medicao | Resultado |
|---|---|
| `npx tsc --noEmit` (pos-rebase, npm 2.12.x) | **OK**, 0 erros |
| `npx vitest run` (antes dos bumps) | **1064 passed** |
| Suite Python completa | **1630 passed, 2 skipped, 9 warnings** em 541,62s |
| Artefato/spec (`test_bundle_gateway_artefato.py`, `test_spec_gateway.py`, `test_artefato_congelado.py`) | **27 passed** em 31,18s |
| `scripts/sync_version.py --check` | **Todos alinhados**, versao `1.2.191` |
| PyInstaller rebuild | **exit 0**; `mt5-gateway.exe` 28.949.497 bytes |
| Hash do bundle (`dist` vs `frontend/src-tauri/bridge`) | **SHA256 identicos** |
| Tunel com token (`/api/health`, `/api/status`, `/api/connections`) | **HTTP 200 nas 3**; sem token, **401** |
| Limpeza Windows (`limpeza_segura.ps1 -Apply -DebugCache`) | 2 passagens; 1o removeu `frontend/src-tauri/NONE`; 2o "Nenhum temporario" |
| Disco C: apos limpeza | **1,98 GB livres** |

## 3. Estado do terminal medido (ninguem foi desligado)

- `MetaEditor64.exe` PID `13116`, desde 24/11 19:26:37.
- `metatester64.exe` PID `7604`, desde 25/11 00:39:02 — backtest ativo.
- `terminal64.exe` PID `4256`, desde 25/11 00:43:41.
- Gateway: PID `7396`, `127.0.0.1:9027`, build
  `xau-ai-pro-1.2.191-universal-20261113`. Nenhuma destas sessoes foi
  encerrada por esta sessao.
- Celular fisico conectado: `R9XY1016R6V` (`SM_A057M`). O emulador
  `emulator-5554` nao aparece mais na lista atual do `adb devices`.

## 4. O que ainda NAO foi feito

- Baixar o APK do run `45545644746`, instalar no celular e varrer as telas.
  O APK antigo de 386 MB abria tela preta; só o artefato do CI conta.
- Confirmar na tela que nao aparece login/URL/conta do app e que so falta
  vincular a conta MT5 — inclusive checar se o `AuthGate` (PIN de
  `auth.json`) trava em instalacao limpa.
- Deploy final do `.ex5` e atualizacao de modelos/backtest: as equipes alfa e
  delta encerraram com `Free usage limit reached` e precisam ser feitas
  manualmente. Nenhum parametro de risco foi alterado.
- Publicacao no MQL5 CodeBase: **nao autorizada**.

## 5. Cuidados para o proximo ciclo

- Quick tunnel e temporario: se o `cloudflared` reiniciar e trocar a URL, o
  APK tem de ser reconstruido com o novo `VITE_API_BASE`.
- Nao publicar tokens, DSNs ou conteudo de `.env` em log/commit/resposta.
- Nao fechar `terminal64.exe` nem `metatester64.exe` enquanto o backtest roda.
- Antes de `git status` travar: `limpeza_segura.ps1 -Apply -DebugCache`, sem
  `-BuildArtifacts` com build no ar.
