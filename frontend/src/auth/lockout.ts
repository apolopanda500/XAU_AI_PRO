export const MAX_TENTATIVAS = 5;
export const CHAVE_LOCKOUT = 'xau-pin-lockout';

const BACKOFF_BASE_MS = 30_000;
const BACKOFF_MAX_MS = 30 * 60_000;

export interface LockoutState {
  falhas: number;
  bloqueadoAte: number;
}

const ZERO: LockoutState = { falhas: 0, bloqueadoAte: 0 };

function armazenamento(): Storage | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage;
  } catch {
    return null;
  }
}

/** Le o estado de bloqueio persistido. Estado corrompido e tratado como zerado. */
export function lerLockout(): LockoutState {
  const store = armazenamento();
  if (!store) return { ...ZERO };
  try {
    const bruto = store.getItem(CHAVE_LOCKOUT);
    if (!bruto) return { ...ZERO };
    const dados = JSON.parse(bruto) as Partial<LockoutState>;
    const falhas = Number(dados?.falhas);
    const bloqueadoAte = Number(dados?.bloqueadoAte);
    if (!Number.isFinite(falhas) || !Number.isFinite(bloqueadoAte)) return { ...ZERO };
    return { falhas: Math.max(0, Math.trunc(falhas)), bloqueadoAte: Math.max(0, bloqueadoAte) };
  } catch {
    return { ...ZERO };
  }
}

function gravar(estado: LockoutState): void {
  const store = armazenamento();
  if (!store) return;
  try {
    if (estado.falhas <= 0 && estado.bloqueadoAte <= 0) store.removeItem(CHAVE_LOCKOUT);
    else store.setItem(CHAVE_LOCKOUT, JSON.stringify(estado));
  } catch {
    /* persistencia indisponivel: o bloqueio vale apenas para a sessao atual */
  }
}

/** Espera progressiva: 30s, 60s, 120s… ate 30 minutos, por ciclo de 5 falhas. */
export function backoffMs(falhas: number): number {
  if (falhas < MAX_TENTATIVAS) return 0;
  const ciclos = Math.floor(falhas / MAX_TENTATIVAS) - 1;
  return Math.min(BACKOFF_BASE_MS * 2 ** ciclos, BACKOFF_MAX_MS);
}

export function estaBloqueado(estado: LockoutState, agora: number): boolean {
  return estado.bloqueadoAte > agora;
}

export function tentativasRestantes(estado: LockoutState): number {
  const resto = estado.falhas % MAX_TENTATIVAS;
  return resto === 0 ? MAX_TENTATIVAS : MAX_TENTATIVAS - resto;
}

/** Registra uma tentativa errada e devolve o novo estado ja com bloqueio aplicado. */
export function registrarFalha(estado: LockoutState, agora: number): LockoutState {
  const falhas = estado.falhas + 1;
  const proximo: LockoutState = { falhas, bloqueadoAte: agora + backoffMs(falhas) };
  gravar(proximo);
  return proximo;
}

/** Limpa o contador apos desbloqueio com sucesso. */
export function limparFalhas(): LockoutState {
  gravar({ ...ZERO });
  return { ...ZERO };
}

export function formatarEspera(ms: number): string {
  const total = Math.max(1, Math.ceil(ms / 1000));
  const min = Math.floor(total / 60);
  const seg = total % 60;
  if (min <= 0) return `${seg}s`;
  return `${min}min ${String(seg).padStart(2, '0')}s`;
}
