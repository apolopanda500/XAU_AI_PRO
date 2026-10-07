import type { AssetRow } from './brokerCatalog';

/*
  A UNIDADE DO VOLUME (05/10/2026)
  ===============================
  MEDIDO nas capturas da XM, o mesmo par com nomes diferentes:

      Bolivar  (forex)  ->  "0,01 Lote(s)"
      BTCUSD   (crypto) ->  "0,01 Token(s)"

  Um "Lote" fixo para os dois e umATCHI: o operador de BTCUSD leria "0,01
  Lote" e nao saberia se esta falando de contrato ou de token.

  A chave e `assetClass`, que vem da HIERARQUIA que a corretora publica
  ("Cryptocurrencies" -> "crypto"), e nao de palavra solta no nome do simbolo.
  Sem classe publicada, a funcao devolve `null`: a tela entao nao escreve
  nenhuma unidade em vez de escrever a errada.
*/
export function unidadeDeVolume(assetClass: string | null | undefined): string | null {
  if (!assetClass) return null;
  if (assetClass === 'crypto') return 'Token(s)';
  return 'Lote(s)';
}

/** Ficha do ativo escolhida, pelo simbolo exato do catalogo. */
export function fichaDoAtivo(catalogo: AssetRow[], simbolo: string): AssetRow | null {
  const alvo = String(simbolo || '').toUpperCase();
  if (!alvo) return null;
  return catalogo.find((a) => a.symbol.toUpperCase() === alvo) ?? null;
}

/*
  A FAIXA DE VOLUME e do ATIVO. MEDIDO: `discover_assets` ja devolve
  `volume_min`, `volume_max` e `volume_step` lidos do item da corretora.

  A constante antiga (0,01 a 10,00) era de forex aplicada a tudo. Para um par
  cujo minimo e 0,001 isso rejeita ordens validas; para um whose max e menor,
  aceita ordens que o gateway recusa - e tela que aceita e gateway que recusa e
  a pior divergencia possivel.

  `fallback` existe para quando a ficha nao traz os campos: nesse caso o valor
  e assumido e `assumido: true` avisa o chamador, que mostra oasterisco.
*/
export type FaixaVolume = {
  minimo: number;
  maximo: number;
  passo: number;
  /** true quando algum valor NAO veio da corretora e foi assumido. */
  assumido: boolean;
};

const FALLBACK = { minimo: 0.01, maximo: 10, passo: 0.01 };

export function faixaDoAtivo(ficha: AssetRow | null): FaixaVolume {
  if (!ficha) return { ...FALLBACK, assumido: true };
  const min = ficha.volumeMin;
  const max = ficha.volumeMax;
  const passo = ficha.volumeStep;

  /*
    `assumido` mede se ALGUM valor caiu no fallback — e nao so se veio `null`.

    MEDIDO (05/10/2026): a primeira versao checava apenas `null`/`undefined`, e
    com `volume_min = 0` e `volume_max = -1` devolvia os numeros do fallback COM
    `assumido: false`. A tela mostrava a faixa sem o asterisco, e o operador
    lia "min 0.01 · max 10" como se a corretora tivesse dito isso. `assumido`
    que so olha ausencia mede a coisa errada: o que importa e se o valor
    ATIVO veio do produtor.
  */
  const minValido = typeof min === 'number' && Number.isFinite(min) && min > 0;
  const maxValido = typeof max === 'number' && Number.isFinite(max) && max > 0;
  const passoValido = typeof passo === 'number' && Number.isFinite(passo) && passo > 0;

  return {
    minimo: minValido ? (min as number) : FALLBACK.minimo,
    maximo: maxValido ? (max as number) : FALLBACK.maximo,
    passo: passoValido ? (passo as number) : FALLBACK.passo,
    assumido: !(minValido && maxValido && passoValido),
  };
}

/** Texto do input: a unidade da corretora, e o passo quando ela existe. */
export function rotuloQuantidade(unidade: string | null, passo: number): string {
  const u = unidade ?? 'Lote(s)';
  return `Quantidade em ${u.toLowerCase()}`;
}

/*
  O MERCADO DO ATIVO, pela classe que a CORRETORA publica (06/10/2026)
  ==================================================================
  MEDIDO no app instalado, 19:56: o par era `ETHUSD` e a tela pedia cotacao em
  `market=forex`. O gateway nao devolve cotacao de cripto em forex, a resposta
  vinha vazia, e o ticket ficava com `passo --`, SL e TP vazios e `AUTO NAO`.
  Como `passo` e 0, o 1:1 padrao nao tinha distancia para aplicar — o painel se
  configurava sozinho, mas sem preco nao tinha o que escrever.

  A classe e a MESMA que decide a unidade (`crypto` -> `Token(s)`), e vem da
  ficha da corretora. E a HIERARQUIA publicada, nao palavra no nome: `SOL`
  casaria dentro de "Solvar" (AGENTS.md 3).

  A TABELA e a mesma do motor, em `backend/auto_engine.py::mercado_do_ativo`.
  Os dois lados precisam falar a mesma lingua: se a tela disser `crypto-spot` e
  o motor disser `crypto`, cada um busca em um mercado e nenhum acha o dado —
  e o sintoma volta a parecer "nao tem preco", que e o AGENTS.md 5.

  `null` quando a classe nao veio. Sem ficha nao ha conversao possivel, e
  escolher um mercado seria adivinhar com confianca.
*/
const MERCADO_POR_CLASSE: Record<string, string> = {
  crypto: 'crypto-spot',
  forex: 'forex',
  metal: 'metals',
  index: 'indices',
  stock: 'stocks',
  bond: 'bonds',
  commodity: 'commodities',
};

export function mercadoDoAtivo(assetClass: string | null | undefined): string | null {
  if (!assetClass) return null;
  return MERCADO_POR_CLASSE[assetClass.trim().toLowerCase()] ?? null;
}

export default unidadeDeVolume;
