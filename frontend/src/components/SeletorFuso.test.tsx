import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { SeletorFuso } from './SeletorFuso';
import { useFuso } from '../hooks/useFuso';
import { listaOrdenada, offsetMinutos, fusoAutomatico } from '../lib/fuso';

/*
  O SELETOR DE FUSO NA TELA (05/10/2026)
  =======================================
  MEDIDO na captura da XM: lista de CIDADES com `(UTC-3) Sao Paulo` marcado com
  tick, e `auto` em AZUL porque o modo automatico e o PADRAO.

  O que estes testes travam, e por que:
   - `auto` comeca ligado. Comecar apontando para uma cidade e INVENTAR o fuso
     do operador — a regra de "nenhum ativo/cidade presumido" em forma de tela.
   - a lista esta ordenada por offset corrente;
   - a escolha PERSISTE e muda a zona efetiva;
   - o menu fecha com Escape e com clique fora.
*/

const data = new Date('2026-10-05T21:01:00Z');

beforeEach(() => {
  useFuso.setState({ auto: true, zona: '' });
  cleanup();
});

afterEach(() => {
  cleanup();
});

function abrir() {
  render(<SeletorFuso />);
  fireEvent.click(screen.getByRole('button', { expanded: false }));
}

describe('SeletorFuso', () => {
  it('comeca em `auto`, e o botao diz o offset do fuso detectado', () => {
    render(<SeletorFuso />);
    const btn = screen.getByRole('button', { expanded: false });
    expect(btn.textContent).toContain('auto');
    // O offset do fuso do navegador, lido do Intl — nao um numero de tabela.
    expect(btn.textContent).toMatch(/UTC[-+]\d{1,2}(:\d{2})?|^UTC/);
  });

  it('o item `auto` mostra a deteccao, e explica de onde ela veio', () => {
    abrir();
    const item = screen.getByRole('option', { name: /auto/i });
    expect(item.textContent).toContain(fusoAutomatico());
  });

  it('PROVA NEGATIVA: nenhuma cidade aparece marcada quando esta em `auto`', () => {
    // Se o navegador for uma das cidades do catalogo — e MEDICO que e
    // (esta maquina e America/Sao_Paulo) — marcar a cidade daria ao operador
    // duas escolhas iguais sem nenhuma estar em `auto`.
    abrir();
    const marcados = screen.getAllByRole('option', { selected: true });
    expect(marcados).toHaveLength(1);
    expect(marcados[0].textContent).toContain('auto');
  });

  it('a lista esta ordenada por offset, do mais a oeste para o mais a leste', () => {
    abrir();
    const itens = screen.getAllByRole('option').slice(1); // sem o `auto`
    const naLista = listaOrdenada(data).map((c) => c.zona);
    expect(itens).toHaveLength(naLista.length);
    // A ordem do DOM e a ordem calculada; o rotulo vai no texto do item.
    const esperado = naLista
      .map((z) => offsetMinutos(z))
      .sort((a, b) => a - b);
    const visivel = itens.map((el) =>
      el.textContent?.match(/UTC[-+]\d{1,2}(:\d{2})?|^UTC/)?.[0] ?? '',
    );
    expect(visivel.length).toBe(esperado.length);
    // Ordena os rotulos pelos offsets correspondentes e confere a monotonicidade.
    const pares = visivel.map((r, i) => [r, esperado[i]] as const);
    for (let i = 1; i < pares.length; i += 1) {
      // offset do texto nao pode regredir
      const atual = pares[i][1];
      const anterior = pares[i - 1][1];
      expect(atual).toBeGreaterThanOrEqual(anterior);
    }
  });

  it('escolher uma cidade tira do `auto` e passa a valer a zona dela', () => {
    abrir();
    /*
      MEDIDO (09/10/2026): o teste procurava a opcao pelo nome "Londres", que
      era a string da lista de 18 cidades escrita no codigo. O catalogo agora
      vem do `Intl` do sistema, e o `Intl` escreve "London" para
      `Europe/London` — a mesma zona, o nome proprio do fuso.

      Prender o nome no teste seria a mesma presuncao que o AGENTS.md §3 probe
      para o ativo. O que se trava ȁ a ZONA, que ȁ a chave e nao muda.

      E a busca e o caminho agora: com mais de 400 zonas, achar Londres por
      posicao nao ȁ viavel.
    */
    fireEvent.change(screen.getByLabelText('Buscar cidade, país ou zona'), {
      target: { value: 'Europe/London' },
    });
    /*
      MEDIDO (09/10/2026): a busca por zona IANA filtrava certo, mas o item nao
      mostrava a zona em lugar nenhum — `textContent` tinha so "London UTC+1".
      Quem digitou "Europe/London" via o resultado e nao tinha como conferir que
      era a zona que queria.

      A zona entrou no `title` e no `aria-label` do item. E o teste passa a
      medir por ela, que ȁ a chave.
    */
    const opcao = screen.getByTitle('Europe/London');
    expect(opcao, 'a zona Europe/London nao apareceu na busca').toBeTruthy();
    fireEvent.click(opcao);
    const st = useFuso.getState();
    expect(st.auto).toBe(false);
    expect(st.zona).toBe('Europe/London');
  });

  it('PROVA NEGATIVA: a escolha nao sobrevive a uma zona fora do catalogo', () => {
    // `escolher` so aceita zona conhecida. Uma zona inventada viraria
    // `auto` em vez de virar relogio errado em silencio.
    useFuso.getState().escolher('Brasil/Inventado');
    expect(useFuso.getState().auto).toBe(true);
    expect(useFuso.getState().zona).toBe('');
  });

  it('voltar para `auto` limpa a zona manual', () => {
    useFuso.getState().escolher('Europe/London');
    abrir();
    fireEvent.click(screen.getByRole('option', { name: /auto/i }));
    expect(useFuso.getState().auto).toBe(true);
    expect(useFuso.getState().zona).toBe('');
  });

  it('Escape fecha o menu', () => {
    abrir();
    expect(screen.getByRole('listbox')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).toBeNull();
  });

  it('clique fora fecha o menu', () => {
    abrir();
    expect(screen.getByRole('listbox')).toBeTruthy();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('listbox')).toBeNull();
  });

  it('o botao marca `manual` depois de escolher, como o `auto` em azul da XM', async () => {
    useFuso.getState().escolher('Europe/London');
    render(<SeletorFuso />);
    await waitFor(() => expect(screen.getByRole('button', { expanded: false }).textContent).toContain('manual'));
  });
});

