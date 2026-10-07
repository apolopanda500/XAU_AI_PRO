/**
 * Testes do tradutor de eventos do calendário (05/10/2026).
 *
 * O DONO PEDIU: "aba calendario traduzir eventos em portugues".
 *
 * O QUE ESTES TESTES PROVAM, E POR QUE
 * ====================================
 * Um dicionário de tradução é a kind of coisa que "funciona" e mente. O pior
 * defeito possível aqui não é traduzir mal — é traduzir de um jeito que parece
 * certo e está errado, porque o operador confia no que lê. Por isso há:
 *
 *   - casos que travam a tradução dos eventos que aparecem TODA semana;
 *   - a PROVA NEGATIVA: título desconhecido volta em inglês, e a tela marca;
 *   - a garantia de que a sigla NÃO é traduzida (traduzir sigla torna o texto
 *     MENOS reconhecível, não mais);
 *   - a garantia de que nada é inventado: nenhum título vira string vazia.
 */
import { describe, expect, it } from 'vitest';
import { categoriaEvento, eventoTraduzido, traduzirEvento } from './traduzirEvento';

describe('traduzirEvento — os eventos que aparecem toda semana', () => {
  it('traduz a decisão de juros do Fed e as três peças do FOMC', () => {
    expect(traduzirEvento('Fed Interest Rate Decision')).toBe('Decisão de juros do Fed');
    expect(traduzirEvento('FOMC Statement')).toBe('Comunicado do FOMC');
    expect(traduzirEvento('FOMC Press Conference')).toBe('Coletiva de imprensa do FOMC');
    expect(traduzirEvento('FOMC Meeting Minutes')).toBe('Ata da reunião do FOMC');
  });

  it('traduz emprego e desemprego dos EUA', () => {
    expect(traduzirEvento('Non-Farm Employment Change')).toBe(
      'Variação do emprego não agrícola',
    );
    expect(traduzirEvento('Unemployment Rate')).toBe('Taxa de desemprego');
    expect(traduzirEvento('Initial Jobless Claims')).toBe(
      'Pedidos iniciais de auxílio-desemprego',
    );
  });

  it('traduz inflação preservando a sigla IPC', () => {
    expect(traduzirEvento('CPI')).toBe('IPC');
    expect(traduzirEvento('Core CPI')).toBe('Núcleo do IPC');
    expect(traduzirEvento('PPI')).toBe('IPP');
  });

  it('traduz a decisão de juros do BCE, do BoE e do BoJ', () => {
    expect(traduzirEvento('ECB Interest Rate Decision')).toBe('Decisão de juros do BCE');
    expect(traduzirEvento('BOE Official Bank Rate')).toBe(
      'Taxa oficial do Banco da Inglaterra',
    );
    expect(traduzirEvento('BOJ Interest Rate Decision')).toBe('Decisão de juros do Banco do Japão');
  });

  it('traduz o Brasil', () => {
    expect(traduzirEvento('BCB Interest Rate Decision')).toBe(
      'Decisão de juros do Banco Central do Brasil',
    );
    expect(traduzirEvento('Copom Rate Decision')).toBe('Decisão do Copom');
  });

  it('traduz os principais da zona do euro', () => {
    expect(traduzirEvento('German Ifo Business Climate')).toBe(
      'Clima de negócios Ifo da Alemanha',
    );
    expect(traduzirEvento('Eurozone GDP')).toBe('PIB da Zona do Euro');
  });

  it('traduz o Reilly com o nome por extenso', () => {
    // O MT5 e a XM mostram "Ireland"; o operador brasileiro lê "Irlanda".
    // A sigla seria mais curta e pior.
    const t = traduzirEvento('Ireland unemployment rate');
    expect(t).toContain('Irlanda');
    expect(t.toLowerCase()).toContain('desemprego');
  });
});

describe('traduzirEvento — o parêntese do mês', () => {
  it('o mês não vira parte da chave: dois meses, a mesma tradução', () => {
    // O feed manda "Retail Sales (Dec)" numa semana e "(Jan)" na seguinte.
    // Se o mês entrasse na chave, o dicionário precisaria de uma entrada por
    // mês — treze entradas para a mesma frase.
    expect(traduzirEvento('Retail Sales (Dec)')).toBe('Vendas no varejo (dez)');
    expect(traduzirEvento('Retail Sales (Jan)')).toBe('Vendas no varejo (jan)');
  });

  it('traduz o nome do mês em português', () => {
    expect(traduzirEvento('Non-Farm Employment Change (Sep)')).toContain('(set)');
    expect(traduzirEvento('Non-Farm Employment Change (Oct)')).toContain('(out)');
  });

  it('mantém a sigla de variação temporal como a corretora escreve', () => {
    // MoM, QoQ e YoY são de uso corrente em português. Traduzir para "no mês"
    // e "no ano" tornaria o título MENOS comparável com o calendário da XM.
    expect(traduzirEvento('Retail Sales MoM')).toBe('Vendas no varejo MoM');
    expect(traduzirEvento('GDP YoY')).toBe('PIB YoY');
  });
});

