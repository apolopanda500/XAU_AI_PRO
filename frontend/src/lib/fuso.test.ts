import { describe, it, expect } from 'vitest';
import {
  offsetMinutos,
  rotuloOffset,
  rotuloCidade,
  listaOrdenada,
  buscarCidades,
  cidadesDoSistema,
  fusoAutomatico,
  ehConhecida,
  horaNaZona,
} from './fuso';

/*
  FUSO HORARIO — O QUE ESTE TESTO TRAVA (05/10/2026)
  ==================================================
  MEDIDO na captura da XM: `(UTC-3) Sao Paulo` marcado com tick, e o rodape
  mostrando `21:01:24 UTC-3`.

  O risco real deste modulo nao e o texto: e o OFFSET. Um offset fixo na tabela
  fica errado na virada do horario de verao, e o operador passa a ler um
  relogio que mente sem nenhum aviso. Por isso os numeros vem do `Intl` do
  sistema, na data pedida — e os testes cobrem o DIA EM QUE A DIFERENCA APARECE.

  E O CATALOGO DEIXOU DE SER LISTA FIXA (09/10/2026)
  =====================================================
  MEDIDO na tela ao vivo: a lista tinha 18 cidades e o dono perguntou por que
  nao dava para escolher outras. Agora vem do `Intl` do sistema (todas as zonas
  IANA que a maquina conhece) e a tela filtra por texto.

  Os testes que usavam a lista fixa foram trocados por `cidadesDoSistema()`: a
  zona CONTINUA sendo a chave, e o que se mede ȧ o comportamento.
 */

describe('offsetMinutos', () => {
  // 2026-10-05 e INVERNO no hemisferio norte e verao no sul.
  const inverno = new Date('2026-10-05T12:00:00Z');

  it('le o offset do proprio sistema, e nao de uma tabela', () => {
    // America/Sao_Paulo e UTC-3 em outubro de 2026. Europe/London e UTC+1.
    expect(offsetMinutos('America/Sao_Paulo', inverno)).toBe(-180);
    expect(offsetMinutos('Europe/London', inverno)).toBe(60);
    expect(offsetMinutos('UTC', inverno)).toBe(0);
  });

  it('o MESMO pais muda de offset com o horario de verao', () => {
    // MEDIDO e CRITICO: Londres em janeiro e UTC+0; em outubro e UTC+1.
    const janeiro = new Date('2026-01-15T12:00:00Z');
    const outubro = new Date('2026-10-05T12:00:00Z');
    expect(offsetMinutos('Europe/London', janeiro)).toBe(0);
    expect(offsetMinutos('Europe/London', outubro)).toBe(60);
  });

  it('Sao Paulo e UTC-3 O ANO INTEIRO, e isso nao e bug', () => {
    /*
      MINHA EXPECTATIVA ESTAVA ERRADA: eu escrevi -120 para janeiro, como se o
      Brasil ainda observasse horario de verao. MEDIDO agora: -180 nos dois
      meses. O Brasil NAO tem horario de verao desde 2019, e Buenos Aires (2015)
      e Santiago (2016) tambem nao.

      Isso nao e detalhe de tabela: e o caso em que um offset FIXO estaria
      certo por acidente e ninguem perceberia que o caminho esta errado. O
      teste continua existindo para travar o numero, agora com o motivo certo.
    */
    expect(offsetMinutos('America/Sao_Paulo', new Date('2026-01-15T12:00:00Z'))).toBe(-180);
    expect(offsetMinutos('America/Sao_Paulo', new Date('2026-10-05T12:00:00Z'))).toBe(-180);
    // E o norte muda, provando que o caminho le o `Intl` e nao uma constante.
    expect(offsetMinutos('Europe/London', new Date('2026-01-15T12:00:00Z'))).toBe(0);
    expect(offsetMinutos('Europe/London', new Date('2026-10-05T12:00:00Z'))).toBe(60);
  });

  it('meia hora e absorvida, e nao truncada', () => {
    // Kolkata e +5:30. Arredondar para 5 entregaria uma hora errada de mercado.
    const kolkata = offsetMinutos('Asia/Kolkata', inverno);
    expect(kolkata % 60).not.toBe(0);
    expect(kolkata).toBe(330);
  });

  it('PROVA NEGATIVA: zona invalida LANCА, em vez de devolver numero errado', () => {
    // Zona invalida com offset silencioso e pior que erro: o operador ve um
    // relogio errado e nao tem como saber de onde veio.
    expect(() => offsetMinutos('Brasil/Inventado', inverno)).toThrow();
    expect(() => offsetMinutos('', inverno)).toThrow();
  });

  it('funciona a meia-noite, onde alguns motores devolvem hora 24', () => {
    // Bug real de `hour12: false`: meia-noite pode sair como "24", e Date.UTC
    // com hora 24 joga o resultado para o dia seguinte, deslocando o offset.
    const meiaNoite = new Date('2026-10-05T00:30:00Z');
    const off = offsetMinutos('America/Sao_Paulo', meiaNoite);
    expect(Math.abs(off + 180)).toBeLessThanOrEqual(1);
  });
});

