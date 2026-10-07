/**
 * O que o jsdom NAO tem e o navegador tem (06/10/2026).
 *
 * POR QUE ISTO EXISTE
 * ===================
 * `lightweight-charts` (usado pelo `PriceChart`) chama `window.matchMedia` no
 * momento em que cria o canvas, para descobrir a densidade de pixels do
 * dispositivo. O jsdom nao implementa `matchMedia`, e a tela inteira quebra com
 * `TypeError: this._window.matchMedia is not a function` — um erro de
 * AMBIENTE, nao de codigo, que reprova o teste antes de o componente rodar.
 *
 * Antes deste arquivo, nenhum teste renderizava o `PriceChart`: o
 * `PriceChart.indicadores.test.ts` exercita so `emaValores`, `rsiValores` e
 * `macdValores`, que sao FUNCOES PURAS e nao tocam no canvas. O primeiro teste
 * que renderiza o grafico descoberta que faltava a base.
 *
 * E UM DUBLE DE AMBIENTE, NAO DE COMPORTAMENTO
 * =============================================
 * Nenhum deste duble devolve dado de negocio. `matchMedia` responde sobre o
 * TAMANHO DA JANELA, e o grafico so usa isso para decidir quantos pixels de
 * aparelho cada pixel de tela ocupa. Um `addListener` faltando derrubaria o
 * grafico em TODO teste, e o conserto e completar a API — nao mudar o que o
 * componente le.
 *
 * `ResizeObserver`: o grafico observa o tamanho do proprio container para
 * redimensionar. O jsdom nao tem, e sem ele o `observe()` lanca
 * `TypeError: ResizeObserver is not defined`.
 */

/** `matchMedia` que respondepelos mesmos criteria de um navegador. */
function instalarMatchMedia(): void {
  if (typeof window === 'undefined') return;
  if (typeof window.matchMedia === 'function') return;

  window.matchMedia = ((consulta: string): MediaQueryList => {
    // As consultas que a biblioteca usa sao de largura e de preferencia de
    // movimento. O detalhe do resultado importa menos que a EXISTENCIA do
    // objeto com `matches` e `addEventListener`, que e o que a biblioteca
    // consome.
    const largura = typeof window.innerWidth === 'number' ? window.innerWidth : 1280;
    const altura = typeof window.innerHeight === 'number' ? window.innerHeight : 720;
    let corresponde = false;
    const min = /\(min-width:\s*(\d+)px\)/.exec(consulta);
    const max = /\(max-width:\s*(\d+)px\)/.exec(consulta);
    if (min) corresponde = largura >= Number(min[1]);
    if (max) corresponde = corresponde && largura <= Number(max[1]);

    const ouvintes = new Set<(evento: MediaQueryListEvent) => void>();
    return {
      matches: corresponde,
      media: consulta,
      onchange: null,
      addEventListener: (_tipo: string, ouvinte: (evento: MediaQueryListEvent) => void) => {
        ouvintes.add(ouvinte);
      },
      removeEventListener: (_tipo: string, ouvinte: (evento: MediaQueryListEvent) => void) => {
        ouvintes.delete(ouvinte);
      },
      addListener: (ouvinte: (evento: MediaQueryListEvent) => void) => {
        ouvintes.add(ouvinte);
      },
      removeListener: (ouvinte: (evento: MediaQueryListEvent) => void) => {
        ouvintes.delete(ouvinte);
      },
      dispatchEvent: () => false,
    } as unknown as MediaQueryList;
  }) as typeof window.matchMedia;
}

/** `ResizeObserver` que nao observa nada e nao lanca. */
function instalarResizeObserver(): void {
  if (typeof globalThis === 'undefined') return;
  if (typeof (globalThis as { ResizeObserver?: unknown }).ResizeObserver === 'function') return;

  class ResizeObserverDuble {
    observe(): void {
      /* sem observacao de verdade: o teste nao mede layout */
    }
    unobserve(): void {
      /* idem */
    }
    disconnect(): void {
      /* idem */
    }
  }

  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = ResizeObserverDuble;
}

instalarMatchMedia();
instalarResizeObserver();