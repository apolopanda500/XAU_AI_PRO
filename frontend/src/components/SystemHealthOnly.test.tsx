// @vitest-environment jsdom
// Leitura da maquina na aba Sistema com cache entre montagens.
//
// O bug corrigido aqui: o componente guardava tudo em useState, entao trocar
// de aba e voltar desmontava a tela e voltava zerada — a tabela aparecia
// "--" em tudo e uma nova coleta partia do zero. O usuario lia isso como
// "recarregou sozinho". Agora a ultima leitura fica num cache de modulo e o
// estado de carregamento diz quando ainda nao ha dado.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const { invokeMock } = vi.hoisted(() => ({ invokeMock: vi.fn() }));

vi.mock('@tauri-apps/api/core', () => ({ invoke: invokeMock }));
vi.mock('../lib/api', () => ({ apiBase: () => 'http://127.0.0.1:9000' }));

const { default: SystemHealthOnly, limparCacheSistema } = await import('./SystemHealthOnly');

const HW = {
  os: 'Windows 11',
  architecture: '64-bit',
  cpu_name: 'Ryzen 7',
  cpu_cores: 8,
  cpu_usage_percent: 12,
  memory_total_gb: 16,
  memory_available_gb: 8,
  disk_total_gb: 500,
  disk_free_gb: 250,
  cpu_temperature_c: 45,
  gpu_name: 'RTX 4070',
  gpu_available: true,
  source: 'WMI',
};

describe('SystemHealthOnly — cache e carregamento', () => {
  beforeEach(() => {
    limparCacheSistema();
    invokeMock.mockReset();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true })),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('diz que esta lendo antes de ter dado, e so entao mostra a maquina', async () => {
    invokeMock.mockResolvedValue(HW);
    render(<SystemHealthOnly />);
    expect(screen.getByText('Lendo…')).toBeTruthy();
    expect(screen.queryByText('Windows 11')).toBeNull();

    await screen.findByText('Windows 11');
    expect(screen.getByText('Ao vivo')).toBeTruthy();
    expect(invokeMock).toHaveBeenCalledTimes(1);
  });

  it('ao voltar para a aba reaproveita a ultima leitura sem re-coletar', async () => {
    invokeMock.mockResolvedValue(HW);
    const montagem = render(<SystemHealthOnly />);
    await screen.findByText('Windows 11');
    montagem.unmount();
    expect(invokeMock).toHaveBeenCalledTimes(1);

    render(<SystemHealthOnly />);
    // Valor na hora, sem passar por "--".
    expect(screen.getByText('Windows 11')).toBeTruthy();
    expect(screen.getByText('Ao vivo')).toBeTruthy();
    await waitFor(() => expect(invokeMock).toHaveBeenCalledTimes(1));
  });

  it('o botao Atualizar força uma nova leitura mesmo com cache quente', async () => {
    invokeMock.mockResolvedValue(HW);
    render(<SystemHealthOnly />);
    await screen.findByText('Windows 11');
    expect(invokeMock).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar leitura da maquina' }));
    await waitFor(() => expect(invokeMock).toHaveBeenCalledTimes(2));
  });

  it('mantem o ultimo valor conhecido quando a leitura falha', async () => {
    invokeMock.mockResolvedValueOnce(HW);
    render(<SystemHealthOnly />);
    await screen.findByText('Windows 11');

    invokeMock.mockRejectedValueOnce(new Error('powershell indisponivel'));
    fireEvent.click(screen.getByRole('button', { name: 'Atualizar leitura da maquina' }));
    await screen.findByText('Falha na leitura');
    expect(screen.getByText('Windows 11')).toBeTruthy();
    expect(screen.getByText('powershell indisponivel')).toBeTruthy();
  });
});