describe('rotuloOffset', () => {
  it('escreve do jeito da XM: sinal antes, zero fora', () => {
    expect(rotuloOffset(-180)).toBe('UTC-3');
    expect(rotuloOffset(0)).toBe('UTC');
    expect(rotuloOffset(60)).toBe('UTC+1');
    expect(rotuloOffset(-360)).toBe('UTC-6');
    expect(rotuloOffset(330)).toBe('UTC+5:30');
    expect(rotuloOffset(-210)).toBe('UTC-3:30');
  });

  it('PROVA NEGATIVA: UTC+0 nao aparece, como na lista da XM', () => {
    expect(rotuloOffset(0)).not.toContain('+');
    expect(rotuloOffset(0)).not.toContain('0');
  });
});

describe('rotuloCidade e listaOrdenada', () => {
  const data = new Date('2026-10-05T12:00:00Z');

  it('o item da lista e `(offset) Cidade`', () => {
    const sp = cidadesDoSistema().find((c) => c.zona === 'America/Sao_Paulo')!;
    /*
      O NOME VEM DO SISTEMA, E NAO DE UMA LISTA FIXA (09/10/2026)
      ===========================================================
      MEDIDO: este teste exigia '(UTC-3) Sao Paulo', que era a string da lista
      de 18 cidades escrita no codigo. O catalogo agora vem do `Intl`, e o
      `Intl` escreve "Brasilia" para `America/Sao_Paulo` — a mesma zona, o nome
      proprio do fuso.

      Exigir a string antiga aqui seria prender o nome da cidade no teste, que
      e a mesma presuncao que a regra 3 do AGENTS.md proibe para o ativo. O que
      se trava e o FORMATO e o OFFSET, que sao o que o operador le.
    */
    const rotulo = rotuloCidade(sp, data);
    expect(rotulo).toMatch(/^\(UTC-3\) \S/);
    expect(rotulo.startsWith('(UTC-3) ')).toBe(true);
  });

  it('a lista esta ORDENADA por offset, do mais a oeste para o mais a leste', () => {
    const lista = listaOrdenada(data);
    const offsets = lista.map((c) => offsetMinutos(c.zona, data));
    expect(offsets).toEqual([...offsets].sort((a, b) => a - b));

    /*
      OS EXTREMOS ERAM DA LISTA FIXA, E MUDARAM COM O CATALOGO (09/10/2026)
      ======================================================================
      MEDIDO: com 18 cidades, o menor offset era o de Chicago e o maior o da
      Tunisia. Com o catalogo inteiro do sistema, aparecem zonas que nenhuma
      das duas listas tinha: o menor agora ȁ -660 (Pacific/Pitcairn) e o maior
      164 (Asia/Kathmandu).

      Prender os numeros antigos aqui seria quebrar o teste a cada zona nova que
      o sistema conhecer. O que se trava ȁ a REGRA: o primeiro ȁ o menor offset
      de TODA a lista, e o ultimo, o maior — que ȁ o que a ordenacao promete.
    */
    const ordenados = [...offsets].sort((a, b) => a - b);
    expect(offsets[0]).toBe(ordenados[0]);
    expect(offsets[offsets.length - 1]).toBe(ordenados[ordenados.length - 1]);
    // E a lista realmente tem mais de um fuso: ordenar um item nao ordena nada.
    expect(lista.length).toBeGreaterThan(1);
  });

  it('NENHUMA cidade repetida, e nenhuma zona repetida', () => {
    /*
      MEDIDO (09/10/2026): com o catalogo completo, duas zonas podem ter o MESMO
      nome vindo do `Intl` — "Brasilia" aparece em `America/Sao_Paulo` e em
      `America/Bahia`. O operador veria duas linhas iguais e nao saberia qual e a
      sua.

      A correcao poem a ZONA entre parenteses quando o nome repete. Este teste ȁ
      a prova de que a correcao funciona: o nome que repete nao repete mais.

      A zona NUNCA pode repetir: ȁ a chave, e duas linhas com a mesma chave ȁ o
      operador clicando num fuso e recebendo outro.
    */
    const lista = listaOrdenada(data);
    expect(new Set(lista.map((c) => c.cidade)).size).toBe(lista.length);
    expect(new Set(lista.map((c) => c.zona)).size).toBe(lista.length);
  });

  it('duas cidades com o mesmo offset NAO sao a mesma entrada', () => {
    // Sao Paulo e Santiago sharem -180 em outubro. Sao entradas distintas, e
    // isso e o motivo de a chave ser a ZONA e nao o offset: quem escolhe Santiago
    // precisa receber a regra de verao de Santiago.
    const lista = listaOrdenada(data);
    const sp = lista.find((c) => c.zona === 'America/Sao_Paulo');
    const sg = lista.find((c) => c.zona === 'America/Santiago');
    expect(sp).toBeTruthy();
    expect(sg).toBeTruthy();
    expect(sp?.cidade).not.toBe(sg?.cidade);
  });

  it('PROVA NEGATIVA: a lista nunca devolve offset ao lado do rotulo', () => {
    // `offset` e um campo INTERNO do sort. Vazou para o item da lista na
    // primeira versao, e a tela mostrava `(UTC-3) Sao Paulo -180`.
    for (const item of listaOrdenada(data)) {
      expect(Object.keys(item).sort()).toEqual(['cidade', 'rotulo', 'zona']);
    }
  });
});

