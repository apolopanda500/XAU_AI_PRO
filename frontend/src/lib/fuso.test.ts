import { describe, it, expect } from 'vitest';
import {
  offsetMinutos,
  rotuloOffset,
  rotuloCidade,
  listaOrdenada,
  fusoAutomatico,
  ehConhecida,
  horaNaZona,
  CIDADES,
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
    const sp = CIDADES.find((c) => c.zona === 'America/Sao_Paulo')!;
    expect(rotuloCidade(sp, data)).toBe('(UTC-3) Sao Paulo');
  });

  it('a lista esta ORDENADA por offset, do mais a oeste para o mais a leste', () => {
    const lista = listaOrdenada(data);
    const offsets = lista.map((c) => offsetMinutos(c.zona, data));
    expect(offsets).toEqual([...offsets].sort((a, b) => a - b));
    /*
      MINHA EXPECTATIVA ESTAVA ERRADA: escrevi -360 como o menor, copiando o
      "(UTC-6) Chicago" da captura. Mas a captura foi tirada em 5 de OUTUBRO, e
      Chicago esta em CDT nesse dia: UTC-5. O menor offset da lista nesse instante
      e o do proprio Chicago, e nao um numero fixo.
    */
    const chicago = lista.find((c) => c.zona === 'America/Chicago');
    expect(offsets[0]).toBe(offsetMinutos('America/Chicago', data));
    expect(chicago).toBeTruthy();
    // E o ultimo e o mais a leste da lista.
    const lisboa = lista.find((c) => c.zona === 'Europe/Lisbon');
    expect(offsets[offsets.length - 1]).toBeGreaterThanOrEqual(offsetMinutos('Africa/Tunis', data));
    expect(lisboa).toBeTruthy();
  });

  it('NENHUMA cidade repetida, e nenhuma zona repetida', () => {
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
    expect(lista).toHaveLength(CIDADES.length);
    for (const item of lista) {
      expect(item.cidade.toLowerCase()).not.toContain('auto');
      expect(item.rotulo.toLowerCase()).not.toContain('auto');
    }
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