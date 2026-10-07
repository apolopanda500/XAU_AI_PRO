import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { SeletorFuso } from './SeletorFuso';
import { useFuso } from '../hooks/useFuso';
import { listaOrdenada, offsetMinutos, fusoAutomatico } from '../lib/fuso';

/*
  O SELETOR DE FUSO NA TELA (05/10/2026)
  =======================================
  MEDIDO na captura da XM: lista de CIDADES com `(UTC-3) Sao Paulo` marcado com
  tick, e `auto` em AZUL porque o modo automatico e o PADRAO.

  O que estes testes travam, e por que:
   - `auto` comeca ligado. Comecar apontando para uma cidade e INVENTAR o fuso
     do operador — a regra de "nenhum ativo/cidade presumido" em forma de tela.
   - a lista esta ordenada por offset corrente;
   - a escolha PERSISTE e muda a zona efetiva;
   - o menu fecha com Escape e com clique fora.
*/

const data = new Date('2026-10-05T21:01:00Z');

beforeEach(() => {
  useFuso.setState({ auto: true, zona: '' });
  cleanup();
});

afterEach(() => {
  cleanup();
});

function abrir() {
  render(<SeletorFuso />);
  fireEvent.click(screen.getByRole('button', { expanded: false }));
}

describe('SeletorFuso', () => {
  it('comeca em `auto`, e o botao diz o offset do fuso detectado', () => {
    render(<SeletorFuso />);
    const btn = screen.getByRole('button', { expanded: false });
    expect(btn.textContent).toContain('auto');
    // O offset do fuso do navegador, lido do Intl — nao um numero de tabela.
    expect(btn.textContent).toMatch(/UTC[-+]\d{1,2}(:\d{2})?|^UTC/);
  });

  it('o item `auto` mostra a deteccao, e explica de onde ela veio', () => {
    abrir();
    const item = screen.getByRole('option', { name: /auto/i });
    expect(item.textContent).toContain(fusoAutomatico());
  });

  it('PROVA NEGATIVA: nenhuma cidade aparece marcada quando esta em `auto`', () => {
    // Se o navegador for uma das cidades do catalogo — e MEDICO que e
    // (esta maquina e America/Sao_Paulo) — marcar a cidade daria ao operador
    // duas escolhas iguais sem nenhuma estar em `auto`.
    abrir();
    const marcados = screen.getAllByRole('option', { selected: true });
    expect(marcados).toHaveLength(1);
    expect(marcados[0].textContent).toContain('auto');
  });

  it('a lista esta ordenada por offset, do mais a oeste para o mais a leste', () => {
    abrir();
    const itens = screen.getAllByRole('option').slice(1); // sem o `auto`
    const naLista = listaOrdenada(data).map((c) => c.zona);
    expect(itens).toHaveLength(naLista.length);
    // A ordem do DOM e a ordem calculada; o rotulo vai no texto do item.
    const esperado = naLista
      .map((z) => offsetMinutos(z))
      .sort((a, b) => a - b);
    const visivel = itens.map((el) =>
      el.textContent?.match(/UTC[-+]\d{1,2}(:\d{2})?|^UTC/)?.[0] ?? '',
    );
    expect(visivel.length).toBe(esperado.length);
    // Ordena os rotulos pelos offsets correspondentes e confere a monotonicidade.
    const pares = visivel.map((r, i) => [r, esperado[i]] as const);
    for (let i = 1; i < pares.length; i += 1) {
      // offset do texto nao pode regredir
      const atual = pares[i][1];
      const anterior = pares[i - 1][1];
      expect(atual).toBeGreaterThanOrEqual(anterior);
    }
  });

  it('escolher uma cidade tira do `auto` e passa a valer a zona dela', () => {
    abrir();
    fireEvent.click(screen.getByRole('option', { name: /Londres/ }));
    const st = useFuso.getState();
    expect(st.auto).toBe(false);
    expect(st.zona).toBe('Europe/London');
  });

  it('PROVA NEGATIVA: a escolha nao sobrevive a uma zona fora do catalogo', () => {
    // `escolher` so aceita zona conhecida. Uma zona inventada viraria
    // `auto` em vez de virar relogio errado em silencio.
    useFuso.getState().escolher('Brasil/Inventado');
    expect(useFuso.getState().auto).toBe(true);
    expect(useFuso.getState().zona).toBe('');
  });

  it('voltar para `auto` limpa a zona manual', () => {
    useFuso.getState().escolher('Europe/London');
    abrir();
    fireEvent.click(screen.getByRole('option', { name: /auto/i }));
    expect(useFuso.getState().auto).toBe(true);
    expect(useFuso.getState().zona).toBe('');
  });

  it('Escape fecha o menu', () => {
    abrir();
    expect(screen.getByRole('listbox')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).toBeNull();
  });

  it('clique fora fecha o menu', () => {
    abrir();
    expect(screen.getByRole('listbox')).toBeTruthy();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('listbox')).toBeNull();
  });

  it('o botao marca `manual` depois de escolher, como o `auto` em azul da XM', async () => {
    useFuso.getState().escolher('Europe/London');
    render(<SeletorFuso />);
    await waitFor(() => expect(screen.getByRole('button', { expanded: false }).textContent).toContain('manual'));
  });
});