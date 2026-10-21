// NENHUM ATIVO PRESUMIDO NO FONTE DO APP (09/10/2026)
// ===================================================
// A regra e do AGENTS.md §3: "Simbolo vazio e RECUSA COM MOTIVO, nunca um ativo
// padrao. Uma lista fixa de ativos contra os milhares que a corretora oferece e
// exatamente essa presuncao."
//
// O backend ja tem a trava dele (`tests/test_ai_inference.py::
// TestNenhumAtivoPresumido`). O FRONTEND nao tinha nenhuma: qualquer arquivo
// `.tsx` podia voltar a assumir um ativo e o app todo continuava verde.
//
// MEDIDO em 09/10/2026, varrendo `frontend/src`:
//   CODIGO — 2 presuncoes, ambas `|| 'XAUUSD'`:
//       RobotMarketBar.tsx:42   simbolo = (selectedSymbol || 'XAUUSD')
//       AIControlTab.tsx:40     selectedSymbol = ... || 'XAUUSD'
//   CODIGO — 1 classe adivinhada pelo NOME (proibido pelo §3):
//       ModelCover.tsx:42       /US30|US500|NAS|SPX|DAX/ -> 'indice'
//   TEXTO — 3 exemplos de ativo em placeholder:
//       StatusBar.tsx:215       placeholder="ex.: XAUUSD"
//       HistoryTab.tsx:357-360  'Opcional (ex.: BTCUSD)' e 'Obrigatorio (ex.: BTCUSDT)'
//   As demais ~160 linhas sao COMENTARIO DE MEDICAO — o registro do que foi
//   medido na conta real — e teste. Nenhuma delas escolhe ativo.
//
// Este teste mede CODIGO, nao comentario: ele le o fonte, tira comentario e
// docstring, e reprova qualquer nome de ativo que sobre. Se alguem escrever de
// novo `|| 'XAUUSD'`, ele reprova no mesmo minuto.
//
// POR QUE `import.meta.glob` E NAO `node:fs`
// ==========================================
// `@types/node` nao esta instalado, e `process.cwd()` / `__dirname` /
// `node:path` nao tem tipagem — os tres reprovariam o `tsc --noEmit`, que e
// gate. MEDIDO em 09/10/2026: as tres formas foram tentadas e as tres falharam.
// O `import.meta.glob` com `?raw` entre o fonte como TEXTO no proprio bundle do
// teste, sem depender de caminho nenhum: e o que `theme/fluidness.test.ts` ja
// usa para varrer CSS.
import { describe, expect, it } from 'vitest';

/**
 * Todo o fonte do app, como texto, menos os proprios testes.
 *
 * MEDIDO (09/10/2026): o padrao de exclusao do glob, escrito aqui dentro do
 * comentario, continha `*` `*` `/` — e o `/` depois de dois `*` FECHA o bloco
 * de comentario no meio. O resto da frase virou codigo e o arquivo reprovou
 * com `Unexpected token`. Por isso o padrao esta escrito no codigo abaixo, e
 * nao neste texto: comentario de bloco nao aceita o proprio fechamento dentro.
 *
 * A exclusao dos testes e necessaria e honesta: este arquivo lista os nomes de
 * ativo para poder acusa-los, e sem excluir ele se reprovaria. Teste PODE
 * nomear ativo — teste nao opera, ele prova a regra; e o teste do backend usa
 * nome de ativo justamente para dizer que ele e recusado.
 */
