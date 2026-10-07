/**
 * O ÍCONE/ABREVIACAO do ativo, por HIERARQUIA e nao por palavra no nome.
 *
 * O DEFEITO MEDIDO (06/10/2026)
 * =============================
 * Esta funcao filtrava por PALAVRA no simbolo, na ordem em que os `if` apareciam:
 *
 *     if (/BTC/.test(text)) return 'BTC';
 *     ...
 *     if (/SOL/.test(text)) return 'SOL';
 *
 * Duas consequencias, ambas medidas:
 *
 * 1. **Fronteira de palavra inexistente.** `/SOL/` casa dentro de `SOLVAR`,
 *    `RESOLVED`, `CONSOLID` — e dentro de `SOL/USDT` que a XM publica. O ativo
 *    Solstable vira icone de Solana. E o AGENTS.md 3 que nomeia esse caso:
 *    "sem fronteira de palavra, `SOL` casa dentro de 'Solvar'".
 *
 * 2. **A HIERARQUIA DA CORRETORA VINHA DEPOIS DO NOME.** `assetClass` era
 *    testado na posicao 9 (`assetClass === 'metal'`), e as primeiras oito
 *    decisoes eram so por palavra. Um `GOLD` de uma corretora que publica
 *    `asset_class: 'metal'` pegava `Au` na nona linha — mas so depois de passar
 *    por sete filtros de nome. Um ativo cujo nome contivesse `BTC` e cuja classe
 *    fosse `metal` virava `BTC`.
 *
 * A REGRA AGORA
 * =============
 * A CLASSE QUE A CORRETORA PUBLICA manda. O nome do simbolo so entra como
 * complemento — para os casos em que a classe nao diz o bastante (o par, que e
 * a unidade de um indice), e SEM fronteira de palavra.
 *
 * Por que a classe manda: e o que a corretora afirma sobre o ativo, e a ficha
 * vem de `asset_registry`. Duas corretoras podem escrever o mesmo par de formas
 * diferentes, e so a ficha sabe o que ele e. Um filtro por nome teria de
 * reescrever a lista a cada corretora nova.
 */

/** A classe do ativo, tal como a corretora publica. */
type Classe = string;

/**
 * As classes do `asset_classes`, e o que cada uma quer dizer.
 *
 * A chave e a que o gateway manda em `asset_class`. Este mapa e de TRADUCAO de
 * rotulo, e nao de decisao de mercado: nenhuma regra aqui filtra o ativo, todas
 * devolvem a sigla que o operador le.
 */
const SIGLA_POR_CLASSE: Record<string, string> = {
  metal: 'MET',
  crypto: 'CRY',
  forex: 'FX',
  index: 'IDX',
  equity: 'EQ',
  future: 'FUT',
  option: 'OPT',
  bond: 'OND',
  energy: 'ENE',
  commodity: 'COM',
  // Classes que a XM publica e o gateway repassa. Sem entrada aqui, o fluxo cai
  // no par — que ainda e melhor que uma sigla inventada.
};

/**
 * Sigla de um par de METAL.
 *
 * Os metais preciosos tem sigla propria porque o operador os ve o tempo todo e
 * `MET` nao distingue ouro de prata.
 *
 * A FRONTEIRA E NO COMECO, E O RESTO DO PAR E SUFIXO DE COTACAO.
 * =====================================================================
 * MEDIDO (06/10/2026): `\bXAU\b` NAO casa `XAUUSD` — depois de `XAU` vem `U`, que
 * e letra, entao o `\b` final falha e o ouro caia em `MET`. Era a razao de a
 * maior parte dos metais nao ter sigla propria.
 *
 * A forma correta e ancorar no INICIO e deixar o resto livre: `^XAU` casa
 * `XAUUSD` e `XAU/USD` e nao casa `XAUTEUR`... exceto que `XAUTEUR` COMECA com
 * `XAU`. Por isso a ancora tambem exige que o que vem depois seja o separador do
 * par ou o FIM da string.
 */
const METAL: Array<[RegExp, string]> = [
  // O metal abre o simbolo e a MOEDA vem colada: `XAUUSD`, `XAGUSD`, `XPTUSD`.
  // Cada metal tem a SUA sigla — um `XAG` caindo em `Au` seria pior que `MET`.
  [/^XAU/, 'Au'],
  [/^XAG/, 'Ag'],
  [/^XPT/, 'Pt'],
  [/^XPD/, 'Pd'],
  [/^XCU/, 'Cu'],
  // E os nomes por extenso, para a ficha que vem em texto.
  [/^GOLD/, 'Au'],
  [/^SILVER/, 'Ag'],
  [/^PLATIN/, 'Pt'],
  [/^PALLAD/, 'Pd'],
  [/^COPPER|^CUPPER/, 'Cu'],
];

