import { describe, expect, it } from 'vitest';
import { classificarJournal } from './journalKind';

/*
  O TIPO DA LINHA DO JOURNAL — trava com PROVA NEGATIVA
  =====================================================
  As mensagens abaixo sao COPIAS LITERAIS de `MQL5\Logs\20261008.log`
  (08/10/2026). Nao sao inventadas para o teste passar: sao o que o produtor
  escreveu, e o classificador precisa ler o valor delas.

  Cada bloco tem o caso que DEVE passar e o caso que DEVE reprovar. Um teste
  que so passa nao prova que a guarda funciona (AGENTS.md §6).
*/

const SAUDE_OK =
  'GD 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) AI: OK | Failures: 0 | Error:';
const SAUDE_COM_FALHA =
  'GK 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) Dataset: FAIL | Failures: 3 | Error:';
const SAUDE_COM_ERRO =
  'NR 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) Broker: OK | Failures: 0 | Error: timeout na API';

/*
  PROVA DE QUE A TRAVA FUNCIONA: o classificador ANTIGO, aplicado nas MESMAS
  linhas, tem de discordar. Se o antigo tambem passasse, o teste nao estaria
  provando nada — seria verde sem verificar (AGENTS.md §6).

  Declarado no TOPO porque os blocos de 10/10/2026 usam antes da definicao
  antiga — `const` usado antes de declarar quebra o modulo inteiro.
*/
const ANTIGO = (message: string): string =>
  /trade|order|execut|buy|sell|close|fill/i.test(message)
    ? 'TRADES'
    : /warn|alert/i.test(message)
      ? 'WARN'
      : /error|fail/i.test(message)
        ? 'ERROR'
        : 'INFO';

describe('a linha de saude nao pode ser ERROR quando o valor diz OK', () => {
  it('Failures: 0 e Error: vazio e PASS, mesmo com as palavras Failures e Error no texto', () => {
    // PROVA NEGATIVA: o classificador antigo (`/error|fail/i`) dava ERROR aqui,
    // e era o que a tela mostrava em 7 linhas 100% saudaveis.
    expect(classificarJournal(SAUDE_OK)).toBe('INFO');
    expect(classificarJournal(SAUDE_OK)).not.toBe('ERROR');
  });

  it('Failures: 3 e ERROR de verdade — o numero manda', () => {
    expect(classificarJournal(SAUDE_COM_FALHA)).toBe('ERROR');
  });

  it('Error: com texto depois e ERROR — o texto depois do rotulo e o estado', () => {
    expect(classificarJournal(SAUDE_COM_ERRO)).toBe('ERROR');
  });

  it('PROVA NEGATIVA: trocar so o numero para 0 tem de virar INFO', () => {
    const antes = SAUDE_COM_FALHA.replace('Failures: 3', 'Failures: 0').replace('FAIL', 'OK');
    expect(classificarJournal(antes)).toBe('INFO');
  });
});

describe('a linha de saude no plural nao pode ser ERROR quando o valor diz 0', () => {
  // MEDIDO na captura de 10/10/2026 20:16 (Terminal ao vivo, ETHUSD H1).
  // Tres checks 100% saudaveis marcados ERROR — o classificador casava a
  // PALAVRA `errors` sem olhar o numero depois do nome do campo.
  const JSON_OK = 'DK 0 21:33:18.416 XAU_AI_PRO (ETHUSD,H1) JSON errors: 0';
  const PYTHON_OK = 'RP 0 21:33:18.416 XAU_AI_PRO (ETHUSD,H1) Python errors: 0';
  const INDICATOR_OK = 'CH 0 21:33:18.416 XAU_AI_PRO (ETHUSD,H1) Indicator errors: 0';

  it('JSON/Python/Indicator errors: 0 e INFO, nao ERROR', () => {
    expect(classificarJournal(JSON_OK)).toBe('INFO');
    expect(classificarJournal(PYTHON_OK)).toBe('INFO');
    expect(classificarJournal(INDICATOR_OK)).toBe('INFO');
  });

  it('PROVA NEGATIVA: o numero manda — errors: 2 e ERROR de verdade', () => {
    expect(classificarJournal(JSON_OK.replace('errors: 0', 'errors: 2'))).toBe('ERROR');
  });

  it('PROVA NEGATIVA: o classificador antigo errava nestas linhas', () => {
    for (const linha of [JSON_OK, PYTHON_OK, INDICATOR_OK]) {
      expect(ANTIGO(linha)).toBe('ERROR');
    }
  });
});

