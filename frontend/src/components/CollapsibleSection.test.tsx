import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import CollapsibleSection from './CollapsibleSection';

describe('CollapsibleSection', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(cleanup);

  it('renderiza o conteudo aberto por padrao e persiste ao minimizar', () => {
    render(
      <CollapsibleSection id="p1" title="Painel Teste">
        <p>corpo do painel</p>
      </CollapsibleSection>,
    );
    expect(screen.getByText('corpo do painel')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /Minimizar Painel Teste/i }));
    expect(screen.queryByText('corpo do painel')).toBeNull();
    expect(window.localStorage.getItem('xau_panel_open_p1')).toBe('0');
  });

  it('respeita a preferencia salva no localStorage', () => {
    window.localStorage.setItem('xau_panel_open_p2', '0');
    render(
      <CollapsibleSection id="p2" title="Painel p2">
        <p>conteudo p2</p>
      </CollapsibleSection>,
    );
    expect(screen.queryByText('conteudo p2')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Expandir Painel p2/i }));
    expect(screen.getByText('conteudo p2')).toBeTruthy();
  });

  it('badge renderiza quando informado', () => {
    render(
      <CollapsibleSection id="p3" title="Painel p3" badge="2 item(ns)">
        <p>x</p>
      </CollapsibleSection>,
    );
    expect(screen.getByText('2 item(ns)')).toBeTruthy();
  });
});
