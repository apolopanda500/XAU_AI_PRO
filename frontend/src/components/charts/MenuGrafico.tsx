/*
  O MENU DO BOTAO DIREITO DO GRAFICO (09/10/2026)
  ===============================================
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

    TRADE  -> o que mexe dinheiro. Primeiro item, como na XM.
              - comprar / vender: so armam a ordem na tela, NAO enviam.
                `onOperar` e quem decide, e ele e o mesmo do botao da mesa:
                armar exige nivel e confirmacao, e nada sai so pelo clique.
              - stop loss / take profit: veem abaixo.
    VER    -> zoom e ajustar a janela, sem tocar em ordem nenhuma.

  DESENHAR e LIMPAR SAIRAM (11/10/2026, decisao do dono: o grafico e para
  colocar ordens, nao para editar/estudar/analisar). Ver `PriceChart` acima
  de `acaoDoMenu`.

  Nao entra:
    - "Propriedades", "Arquivos", "Opcoes": sao menu da PLATAFORMA XM, e este
      app e o XAU AI PRO. Copiar o rotulo sem a funcao e exatamente o defeito
      que o AGENTS.md §9 descreve — controle que o operador acredita ter.
    - "Salvar como imagem": o navegador ja oferece, e um menu que duplica o
      do sistema e ruido.

  POR QUE UM COMPONENTE SO
  ========================
  O menu precisa saber ONDE o clique caiu (o preco, para o stop) e O QUE fazer.
  As duas coisas vem de fora: `PriceChart` tem a serie e converte pixel em
  preco, e quem opera e a mesa. Este componente so desenha a lista e devolve o
  que foi escolhido.
*/
import { useEffect, useRef, useState } from 'react';

export type AcaoDoMenu =
  | 'operar-compra'
  | 'operar-venda'
  | 'stop'
  | 'alvo'
  | 'zoom-mais'
  | 'zoom-menos'
  | 'ajustar';

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
];

export type MenuGraficoProps = {
  aberto: boolean;
  /** Posicao em px, relativa ao container do grafico. */
  x: number;
  y: number;
  /** O preco onde o clique caiu, ou `null` se a serie nao respondeu. */
  precoNoPonto: number | null;
  aoEscolher: (acao: AcaoDoMenu, preco: number | null) => void;
  aoFechar: () => void;
};

export default function MenuGrafico({
  aberto,
  x,
  y,
  precoNoPonto,
  aoEscolher,
  aoFechar,
}: MenuGraficoProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [altura, setAltura] = useState(0);

  /*
    FECHAR NO CLIQUE FORA E NO ESC.

       O `mousedown` e nao o `click`: no `click` o menu ja fechou antes de o
    alvo receber o evento, e o operador clica no item e nao acontece nada.
  */
  useEffect(() => {
    if (!aberto) return undefined;
    const fora = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) aoFechar();
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        aoFechar();
      }
    };
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', fora);
      document.removeEventListener('keydown', esc);
    };
  }, [aberto, aoFechar]);

  /*
    O MENU NAO SAI DA TELA (09/10/2026)
    ===================================
    MEDIDO na captura de 20:37: com o clique perto da borda, o menu aparecia
    cortado — e os itens de baixo (LIMPAR) ficavam inalcancaveis. Um menu com
    item inalcancavel e o mesmo defeito do icone invisivel: o operador nao
    pode usar o que nao ve.

    A medida Ȩ a altura real depois de montar, e o reposicionamento Ȩ para
    dentro. `altura` comeca em zero e so Ȩ lida depois do primeiro render.
  */
  useEffect(() => {
    if (aberto && ref.current) setAltura(ref.current.offsetHeight);
  }, [aberto, x, y]);

  if (!aberto) return null;

  const bloco = (itens: Item[]) => (
    <>
      {itens.map((item) => (
        <button
          key={item.chave}
          type="button"
          className={`menu-grafico-item${item.perigosa ? ' perigosa' : ''}`}
          onClick={() => {
            aoEscolher(item.chave, precoNoPonto);
            aoFechar();
          }}
        >
          <span>{item.rotulo}</span>
          {item.atalho && <kbd>{item.atalho}</kbd>}
        </button>
      ))}
    </>
  );

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
    </div>
  );
}
