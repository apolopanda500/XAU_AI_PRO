# 📱 Preparação para Produção Real + Android

## Visão geral da arquitetura multiplataforma

```
Desktop (Windows)                        Android (Tauri 2)
┌─────────────────────┐                  ┌──────────────────────┐
│ WebView (frontend)  │                  │ WebView (frontend)   │
│  apiBase() ──────────────── HTTP ──────►│  apiBase() remoto    │
│  wsUrl() ─────────────────── WSS ──────►│  wsUrl() remoto      │
└────────┬────────────┘                  └──────────┬───────────┘
         │ 127.0.0.1:9001                           │ HTTPS/WSS
         ▼                                          ▼
┌─────────────────────┐                  ┌──────────────────────┐
│ Gateway Python 9001 │                  │ Gateway em VPS/Nuvem │
│ Core Rust 9002 (WS) │◄── MT5/EA local  │ + túnel p/ PC trader │
└─────────────────────┘                  └──────────────────────┘
```

**Regra de ouro:** o celular NUNCA fala com o MT5 diretamente. O MT5 vive no
PC/VPS do trader; o app Android consome o gateway por HTTPS/WSS com token.

## O que já está pronto (implementado nesta revisão)

1. **`frontend/src/lib/api.ts`** — fonte única de configuração:
   - Desktop: `http://127.0.0.1:9001` + `ws://127.0.0.1:9002/ws/market`
   - Android: definir `VITE_API_BASE` / `VITE_WS_URL` no build, ou
     `localStorage.xau-api-base` / `xau-ws-url` em runtime (tela de ajuste futura)
   - **42 arquivos** do frontend migrados para `apiBase()`/`wsUrl()` — zero URL fixa
2. **CSP ativa** em `tauri.conf.json` (antes `null`): conexões só para localhost +
   HTTPS de mercados
3. **CORS do gateway** coberto por testes (`tests/test_gateway_cors.py`)
4. **Vitest** instalado com primeiro suíte (`src/lib/api.test.ts`) + `vitest.config.ts`
5. **Targets Rust Android completos**: aarch64, armv7, i686 e x86_64 ✓
6. **`gen/android`** já gerado pelo `tauri android init` ✓

## Pré-requisitos Android (máquina de build)

| Requisito | Status |
|---|---|
| Android SDK (`ANDROID_HOME`) | ✅ `C:\Users\Micro\AppData\Local\Android\Sdk` |
| JDK 17+ | ✅ JBR do Android Studio (OpenJDK 25) |
| Targets Rust android (4 ABIs) | ✅ |
| NDK (`ndk;26.x`) via `sdkmanager` | ⚠️ instalar se ausente |
| `JAVA_HOME` apontando para o JBR | ⚠️ setar por sessão (ver abaixo) |

## Passo a passo do build Android (quando o backend remoto estiver no ar)

```powershell
# 1) JDK do Android Studio para esta sessão
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"

# 2) NDK (uma vez)
sdkmanager "ndk;26.3.11579264"

# 3) Build do frontend com o servidor de produção do gateway
#    (em frontend/, crie .env.production com:)
#    VITE_API_BASE=https://SEU-SERVIDOR:9001
#    VITE_WS_URL=wss://SEU-SERVIDOR:9002/ws/market
npm run build

# 4) APK/AAB de debug primeiro (valida emulador/aparelho)
npx tauri android build --debug --apk

# 5) Release assinado (Play Store exige .aab)
npx tauri android build         # gera .aab + .apk assinados
```

Assinatura (uma vez):
```powershell
keytool -genkey -v -keystore xau-ai-pro.keystore -alias xauaipro -keyalg RSA -keysize 2048 -validity 10000
```

## Endurecimentos de produção recomendados (backend)

- **Não expor `allow_origins=["*"]`** no FastAPI em produção: restringir à origem do app
- **Token de API** no gateway remoto (header `Authorization`) — o campo `api_key`
  já existe no `config.json` do app, falta o gateway validar
- **WSS obrigatório** no Android (TLS); no desktop o WS local pode continuar em `ws://`
- **Rate limit** nos endpoints de comando do gateway remoto

## Checklist de lançamento

- [x] Frontend sem URLs hardcoded (42 arquivos migrados)
- [x] CSP ativa no Tauri
- [x] CORS testado no gateway
- [x] Testes frontend (vitest) e backend (pytest) verdes
- [ ] Gateway remoto (VPS) com HTTPS/WSS + token
- [ ] `.env.production` com `VITE_API_BASE`/`VITE_WS_URL` reais
- [ ] `tauri android build --debug` validado em aparelho
- [ ] Keystore de release gerada e guardada
- [ ] `.aab` assinado enviado à Play Console
