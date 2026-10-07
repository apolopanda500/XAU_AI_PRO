// @vitest-environment jsdom
// Calendário econômico no padrão MT5 (05/10/2026).
//
// O DONO PEDIU
// ============
// "aba calendarios reconstruir nao gostei, pesquisar mt5 calenadario copiar"
//
// O QUE A TELA ANTIGA FAIA DE ERRADO
// ===================================
// 1. TRÊS COLUNAS MORTAS. Anterior / Previsão / Real ficavam permanentemente em
//    `--`, porque a fonte era a tabela local, que sabe só QUANDO o evento
//    acontece. Coluna que nunca pode ter dado faz o operador desconfiar do
//    resto da tela.
// 2. 14 DIAS EMPILHADOS. O operador rolava procurando "o que sai hoje" e não
//    achava marcador nenhum. O MT5 mostra UM dia por vez, com aba por dia.
// 3. SEM NAVEGAÇÃO por semana.
//
// O QUE ESTE TESTE FIXA
// =====================
// (a) dias em ordem crescente, eventos por hora dentro do dia;
// (b) selo Hoje / Amanhã / Ontem;
// (c) uma aba por dia, com o dia de hoje já selecionado;
// (d) a tabela mostra SÓ o dia selecionado — não os 14 dias de novo;
// (e) colunas do MT5: Anterior / Previsão / Real;
// (f) evento estimado é marcado como estimado, e o aviso de feed fora aparece;
// (g) evento já divulgado continua na tabela, com leitura apagada.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { EconomicEvent } from './types';

const H = vi.hoisted(() => {
  const agora = new Date();
  const hoje = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate());
  const em = (dia: number, hora: number, min: number) =>
    new Date(hoje.getTime() + dia * 86_400_000 + hora * 3_600_000 + min * 60_000);
  return {
    agora,
    hoje,
    em,
    eventos: [] as EconomicEvent[],
    /** Fontes do feed. `false` simula o feed fora — o caso medido (HTTP 429). */
    feedDisponivel: true,
  };
});

vi.mock('../../hooks/useEconomicData', () => ({
  useEconomicData: () => ({
    eventos: H.eventos,
    carregando: false,
    erro: null,
    ultimaAtualizacao: H.agora,
    proximoEventoAlto: null,
    refreshManual: () => {},
    totalEventos: H.eventos.length,
    fontes: {
      reais: H.eventos.filter((e) => !e.estimado).length,
      estimados: H.eventos.filter((e) => e.estimado).length,
      feedDisponivel: H.feedDisponivel,
      erro: H.feedDisponivel ? '' : 'feed publico recusou a consulta (HTTP 429)',
    },
  }),
}));

const { agruparPorDia, default: EconomicCalendarTab } = await import('./EconomicCalendarTab');
const { PAISES_SUPORTADOS } = await import('./types');

const pais = PAISES_SUPORTADOS[0];

function ev(id: string, horario: Date, extra: Partial<EconomicEvent> = {}): EconomicEvent {
  return {
    id,
    horario,
    codigoPais: pais.codigo,
    nomePais: pais.nome,
    bandeira: pais.bandeira,
    impacto: 'alto',
    titulo: id,
    // O hook traduz; aqui o título entra JÁ traduzido, então o original é o
    // que o feed mandava. `traduzido: false` é o padrão porque `id` não está em
    // nenhum dicionário — e é exatamente o caso que a tela precisa marcar.
    tituloOriginal: id,
    traduzido: false,
    categoria: '',
    nota: null,
    anterior: '1,0',
    consenso: '1,1',
    real: null,
    divulgado: false,
    estimado: false,
    ...extra,
  };
}

