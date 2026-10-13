// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

/*
  A TELA PRETA — A PORTA FIXA ESCRITA A MAO (09/10/2026)
  =====================================================
  MEDIDO no app instalado, com `XAU_GATEWAY_PORT=9011` no ambiente do usuario:

      [captura da janela do app]
      Falha ao inicializar o ambiente local seguro.

      e nada mais. Janela preta, sem botao, sem saida, sem erro no console.

 processo: `XAU AI PRO` PID 13648, e NENHUM backend — sem `mt5-gateway`,
  sem `xau-ai-pro-core`, com 9002, 9003 e 9011 livres.

  A CAUSA
  =======
  A sessao de 09/10 converteu a porta em variavel em Python (`_porta_gateway`),
  no Core (`porta_de`), no Tauri (`porta_gateway()`) e na CSP. O **frontend
  ficou de fora**, com `9001` escrito a mao em quatro lugares:

      main.tsx:66           fetch('http://127.0.0.1:9001/api/health')
      lib/api.ts:36         return 'http://127.0.0.1:9001'
      lib/tauri.ts:19       url.port === '9001'
      lib/api.ts:142        url.port === '9001'

  Entao: o gateway subia em 9011, o `fetch` batia na 9001 — que e onde o
  `terminal64` escuta por causa do `[MCP.MetaTrader]` — e nunca recebia a
  identidade do gateway. 60 tentativas, depois o `throw`, e o `catch` pintava a
  tela preta SEM registrar o erro.

  O AGENTS.md §5, do lado do cliente: onde os dois lados discordam do nome, o
  defeito e do lado que procura no outro. E §1: sintoma de recusa sem motivo faz
  o operador culpar a coisa errada.

  O QUE ESTES TESTES TRAVAM
  =========================
  1. A base segue a PORTA que o Tauri mandou — em 9001 e em 9011.
  2. O TOKEN DE SESSAO e injetado na porta nova. Sem isso o gateway responde 401
     em tudo, e o sintoma seria "o app perdeu a sessao".
  3. O texto com `9001` escrito a mao nao volta no codigo. Um teste que mede o
     comportamento passa com o numero escrito duas vezes; este mede o numero.
  4. PROVA NEGATIVA: com a porta em 9011, a regra antiga reprova.
*/
import { apiBase, isGatewayRequest, wsUrl } from './api';
import {
  definirBaseLocal as definir,
  ehGatewayLocal as gatewayLocal,
  limparBaseLocal as limpar,
  portaGateway as porta,
} from './portas';
import { isLocalGatewayRequest } from './tauri';

/*
  O QUE ESTE ARQUIVO FAZ COM O CODIGO
  ====================================
  Le as folhas e mede o numero — `9001` escrito a mao. Antes de medir, tira os
  COMENTARIOS. E tira de verdade, com estado de string e de comentario:

      barra-barra, ate o fim da linha
      barra-estrela ate a barra-estrela-barra, de varias linhas
      e, dentro de aspas simples, duplas ou de crase, nada e comentario

  Um filtro por linha (`linha.startsWith('//')`) NAO serve, e MEDIDO aqui: a
  linha `Era url.port === '9001' && loopback` esta no MEIO de um bloco de
  comentario e nao comeca com marcador nenhuma — o filtro a deixava passar, e o
  teste reprovava por causa do TEXTO QUE DOCUMENTA A MEDICAO.

  E o AGENTS.md §6.4, escrito para Python e valer aqui tambem: case a REGRA, nao
  a palavra; e um `#` dentro de string (URL, caminho) nao e comentario. Ja
  aconteceu neste projeto: em 07/10 a trava "o mapa e config e o codigo nao tem
  nome de ativo" reprovou no proprio texto que media o defeito — e o defeito
  era o TESTE, nao a regra. Aqui a regra esta certa e o teste e que tem de
  aprender a ler.
*/
function semComentarios(fonte: string): string {
  let saida = '';
  let i = 0;
  let estado: 'codigo' | 'linha' | 'bloco' | 'aspas' = 'codigo';
  let aspas = '';
  while (i < fonte.length) {
    const c = fonte[i];
    const d = fonte[i + 1];
    if (estado === 'codigo') {
      if (c === '/' && d === '/') {
        estado = 'linha';
        i += 2;
        continue;
      }
      if (c === '/' && d === '*') {
        estado = 'bloco';
        i += 2;
        continue;
      }
      if (c === "'" || c === '"' || c === '`') {
        estado = 'aspas';
        aspas = c;
        saida += c;
        i += 1;
        continue;
      }
      saida += c;
      i += 1;
      continue;
    }
    if (estado === 'linha') {
      if (c === '\n') {
        estado = 'codigo';
        saida += '\n';
      }
      i += 1;
      continue;
    }
    if (estado === 'bloco') {
      if (c === '*' && d === '/') {
        estado = 'codigo';
        i += 2;
        continue;
      }
      if (c === '\n') saida += '\n';
      i += 1;
      continue;
    }
    /* aspas: so o fechamento de verdade encerra; barra invertida escapa */
    if (c === '\\') {
      saida += c + (d ?? '');
      i += 2;
      continue;
    }
    if (c === aspas) {
      estado = 'codigo';
      saida += c;
      i += 1;
      continue;
    }
    saida += c;
    i += 1;
  }
  return saida;
}