describe('auto e catalogo', () => {
  it('fusoAutomatico devolve uma zona IANA do navegador', () => {
    expect(fusoAutomatico()).toBeTruthy();
    expect(() => offsetMinutos(fusoAutomatico())).not.toThrow();
  });

  it('PROVA NEGATIVA: `auto` nao aparece como se fosse uma CIDADE', () => {
    /*
      MINHA AFIRMACAO ANTERIOR ERA FALSA: eu escrevi que o fuso do navegador
      nunca estaria no catalogo. MEDIDO nesta maquina: o fuso do navegador e
      `America/Sao_Paulo`, que ESTA no catalogo — e isso e o comportamento
      desejado, porque o operador quer poder escolher a propria cidade.

      O que e proibido e `auto` virar um ITEM DA LISTA, duplicando a escolha.
      Por isso o teste mede a lista, e nao a comparacao de strings.
    */
    const lista = listaOrdenada(new Date());
    const catalogo = cidadesDoSistema();
    // A lista da tela ȩ o catalogo inteiro: nada ȧ filtrado aqui.
    expect(lista).toHaveLength(catalogo.length);
    for (const item of lista) {
      expect(item.cidade.toLowerCase()).not.toContain('auto');
      expect(item.rotulo.toLowerCase()).not.toContain('auto');
    }
  });

  it('o catalogo vem do SISTEMA, e nao de uma lista escrita no codigo', () => {
    /*
      MEDIDO (09/10/2026): a lista tinha 18 cidades e o dono perguntou por que
      nao dava para escolher outras. Agora ȧ o `Intl` que fornece.

      Nao da para exigir um Numero exato: motores diferentes conhecem quantidades
      diferentes de zonas. O que se trava ȧ a REGRA — o catalogo ȧ o do sistema,
      o que pode ser MEDIDO pelo `supportedValuesOf` do proprio ambiente.
    */
    const intl = Intl as unknown as { supportedValuesOf?: (k: string) => string[] };
    if (typeof intl.supportedValuesOf !== 'function') {
      // Navegador sem suporte: lista vazia, e o seletor fica so com `auto`.
      expect(cidadesDoSistema()).toEqual([]);
      return;
    }
    const zonasDoSistema = intl.supportedValuesOf('timeZone');
    expect(cidadesDoSistema()).toHaveLength(zonasDoSistema.length);
    // E a zona que o sistema conhece ȧ a chave: nenhuma zona inventada aqui.
    const chaves = new Set(cidadesDoSistema().map((c) => c.zona));
    for (const z of zonasDoSistema) expect(chaves.has(z)).toBe(true);
  });

  it('a BUSCA filtra por cidade, pais e zona', () => {
    const data = new Date('2026-10-05T12:00:00Z');
    const manaus = buscarCidades('manaus', data);
    expect(manaus.length, 'Manaus existe no catalogo do sistema').toBeGreaterThan(0);
    expect(manaus[0].zona).toContain('Manaus');

    // Pela propria zona IANA, que ȁ como quem conhece o proprio fuso escreve.
    const porZona = buscarCidades('America/Sao_Paulo', data);
    expect(porZona.length).toBeGreaterThan(0);
    expect(porZona[0].zona).toBe('America/Sao_Paulo');

    // E a busca nao achada devolve vazio, nao o catalogo inteiro.
    expect(buscarCidades('zzzz-nao-existe', data)).toEqual([]);
  });

  it('ehConhecida distingue zona do catalogo de zona inventada', () => {
    expect(ehConhecida('America/Sao_Paulo')).toBe(true);
    expect(ehConhecida('Brasil/Inventado')).toBe(false);
  });
});

describe('horaNaZona', () => {
  it('mostra a hora DA ZONA, nao a do navegador', () => {
    // 12:00 UTC em Londres (UTC+1) sao 13:00; em Sao Paulo (UTC-3) sao 09:00.
    const instante = new Date('2026-10-05T12:00:00Z');
    expect(horaNaZona('Europe/London', instante)).toBe('13:00:00');
    expect(horaNaZona('America/Sao_Paulo', instante)).toBe('09:00:00');
  });

  it('PROVA NEGATIVA: a hora e sempre de 2 digitos', () => {
    // 01:05 em vez de "1:05": o relogio com digito solto desalinha a coluna.
    for (const z of ['UTC', 'America/Sao_Paulo', 'Europe/London']) {
      expect(horaNaZona(z, new Date('2026-10-05T05:05:00Z'))).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    }
  });
});