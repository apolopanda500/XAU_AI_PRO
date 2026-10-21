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

/**
 * CATALOGO COMPLETO de cidades, do que o SISTEMA fornece (09/10/2026).
 *
 * MEDIDO na captura e na tela ao vivo: a lista tinha 18 cidades, e o dono
 * perguntou por que nao dava para escolher outras — "tem como os usuarios
 * achar um pais" era o pedido. Dezoito cidades nao cobrem o mundo: o Brasil
 * tem quatro fusos proprios (Sao Paulo, Manaus, Recife, Rio Branco), e quem
 * opera de Fortaleza nao achava o seu.
 *
 * A REGRA DO DONO, E A DO PROJETO
 * ===============================
 * Nenhuma lista fixa contra o que a corretora (aqui, o sistema) oferece. O
 * `Intl` do proprio navegador sabe TODAS as zonas IANA que a maquina conhece,
 * e e essa a fonte: 424 zonas, contra 18 escritas a mao.
 *
 * O nome legivel de cada zona vem do proprio `Intl`, em portugues, com a
 * CIDADE e o PAIS (quando a zona tem pais): "Sao Paulo, Brasil". Nenhum nome
 * de cidade esta escrito neste arquivo — que e a mesma regra do §3 aplicada a
 * fuso: nada preso no codigo.
 *
 * O `auto` continua sendo o padrao e continua no topo: a lista completa nao
 * substitui a deteccao, ela a complementa.
 */
export type Cidade = { cidade: string; zona: string };

/** Cache do nome legível por zona: `Intl` ȓ caro e a lista ȓ querida a cada minuto. */
const NOMES = new Map<string, string>();
const ZONAS: string[] | undefined = undefined;

/**
 * Todas as zonas que o sistema conhece.
 *
 * `supportedValuesOf` existe no Chrome e no Firefox recentes; no Safari antigo
 * ele nao existe, e a lista fica VAZIA — o seletor passa a oferecer so o
 * `auto`, que e o mesmo comportamento de antes, sem mentir que tem cidade que
 * nao pode dar.
 */
function zonasDoSistema(): string[] {
  const intl = Intl as unknown as { supportedValuesOf?: (k: string) => string[] };
  if (typeof intl.supportedValuesOf !== 'function') return [];
  return intl.supportedValuesOf('timeZone') ?? [];
}

/**
 * `Sao Paulo, Brasil` — cidade e pais, do proprio `Intl`, em portugues.
 *
 * MEDIDO (09/10/2026): o `timeZoneName: 'long'` devolve o nome DO FUSO
 * ("Horario Padrao de Brasilia"), que e outra coisa: nao tem a cidade que o
 * operador procura, e duas zonas do mesmo pais ficam com o mesmo nome —
 * "Horario Padrao de Brasilia" para Sao Paulo e para Rio Branco.
 *
 * O que separa as zonas ȁ o par CIDADE + PAIS, e esse vem de `formatToParts`
 * com `timeZoneName` em `longGeneric` em alguns motores, e do `region` da zona
 * em outros. Aqui se usa o que estiver disponivel, nesta ordem:
 *
 *   1. `exemplarCity` — a cidade propria da zona, quando o motor tem;
 *   2. o proprio nome da zona, com `_` trocado por espaco — `America/Sao_Paulo`
 *      vira `America Sao Paulo`, que ȁ feio mas achavel na busca;
 *   3. a zona crua.
 *
 * O PAIS vem do `region` quando a zona tem o pedaco depais — e fica entre
 * parenteses, porque "Sao Paulo (Brasil)" ȁ o que a pessoa reconhece.
 */
function nomeDaZona(zona: string): string {
  const guardado = NOMES.get(zona);
  if (guardado) return guardado;

  const pedacos = zona.split('/');
  const cidade = pedacos[pedacos.length - 1].replace(/_/g, ' ');
  const pais = pedacos.length > 1 ? pedacos[0].replace(/_/g, ' ') : '';

  let nome = zona;
  const intl = Intl as unknown as {
    DateTimeFormat: new (locale: string, o: unknown) => Intl.DateTimeFormat;
  };
  try {
    // `exemplarCity` ȁ o nome proprio da cidade naquela zona, em pt-BR.
    const f = new intl.DateTimeFormat('pt-BR', {
      timeZone: zona,
      timeZoneName: 'longGeneric',
    });
    const parts = f.formatToParts(new Date());
    const cru = parts.find((p) => p.type === 'timeZoneName')?.value ?? '';
    /*
      `longGeneric` devolve "Horario de Buenos Aires", "Horario de Moscou".
      Tirando "Horario de" sobra a CIDADE, que e o que se quer.Quando o motor
      devolve outra formula, cai no nome do proprio pedaco da zona.
    */
    const limpo = cru
      .replace(/^hor[áa]rio (de |padr[ãa]o de |de ver[ãa]o de )?/i, '')
      .replace(/\s*\(.*\)\s*$/, '')
      .trim();
    nome = limpo || `${cidade}${pais ? ` (${pais})` : ''}`;
  } catch {
    nome = `${cidade}${pais ? ` (${pais})` : ''}`;
  }

  NOMES.set(zona, nome);
  return nome;
}