describe('traduzirEvento — cobertura por palavra, para evento raro', () => {
  it('traduz o país mesmo sem entrada no dicionário exato', () => {
    const t = traduzirEvento('Swedish Trade Balance');
    expect(t).toContain('Suécia');
    // A ORDEM DAS PALAVRAS fica em inglês nesta camada, e isso é uma limitação
    // declarada, não um defeito escondido. O que não pode acontecer é o termo
    // sumir: o operador precisa achar "balança comercial" para ler o evento.
    expect(t.toLowerCase()).toContain('balança comercial');
  });

  it('traduz o mês de um evento que só existe por palavra', () => {
    const t = traduzirEvento('Turkish CPI (Aug)');
    expect(t).toContain('Turquia');
    expect(t).toContain('ago');
  });
});

// ==========================================================================
// PROVA NEGATIVA — o que o tradutor NÃO pode fazer
// ==========================================================================
describe('traduzirEvento — o que ele NÃO faz', () => {
  it('título desconhecido volta EM INGLÊS, nunca vazio', () => {
    // Evento não reconhecido NÃO pode virar string vazia: o operador precisa
    // saber qual é o evento, mesmo sem entender inglês.
    const t = traduzirEvento('Zorkian Widget Index Release');
    expect(t).toBe('Zorkian Widget Index Release');
    expect(t.length).toBeGreaterThan(0);
  });

  it('eventoTraduzido diz se houve tradução — é o que marca a linha', () => {
    expect(eventoTraduzido('Fed Interest Rate Decision')).toBe(true);
    expect(eventoTraduzido('Zorkian Widget Index Release')).toBe(false);
    expect(eventoTraduzido('')).toBe(false);
  });

  it('NÃO traduz sigla de banco central nem de indicador', () => {
    // Traduzir sigla deixa o título MENOS reconhecável para quem lê calendário
    // todo dia. As siglas são o que o operador procura.
    const t = traduzirEvento('BOJ Governor Ueda speaks');
    expect(t).toContain('BOJ');
    expect(t).not.toContain('Banco do Japão Governor');
    expect(t).toContain('Ueda');
  });

  it('NÃO deixa palavra em inglês com "de" pendurado', () => {
    // Trocar palavra a palavra deixa preposição órfã. A camada de limpeza
    // existe para isso: "Change of" vira "Variação de", não "Variação de
    // unemployment".
    const t = traduzirEvento('Change of Unemployed Persons');
    expect(t).not.toMatch(/\bde (unemployed|persons)\b/i);
    expect(t).not.toMatch(/\s{2,}/);
  });

  it('devolve string para entrada vazia, sem quebrar a tela', () => {
    expect(traduzirEvento('')).toBe('');
    expect(traduzirEvento('   ')).toBe('');
  });
});

describe('categoriaEvento — o que o operador procura antes do nome', () => {
  it('classifica juros, inflação, emprego, atividade e energia', () => {
    expect(categoriaEvento('Fed Interest Rate Decision')).toBe('Juros');
    expect(categoriaEvento('ECB Rate Decision')).toBe('Juros');
    expect(categoriaEvento('CPI MoM')).toBe('Inflação');
    expect(categoriaEvento('Core CPI')).toBe('Inflação');
    expect(categoriaEvento('Non-Farm Employment Change')).toBe('Emprego');
    expect(categoriaEvento('Unemployment Claims')).toBe('Emprego');
    expect(categoriaEvento('Retail Sales MoM')).toBe('Atividade');
    expect(categoriaEvento('German Ifo')).toBe('Atividade');
    expect(categoriaEvento('API Crude Oil Inventories')).toBe('Energia');
  });

  it('devolve vazio quando não é uma categoria conhecida', () => {
    // Vazio é resposta honesta: forçar uma categoria seria inventar.
    expect(categoriaEvento('Zorkian Widget Index Release')).toBe('');
  });
});

