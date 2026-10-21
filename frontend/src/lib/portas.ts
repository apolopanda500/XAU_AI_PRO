/*
  A PORTA DO GATEWAY — FONTE UNICA NO FRONTEND (09/10/2026)
  ==========================================================
  MEDIDO: com `XAU_GATEWAY_PORT=9011` no ambiente do usuario, o app instalado
  abriu uma janela **PRETA** com uma unica frase:

      Falha ao inicializar o ambiente local seguro.

  Nenhum backend subiu. Nenhum erro no console. Nenhuma pista do porque.

  A CAUSA, e ela e o AGENTS.md §5 dos dois lados
  ================================================
  O PRODUTOR, o gateway, obedecia `XAU_GATEWAY_PORT=9011`. O CONSUMIDOR, o
  frontend, tinha a porta **escrita à mão** em quatro lugares:

      frontend/src/main.tsx:66   fetch('http://127.0.0.1:9001/api/health')
      frontend/src/lib/api.ts:36 return 'http://127.0.0.1:9001'
      frontend/src/lib/tauri.ts:19  url.port === '9001'
      frontend/src/lib/api.ts:142   url.port === '9001'

  A sessao de 09/10 tinha convertido a porta em variavel em Python
  (`_porta_gateway`), no Core (`porta_de`), no Tauri (`porta_gateway()`) e na
  CSP — e o **frontend ficou de fora**. Ele continuaria batendo na 9001, que e
  onde o `terminal64` escuta por causa do `[MCP.MetaTrader]`. O fetch nao
  receberia a identidade do gateway, e o bootstrap cairia no `catch`.

  Este arquivo e a FONTE UNICA. Nenhum outro lugar do frontend escreve a porta
  do gateway local, e este e o unico que a pergunta ao Tauri.

  POR QUE O VALOR FICA EM MODULO, E NAO EM VARIAVEL DE AMBIENTE DO VITE
  =====================================================================
  `apiBase()` e SINCRONO e e chamada por todo o app — por cada `useQuery`, por
  cada `fetch`. Torna-la `async` arrastaria o app inteiro. E `VITE_*` e
  resolvido no BUILD: um `.env.production` com 9011 fixaria o numero no
  instalador, e a variavel de ambiente do usuario deixaria de valer — que e
  justamente o que o dono pediu (porta ajustavel sem recompilar).

  O caminho e: o Tauri le `XAU_GATEWAY_PORT` no BOOT, o frontend pergunta uma
  vez no bootstrap, e daqui em diante le o valor em memoria. Mesmo padrao do
  token de sessao, que tambem e injetado pelo Tauri por sessao (AGENTS.md §4).
*/

const PORTA_PADRAO = 9001;
const PORTA_WS_PADRAO = 9002;

/**
 * A porta resolvida e gravada no `localStorage`, e nao so em memoria.
 *
 * MEDIDO: `portas.test.ts` reprovou ao recarregar os modulos
 * (`vi.resetModules()`): o modulo novo nascia com `baseLocal` vazio e
 * `apiBase()` voltava a 9001. A base vivia **dentro do modulo**, e qualquer
 * recarga a perdia.
 *
 * Isso nao era hipotetico: vale para recarga de modulo em desenvolvimento, e
 * vale para o `import` dinamico que o `main.tsx` faz do `App` — a ordem
 * passou a carregar, mas a base continuava Depending do momento exato.
 *
 * O mesmo caminho que o token de sessao usa (`xau-session-token`): o dado e
 * resolvido uma vez por sessao e relido por quem precisar. `apiBase()` e
 * SINCRONO e chamada por todo o app, entao nao pode depender de `await`.
 */
const CHAVE_PORTA = 'xau-gateway-port';

function lerPortaGravada(): number {
  try {
    const bruto = typeof window !== 'undefined' ? window.localStorage.getItem(CHAVE_PORTA) : null;
    const n = Number(bruto);
    return Number.isInteger(n) && n > 0 && n <= 65535 ? n : 0;
  } catch {
    return 0;
  }
}

function gravarPorta(porta: number): void {
  try {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(CHAVE_PORTA, String(porta));
  } catch {
    /* localStorage indisponivel: a base segue em memoria */
  }
}

/** O padrao em numero — para a mensagem de aviso, sem URL escrita a mao. */
export function portaPadraoGateway(): number {
  return PORTA_PADRAO;
}

