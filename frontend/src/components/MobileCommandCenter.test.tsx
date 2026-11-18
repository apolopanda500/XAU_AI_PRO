// @vitest-environment jsdom
// Central de comando movel - o que estes testes travam.
//
// NAO e aparencia: e a REGRA. Duas coisas nao podem regredir sem reprovar:
//   1. a tela NAO oferece comando (nem botao, nem chamada de escrita);
//   2. o servidor NAO consegue autorizar escrita pelo cliente (fail-closed).
//
// E os tres estados de falha continuam distinguiveis: 401, 429 e gateway fora
// ja produziram a mesma tela vazia em outro componente deste projeto
// (`LatenciaBar.tsx`), e a licao custou uma sessao de diagnostico errado.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, waitFor } from '@testing-library/react';

const pedidos: string[] = [];

type Resposta = { status: number; corpo: unknown };

let proxima: Resposta = { status: 500, corpo: null };

function retratoSeguro(extra: Record<string, unknown> = {}) {
  return {
    ok: true,
    read_only: true,
    commands_enabled: false,
    execution_enabled: false,
    withdrawals_enabled: false,
    gerado_em: 1_700_000_000,
    conta: {
      ok: true,
      motivo: '',
      login: 55512,
      servidor: 'XM-DEMO',
      corretora: 'XM',
      moeda: 'USD',
      saldo: 1500.5,
      equity: 1520.25,
      margem_livre: 1400,
      alavancagem: 500,
    },
    posicoes: {
      ok: true,
      disponivel: true,
      motivo: '',
      total: 1,
      lidos: 1,
      recusadas: 0,
      itens: [
        {
          ticket: 90210,
          simbolo: 'EURUSD',
          lado: 'venda',
          volume: 0.25,
          preco_abertura: 1.08412,
          preco_atual: 1.0835,
          stop_loss: 1.089,
          take_profit: 1.075,
          lucro: 12.4,
          comentario: 'mcc-test',
        },
      ],
    },
    ordens: { ok: true, disponivel: true, motivo: '', total: 0, recusadas: 0, itens: [] },
    saude: {
      ok: true,
      motivo: '',
      gateway_build: '1.2.4',
      uptime_sec: 600,
      terminal_connected: true,
    },
    risco: {
      ok: true,
      motivo: '',
      risco_por_operacao_pct: 0.5,
      perda_diaria_pct: 1.2,
      perda_diaria_limite_pct: 3,
      drawdown_pct: 4.5,
      drawdown_limite_pct: 10,
      bloqueios: [],
    },
    avisos: [],
    comandos_recusados: ['abrir ordem', 'saque ou transferencia'],
    ...extra,
  };
}

const { default: MobileCommandCenter } = await import('./MobileCommandCenter');

