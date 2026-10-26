import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { invoke } from '@tauri-apps/api/core';
import { queryClient } from './hooks/queries';
import { isMobileRuntime, sessionToken, apiBase } from './lib/api';
import { definirBaseLocal, definirPortaWs, portaPadraoGateway } from './lib/portas';
import { installGatewayAuth, installRemoteGatewayAuth, isTauri } from './lib/tauri';
import { GATEWAY_BUILD } from './version';
/*
  `App` NAO E IMPORTADO AQUI (09/10/2026)
  =========================================
  MEDIDO, no app instalado, logo apos a correcao da porta: a aba **Sistema**
  mostrava `GATEWAY OK`, e o **Historico** mostrava `mt5: Failed to fetch` — ao
  mesmo tempo, na mesma janela, na mesma sessao.

  A CAUSA, e ela e ordem de avaliacao
  =====================================
  Nove arquivos guardam a base no TOPO do modulo:

      frontend/src/lib/historico.ts:305     const API = `${apiBase()}`
      frontend/src/hooks/queries.ts:34      idem
      frontend/src/components/UniversalLiveTerminal.tsx:17
      ... e mais seis

  `import` e hoisted: essas linhas rodam quando o modulo CARREGA, e um modulo
  carrega antes de qualquer codigo deste arquivo executar. Com a porta resolvida
  em tempo de BOOT, `apiBase()` devolvia 9001 — o padrao — e o `API` ficava
  congelado em 9001 para sempre.

  MEDIDO: nada escutava na 9001, e `Failed to fetch` e exatamente o erro de um
  `fetch` para um soquete sem dono.

  Por que Sistema funcionava: `SystemHealthOnly.tsx` chama `apiBase()` DENTRO da
  funcao, em tempo de execucao, e le a base ja resolvida. Duas metades do mesmo
  app medindo a mesma coisa em momentos diferentes — o AGENTS.md §5.

  A CORRECAO
  ==========
  `App` passa a ser importado DENTRO do bootstrap, DEPOIS que a porta foi
  resolvida. Isso corrige os nove de uma vez, sem editar nove arquivos.

  E o texto sozinho nao segura: o proximo `const API = apiBase()` num arquivo
  novo volta a congelar. Por isso `portas.test.ts` trava a ordem, e a base
  continua resolvida por `lib/portas.ts` — a fonte unica.
*/
import './theme/global.css';
import './theme/market.css';

import './theme/asset-icons.css';
import './theme/exit.css';
import './theme/history-compact.css';
import './theme/portfolio-balance.css';
import './theme/dashboard-clean.css';
import './theme/robot-asset-table.css';
import './theme/robot-ticket.css';
import './theme/robot-quick.css';
import './theme/robot-terminal.css';
import './theme/quantum.css';
import './theme/wallpapers.css';
import './theme/mining.css';
import './theme/clock.css';
import './theme/mini-info.css';
import './theme/level1.css';
import './theme/guardian.css';
// Escala visual: tipografia minima, espacamento em multiplos de 4 e tabelas
// com numerais tabulares. Carregada por ULTIMO de proposito — assim ela
// vence as folhas que inventaram valores proprios. Ver theme/scale.css.
import './theme/scale.css';

// TOKENS DA FIGMA — carregados por ULTIMO de todos.
//
// A ordem e o que faz a Figma ganhar: este arquivo vem depois do
// `scale.css`, entao os valores que a Figma definir VENCEM o que estiver no
// CSS escrito a mao. Sem essa ordem, o token da Figma seria sobrescrito e a
// mudanca na Figma nao apareceria na app — que e o modo silencioso de uma
// fonte de verdade nao estar na fonte da verdade.
//
// O arquivo e gerado por `scripts/sincronizar_figma.py --aplicar` e contem SO
// o que existe na Figma. Enquanto ele nao existir, o app segue usando o CSS
// manual sem nenhum erro: e por isso que o arquivo precisa existir no repo
// mesmo vazio.
import './theme/figma-tokens.css';
// FLUIDEZ — carregada depois de TODOS os temas (05/10/2026).
//
// Precisa vir depois porque ela declara `--fluido-*`, as duracoes e curvas que
// as outras folhas nao conhecem. E antes dela nao apareceria: qualquer regra
// de `transition` escrita em `global.css`, `quantum.css` ou `mining.css`
// venceria a regra de fluidez por estar mais abaixo na cascata.
import './theme/fluidness.css';

// Ajusta para Tauri (mobile viewport)
const metaViewport = document.querySelector('meta[name="viewport"]');
if (metaViewport) {
  metaViewport.setAttribute('content', 'width=device-width, initial-scale=1.0');
}

const root = document.getElementById('root');