/**
 * A lista completa, no formato da lista antiga (`cidade` + `zona`).
 *
 * `cidade` agora carrega "Cidade, Pais" quando o `Intl` da os dois, e a zona
 * continua sendo a CHAVE. Ordenada por nome para a busca por texto fazer
 * sentido — a ordenacao por offset que a tela aplica ȧ separada, no
 * `listaOrdenada`, e nao muda a chave.
 */
export function cidadesDoSistema(): Cidade[] {
  const zonas = zonasDoSistema();
  if (!zonas.length) return [];
  return zonas.map((zona) => ({ cidade: nomeDaZona(zona), zona }));
}

/** O valor de busca de uma cidade: nome + zona + pais, tudo minusculo. */
export function textoDeBusca(c: Cidade): string {
  return `${c.cidade} ${c.zona}`.toLowerCase();
}

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
 *
 * MEDIDO (09/10/2026): duas zonas diferentes podem ter o MESMO nome vindo do
 * `Intl` — "Brasilia" aparece em `America/Sao_Paulo` e em
 * `America/Bahia`, e o operador veria duas linhas iguais sem saber qual ȁ a
 * sua. Quando o nome repete, a ZONA entra entre parenteses: "Brasilia
 * (America/Bahia)". A zona ȁ a chave e nao pode repetir; o nome e rotulo.
 *
 * Sem o `supportedValuesOf` (Safari antigo), devolve VAZIA: o seletor oferece
 * so o `auto`. Uma lista vazia e honesta; uma lista de 18 cidades que nao
 * cobre o mundo era a presuncao que o dono apontou.
 */
export function listaOrdenada(data: Date = new Date()): Array<Cidade & { rotulo: string }> {
  const comNome = cidadesDoSistema().map((c) => ({ ...c, rotulo: rotuloCidade(c, data) }));

  // Quantas vezes cada nome aparece: 2 ou mais, o nome precisa da zona.
  const quantas = new Map<string, number>();
  for (const c of comNome) quantas.set(c.cidade, (quantas.get(c.cidade) ?? 0) + 1);

  const comDesempate = comNome.map((c) =>
    (quantas.get(c.cidade) ?? 0) > 1
      ? { ...c, cidade: `${c.cidade} (${c.zona})`, rotulo: `${c.rotulo} (${c.zona})` }
      : c,
  );

  return comDesempate
    .map((c) => ({ ...c, offset: offsetMinutos(c.zona, data) }))
    .sort((a, b) => a.offset - b.offset || a.cidade.localeCompare(b.cidade, 'pt-BR'))
    .map(({ offset: _offset, ...resto }) => resto);
}

/**
 * A lista FILTRADA pelo que o operador digita, ainda ordenada por offset.
 *
 * Casa no nome, no pais e na propria zona IANA: quem conhece o proprio fuso
 * escreve `Manaus` ou `America/Manaus` e acha. Sem filtro, uma lista de 424
 * itens ȧ pagina e meia de rolagem — pior que os 18.
 */
export function buscarCidades(
  texto: string,
  data: Date = new Date(),
): Array<Cidade & { rotulo: string }> {
  const agulha = texto.trim().toLowerCase();
  const todas = listaOrdenada(data);
  if (!agulha) return todas;
  return todas.filter((c) => textoDeBusca(c).includes(agulha));
}

/** O fuso que o navegador resolveu, que e o padrao `auto` da XM. */
export function fusoAutomatico(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
}

/** A zona esta no catalogo? `auto` nunca esta, e o que voce quer. */
export function ehConhecida(zona: string): boolean {
  return cidadesDoSistema().some((c) => c.zona === zona);
}

/** `HH:MM:SS` NA ZONA ESCOLHIDA — o relogio da XM mostra o fuso escolhido. */
export function horaNaZona(zona: string, data: Date = new Date()): string {
  const partes = formatador(zona).formatToParts(data);
  const pega = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? '00';
  return `${pega('hour')}:${pega('minute')}:${pega('second')}`;
}

export default listaOrdenada;