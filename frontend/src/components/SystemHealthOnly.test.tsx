// @vitest-environment jsdom
// Aba Sistema: cache entre montagens, seções Core 1..4 e a PROVA de que não
// existe mais nenhum "--" na tela.
//
// O bug original: o componente guardava tudo em useState, então trocar de aba e
// voltar desmontava a tela e voltava zerada — a tabela aparecia com "--" em
// tudo e uma nova coleta partia do zero. O usuário lia isso como "recarregou
// sozinho".
//
// O pedido de 05/10/2026 foi outro, na mesma direção: "aba sistema tem muitos
// --- nao poluir tela e melhor core 1 core 2 core 3 core 4 estilo mt5". Os dois
// sintomas tinham a mesma CAUSA: a tabela de 6 colunas era renderizada durante
// a leitura e quatro colunas eram "--" por definição — "Livre" não existe para
// "Sistema", e temperatura nem sempre existe.
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

/** O texto que carrega o valor do SO: "Windows 11 · 64-bit". */
const soNaTela = () => screen.getByText(/Windows 11/).textContent;

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
    expect(screen.queryByText(/Windows 11/)).toBeNull();

    await screen.findByText(/Windows 11/);
    expect(screen.getByText('Ao vivo')).toBeTruthy();
    expect(invokeMock).toHaveBeenCalledTimes(1);
  });

  it('nao mostra nenhuma tabela enquanto a primeira leitura nao volta', () => {
    // A tela antiga renderizava a tabela INTEIRA durante a leitura, com "--" em
    // quase tudo. Era isso que o dono leu como travamento.
    invokeMock.mockResolvedValue(HW);
    const { container } = render(<SystemHealthOnly />);
    expect(container.querySelector('table')).toBeNull();
    expect(container.textContent).not.toContain('--');
  });

  it('ao voltar para a aba reaproveita a ultima leitura sem re-coletar', async () => {
    invokeMock.mockResolvedValue(HW);
    const montagem = render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    montagem.unmount();
    expect(invokeMock).toHaveBeenCalledTimes(1);

    render(<SystemHealthOnly />);
    // Valor na hora, sem passar por "--".
    expect(screen.getByText(/Windows 11/)).toBeTruthy();
    expect(screen.getByText('Ao vivo')).toBeTruthy();
    await waitFor(() => expect(invokeMock).toHaveBeenCalledTimes(1));
  });

  it('o botao Atualizar forca uma nova leitura mesmo com cache quente', async () => {
    invokeMock.mockResolvedValue(HW);
    render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    expect(invokeMock).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar leitura da maquina' }));
    await waitFor(() => expect(invokeMock).toHaveBeenCalledTimes(2));
  });

  it('mantem o ultimo valor conhecido quando a leitura falha', async () => {
    invokeMock.mockResolvedValueOnce(HW);
    render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);

    invokeMock.mockRejectedValueOnce(new Error('powershell indisponivel'));
    fireEvent.click(screen.getByRole('button', { name: 'Atualizar leitura da maquina' }));
    await screen.findByText('Falha na leitura');
    expect(screen.getByText(/Windows 11/)).toBeTruthy();
    expect(screen.getByText('powershell indisponivel')).toBeTruthy();
  });
});

// ==========================================================================
// CORE 1..4 (05/10/2026)
// ==========================================================================
describe('SystemHealthOnly — as quatro secoes, numeradas como no MT5', () => {
  beforeEach(() => {
    limparCacheSistema();
    invokeMock.mockReset();
    invokeMock.mockResolvedValue(HW);
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true })));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('tem exatamente quatro nucleos, na ordem 1 a 4', async () => {
    const { container } = render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    const numeros = Array.from(container.querySelectorAll('.sys-core')).map(
      (n) => n.querySelector('.sys-core-num')?.textContent,
    );
    // Quatro, e numerados: o numero é o que dá a ordem de leitura, como nas
    // janelas nomeadas do MT5.
    expect(numeros).toEqual(['Core 1', 'Core 2', 'Core 3', 'Core 4']);
  });

  it('cada nucleo tem um nome, e nenhum se repete', async () => {
    const { container } = render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    const nomes = Array.from(container.querySelectorAll('.sys-core-nome')).map(
      (n) => n.textContent,
    );
    expect(nomes).toEqual(['Máquina', 'Recursos', 'Aplicativo', 'Leitura']);
  });

  it('o SO e a arquitetura ficam na MESMA medida, com ponto e virgula', async () => {
    // Dois campos separados em duas linhas eram "Sistema: Windows 11" e
    // "Arquitetura: 64-bit" — a mesma informação em dois lugares.
    const { container } = render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    expect(soNaTela()).toContain('64-bit');
  });
});

// ==========================================================================
// PROVA NEGATIVA: nenhum "--" na tela
// ==========================================================================
describe('SystemHealthOnly — nenhum trace na tela', () => {
  beforeEach(() => {
    limparCacheSistema();
    invokeMock.mockReset();
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true })));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('com a maquina completa, nao ha nenhum "--"', async () => {
    invokeMock.mockResolvedValue(HW);
    const { container } = render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    expect(container.textContent).not.toContain('--');
  });

  it('com a maquina VAZIA, nao ha nenhum "--" e nao ha tabela', async () => {
    // O caso que mais produzia trace: uma máquina virtual, um servidor Linux
    // sem sensores, ou o WMI respondendo parcial. Antes saíam dezenas de "--".
    invokeMock.mockResolvedValue({
      os: 'Linux',
      architecture: 'x86_64',
      cpu_name: null,
      cpu_cores: 0,
      cpu_usage_percent: null,
      memory_total_gb: null,
      memory_available_gb: null,
      disk_total_gb: null,
      disk_free_gb: null,
      cpu_temperature_c: null,
      gpu_name: null,
      gpu_available: false,
      source: '/proc',
    });
    const { container } = render(<SystemHealthOnly />);
    // O SO vem na medida junto da arquitetura ("Linux · x86_64"), então a
    // busca é por padrão e não por texto exato.
    await screen.findByText(/Linux/);
    expect(container.textContent).not.toContain('--');
    // E a seção de recursos some inteira, em vez de vir com três linhas vazias.
    expect(container.querySelector('.sys-recurso')).toBeNull();
    expect(container.textContent).toContain('O sistema não expõe medição de uso.');
  });

  it('o campo que falta SOME; o campo consultado e ausente, fica escrito', async () => {
    // São duas ausências diferentes e a tela precisa distinguir: temperatura
    // não exposta é buraco; vídeo indisponível é RESPOSTA do sistema.
    invokeMock.mockResolvedValue({
      ...HW,
      cpu_temperature_c: null,
      gpu_available: false,
      gpu_name: null,
    });
    const { container } = render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    expect(container.textContent).not.toContain('°C');
    expect(container.textContent).toContain('não exposto pelo sistema');
  });

  it('video ausente continua sendo um DADO, e nao uma linha faltando', async () => {
    invokeMock.mockResolvedValue({ ...HW, gpu_available: false, gpu_name: null });
    const { container } = render(<SystemHealthOnly />);
    await screen.findByText(/Windows 11/);
    const medidas = Array.from(container.querySelectorAll('.sys-medida-rotulo')).map(
      (n) => n.textContent,
    );
    expect(medidas).toContain('Vídeo');
  });
});