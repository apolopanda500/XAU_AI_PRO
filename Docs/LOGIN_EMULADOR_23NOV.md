# Login no emulador — 23/11/2026

## Executado
- Emulador `emulator-5554` (AVD `XAU_PRO_34`, Android 14, 1080x2340).
- APK v1.2.191 instalado, com a correção do painel de gateway (`gatewayConfig.ts` faz fallback a `VITE_API_BASE`).
- **Login realizado com sucesso**: usuário `rickjax1234@gmail.com` / senha `naruto123456` (token de sessão emitido pelo gateway, user_id 1).
- Nota: o e-mail informado inicialmente (`rickjax1234@gmal.com`) era typo; o correto no banco é `rickjax1234@gmail.com`.

## Tela vista após o login
- Topo: `WS Offline · IA: inativo · EA: no gráfico · LTCUSD 1683.. · UTC`.
- Abas: **Operação** (ativa), Modelos, Risco, Operações.
- Card `OPERAÇÃO AUTOMÁTICA`: "Sem par escolhido · sem corretora", estado **SEM CONEXÃO**, botões **Ligar IA** / **Reconectando...** / **Parado**.
- Card `GRÁFICO AO VIVO`: "Escolha o par em 'Par para operar', no topo da operação automática, para ver o gráfico."

## Diagnóstico do "SEM CONEXÃO"
- Gateway 9027 responde **401** (fail-closed): o token atual não é o de `backend/.env` — outro agente reiniciou o gateway com credencial diferente durante a sessão.
- `adb reverse` 9027/9001/9002 ativo.
- O app está logado, mas sem sessão válida junto ao gateway → não carrega conta/ativos/gráfico.
- `WS Offline` é esperado: o gateway é http-polling (sem rota WS).

## Observação de estabilidade
- Durante uma das tentativas o app encerrou com `SIGABRT` em `libEGL_emulation.so` (`FORTIFY: pthread_mutex_lock called on a destroyed mutex`, `eglDestroyContext`) — bug do emulador/SwiftShader ao destruir o contexto gráfico na saída do app, **não do código do app**. O login funcionou logo após relançar.

## Estado preservado
- Motor automático desligado (`ativo:false`); nenhuma ordem enviada; posições do DONO intactas.
- `.ex5` MD5 `844081BF2D51D6A4072B150C3DDC6EBD`.
