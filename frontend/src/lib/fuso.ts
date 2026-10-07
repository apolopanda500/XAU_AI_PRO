/*
  FUSO HORARIO — CIDADE, OFFSET E MODO AUTOMATICO (05/10/2026)
  ============================================================
  MEDIDO na captura da XM (05/10/2026, 21:01): o seletor e uma LISTA DE
  CIDADES com o offset entre parenteses, e o offset e o que aparece no relogio:

      (UTC-6) Chicago      (UTC-3) Santiago     (UTC+1) Londres
      (UTC-5) Lima         (UTC-3) Sao Paulo     (UTC+2) Amsterdam
      (UTC-4) Caracas      (UTC)   Açores        (UTC+2) Belgrade

  E o rodape mostra `21:01:24 UTC-3`, com `auto` em AZUL — ou seja, o modo
  automatico e o PADRAO e a lista e a excecao. Nao e um seletor de fuso: e um
  override sobre um fuso derivado.

  TRES COISAS QUE ESTE MODULO NAO FAZ, E POR QUE
  -----------------------------------------------
  1. Nao tem tabela de offset..Offset muda com horario de verao: Buenos Aires
     ja foi UTC-3 e e UTC-3, mas o Egito alternou, e a Europa muda em marco e
     em outubro. Um numero fixo errado em meia hora do ano e pior que nenhum
     numero: o operador confia no relogio. Aqui o offset e lido do `Intl` do
     proprio sistema, na DATA PEDIDA.

  2. Nao presume pais do operador. A lista e umaCatalogo explicito de cidades,
     e o padrao e o fuso que o navegador resolveu. Se a lista faltar a cidade
     do operador, ele usa `auto` — que e exatamente o que a XM faz.

  3. Nao aceita string solta. A chave e uma zona IANA valida. `timeZone`
     invalida lanca `RangeError`, e quem chama precisa saber que falhou em vez
     de receber um offset silenciosamente errado.
*/

/** Cidade + zona IANA. A zona e a chave; o nome e o que o operador le. */
export type Cidade = { cidade: string; zona: string };

/**
 * CATALOGO DE CIDADES.
 *
 * Copiado do que a XM oferece na captura, com a zona IANA de cada uma. A
 * ordem aqui nao manda: a tela ordena por offset corrente, que e o que a XM
 * faz (a lista vai de UTC-6 para baixo e continua rolando).
 *
 * Notar que "Sao Paulo" e "Santiago" tem o MESMO offset e nao sao o mesmo
 * fuso — sao zonas IANA diferentes. E por isso que a chave e a zona e nao o
 * offset: dois lugares com o mesmo numero nao podem ser trocados sem mudar o
 * que acontece no horario de verao.
 */
export const CIDADES: Cidade[] = [
  { cidade: 'Chicago', zona: 'America/Chicago' },
  { cidade: 'Lima', zona: 'America/Lima' },
  { cidade: 'Caracas', zona: 'America/Caracas' },
  { cidade: 'Nova York', zona: 'America/New_York' },
  { cidade: 'Buenos Aires', zona: 'America/Argentina/Buenos_Aires' },
  { cidade: 'Santiago', zona: 'America/Santiago' },
  { cidade: 'Sao Paulo', zona: 'America/Sao_Paulo' },
  { cidade: 'Acores', zona: 'Atlantic/Azores' },
  { cidade: 'Reykjavik', zona: 'Atlantic/Reykjavik' },
  { cidade: 'Casablanca', zona: 'Africa/Casablanca' },
  { cidade: 'Dublin', zona: 'Europe/Dublin' },
  { cidade: 'Lagos', zona: 'Africa/Lagos' },
  { cidade: 'Lisboa', zona: 'Europe/Lisbon' },
  { cidade: 'Londres', zona: 'Europe/London' },
  { cidade: 'Tunísia', zona: 'Africa/Tunis' },
  { cidade: 'Amsterdam', zona: 'Europe/Amsterdam' },
  { cidade: 'Belgrado', zona: 'Europe/Belgrade' },
  { cidade: 'Budapeste', zona: 'Europe/Budapest' },
];

