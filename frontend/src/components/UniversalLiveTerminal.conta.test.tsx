// @vitest-environment jsdom
/*
  A MARGEM LIVRE NA TELA VEM DA CHAVE QUE O GATEWAY MANDA (09/10/2026)
  ===================================================================
  MEDIDO na captura de 07/10 00:33, no app instalado, na faixa "Terminal ao
  vivo":

      Saldo 2,78 | Patrimonio 8,40 | Flutuante 0,00 | Margem 0,00 | Livre 0,00

  `Livre 0,00` com `Patrimonio 8,40` e um numero que nao existe: em conta com
  posicao fechada a margem livre e o proprio patrimonio.

  A CAUSA, e ela e nome de campo — o AGENTS.md §5
  ====================================================
  PRODUTOR, `backend/mt5_gateway.py:1617`:

      "margin_free": optional_number(getattr(info, "margin_free", None)),

  O MT5 tambem chama assim (`account_info().margin_free`), e o `queries.ts:197`
  le a chave certa no `TelemetrySnapshot`.

  CONSUMIDOR, `UniversalLiveTerminal.tsx`, lia e DECLARAVA `free_margin`:

      free_margin?: number;                                  // o tipo repetia
      const freeMargin = Number(account?.free_margin ?? 0);   // o erro

  Chave inexistente no payload + `?? 0` = `0,00` na tela. Sem excecao, sem log,
  e com o TIPO repetindo o erro, entao `tsc --noEmit` ficava limpo. E o teste
  que existia nao olhava a celula.

  POR QUE ESTE TESTE EXISTE
  =========================
  `UniversalLiveTerminal.journal.test.tsx:30` monta o mock com `margin_free: 0`
  — a chave CERTA — e nunca le `Livre`. O `0` no mock escondia justamente o
  valor que estava quebrado. Um teste que so verifica o que ja funciona nao
  pega o que esta quebrado (AGENTS.md §6).

  Este aqui monta `margin_free` com um valor que NAO E ZERO e exige que ele
  apareca na celula. Se o nome voltar a divergir, a tela volta a `0,00` e este
  teste reprova.

  E O QUE A MARGEM LIVRE DECIDE
  =============================
  `MinFreeMargin` e a trava de risco. MEDIDO em 09/10 na conta 391773676:
  margem livre 15,48 contra piso 10,00. O operador lia `0,00` — que e a leitura
  que diria "a trava esta no chao, e por isso que nada abre". Ele nao conseguia
  ver a folga que existia. Um numero que nunca sai do zero ensina a desconfiar
  da tela inteira (AGENTS.md §9).
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

/*
  O CONTA DA CAPTURA DE 07/10 00:33
  ================================
  `Saldo 2,78 | Patrimonio 8,40 | Flutuante 0,00 | Margem 0,00 | Livre 0,00`.

  A margem livre de 8,40 e o que o MT5 devolve com `POSICOES 0` e margem
  zerada. Nao e valor inventado para o teste passar: e o unico valor que a
  conta da captura poderia ter, e o valor que a tela NAO mostrava.
*/
const contaDaCaptura = {
  login: 391773676,
  server: 'XMGlobal-MT5 14',
  balance: 2.78,
  equity: 8.4,
  profit: 0,
  margin: 0,
  margin_free: 8.4,
  margin_level: 0,
};

const estado = vi.hoisted(() => ({
  conta: {} as Record<string, unknown>,
  criptos: [] as Array<Record<string, unknown>>,
}));

vi.mock('../hooks/queries', () => ({
  useCoreStatus: () => ({ data: { pronto: true, ligado: false } }),
  useAccount: () => ({ data: estado.conta }),
  usePositions: () => ({ data: { positions: [] } }),
  useJournal: () => ({ data: { lines: [] }, isFetching: false }),
  useAllCryptoAccounts: () => ({ data: estado.criptos }),
  useAutoState: () => ({ data: null }),
  useUniversalOverview: () => ({ data: { connections: [] } }),
  useUniversalAccount: () => ({ data: {} }),
  useUniversalPositions: () => ({ data: { positions: [] } }),
}));

import UniversalLiveTerminal from './UniversalLiveTerminal';

/** O valor da celula cujo rotulo (`em`) e `rotulo`. */
const celula = (container: HTMLElement, rotulo: string): string => {
  const caixa = Array.from(container.querySelectorAll('.mt-status-strip > span')).find(
    (s) => s.querySelector('em')?.textContent?.trim() === rotulo,
  );
  if (!caixa) throw new Error(`celula nao encontrada na faixa: ${rotulo}`);
  return caixa.querySelector('strong')?.textContent ?? '';
};

