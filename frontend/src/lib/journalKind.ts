/**
 * O TIPO DA LINHA DO JOURNAL — medido, nao presumido
 * =================================================
 *
 * MEDIDO na captura de 08/10/2026 14:20 (Terminal ao vivo) e no
 * `MQL5\Logs\20261008.log`:
 *
 * ```
 * 14:20:25  INFO   QQ 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) [RECOVERY]
 * 14:20:25  ERROR  GD 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) AI: OK | Failures: 0 | Error:
 * 14:20:25  ERROR  CI 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) Indicators: OK | Failures: 0 | Error:
 * 14:20:25  ERROR  NR 0 14:20:22.295 XAU_AI_PRO (BTCUSD,M5) Broker: OK | Failures: 0 | Error:
 * ```
 *
 * **Sete checks 100% OK marcados ERROR.** O classificador antigo casava a
 * PALAVRA: `/error|fail/i` acha `Failures` e `Error:` — que sao NOME DE CAMPO
 * da linha de saude, impressos em toda linha, com saude ou nao. E o formato
 * vem do produtor, `RecoveryManager.mqh:621`:
 *
 * ```mql5
 * "  %s: %s | Failures: %d | Error: %s\n"
 * ```
 *
 * O valor e o que vem DEPOIS do nome do campo. Ler o nome e ler o rotulo, nao
 * o estado — AGENTS.md §5, a regra que mais caro neste projeto.
 *
 * O mesmo classificador erra no outro sentido tambem. Medido nas 200.185 linhas
 * do EA nesta janela:
 *
 * | tag | ocorrencias | o que e | o painel dizia |
 * |---|---|---|---|
 * | `[SAFETY]` | 63.837 | trava de margem/seguranca | INFO |
 * | `[CIRCUIT]` | 29.574 | disjuntor de spread | INFO |
 * | `[BACKUP]` | 1.865 | `FAIL \| copiados=9 \| falhas=98` | INFO |
 * | `[VALIDATION]` | 30 | `1 BLOCKED` | INFO |
 * | `[CRITICAL]` | 70 | `Execution: PASS` | **TRADES** |
 *
 * Entao o operador via VERMELHO no que estava saudavel e nao via o que estava
 * bloqueando. O painel mostra 14 linhas de 200.185.
 */

export type JournalKind = 'TRADES' | 'WARN' | 'ERROR' | 'INFO';

/**
 * Vocabulario real do EA, contado em `MQL5\Logs\20261008.log`.
 * Nao e lista de palavras em ingles: sao as ETIQUETAS que o produtor escreve.
 * Medido: [SAFETY] 63837 · [CIRCUIT] 29574 · [BACKUP] 1865 · [RECOVERY] 1811
 * · [OPTIONAL] 100 · [CRITICAL] 70 · [VERSION] 60 · [NOTIFY] 51 · [INIT] 40
 * · [CONFIG] 40 · [VALIDATION] 30 · [SCHEDULER] 20 · [CHECKLIST] 20
 * · [BENCHMARK] 20 · [AI] 20 · [EXECUTION] 10 · [DATABASE] 10 · [FAILMODE] 10
 * · [TELEMETRY] 10 · [DIAG] 10 · [SYNC] 10 · [DAILYRISK] 10 · [MARGIN] 10
 * · [STATS] 10 · [ANTILOOP] 10 · [RETRY] 10 · [QUALITY] 10 · [ADX] [RSI] [TREND]
 */
const SEVERIDADE_POR_TAG: Record<string, JournalKind> = {
  // Trava que impediu operacao. O painel antigo dizia INFO.
  SAFETY: 'WARN',
  CIRCUIT: 'WARN',
  VALIDATION: 'WARN',
  OPTIONAL: 'WARN',
  ANTILOOP: 'WARN',
  RETRY: 'WARN',
  MARGIN: 'WARN',
  DAILYRISK: 'WARN',
  // Falha medida, com numero: `FAIL | copiados=9 | falhas=98`.
  BACKUP: 'ERROR',
  CRITICAL: 'ERROR',
  FAILMODE: 'ERROR',
  DATABASE: 'ERROR',
  // `[CRITICAL] Execution: PASS` e um check que passou. O painel antigo
  // classificava como TRADES por causa da palavra `Execution`.
  EXECUTION: 'INFO',
  RECOVERY: 'INFO',
  VERSION: 'INFO',
  NOTIFY: 'INFO',
  INIT: 'INFO',
  CONFIG: 'INFO',
  SCHEDULER: 'INFO',
  CHECKLIST: 'INFO',
  BENCHMARK: 'INFO',
  AI: 'INFO',
  TELEMETRY: 'INFO',
  DIAG: 'INFO',
  SYNC: 'INFO',
  STATS: 'INFO',
  QUALITY: 'INFO',
  ADX: 'INFO',
  RSI: 'INFO',
  TREND: 'INFO',
};