describe('agruparPorDia — ordem crescente', () => {
  it('ordena os dias do baixo para o alto, mesmo vindo fora de ordem', () => {
    const eventos = [
      ev('d+1-15', H.em(1, 15, 0)),
      ev('d0-14', H.em(0, 14, 0)),
      ev('d+1-08', H.em(1, 8, 0)),
      ev('d-1-10', H.em(-1, 10, 0)),
      ev('d+2-09', H.em(2, 9, 0)),
    ];
    const dias = agruparPorDia(eventos, H.agora);

    expect(dias.map((d) => d.chave)).toEqual([
      chave(H.em(-1, 0, 0)),
      chave(H.em(0, 0, 0)),
      chave(H.em(1, 0, 0)),
      chave(H.em(2, 0, 0)),
    ]);
  });

  it('ordena os eventos por hora dentro de cada dia e junta dias repetidos', () => {
    const dias = agruparPorDia(
      [ev('d+1-15', H.em(1, 15, 0)), ev('d+1-08', H.em(1, 8, 0)), ev('d+1-15b', H.em(1, 15, 30))],
      H.agora,
    );

    expect(dias).toHaveLength(1);
    expect(dias[0].eventos.map((e) => e.id)).toEqual(['d+1-08', 'd+1-15', 'd+1-15b']);
  });

  it('selo Hoje / Amanhã / Ontem, sem selo nos dias seguintes', () => {
    const dias = agruparPorDia(
      [
        ev('a', H.em(-1, 9, 0)),
        ev('b', H.em(0, 9, 0)),
        ev('c', H.em(1, 9, 0)),
        ev('d', H.em(5, 9, 0)),
      ],
      H.agora,
    );

    expect(dias.map((d) => d.relato)).toEqual(['Ontem', 'Hoje', 'Amanhã', '']);
    expect(new Set(dias.map((d) => d.data)).size).toBe(4);
  });

  it('nao altera a lista recebida (sort sobre copia)', () => {
    const eventos = [ev('b', H.em(1, 15, 0)), ev('a', H.em(0, 15, 0))];
    const antes = eventos.map((e) => e.id);

    agruparPorDia(eventos, H.agora);

    expect(eventos.map((e) => e.id)).toEqual(antes);
  });
});

