// @vitest-environment jsdom
// Trocar a credencial de uma conexão que já existe (05/10/2026).
//
// O QUE ESTE TESTE PROTEGE
// ========================
// Antes, a tela de contas e conexões só sabia CRIAR. Trocar a chave significava
// excluir a conexão e cadastrar outra com o mesmo nome — dois cliques, com a
// conta sem credencial no meio, e sem volta se o cadastro novo falhasse.
//
// Além disso, o `id` da conexão carrega `broker:market:nome`: salvar com o
// nome em branco gerava `mt5:forex:` e o backend recusava. A tela exibia um
// erro genérico em vez de o botão simplesmente não estar pronto.
//
// A garantia aqui é o CONTRATO com o backend:
//   - `PUT /api/connections/{id}` recebe só o que foi digitado;
//   - campo em branco NÃO é enviado, e o backend mantém o que está gravado;
//   - a chave atual nunca é lida de volta para a tela.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

// `vi.hoisted` corre antes de TUDO, inclusive antes do `vi.mock` — por isso o
// estado compartilhado mora aqui e o mock só o referencia. Declarar o estado
// dentro do `vi.mock` e chamar `vi.hoisted` de lá é erro de hoisting.
const estado = vi.hoisted(() => ({
  chamadas: [] as Array<{ path: string; method: string; payload?: unknown }>,
  falharLeitura: false,
}));

vi.mock('../lib/connections', () => {
  const ROTULO_BROKER = {
    mt5: 'MT5',
    binance: 'Binance',
    mexc: 'MEXC',
    bybit: 'Bybit',
    okx: 'OKX',
  };
  return {
    ROTULO_BROKER,
    marketsFor: (broker: string) =>
      broker === 'mt5' ? ['forex', 'metals', 'indices'] : ['crypto-spot', 'crypto-futures'],
    connectionAction: async (id: string, command: string) => {
      estado.chamadas.push({ path: `/api/connections/${id}/${command}`, method: 'POST' });
      // Falha SÓ na leitura: o PUT passou, e é esse o caso que a tela precisa
      // distinguir de "não salvou".
      if (estado.falharLeitura) throw new Error('Falha na comunicação com o gateway.');
      return { ok: true };
    },
    requestConnection: async (path: string, method = 'GET', payload?: unknown) => {
      estado.chamadas.push({ path, method, payload });
      return { ok: true, connections: [] };
    },
  };
});

const { default: EditarConexao } = await import('./EditarConexao');

/** Digitar em campo controlado: `fireEvent.change` e o caminho do RTL. */
function digitar(rotulo: RegExp, valor: string) {
  const campo = screen.getByLabelText(rotulo) as HTMLInputElement;
  fireEvent.change(campo, { target: { value: valor } });
  return campo;
}

const LINHA = {
  id: 'binance:crypto-spot:conta principal',
  broker: 'binance',
  market: 'crypto-spot',
  configured: true,
  active: true,
  credential_source: 'api_key' as const,
};

const SESSAO = {
  id: 'mt5:forex:principal',
  broker: 'mt5',
  market: 'forex',
  configured: false,
  active: true,
  credential_source: 'session' as const,
};

function pedir(caminho: string, metodo = 'GET') {
  return estado.chamadas.find((c) => c.path === caminho && c.method === metodo);
}

afterEach(() => {
  cleanup();
  estado.chamadas.length = 0;
  estado.falharLeitura = false;
});

async function abrir() {
  screen.getByRole('button', { name: /Trocar chave/i }).click();
  await waitFor(() => expect(document.querySelector('.conexao-edicao')).toBeTruthy());
}