/**
 * Veredito explicito, quando existe. Precisa ser o VALOR, com fronteira de
 * palavra: `FAIL` casa `FAILURE`/`falhas` e `FAIL:` casa o campo `Failures:`.
 */
const VEREDITO: Array<[RegExp, JournalKind]> = [
  [
    /\bFAIL(ED|URE)?\b|\bfalhou\b|\bfalhas?\b|\bBLOCKED\b|\bbloquead[oa]\b|\b(erro|erros|error|errors)\b/i,
    'ERROR',
  ],
  [/\bWARN(ING)?\b|\bALERT\b|\bATEN[CÇ][AÃ]O\b|\bAVISO\b/i, 'WARN'],
];

/** Veredito de check explicito: `PASS`, `OK`. Vence a palavra do rotulo. */
const PASSOU = /\b(PASS|PASSOU|OK|OK\b|TUDO (OK|CERTO))\b/i;

/** `Failures: 3` — o NUMERO e o estado, o nome do campo nao e. */
function falhasDeclaradas(linha: string): number | null {
  const m = linha.match(/Failures:\s*(\d+)/i);
  return m ? Number(m[1]) : null;
}

/**
 * `Error: <texto>` — o TEXTO DEPOIS do dois-pontos e o estado.
 *
 * Devolve `null` quando o rotulo NAO existe. `''` nao serve: `'' !== null` e
 * verdadeiro, e a linha entrava no ramo da saude como se declarasse erro —
 * foi o primeiro defeito deste modulo, e o classificador devolvia INFO para
 * TUDO.
 */
function erroDeclarado(linha: string): string | null {
  const m = linha.match(/Error:\s*(.*)$/i);
  return m ? m[1].trim() : null;
}

/** `[TAG]` — a etiqueta que o produtor escreve, depois do nome do simbolo. */
function tagDaLinha(linha: string): string | null {
  const m = linha.match(/XAU_AI_PRO\s*\([^)]*\)\s*\[([A-Z_]+)\]/i);
  if (m) return m[1].toUpperCase();
  const solto = linha.match(/(?:^|\s)\[([A-Z_]{2,})\]/);
  return solto ? solto[1].toUpperCase() : null;
}

/**
 * O tipo da linha. Le o VALOR do que o produtor escreveu.
 *
 * Ordem deliberada: o veredito explicito e o numero declarado vencem a
 * palavra, porque sao o estado; a etiqueta do EA vence a palavra solta; e so
 * entao se olha o texto, porque e o que resta.
 */
export function classificarJournal(mensagem: string): JournalKind {
  const linha = String(mensagem ?? '').trim();
  if (!linha) return 'INFO';

  // 1. A linha de saude: `AI: OK | Failures: 0 | Error:`. O NUMERO e o TEXTO
  //    depois do rotulo. `Failures: 0 | Error:` vazio e PASS, e nao ERROR.
  //    So entra aqui se UM dos dois rotulos existir — e o ramo devolve sempre,
  //    para que a palavra `Error` do campo nao vaze para o passo 3.
  const falhas = falhasDeclaradas(linha);
  const erro = erroDeclarado(linha);
  if (falhas !== null || erro !== null) {
    if (falhas !== null && falhas > 0) return 'ERROR';
    if (erro) return 'ERROR';
    return 'INFO';
  }

  // 2. A etiqueta do produtor. `[CRITICAL] Execution: PASS` e INFO: o check
  //    passou, e a palavra `Execution` nao faz dele uma operacao — nem a
  //    etiqueta `[CRITICAL]`, que aqui nomeia a ETAPA, nao o resultado dela.
  //    O veredito da propria linha vence a severidade nominal da etiqueta.
  const tag = tagDaLinha(linha);
  const pelaTag = tag ? SEVERIDADE_POR_TAG[tag] : undefined;
  if (pelaTag) {
    if ((pelaTag === 'ERROR' || pelaTag === 'WARN') && PASSOU.test(linha)) return 'INFO';
    return pelaTag;
  }

  // 3. Veredito explicito com fronteira de palavra.
  for (const [re, kind] of VEREDITO) {
    if (re.test(linha)) {
      if (kind === 'ERROR' && PASSOU.test(linha) && !/\bfalhas?\b|\bFAIL\b/i.test(linha)) {
        return 'INFO';
      }
      return kind;
    }
  }

  // 4. Acao de mercado de verdade, e nao a palavra `close` dentro de um texto.
  if (/\b(order (sent|filled|closed|opened)|BUY|SELL|fill|executed|deal)\b/i.test(linha)) {
    return 'TRADES';
  }
  return 'INFO';
}