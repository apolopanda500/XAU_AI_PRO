/*
  O MENU DO BOTAO DIREITO DO GRAFICO (09/10/2026, AMPLIADO 11/11/2026)
  =====================================================================
  MEDIDO na captura da XM (`Screenshot 2026-10-09 201959.png`): o clique com
  o botao direito dentro do grafico abre um menu com TRADE no topo, um
  separador, e abaixo propriedades, arquivos, opcoes e linhas de estudo.

  O DONO PEDIU, textualmente: "quando tem direito tem que abrir todas funcoes
  do menu". Hoje o clique direito aqui abre o menu do proprio navegador
  (Recarregar, Inspecionar...), que e o menu DO WEBVIEW, nao o do grafico — e
  nao tem nenhuma funcao de operacao.

  O QUE ENTRA, E O QUE NAO ENTRA
  ===============================
  Entra o que a captura mostra e que ESTE app tem como responder:

    TRADE   -> o que mexe dinheiro. Primeiro item, como na XM.
               - comprar / vender: so armam a ordem na tela, NAO enviam.
                 `onOperar` e quem decide, e ele e o mesmo do botao da mesa:
                 armar exige nivel e confirmacao, e nada sai so pelo clique.
               - stop loss / take profit: veem abaixo.
    VER     -> zoom e ajustar a janela, sem tocar em ordem nenhuma.
    PERIODO -> os 9 timeframes que o gateway aceita (`_TIMEFRAME_MAP`), com o
               atual marcado. E o mesmo `changeTimeframe` da barra de baixo:
               dois caminhos, um so consumidor.
    EXIBIR  -> grade e volumes, ligados/desligados com `aria-pressed`.

  DESENHAR e LIMPAR SAIRAM (11/10/2026, decisao do dono: o grafico e para
  colocar ordens, nao para editar/estudar/analisar). Ver `PriceChart` acima
  de `acaoDoMenu`.

  Nao entra:
    - "Propriedades", "Arquivos", "Opcoes": sao menu da PLATAFORMA XM, e este
      app e o XAU AI PRO. Copiar o rotulo sem a funcao e exatamente o defeito
      que o AGENTS.md §9 descreve — controle que o operador acredita ter.
    - "Salvar como imagem": o navegador ja oferece, e um menu que duplica o
      do sistema e ruido.

  OS ATALHOS DA COLUNA `kbd` AGORA EXISTEM (11/11/2026)
  ------------------------------------------------------
  MEDIDO antes: `B`, `S`, `T`, `P`, `+` e `-` apareciam no menu e NENHUM
  teclado era ouvido — o rótulo prometia e o handler nao existia, o defeito
  que o AGENTS.md §9 chama de "controle sem consumidor". Agora, com o menu
  ABERTO, a tecla escolhe o item e fecha o menu, exatamente como o clique.
  O atalho vive enquanto o item esta na tela (e e ele que o mostra).

  POR QUE UM COMPONENTE SO
  ========================
  O menu precisa saber ONDE o clique caiu (o preco, para o stop) e O QUE fazer.
  As duas coisas vem de fora: `PriceChart` tem a serie e converte pixel em
  preco, e quem opera e a mesa. Este componente so desenha a lista e devolve o
  que foi escolhido.
*/
import { useEffect, useRef, useState } from 'react';
import { TIMEFRAMES, type ChartTimeframe } from './timeframes';

export type AcaoDoMenu =
  | 'operar-compra'
  | 'operar-venda'
  | 'stop'
  | 'alvo'
  | 'zoom-mais'
  | 'zoom-menos'
  | 'ajustar'
  | 'ir-para-agora'
  | 'copiar-preco'
  | 'tela-cheia'
  | 'timeframe'
  | 'grade'
  | 'volumes';

