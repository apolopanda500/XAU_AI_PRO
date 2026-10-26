// Desenho de fundo do card, decidido pela CLASSE que a corretora publica.
//
// POR QUE CLASSE E NAO NOME
// =========================
// A regra do projeto (AGENTS.md §3) e que a classe vem da hierarquia da
// corretora, nunca de palavra solta no simbolo. Este componente recebe a
// classe ja resolvida e o `seed`, e nao ve o simbolo — nao tem como adivinhar.
// Classe desconhecida cai no desenho neutro, que e honesto: nao afirma nada.
//
// O `seed` (a mesma matiz do card) muda posicao e inclinacao do desenho. E
// decoracao deterministica, nao informacao: dois cards nunca tem a mesma cara,
// e nenhum dado do treino e inventado para isso.
//
// RENDERIZACAO
// ============
// SVG inline em `currentColor` (sem `id` de gradiente, que colidiria entre
// cards), traco geometrico, `vector-effect: non-scaling-stroke` no CSS e
// `contain: paint` no container. Sem filtro pesado e sem sombra por card:
// a lista tem dezenas de capas e o WebView nao deve pagar caro por decoracao.
import { memo, type CSSProperties, type ReactElement } from 'react';

type Props = {
  classe: string;
  seed: number;
  cor: string;
};

function Metal() {
  return (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round">
      <ellipse cx="146" cy="44" rx="31" ry="31" opacity="0.5" />
      <ellipse cx="146" cy="44" rx="21" ry="21" opacity="0.75" />
      <path d="M128 102 L170 102 L178 118 L120 118 Z" fill="currentColor" fillOpacity="0.16" />
      <path d="M116 78 L156 78 L164 94 L108 94 Z" fill="currentColor" fillOpacity="0.2" />
      <path d="M134 54 L174 54 L182 70 L126 70 Z" fill="currentColor" fillOpacity="0.24" />
    </g>
  );
}

function Cripto() {
  return (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round">
      <path d="M124 18 L158 38 L158 78 L124 98 L90 78 L90 38 Z" opacity="0.55" />
      <path d="M124 34 L144 46 L144 70 L124 82 L104 70 L104 46 Z" fill="currentColor" fillOpacity="0.12" />
      <path d="M158 38 L182 24 M158 78 L184 92 M90 38 L66 24 M90 78 L64 92" opacity="0.4" />
      <circle cx="184" cy="24" r="3" fill="currentColor" fillOpacity="0.7" stroke="none" />
      <circle cx="184" cy="92" r="3" fill="currentColor" fillOpacity="0.7" stroke="none" />
      <circle cx="64" cy="92" r="3" fill="currentColor" fillOpacity="0.7" stroke="none" />
    </g>
  );
}

function Forex() {
  return (
    <g fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
      <path d="M36 112 L168 112" opacity="0.35" />
      <path d="M52 96 L52 66" opacity="0.6" />
      <rect x="46" y="74" width="12" height="16" fill="currentColor" fillOpacity="0.18" />
      <path d="M76 88 L76 50" opacity="0.6" />
      <rect x="70" y="56" width="12" height="24" fill="currentColor" fillOpacity="0.22" />
      <path d="M100 92 L100 58" opacity="0.6" />
      <rect x="94" y="66" width="12" height="18" fill="currentColor" fillOpacity="0.18" />
      <path d="M124 78 L124 40" opacity="0.6" />
      <rect x="118" y="46" width="12" height="24" fill="currentColor" fillOpacity="0.24" />
      <path d="M148 66 L148 28" opacity="0.6" />
      <rect x="142" y="34" width="12" height="22" fill="currentColor" fillOpacity="0.28" />
      <path d="M40 98 L70 82 L100 88 L130 62 L160 44 L186 30" strokeDasharray="4 5" opacity="0.45" />
    </g>
  );
}

function Indice() {
  return (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <path
        d="M20 116 L48 96 L76 104 L104 74 L132 82 L160 48 L190 26"
        fill="currentColor"
        fillOpacity="0.1"
        stroke="none"
      />
      <path d="M20 116 L48 96 L76 104 L104 74 L132 82 L160 48 L190 26" opacity="0.8" />
      {[
        [48, 96],
        [104, 74],
        [160, 48],
      ].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="2.6" fill="currentColor" stroke="none" />
      ))}
      <path d="M20 128 L190 128" opacity="0.3" strokeDasharray="2 6" />
    </g>
  );
}

function Neutro() {
  return (
    <g fill="none" stroke="currentColor" strokeWidth="1.1" opacity="0.55">
      <circle cx="150" cy="70" r="46" />
      <circle cx="150" cy="70" r="30" opacity="0.7" />
      <path d="M104 70 L196 70 M150 24 L150 116" opacity="0.35" strokeDasharray="3 6" />
    </g>
  );
}

const DESENHOS: Record<string, () => ReactElement> = {
  metal: Metal,
  cripto: Cripto,
  forex: Forex,
  indice: Indice,
  indefinida: Neutro,
};

function AssetArtBase({ classe, seed, cor }: Props) {
  const Desenho = DESENHOS[classe] ?? Neutro;
  const giro = (seed % 9) - 4;
  const dx = (seed % 13) - 6;
  const dy = (seed % 7) - 3;
  return (
    <svg
      className="mc-art-svg"
      data-art={classe in DESENHOS ? classe : "indefinida"}
      viewBox="0 0 200 140"
      preserveAspectRatio="xMaxYMax meet"
      shapeRendering="geometricPrecision"
      aria-hidden="true"
      focusable="false"
      style={
        {
          color: cor,
          '--aa-x': `${dx}px`,
          '--aa-y': `${dy}px`,
          '--aa-r': `${giro}deg`,
        } as CSSProperties
      }
    >
      <Desenho />
    </svg>
  );
}

export default memo(AssetArtBase);
