// @vitest-environment jsdom
// Barra inferior estilo MT5 (05/10/2026).
//
// O DONO PEDIU
// ============
// "barra inferios sem fixo por ativos ou nomes, pesquisar esta melhorias
//  iguais a corretora usa, botoes com uso essencial alinhados compactos"
//
// O QUE A PESQUISA DO MT5 DEU
// ============================
// A barra de status do MT5 fica ABAIXO de todas as janelas e é uma faixa fina.
// Da esquerda para a direita: dica do comando, perfil, OHLC do ponto sob o
// cursor, INDICADOR DE CONEXÃO ao servidor, tráfego da sessão.
//
// Duas decisões tiradas daí:
//   - o indicador de conexão é um MARCADOR, não uma frase. "Tempo real" ocupa
//     70 px para dizer o que um ponto verde já diz;
//   - a faixa é fina, porque o que fica nela é REFERÊNCIA, não leitura. O
//     operador olha quando precisa, não enquanto opera.
//
// ANTES DE ESTA VERSÃO
// ====================
// Dois botões com rótulo ("Ativo" e "TF"), e o `window.prompt` para trocar o
// par. O prompt é bloqueante, some atrás da janela do navegador e não aceita
// colar com o botão direito — e trocar de par é a ação mais frequente.
//
// ESTES TESTES TRAVAM O COMPORTAMENTO, NÃO A APARÊNCIA
// =====================================================
// CSS não é testável aqui (vitest não aplica folha em jsdom), então o que se
// fixa é: o que a barra FAZ, o que ela DIZ e o que ela NÃO diz.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const chamadas: Array<{ url: string; body: Record<string, unknown> }> = [];

const estado = vi.hoisted(() => ({
  auto: { ativo: false, simbolo: 'GOLD', timeframe: 'H1' } as Record<string, unknown>,
  ws: true,
  simbolo: 'GOLD',
}));

vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({ data: estado.auto, refetch: async () => {} }),
}));

vi.mock('../hooks/useAppStore', () => ({
  useAppStore: (seletor: (s: unknown) => unknown) =>
    seletor({
      wsConnected: estado.ws,
      selectedSymbol: estado.simbolo,
      setSelectedSymbol: (v: string) => {
        estado.simbolo = v;
      },
    }),
}));

vi.mock('./LatenciaBar', () => ({
  default: (p: { ativa?: string }) => <div data-testid="latencias" data-ativa={p.ativa ?? ''} />,
}));

const { default: StatusBar } = await import('./StatusBar');

