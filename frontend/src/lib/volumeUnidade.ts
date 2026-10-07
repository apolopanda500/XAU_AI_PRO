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

/*
  O REQUISITO DE MARGEM (06/10/2026)
  ===================================
  MEDIDO nas capturas da XM (`my.xm.com/pt/symbol-info/BTCUSD`, 20:43):
  `Quantidade 0,01 lotes` · `Requisito de margem $0.85` · barra em `8,01%`.

  A CONTA E O QUE CONFIRMA. MEDIDO no painel `Gerir` da XM e no
  `account_info()` do MT5, os dois lados dizem **1000:1**. E a conta confere:

      nocional   = 0,01 x contract_size x preco
                = 0,01 x 1,0 x 85.523        ($855,23 — contract_size do BTCUSD
                                                e 1,0, MEDIDO no symbol_info)
      requisito = 855,23 / 1000 = 0,855      → a XM escreve `$0.85`

  `contract_size` e o que separa cripto de forex, e sem ele o dinheiro vira preco
  errado: EURUSD tem `contract_size = 100.000` e GOLD tem `100`. Um requisito de
  margem calculado com `1` no lugar do contrato daria `0,86` no BTCUSD e
  `855,23` no EURUSD — o mesmo valor para os dois, e errado num deles.

  POR QUE ISTO NAO ERA "NUMERO INVENTADO" (06/10/2026)
  =====================================================
  O ciclo anterior recusou este numero, com o motivo certo mas a conclusao
  errada: escrevia-se que a alavancagem "e um numero que a corretora calcula e
  que o app nao tem de onde ler". **A corretora publica, e o gateway ja lia a
  conta.** Bastava a alavancagem virar campo do payload — feito em
  `mt5_gateway.py`, campo `leverage`.

  Um requisito de margem estimado seria o "numero inventado no painel vira
  limite real" do AGENTS.md. Um requisito de margem CALCULADO com a
  alavancagem da conta e o contract_size do ativo nao e estimativa: e a conta
  da XM, conferida.

  O QUE ESTA FUNCAO NAO FAZ, E POR QUE
  =====================================
  Ela nao sabe a margem LIVRE da conta, e por isso a BARRA fica de fora. A XM
  escreve `8,01%` — que e `requisito / margem livre` — e a margem livre muda a
  cada tique. Um percentual guardado no painel seria um numero que muda sozinho
  sem que ninguem leia. Quem tem a margem livre em tempo real e a Carteira.
*/
export type RequisitoMargem = {
  /** Requisito em dinheiro, ou `null` quando falta dado medido. */
  valor: number | null;
  /** O nocional em dinheiro que o operador esta realmente arriscando. */
  nocional: number | null;
  /** Por que `valor` e `null`, quando e. A tela mostra isto. */
  motivo: string | null;
  /**
   * true quando algum insumo NAO veio da corretora.
   *
   * O mesmo sentido de `FaixaVolume.assumido`: o que importa e se o valor
   * ATIVO veio do produtor, e nao se veio `null`. Com `contractSize` ausente e
   * volume 0,01, um requisito calculado com `1` no lugar do contrato seria
   * `0,86` no BTCUSD — e `855,23` no EURUSD, cujo contrato e 100.000. O numero
   * errado com aparencia de certo e o que este campo existe para denunciar.
   */
  assumido: boolean;
};

export function requisitoDeMargem(
  volume: number,
  preco: number,
  contractSize: number | null | undefined,
  leverage: number | null | undefined,
): RequisitoMargem {
  const faltando: string[] = [];
  if (!Number.isFinite(volume) || volume <= 0) faltando.push('quantidade');
  if (!Number.isFinite(preco) || preco <= 0) faltando.push('preço');
  if (typeof contractSize !== 'number' || !Number.isFinite(contractSize) || contractSize <= 0) {
    faltando.push('tamanho do contrato');
  }
  if (typeof leverage !== 'number' || !Number.isFinite(leverage) || leverage <= 0) {
    faltando.push('alavancagem da conta');
  }
  if (faltando.length) {
    return { valor: null, nocional: null, motivo: `Falta ${faltando.join(', ')}`, assumido: true };
  }

  const nocional = volume * (contractSize as number) * preco;
  return {
    valor: nocional / (leverage as number),
    nocional,
    motivo: null,
    assumido: false,
  };
}

export default unidadeDeVolume;