/** A porta do WebSocket de mercado. `9002` ate o Tauri responder. */
let portaWs = 0;

export function portaWsMercado(): number {
  return portaWs || PORTA_WS_PADRAO;
}

/**
 * Grava a porta do WebSocket que o Tauri mandou.
 *
 * MEDIDO: `cargo check` acusava `porta_ws is never used` — e o compilador estava
 * certo. `wsUrl()` tinha `ws://127.0.0.1:9002` escrito a mao, com consumidor
 * real (`useMarketWebSocket.ts:122`, `new WebSocket(getWsUrl())`).
 *
 * Hoje `XAU_WS_PORT` nao esta definido, entao o 9002 funciona POR ACASO: o
 * padrao do Rust e o padrao do frontend coincidem. No dia em que o dono definir
 * `XAU_WS_PORT` para mover o WebSocket, o Rust subiria na porta nova e o
 * frontend continuaria no 9002 — e o sintoma seria "o preco nao atualiza",
 * sem erro nenhum no console.
 *
 * E o AGENTS.md §9: um controle que nada le e pior que a ausencia dele. Deixar
 * `porta_ws` morta seriaExactly isso.
 */
export function definirPortaWs(porta: number): void {
  if (Number.isInteger(porta) && porta > 0 && porta <= 65535) portaWs = porta;
}

/** Zera a porta do WebSocket. Existe para o teste. */
export function limparPortaWs(): void {
  portaWs = 0;
}

/** A base do gateway local ja resolvida. Cai na porta gravada na sessao. */
let baseLocal = (() => {
  const porta = lerPortaGravada();
  return porta ? `http://127.0.0.1:${porta}` : '';
})();

/** A porta do gateway local. `9001` ate o Tauri responder. */
export function portaGateway(): number {
  if (!baseLocal) return PORTA_PADRAO;
  try {
    return Number(new URL(baseLocal).port) || PORTA_PADRAO;
  } catch {
    return PORTA_PADRAO;
  }
}

/** A base do gateway local ja resolvida. Vazio antes do bootstrap. */
export function baseGatewayLocal(): string {
  return baseLocal;
}

/**
 * Grava a base que o Tauri mandou.
 *
 * Aceita so `http` em loopback: a base local nao pode apontar para fora da
 * maquina, porque o token de sessao e injetado em toda requisicao que case
 * com ela (`installGatewayAuth`). Uma base errada vazaria o token — que e o
 * que o AGENTS.md §12 proibe.
 */
export function definirBaseLocal(base: string): void {
  const limpa = String(base ?? '').trim();
  if (!limpa) return;
  try {
    const url = new URL(limpa);
    const loopback = url.hostname === '127.0.0.1' || url.hostname === 'localhost';
    if (url.protocol !== 'http:' || !loopback) return;
    baseLocal = `${url.protocol}//${url.host}`;
    gravarPorta(Number(url.port) || PORTA_PADRAO);
  } catch {
    /* base ilegivel: segue com o padrao, que e o comportamento anterior */
  }
}

/** Zera a base. Existe para o teste; o app nao usa. */
export function limparBaseLocal(): void {
  baseLocal = '';
  try {
    if (typeof window !== 'undefined') window.localStorage.removeItem(CHAVE_PORTA);
  } catch {
    /* sem localStorage: nada a limpar */
  }
}

/** `true` quando a URL e do gateway LOCAL, em qualquer porta. */
export function ehGatewayLocal(url: URL): boolean {
  if (url.protocol !== 'http:') return false;
  if (url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') return false;
  /*
    COMPARA COM A BASE RESOLVIDA, E NAO COM '9001' ESCRITO A MAO.

    Era `url.port === '9001'`. Com o gateway em 9011, essa comparacao dava
    `false` para a propria requisicao do app — e o token de sessao deixava de
    ser injetado, o gateway respondia 401 em TUDO, e o sintoma seria "o app
    perdeu a sessao". O servidor estaria certo e o cliente errado: o
    AGENTS.md §5 de novo, e desta vez na propria correcao.

    Se a base ainda nao foi resolvida, cai no padrao — e o comportamento e o de
    antes da mudanca, que e o que o teste antigo mede.
  */
  if (!baseLocal) return url.port === String(PORTA_PADRAO);
  return url.origin === baseLocal;
}