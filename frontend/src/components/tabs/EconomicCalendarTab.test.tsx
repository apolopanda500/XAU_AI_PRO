// @vitest-environment jsdom
// Calendário econômico: ordem dos dias e leitura da tabela.
//
// O agrupamento usava a ordem de chegada da API (agrupada por país/fonte),
// então o dia 29 aparecia antes do 28 e os rótulos subiam fora de ordem na
// rolagem. Aqui o que se fixa é a promessa da tela: dias do baixo para o
// alto, eventos em ordem de hora dentro de cada dia, selo Hoje/Amanhã/Ontem
// e eventos já divulgados com leitura apagada (sem sumir da tabela).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import type { EconomicEvent } from './types';

const H = vi.hoisted(() => {
  const agora = new Date();
  const hoje = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate());
  const em = (dia: number, hora: number, min: number) =>
    new Date(hoje.getTime() + dia * 86_400_000 + hora * 3_600_000 + min * 60_000);
  return { agora, hoje, em, eventos: [] as EconomicEvent[] };
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
  }),
}));

const { agruparPorDia, default: EconomicCalendarTab } = await import('./EconomicCalendarTab');
const { PAISES_SUPORTADOS } = await import('./types');

const pais = PAISES_SUPORTADOS[0];

function ev(id: string, horario: Date): EconomicEvent {
  return {
    id,
    horario,
    codigoPais: pais.codigo,
    nomePais: pais.nome,
    bandeira: pais.bandeira,
    impacto: 'alto',
    titulo: id,
    anterior: '1,0',
    consenso: '1,1',
    real: null,
    divulgado: false,
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
      [ev('a', H.em(-1, 9, 0)), ev('b', H.em(0, 9, 0)), ev('c', H.em(1, 9, 0)), ev('d', H.em(5, 9, 0))],
      H.agora,
    );

    expect(dias.map((d) => d.relato)).toEqual(['Ontem', 'Hoje', 'Amanhã', '']);
    // Datas legíveis e distintas entre si.
    expect(new Set(dias.map((d) => d.data)).size).toBe(4);
    expect(dias[1].data).toContain('/');
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

describe('EconomicCalendarTab — tabela', () => {
  afterEach(() => cleanup());

  it('renderiza os dias em ordem crescente, com selo e contagem', () => {
    H.eventos = [ev('hoje-tarde', H.em(0, 23, 0)), ev('amanha', H.em(1, 10, 0)), ev('depois', H.em(2, 8, 0)), ev('hoje-madrugada', H.em(0, 0, 0))];

    render(<EconomicCalendarTab />);

    const labels = Array.from(document.querySelectorAll('.cal-day-label'));
    expect(labels).toHaveLength(3);

    const selos = labels.map((l) => l.querySelector('.cal-day-badge')?.textContent ?? '');
    expect(selos).toEqual(['Hoje', 'Amanhã', '']);

    expect(labels[0].querySelector('.cal-day-count')?.textContent).toContain('2 eventos');
    expect(labels[1].querySelector('.cal-day-count')?.textContent).toContain('1 evento');
    expect(labels[2].querySelector('.cal-day-count')?.textContent).toContain('1 evento');

    // A ordem visual acompanha a ordem do store de dias.
    const datas = labels.map((l) => l.querySelector('.cal-day-data')?.textContent ?? '');
    expect(datas[0]).not.toBe(datas[1]);
  });

  it('mantem o evento ja divulgado na tabela, com leitura apagada', () => {
    H.eventos = [ev('passou', H.em(0, 0, 0)), ev('ainda-nao', H.em(0, 23, 59))];

    render(<EconomicCalendarTab />);

    const linhas = Array.from(document.querySelectorAll('.cal-row'));
    expect(linhas).toHaveLength(2);
    expect(linhas.filter((l) => l.classList.contains('passado'))).toHaveLength(1);
    expect(linhas.find((l) => l.classList.contains('passado'))?.textContent).toContain('passou');
  });

  it('sem eventos mostra o estado vazio, nao uma tabela quebrada', () => {
    H.eventos = [];

    render(<EconomicCalendarTab />);

    expect(document.querySelector('.cal-state')?.textContent).toContain('Nenhum evento encontrado');
    expect(document.querySelectorAll('.cal-day')).toHaveLength(0);
  });
});