// ==========================================================================
// COBERTURA DO FEED REAL (05/10/2026)
// ==========================================================================
// O dono apontou: "nomes dos eventos em outros idiomas e outros PT BR".
//
// MEDIDO: o feed `ff_calendar_thisweek.json` devolveu 82 eventos, e **61 titulos
// distintos cafram fora** das 162 entradas escritas a mao. Cobertura: **16%**.
// Era esse o motivo do calendario parecer poluido.
//
// Este bloco trava a cobertura do que o feed REAL traz. Um dicionario de
// memoria cobre o que a gente imagina que vem; o feed traz o que vem.
const TITULOS_DO_FEED_MEDIDOS = [
  'Bank Holiday', 'Final Services PMI', '10-y Bond Auction',
  'ADP Weekly Employment Change', '30-y Bond Auction', 'OPEC-JMMC Meetings',
  'MI Inflation Gauge m/m', 'ANZ Commodity Prices m/m', 'Spanish Services PMI',
  'German Buba President Nagel Speaks', 'Italian Services PMI',
  'French Final Services PMI', 'German Final Services PMI',
  'Sentix Investor Confidence', 'PPI m/m', 'NZIER Business Confidence',
  'Westpac Consumer Sentiment', 'ANZ Job Advertisements m/m',
  'German Factory Orders m/m', 'BOJ Gov Ueda Speaks', 'French Gov Budget Balance',
  'Construction PMI', 'MPC Member Mann Speaks', 'Housing Equity Withdrawal q/q',
  'Retail Sales m/m', 'Ivey PMI', 'RCM/TIPP Economic Optimism',
  'FOMC Member Bowman Speaks', 'GDT Price Index', 'FOMC Member Schmid Speaks',
  'API Weekly Statistical Bulletin', 'Average Cash Earnings y/y',
  'Leading Indicators', 'German Industrial Production m/m', 'Lloyds HPI m/m',
  'French Trade Balance', 'Foreign Currency Reserves', 'Consumer Credit m/m',
  'RICS House Price Balance', 'MI Inflation Expectations',
  'Economy Watchers Sentiment', 'Gov Board Member Martin Speaks',
  'BOE Credit Conditions Survey', 'FOMC Member Waller Speaks',
  'MPC Member Greene Speaks', 'Eurogroup Meetings', 'MPC Member Pill Speaks',
  'ECB Monetary Policy Meeting Accounts', 'Unemployment Claims',
  'MPC Member Lombardelli Speaks', 'Final Wholesale Inventories m/m',
  'FOMC Member Musalem Speaks', 'Household Spending y/y',
  'Prelim Machine Tool Orders y/y', 'SECO Consumer Climate',
  'Italian Industrial Production m/m', 'ECOFIN Meetings',
  'Prelim UoM Consumer Sentiment', 'Prelim UoM Inflation Expectations',
  'FOMC Member Collins Speaks',
];

describe("traduzirEvento — cobertura do feed real medido", () => {
  it("NAO fica nenhum titulo do feed em ingles", () => {
    const sobrando = TITULOS_DO_FEED_MEDIDOS.filter((t) => !eventoTraduzido(t));
    // Este e o teste do item 1. Antes: 61 sobrando. Agora: zero.
    expect(
      sobrando,
      `titulos do feed que ficaram sem traducao: ${sobrando.join(", ")}`,
    ).toEqual([]);
  });

  it("NAO deixa palavra INGLESA na traducao dos titulos do feed", () => {
    /*
      A lista NAO contem siglas. A primeira versao desta lista tinha `PMI` dentro,
      e o teste acusou 16 titulos — todos legitimos: `PMI` e sigla de uso
      corrente em portugues e o proprio projeto manda preservar sigla. Um teste
      que acusa o comportamento correto e um teste que protege o defeito, com o
      nome de "regressao".
    */
    const PALAVRAS_INGLESAS =
      /\b(Retail|Industrial|Production|Employment|Sales|Consumer|Credit|Factory|Orders|Holiday|Final|Services|Balance|Expectations|Inflation|Confidence|Sentiment|Manufacturing|Wholesale|Inventories|Housing|Current|Account|Building|Permits|Existing|Speaks|Change|Weekly|Prelim|Gauge|Holiday|Claims|Spending|Bank|Member|Governor|Prices|Commodity|Advertisements|Withdrawals|Wage|Tool|Machine|Reserve|Currency|Foreign|Watchers|Bulletin|Statistical|Meetings|Accounts|Meeting|Assumptions|Observations|Earnings|Average)\b/;
    const sujos = TITULOS_DO_FEED_MEDIDOS.filter((t) => PALAVRAS_INGLESAS.test(traduzirEvento(t)));
    expect(
      sujos,
      `ainda com palavra inglesa na traducao: ${sujos.map((t) => `${t} -> ${traduzirEvento(t)}`).join(" | ")}`,
    ).toEqual([]);
  });

  it("sigla NAO e palavra inglesa: PMI, HPI, UoM e ANZ permanecem", () => {
    expect(traduzirEvento("Final Services PMI")).toContain("PMI");
    expect(traduzirEvento("Lloyds HPI m/m")).toContain("HPI");
    expect(traduzirEvento("Prelim UoM Consumer Sentiment")).toContain("UoM");
    expect(traduzirEvento("ANZ Commodity Prices m/m")).toContain("ANZ");
  });

  it("traduz o titulo inteiro, e nao o prefixo", () => {
    expect(traduzirEvento("Bank Holiday")).toBe("Feriado banc\u00e1rio");
    expect(traduzirEvento("Unemployment Claims")).toContain("aux\u00edlio-desemprego");
    expect(traduzirEvento("FOMC Member Waller Speaks")).toContain("Waller");
    expect(traduzirEvento("FOMC Member Waller Speaks")).toContain("fala");
  });

  it("sigla de banco central sobrevive a traducao", () => {
    // Traduzir sigla deixa o titulo MENOS reconhec\u00e1vel para quem opera todo dia.
    for (const t of ["BOJ Gov Ueda Speaks", "FOMC Member Collins Speaks", "MPC Member Pill Speaks"]) {
      expect(traduzirEvento(t)).toMatch(/BOJ|FOMC|MPC/);
    }
  });
});
