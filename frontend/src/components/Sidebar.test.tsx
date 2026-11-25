// @vitest-environment jsdom
// O BOTAO DE RECOLHER/EXPANDIR NAO PODE SER CORTADO (11/10/2026)
// ==============================================================
// MEDIDO na captura do dono: com a barra lateral minimizada, so UMA PARTE do
// botao `›` aparecia — dificil acesso. A conta: 60px de barra menos 24px de
// padding do `.brand` = 36px para logo (34px fixos) + botao lado a lado, com
// o `.brand` em `overflow: hidden`. Recolhido, o topo empilha (logo em cima,
// botao embaixo com largura cheia).
//
// ESTE ARQUIVO TRAVA AS DUAS METADES:
//   1. o comportamento: recolher mostra "Expandir menu", e clicar volta;
//   2. a folha: `.sidebar.collapsed .brand` empilha em coluna (o que tira o
//      botao da zona de corte), e o `.collapse-btn` tem largura cheia.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { useAppStore } from '../hooks/useAppStore';

const { default: Sidebar } = await import('./Sidebar');

async function lerFolhaGlobal(): Promise<string> {
  // @ts-expect-error `node:fs` nao tem tipagem neste projeto (sem @types/node)
  const { readFileSync } = await import('node:fs');
  // @ts-expect-error `node:url` nao tem tipagem neste projeto (sem @types/node)
  const { fileURLToPath } = await import('node:url');
  const aqui = fileURLToPath(import.meta.url).replace(/\\/g, '/');
  const pasta = aqui.slice(0, aqui.lastIndexOf('/'));
  return String(readFileSync(`${pasta}/../theme/global.css`, 'utf-8'));
}

afterEach(() => {
  cleanup();
  useAppStore.setState({ sidebarOpen: true });
});

describe('Sidebar — recolher e expandir sem perder o botao', () => {
  it('PROVA: recolhido, o botao vira "Expandir menu" — e clicar volta', () => {
    useAppStore.setState({ sidebarOpen: true });
    render(<Sidebar />);
    fireEvent.click(screen.getByRole('button', { name: 'Recolher menu' }));
    expect(useAppStore.getState().sidebarOpen).toBe(false);

    // PROVA NEGATIVA: recolhido sem botao de volta seria beco sem saida — o
    // operador minimizaria uma vez e nunca mais abriria.
    const expandir = screen.getByRole('button', { name: 'Expandir menu' });
    expect(expandir).toBeTruthy();
    expect((expandir as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(expandir);
    expect(useAppStore.getState().sidebarOpen).toBe(true);
    expect(screen.getByRole('button', { name: 'Recolher menu' })).toBeTruthy();
  });

  it('PROVA: recolhido, o topo empilha — o botao sai da zona de corte', async () => {
    const folha = await lerFolhaGlobal();
    const bloco = (folha.match(/\.sidebar\.collapsed \.brand\s*\{[^}]*\}/) ?? [])[0] ?? '';
    expect(bloco, 'sem regra de empilhamento o botao volta a ser cortado').toContain(
      'flex-direction: column',
    );
    const botao = (folha.match(/\.sidebar\.collapsed \.collapse-btn\s*\{[^}]*\}/) ?? [])[0] ?? '';
    expect(botao).toContain('width: 100%');
  });

  it('PROVA: marca e carimbo reservam tamanho antes do PNG entrar', () => {
    useAppStore.setState({ sidebarOpen: true });
    render(<Sidebar />);
    const imagens = screen.getAllByAltText('XAU AI PRO') as HTMLImageElement[];
    expect(imagens.length).toBe(2);

    const [topo, rodape] = imagens;
    for (const img of imagens) {
      expect(img.getAttribute('src')).toBe('/xau-ai-pro-mark.png');
      expect(img.getAttribute('decoding')).toBe('async');
      expect(img.draggable).toBe(false);
      // PROVA NEGATIVA: sem width/height o navegador reserva 0x0 e o texto da
      // marca salta quando o PNG de 2,1 MB termina de decodificar no celular.
      expect(Number(img.getAttribute('width'))).toBeGreaterThan(0);
      expect(Number(img.getAttribute('height'))).toBeGreaterThan(0);
    }
    expect(Number(topo.getAttribute('width'))).toBe(34);
    expect(Number(rodape.getAttribute('width'))).toBe(44);
  });
});