const FONTES = import.meta.glob('./**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const NAO_E_TESTE = (caminho: string) => !/\.test\./.test(caminho);

/**
 * IDs de tema que tinham nome de ativo, e que NAO podem voltar (10/10/2026).
 *
 * MEDIDO: os dois temas se chamavam `xau_dark` e `btc_dark` — apelidos de COR com
 * nome de ativo. Renomeados para a cor que descrevem (`dourado_dark`,
 * `laranja_dark`), com migracao em `useTheme.ts` para a preferencia ja salva.
 *
 * Estao fora do `NOMES_DE_ATIVO` porque `XAU` e `BTC` sozinhos nao podem entrar
 * la: o nome do PRODUTO ȁ "XAU AI PRO" e apareceria falso positivo em todo
 * canto. Aqui a lista e dos IDs exatos que foram medidos como violacao, e so
 * deles — o que a regra probe ȁ o apelido com nome de ativo, nao a sigla.
 */
const IDS_DE_TEMA_PROIBIDOS = ['xau_dark', 'btc_dark', 'wallpaper-xau', 'wallpaper-btc'];

/** Nomes que corretoras publicam. Nomes, nao classes: 'crypto' nao entra. */
const NOMES_DE_ATIVO = [
  'XAUUSD', 'XAGUSD', 'XPTUSD', 'XPDUSD',
  'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'ADAUSD', 'BNBUSD', 'BTCUSDT',
  'EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'NZDUSD', 'USDCHF',
  'MULTI_METALS', 'MULTI_FIAT', 'MULTI_ENERGY', 'MULTI_INDEX', 'MULTI_CRYPTO',
  'NAS100', 'US30', 'US500', 'SPX500', 'GER30', 'UK100', 'JPN225', 'BRENT', 'WTI',
];

/**
 * CODIGO sem comentario, sem docstring — assim como no backend.
 *
 * O que importa e o codigo. Comentario e docstring sao onde o registro da
 * medicao fica: apaga-los seria apagar a prova do que foi medido.
 */
const soCodigo = (fonte: string): string => {
  let fora = '';
  let i = 0;
  while (i < fonte.length) {
    const dois = fonte.slice(i, i + 2);
    if (dois === '/*') {
      const fim = fonte.indexOf('*/', i + 2);
      i = fim === -1 ? fonte.length : fim + 2;
      continue;
    }
    if (dois === '//') {
      const fim = fonte.indexOf('\n', i);
      i = fim === -1 ? fonte.length : fim;
      continue;
    }
    if (dois === '"""' || dois === "'''") {
      const fim = fonte.indexOf(dois, i + 3);
      i = fim === -1 ? fonte.length : fim + 3;
      continue;
    }
    fora += fonte[i];
    i += 1;
  }
  return fora;
};

const arquivos = () => Object.keys(FONTES).filter(NAO_E_TESTE);

describe('o frontend NAO presume nenhum ativo', () => {
  it('a varredura acha o fonte do app, e nao pasta vazia', () => {
    // Sem este, um glob que nao casasse nada varreria zero arquivo e o teste
    // passaria VAZIO — e um teste que passa vazio e pior que um que reprova.
    expect(arquivos().length, 'o glob nao trouxe nenhum fonte').toBeGreaterThan(100);
    expect(
      Object.keys(FONTES).some((c) => c.endsWith('RobotMarketBar.tsx')),
      'nao achou um componente conhecido: o glob esta errado',
    ).toBe(true);
  });

  it('nenhum ID de tema com nome de ativo', () => {
    /*
      Os dois temas `xau_dark` e `btc_dark` foram renomeados para
      `dourado_dark` e `laranja_dark` em 10/10/2026.

      REGRA: o ID velho pode existir em UM lugar so — o mapa de MIGRACAO de
      `hooks/useTheme.ts`, e so como CHAVE, para a preferencia ja salva do
      operador nao voltar para `dark`. Em qualquer outro arquivo, ou mais de uma
      vez, ȁ violacao: o mapa existe para migrar, nao para manter os dois nomes
      vivos.
    */
    const achados: string[] = [];
    for (const caminho of arquivos()) {
      const codigo = soCodigo(FONTES[caminho]);
      for (const id of IDS_DE_TEMA_PROIBIDOS) {
        const quantas = codigo.split(id).length - 1;
        if (quantas === 0) continue;
        const ehOmapaDeMigracao =
          caminho.endsWith('hooks/useTheme.ts') && quantas === 1;
        if (!ehOmapaDeMigracao) {
          achados.push(`${caminho} -> ${id} (${quantas}x)`);
        }
      }
    }
    expect(achados, `ID de tema com nome de ativo:\n${achados.join('\n')}`).toEqual([]);

    // E o tema atual ȁ o novo.
    expect(
      Object.keys(FONTES).some(
        (c) => c.endsWith('hooks/useTheme.ts') && FONTES[c].includes('dourado_dark'),
      ),
      'o tema dourado nao existe mais',
    ).toBe(true);
  });

  it('PROVA NEGATIVA: o ID de tema velho fora do mapa reprova', () => {
    // O codigo que existia e foi renomeado. Ele TEM de reprovar.
    for (const velho of IDS_DE_TEMA_PROIBIDOS) {
      expect(IDS_DE_TEMA_PROIBIDOS.includes(velho)).toBe(true);
      expect("theme: 'dourado_dark'".includes(velho)).toBe(false);
    }
  });

  it('nenhum nome de ativo no codigo do app', () => {
    const achados: string[] = [];
    for (const caminho of arquivos()) {
      const linhas = soCodigo(FONTES[caminho]).split('\n');
      linhas.forEach((linha, i) => {
        for (const nome of NOMES_DE_ATIVO) {
          if (linha.includes(nome)) {
            achados.push(`${caminho}:${i + 1}  ${nome}  ${linha.trim().slice(0, 90)}`);
            break;
          }
        }
      });
    }
    expect(
      achados,
      `nome de ativo no codigo do frontend:\n${achados.join('\n')}`,
    ).toEqual([]);
  });

  it('PROVA NEGATIVA: a trava pega os `|| \'XAUUSD\'` de verdade', () => {
    // A regra nao pode ser um regex que nao casa. Aqui esta o codigo que foi
    // MEDIDO em 09/10/2026 nos arquivos citados acima — ele TEM de reprovar.
    const linhas = [
      "const simbolo = (selectedSymbol || 'XAUUSD').toUpperCase();",
      "const selectedSymbol = useAppStore((s) => s.selectedSymbol) || 'XAUUSD';",
      '<input placeholder="ex.: XAUUSD" />',
      'const lista = ["XAUUSD", "EURUSD"];',
      "if (/US30|US500|NAS/.test(s)) return 'indice';",
    ];
    for (const linha of linhas) {
      const bate = NOMES_DE_ATIVO.some((nome) => linha.includes(nome));
      expect(bate, `nao acusou: ${linha}`).toBe(true);
    }
  });

  it('PROVA NEGATIVA: a trava nao acusa o que nao e ativo', () => {
    // Uma trava que reprova codigo certo vira trava desligada. Estes sao os
    // valores que o app USA e que nao sao nome de ativo.
    const naoAtivos = [
      'const market = escopo.market;',
      "brokerLabel('mt5')",
      "const timeframes = ['M1','H1','D1'];",
      "assetIcon(simbolo, 'crypto')",
      "const valor = '0,01';",
      "const classe = 'forex';",
    ];
    for (const linha of naoAtivos) {
      const bate = NOMES_DE_ATIVO.some((nome) => linha.includes(nome));
      expect(bate, `acusou o que nao e ativo: ${linha}`).toBe(false);
    }
  });

  it('o mapeador de sigla nao tem lista de tokens de ativo', () => {
    /*
      MEDIDO (09/10/2026): o `lib/assetIcons.ts` tinha uma lista de tokens
      (`BTC`, `SOL`, `DOGE`...) e uma lista de moedas de cotacao (`USDT`, `USD`,
      `BRL`...) usadas para ADIVINHAR onde o ativo terminava. Foi removido pela
      decisao do dono — "deixar o catalogo sem icone apenas lista opcional".

      A trava de nomes completos acima NAO pega token curto: `'BTC'` nao contem
      `BTCUSD`. Por isso esta, medida no arquivo que decide sigla.

      Um token curto solto no codigo de decisoes e o que o AGENTS.md §3 nomeia:
      sem fronteira de palavra, `SOL` casa dentro de `SOLVAR`.
    */
    const TOKENS = [
      'XAU', 'XAG', 'XPT', 'XPD', 'XCU', 'GOLD', 'SILVER', 'PLATIN', 'PALLAD',
      'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'BNB', 'MATIC', 'POL',
      'AVAX', 'LINK', 'DOT', 'LTC', 'BCH', 'TRX',
      'USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD',
    ];

    const entrada = Object.entries(FONTES).find(([caminho]) =>
      caminho.endsWith('lib/assetIcons.ts'),
    );
    expect(entrada, 'nao achou o mapeador de sigla').toBeTruthy();

    /*
      Aqui a medida e por SUBSTRING, e nao por string citada: o codigo antigo
      escrevia os tokens em regex (`/^XAU/`, `/^SILVER/`), e o token nao ficava
      entre aspas — a prova com aspas nao acusava nada.

      Este arquivo e o unico onde isso nao gera falso positivo: o mapeador nao
      tem nenhuma razao para conter token de ativo, e o que ele contera sao
      nomes de classe (`metal`, `crypto`), que nao estao na lista.
    */
    const codigo = soCodigo(entrada![1]);
    const achados = TOKENS.filter((t) => codigo.includes(t));
    expect(
      achados,
      `lista de tokens no mapeador de sigla: ${achados.join(', ')}`,
    ).toEqual([]);
  });

  it('PROVA NEGATIVA: a trava pega a lista de tokens de volta', () => {
    /*
      O codigo que existia e foi removido. Cada linha TEM de reprovar — inclusive
      a de regex, que foi a forma que o codigo antigo usava quase sempre.
    */
    const linhas = [
      "['BTC', 'BTC'],",
      "const MOEDAS = ['USDT', 'USD', 'BRL'];",
      "[/^XAU/, 'Au'],",
      'if (/^SOL/.test(base)) return token;',
    ];
    const TOKENS = ['BTC', 'SOL', 'XAU', 'USDT', 'USD', 'BRL'];
    for (const linha of linhas) {
      const bate = TOKENS.some((t) => linha.includes(t));
      expect(bate, `nao acusou: ${linha}`).toBe(true);
    }
  });
});