describe('a margem livre vem da chave que o PRODUTOR manda', () => {
  beforeEach(() => {
    estado.conta = { ...contaDaCaptura };
  });
  afterEach(cleanup);

  it('PROVA: `Livre` mostra a margem livre que o gateway mandou', () => {
    /*
      `fmtNum` formata em pt-BR com duas casas: 8,4 vira `8,40`.
    */
    const { container } = render(<UniversalLiveTerminal />);
    expect(celula(container, 'Livre')).toBe('8,40');
  });

  it('PROVA: as celulas vizinhas continuam medidas — a correcao nao e achatar', () => {
    /*
      Se a correcao tivesse virado "mostrar o patrimonio quando a chave faltar",
      `Livre` passaria com `8,40` — e a trava de risco passaria a ler o saldo.
      E um chute, e o AGENTS.md §3 proibe exatamente chute em numero que vira
      limite.

      Por isso o saldo tem de continuar 2,78: sao numeros diferentes na captura.
    */
    const { container } = render(<UniversalLiveTerminal />);
    expect(celula(container, 'Saldo')).toBe('2,78');
    expect(celula(container, 'Patrimônio')).toBe('8,40');
    expect(celula(container, 'Livre')).not.toBe(celula(container, 'Saldo'));
  });

  it('PROVA: uma margem livre de verdade, nao zero, nao some da tela', () => {
    /*
      A medida mais proxima do que o operador precisa: o VALOR da trava.
      MEDIDO em 09/10: `MinFreeMargin = 10,0` contra margem livre 15,48.
      Com 15,48 a tela tem de mostrar 15,48.
    */
    estado.conta = { ...contaDaCaptura, margin_free: 15.48 };
    const { container } = render(<UniversalLiveTerminal />);
    expect(celula(container, 'Livre')).toBe('15,48');
  });

  it('PROVA NEGATIVA: com as DUAS chaves e valores diferentes, a tela segue o PRODUTOR', () => {
    /*
      A prova de que o teste acima nao e decorativo.

      Se o componente voltar a ler `free_margin` — e nao e exagero: ja aconteceu, e
      o tipo repetia o erro, entao `tsc` nao reclama —, esta tela passa a
      mostrar `0,00` e o primeiro teste deste arquivo reprova.

      O payload traz as duas chaves de proposito, com numeros diferentes: e o
      unico jeito de a tela dizer QUAL nome ela esta lendo. O gateway real so
      manda uma delas.
    */
    estado.conta = { ...contaDaCaptura, margin_free: 15.48, free_margin: 0 };
    const { container } = render(<UniversalLiveTerminal />);

    // A chave que o PRODUTOR manda (`backend/mt5_gateway.py:1617`).
    expect(celula(container, 'Livre')).toBe('15,48');
    // E nao a que o PRODUTOR nunca mandou.
    expect(celula(container, 'Livre')).not.toBe('0,00');
  });

  it('`0,00` de verdade continua `0,00` — o operador distingue os dois zeros', () => {
    /*
      Este e o ponto que a prova anterior nao cobre, e ele importa mais.

      Antes da correcao, `0,00` significava DUAS coisas ao mesmo tempo: margem
      livre zero, e chave nao encontrada. O operador nao tinha como saber qual
      das duas estava olhando — e a segunda e um defeito do app, nao da conta.

      Depois da correcao, `margin_free: 0` do gateway e margem livre zero, e
      isso e verdade. Este teste trava essa distincao: o `0,00` que aparece vem
      do numero, nao do `?? 0`.

      E o outro lado: chave AUSENTE tambem da `0,00`, porque e o que o MT5
      devolve quando nao ha margem. Nao ha como — nem faz sentido — pintar
      `--` no lugar de um zero legitimo.
    */
    estado.conta = { ...contaDaCaptura, margin_free: 0 };
    const comZero = render(<UniversalLiveTerminal />);
    expect(celula(comZero.container, 'Livre')).toBe('0,00');

    // O valor zero veio da conta, e nao do fallback: com 15,48 a MESMA celula
    // muda. Um `0,00` fixo na regra nao mudaria.
    estado.conta = { ...contaDaCaptura, margin_free: 15.48 };
    const comFolga = render(<UniversalLiveTerminal />);
    expect(celula(comFolga.container, 'Livre')).toBe('15,48');
    expect(celula(comFolga.container, 'Livre')).not.toBe(celula(comZero.container, 'Livre'));
  });

  it('PROVA NEGATIVA: trocar `Livre` por `Patrimonio` NAO passa a medicao', () => {
    /*
      A outra forma de "consertar": fazer a celula mostrar `equity` porque os
      dois valem 8,40 na captura. A medicao de `15,48` acima REPROVA isso — e e
      por isso que ela existe com um valor que `equity` nao tem.
    */
    estado.conta = { ...contaDaCaptura, margin_free: 15.48 };
    const { container } = render(<UniversalLiveTerminal />);

    expect(celula(container, 'Livre')).toBe('15,48');
    // `Patrimonio` segue sendo o outro numero, e o teste le a celula certa.
    expect(celula(container, 'Patrimônio')).toBe('8,40');
  });

  it('a conta da captura mede a tela inteira, e nao so a celula quebrada', () => {
    /*
      Se `Livre` sumisse da faixa, os testes acima passariam por acidente ao
      procurar por `Saldo`. Este `expect` diz que a conta tem oito casas medidas
      e que `Livre` e uma delas.
    */
    const { container } = render(<UniversalLiveTerminal />);
    const casas = Array.from(container.querySelectorAll('.mt-status-strip > span')).map(
      (s) => s.querySelector('em')?.textContent?.trim(),
    );
    for (const r of ['Conta', 'Servidor', 'Saldo', 'Patrimônio', 'Margem', 'Livre', 'Posições']) {
      expect(casas, `falta a casa ${r}`).toContain(r);
    }
  });

  it('PROVA: SEM conta lida, o numero e `--` — e nao `0,00`', () => {
    /*
      MEDIDO no app instalado, 19:37, com o MT5 FECHADO:

          SALDO --  PATRIMONIO --  FLUTUANTE 0,00  MARGEM 0,00  LIVRE 0,00

      `fmtNum(account?.balance)` devolve `--` — `fmtNum(undefined)` nao e numero.
      Mas `freeMargin` e `margin` ja tinham virado `0` pelo `?? 0`, e
      `fmtNum(0)` escreve `0,00`.

      O operador lia "a margem livre e zero" numa tela que, duas casas antes,
      dizia que nao leu conta nenhuma. E `Livre` e a casa que a trava de risco
      `MinFreeMargin` le — um zero nao medido ali e o numero mais caro da tela.
    */
    estado.conta = null as never;
    const { container } = render(<UniversalLiveTerminal />);

    expect(celula(container, 'Livre')).toBe('--');
    expect(celula(container, 'Margem')).toBe('--');
    expect(celula(container, 'Flutuante')).toBe('--');
    // E continua coerente com as casas que ja diziam `--`.
    expect(celula(container, 'Saldo')).toBe('--');
  });

  it('PROVA NEGATIVA: `0,00` de verdade continua `0,00`', () => {
    /*
      A distincao que o teste anterior nao cobre e que importa mais.

      Antes, `0,00` significava DUAS coisas: margem livre zero, e chave nao
      encontrada. O operador nao tinha como saber qual das duas estava olhando —
      e a segunda e um defeito do app, nao da conta.

      Depois, `margin_free: 0` do gateway e margem livre zero, e isso e verdade.
      Este teste trava essa distincao: o `--` so aparece quando a conta nao
      veio, e o zero lido continua zero.
    */
    estado.conta = { ...contaDaCaptura, margin_free: 0, margin: 0 };
    const { container } = render(<UniversalLiveTerminal />);
    expect(celula(container, 'Livre'), 'zero lido virou nao-lido').toBe('0,00');
  });
});