import { definirPortaWs, limparPortaWs, portaWsMercado } from './portas';

describe('a porta do gateway e MEDIDA, nao escrita', () => {
  beforeEach(() => {
    limpar();
    limparPortaWs();
    window.localStorage.clear();
  });
  afterEach(() => {
    limpar();
    limparPortaWs();
  });

  it('PROVA: com o Tauri em 9011, a base do app e a 9011', () => {
    definir('http://127.0.0.1:9011');
    expect(porta()).toBe(9011);
    expect(apiBase()).toBe('http://127.0.0.1:9011');
  });

  it('PROVA: com o Tauri em 9001, a base continua a 9001 — o padrao nao mudou', () => {
    definir('http://127.0.0.1:9001');
    expect(apiBase()).toBe('http://127.0.0.1:9001');
  });

  it('PROVA: sem o Tauri, cai no padrao — o comportamento antigo', () => {
    /*
      O build instalado de hoje NAO tem o comando `porta_gateway_command`. Sem
      este `expect`, o app de hoje ficaria preto para sempre depois da
      atualizacao: o `invoke` rejeitaria e a base resolveria para `''`.
    */
    expect(porta()).toBe(9001);
    expect(apiBase()).toBe('http://127.0.0.1:9001');
  });

  it('PROVA: o TOKEN entra na porta nova — sem isto e 401 em tudo', () => {
    definir('http://127.0.0.1:9011');
    /*
      Esta e a assercao que impede o pior desfecho. `isLocalGatewayRequest`
      decidia por `url.port === '9001'`; com o gateway em 9011, a propria
      requisicao do app deixava de ser "local", o `Authorization: Bearer` nao
      era injetado, e o gateway recusava tudo. O token equivale a acesso ao
      terminal (AGENTS.md §12) — e o sintoma seria "a conta perdeu a sessao".
    */
    expect(isLocalGatewayRequest('http://127.0.0.1:9011/api/account')).toBe(true);
    expect(isGatewayRequest('http://127.0.0.1:9011/api/health')).toBe(true);
  });

  it('PROVA NEGATIVA: na 9011, a regra antiga REPROVA estas duas medidas', () => {
    definir('http://127.0.0.1:9011');

    /*
      A MESMA comparacao, com a regra COMO ESTAVA:
      `url.port === '9001' && loopback`.
    */
    const regraAntiga = (url: URL) => url.port === '9001' && url.hostname === '127.0.0.1';
    const naPortaNova = new URL('http://127.0.0.1:9011/api/account');

    // A regra antiga NAO reconhece a porta nova — e por isso o token sumia.
    expect(regraAntiga(naPortaNova)).toBe(false);
    expect(regraAntiga(naPortaNova)).not.toBe(true);

    // A regra nova reconhece, que e o que os testes acima exigem.
    expect(gatewayLocal(naPortaNova)).toBe(true);
    // E segue reconhecendo a porta padrao quando e a que o Tauri mandou.
    limpar();
    definir('http://127.0.0.1:9001');
    expect(gatewayLocal(new URL('http://127.0.0.1:9001/api/account'))).toBe(true);
  });

  it('o token NAO vai para a porta que nao e a do gateway — e nao um detalhe', () => {
    /*
      MEDIDO: com o Tauri em 9011, a 9001 esta o `terminal64`, por causa do
      `[MCP.MetaTrader]` do MT5 (`assistant.ini`). Uma requisicao para la NAO e
      do gateway.

      E por isso que `ehGatewayLocal` compara com a base RESOLVIDA e nao com
      `url.port === '9001' || url.hostname === '127.0.0.1'`: a versao frouxa
      injetaria o `Authorization: Bearer` do token de sessao em um processo que
      nao e o gateway. O token equivale a acesso ao terminal — e o AGENTS.md §12
      proibe registra-lo, quanto mais injeta-lo em host desconhecido.

      Este teste existia para documentar que a escolha e DELIBERADA. Sem ele, um
      "corrigir" future trocaria a comparacao por uma mais permissiva achando
      que estaria consertando o acesso local.
    */
    definir('http://127.0.0.1:9011');

    // A porta do gateway: recebe o token.
    expect(isLocalGatewayRequest('http://127.0.0.1:9011/api/account')).toBe(true);
    // A porta do terminal64: NAO recebe.
    expect(isLocalGatewayRequest('http://127.0.0.1:9001/api/account')).toBe(false);
    // E host de fora continua de fora, com qualquer porta.
    expect(isLocalGatewayRequest('http://exemplo.invalido:9011/api/account')).toBe(false);
  });

  it('PROVA NEGATIVA: a URL antiga some do codigo — o numero nao volta escrito a mao', () => {
    /*
      Um teste de comportamento passa com `9001` escrito duas vezes. Este mede o
      NUMERO: le `main.tsx`, `api.ts` e `tauri.ts`, tira comentarios e linhas em
      branco, e reprova se sobrar `127.0.0.1:9001` ou `=== '9001'` em codigo.

      E o AGENTS.md §6.4: casa a REGRA, nao a palavra. Por isso os COMENTARIOS
      sao removidos antes — sem isso, um comentario que DOCUMENTA a medicao
      reprovaria o teste, e o defeito seria o teste (ja aconteceu em 07/10,
      §3.2 do PASSAGEM).
    */
    return Promise.all(
      ['./api.ts', './tauri.ts', './portas.ts', '../main.tsx'].map(async (arquivo) => {
        // @ts-expect-error `node:fs` nao tem tipagem neste projeto
        const { readFileSync } = await import('node:fs');
        const codigo = semComentarios(String(readFileSync(new URL(arquivo, import.meta.url), 'utf-8')));

        // A porta literal que produzia a tela preta.
        expect(codigo, `${arquivo} com 9001 escrito a mao`).not.toMatch(
          /127\.0\.0\.1:9001|localhost:9001/,
        );
        // E a do WebSocket, que `cargo check` acusou como controle morto
        // (`porta_ws is never used`): mesma classe de defeito, mesma regra.
        expect(codigo, `${arquivo} com 9002 escrito a mao`).not.toMatch(
          /127\.0\.0\.1:9002|localhost:9002/,
        );
      }),
    );
  });

  it('PROVA NEGATIVA: o removedor de comentarios e o que segura este teste', () => {
    /*
      Sem isto, o filtro ingenuo por linha volta — e reprova no texto que
      documenta a medicao, que foi EXATAMENTE o que aconteceu na primeira
      rodada deste arquivo. MEDIDO: a linha `Era url.port === '9001' && loopback`
      esta no meio de um bloco `/* ... *\/` e nao comeca com marcador nenhuma.
    */
    const fonte = [
      'const a = 1; // isto e comentario',
      '/* isto e bloco,\n   e esta linha NAO comeca com marcador */',
      "const url = 'http://exemplo/nao/comentario';",
    ].join('\n');

    const sem = semComentarios(fonte);

    // As duas linhas de codigo ficam.
    expect(sem).toContain('const a = 1;');
    expect(sem).toContain('const url =');
    // O `//` e o bloco saem, inclusive a linha do meio que o filtro por linha
    // deixaria passar.
    expect(sem).not.toContain('isto e comentario');
    expect(sem).not.toContain('NAO comeca com marcador');
    // E a barra dentro da string continua — um filtro por linha a apagaria
    // junto com o codigo dela (AGENTS.md §6.4).
    expect(sem).toContain('http://exemplo/nao/comentario');
  });

  it('so aceita base local em loopback — o token nao pode vazar para fora', () => {
    /*
      `definirBaseLocal` decide se o `Authorization: Bearer` sera injetado
      naquela base (`installGatewayAuth`). Uma base apontando para fora faria o
      token de sessao sair para um host desconhecido — o que o AGENTS.md §12
      proibe.
    */
    definir('http://exemplo.invalido:9011');
    expect(porta()).toBe(9001);

    definir('https://127.0.0.1:9011');
    expect(porta()).toBe(9001);

    definir('http://127.0.0.1:9011');
    expect(porta()).toBe(9011);
  });

  it('base em `localhost` e a mesma coisa que em `127.0.0.1`', () => {
    definir('http://localhost:9011');
    expect(porta()).toBe(9011);
    expect(gatewayLocal(new URL('http://localhost:9011/api/account'))).toBe(true);
  });
});