describe('o dump do HealthMonitor: "<modulo>: N falhas" nao e ERROR quando N=0', () => {
  // MEDIDO: `HealthMonitorSummary()` (Monitoring/HealthMonitor.mqh:762) emite
  // `<modulo>: N falhas` por modulo do watchdog (ATR, ADX, RSI, AI, PYTHON,
  // CSV, JSON). Modulo saudavel (N=0) e INFO; so N>0 e falha de verdade.
  //
  // E a MESMA familia do `errors: 0` de 10/10, na variante que o produtor
  // escreve em portugues: o classificador casava a PALAVRA `falhas` no passo 3
  // (VEREDITO) sem olhar o numero depois dos dois-pontos — vermelho no saudavel.
  const MODULO_OK = 'GD 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) AI: 0 falhas';
  const MODULO_FALHA = 'GD 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) RSI: 23 falhas';

  it('AI: 0 falhas e INFO, nao ERROR', () => {
    expect(classificarJournal(MODULO_OK)).toBe('INFO');
    expect(classificarJournal(MODULO_OK)).not.toBe('ERROR');
  });

  it('PROVA NEGATIVA: o numero manda — RSI: 23 falhas e ERROR de verdade', () => {
    expect(classificarJournal(MODULO_FALHA)).toBe('ERROR');
  });

  it('PROVA NEGATIVA: trocar so o numero 0 por 23 no modulo OK vira ERROR', () => {
    expect(classificarJournal(MODULO_OK.replace('0 falhas', '23 falhas'))).toBe('ERROR');
  });
});

describe('as travas do EA sao WARN, nao INFO', () => {
  // MEDIDO: [SAFETY] 63.837 e [CIRCUIT] 29.574 em 200.185 linhas. O painel
  // antigo mostrava as duas como INFO — o operador via o caso saudavel em
  // vermelho e a trava em branco.
  it('[SAFETY] Free margin low e travado: WARN', () => {
    expect(classificarJournal('[SAFETY] Free margin low: 0.23/20.00')).toBe('WARN');
  });

  it('[CIRCUIT] SPREAD ALTO e travado: WARN', () => {
    expect(
      classificarJournal('[CIRCUIT] SPREAD ALTO | USDSEK | Bloqueio delegado ao ValidateTrade'),
    ).toBe('WARN');
  });

  it('PROVA NEGATIVA: [MARGIN] tambem e WARN, e nao INFO', () => {
    expect(classificarJournal('[MARGIN] Free: 0.11 | Level: 100.55%')).toBe('WARN');
  });

  it('PROVA NEGATIVA: [VALIDATION] 1 BLOCKED nao pode ser INFO', () => {
    expect(classificarJournal('[VALIDATION] 1 BLOCKED - verificar antes de operar')).not.toBe('INFO');
  });
});

describe('falha medida com numero e ERROR', () => {
  it('[BACKUP] FAIL | falhas=98 e ERROR — o painel antigo dizia INFO', () => {
    expect(classificarJournal('[BACKUP] FAIL | copiados=9 | falhas=98')).toBe('ERROR');
  });

  it('PROVA NEGATIVA: o mesmo backup sem falha volta a ser INFO', () => {
    expect(classificarJournal('[BACKUP] PASS | copiados=107 | falhas=0')).toBe('INFO');
  });
});

