/*
  HORA DO SERVIDOR DA CORRETORA (23/10/2026)
  ==========================================
  MEDIDO nesta maquina, conta XMGlobal-MT5: o tick do EURUSD veio com
  `time` = 2026-10-23T23:14:19 e o UTC real era 20:14:19. O `deal.time` do MT5
  e a hora de PAREDE do servidor (UTC+3 aqui) codificada como se fosse UTC.

  Formatado no fuso da maquina (UTC-3), o MESMO deal que o MT5 mostra as
  `23:14:19` aparecia as `17:14:19` na tela — e, cruzando a meia-noite, no DIA
  anterior. O gateway passou a mandar `time_server` com o carimbo literal do
  MT5 (`2026.10.05 01:46:43`); quando ele existe, e ele que a tela usa.

  Cripto nao tem esse campo: o `executedAt` dessas corretoras e UTC de verdade,
  e ali formatar no fuso da maquina e o certo.
*/

/** Só a HORA, como a captura do MT5: `01:46:43`. */
export function hora(v?: string): string {
  if (!v) return '';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('pt-BR');
}

/** Data e hora completas, para o `title` de quem precisa do valor inteiro. */
export function stamp(v?: string): string {
  if (!v) return '';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('pt-BR');
}

/**
 * A hora da linha: a do SERVIDOR quando existe, senao a do fuso da maquina.
 * `horarioServidor` vazio (`''`) e ausencia — nunca um horario inventado.
 */
export function horaDaLinha(l: { horario: string; horarioServidor?: string }): string {
  const srv = String(l.horarioServidor ?? '').trim();
  if (srv.length >= 19) return srv.slice(11, 19);
  return hora(l.horario);
}

/** Data e hora completas da abertura, com a mesma preferencia. */
export function stampDaLinha(l: { horario: string; horarioServidor?: string }): string {
  const srv = String(l.horarioServidor ?? '').trim();
  return srv || stamp(l.horario);
}

/**
 * `YYYY-MM-DD` de uma data do historico.
 *
 * O carimbo do MT5 (`2026.10.05 01:46:43`) NAO e ISO: `new Date` devolve
 * Invalid Date com os pontos, e todos os grupos cairiam em "sem-data". O
 * carimbo ja e a DATA DO SERVIDOR, entao a chave sai por corte de string, sem
 * conversao de fuso que traria o dia errado de volta.
 */
export function chaveDia(valor: string): string {
  if (!valor) return 'sem-data';
  const carimbo = /^(\d{4})\.(\d{2})\.(\d{2})/.exec(valor);
  if (carimbo) return `${carimbo[1]}-${carimbo[2]}-${carimbo[3]}`;
  const d = new Date(valor);
  if (Number.isNaN(d.getTime())) return 'sem-data';
  const mes = String(d.getMonth() + 1).padStart(2, '0');
  const dia = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mes}-${dia}`;
}