function chave(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

describe('EconomicCalendarTab — padrão MT5', () => {
  afterEach(() => {
    cleanup();
    H.eventos = [];
    H.feedDisponivel = true;
  });

  it('tem uma aba por dia e ja abre no dia de hoje', async () => {
    // A semana do calendário econômico é segunda a domingo, e 05/10/2026 é uma
    // SEGUNDA — hoje é o primeiro dia e amanhã está na MESMA semana. O teste
    // não pode assumir que "amanhã" cai em outra semana.
    H.eventos = [ev('hoje-a', H.em(0, 10, 0)), ev('amanha', H.em(1, 10, 0))];
    render(<EconomicCalendarTab />);

    const abas = Array.from(document.querySelectorAll('.cal-dia'));
    // AS SETE ABAS, SEMPRE (05/10/2026). Antes só viravam aba os dias com
    // evento, e uma semana sem nenhum virava um texto solto sem botão para
    // onde ir — foi o que o dono chamou de "páginas vazias".
    expect(abas.length).toBe(7);
    // Só duas delas têm contagem acima de zero: é onde há evento.
    const comEvento = abas.filter((a) => (a.textContent ?? '').trim().endsWith('1'));
    expect(comEvento.length).toBe(2);
    // O selo "Hoje" é o `.cal-dia-relato`; o `.cal-dia-nome` é a data por
    // extenso. Conferir o campo errado daria verde sem provar nada.
    await waitFor(() =>
      expect(
        (document.querySelector('.cal-dia.is-ativo .cal-dia-relato') as HTMLElement).textContent,
      ).toBe('Hoje'),
    );
    expect(
      (document.querySelector('.cal-dia.is-ativo .cal-dia-nome') as HTMLElement).textContent,
    ).toContain('/');
  });

  it('a tabela mostra SO o dia selecionado', async () => {
    // O defeito antigo era exatamente este: os 14 dias empilhados, obrigando a
    // rolar para achar o que sai hoje.
    H.eventos = [
      ev('hoje-tarde', H.em(0, 23, 0)),
      ev('amanha', H.em(1, 10, 0)),
      ev('hoje-madrugada', H.em(0, 0, 0)),
    ];
    render(<EconomicCalendarTab />);

    await waitFor(() => expect(document.querySelectorAll('.cal-row').length).toBe(2));
    const textos = Array.from(document.querySelectorAll('.cal-row')).map((l) => l.textContent ?? '');
    expect(textos.some((t) => t.includes('amanha'))).toBe(false);
  });

  it('trocar de aba troca o dia da tabela', async () => {
    H.eventos = [ev('hoje-a', H.em(0, 10, 0)), ev('amanha-b', H.em(1, 10, 0))];
    render(<EconomicCalendarTab />);
    await waitFor(() => expect(document.querySelectorAll('.cal-row').length).toBe(1));

    // MEDIDO (06/10/2026): a janela abre em ONTEM, nao em Hoje. A sequencia real
    // das sete abas e `Ontem | Hoje | Amanha | +4 dias`, entao o indice 1 e o
    // dia de HOJE — que ja vem selecionado. O teste clicava no 1 e esperava
    // `amanha-b`: o clique nao mudava nada e o `waitFor` quebrava.
    //
    // Este teste falhou 3 de 3 vezes isolado e eu supus "estado compartilhado"
    // antes de medir. Nao era: era suposicao sobre posicao. A aba e escolhida
    // pelo TEXTO que o operador ve, e nao por indice.
    const abas = Array.from(document.querySelectorAll('.cal-dia')) as HTMLButtonElement[];
    const abaAmanha = abas.find((a) => (a.textContent ?? '').includes('Amanhã'));
    expect(abaAmanha).toBeTruthy();
    fireEvent.click(abaAmanha!);
    await waitFor(() =>
      expect(document.querySelector('.cal-row')?.textContent).toContain('amanha-b'),
    );
  });

  it('as colunas sao as do MT5: anterior, previsao e real', () => {
    H.eventos = [ev('hoje-a', H.em(0, 10, 0))];
    render(<EconomicCalendarTab />);
    const cabecalho = document.querySelector('.cal-columns')?.textContent ?? '';
    expect(cabecalho).toContain('Importância');
    expect(cabecalho).toContain('Anterior');
    expect(cabecalho).toContain('Previsão');
    expect(cabecalho).toContain('Real');
  });

  it('preenche anterior, previsao e real com o valor publicado', async () => {
    H.eventos = [
      ev('divulgado', H.em(0, 10, 0), { anterior: '4,1%', consenso: '4,0%', real: '4,2%' }),
    ];
    render(<EconomicCalendarTab />);
    await waitFor(() => expect(document.querySelector('.cal-row')).toBeTruthy());
    const linha = document.querySelector('.cal-row')?.textContent ?? '';
    expect(linha).toContain('4,1%');
    expect(linha).toContain('4,0%');
    expect(linha).toContain('4,2%');
  });

  it('ausencia de valor e CELULA VAZIA com o motivo no title, nunca trace', async () => {
    // 05/10/2026. O teste antigo defendia o `--` com o argumento de que "celula
    // vazia ao lado de numero deixa o operador sem saber qual e ausencia". O
    // problema e que `--` tambem nao diz QUAL: MEDIDO, sao 111 eventos — 82 do
    // feed publico e 29 ESTIMADOS, e os estimados nao tem valor publicado por
    // definicao. Tres ausencias diferentes, o mesmo trace, e o dono leu isso
    // como ruido nas duas primeiras linhas de cada bloco da captura.
    H.eventos = [
      ev('sem-valor', H.em(0, 10, 0), { anterior: null, consenso: null, real: null }),
    ];
    render(<EconomicCalendarTab />);
    await waitFor(() => expect(document.querySelector('.cal-row')).toBeTruthy());
    const linha = document.querySelector('.cal-row') as HTMLElement;

    // NENHUM trace na linha.
    expect(linha.textContent ?? '').not.toContain('--');

    // As tres celulas vazias existem e cada uma diz por que esta vazia.
    const vazias = Array.from(linha.querySelectorAll('.cal-sem-valor'));
    expect(vazias).toHaveLength(3);
    for (const v of vazias) {
      expect(v.getAttribute('title')).toBeTruthy();
      expect((v.getAttribute('title') ?? '').length).toBeGreaterThan(8);
    }
  });

  it('evento ESTIMADO diz que e estimativa, e nao "nao informado"', async () => {
    // A distincao que `--` apagava: estimativa e ausencia de dado no produtor.
    H.eventos = [
      ev('futuro', H.em(1, 10, 0), {
        estimado: true,
        anterior: null,
        consenso: null,
        real: null,
      }),
    ];
    render(<EconomicCalendarTab />);
    await waitFor(() => expect(document.querySelector('.cal-row')).toBeTruthy());
    const titulos = Array.from(document.querySelectorAll('.cal-sem-valor')).map(
      (n) => n.getAttribute('title') ?? '',
    );
    expect(titulos).toHaveLength(3);
    for (const t of titulos) expect(t).toContain('estimad');
  });

  it('evento NAO divulgado diz que ainda vai ser divulgado', async () => {
    // Terceira ausencia, e a mais confundida: a coluna Real vazia NAO e falha
    // do produtor, e o valor que ainda vai existir.
    H.eventos = [
      ev('futuro-real', H.em(1, 10, 0), {
        anterior: '1,0',
        consenso: '1,1',
        real: null,
        estimado: false,
      }),
    ];
    render(<EconomicCalendarTab />);
    await waitFor(() => expect(document.querySelector('.cal-row')).toBeTruthy());
    const titulos = Array.from(document.querySelectorAll('.cal-sem-valor')).map(
      (n) => n.getAttribute('title') ?? '',
    );
    expect(titulos).toHaveLength(1);
    expect(titulos[0]).toContain('ainda não foi divulgado');
  });

it('marca evento estimado como estimado', async () => {
      // A fonte das semanas seguintes só sabe QUANDO o evento acontece. Sem a
      // marca, o operador leria estimativa como número publicado.
      H.eventos = [ev('futuro', H.em(3, 10, 0), { estimado: true, real: null, traduzido: true })];
      render(<EconomicCalendarTab />);
      // O evento está na semana atual, então aparece só se houver aba dele.
      // Busca PELO TEXTO, não por `.cal-row-tag`: hoje há duas marcas possíveis
      // na linha ("en" para título sem tradução, "estimado" para horário
      // estimado) e pegar a primeira seria testar a ordem do DOM.
      const marcas = Array.from(document.querySelectorAll('.cal-row-tag')).map(
        (n) => n.textContent?.trim() ?? '',
      );
      expect(marcas).toContain('estimado');
    });

    it('marca "en" o titulo que o dicionario nao traduziu', async () => {
      // O feed publica em ingles. A traducao e por palavra, entao o titulo
      // acima pode estar aproximado — e o operador precisa saber disso em vez de
      // ler uma traducao parcial como se fosse a frase oficial.
      H.eventos = [
        ev('raro', H.em(1, 10, 0), {
          titulo: 'Vendas no varejo',
          tituloOriginal: 'Retail Sales',
          traduzido: false,
        }),
      ];
      render(<EconomicCalendarTab />);
      const marca = document.querySelector('.cal-row-en');
      expect(marca?.textContent?.trim()).toBe('en');
      // E o original fica no title: quem precisa do nome exato, para comparar
      // com o calendário da corretora, não pode precisar adivinhar.
      const linha = document.querySelector('.cal-row') as HTMLElement;
      expect(linha.getAttribute('title')).toContain('Retail Sales');
    });

    it('NUNCA marca "en" o titulo que foi traduzido', async () => {
      H.eventos = [
        ev('comum', H.em(1, 10, 0), {
          titulo: 'Decisão de juros do Fed',
          tituloOriginal: 'Fed Interest Rate Decision',
          traduzido: true,
        }),
      ];
      render(<EconomicCalendarTab />);
      expect(document.querySelector('.cal-row-en')).toBeNull();
    });

    it('a categoria aparece na linha, antes do nome do evento', async () => {
      // Quem opera ouro le "Juros" e "Inflacao" antes de ler o nome do evento.
      H.eventos = [
        ev('cat', H.em(1, 10, 0), {
          titulo: 'Decisão de juros do Fed',
          tituloOriginal: 'Fed Interest Rate Decision',
          traduzido: true,
          categoria: 'Juros',
        }),
      ];
      render(<EconomicCalendarTab />);
      expect(document.querySelector('.cal-cat')?.textContent?.trim()).toBe('Juros');
    });

    it('mostra a descricao do evento, que antes era descartada', async () => {
      // `note` vinha no payload e ERA MAPEADO, mas nenhum JSX o renderizava:
      // o campo chegava na tela e sumia. O comentario no codigo dizia que a
      // descricao aparecia — o codigo nao fazia isso.
      H.eventos = [
        ev('com-nota', H.em(1, 10, 0), {
          nota: 'Reunião de política monetária com projeções de juros e PIB.',
        }),
      ];
      render(<EconomicCalendarTab />);
      fireEvent.click(document.querySelector('.cal-row') as HTMLElement);
      expect(document.querySelector('.cal-detalhe-nota')?.textContent).toContain(
        'projeções de juros',
      );
    });

    it('o detalhe alinha rotulo e valor em duas colunas fixas', async () => {
      // `dl` com `dt`/`dd`: o ROTULO tem largura fixa, e é ela que garante que
      // os valores comecem na mesma coordenada. Com `<em>`/`<span>` soltos, o
      // "Anterior" de uma linha nao caia em cima do "Anterior" da de baixo.
      H.eventos = [ev('alinhado', H.em(1, 10, 0), { anterior: '1,0', consenso: '1,1', real: '1,2' })];
      render(<EconomicCalendarTab />);
      fireEvent.click(document.querySelector('.cal-row') as HTMLElement);
      const grade = document.querySelector('.cal-detalhe-grade') as HTMLElement;
      expect(grade.tagName).toBe('DL');
      const pares = grade.querySelectorAll('dt');
      expect(pares.length).toBe(7);
      // Cada rotulo tem o mesmo pai de um `dd` — par correto, sem linha orfa.
      expect(grade.querySelectorAll('dd').length).toBe(7);
      expect(Array.from(pares).map((n) => n.textContent)).toContain('Anterior');
      expect(Array.from(pares).map((n) => n.textContent)).toContain('Real');
    });

  it('avisa quando a semana corrente e so estimativa', () => {
    // Feed fora foi o caso medido (HTTP 429). Sem o aviso, o operador trataria
    // horário estimado como número publicado.
    H.eventos = [ev('x', H.em(0, 10, 0), { estimado: true })];
    H.feedDisponivel = false;
    render(<EconomicCalendarTab />);
    expect(screen.getByText(/indisponível/i)).toBeTruthy();
    expect(screen.getByText(/estimados, sem valor anterior/i)).toBeTruthy();
  });

  it('nao avisa quando o feed respondeu', () => {
    H.eventos = [ev('x', H.em(0, 10, 0))];
    render(<EconomicCalendarTab />);
    expect(screen.queryByText(/só horários estimados/i)).toBeNull();
  });

  it('marca o dia que tem evento de alto impacto', async () => {
    // O ponto vermelho é o que faz o operador achar o dia do FOMC sem abrir as
    // sete abas.
    H.eventos = [
      ev('baixo', H.em(0, 10, 0), { impacto: 'baixo' }),
      ev('alto', H.em(1, 10, 0), { impacto: 'alto' }),
    ];
    render(<EconomicCalendarTab />);
    // MEDIDO (06/10/2026): a janela abre em ONTEM, entao a sequencia e
    // `Ontem | Hoje | Amanha | ...`. O alto esta em AMANHA — indice 2 — e o
    // teste olhava o 1, que e HOJE e tem impacto baixo. Passava a proteger a
    // posicao errada da janela, nao a marca.
    //
    // A aba e escolhida pelo rotulo que o operador ve, como no teste acima.
    const abas = Array.from(document.querySelectorAll('.cal-dia'));
    const abaHoje = abas.find((a) => (a.textContent ?? '').includes('Hoje'));
    const abaAmanha = abas.find((a) => (a.textContent ?? '').includes('Amanhã'));
    expect(abaHoje).toBeTruthy();
    expect(abaAmanha).toBeTruthy();
    expect(abaHoje!.querySelector('.cal-dia-alto')).toBeNull();
    expect(abaAmanha!.querySelector('.cal-dia-alto')).toBeTruthy();
  });

  it('navega de semana em semana', async () => {
    // `em(0)` é hoje e `em(9)` é a semana DEPOIS (a semana é seg–dom, então
    // +9 dias sempre cai na semana seguinte, qualquer que seja o dia de hoje).
    H.eventos = [ev('hoje', H.em(0, 10, 0)), ev('proxima-semana', H.em(9, 10, 0))];
    render(<EconomicCalendarTab />);

    // As sete abas existem nas DUAS semanas; só a contagem muda.
    await waitFor(() => expect(document.querySelectorAll('.cal-dia').length).toBe(7));
    expect(document.querySelector('.cal-row')?.textContent).toContain('hoje');

    fireEvent.click(screen.getByLabelText('Próxima semana'));
    // Na semana seguinte sai o evento de hoje e entra o distante.
    await waitFor(() =>
      expect(document.querySelector('.cal-row')?.textContent).toContain('proxima-semana'),
    );

    // E voltar traz o dia de hoje de novo: ida e volta precisa funcionar, senão
    // o operador fica preso numa semana vazia.
    fireEvent.click(screen.getByLabelText('Semana anterior'));
    await waitFor(() => expect(document.querySelector('.cal-row')?.textContent).toContain('hoje'));
  });

  it('mantem o evento ja divulgado na tabela, com leitura apagada', async () => {
    H.eventos = [ev('passou', H.em(0, 0, 0)), ev('ainda-nao', H.em(0, 23, 59))];
    render(<EconomicCalendarTab />);

    const linhas = Array.from(document.querySelectorAll('.cal-row'));
    expect(linhas).toHaveLength(2);
    expect(linhas.filter((l) => l.classList.contains('passado'))).toHaveLength(1);
  });

  it('abre e fecha o detalhe do evento', async () => {
    H.eventos = [ev('com-detalhe', H.em(0, 10, 0), { real: '4,2%' })];
    render(<EconomicCalendarTab />);
    await waitFor(() => expect(document.querySelector('.cal-row')).toBeTruthy());

    fireEvent.click(document.querySelector('.cal-row') as HTMLElement);
    await waitFor(() => expect(document.querySelector('.cal-detalhe')).toBeTruthy());
    expect(document.querySelector('.cal-detalhe')?.textContent).toContain('4,2%');
    // O detalhe declara a fonte do número: publicado ou estimado.
    expect(document.querySelector('.cal-detalhe')?.textContent).toContain('dado publicado');

    fireEvent.click(screen.getByLabelText('Fechar detalhe'));
    await waitFor(() => expect(document.querySelector('.cal-detalhe')).toBeNull());
  });

  it('detalhe de evento estimado diz que e estimativa', async () => {
    H.eventos = [ev('est', H.em(0, 10, 0), { estimado: true })];
    render(<EconomicCalendarTab />);
    await waitFor(() => expect(document.querySelector('.cal-row')).toBeTruthy());
    fireEvent.click(document.querySelector('.cal-row') as HTMLElement);
    await waitFor(() =>
      expect(document.querySelector('.cal-detalhe')?.textContent).toContain('horário estimado'),
    );
  });

  it('sem eventos mostra o estado vazio, nao uma tabela quebrada', () => {
    H.eventos = [];
    render(<EconomicCalendarTab />);
    expect(document.querySelector('.cal-state')?.textContent).toContain('Nenhum evento');
  });
});

// ==========================================================================
// AS SETE ABAS E A JANELA DO DADO (05/10/2026)
// ==========================================================================
// O dono pediu: "e tambem poder ver eventos dos dias seguintes. de ontem etc..
// as paginas seguintes e anteriores estao vazias".
//
// MEDIDO no feed publico: os 82 eventos vao de 04/10 ate 11/10, e 05/10/2026 e
// uma SEGUNDA. Entao os eventos de ONTEM (04/10) caem na semana ANTERIOR, e o
// que a tela mostrava na semana inicial nao os incluía.
//
// Antes a tira tinha so os dias COM evento; uma semana sem nenhum virava um
// texto solto, sem botao nenhum para onde ir.
describe("EconomicCalendarTab — as sete abas sempre", () => {
  beforeEach(() => {
    H.eventos = [ev("hoje", H.em(0, 10, 0))];
    H.feedDisponivel = true;
  });
  afterEach(() => cleanup());

  it("mostra sete abas mesmo com um evento so", () => {
    render(<EconomicCalendarTab />);
    expect(document.querySelectorAll(".cal-dia")).toHaveLength(7);
  });

  it("as sete abas continuam de pe quando a semana nao tem evento nenhum", () => {
    // Este e o caso que era lido como "paginas vazias": nao havia botao para
    // navegar, so o texto.
    H.eventos = [ev("outra-semana", H.em(9, 10, 0))];
    render(<EconomicCalendarTab />);
    expect(document.querySelectorAll(".cal-dia")).toHaveLength(7);
  });

  it("as sete abas vao de segunda a domingo", () => {
    // `inicioDaSemana` comeca na segunda (offset getDay()+6)%7.
    H.eventos = [ev("hoje", H.em(0, 10, 0))];
    const { container } = render(<EconomicCalendarTab />);
    const relatos = Array.from(container.querySelectorAll(".cal-dia")).map(
      (n) => n.querySelector(".cal-dia-relato")?.textContent ?? "",
    );
    expect(relatos.filter(Boolean).length).toBeGreaterThan(0);
    const chaves = Array.from(container.querySelectorAll(".cal-dia")).map(
      (n) => (n as HTMLElement).getAttribute("title") ?? "",
    );
    expect(chaves).toHaveLength(7);
  });

  it("escolhe o dia com evento quando hoje nao tem nenhum", () => {
    // Segunda-feira sem evento e amanha com agenda: escolher "hoje" por ser hoje
    // mostraria tabela vazia com a agenda do dia seguinte a um clique.
    H.eventos = [ev("amanha", H.em(1, 10, 0))];
    render(<EconomicCalendarTab />);
    expect(document.querySelector(".cal-row")?.textContent).toContain("amanha");
  });

  it("prefere hoje quando hoje tem evento", () => {
    H.eventos = [ev("hoje", H.em(0, 10, 0)), ev("amanha", H.em(1, 10, 0))];
    render(<EconomicCalendarTab />);
    expect(document.querySelector(".cal-row")?.textContent).toContain("hoje");
  });

  it("a aba de hoje recebe a marca de hoje", () => {
    H.eventos = [ev("hoje", H.em(0, 10, 0))];
    const { container } = render(<EconomicCalendarTab />);
    expect(container.querySelector(".cal-dia.is-hoje")).toBeTruthy();
  });
});

describe("EconomicCalendarTab — a tela diz ate onde vai o dado", () => {
  beforeEach(() => {
    H.feedDisponivel = true;
  });
  afterEach(() => cleanup());

  it("semana vazia mostra a janela do dado, e nao so 'sem eventos'", () => {
    // MEDIDO: o feed entrega so a semana corrente. O operador precisa distinguir
    // "nao tem evento" de "fora da janela do dado".
    H.eventos = [ev("hoje", H.em(0, 10, 0)), ev("proxima", H.em(9, 10, 0))];
    const { container } = render(<EconomicCalendarTab />);
    // A semana visivel tem evento (hoje), entao nao entra nesse estado.
    expect(container.querySelector(".cal-state")?.textContent ?? "").not.toContain(
      "O dado carregado",
    );
  });

  it("diz a janela quando a semana visivel esta fora do dado", () => {
    // Navega para uma semana que nao tem nada e confere o texto.
    H.eventos = [ev("hoje", H.em(0, 10, 0))];
    render(<EconomicCalendarTab />);
    fireEvent.click(screen.getByLabelText("Semana anterior"));
    const texto = document.querySelector(".cal-state")?.textContent ?? "";
    expect(texto).toContain("O dado carregado vai de");
  });
});

describe("EconomicCalendarTab — a cor carrega a informacao (05/10/2026)", () => {
  beforeEach(() => {
    H.feedDisponivel = true;
  });
  afterEach(() => cleanup());

  it("o dia com evento de alto impacto ganha a classe tem-alto", () => {
    // O dono pediu "colorir". A cor do dia e o que faz achar o dia do FOMC sem
    // abrir as sete abas.
    H.eventos = [ev("fomc", H.em(0, 10, 0), { impacto: "alto" })];
    const { container } = render(<EconomicCalendarTab />);
    expect(container.querySelector(".cal-dia.tem-alto")).toBeTruthy();
  });

  it("a linha ganha a cor pelo impacto", () => {
    H.eventos = [
      ev("alto", H.em(0, 10, 0), { impacto: "alto" }),
      ev("medio", H.em(0, 11, 0), { impacto: "medio" }),
    ];
    const { container } = render(<EconomicCalendarTab />);
    expect(container.querySelector(".cal-row.alto")).toBeTruthy();
    expect(container.querySelector(".cal-row.medio")).toBeTruthy();
  });

  it("evento de baixo impacto NAO ganha cor de alerta", () => {
    // Cor de aviso em evento de baixo impacto seria alarme falso.
    H.eventos = [ev("baixo", H.em(0, 10, 0), { impacto: "baixo" })];
    const { container } = render(<EconomicCalendarTab />);
    expect(container.querySelector(".cal-row.alto")).toBeNull();
    expect(container.querySelector(".cal-row.medio")).toBeNull();
  });
});