describe('a base e resolvida ANTES de qualquer modulo que a congele', () => {
  beforeEach(() => {
    limpar();
    limparPortaWs();
    window.localStorage.clear();
  });
  afterEach(() => {
    limpar();
    limparPortaWs();
    vi.restoreAllMocks();
  });

  /*
    O DEFEITO, MEDIDO NA TELA
    =========================
    Logo apos a correcao da porta, a aba **Sistema** mostrava `GATEWAY OK` e o
    **Historico** mostrava `mt5: Failed to fetch` — na mesma janela, na mesma
    sessao. E nada escutava na 9001, que e o erro exato de um `fetch` sem dono.

    Nove arquivos guardam a base no topo do modulo (`const API = apiBase()`).
    `import` e hoisted: a linha roda no CARREGAMENTO, antes de o bootstrap
    resolver a porta. O resultado era `API` congelado em 9001 para sempre.

    Por que Sistema escapava: `SystemHealthOnly.tsx` chama `apiBase()` dentro da
    funcao, em tempo de execucao.

    O QUE ESTE TESTE FAZ
    ===================
    Nao mede texto. Carrega o app inteiro do jeito que o `main.tsx` carrega —
    `await import('./App')` DEPOIS da porta — e mede a URL que o historico
    realmente usa. Se a ordem voltar a ser "import estatico no topo", este
    teste reprova com `9001` na URL.
  */
  it('PROVA: depois de resolver a porta, o historico fala com a porta resolvida', async () => {
    definir('http://127.0.0.1:9011');

    const chamadas: string[] = [];
    vi.stubGlobal('fetch', (url: unknown) => {
      chamadas.push(String(url));
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ok: true, deals: [], connected: false }),
      });
    });

    const { useHistorico } = await import('./historico');
    // O caminho inteiro do historico: hook montado, fetch disparado.
    const { renderHook, waitFor } = await import('@testing-library/react');
    renderHook(() => useHistorico({ broker: 'mt5', days: '30', symbol: '' }));
    await waitFor(() => expect(chamadas.length).toBeGreaterThan(0));

    for (const url of chamadas) {
      expect(url, `historico falou com ${url}`).toContain('127.0.0.1:9011');
      expect(url, `historico falou com ${url}`).not.toContain(':9001');
    }
  });

  it('PROVA: nenhum modulo congela mais a base — a contagem zerou em 13/10/2026', async () => {
    /*
      NENHUM `const API = apiBase()` NO TOPO (13/10/2026).
      =====================================================
      MEDIDO nas capturas do dono (12:12, MT5 fechado): a aba Plano mostrava
      "Assinatura indisponível: Failed to fetch" e o journal "Spot/Futuros
      indisponível: Failed to fetch" — enquanto o grafico (que resolve a base
      por chamada) lia candles normalmente, na mesma janela, na mesma sessao.

      A CAUSA era esta lista: dez modulos congelavam `apiBase()` no
      carregamento, antes de o bootstrap resolver a porta. Com a base congelada
      na 9001 padrao — que e onde o terminal64 do MT5 escuta — o sintoma
      dependia do MT5: fechado, conexao recusada ("Failed to fetch"); aberto,
      outra resposta. O operador culpava o MT5 pelo que era ordem de
      carregamento do frontend (AGENTS.md 5).

      O corretivo: todos os dez resolvem `apiBase()` POR CHAMADA. Esta lista
      continua medida, nao lembrada: se um arquivo voltar a congelar, a
      contagem sai de zero e o teste reprova nomeando o arquivo.
    */
    // @ts-expect-error `node:fs` nao tem tipagem neste projeto
    const { readFileSync } = await import('node:fs');

    const suspeitos = [
      '../hooks/queries.ts',
      '../hooks/useAICommunication.ts',
      '../hooks/useEconomicData.ts',
      './connections.ts',
      './historico.ts',
      '../components/AutoEnginePanel.tsx',
      '../components/CopilotPanel.tsx',
      '../components/SeletorModelo.tsx',
      '../components/UniversalLiveTerminal.tsx',
      '../components/tabs/PortfolioHomeSafe.tsx',
    ];
    const achados: string[] = [];
    for (const arquivo of suspeitos) {
      const codigo = semComentarios(String(readFileSync(new URL(arquivo, import.meta.url), 'utf-8')));
      // O padrao exato do defeito: `const API = `${apiBase()}``. O regex
      // antigo (`const ...Api... =`) dava falso positivo em `const dadosApi`
      // (o payload do calendario) — media o NOME, nao o congelamento.
      if (/const\s+\w+\s*=\s*`\$\{apiBase\(\)\}`/.test(codigo)) achados.push(arquivo);
    }
    // A contagem e medida: se mudar, o numero do comentario precisa mudar.
    expect(achados.length, `voltaram a congelar a base: ${achados.join(', ')}`).toBe(0);

    // E, com a porta resolvida ANTES do import, a base deles e a nova.
    definir('http://127.0.0.1:9011');
    const { apiBase: base } = await import('./api');
    expect(base()).toBe('http://127.0.0.1:9011');
  });

  it('PROVA NEGATIVA: importando o App com a porta ja resolvida, nenhum modulo fica em 9001', async () => {
    /*
      A prova de que a correcao do `main.tsx` segura.

      Carrega o app do jeito que o bootstrap faz — porta primeiro — e mede a
      base de cada um dos nove. Com o `App` importado no TOPO do `main.tsx`, a
      base do `historico` seria 9001 e esta lista reprovaria.
    */
    definir('http://127.0.0.1:9011');

    const modulos = [
      './historico',
      './connections',
      '../hooks/queries',
      '../hooks/useAICommunication',
      '../hooks/useEconomicData',
    ];
    for (const m of modulos) {
      // Recarrega para simular o primeiro carregamento depois da porta.
      vi.resetModules();
      await import(m);
    }

    const { apiBase: base } = await import('./api');
    expect(base()).toBe('http://127.0.0.1:9011');
    // A base continua a resolvida DEPOIS de todos esses modulos carregarem.
    expect(base()).not.toContain(':9001');
  });
});