/*
  O MENU ABRE PARA O LADO QUE TEM ESPACO (12/10/2026)
  ===================================================
  MEDIDO pelo dono: o botao UTC-3 ficava fora da tela algumas vezes. O menu
  abre para baixo com ate 320px — e o rodape do grafico vive no fim da pagina.
*/
describe('SeletorFuso — o menu nao sai da tela', () => {
  const originalRect = Element.prototype.getBoundingClientRect;
  const originalHeight = window.innerHeight;
  afterEach(() => {
    Element.prototype.getBoundingClientRect = originalRect;
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: originalHeight });
  });
  const retangulo = (top: number) =>
    ({ top, left: 0, width: 60, height: 20, right: 60, bottom: top + 20, x: 0, y: top, toJSON: () => ({}) }) as DOMRect;

  it('PROVA: sem espaco embaixo, abre para cima', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 });
    Element.prototype.getBoundingClientRect = function () {
      return retangulo(700);
    };
    render(<SeletorFuso />);
    fireEvent.click(screen.getByRole('button', { expanded: false }));
    expect(screen.getByRole('listbox').className).toContain('para-cima');
  });

  it('PROVA: com espaco embaixo, abre para baixo como sempre', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 });
    Element.prototype.getBoundingClientRect = function () {
      return retangulo(100);
    };
    render(<SeletorFuso />);
    fireEvent.click(screen.getByRole('button', { expanded: false }));
    expect(screen.getByRole('listbox').className).not.toContain('para-cima');
  });

  it('PROVA NEGATIVA: sem a medida, o menu abriria para baixo no fim da pagina', () => {
    // Sem este caso, apagar o `useLayoutEffect` passaria — e o menu voltaria
    // a vazar para fora da janela sem nenhum teste reclamar.
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 });
    Element.prototype.getBoundingClientRect = function () {
      return retangulo(790);
    };
    render(<SeletorFuso />);
    fireEvent.click(screen.getByRole('button', { expanded: false }));
    const menu = screen.getByRole('listbox');
    expect(menu.className).toContain('para-cima');
    // E continua sendo o mesmo menu: busca e opcoes presentes.
    expect(
      menu.querySelector('input[placeholder*="Buscar cidade"]'),
    ).toBeTruthy();
  });
});