beforeEach(() => {
  chamadas.length = 0;
  estado.auto = { ativo: false, simbolo: 'GOLD', timeframe: 'H1' };
  estado.ws = true;
  estado.simbolo = 'GOLD';
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    chamadas.push({ url: String(url), body: JSON.parse(String(init?.body ?? '{}')) });
    if (String(url).includes('/api/ai/trained')) {
      return {
        ok: true,
        json: async () => ({
          models: [
            { symbol: 'BTCUSD', timeframe: 'H1', pkl_present: true, publicable: true },
            { symbol: 'BTCUSD', timeframe: 'H4', pkl_present: true, publicable: true },
            { symbol: 'ETHUSD', timeframe: 'H1', pkl_present: true, publicable: true },
            { symbol: 'XAGUSD', timeframe: 'H4', pkl_present: false, publicable: false },
            { symbol: '', timeframe: 'H1', pkl_present: true, publicable: true },
          ],
        }),
      };
    }
    return { ok: true, json: async () => ({ ok: true }) };
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** Abre a lista pelo botão do símbolo+timeframe. */
async function abrir() {
  fireEvent.click(document.querySelector('.status-simbolo') as HTMLButtonElement);
  await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeTruthy());
}

describe('StatusBar — um item para ativo e timeframe', () => {
  it('mostra os dois no mesmo botao, sem rotulo', () => {
    const { container } = render(<StatusBar />);
    const botao = container.querySelector('.status-simbolo') as HTMLElement;
    expect(botao.textContent).toContain('GOLD');
    expect(botao.textContent).toContain('H1');
    // "Ativo" e "TF" sairam: o valor ja diz o que e, e o MT5 nao escreve
    // "Symbol:" nem "Period:" na barra.
    expect(botao.textContent).not.toContain('Ativo');
    expect(container.querySelector('.status-rotulo')).toBeNull();
  });

});

describe('StatusBar — trocar o ativo pela LISTA (25/10/2026)', () => {
  /*
    PEDIDO DO DONO: "remover barra de pesquisar ativo na parte inferior do app,
    manter apenas uma lista e os modelos validar real todos". O campo digitavel
    aceitava qualquer simbolo (§3: nenhum ativo e presumido; quem lista e a
    corretora). A lista vem de `/api/ai/trained` e cada modelo MarCA o que e:
    `real` (artefato no disco) ou `sem artefato` (nao operavel).
  */
  it('PROVA NEGATIVA: nao existe mais campo de texto para digitar simbolo', async () => {
    render(<StatusBar />);
    await abrir();
    expect(document.getElementById('status-ativo-campo')).toBeNull();
    expect(document.querySelector('.status-tf-ativo-input')).toBeNull();
  });

  it('a lista traz os modelos reais de /api/ai/trained, um por par', async () => {
    render(<StatusBar />);
    await abrir();
    await waitFor(() => expect(document.querySelectorAll('.status-ativo-item').length).toBeGreaterThan(0));
    const nomes = Array.from(document.querySelectorAll('.status-ativo-item')).map(
      (n) => n.querySelector('.status-tf-nome')?.textContent,
    );
    expect(new Set(nomes).size).toBe(nomes.length);
    expect(nomes).toContain('BTCUSD');
  });

  it('modelo SEM artefato nao e operavel e diz a falta', async () => {
    render(<StatusBar />);
    await abrir();
    await waitFor(() =>
      expect(document.querySelector('.status-ativo-item.sem-disco')).toBeTruthy(),
    );
    const morto = document.querySelector('.status-ativo-item.sem-disco') as HTMLButtonElement;
    expect(morto.disabled).toBe(true);
    expect(morto.textContent).toContain('sem artefato');
  });

  it('PROVA: clicar no par real busca o motor com SO o simbolo', async () => {
    render(<StatusBar />);
    await abrir();
    const item = await waitFor(() =>
      (
        Array.from(document.querySelectorAll('.status-ativo-item')).find(
          (n) => n.querySelector('.status-tf-nome')?.textContent === 'BTCUSD',
        ) ?? null
      ) as HTMLButtonElement | null,
    );
    fireEvent.click(item!);
    await waitFor(() => {
      const cfg = chamadas.find((c) => c.url.includes('/api/auto/config'));
      expect(cfg?.body).toEqual({ simbolo: 'BTCUSD' });
    });
    expect(estado.simbolo).toBe('BTCUSD');
  });

  it('PROVA NEGATIVA: par em uso sem modelo continua na lista', async () => {
    render(<StatusBar />);
    await abrir();
    await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeTruthy());
    const atual = document.querySelector('.status-tf-atual') as HTMLElement;
    expect(atual.textContent).toContain('GOLD');
    expect(atual.textContent).toContain('em uso');
  });
});

describe('StatusBar — o timeframe', () => {
  /** Espera a lista de MODELOS carregar, e devolve os itens de TIMEFRAME. */
  async function abreComModelos() {
    render(<StatusBar />);
    await abrir();
    await waitFor(() => expect(document.querySelectorAll('.status-ativo-item').length).toBe(3));
    return Array.from(document.querySelectorAll('.status-tf-item:not(.status-ativo-item)'));
  }

  it('a lista tem os 7 timeframes que o MT5 le', async () => {
    // So os que o MT5 sabe ler. O backend recusa o resto, e botao que nao
    // funciona e pior que botao ausente.
    const opcoes = await abreComModelos();
    expect(opcoes.length).toBe(7);
    const nomes = opcoes.map((n) => n.querySelector('.status-tf-nome')?.textContent);
    expect(nomes).toEqual(['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']);
  });

  it('marca o que o modelo aceita e o que e so grafico', async () => {
    // `TIMEFRAMES_VALIDOS` em `ai_inference.py` = M5, M15, H1, H4. M1, M30 e
    // D1 o MT5 le, mas a inferencia recusa. Escolher D1 sem aviso ligaria um
    // motor que nao infere.
    await abreComModelos();
    const soGrafico = Array.from(document.querySelectorAll('.status-tf-item.so-grafico')).map(
      (n) => n.querySelector('.status-tf-nome')?.textContent,
    );
    expect(soGrafico.sort()).toEqual(['D1', 'M1', 'M30']);
  });

  it('manda SO o timeframe — nao toca em lote, SL e TP', async () => {
    // `configurar()` mescla campo a campo. Enviar o resto sobrescreveria a
    // protecao que o operador configurou, sem ele ter pedido.
    await abreComModelos();
    const d1 = Array.from(document.querySelectorAll('.status-tf-item:not(.status-ativo-item)')).find(
      (n) => n.querySelector('.status-tf-nome')?.textContent === 'D1',
    ) as HTMLButtonElement;
    fireEvent.click(d1);
    await waitFor(() => {
      const configs = chamadas.filter((c) => c.url.includes('/api/auto/config'));
      expect(configs.length).toBe(1);
      expect(configs[0].body).toEqual({ timeframe: 'D1' });
    });
    for (const campo of ['lote', 'sl_preco', 'tp_preco', 'simbolo', 'broker', 'market']) {
      expect(campo in chamadas.find((c) => c.url.includes('/api/auto/config'))!.body).toBe(false);
    }
  });

  it('nao chama o gateway ao escolher o timeframe que ja esta', async () => {
    await abreComModelos();
    const h1 = Array.from(document.querySelectorAll('.status-tf-item:not(.status-ativo-item)')).find(
      (n) => n.querySelector('.status-tf-nome')?.textContent === 'H1',
    ) as HTMLButtonElement;
    fireEvent.click(h1);
    await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeNull());
    expect(chamadas.filter((c) => c.url.includes('/api/auto/config')).length).toBe(0);
  });

  it('a lista fecha no Escape', async () => {
    render(<StatusBar />);
    await abrir();
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeNull());
  });
});