describe('a porta do WebSocket e MEDIDA — `porta_ws` nao pode ser um controle morto', () => {
  beforeEach(() => {
    limpar();
    limparPortaWs();
    window.localStorage.clear();
  });
  afterEach(() => {
    limpar();
    limparPortaWs();
  });

  it('sem o Tauri, a porta do WS e o padrao — o comportamento de antes', () => {
    expect(portaWsMercado()).toBe(9002);
    expect(wsUrl()).toBe('ws://127.0.0.1:9002/ws/market');
  });

  it('com `XAU_WS_PORT=9012`, a URL do preco segue a porta', () => {
    /*
      MEDIDO: `cargo check` acusava `porta_ws is never used`. O frontend tinha
      `ws://127.0.0.1:9002` escrito a mao e o Rust lia `XAU_WS_PORT`. Funcionava
      POR ACASO, porque os dois padroes eram o mesmo numero.

      No dia em que o dono movesse o WebSocket, o Rust subiria na 9012 e o
      `new WebSocket(getWsUrl())` de `useMarketWebSocket.ts:122` continuaria
      no 9002 — e o sintoma seria "o preco nao atualiza", SEM erro no console.
      Um websocket que nao conecta e um websocket que ninguem percebe quebrado.
    */
    definirPortaWs(9012);
    expect(portaWsMercado()).toBe(9012);
    expect(wsUrl()).toBe('ws://127.0.0.1:9012/ws/market');
  });

  it('PROVA NEGATIVA: porta invalida e porta zero nao viram a URL do preco', () => {
    /*
      `definirPortaWs` aceita intervalo valido. Um 0 viraria
      `ws://127.0.0.1:0/ws/market`, que o navegador recusa — e um prefixo de URL
      invalido viraria `ws://undefined/...`.
    */
    for (const invalida of [0, -1, 70000, Number.NaN, 1.5]) {
      limparPortaWs();
      definirPortaWs(invalida);
      expect(portaWsMercado(), `porta ${invalida} foi aceita`).toBe(9002);
    }
  });

  it('a URL explicita do operador continua valendo sobre a porta', () => {
    /*
      `stored('xau-ws-url')` e o ajuste em runtime, e a prioridade do codigo e
      do dono. A porta do Tauri nao pode atropelar uma escolha Feita na tela.
    */
    window.localStorage.setItem('xau-ws-url', 'wss://mercado.exemplo.com/ws');
    definirPortaWs(9012);
    expect(wsUrl()).toBe('wss://mercado.exemplo.com/ws');
  });
});