# ANDROID_QA_PROVADO_2026-11-18

Data: 2026-11-18 (sessão de correção em worktree limpa)
Worktree: `MQL5/Files/Temp/upgrade_10_10_wt`
Branch: `feat/upgrade-10-10` (base `813996f3`, alterações locais não commitadas no momento deste relatório)
Escopo: Fases 1–4 (Mobile Pro / v1.2.182 prep) sem tocar em `.ex5` de produção, tokens, inputs de risco ou gateway/produção.

## Guardas preservadas
- `.ex5` canônico de produção preservado: MD5 `844081BF2D51D6A4072B150C3DDC6EBD` (`Experts/XAU_AI_PRO/XAU_AI_PRO.ex5`).
- Sem rotação de `XAU_GATEWAY_TOKEN`; sem alteração de `withdrawals_enabled`/inputs de risco; sem commit/push automático.

## Fase 1 — Ruído visual e conectividade mobile
- **CORE MÁQUINA (Sistema)**: `frontend/src/components/SystemHealthOnly.tsx` detecta runtime mobile e exibe telemetria limpa (`Modo Mobile Ativo · Latência Gateway XX ms`), sem invocar telemetria WMI/PowerShell local do PC no cliente Android e sem erro laranja contraditório.
- **WS após login**: `frontend/src/hooks/useMarketWebSocket.ts` passa a anexar `token=<sessionToken>` na URL do WebSocket quando há sessão autenticada, permitindo handshake autenticado em endpoint compatível e refletindo estado real da conexão.
- **Painel mobile /auth**: `frontend/src/components/MobileCommandCenter.tsx` envia `Authorization: Bearer <sessionToken()>` em `GET /api/mobile/control`.
- **Configurações > Segurança (overlap)**: `frontend/src/theme/settings.css` desativa `position: sticky` do menu lateral em layout empilhado (`@media max-width: 860px`) para evitar sobreposição.
- **Rótulo Operações**: navegação/sub-abas existentes preservadas com semântica correta; adicionada navegação inferior móvel (`MobileBottomNav`) com rótulos claros para uso no celular.

## Fase 2 — Estados inteligentes e modelos remotos
- **Calendário econômico vazio**: `frontend/src/hooks/useEconomicData.ts` deixa de tratar resposta HTTP OK com lista vazia como erro; `frontend/src/components/tabs/EconomicCalendarTab.tsx` exibe estado informativo limpo `Sem eventos econômicos relevantes na janela atual.` (sem alerta vermelho para janela vazia).
- **Modelos no Android (gateway remoto)**: `frontend/src/components/ListaModelos.tsx` adapta mensagens/estado em runtime mobile para refletir modelos servidos pelo gateway remoto (ex.: "ativo no gateway" / "indisponível no gateway", mensagem de vazio orientando verificação da conexão com gateway), evitando acusar ausência de `.pkl` local no aparelho.

