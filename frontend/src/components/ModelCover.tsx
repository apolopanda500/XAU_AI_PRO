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
  /*
    A CLASSE, quando quem chama souber.

    MEDIDO (09/10/2026): esta capa tinha um `classeDe(simbolo)` que adivinhava
    a classe pelo NOME — `/XAU|XAG|GOLD|.../`, `/BTC|ETH|SOL|.../`,
    `/US30|US500|NAS|.../` e `forex` no resto. E exatamente o que o AGENTS.md §3
    proibe: "a classe de um ativo vem da HIERARQUIA que a corretora preenche,
    nao de palavra solta no nome", porque `SOL` casa dentro de `SOLVAR`.

    Adivinhar a classe erra a cor da capa — e pior, faz o operador achar que um
    par de forex e um indice porque a tela coloriu como indice.

    Agora a classe VEM DE FORA, do catalogo da corretora ou do `.meta.json`.
    Sem ela, a capa usa a cor NEUTRA. Nada e inventado.
  */
  assetClass?: string | null;
};

/**
 * As classes que a corretora publica, e mais nada.
 *
 * O `Literal` e o que o app SUPORTA, nao uma lista de ativos. Classe nova
 * entra aqui com o nome que a corretora usa.
 */
type ClasseAtivo = 'metal' | 'cripto' | 'forex' | 'indice' | 'indefinida';

/**
 * O nome da classe como a corretora escreve, para a cor da capa.
 *
 * Nao ha ramo de nome: se a corretora nao mandou a classe, devolve
 * `indefinida`. A cor neutra existe justamente para esse caso — uma capa cinza
 * e honesta, e uma capa colorida errada engana.
 */
function classeDe(assetClass: string | null | undefined): ClasseAtivo {
  const c = String(assetClass ?? '')
    .trim()
    .toLowerCase();
  if (c === 'metal' || c === 'metals' || c === 'commodity' || c === 'commodities') {
    return 'metal';
  }
  if (c === 'crypto' || c === 'crypto-spot' || c === 'crypto_futures') return 'cripto';
  if (c === 'forex' || c === 'fx') return 'forex';
  if (c === 'index' || c === 'indices' || c === 'indice') return 'indice';
  return 'indefinida';
}

// Metal = dourado, cripto = ciano, forex = azul frio, indice = violeta.
// Nenhuma distincao depende so de cor: o glifo e o timeframe tambem separam.
// `indefinida` = cinza, que diz "a corretora nao me contou a classe".
const PALETA: Record<ClasseAtivo, { base: string; borda: string; glifo: string }> = {
  metal: { base: '#3a2a08', borda: '#c99400', glifo: '#ffd24a' },
  cripto: { base: '#062b33', borda: '#00b8c4', glifo: '#3ee6f0' },
  forex: { base: '#0d2136', borda: '#2f7fd1', glifo: '#7fc0ff' },
  indice: { base: '#241436', borda: '#8b5cf6', glifo: '#c4a6ff' },
  indefinida: { base: '#141821', borda: '#3a4252', glifo: '#8a94a6' },
};

const TF_CURTO: Record<string, string> = {
  M1: '1M',
  M5: '5M',
  M15: '15M',
  M30: '30M',
  H1: '1H',
  H4: '4H',
  D1: '1D',
  W1: '1S',
};

function pct(v: number | null | undefined, casas = 1): string {
  return v === null || v === undefined || !Number.isFinite(v)
    ? '--'
    : `${(v * 100).toFixed(casas)}%`;
}

export default function ModelCover({
  modelo,
  selecionado,
  onSelect,
}: {
  modelo: CapaModelo;
  selecionado?: boolean;
  onSelect?: (id: string) => void;
}) {
  /*
    A classe vem de `modelo.assetClass` — de quem tem a ficha da corretora, nao
    do nome. Sem ela: `indefinida`, e a capa fica cinza em vez de chutar.
  */
  const classe = classeDe(modelo.assetClass);
  const paleta = PALETA[classe];
  const tf =
    TF_CURTO[String(modelo.timeframe || '').toUpperCase()] ??
    String(modelo.timeframe || '').toUpperCase();
  /*
    A SIGLA E OPCIONAL (09/10/2026), pela decisao do dono: "deixar o catalogo
    sem icone apenas lista opcional".

    `assetIcon` agora recebe SO a classe — ele nem ve o nome do ativo, e por isso
    nao tem como adivinhar. Sem classe conhecida nao vem sigla, e o selo nao e
    desenhado: o topo da capa fica so com o periodo.
  */
  const sigla = assetIcon(classe);
  const edge = modelo.edge;
  const temEdge = edge !== null && edge !== undefined && Number.isFinite(edge) && edge > 0;

  const conteudo = (
    <>
      <span className="mc-topo" style={{ background: paleta.base, borderColor: paleta.borda }}>
        {sigla && (
          <span className="mc-glifo" style={{ color: paleta.glifo }} aria-hidden="true">
            {sigla}
          </span>
        )}
        <span className="mc-tf" style={{ color: paleta.glifo }}>
          {tf}
        </span>
      </span>
      <span className="mc-corpo">
        <span className="mc-nome">{modelo.symbol}</span>
        <span className="mc-metricas">
          <span title="Acurácia no treino">
            acc <b className="num">{pct(modelo.accuracy)}</b>
          </span>
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
    return (
      <div className="model-cover" aria-label={`Modelo ${modelo.symbol} ${tf}`}>
        {conteudo}
      </div>
    );
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