describe('StatusBar — o ponto de conexao', () => {
  it('mostra o ponto e NAO a frase visivel', () => {
    // Na barra do MT5 o indicador de conexao e um marcador. "Tempo real"
    // ocupa 70 px para dizer o que um ponto verde ja diz.
    const { container } = render(<StatusBar />);
    const conexao = container.querySelector('.status-conexao') as HTMLElement;

    // O que o olho le: o texto FORA do `.sr-only`. Conferir `textContent`
    // inteiro reprovaria por causa do texto de acessibilidade, e esse e
    // justamente o texto que tem de estar la.
    const visivel = Array.from(conexao.childNodes)
      .filter((n) => !(n instanceof HTMLElement && n.classList.contains('sr-only')))
      .map((n) => n.textContent ?? '')
      .join('')
      .trim();
    expect(visivel).toBe('');
    expect(conexao.querySelector('.status-ponto')).toBeTruthy();
  });

  it('a frase continua no title e para o leitor de tela', () => {
    // Perder a informacao para o olho e ganho; perder para o leitor de tela
    // seria defeito.
    const { container } = render(<StatusBar />);
    const conexao = container.querySelector('.status-conexao') as HTMLElement;
    expect(conexao.getAttribute('title')).toContain('Tempo real conectado');
    expect(conexao.querySelector('.sr-only')?.textContent).toContain('Tempo real conectado');
  });

  it('muda de estado quando o tempo real cai', () => {
    estado.ws = false;
    const { container } = render(<StatusBar />);
    const conexao = container.querySelector('.status-conexao') as HTMLElement;
    expect(conexao.className).toContain('is-warn');
    expect(conexao.getAttribute('title')).toContain('Reconectando');
  });
});

describe('StatusBar � o par da barra configura o motor', () => {
  it('PROVA: clicar num par da lista avisa o motor com SO o simbolo', async () => {
    // MEDIDO na captura (par EURUSD na barra, grafico em BTCUSD): a barra
    // gravava so a tela. Agora o gesto configura, e `configurar` mescla —
    // lote, SL, TP e timeframe ficam como estao.
    render(<StatusBar />);
    await abrir();
    const item = await waitFor(() =>
      (
        Array.from(document.querySelectorAll('.status-ativo-item')).find(
          (n) => n.querySelector('.status-tf-nome')?.textContent === 'ETHUSD',
        ) ?? null
      ) as HTMLButtonElement | null,
    );
    fireEvent.click(item!);
    await waitFor(() => {
      const cfg = chamadas.find((c) => String(c.url).includes('/api/auto/config'));
      expect(cfg?.body).toEqual({ simbolo: 'ETHUSD' });
    });
    expect(estado.simbolo).toBe('ETHUSD');
  });

  it('PROVA NEGATIVA: par igual ao da lista nao chama o gateway', async () => {
    estado.simbolo = 'ETHUSD';
    render(<StatusBar />);
    await abrir();
    await waitFor(() => expect(document.querySelectorAll('.status-ativo-item').length).toBe(3));
    const item = Array.from(document.querySelectorAll('.status-ativo-item')).find(
      (n) => n.querySelector('.status-tf-nome')?.textContent === 'ETHUSD',
    ) as HTMLButtonElement | null;
    expect(item).toBeTruthy();
    fireEvent.click(item!);
    await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeNull());
    expect(chamadas.filter((c) => String(c.url).includes('/api/auto/config')).length).toBe(0);
  });
});