## Fase 3 — Responsividade e Mobile Pro
- **Overflow PRICE/FLUTUANTE (<=420px)**: `frontend/src/theme/mobile-command-center.css` ajustado (quebra de linha, grid/empilhamento de valores e `overflow-wrap`) para telas estreitas.
- **Permissões nativas Android**: `frontend/src-tauri/gen/android/app/src/main/AndroidManifest.xml` atualizado com `INTERNET`, `ACCESS_NETWORK_STATE`, `WAKE_LOCK`, `FOREGROUND_SERVICE`, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`, `POST_NOTIFICATIONS`, `VIBRATE`, `MODIFY_AUDIO_SETTINGS`, `SYSTEM_ALERT_WINDOW`, `READ_MEDIA_IMAGES`, `READ/WRITE_EXTERNAL_STORAGE` (compat), `USE_BIOMETRIC`/`USE_FINGERPRINT`.
- **Módulos criados e conectados na UI**:
  - `frontend/src/lib/mobileAlerts.ts` — som Web Audio, vibração, notificação e teste de alerta.
  - `frontend/src/lib/mobileExport.ts` — exportação JSON/CSV/texto com fallback/share.
  - `frontend/src/components/MobilePermissionsHub.tsx` — central de permissões/alertas/bateria/exportação.
  - `frontend/src/components/MobileBottomNav.tsx` — navegação inferior móvel.
  - `frontend/src/components/MobileBiometricLock.tsx` — bloqueio biométrico/PIN opcional.
  - `frontend/src/components/MarketSessionsClock.tsx` — relógio de sessões GMT (overlap XAU LDN+NY).
  - `frontend/src/components/MobileLotCalculator.tsx` — calculadora de lote/risco.
  - `frontend/src/hooks/useMobileResilientSync.ts` — resync em visibility/online/focus.
- **Integrações**:
  - `frontend/src/components/MobileCommandCenter.tsx`: inclui relógio de sessões, calculadora de lote, exportação de auditoria JSON e hub de permissões no mobile.
  - `frontend/src/App.tsx`: integra `MobileBottomNav` e `useMobileResilientSync` (invalidate queries no mobile).
  - `frontend/src/components/auth/UserSessionGate.tsx`: suporta `MobileBiometricLock` opcional (`localStorage xau_mobile_lock=1`, sessão desbloqueada via `sessionStorage`).

## Fase 4 — Validação e dependências
- **npm audit (frontend/worktree)**: 0 vulnerabilidades (`npm audit --json` => info/low/moderate/high/critical = 0).
  - Pacotes observados: `vite@8.3.4`, `vitest@5.0.5`, `picomatch@4.0.7`, `tinyglobby@0.2.17`.
- **TypeScript**: `npx tsc --noEmit` (frontend) => **OK**.
- **Vitest (direcionados)**:
  - `src/components/MobileCommandCenter.test.tsx` => **13 passed**.
  - `src/components/SystemHealthOnly.test.tsx` + `src/components/tabs/EconomicCalendarTab.test.tsx` => **50 passed** (ajustes de mock/texto para suportar detecção mobile-safe e novo estado vazio informativo do calendário).
- **Vitest (suite completa)**: `vitest_full_rerun.log` => **84 files passed, 1024 tests passed, EXIT:0** (Duration 85.89s). Execução anterior antes dos ajustes finais havia mostrado 2 arquivos/13 testes falhando por mock de `isMobileRuntime` e expectativa de texto vazio do calendário; corrigido.
- **Pytest**: `uv run --no-project --with pytest pytest -q tests/test_sem_codigo_morto.py` => **1 passed** (24.58s).

## Diagnóstico Android (medido nesta sessão)
- Dispositivo: **SM-A057M** (Android 15, R9XY1016R6V), app `com.xau_ai_pro.desktop` v1.2.181 instalado (build antigo 5e04111f).
- Rede local de teste: demo gateway `127.0.0.1:9028` ativo; `adb reverse tcp:9001 tcp:9028` ativo; `curl` do aparelho para `POST /api/auth/login` em `127.0.0.1:9001` => **200**.
- Evidência visual: `MQL5/Files/Temp/visual_audit_latest/android_erro_login_01.png`.
- Achados: build instalado desatualizado (não contém correções desta worktree), e UI do app instalado rejeitou configuração de gateway `http://127.0.0.1:9001` em fluxo de teste/salvamento; `gatewayConfig.ts` na worktree ajustado para permitir loopback/localhost no mobile local (adb reverse). Não houve evidência de novo crash do app; erros esperados de WS ao cair gateway foram observados em sessões anteriores.

## Antes/depois (resumo funcional)
- **Antes (1.2.181 instalado)**: CORE MÁQUINA podia mostrar erro contraditório de `powershell.exe`/WMI no Android; WS/header auth inconsistente no painel mobile; calendário vazio podia cair em erro vermelho; aba Modelos acusava ausência local de artefatos no aparelho; Configurações>Segurança com risco de sobreposição; overflow de valores em telas estreitas; manifesto mobile sem permissões/recursos nativos completos; módulos mobile pro ausentes.
- **Depois (1.2.182 debug, worktree, auditado no SM-A057M)**: telemetria mobile limpa e latência de gateway comprovadas em Sistema; calendário vazio informativo comprovado; Modelos exibem mensagem orientada ao gateway remoto no mobile; Configurações>Segurança abre/renderiza sem sobreposição observada; sub-aba Operações/terminal renderizados; manifesto Android ampliado; módulos mobile pro integrados na UI. WS com token na URL e Bearer em chamadas mobile implementados em código/testes (E2E WS online não comprovado nesta configuração de teste).

## Status de validação consolidado (worktree)
- `npx tsc --noEmit` (frontend): **OK**
- `npx vitest run`: **84 files / 1024 tests passed** (`vitest_full_rerun.log`, EXIT:0)
- `uv run --no-project --with pytest pytest -q tests/test_sem_codigo_morto.py`: **1 passed**
- `npm audit --json` (frontend): **0 vulnerabilidades** (vite 8.3.4, vitest 5.0.5, picomatch 4.0.7, tinyglobby 0.2.17)
- `.ex5` produção MD5 preservado: **844081BF2D51D6A4072B150C3DDC6EBD**

