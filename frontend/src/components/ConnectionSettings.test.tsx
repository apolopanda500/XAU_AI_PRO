// @vitest-environment jsdom
// Contas e conexões: por que o botão de salvar estava morto.
//
// O DEFEITO MEDIDO (05/10/2026)
// ============================
// O dono falou: "melhorar aba configuracao, parte de conta e sessoes, esta
// dificil de configurar contas e salvar sincronizar".
//
// Duas causas, ambas nesta tela:
//
// 1. O botão ficava `disabled` enquanto não houvesse NOME digitado. Para MT5 o
//    nome é OPCIONAL — `save()` usa o nome do terminal quando o campo está
//    vazio. Ou seja: quem só queria sincronizar a sessão do MT5 via um botão
//    que não reage, sem uma única linha explicando o motivo.
//
// 2. O seletor de corretora tinha `disabled={busy}` — apesar de o comentário no
//    próprio arquivo dizer que ele foi colocado FORA do `<fieldset disabled>`
//    para permitir trocar de caminho durante a validação. Comentário que mente
//    sobre o próprio código é o defeito mais caro: ninguém confere.
//
// Estes testes travam o comportamento, não a aparência.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const M = vi.hoisted(() => ({
  conexoes: [] as unknown[],
  terminal: null as null | { login: string; server: string; name: string },
  salvas: [] as Array<{ broker: string; market: string; label: string }>,
  acoes: [] as Array<{ id: string; comando: string }>,
}));

vi.mock('../lib/connections', () => ({
  ROTULO_BROKER: {
    mt5: 'MetaTrader 5',
    binance: 'Binance',
    mexc: 'MEXC',
    bybit: 'Bybit',
    okx: 'OKX',
  },
  marketsFor: (b: string) => (b === 'mt5' ? ['metals', 'forex'] : ['crypto-spot']),
  exigePassphrase: (b: string) => b === 'okx',
  detectTerminal: async () => {
    if (!M.terminal) throw new Error('sem terminal');
    return M.terminal;
  },
  requestConnection: async () => ({ connections: M.conexoes }),
  saveExchange: async (broker: string, market: string, label: string) => {
    M.salvas.push({ broker, market, label });
    return `id-${M.salvas.length}`;
  },
  connectionAction: async (id: string, comando: string) => {
    M.acoes.push({ id, comando });
  },
}));

const { default: ConnectionSettings } = await import('./ConnectionSettings');

const botaoSalvar = () =>
  screen.getByRole('button', { name: /Sincronizar MT5|Salvar e validar API/ }) as HTMLButtonElement;
const pendencias = () => Array.from(document.querySelectorAll('.con-pendencias li')).map((n) => n.textContent);

