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

vi.mock('./LatenciaBar', () => ({ default: () => <div data-testid="latencias" /> }));

const { default: StatusBar } = await import('./StatusBar');

beforeEach(() => {
  chamadas.length = 0;
  estado.auto = { ativo: false, simbolo: 'GOLD', timeframe: 'H1' };
  estado.ws = true;
  estado.simbolo = 'GOLD';
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    chamadas.push({ url: String(url), body: JSON.parse(String(init?.body ?? '{}')) });
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

  it('a latencia fica no lado direito, como no MT5', () => {
    const { container } = render(<StatusBar />);
    const direita = container.querySelector('.status-bar-dir') as HTMLElement;
    expect(direita.querySelector('[data-testid="latencias"]')).toBeTruthy();
    const esquerda = container.querySelector('.status-bar-esq') as HTMLElement;
    expect(esquerda.querySelector('[data-testid="latencias"]')).toBeNull();
  });
});

describe('StatusBar — trocar o ativo sem prompt', () => {
  it('o campo de texto esta no topo da lista', async () => {
    // O `window.prompt` era bloqueante, somia atras da janela do navegador e
    // nao aceitava colar com o botao direito.
    render(<StatusBar />);
    await abrir();
    const campo = document.getElementById('status-ativo-campo') as HTMLInputElement;
    expect(campo).toBeTruthy();
    expect(campo.value).toBe('GOLD');
    // Com foco: quem abriu a lista quer digitar.
    expect(document.activeElement).toBe(campo);
  });

  it('Enter grava o par em maiuscula e fecha a lista', async () => {
    render(<StatusBar />);
    await abrir();
    const campo = document.getElementById('status-ativo-campo') as HTMLInputElement;
    fireEvent.change(campo, { target: { value: '  btcusdt ' } });
    fireEvent.keyDown(campo, { key: 'Enter' });
    await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeNull());
    expect(estado.simbolo).toBe('BTCUSDT');
  });

  it('campo em branco nao apaga o par', async () => {
    render(<StatusBar />);
    await abrir();
    const campo = document.getElementById('status-ativo-campo') as HTMLInputElement;
    fireEvent.change(campo, { target: { value: '   ' } });
    fireEvent.keyDown(campo, { key: 'Enter' });
    await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeNull());
    expect(estado.simbolo).toBe('GOLD');
  });
});

describe('StatusBar — o timeframe', () => {
  it('a lista tem os 7 timeframes que o MT5 le', async () => {
    render(<StatusBar />);
    await abrir();
    const opcoes = document.querySelectorAll('.status-tf-item');
    // So os que o MT5 sabe ler. O backend recusa o resto, e botao que nao
    // funciona e pior que botao ausente.
    expect(opcoes.length).toBe(7);
    const nomes = Array.from(opcoes).map((n) => n.querySelector('.status-tf-nome')?.textContent);
    expect(nomes).toEqual(['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']);
  });

  it('marca o que o modelo aceita e o que e so grafico', async () => {
    // `TIMEFRAMES_VALIDOS` em `ai_inference.py` = M5, M15, H1, H4. M1, M30 e
    // D1 o MT5 le, mas a inferencia recusa. Escolher D1 sem aviso ligaria um
    // motor que nao infere.
    render(<StatusBar />);
    await abrir();
    const soGrafico = Array.from(document.querySelectorAll('.status-tf-item.so-grafico')).map(
      (n) => n.querySelector('.status-tf-nome')?.textContent,
    );
    expect(soGrafico.sort()).toEqual(['D1', 'M1', 'M30']);
  });

  it('manda SO o timeframe — nao toca em lote, SL e TP', async () => {
    // `configurar()` mescla campo a campo. Enviar o resto sobrescreveria a
    // protecao que o operador configurou, sem ele ter pedido.
    render(<StatusBar />);
    await abrir();
    const d1 = Array.from(document.querySelectorAll('.status-tf-item')).find(
      (n) => n.querySelector('.status-tf-nome')?.textContent === 'D1',
    ) as HTMLButtonElement;
    fireEvent.click(d1);
    await waitFor(() => expect(chamadas.length).toBe(1));
    expect(chamadas[0].url).toContain('/api/auto/config');
    expect(chamadas[0].body).toEqual({ timeframe: 'D1' });
    for (const campo of ['lote', 'sl_preco', 'tp_preco', 'simbolo', 'broker', 'market']) {
      expect(campo in chamadas[0].body).toBe(false);
    }
  });

  it('nao chama o gateway ao escolher o timeframe que ja esta', async () => {
    render(<StatusBar />);
    await abrir();
    const h1 = Array.from(document.querySelectorAll('.status-tf-item')).find(
      (n) => n.querySelector('.status-tf-nome')?.textContent === 'H1',
    ) as HTMLButtonElement;
    fireEvent.click(h1);
    await waitFor(() => expect(document.querySelector('.status-tf-lista')).toBeNull());
    expect(chamadas.length).toBe(0);
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