## Build, instalação e auditoria Android (pós-fix)
- **APK (debug aarch64/universal, v1.2.182)**: `frontend/src-tauri/gen/android/app/build/outputs/apk/universal/debug/app-universal-debug.apk`
  - Build: `npx tauri android build --apk --debug --target aarch64` (NDK `28.2.13676358`, `ANDROID_HOME` configurado) => **sucesso** (`android_build.log`).
  - Instalação: `adb -s R9XY1016R6V install -r -t ...` => **Success** (SM-A057M, Android 15).
- **Ambiente de teste**: demo gateway `127.0.0.1:9028` ativo; `adb reverse tcp:9001 -> tcp:9028` (sem tocar produção).

### Evidências capturadas (`MQL5/Files/Temp/visual_audit_latest`)
- `android_182_01_launch.png|.xml` — Calendário com estado vazio informativo (`Sem eventos econômicos relevantes na janela atual.`).
- `android_182_02_sistema.png|.xml`, `android_182_03_sistema_scroll.png|.xml` — Sistema mobile limpo (`Modo Mobile Ativo · Latência Gateway ...`, `Telemetria local do PC não aplicável neste aparelho`, gateway respondendo) e Central de comando read-only com conta/posições/ordens/risco.
- `android_182_05_operar.png|.xml` — aba Operar com sub-abas `Operação`, `Modelos`, `Risco`, `Operações`.
- `android_182_06_modelos.png|.xml` — Modelos com mensagem mobile orientada ao gateway remoto.
- `android_182_09_operacoes.png|.xml` — sub-aba Operações/terminal ao vivo (inclui FLUTUANTE/PRICE/PNL).
- `android_182_10_config.xml`, `android_182_04_config.*`, `android_182_08_config.*` — Configurações e menu (inclui Segurança).
- `android_182_11_seguranca.png|.xml` — seção Segurança aberta/renderizada.
- `android_182_logcat_filtered.txt` — logcat filtrado (`chromium|WebView|Console|ERR_|CLEARTEXT|fetch|auth|WS|WebSocket|xau|gateway|login|token|Seguran|Model`).

### Resultado por item auditado
- **Sistema (CORE MÁQUINA mobile/latência gateway)**: **comprovado**.
- **Modelos (gateway remoto)**: **comprovado** (mensagem/comportamento mobile).
- **Calendário (estado vazio informativo)**: **comprovado**.
- **Configurações > Segurança (sem sobreposição)**: **comprovado visualmente** na seção aberta.
- **Operações/labels**: **comprovado**.
- **Overflow PRICE/FLUTUANTE (<=420px)**: **ajustes aplicados e sem overflow evidente nas capturas do SM-A057M (1080px)**; prova dedicada em viewport <=420px não executada.
- **Login/WS online ponta-a-ponta**: **parcial/não comprovado**. App exibiu `WS Offline` e avisos de configuração de gateway remoto (`VITE_API_BASE/xau-api-base` não definido no runtime), com reconexões de WS no log; porém dados HTTP do gateway foram exibidos na Central de comando no contexto testado. Sem inserção de credenciais reais/alteração de produção.

## Preparação de release v1.2.182 (worktree, sem commit/push)
- **Versões sincronizadas**: `Docs/version.json`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/gen/android/app/tauri.properties` (`1.2.182` / `1002182`), `frontend/src/version.ts`.
- **Artefato local**: APK debug `app-universal-debug.apk` (v1.2.182). MSI/release assinado não gerados.
- **Não executado**: commit, push, tag/release, assinatura/store, rotação de `XAU_GATEWAY_TOKEN`, alterações em `.ex5`, inputs de risco ou serviços de produção.

## Pendências / bloqueios restantes
1. **E2E autenticado + WS online** no aparelho com gateway/sessão de teste corretamente configurados (evidência de login bem-sucedido e WS conectado).
2. **Prova visual dedicada em viewport <=420px** para overflow PRICE/FLUTUANTE, se requerida.
3. **Build/assinatura de release** conforme política (debug vs release, keystore) e eventual MSI Tauri.
4. **Decisão de versionamento remoto**: antes de qualquer `git commit`/`git push`/tag, reportar diff final e validar política (tag `v1.2.181` protegida; CI/workflows com falhas pré-existentes conhecidas).
5. `uv.lock` apareceu como não rastreado na worktree (gerado por execução `uv`); revisar inclusão/exclusão caso haja commit futuro.