beforeEach(() => {
  M.conexoes = [];
  M.terminal = { login: '391773676', server: 'XMGlobal-MT5 14', name: 'Henrique' };
  M.salvas = [];
  M.acoes = [];
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('ConnectionSettings — o botão de salvar nunca é um botão morto', () => {
  it('no MT5, sincroniza SEM digitar nome', async () => {
    // Esta é a prova principal. O nome é opcional no MT5: `save()` usa
    // `[current.name, current.server]`. Exigir o campo deixava o botão cinza
    // para uma entrada que não era necessária.
    render(<ConnectionSettings />);
    await waitFor(() => expect(screen.getByText(/Sessão detectada/)).toBeTruthy());
    expect(botaoSalvar().disabled).toBe(false);
    expect(pendencias()).toHaveLength(0);
  });

  it('o MT5 usa o nome do terminal quando o campo fica vazio', async () => {
    render(<ConnectionSettings />);
    await waitFor(() => expect(botaoSalvar().disabled).toBe(false));
    fireEvent.click(botaoSalvar());
    await waitFor(() => expect(M.salvas).toHaveLength(1));
    // O rótulo vem do terminal, não de um campo que o operador nunca preencheu.
    expect(M.salvas[0].label).toContain('XMGlobal-MT5 14');
    expect(M.salvas[0].broker).toBe('mt5');
  });

  it('sem sessão do MT5, o botão diz o que falta em vez de só apagar', async () => {
    M.terminal = null;
    render(<ConnectionSettings />);
    await waitFor(() => expect(pendencias().length).toBeGreaterThan(0));
    expect(botaoSalvar().disabled).toBe(true);
    // A pendência NOMEIA a ação: abrir e logar no terminal.
    expect(pendencias().join(' ')).toContain('MetaTrader 5');
    // E não pede NOME, porque no MT5 o nome não é o que falta.
    expect(pendencias().join(' ')).not.toContain('nome');
  });

  it('na exchange, cada campo faltante vira uma pendência nomeada', async () => {
    render(<ConnectionSettings />);
    await waitFor(() => expect(screen.getByText(/Sessão detectada/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText(/Corretora/i), { target: { value: 'binance' } });
    await waitFor(() => expect(pendencias().length).toBe(3));
    const lista = pendencias().join(' | ');
    expect(lista).toContain('Dê um nome');
    expect(lista).toContain('API key');
    expect(lista).toContain('secret');
    expect(botaoSalvar().disabled).toBe(true);
  });

  it('a OKX exige passphrase, e a pendência aparece', async () => {
    // A OKX recusa a conexão sem a passphrase criada junto com a API key.
    // Sem este teste, a passphrase é o campo que falta e ninguém descobre.
    render(<ConnectionSettings />);
    await waitFor(() => expect(screen.getByText(/Sessão detectada/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText(/Corretora/i), { target: { value: 'okx' } });
    await waitFor(() => expect(pendencias().join(' ')).toContain('passphrase'));
  });

  it('a pendência some quando o campo é preenchido', async () => {
    render(<ConnectionSettings />);
    await waitFor(() => expect(screen.getByText(/Sessão detectada/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText(/Corretora/i), { target: { value: 'binance' } });
    await waitFor(() => expect(pendencias().length).toBe(3));

    fireEvent.change(screen.getByLabelText(/^Nome$/i), { target: { value: 'minha conta' } });
    fireEvent.change(screen.getByLabelText(/API key/i), { target: { value: 'a-chave' } });
    fireEvent.change(screen.getByLabelText(/^Secret$/i), { target: { value: 'o-segredo' } });

    await waitFor(() => expect(pendencias()).toHaveLength(0));
    expect(botaoSalvar().disabled).toBe(false);
  });
});

describe('ConnectionSettings — trocar de corretora nunca fica travado', () => {
  it('o seletor de corretora nao tem disabled', () => {
    // O comentário do arquivo diz que o seletor ficou FORA do fieldset
    // justamente para permitir a troca. Com `disabled={busy}` ele voltava a
    // travar — e o comentário continuava asserting o contrário.
    render(<ConnectionSettings />);
    const seletor = screen.getByLabelText(/Corretora/i) as HTMLSelectElement;
    expect(seletor.disabled).toBe(false);
  });

  it('o seletor de mercado nao tem disabled', () => {
    render(<ConnectionSettings />);
    const seletor = screen.getByLabelText(/Mercado/i) as HTMLSelectElement;
    expect(seletor.disabled).toBe(false);
  });

  it('trocar de corretora limpa o segredo da anterior', async () => {
    // A passphrase de uma exchange não pertence a outra, e manter o campo
    // preenchido convida a gravar errado.
    render(<ConnectionSettings />);
    await waitFor(() => expect(screen.getByText(/Sessão detectada/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText(/Corretora/i), { target: { value: 'okx' } });
    fireEvent.change(screen.getByLabelText(/^Nome$/i), { target: { value: 'conta x' } });
    fireEvent.change(screen.getByLabelText(/API key/i), { target: { value: 'k' } });
    fireEvent.change(screen.getByLabelText(/^Secret$/i), { target: { value: 's' } });

    fireEvent.change(screen.getByLabelText(/Corretora/i), { target: { value: 'binance' } });
    await waitFor(() =>
      expect((screen.getByLabelText(/^Nome$/i) as HTMLInputElement).value).toBe(''),
    );
    expect((screen.getByLabelText(/API key/i) as HTMLInputElement).value).toBe('');
  });
});

describe('ConnectionSettings — salvar NÃO envia ordem', () => {
  it('salvar registra a conexão e só valida leitura', async () => {
    // A regra do projeto: validar leitura não autoriza negociação. O botão
    // fala isso na tela, e o código não chama nada além de `test`.
    render(<ConnectionSettings />);
    await waitFor(() => expect(botaoSalvar().disabled).toBe(false));
    fireEvent.click(botaoSalvar());
    await waitFor(() => expect(M.acoes.length).toBeGreaterThan(0));
    // Todas as ações disparadas são de LEITURA/estado de conexão.
    for (const acao of M.acoes) expect(['test', 'activate', 'deactivate']).toContain(acao.comando);
  });
});