async function waitForGateway() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    let retry = true;
    try {
      /*
        A BASE VEM DE `apiBase()`, E NAO DE 'http://127.0.0.1:9001' (09/10/2026)
        ====================================================================
        MEDIDO: com `XAU_GATEWAY_PORT=9011`, o app instalado abria uma janela
        PRETA com "Falha ao inicializar o ambiente local seguro", sem backend e
        sem erro no console.

        A CAUSA era esta linha: ela batia na 9001 — que e onde o `terminal64`
        escuta por causa do `[MCP.MetaTrader]` do MT5 — e nunca recebia a
        identidade do gateway. Depois de 60 tentativas o `waitForGateway`
        lancava, e o `catch` abaixo pintava a tela preta.

        A porta e uma MEDIDA: quem mede e o Tauri, que le `XAU_GATEWAY_PORT`
        (`porta_gateway()` em `main.rs`). Aqui so se usa o valor que ele mandou
        — o mesmo que o resto do app usa em `apiBase()`. Duas bases
        diferentes no mesmo processo seria o AGENTS.md §5 de novo: o token
        iria num endereco e o corpo em outro.
      */
      const response = await fetch(`${apiBase()}/api/health`, {
        signal: AbortSignal.timeout(2000),
      });
      if (response.status === 401) {
        retry = false;
        throw new Error('gateway local nao autenticado');
      }
      const payload = (await response.json()) as {
        ok?: boolean;
        source?: string;
        gateway_build?: string;
      };
      if (
        response.ok &&
        payload.ok === true &&
        payload.source === 'mt5_gateway' &&
        payload.gateway_build === GATEWAY_BUILD
      )
        return;
      retry = false;
      throw new Error('identidade do gateway local invalida');
    } catch (error) {
      if (!retry) throw error;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 500));
  }
  throw new Error('gateway local indisponivel');
}

async function bootstrap() {
  const mobile = isMobileRuntime();
  if (isTauri() && !mobile) {
    /*
      A PORTA PRIMEIRO, O TOKEN DEPOIS (09/10/2026)
      ==============================================
      A ordem importa. `installGatewayAuth` decide o que e "gateway local"
      comparando com a base resolvida (`lib/portas.ts`), e `waitForGateway`
      consulta `apiBase()`. Perguntar a porta depois deixaria os dois medindo
      9001 enquanto o gateway sobe em 9011 — e o sintoma seria 401 em tudo,
      que e o AGENTS.md §5: servidor certo, cliente medindo a coisa errada.

      A falha aqui NAO derruba o app: um Tauri antigo, sem o comando, devolve
      um `invoke` que rejeita, e o padrao 9001 e o comportamento de antes da
      mudanca. Um `catch` vazio aqui seria trocar uma tela preta por outra.
    */
    try {
      const [porta, portaWs] = await Promise.all([
        invoke<number>('porta_gateway_command'),
        invoke<number>('porta_ws_command'),
      ]);
      if (Number.isInteger(porta) && porta > 0 && porta <= 65535) {
        definirBaseLocal(`http://127.0.0.1:${porta}`);
      }
      definirPortaWs(portaWs);
    } catch {
      console.warn(
        `[bootstrap] Tauri nao devolveu a porta do gateway; usando a padrao ${portaPadraoGateway()}`,
      );
    }
    const token = await invoke<string>('gateway_token_command');
    if (!/^[a-f0-9]{64}$/.test(token)) throw new Error('token de sessao invalido');
    installGatewayAuth(token);
    await waitForGateway();
  }
  if (mobile) {
    // No celular o Tauri desktop nao existe, entao nao ha gateway_token_command
    // nem espera por 127.0.0.1:9001. O token vem de /api/auth/login, guardado
    // por LoginGate. O interceptor e instalado sempre, mesmo sem sessao: a
    // funcao de token e consultada a cada requisicao, entao o header passa a
    // existir no instante em que o login acontece.
    installRemoteGatewayAuth(sessionToken);
  }
  if (!root) throw new Error('elemento raiz indisponivel');
  /*
    O `App` entra AGORA, e nao no topo do arquivo. Ver o bloco de comentario la
    em cima: nove modulos congelam `apiBase()` no carregamento, e a porta so
    existe depois do `invoke`.
  */
  const { default: App } = await import('./App');
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>,
  );
}

/*
  A TELA PRETA, E O QUE ELA DIZ (09/10/2026)
  ===========================================
  MEDIDO: `void bootstrap().catch(() => { root.textContent = 'Falha ao
  inicializar o ambiente local seguro.' })`.

  O `catch` ignorava o erro. Consequencias, todas medidas:

  - a tela ficava PRETA, com uma frase e nada mais;
  - o motivo nao ia para o console, porque nem era registrado;
  - o operador via "falhou" e culparia o gateway, a corretora ou a conta.

  O defeito real era UMA PALAVRA ERRADA na URL — a porta 9001 escrito à mão
  em `main.tsx`, `api.ts` e `tauri.ts`, com o gateway em 9011. Levou um ciclo
  inteiro para achar, e a maior parte dele foi caçar no servidor.

  E o AGENTS.md §5: sintoma de recusa sem motivo faz o operador culpar a coisa
  errada. Este `catch` é a forma exata disso.

  AGORA
  -----
  O erro vai para o console, e a tela diz o que aconteceu e qual endereco foi
  consultado. O dono ve o mesmo numero que o codigo mediu, e o proximo ciclo
  comeca pelo lugar certo.
*/
void bootstrap().catch((erro: unknown) => {
  const motivo = erro instanceof Error ? erro.message : String(erro);
  console.error('[bootstrap] falha ao iniciar o ambiente local:', erro);
  if (root) {
    root.textContent = '';
    const titulo = document.createElement('div');
    titulo.textContent = 'Falha ao inicializar o ambiente local seguro.';
    const detalhe = document.createElement('div');
    detalhe.textContent = `Motivo: ${motivo}`;
    const endereco = document.createElement('div');
    try {
      endereco.textContent = `Endereco consultado: ${apiBase()}`;
    } catch {
      endereco.textContent = 'Endereco consultado: (indisponivel)';
    }
    root.append(titulo, detalhe, endereco);
  }
});