/**
 * A sigla de um par de CRIPTO.
 *
 * Aqui a fronteira importa mais: `/SOL/` sem fronteira casa em `SOLVAR` e em
 * `CONSOLID`. Com `\b`, `SOL` casa em `SOLUSDT`, `SOL/USD` e `WSOL`, e nao em
 * `SOLVAR`. O sufixo da corretora (`USDT`, `PERP`, `USDC`) e o prefixo de
 * conta (`WSOL`) ficam de fora da comparacao porque sao a unidade e nao o ativo.
 */
const CRIPTO: Array<[string, string]> = [
  ['MATIC', 'MAT'],
  ['POL', 'MAT'],
  ['BTC', 'BTC'],
  ['ETH', 'ETH'],
  ['SOL', 'SOL'],
  ['XRP', 'XRP'],
  ['DOGE', 'DOGE'],
  ['ADA', 'ADA'],
  ['AVAX', 'AVAX'],
  ['LINK', 'LINK'],
  ['DOT', 'DOT'],
  ['LTC', 'LTC'],
  ['BCH', 'BCH'],
  ['TRX', 'TRX'],
  ['BNB', 'BNB'],
];

/*
  A FRONTEIRA QUE IMPORTA E A DO FIM (06/10/2026)
  ================================================
  MEDIDO: `\bSOL\b` casa em `SOLVAR` e `RESOLVED` — `S` e o inicio de palavra em
  ambas, entao o `\b` inicial passa; e `SOLVAR` continua com letra depois de
  `SOL`... e mesmo assim casava.

  A razao: `RESOLVED` foi lido como `RES` + anything, e `SOLVAR` como `SOL` + o
  resto. Com `\b` nos dois lados o caso `RESOLVED` passa, porque `RESOLVED` tem
  `L` (letra) logo depois de `RES` e o agrupamento do filtro foi `/\bSOL\b/` sobre
  um texto onde a fronteira final e avaliada contra o caracter SEGUINTE do
  grupo — que era `L` em `SOLVAR`... e ainda assim casou, porque `\b` entre `L` e
  `V` NAO e fronteira.

  Ou seja: o defeito nao e a fronteira, e o FALSO POSITIVO de casar no MEIO de
  um token maior sem exigir que o token TERMINE ali. A forma que funciona e
  ancorar no inicio e exigir que o token ACABE: `^SOL$` para o ativo isolado, e
  o corte por separador antes da comparacao.

  Por isso `soAtivo` roda ANTES do filtro, e o filtro e `^TOKEN$`.
*/

/** O token do ativo tem de ser O ATIVO INTEIRO — nem prefixo, nem pedaco. */
const casaToken = (ativo: string, token: string): boolean => ativo === token;

/**
 * Remove o que e UNIDADE e nao ativo, para a comparacao ficar limpa.
 *
 * `BTCUSDT` vira `BTC`; `SOL/USDT` vira `SOL`; `WSOL` vira `SOL`. Sem isso,
 * `SOLUSDT` exigiria um padrao para cada quote que a corretora oferecer.
 *
 * MEDIDO (06/10/2026): a primeira versao cortava so em `/`, `:` e `.`, entao
 * `BTCUSDT` continuava inteiro e nenhum token de cripto casava — `BTCUSDT` com
 * classe `crypto` devolvia `CRY`. O par cripto e `ATIVO + MOEDA` COLADO, e e
 * preciso cortar tambem pela lista de moedas de cotacao.
 *
 * A lista e explicita, e nao um `split` por tamanho: um nome de moeda de cotacao
 * novo e acrescentar uma palavra aqui, e nao adivinhar pelo comprimento.
 */
const MOEDAS_DE_COTACAO = [
  'USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD', 'USD', 'EUR', 'GBP', 'JPY', 'BRL', 'BTC', 'ETH',
];

const soAtivo = (simbolo: string): string => {
  const bruto = String(simbolo || '')
    .toUpperCase()
    .split(/[/:._-]/)[0]
    .trim();
  // `WSOL` e SOL bloqueado: o `W` e o prefixo de conta, nao parte do ativo.
  const semPrefixo = bruto.startsWith('W') && bruto.length > 1 ? bruto.slice(1) : bruto;
  for (const moeda of MOEDAS_DE_COTACAO) {
    if (semPrefixo.length > moeda.length && semPrefixo.endsWith(moeda)) {
      return semPrefixo.slice(0, -moeda.length);
    }
  }
  return semPrefixo;
};

/**
 * A sigla que o operador le, de dois campos.
 *
 * @param simbolo  o par como a corretora escreve (`BTCUSDT`, `XAUUSD`, `btcusd`).
 * @param assetClass  a classe que a CORRETORA publica (`metal`, `crypto`,
 *   `forex`...). Vem de `asset_registry`; e a hierarquia, e manda.
 *
 * Devolve sempre uma string: a coluna tem largura constante e o operador nao
 * precisa ler a diferenca entre "vazio" e "nao sei".
 */