type Item = {
  chave: AcaoDoMenu;
  rotulo: string;
  /*
    A acao perigosa fica vermelha, e e a unica cor do menu.

    MEDIDO: um menu todo em vermelho nao distingue nada, e um menu todo cinza
    esconde a acao que move dinheiro. Na XM o TRADE e a area de cor propria.
  */
  perigosa?: boolean;
  atalho?: string;
  /** O valor da acao quando o rotulo nao e o dado (timeframes). */
  valor?: string;
  /** Estado de um item que Liga/Desliga: vira `aria-pressed`. */
  ativo?: boolean;
};

/** O bloco que move dinheiro. Fica primeiro, como na captura da XM. */
const TRADE: Item[] = [
  { chave: 'operar-compra', rotulo: 'Comprar', perigosa: true, atalho: 'B' },
  { chave: 'operar-venda', rotulo: 'Vender', perigosa: true, atalho: 'S' },
  { chave: 'stop', rotulo: 'Stop loss no ponto', atalho: 'T' },
  { chave: 'alvo', rotulo: 'Take profit no ponto', atalho: 'P' },
];

/** O que muda a VISTA, sem tocar em ordem nenhuma. */
const VISUAL: Item[] = [
  { chave: 'zoom-mais', rotulo: 'Aproximar', atalho: '+' },
  { chave: 'zoom-menos', rotulo: 'Afastar', atalho: '-' },
  { chave: 'ajustar', rotulo: 'Ajustar a janela' },
  { chave: 'ir-para-agora', rotulo: 'Ir para o preco atual' },
  { chave: 'tela-cheia', rotulo: 'Tela cheia' },
  { chave: 'copiar-preco', rotulo: 'Copiar preco do ponto' },
];

/** O que Liga/Desliga a tela: so tem consumidor quando existe de verdade. */
const EXIBIR_BASE: Array<Pick<Item, 'chave' | 'rotulo'>> = [
  { chave: 'grade', rotulo: 'Grade' },
  { chave: 'volumes', rotulo: 'Volumes' },
];

/**
  O que a tecla faz com o menu ABERTO. O `=` e o `+` da mesma tecla sem Shift,
  e o `_` e o `-` com Shift: quem aperta Shift para escrever `-` nao pode ficar
  sem a acao que o proprio menu promete.
*/
const ATALHOS: Record<string, AcaoDoMenu> = {
  b: 'operar-compra',
  s: 'operar-venda',
  t: 'stop',
  p: 'alvo',
  '+': 'zoom-mais',
  '=': 'zoom-mais',
  '-': 'zoom-menos',
  _: 'zoom-menos',
};

export type MenuGraficoProps = {
  aberto: boolean;
  /** Posicao em px, relativa ao container do grafico. */
  x: number;
  y: number;
  /** O preco onde o clique caiu, ou `null` se a serie nao respondeu. */
  precoNoPonto: number | null;
  aoEscolher: (acao: AcaoDoMenu, preco: number | null, valor?: string) => void;
  aoFechar: () => void;
  /** O timeframe ligado agora, para MARCAR no bloco PERIODO. */
  timeframeAtual: ChartTimeframe;
  /** Estado da grade e dos volumes, para o `aria-pressed` do bloco EXIBIR. */
  grade: boolean;
  volumes: boolean;
};