/*
  A LINHA DE CONTA FALHA DIZ O MOTIVO (12/10/2026)
  =================================================
  MEDIDO nas capturas do dono (Operacoes): quatro linhas WARN — "MEXC / Spot
  indisponível", "MEXC / Futuros indisponível", e o mesmo para BINANCE — sem
  dizer POR QUE. Chave invalida, IP bloqueado, sem permissao e gateway fora
  produziam a mesma linha, e o operador nao tinha por onde comecar (a rede,
  medida do repo, responde 200 nas duas — nao e conectividade).

  O gateway devolve o motivo; o `catch` do `useAllCryptoAccounts` o engolia.
  Agora ele viaja em `error` e a linha o mostra, cortado em 90.
*/
describe('a conta de exchange que falha diz o motivo na linha', () => {
  beforeEach(() => {
    estado.conta = { ...contaDaCaptura };
    estado.criptos = [];
  });
  afterEach(cleanup);

  it('PROVA: falha COM motivo mostra o motivo na linha', () => {
    estado.criptos = [
      { broker: 'mexc', market: 'crypto-spot', ok: false, balance: null, currency: 'USDT', assets: [], error: 'API key invalida (401)' },
    ];
    const { container } = render(<UniversalLiveTerminal />);
    const corpo = container.textContent ?? '';
    expect(corpo).toContain('Spot indisponível');
    expect(corpo).toContain('API key invalida (401)');
  });

  it('PROVA: falha SEM motivo mantem o texto antigo, sem dois-pontos solto', () => {
    estado.criptos = [
      { broker: 'binance', market: 'crypto-futures', ok: false, balance: null, currency: 'USDT', assets: [] },
    ];
    const { container } = render(<UniversalLiveTerminal />);
    const corpo = container.textContent ?? '';
    expect(corpo).toContain('Futuros indisponível');
    expect(corpo).not.toContain('Futuros indisponível:');
  });

  it('PROVA NEGATIVA: motivo longo e cortado — a linha continua sendo uma linha', () => {
    estado.criptos = [
      { broker: 'mexc', market: 'crypto-spot', ok: false, balance: null, currency: 'USDT', assets: [], error: `x`.repeat(200) },
    ];
    const { container } = render(<UniversalLiveTerminal />);
    const corpo = container.textContent ?? '';
    expect(corpo).toContain('Spot indisponível: ' + 'x'.repeat(90));
    expect(corpo).not.toContain('x'.repeat(91));
  });
});