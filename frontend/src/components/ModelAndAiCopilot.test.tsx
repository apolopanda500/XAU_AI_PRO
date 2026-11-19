// @vitest-environment jsdom
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ModelCards3DGrid, type DynamicAssetModelProfile } from './ModelCards3DGrid';
import { LiveAiRiskCopilot, analisarRegime, gerarSetups } from './LiveAiRiskCopilot';

afterEach(() => {
  cleanup();
  document.querySelectorAll('[data-xau-command-center-mounted="true"]').forEach((n) => n.remove());
});

const perfil: DynamicAssetModelProfile = {
  symbol: 'ATIVO_TESTE_01', assetClass: 'METALS', timeframe: 'M5', modelId: 'modelo_teste',
  rocAuc: 0.685, precisionPct: 64.2, featureCount: 18,
  requirements: { minAtrPoints: 110, maxSpreadPoints: 45, minAdx: 22, preferredSession: 'Londres / Nova York' },
  liveStatus: 'READY',
};

describe('ModelCards3DGrid — 100% dinâmico', () => {
  it('renderiza perfil do catálogo e dispara seleção para o gráfico', () => {
    const onSelect = vi.fn();
    render(<ModelCards3DGrid profiles={[perfil]} onSelectSymbol={onSelect} />);
    expect(screen.getByText('ATIVO_TESTE_01')).toBeTruthy();
    expect(screen.getByText(/APTO PARA OPERAR/i)).toBeTruthy();
    expect(screen.getByText('0.685')).toBeTruthy();
    expect(screen.getByText('64.2%')).toBeTruthy();
    expect(screen.getByText('18D')).toBeTruthy();
    fireEvent.click(screen.getByText(/Abrir ATIVO_TESTE_01 no Gráfico/i));
    expect(onSelect).toHaveBeenCalledWith('ATIVO_TESTE_01');
  });
  it('PROVA NEGATIVA: catálogo vazio não inventa símbolo', () => {
    render(<ModelCards3DGrid profiles={[]} onSelectSymbol={vi.fn()} />);
    expect(screen.getByText(/Aguardando catálogo dinâmico/i)).toBeTruthy();
  });
});

describe('LiveAiRiskCopilot — leitura ao vivo e fail-closed', () => {
  const base = { symbol: 'PAR_DINAMICO', timeframe: 'M15', bid: 2500.0, ask: 2500.2,
    spreadPoints: 20, rsi: 61.5, adx: 29.0, atrPoints: 100, balance: 10000,
    dailyDrawdownPct: 0.5, maxDailyDrawdownPct: 3.0, point: 0.01 };

  it('gera setup de tendência e aplica na boleta', () => {
    const onApply = vi.fn();
    render(<LiveAiRiskCopilot telemetry={base} onApplySetupToTicket={onApply} />);
    expect(screen.getByText(/TENDÊNCIA DE ALTA INSTITUCIONAL/i)).toBeTruthy();
    expect(screen.getByText(/Continuação de Alta · PAR_DINAMICO/i)).toBeTruthy();
    fireEvent.click(screen.getByText(/Carregar Parâmetros na Boleta de Risco/i));
    expect(onApply).toHaveBeenCalledTimes(1);
  });
  it('PROVA NEGATIVA: spread alto veta todo setup', () => {
    render(<LiveAiRiskCopilot telemetry={{ ...base, spreadPoints: 60, adx: 32, rsi: 60 }} />);
    expect(screen.getByText(/SPREAD ELEVADO \(PROTEÇÃO ATIVA\)/i)).toBeTruthy();
    expect(screen.getByText(/IA em Vigilância Ativa/i)).toBeTruthy();
    expect(gerarSetups({ ...base, spreadPoints: 60 })).toHaveLength(0);
  });
  it('PROVA NEGATIVA: sem point real da corretora, nenhum preço é inventado', () => {
    expect(gerarSetups({ ...base, point: undefined })).toHaveLength(0);
    expect(gerarSetups({ ...base, point: 0 })).toHaveLength(0);
  });
  it('classifica exaustão por RSI extremo', () => {
    expect(analisarRegime({ ...base, rsi: 78, adx: 10 }).label).toMatch(/EXAUSTÃO/);
  });
});