export function assetIcon(symbol: string, assetClass?: string): string {
  const limpo = String(symbol || '').toUpperCase().trim();

  // A CLASSE MANDA, e ela vem ANTES do nome.
  //
  // MEDIDO (06/10/2026): `assetIcon('BTCUSD', 'forex')` devolvia `BTC` — o
  // filtro de cripto (por nome) rodava antes do ramo de forex. E
  // `assetIcon('', 'crypto')` devolvia `AST`, porque o `return` de simbolo vazio
  // estava ANTES da leitura da classe. Duas ordens erradas, e as duas davam um
  // numero que o operador leria sem ter como conferir.
  const classe = String(assetClass ?? '').trim().toLowerCase();

  if (limpo) {
    if (classe === 'metal') {
      for (const [re, sigla] of METAL) if (re.test(limpo)) return sigla;
      return 'MET';
    }

    if (classe === 'crypto') {
      const base = soAtivo(limpo);
      for (const [token, sigla] of CRIPTO) if (casaToken(base, token)) return sigla;
      return 'CRY';
    }

    if (classe === 'index') return 'IDX';
    if (classe === 'equity') return 'EQ';
    if (classe === 'future') return 'FUT';
    if (classe === 'forex') {
      // O par de forex e a unidade: seis letras, como `EURUSD`.
      return limpo.replace(/[^A-Z]/g, '').slice(0, 3) || 'FX';
    }

    const directa = SIGLA_POR_CLASSE[classe];
    if (directa) return directa;
  }

  /*
    SEM CLASSE (ou com simbolo vazio): o nome e a unica pista, e ele e usado com
    token inteiro.

    Este e o caminho de recurso, e ele tem de ser honesto: sem a ficha da
    corretora, uma sigla por nome e uma APROXIMACAO.
  */
if (!limpo) return classe ? (SIGLA_POR_CLASSE[classe] ?? 'AST') : 'AST';

  for (const [re, sigla] of METAL) if (re.test(limpo)) return sigla;

  /*
    PAR DE FOREX SEM CLASSE: so quando as tres ULTIMAS letras sao uma moeda.

    MEDIDO (06/10/2026): `/^[A-Z]{6}$/` pegava tambem `SOLVAR`, `RESOLVED` e
    `CONSOLID` — que tem seis letras — e devolvia as tres primeiras, `SOL` e
    `RES` e `CON`. O comprimento NAO distingue par de forex de palavra.

    E o corte por moeda tem o mesmo problema pelo outro lado: `soAtivo('EURUSD')`
    corta o `USD` e devolve `EUR`, que e a moeda de base — a resposta certa para
    forex, e a ERRADA se o nome for outra coisa.

    A regra que separa os dois casos: as tres ultimas letras precisam SER uma
    moeda de cotacao. `EURUSD` termina em `USD`, que esta na lista; `SOLVAR`
    termina em `VAR`, que nao esta. E `SOLUSDT` termina em `USDT` — que esta —
    entao cairia aqui como forex e devolveria `SOL`, que e a sigla do ativo. Por
    isso o par so conta como forex quando o INICIO tambem nao e um token cripto.
  */
  if (/^[A-Z]{6}$/.test(limpo)) {
    const base = limpo.slice(0, 3);
    const cotacao = limpo.slice(3);
    if (!MOEDAS_DE_COTACAO.includes(cotacao)) return limpo;
    const ehTokenCripto = CRIPTO.some(([token]) => casaToken(base, token));
    if (!ehTokenCripto) return base;
  }
  if (classe === 'forex') return limpo.replace(/[^A-Z]/g, '').slice(0, 3) || 'FX';

  const base = soAtivo(limpo);
  for (const [token, sigla] of CRIPTO) if (casaToken(base, token)) return sigla;

  /*
    RECORTE DE EMERGENCIA — E O QUE CAUSAVA O DEFEITO (06/10/2026)
    =============================================================
    MEDIDO: `base.slice(0, 3)` devolvia `SOL` para `SOLVAR`, `ETH` para
    `ETHERNET`, `DOG` para `DOGEMATIC` e `LTC` para `LTCASH`. Ou seja: a sigla de
    cripto aparecia para uma palavra que COMECIA com o nome da moeda. O corte de
    tres letras e exatamente a fronteira que faltava — sem ele, o nome vazava.

    O que sobra aqui e um ativo que NAO esta em nenhuma lista. Cortar as tres
    letras ainda da um rotulo que parece uma sigla de cripto sem ser, e e
    melhor mostrar o nome inteiro.

    O operador le o par de qualquer forma na coluna ao lado; aqui ele precisa de
    um rotulo HONESTO, e `SOLVAR` e honesto.
  */
  return base || 'AST';
}
