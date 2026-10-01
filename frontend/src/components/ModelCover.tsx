// Mini capa de modelo.
//
// POR QUE UMA CAPA E NAO SO UM TEXTO
// ==================================
// A lista de modelos e uma parede de identificadores: "XAUUSD_H1",
// "XAUUSD_H4", "XAUUSD_M15". O operador precisa abrir o .meta.json para saber
// qual e melhor. A capa resolve isso sem adicionar coluna: cada modelo vira
// um cartao com simbolo, timeframe e a metrica que decide se ele serve —
// accuracy e edge, vindas do arquivo do treino, nunca inventadas na tela.
//
// A identidade visual vem da CLASSE do ativo, e nao do nome. Metal com o
// mesmo tratamento visual de um par de forex esconde o que muda de verdade
// na operacao: o tamanho do contrato, o horario e o comportamento.
//
// NADA E INVENTADO NESTA CAPA
// ==========================
// O glifo vem de `assetIcon`. As metricas vem do `.meta.json`. O selo de
// "publicavel" vem do quality gate do treino. O que nao existe no arquivo
// aparece como "--", nunca preenchido.
import { assetIcon } from '../lib/assetIcons';

export type CapaModelo = {
  id: string;
  label?: string;
  symbol: string;
  timeframe: string;
  accuracy?: number | null;
  edge?: number | null;
  f1?: number | null;
  publicable?: boolean;
  pklPresent?: boolean;
};

type ClasseAtivo = 'metal' | 'cripto' | 'forex' | 'indice';

// A ordem importa: "XAUUSD" tem 6 letras e cairia em forex se a regra fosse
// "6 letras = forex". Metal e cripto sao testados antes.
function classeDe(simbolo: string): ClasseAtivo {
  const s = String(simbolo || '').toUpperCase();
  if (/XAU|XAG|GOLD|SILVER|XPT/.test(s)) return 'metal';
  if (/BTC|ETH|SOL|XRP|DOGE/.test(s)) return 'cripto';
  if (/US30|US500|NAS|SPX|DAX|HK50|USTEC/.test(s)) return 'indice';
  return 'forex';
}

// Metal = dourado, cripto = ciano, forex = azul frio, indice = violeta.
// Nenhuma distincao depende so de cor: o glifo e o timeframe tambem separam.
const PALETA: Record<ClasseAtivo, { base: string; borda: string; glifo: string }> = {
  metal: { base: '#3a2a08', borda: '#c99400', glifo: '#ffd24a' },
  cripto: { base: '#062b33', borda: '#00b8c4', glifo: '#3ee6f0' },
  forex: { base: '#0d2136', borda: '#2f7fd1', glifo: '#7fc0ff' },
  indice: { base: '#241436', borda: '#8b5cf6', glifo: '#c4a6ff' },
};

const TF_CURTO: Record<string, string> = {
  M1: '1M', M5: '5M', M15: '15M', M30: '30M',
  H1: '1H', H4: '4H', D1: '1D', W1: '1S',
};

function pct(v: number | null | undefined, casas = 1): string {
  return v === null || v === undefined || !Number.isFinite(v) ? '--' : `${(v * 100).toFixed(casas)}%`;
}

export default function ModelCover({
  modelo, selecionado, onSelect,
}: {
  modelo: CapaModelo;
  selecionado?: boolean;
  onSelect?: (id: string) => void;
}) {
  const classe = classeDe(modelo.symbol);
  const paleta = PALETA[classe];
  const tf = TF_CURTO[String(modelo.timeframe || '').toUpperCase()]
    ?? String(modelo.timeframe || '').toUpperCase();
  const edge = modelo.edge;
  const temEdge = edge !== null && edge !== undefined && Number.isFinite(edge) && edge > 0;

  const conteudo = (
    <>
      <span className="mc-topo" style={{ background: paleta.base, borderColor: paleta.borda }}>
        <span className="mc-glifo" style={{ color: paleta.glifo }} aria-hidden="true">
          {assetIcon(modelo.symbol, classe)}
        </span>
        <span className="mc-tf" style={{ color: paleta.glifo }}>{tf}</span>
      </span>
      <span className="mc-corpo">
        <span className="mc-nome">{modelo.symbol}</span>
        <span className="mc-metricas">
          <span title="Acurácia no treino">acc <b className="num">{pct(modelo.accuracy)}</b></span>
          <span title="Edge no treino" className={temEdge ? 'pos' : 'neg'}>
            edge <b className="num">{pct(edge)}</b>
          </span>
        </span>
      </span>
      <span className="mc-selo" data-classe={classe}>
        {modelo.publicable ? 'publicavel' : 'reprovado'}
      </span>
    </>
  );

  if (!onSelect) {
    return <div className="model-cover" aria-label={`Modelo ${modelo.symbol} ${tf}`}>{conteudo}</div>;
  }

  return (
    <button
      type="button"
      className="model-cover is-botao"
      aria-pressed={selecionado}
      onClick={() => onSelect(modelo.id)}
      aria-label={`Modelo ${modelo.symbol} ${tf}, acurácia ${pct(modelo.accuracy)}, edge ${pct(edge)}`}
    >
      {conteudo}
    </button>
  );
}
