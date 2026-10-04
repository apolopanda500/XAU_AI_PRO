# Teste do APK no emulador Android

## Estado em 2026-09-27

| Etapa                                    | Estado                                                                        |
| ---------------------------------------- | ----------------------------------------------------------------------------- |
| APK `x86_64`/universal gerado e assinado | **OK** — `XAU-AI-PRO-1.2.3-universal.apk`, 32,5 MB, v2+v3, `zipalign` OK      |
| Emulador sobe e registra no `adb`        | **OK** — `sys.boot_completed=1`                                               |
| APK instala no emulador                  | **OK** — `Success`                                                            |
| App inicia sem crash                     | **OK** — pid ativo, `topResumedActivity=com.xau_ai_pro.desktop/.MainActivity` |
| Tela renderiza conteudo                  | **BLOQUEADO** — tela preta; ver causa abaixo                                  |

## A tela preta NAO e bug do app

A imagem de sistema instalada e `system-images;android-35/aosp_atd/x86_64`, uma
**ATD (Automated Test Device)**. Por definicao, ATD:

- remove o **SystemUI**;
- **desabilita a renderizacao por hardware**;
- roda em modo headless, para teste instrumentado.

Resultado no logcat:

```
E chromium: [ERROR:tile_manager.cc(982)] WARNING: tile memory limits exceeded, some content may not draw
```

O WebView do Chromium sobe, a Activity fica em `topResumedActivity`, e mesmo
assim nada e desenhado. Confirmado por dois caminhos:

1. Documentacao do Android Studio: _"ATDs improve runtime performance... Disable
   hardware rendering"_ e a tabela de componentes removidos inclui SystemUI.
2. Bug conhecido da comunidade (scrcpy #4609, "Blank screen when connected to
   Android ATD virtual device"): _"If I change to regular, non-ATD device,
   display output gets forwarded properly."_

Nao adianta aumentar RAM nem trocar GPU: o renderizador esta desligado na imagem.
**A correcao e usar uma imagem com UI real.**

## Como testar de verdade

```powershell
# 1. Imagem com UI (nao ATD)
$sdk = "$env:LOCALAPPDATA\Android\Sdk"
$jdk = "$env:LOCALAPPDATA\Temp\opencode\jdk21-temurin\jdk"
$env:JAVA_HOME = $jdk
& "$sdk\cmdline-tools\latest\bin\sdkmanager.bat" --install "system-images;android-35;default;x86_64"

# 2. AVD novo com a imagem correta
& "$sdk\cmdline-tools\latest\bin\avdmanager.bat" create avd -n xau_ui -k "system-images;android-35;default;x86_64" -d pixel_6 --force

# 3. Sobe com GPU de host
& "$sdk\emulator\emulator.exe" -avd xau_ui -no-snapshot -no-boot-anim -gpu host -no-audio -memory 4096

# 4. Instala e abre
$adb = "$sdk\platform-tools\adb.exe"
& $adb install -r -t frontend\src-tauri\gen\android\app\build\outputs\apk\universal\release\XAU-AI-PRO-1.2.3-universal.apk
& $adb shell am start -n com.xau_ai_pro.desktop/.MainActivity
& $adb shell screencap -p /sdcard/xau.png
& $adb pull /sdcard/xau.png "$env:TEMP\xau.png"
```

## O emulador nao ve o gateway do host em 127.0.0.1

O `10.0.2.2` e o alias que o emulador usa para alcancar a maquina do host. O
APK de teste ja nasce com esse destino:

```
VITE_API_BASE=http://10.0.2.2:9001
VITE_WS_URL=ws://10.0.2.2:9002/ws/market
```

A CSP do bundle precisa da mesma origem, e o script de CSP recusa texto claro
quando `XAU_BUILD_TARGET=production`:

```
XAU_GATEWAY_ORIGIN=http://10.0.2.2:9001
XAU_WS_ORIGIN=ws://10.0.2.2:9002
```

O gateway precisa estar no host:

```powershell
.\scripts\Start-Detached.ps1 -FilePath ".\.venv\Scripts\python.exe" `
    -CommandLine "-m backend.mt5_gateway" -WorkingDirectory "$PWD" -WaitPort 9001
```

> **Use sempre `Start-Detached.ps1`.** Com `Start-Process`, o filho fica preso ao
> job object da sessao do PowerShell e morre junto com ela — foi o que fez o
> gateway responder 200 e sumir em segundos, e o emulador sumir do `adb`.

## Se a tela continuar preta na imagem com UI

Causas em ordem de probabilidade:

1. Falta de espaco: `python scripts/preflight.py --etapa android` exige 8 GB.
2. `-gpu host` sem aceleracao: a maquina tem Hypervisor, mas nem todo host
   suporta GPU passthrough. Troque por `-gpu swiftshader_indirect`.
3. O app entrou na tela de login e o WebView esta em branco porque o gateway nao
   responde: confira `http://127.0.0.1:9001/api/health` no host e use o painel
   "Configurar gateway" da tela de login (ele grava `xau-api-base`).
4. CSP bloqueando: a origem do `10.0.2.2` precisa estar no `connect-src` do
   bundle. `npm run csp` regenera a partir das variaveis de ambiente.