describe('check que passou nao e operacao', () => {
  it('[CRITICAL] Execution: PASS e INFO — a palavra Execution nao faz trade', () => {
    // PROVA NEGATIVA: o classificador antigo casava /execut/i e dava TRADES.
    expect(classificarJournal('[CRITICAL] Execution: PASS - Bid/Ask disponiveis')).toBe('INFO');
    expect(classificarJournal('[CRITICAL] Execution: PASS - Bid/Ask disponiveis')).not.toBe('TRADES');
  });

  it('[EXECUTION] SmartExecution initialized e INFO', () => {
    expect(classificarJournal('[EXECUTION] SmartExecution initialized')).toBe('INFO');
  });
});

describe('acao de mercado de verdade continua TRADES', () => {
  it('ordem enviada e TRADES', () => {
    expect(classificarJournal('[TRADE] order sent EURUSD SELL 0.01')).toBe('TRADES');
  });

  it('PROVA NEGATIVA: so a palavra close num texto nao cria trade', () => {
    expect(classificarJournal('Pressione para fechar a janela do terminal')).toBe('INFO');
  });
});

/* ANTIGO declarado no topo (usado pelos blocos de 10/10/2026). */

describe('prova negativa: o classificador antigo erra nestas linhas', () => {
  const CASOS: Array<[string, string]> = [
    [SAUDE_OK, 'INFO'],
    ['[SAFETY] Free margin low: 0.23/20.00', 'WARN'],
    ['[CIRCUIT] SPREAD ALTO | USDSEK | Bloqueio delegado ao ValidateTrade', 'WARN'],
    ['[BACKUP] FAIL | copiados=9 | falhas=98', 'ERROR'],
    ['[CRITICAL] Execution: PASS - Bid/Ask disponiveis', 'INFO'],
    ['[MARGIN] Free: 0.11 | Level: 100.55%', 'WARN'],
  ];

  it('o novo concorda com o esperado em TODOS os casos', () => {
    for (const [linha, esperado] of CASOS) {
      expect(`${linha} -> ${classificarJournal(linha)}`).toBe(`${linha} -> ${esperado}`);
    }
  });

  it('o ANTIGO discorda em pelo menos um — a guarda tem o que segurar', () => {
    const divergentes = CASOS.filter(([linha, esperado]) => ANTIGO(linha) !== esperado);
    expect(divergentes.length).toBeGreaterThan(0);
    // Registrado para o relatorio: quantas linhas o painel antigo mentia.
    console.log(
      `antigo discorda em ${divergentes.length} de ${CASOS.length}: ` +
        divergentes.map(([l, e]) => `${ANTIGO(l)} (era) != ${e} (e) em "${l.slice(0, 40)}"`).join(' | '),
);
  });
});

describe('rotulo vazio e a fronteira de palavra', () => {
  it('string vazia e INFO, sem lancar', () => {
    expect(classificarJournal('')).toBe('INFO');
    expect(classificarJournal('   ')).toBe('INFO');
    expect(classificarJournal(undefined as unknown as string)).toBe('INFO');
  });

  it('a palavra Error no rotulo de saude ja foi tratada; fora dele e erro', () => {
    // `Error:` followed de nada e o campo da linha de saude — tratado no
    // passo 1, que devolve sempre. Fora do formato, `error` em texto livre e
    // erro de verdade, e a palavra com fronteira conta.
    expect(classificarJournal('campo Error nao preenchido')).toBe('ERROR');
    expect(classificarJournal('campo Error')).toBe('ERROR');
  });

  it('PROVA NEGATIVA: trocar o rotulo de saude por texto normal muda o tipo', () => {
    expect(classificarJournal('Erro ao ler dataset')).toBe('ERROR');
    expect(classificarJournal('Dataset lido com 1.354.289 linhas')).toBe('INFO');
  });
});