export default function MenuGrafico({
  aberto,
  x,
  y,
  precoNoPonto,
  aoEscolher,
  aoFechar,
  timeframeAtual,
  grade,
  volumes,
}: MenuGraficoProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [altura, setAltura] = useState(0);

  /*
    FECHAR NO CLIQUE FORA E NO ESC — E AS TECLAS DO MENU.

       O `mousedown` e nao o `click`: no `click` o menu ja fechou antes de o
    alvo receber o evento, e o operador clica no item e nao acontece nada.

    MESMA REGRA PARA A TECLA: o handler chama `aoEscolher` e `aoFechar` na
    mesma ordem do clique. Tecla que so fecha sem escolher parece item morto.
  */
  useEffect(() => {
    if (!aberto) return undefined;
    const fora = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) aoFechar();
    };
    const teclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        aoFechar();
        return;
      }
      // Atalho com Ctrl/Alt/Shift nao e o atalho do menu: e do navegador ou
      // do sistema, e o menu nao pode sequestrar `Ctrl + S` (salvar pagina).
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const acao = ATALHOS[e.key.toLowerCase()];
      if (!acao) return;
      e.preventDefault();
      e.stopPropagation();
      aoEscolher(acao, precoNoPonto);
      aoFechar();
    };
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', teclar);
    return () => {
      document.removeEventListener('mousedown', fora);
      document.removeEventListener('keydown', teclar);
    };
  }, [aberto, aoFechar, aoEscolher, precoNoPonto]);

  /*
    O MENU NAO SAI DA TELA (09/10/2026)
    ===================================
    MEDIDO na captura de 20:37: com o clique perto da borda, o menu aparecia
    cortado — e os itens de baixo (LIMPAR) ficavam inalcancaveis. Um menu com
    item inalcancavel e o mesmo defeito do icone invisivel: o operador nao
    pode usar o que nao ve.

    A medida Ȩ a altura real depois de montar, e o reposicionamento Ȩ para
    dentro. `altura` comeca em zero e so Ȩ lida depois do primeiro render.

    COM OS 4 BLOCOS O MENU FICOU MAIS ALTO QUE A TELA (11/11/2026): 21 itens.
    O `.menu-grafico` ja tem `max-height: calc(100% - 8px); overflow-y: auto`
    (menu-grafico.css), entao a altura MEDIDA e sempre no maximo a do grafico —
    o `top` abaixo nunca e empurrado para fora por um menu gigante.
  */
  useEffect(() => {
    if (aberto && ref.current) setAltura(ref.current.offsetHeight);
  }, [aberto, x, y]);

  if (!aberto) return null;

  const bloco = (itens: Item[]) => (
    <>
      {itens.map((item) => (
        <button
          key={`${item.chave}:${item.valor ?? ''}`}
          type="button"
          className={`menu-grafico-item${item.perigosa ? ' perigosa' : ''}`}
          aria-pressed={item.ativo}
          onClick={() => {
            aoEscolher(item.chave, precoNoPonto, item.valor);
            aoFechar();
          }}
        >
          <span>{item.rotulo}</span>
          {item.atalho && <kbd>{item.atalho}</kbd>}
        </button>
      ))}
    </>
  );

  const periodo: Item[] = TIMEFRAMES.map((tf) => ({
    chave: 'timeframe' as const,
    rotulo: tf,
    valor: tf,
    ativo: tf === timeframeAtual,
  }));
  const exibir: Item[] = EXIBIR_BASE.map((base) => ({
    ...base,
    ativo: base.chave === 'grade' ? grade : volumes,
  }));

  return (
    <div
      ref={ref}
      className="menu-grafico"
      role="menu"
      aria-label="Menu do gráfico"
      style={{
        left: Math.max(4, Math.min(x, window.innerWidth - 232)),
        top: Math.max(4, Math.min(y, window.innerHeight - (altura || 320) - 8)),
      }}
    >
      <div className="menu-grafico-titulo" role="presentation">
        TRADE
      </div>
      {bloco(TRADE)}
      <div className="menu-grafico-sep" role="presentation" />
      <div className="menu-grafico-titulo" role="presentation">
        VER
      </div>
      {bloco(VISUAL)}
      <div className="menu-grafico-sep" role="presentation" />
      <div className="menu-grafico-titulo" role="presentation">
        PERIODO
      </div>
      {bloco(periodo)}
      <div className="menu-grafico-sep" role="presentation" />
      <div className="menu-grafico-titulo" role="presentation">
        EXIBIR
      </div>
      {bloco(exibir)}
    </div>
  );
}