const PARTES = new Map<string, Intl.DateTimeFormat>();

function formatador(zona: string): Intl.DateTimeFormat {
  let f = PARTES.get(zona);
  if (!f) {
    f = new Intl.DateTimeFormat('en-US', {
      timeZone: zona,
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    PARTES.set(zona, f);
  }
  return f;
}

/**
 * Offset da zona em MINUTOS, positivo a leste de UTC, NA DATA PEDIDA.
 *
 * `America/Sao_Paulo` em outubro/2026 e -180. `Europe/London` no mesmo dia e
 * +60 — e em julho e +60 tambem, porque aoniao observa horario de verao.
 *
 * Lanca `RangeError` se a zona nao existir. Preferivel a devolver um numero:
 * zona invalida com offset silenciosociao, e o operador ve um relogio errado
 * sem nenhuma pista do por que.
 */
export function offsetMinutos(zona: string, data: Date = new Date()): number {
  const partes = formatador(zona).formatToParts(data);
  const pega = (tipo: string) => Number(partes.find((p) => p.type === tipo)?.value);
  const ano = pega('year');
  const mes = pega('month');
  const dia = pega('day');
  // Alguns motores devolvem hora "24" para meia-noite em hora12:false.
  const hora = pega('hour') % 24;
  const minuto = pega('minute');
  const segundo = pega('second');

  const comoUtc = Date.UTC(ano, mes - 1, dia, hora, minuto, segundo);
  // O instante real, sem a parte de segundos do fuso.
  const instante = Math.floor(data.getTime() / 1000) * 1000;
  return Math.round((comoUtc - instante) / 60000);
}

/**
 * `UTC-3`, `UTC+5:30`, `UTC` — como a XM escreve.
 *
 * O sinal fica ANTES do numero e o zero some: `UTC+0` seria ruido, e o item
 * (UTC) da lista da XM ja aparece sem numero.
 */
export function rotuloOffset(minutos: number): string {
  if (minutos === 0) return 'UTC';
  const sinal = minutos < 0 ? '-' : '+';
  const abs = Math.abs(minutos);
  const h = Math.floor(abs / 60);
  const m = abs % 60;
  return `UTC${sinal}${h}${m ? `:${String(m).padStart(2, '0')}` : ''}`;
}

/** `(UTC-3) Sao Paulo` — o formato do item da lista. */
export function rotuloCidade(c: Cidade, data: Date = new Date()): string {
  return `(${rotuloOffset(offsetMinutos(c.zona, data))}) ${c.cidade}`;
}

/**
 * A lista ORDENADA por offset corrente, como na captura: de UTC-6 para baixo.
 *
 * Ordenar pela zona seria ordenar alfabeticamente e nao ajuda ninguem a achar
 * o proprio fuso. Desempate pelo nome, para a lista nao pular entre renders.
 */
export function listaOrdenada(data: Date = new Date()): Array<Cidade & { rotulo: string }> {
  return CIDADES.map((c) => ({ ...c, rotulo: rotuloCidade(c, data) }))
    .map((c) => ({ ...c, offset: offsetMinutos(c.zona, data) }))
    .sort((a, b) => a.offset - b.offset || a.cidade.localeCompare(b.cidade, 'pt-BR'))
    .map(({ offset: _offset, ...resto }) => resto);
}

/** O fuso que o navegador resolveu, que e o padrao `auto` da XM. */
export function fusoAutomatico(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
}

/** A zona esta no catalogo? `auto` nunca esta, e o que voce quer. */
export function ehConhecida(zona: string): boolean {
  return CIDADES.some((c) => c.zona === zona);
}

/** `HH:MM:SS` NA ZONA ESCOLHIDA — o relogio da XM mostra o fuso escolhido. */
export function horaNaZona(zona: string, data: Date = new Date()): string {
  const partes = formatador(zona).formatToParts(data);
  const pega = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? '00';
  return `${pega('hour')}:${pega('minute')}:${pega('second')}`;
}

export default listaOrdenada;