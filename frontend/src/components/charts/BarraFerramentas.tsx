/*
  A BARRA DE FERRAMENTAS DO GRAFICO (06/10/2026)
  =============================================
  O dono pediu: "as barras de ferramentas do grafico isso e crucial para eu
  operar, linhas de tendencias etc... se possivel copiar controles de robo
  automaticos de outras corretoras".

  O QUE ENTRA, E POR QUE ESTES
  ============================
  - GRADE: as plataformas mostram a grade ligada por padrao. Aqui ela vinha
    com as linhas verticais DESLIGADAS (`grid.vertLines.visible: false` no
    `createChart`), e o operador nao tinha como liga-las.
  - CRUZ: o crosshair existe, mas nao ha como voltar ao modo normal depois de
    o "snap" magnético.
  - TENDENCIA e HORIZONTAL: as duas ferramentas que servem para planejar
    entrada e stop olhando o preco, e que o lightweight-charts 4.2.3 NAO tem
    (ele so desenha serie e linha de preco).
  - ZOOM +/−/AJUSTAR: o grafico ja aceita zoom pelo mouse, mas nao por botao.
    Para quem opera com uma mao so, botao e a diferenca entre ajustar e caçar.

  POR QUE UM COMPONENTE SO
  ========================
  A barra e uma fileira de botoes que NAO sabe falar com o lightweight-charts.
  Ela recebe o estado e avisa a intencao. Quem conversa com o grafico e o
  `PriceChart`, que e quem tem `createChart` e a serie. Botar `applyOptions`
  aqui exigiria passar o grafico inteiro para dentro — e o componente viraria
  um segundo lugar com estado do grafico, que e como dois lugares divergem.

  `aria-pressed` em botao de ferramenta e o que um leitor de tela anuncia como
  "ligado". O `title` diz o que a ferramenta faz, porque o botao e um icone.
*/
import type { EstiloDesenho, TipoDesenho } from './desenhos';
import { ESPESSURAS, PALETA, normalizarEspessura, normalizarOpacidade } from './desenhos';

export type FerramentaAtiva = 'nenhuma' | TipoDesenho | 'apagar';

export type BarraProps = {
  ferramenta: FerramentaAtiva;
  gradeVertical: boolean;
  gradeHorizontal: boolean;
  crosshairMagnetico: boolean;
  quantosDesenhos: number;
  /** O desenho escolhido, ou `null`. Sem ele nao ha estilo para mudar. */
  selecionado: boolean;
  estiloSelecionado: EstiloDesenho;
  /** Ha passo para desfazer? O botao desabilita quando nao ha. */
  podeDesfazer: boolean;
  /** Ha passo para refazer? */
  podeRefazer: boolean;
  aoEscolher: (f: FerramentaAtiva) => void;
  aoAlternarGrade: (eixo: 'vertical' | 'horizontal') => void;
  aoAlternarCrosshair: () => void;
  aoZoom: (direcao: 1 | -1 | 0) => void;
  aoLimparDesenhos: () => void;
  aoDesfazer: () => void;
  aoRefazer: () => void;
  aoMudarCor: (cor: string) => void;
  aoMudarEspessura: (espessura: number) => void;
  aoMudarOpacidade: (opacidade: number) => void;
  aoAlternarTrava: () => void;
};

type Botao = {
  chave: string;
  rotulo: string;
  titulo: string;
  ativo?: boolean;
  desabilitado?: boolean;
  aoClicar: () => void;
};