beforeEach(() => {
  pedidos.length = 0;
  proxima = { status: 200, corpo: retratoSeguro() };
  vi.stubGlobal('fetch', async (url: string) => {
    pedidos.push(String(url));
    return { status: proxima.status, json: async () => proxima.corpo };
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** Espera a primeira leitura terminar. */
async function montado() {
  const utils = render(<MobileCommandCenter intervaloMs={60_000} />);
  await waitFor(() => expect(pedidos.length).toBeGreaterThan(0));
  return utils;
}

describe('MobileCommandCenter — leitura, nunca comando', () => {
  it('le a rota movel do gateway, e so ela', async () => {
    await montado();
    expect(pedidos.every((u) => u.includes('/api/mobile/control'))).toBe(true);
  });

  it('PROVA NEGATIVA: nao existe nenhum botao na tela', async () => {
    const { container } = await montado();
    await waitFor(() => expect(container.querySelector('.mcc-bloco')).toBeTruthy());
    // O caminho do celular e curto demais para um alvo de clique que abre ordem.
    expect(container.querySelectorAll('button').length).toBe(0);
    expect(container.textContent ?? '').not.toMatch(/comprar|vender|fechar posi/i);
  });

  it('o selo SOMENTE LEITURA aparece mesmo em erro', async () => {
    proxima = { status: 503, corpo: null };
    const { container } = await montado();
    await waitFor(() => expect(container.querySelector('.mcc-selo')).toBeTruthy());
    expect(container.querySelector('.mcc-selo')?.textContent).toContain('SOMENTE LEITURA');
    // 503 e o gateway dizendo que nao tem dado agora - nao e "conta vazia".
    expect(container.textContent ?? '').toContain('Gateway fora');
  });

  it('mostra conta e posicao quando o retrato e seguro', async () => {
    const { container } = await montado();
    await waitFor(() => expect(container.querySelector('.mcc-simbolo')).toBeTruthy());
    const texto = container.textContent ?? '';
    expect(texto).toContain('EURUSD');
    // Lateralidade vai ESCRITA, nao so colorida.
    expect(texto).toContain('venda');
    expect(texto).toContain('XM-DEMO');
  });

  it('lado desconhecido nao vira compra nem venda', async () => {
    const corpo = retratoSeguro();
    corpo.posicoes.itens[0].lado = 'desconhecido';
    proxima = { status: 200, corpo };
    const { container } = await montado();
    await waitFor(() => expect(container.querySelector('.mcc-lado-desconhecido')).toBeTruthy());
    expect(container.querySelector('.mcc-lado-compra')).toBeNull();
  });
});

describe('MobileCommandCenter — os tres estados de falha sao distinguiveis', () => {
  it('401 diz SEM SESSAO, nao "sem posicao"', async () => {
    proxima = { status: 401, corpo: { ok: false, error: 'token invalido' } };
    const { container } = await montado();
    await waitFor(() => expect(container.textContent ?? '').toContain('Sem sessao'));
    expect(container.textContent ?? '').not.toContain('nenhuma posicao aberta');
  });

  it('429 diz COTA DO MINUTO, nao corretora fora do ar', async () => {
    proxima = { status: 429, corpo: { ok: false, error: 'rate limit excedido' } };
    const { container } = await montado();
    await waitFor(() => expect(container.textContent ?? '').toContain('Cota do minuto'));
  });

  it('rede fora diz GATEWAY FORA', async () => {
    vi.stubGlobal('fetch', async () => {
      throw new Error('ECONNREFUSED');
    });
    const { container } = render(<MobileCommandCenter intervaloMs={60_000} />);
    await waitFor(() => expect(container.textContent ?? '').toContain('Gateway fora'));
  });

  it('PROVA NEGATIVA: terminal mudo nao vira "nenhuma posicao aberta"', async () => {
    const corpo = retratoSeguro();
    corpo.posicoes = {
      ok: false,
      disponivel: false,
      motivo: 'posicoes indisponiveis: o terminal MT5 nao respondeu',
      total: 0,
      lidos: 0,
      recusadas: 0,
      itens: [],
    };
    proxima = { status: 200, corpo };
    const { container } = await montado();
    const texto = container.textContent ?? '';
    await waitFor(() => expect(texto).toContain('nao respondeu'));
    expect(texto).not.toContain('nenhuma posicao aberta');
    expect(texto).toContain('sem leitura');
  });

  it('terminal desconectado aparece escrito, nao so colorido', async () => {
    const corpo = retratoSeguro();
    corpo.saude.terminal_connected = false;
    proxima = { status: 200, corpo };
    const { container } = await montado();
    await waitFor(() => expect(container.textContent ?? '').toContain('desconectado'));
  });
});

describe('MobileCommandCenter — fail-closed do lado do cliente', () => {
  it('PROVA NEGATIVA: servidor que declara escrita habilitada NAO e exibido', async () => {
    // O gateway pode estar mal configurado; o cliente nao herda a permissao.
    proxima = {
      status: 200,
      corpo: { ...retratoSeguro(), read_only: false, commands_enabled: true },
    };
    const { container } = await montado();
    await waitFor(() => expect(container.textContent ?? '').toContain('Leitura recusada'));
    // Nenhum dado de conta/posicao pode atravessar esse estado.
    expect(container.textContent ?? '').not.toContain('EURUSD');
    expect(container.textContent ?? '').not.toContain('55512');
  });

  it('PROVA NEGATIVA: corpo invalido nao vira tela vazia silenciosa', async () => {
    proxima = { status: 200, corpo: { hello: 'world' } };
    const { container } = await montado();
    await waitFor(() => expect(container.textContent ?? '').toContain('Leitura recusada'));
  });

  it('403 do perfil de compatibilidade tambem recusa a tela', async () => {
    proxima = { status: 403, corpo: { ok: false, error: 'perfil de compatibilidade somente leitura' } };
    const { container } = await montado();
    await waitFor(() => expect(container.textContent ?? '').toContain('Leitura recusada'));
  });
});
