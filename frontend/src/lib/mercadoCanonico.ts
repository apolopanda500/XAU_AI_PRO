/*
  O MERCADO EM UMA SO GRAFIA (12/11/2026)
  =======================================
  MEDIDO no app instalado 1.2.181, captura das 22:40 da aba ROBO, grafico ao
  vivo de XAUUSD M1:

      M1 · Abr 3.917,60089766 · Max igual · Min igual · Fecha igual
         · yahoo · dados publicos (sem execucao)

  A cadeia, elo por elo — e o primeiro elo e um NOME, nao um dado:

    1. `auto.market` chega do motor como `metal`, no SINGULAR (e a classe que a
       corretora publica na ficha: `asset_class = metal`).
    2. `useCatalogoAtivos(mt5, 'metal')` pede
       `/api/universal/assets?broker=mt5&market=metal`.
    3. `broker_registry.normalize_read_scope` recusa `metal` — o MT5 so conhece
       `metals` — e a rota responde erro. Catalogo VAZIO.
    4. Sem catalogo nao ha `fichaDoAtivo`, sem ficha nao ha `mercadoDoAtivo`, e
       o mercado derivado fica `''` → `configurado` falso.
    5. `configurado` falso cai na rota LIVRE (`/api/publico/ohlc`): yahoo GC=F,
       com a ultima vela degenerada (Abr = Max = Min = Fecha).

  E o yahoo estava DECLARADO — `dados publicos (sem execucao)` na mesma linha.
  Por isso nada parecia quebrado: a tela dizia a verdade sobre um dado que nao
  devia estar ali.

  A TABELA E A MESMA DOS OUTROS DOIS LADOS, e e o que o AGENTS.md 5 cobra:
  `backend/broker_registry.normalize_market` (gateway) e
  `backend/auto_engine.mercado_do_ativo` (motor) ja falam plural. O app era o
  unico dos tres que repassava o que recebeu — e o sintoma caiu no servidor,
  que estava certo.

  O QUE ESTA FUNCAO **NAO** FAZ
  ===========================
  Nao inventa mercado. Nome que ela nao conhece volta como veio (so aparado e
  em minusculas): quem recusa e a camada que sabe — `normalizeMarketSource`
  devolve `null` e a tela mostra a recusa com motivo. E vazio continua vazio:
  "sem mercado medido" e resposta; palpite nao (AGENTS.md 3).

  Isto tambem NAO e o mapeador de classe do ativo (`mercadoDoAtivo`, em
  `volumeUnidade.ts`): aquele traduz a CLASSE que a corretora publica
  (`crypto`, `equity`, `other`), este canoniza o NOME do mercado que ja veio
  de algum lugar. Os dois terminam na mesma grafia, e por isso a lista de
  mercados do `marketApi.ts` (`MARKET_SOURCES`) e uma so.
*/
const MERCADO_CANONICO: Record<string, string> = {
  forex: 'forex',
  fx: 'forex',
  moedas: 'forex',
  metals: 'metals',
  metal: 'metals',
  indices: 'indices',
  index: 'indices',
  indice: 'indices',
  stocks: 'stocks',
  stock: 'stocks',
  // O backend publica `equity` (asset_registry), o MT5 publica `Stocks`: os
  // dois chegam aqui, e o mercado do gateway e um so. Ver `mercadoDoAtivo`.
  equity: 'stocks',
  equities: 'stocks',
  acao: 'stocks',
  acoes: 'stocks',
  commodities: 'commodities',
  commodity: 'commodities',
  bonds: 'bonds',
  bond: 'bonds',
  titulo: 'bonds',
  titulos: 'bonds',
  other: 'other',
  outros: 'other',
  'crypto-spot': 'crypto-spot',
  crypto: 'crypto-spot',
  cripto: 'crypto-spot',
  spot: 'crypto-spot',
  'crypto-futures': 'crypto-futures',
  crypto_futures: 'crypto-futures',
  futures: 'crypto-futures',
  futuros: 'crypto-futures',
};

/** O nome do mercado na grafia que o gateway e o `marketApi` usam. */
export function mercadoCanonico(valor: string | null | undefined): string {
  const bruto = String(valor ?? '')
    .trim()
    .toLowerCase();
  if (!bruto) return '';
  return MERCADO_CANONICO[bruto] ?? bruto;
}