export default function BarraFerramentas({
  ferramenta,
  gradeVertical,
  gradeHorizontal,
  crosshairMagnetico,
  quantosDesenhos,
  selecionado,
  estiloSelecionado,
  podeDesfazer,
  podeRefazer,
  aoEscolher,
  aoAlternarGrade,
  aoAlternarCrosshair,
  aoZoom,
  aoLimparDesenhos,
  aoDesfazer,
  aoRefazer,
  aoMudarCor,
  aoMudarEspessura,
  aoMudarOpacidade,
  aoAlternarTrava,
}: BarraProps) {
  /*
    ATIVAR A FERRAMENTA JA DESARMA A ORDEM.

    Nao e detalhe de implementacao: enquanto a ferramenta de desenho esta
    armada, o clique NAO pode armar uma ordem. Sem esta separacao, o primeiro
    clique de uma linha de tendencia seria tambem uma ordem — e a linha
    apareceria sobre uma posicao que o operador nao pediu. Por isso o estado e
    UNICO: uma ferramenta ou outra, nunca as duas.
  */
  const ferramentas: Botao[] = [
    {
      /*
        O CURSOR primeiro, como na XM. E a ferramenta que DESARMA todas as
        outras: sem ela, nao ha como voltar a "so olhar" depois de armar a
        tendencia, e o grafico fica preso na ferramenta.
      */
      chave: 'cursor',
      rotulo: '✛',
      titulo: 'Cursor: voltar a apenas observar o gráfico',
      ativo: ferramenta === 'nenhuma',
      aoClicar: () => aoEscolher('nenhuma'),
    },
    {
      chave: 'tendencia',
      rotulo: '⌁',
      titulo: 'Linha de tendência: clique em dois pontos do gráfico',
      ativo: ferramenta === 'tendencia',
      aoClicar: () => aoEscolher(ferramenta === 'tendencia' ? 'nenhuma' : 'tendencia'),
    },
    {
      chave: 'horizontal',
      rotulo: '─',
      titulo: 'Linha horizontal: clique em um ponto do gráfico (Alt + H)',
      ativo: ferramenta === 'horizontal',
      aoClicar: () => aoEscolher(ferramenta === 'horizontal' ? 'nenhuma' : 'horizontal'),
    },
    {
      chave: 'apagar',
      rotulo: '⌫',
      titulo: 'Apagar desenho: clique sobre a linha',
      ativo: ferramenta === 'apagar',
      // Sem desenho nao ha o que apagar, e botao que parece funcionar e nao
      // funciona e o defeito que o dono reportou no botao EMA.
      desabilitado: quantosDesenhos === 0,
      aoClicar: () => aoEscolher(ferramenta === 'apagar' ? 'nenhuma' : 'apagar'),
    },
  ];

  const visor: Botao[] = [
    {
      chave: 'grade-v',
      rotulo: '⊞',
      titulo: 'Linhas verticais da grade',
      ativo: gradeVertical,
      aoClicar: () => aoAlternarGrade('vertical'),
    },
    {
      chave: 'grade-h',
      rotulo: '⊟',
      titulo: 'Linhas horizontais da grade',
      ativo: gradeHorizontal,
      aoClicar: () => aoAlternarGrade('horizontal'),
    },
    {
      chave: 'cruz',
      rotulo: '✛',
      titulo: crosshairMagnetico ? 'Crosshair preso no candle' : 'Crosshair livre',
      ativo: crosshairMagnetico,
      aoClicar: aoAlternarCrosshair,
    },
    {
      chave: 'zoom-mais',
      rotulo: '+',
      titulo: 'Aproximar',
      aoClicar: () => aoZoom(1),
    },
    {
      chave: 'zoom-menos',
      rotulo: '−',
      titulo: 'Afastar',
      aoClicar: () => aoZoom(-1),
    },
    {
      chave: 'zoom-ajustar',
      rotulo: '⤢',
      titulo: 'Ajustar à janela',
      aoClicar: () => aoZoom(0),
    },
  ];

  return (
    <div className="price-chart-barra" role="toolbar" aria-label="Ferramentas do gráfico">
      <div className="btn-row" role="group" aria-label="Desenhar">
        {ferramentas.map((b) => (
          <button
            key={b.chave}
            type="button"
            className={`btn sm ${b.ativo ? 'primary' : 'ghost'} price-chart-ferramenta`}
            aria-pressed={Boolean(b.ativo)}
            disabled={b.desabilitado}
            title={b.titulo}
            aria-label={b.titulo}
            onClick={b.aoClicar}
          >
            {b.rotulo}
          </button>
        ))}
      </div>

      <div className="btn-row" role="group" aria-label="Visualizar">
        {visor.map((b) => (
          <button
            key={b.chave}
            type="button"
            className={`btn sm ${b.ativo ? 'primary' : 'ghost'} price-chart-ferramenta`}
            aria-pressed={Boolean(b.ativo)}
            title={b.titulo}
            aria-label={b.titulo}
            onClick={b.aoClicar}
          >
            {b.rotulo}
          </button>
        ))}
      </div>

      {/*
        O CONTADOR DE DESENHOS, e nao um botao de "limpar tudo" solto.

        Um "limpar tudo" sem quantos existem faz o operador clicar sem saber o
        que vai apagar. O numero diz o que sera perdido, e o `title` do botao
        repete isso em texto para o leitor de tela.
      */}
      {quantosDesenhos > 0 && (
        <div className="btn-row" role="group" aria-label="Desenhos">
          <span className="muted price-chart-conta" aria-live="polite">
            {quantosDesenhos} desenho{quantosDesenhos > 1 ? 's' : ''}
          </span>
          <button
            type="button"
            className="btn sm ghost"
            title={`Apagar os ${quantosDesenhos} desenhos do gráfico`}
            aria-label={`Apagar os ${quantosDesenhos} desenhos do gráfico`}
            onClick={aoLimparDesenhos}
          >
            Limpar
          </button>
        </div>
      )}

      {/*
        DESFAZER E REFAZER, ao lado do contador (06/10/2026).

        MEDIDO nas capturas da XM (20:37): o `↶` do topo acende depois de uma
        acao, e o `Ctrl + Z` desfaz. Aqui eles ficam perto do contador de
        desenhos porque e isso que eles desfazem.

        O par aparece quando ha desenho OU ha passo para desfazer/refazer.

        Este ultimo `ou` e o que faz o refazer funcionar: logo apos desfazer o
        ULTIMO desenho, a contagem vai a zero, e um botao que so aparece com
        desenho na tela sumiria justamente no passo em que o operador precisa
        dele. O `disabled` e o que diz que nao ha passo; esconder e o que faz o
        botao sumir quando ele era preciso.
      */}
      {(quantosDesenhos > 0 || podeDesfazer || podeRefazer) && (
        <div className="btn-row" role="group" aria-label="Desfazer e refazer">
          <button
            type="button"
            className="btn sm ghost"
            title={podeDesfazer ? 'Desfazer a última mudança no desenho (Ctrl + Z)' : 'Nada para desfazer'}
            aria-label={podeDesfazer ? 'Desfazer a última mudança no desenho (Ctrl + Z)' : 'Nada para desfazer'}
            disabled={!podeDesfazer}
            onClick={aoDesfazer}
          >
            ↶
          </button>
          <button
            type="button"
            className="btn sm ghost"
            title={podeRefazer ? 'Refazer a mudança desfeita (Ctrl + Y)' : 'Nada para refazer'}
            aria-label={podeRefazer ? 'Refazer a mudança desfeita (Ctrl + Y)' : 'Nada para refazer'}
            disabled={!podeRefazer}
            onClick={aoRefazer}
          >
            ↷
          </button>
        </div>
      )}

      {/*
        O ESTILO DO DESENHO ESCOLHIDO (06/10/2026)
        ==============================================
        MEDIDO nas capturas da XM (20:35 e 20:36): a paleta, a espessura e o
        cadeado aparecem na barra flutuante SOBRE o desenho escolhido, e valem
        para ele.

        Aparece SO com selecao, e essa e a razao de ser: sem desenho escolhido
        nao ha o que mudar de cor. Um estilo global obrigaria o operador a
        redesenhar a linha para trocar a cor — e a linha existe justamente para
        marcar o stop no lugar certo. Perder o ponto marcado para mudar a cor e
        o oposto do que a ferramenta serve.
      */}
      {selecionado && (
        <div className="btn-row price-chart-estilo" role="group" aria-label="Estilo do desenho">
          <span className="muted price-chart-conta">Estilo</span>
          {/*
            A PALETA. Botao com o quadrado da cor e o NOME da cor no `title` e no
            `aria-label`: so a cor nao diz nada a um leitor de tela, e o operador
            precisa do nome para comparar com a paleta da XM.
          */}
          {PALETA.map((cor) => (
            <button
              key={cor}
              type="button"
              className={`price-chart-cor ${estiloSelecionado.cor === cor ? 'ativo' : ''}`}
              style={{ background: cor }}
              title={`Cor ${cor}`}
              aria-label={`Cor ${cor}`}
              aria-pressed={estiloSelecionado.cor === cor}
              onClick={() => aoMudarCor(cor)}
            />
          ))}
          {ESPESSURAS.map((espessura) => (
            <button
              key={espessura}
              type="button"
              className={`btn sm ${estiloSelecionado.espessura === espessura ? 'primary' : 'ghost'} price-chart-espessura`}
              title={`Espessura ${espessura} px`}
              aria-label={`Espessura ${espessura} px`}
              aria-pressed={estiloSelecionado.espessura === espessura}
              onClick={() => aoMudarEspessura(espessura)}
            >
              {espessura}px
            </button>
          ))}
          <label className="price-chart-opacidade">
            <span className="muted">Opacidade</span>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={Math.round(estiloSelecionado.opacidade * 100)}
              title={`Opacidade ${Math.round(estiloSelecionado.opacidade * 100)}%`}
              aria-label={`Opacidade do desenho, ${Math.round(estiloSelecionado.opacidade * 100)}%`}
              onChange={(e) => {
                const normalizado = normalizarOpacidade(Number(e.target.value) / 100);
                if (normalizado !== null) aoMudarOpacidade(normalizado);
              }}
            />
            <span className="muted mono">{Math.round(estiloSelecionado.opacidade * 100)}%</span>
          </label>
          <button
            type="button"
            className={`btn sm ${estiloSelecionado.travado ? 'primary' : 'ghost'}`}
            title={
              estiloSelecionado.travado
                ? 'Destravar o desenho para mover as pontas de novo'
                : 'Travar o desenho: as pontas param de ser arrastáveis'
            }
            aria-label={
              estiloSelecionado.travado
                ? 'Destravar o desenho para mover as pontas de novo'
                : 'Travar o desenho: as pontas param de ser arrastáveis'
            }
            aria-pressed={estiloSelecionado.travado}
            onClick={aoAlternarTrava}
          >
            {estiloSelecionado.travado ? '🔒' : '🔓'}
          </button>
        </div>
      )}
    </div>
  );
}