# Deploy do gateway remoto para o app Android

Data: 2026-09-25
Status: **documentado, não executado**. Não há host remoto provisioned nem TLS válido neste ambiente.

## Por que isso é obrigatório

O APK `aarch64` foi gerado e assinado, mas **não funciona como produto** enquanto o gateway não estiver acessível de fora da máquina do trader.

Em `frontend/src/lib/api.ts`:

- linha 29: `const explicit = stored('xau-api-base') || viteEnv.env?.VITE_API_BASE;`
- linhas 32–36: em Android, sem valor configurado, o app faz fallback para `http://127.0.0.1:9001` e emite o aviso `[api] Android sem VITE_API_BASE/xau-api-base: configure o gateway remoto.`
- linha 43: o WebSocket usa `VITE_WS_URL` com fallback `ws://127.0.0.1:9002/ws/market`.

No celular, `127.0.0.1` aponta para o próprio aparelho. Logo, sem gateway remoto o app abre, mas **toda chamada de API falha**.

## Contrato do gateway

O gateway Python escuta em `0.0.0.0:9001` quando exposto (HTTP) e `9002` (WebSocket de mercado). O Core Rust usa `9003`. Rotas de saúde e dados começam em `/api/` e `/health`.

Proteções ativas que **não** podem ser desligadas na exposição:

| Trava | Comportamento verificado |
| --- | --- |
| `XAU_GATEWAY_TOKEN` | `/health`, `/api/boot` e o Core retornam **401** sem token (validado em 2026-09-25) |
| `XAU_MCP_TRADING` | manter em `0` |
| `XAU_ENABLE_REAL_ORDERS` | manter em `0` |
| `XAU_ENABLE_EMERGENCY_RESUME` | manter em `0` |
| Clientes externos | exigem **HTTPS** e bloqueiam redirect para destino não permitido |
| SSRF guard | ativo nas rotas de saída |

## Passo a passo

### 1. Preparar o host

- Uma VM ou VPS com MT5 instalado e login da corretora configurado. O gateway depende do terminal MT5 no Windows.
- Abrir apenas `9001/tcp` e `9002/tcp` para o IP do celular. **Não** expor `9003` (Core) publicamente.
- Gerar token forte: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

### 2. Publicar atrás de TLS

Não expor o gateway diretamente. Usar um reverse proxy com certificado válido. Exemplo com Caddy, porque emite certificado automaticamente:

```
chat.exemplo.com {
    reverse_proxy 127.0.0.1:9001
}
```

Para o WebSocket, o Caddy faz upgrade automaticamente. Em Nginx é preciso `proxy_set_header Upgrade $http_upgrade;` e `proxy_set_header Connection "upgrade";`.

### 3. Iniciar o gateway com as variáveis de segurança

```powershell
$env:XAU_GATEWAY_TOKEN      = '<token gerado no passo 1>'
$env:XAU_MCP_TRADING        = '0'
$env:XAU_ENABLE_REAL_ORDERS = '0'
$env:XAU_ENABLE_EMERGENCY_RESUME = '0'
.\mt5-gateway.exe
```

O bind deve ser em `0.0.0.0`, não em `127.0.0.1`. Confirmar na configuração de bind do `backend/fastapi_gateway.py` antes de expor.

### 4. Validar o host antes do celular

```powershell
# deve responder 401 (prova que o token e a rota existem)
curl -i https://chat.exemplo.com/health

# com token, deve devolver o build
curl -i -H "Authorization: Bearer <token>" https://chat.exemplo.com/health

# capabilities deve retornar ok=true
curl -s -H "Authorization: Bearer <token>" https://chat.exemplo.com/api/capabilities
```

Só seguir para o passo 5 se o terceiro comando retornar `ok=true` e o build for o esperado.

### 5. Apontar o app Android

Duas opções, sem recompilar:

1. **Runtime** — definir `xau-api-base` e `xau-ws-url` em `localStorage` do WebView.
2. **Build** — criar `frontend/.env.production`:

```
VITE_API_BASE=https://chat.exemplo.com
VITE_WS_URL=wss://chat.exemplo.com/ws/market
```

Depois recompilar o APK com o mesmo JDK 21 usado em 2026-09-25. O CSP do Tauri Android já permite `wss:`.

## Pendências honestas

- **Não validado** com host remoto real nem TLS válido. Todo o passo 4–5 acima é procedimento, não resultado medido.
- **Não testado** em aparelho físico nem emulador. Não havia dispositivo conectado em 2026-09-25.
- O token hoje é entregue ao gateway filho pelo próprio Tauri em `XAU_GATEWAY_TOKEN`. Em Android não há Tauri desktop para injetá-lo, então **é preciso definir como o app Android obtém o token**. Esta é uma lacuna de projeto ainda não resolvida e é o principal bloqueador técnico do Android.
- Sem um esquema de distribuição de token seguro, qualquer APK com token embutido vira credencial exposta.
