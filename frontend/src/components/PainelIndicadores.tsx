/*
  PAINEL DE INDICADORES (13/10/2026, pedido do dono)
  ==================================================
  "lista com botao igual dos modelos para indicadores": cada indicador e um
  item com nome, parametros, o que mede e botao Liga/Desliga — a mesma leitura
  dos cards de modelo, sem exigir que o operador descubra sigla.

  O QUE LIGA DE VERDADE: EMA, SMA, BOLLINGER, VWAP, RSI e MACD. Todos sao
  calculados dos candles exibidos e desenhados pelo `PriceChart`; o painel so
  chama `onAlternar`, e o grafico e o consumidor. Controle sem consumidor e
  pior que ausencia (AGENTS.md 9).

  ESTOCASTICO aparece como ROTEIRO (texto, nao botao): o calculo e o desenho
  ainda nao existem, e um botao para ele seria o botao que parece funcionar e
  nao funciona. Quando o desenho existir, vira item.
*/
import '../theme/indicadores.css';

export type IndicadorId = 'ema' | 'sma' | 'bollinger' | 'vwap' | 'rsi' | 'macd';

export type EstadoIndicadores = Record<IndicadorId, boolean>;

type Item = {
  id: IndicadorId;
  nome: string;
  params: string;
  mede: string;
};

const ITENS: Item[] = [
  {
    id: 'ema',
    nome: 'EMA',
    params: '12 · 26',
    mede: 'tendência pelas médias exponenciais, no gráfico',
  },
  {
    id: 'sma',
    nome: 'SMA 20',
    params: '20',
    mede: 'média móvel simples, no gráfico',
  },
  {
    id: 'bollinger',
    nome: 'Bollinger',
    params: '20 · 2',
    mede: 'volatilidade por bandas, no gráfico',
  },
  {
    id: 'vwap',
    nome: 'VWAP',
    params: 'volume',
    mede: 'preço médio ponderado pelo volume, no gráfico',
  },
  {
    id: 'rsi',
    nome: 'RSI',
    params: '14',
    mede: 'força 0–100 com faixas 70/30, em painel próprio',
  },
  {
    id: 'macd',
    nome: 'MACD',
    params: '12 · 26 · 9',
    mede: 'macd, sinal e histograma, em painel próprio',
  },
];

const ROTEIRO = [
  { nome: 'Estocástico', params: '14 · 3 · 3', mede: '%K/%D 0–100 com faixas 80/20, em painel próprio' },
];

type Props = {
  ativos: EstadoIndicadores;
  onAlternar: (id: IndicadorId) => void;
};

export default function PainelIndicadores({ ativos, onAlternar }: Props) {
  return (
    <div className="painel-indicadores" aria-label="Indicadores do gráfico">
      <div className="painel-indicadores-titulo">Indicadores</div>
      <ul className="painel-indicadores-lista">
        {ITENS.map((item) => {
          const ligado = ativos[item.id];
          return (
            <li key={item.id} className={`indicador-item${ligado ? ' ligado' : ''}`}>
              <div className="indicador-item-info">
                <strong>{item.nome}</strong>
                <span className="muted">{item.params}</span>
                <span className="indicador-item-mede">{item.mede}</span>
              </div>
              <button
                type="button"
                className={`btn sm ${ligado ? 'primary' : 'ghost'}`}
                aria-pressed={ligado}
                aria-label={`${ligado ? 'Desligar' : 'Ligar'} ${item.nome}`}
                onClick={() => onAlternar(item.id)}
              >
                {ligado ? 'Ligado' : 'Ligar'}
              </button>
            </li>
          );
        })}
      </ul>
      <div className="painel-indicadores-roteiro">
        <span className="muted">A caminho com a barra de ferramentas:</span>
        <ul>
          {ROTEIRO.map((r) => (
            <li key={r.nome}>
              <strong>{r.nome}</strong> <span className="muted">{r.params}</span>
              {' — '}
              <span>{r.mede}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