describe('EditarConexao', () => {
  it('comeca fechado e abre para trocar a chave', async () => {
    render(<EditarConexao linha={LINHA} aoTerminar={() => {}} />);
    expect(screen.getByRole('button', { name: /Trocar chave/i })).toBeTruthy();
    expect(document.querySelector('.conexao-edicao')).toBeNull();
    await abrir();
    expect(screen.getByLabelText(/Nova API key/i)).toBeTruthy();
    expect(screen.getByLabelText(/Novo secret/i)).toBeTruthy();
  });

  it('envia o id da propria conexao, sem campo de nome', async () => {
    render(<EditarConexao linha={LINHA} aoTerminar={() => {}} />);
    await abrir();

    digitar(/Nova API key/i, 'CHAVE-NOVA');
    digitar(/Novo secret/i, 'SECRET-NOVO');
    screen.getByRole('button', { name: /Gravar e validar/i }).click();

    await waitFor(() =>
      expect(pedir(`/api/connections/${encodeURIComponent(LINHA.id)}`, 'PUT')).toBeTruthy(),
    );
    // O id vem do path. Sem isso, um nome digitado errado criaria conexao nova.
    expect(pedir(`/api/connections/${encodeURIComponent(LINHA.id)}`, 'PUT')?.payload).toMatchObject({
      id: LINHA.id,
      broker: 'binance',
      market: 'crypto-spot',
      api_key: 'CHAVE-NOVA',
      api_secret: 'SECRET-NOVO',
    });
  });

  it('campo em branco nao entra no payload — o backend mantem o atual', async () => {
    render(<EditarConexao linha={LINHA} aoTerminar={() => {}} />);
    await abrir();

    // So a chave. O secret em branco NAO pode virar `api_secret: ""`, que
    // sobrescreveria a credencial valida por uma vazia.
    digitar(/Nova API key/i, 'SO-A-CHAVE');
    screen.getByRole('button', { name: /Gravar e validar/i }).click();

    await waitFor(() =>
      expect(pedir(`/api/connections/${encodeURIComponent(LINHA.id)}`, 'PUT')).toBeTruthy(),
    );
    const payload = pedir(`/api/connections/${encodeURIComponent(LINHA.id)}`, 'PUT')?.payload as Record<
      string,
      string
    >;
    expect(payload.api_key).toBe('SO-A-CHAVE');
    expect('api_secret' in payload).toBe(false);
    expect('api_passphrase' in payload).toBe(false);
  });

  it('valida a leitura depois de gravar', async () => {
    render(<EditarConexao linha={LINHA} aoTerminar={() => {}} />);
    await abrir();
    digitar(/Nova API key/i, 'X');
    screen.getByRole('button', { name: /Gravar e validar/i }).click();

    // `connectionAction` recebe o id CRU e faz o encode por conta propria.
    // O mock registra o caminho como ele chegou, por isso a comparacao usa o
    // id sem encode aqui.
    await waitFor(() =>
      expect(pedir(`/api/connections/${LINHA.id}/test`, 'POST')).toBeTruthy(),
    );
  });

  it('diz que a conexao por sessao nao tem chave para trocar', async () => {
    render(<EditarConexao linha={SESSAO} aoTerminar={() => {}} />);
    await abrir();

    // MT5 usa a sessao do terminal. Pedir API key aqui seria pedir o que nao
    // existe — e o campo sumindo é a resposta certa.
    expect(screen.queryByLabelText(/Nova API key/i)).toBeNull();
    expect(screen.getByText(/sessão do terminal/i)).toBeTruthy();
  });

  it('conexao por sessao nao envia credencial nenhuma', async () => {
    render(<EditarConexao linha={SESSAO} aoTerminar={() => {}} />);
    await abrir();
    screen.getByRole('button', { name: /Gravar e validar/i }).click();

    await waitFor(() =>
      expect(pedir(`/api/connections/${encodeURIComponent(SESSAO.id)}`, 'PUT')).toBeTruthy(),
    );
    const payload = pedir(`/api/connections/${encodeURIComponent(SESSAO.id)}`, 'PUT')?.payload as Record<
      string,
      string
    >;
    expect('api_key' in payload).toBe(false);
    expect('api_secret' in payload).toBe(false);
  });

  it('explica que gravar pode ter dado certo e a leitura nao', async () => {
    // O PUT passa; a LEITURA depois dele falha. Dizer "nao salvou" seria falso.
    estado.falharLeitura = true;

    render(<EditarConexao linha={LINHA} aoTerminar={() => {}} />);
    await abrir();
    digitar(/Nova API key/i, 'X');
    screen.getByRole('button', { name: /Gravar e validar/i }).click();

    await waitFor(() => expect(screen.getByText(/pode ter sido gravada/i)).toBeTruthy());
  });

  it('nunca preenche os campos com a chave atual', async () => {
    render(<EditarConexao linha={LINHA} aoTerminar={() => {}} />);
    await abrir();

    const campo = screen.getByLabelText(/Nova API key/i) as HTMLInputElement;
    expect(campo.value).toBe('');
    expect(campo.type).toBe('password');
  });
});