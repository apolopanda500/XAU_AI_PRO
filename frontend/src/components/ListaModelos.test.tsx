// @vitest-environment jsdom
// A lista de modelos treinados — o painel que diz COM QUE MODELO o Robô opera.
//
// O PEDIDO
// ========
// "mais tem que ter lista dos modelos treinados, eles vão operar automáticos,
//  seja qual for os modelos único ou multi".
//
// A DIFICULDADE REAL
// ==================
// MEDIDO (`ai_inference.listar_modelos`, 05/10/2026): **39 modelos, 28
// publicáveis**. Os M5 são REPROVADOS — `AUDUSD_M5` com accuracy 0,344 e edge
// 0,011, contra 0,465/0,132 do H1 do mesmo par.
//
// Dois erros possíveis, e este arquivo trava os dois:
//
//  1. mostrar só os publicáveis e esconder os reprovados — o operador passa a
//     achar que o app não tem M5, e não entende por que aquele par não opera;
//  2. mostrar accuracy como se fosse PREVISÃO. Vem do treino (`.meta.json`) e
//     não é promessa de resultado. A coluna diz "acerto", não "ganho".
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const M = vi.hoisted(() => ({
  modelos: [] as unknown[],
  chamadas: [] as Array<{ url: string; body: unknown }>,
  simbolo: '',
}));

vi.mock('../lib/api', () => ({ apiBase: () => 'http://127.0.0.1:9000' }));
vi.mock('../hooks/useAppStore', () => ({
  useAppStore: (s: (x: unknown) => unknown) =>
    s({
      selectedSymbol: M.simbolo,
      setSelectedSymbol: (v: string) => {
        M.simbolo = v;
      },
    }),
}));
vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({ data: { simbolo: 'GOLD', timeframe: 'H1' } }),
}));

const { default: ListaModelos } = await import('./ListaModelos');

/** Um modelo no formato REAL de `listar_modelos`. */
const modelo = (extra: Record<string, unknown>) => ({
  id: 'BTCUSD_H1',
  symbol: 'BTCUSD',
  timeframe: 'H1',
  accuracy: 0.4558,
  edge: 0.1224,
  f1: 0.51,
  test_samples: 258,
  train_date: '2026-09-01',
  publicable: true,
  pkl_present: true,
  ...extra,
});

const PUBLICAVEL = modelo({});
const REPROVADO = modelo({
  id: 'AUDUSD_M5',
  symbol: 'AUDUSD',
  timeframe: 'M5',
  accuracy: 0.344,
  edge: 0.0106,
  publicable: false,
  reason: 'edge abaixo do minimo no treino',
});
const SEM_ARTEFATO = modelo({
  id: 'EURUSD_M15',
  symbol: 'EURUSD',
  timeframe: 'M15',
  pkl_present: false,
  publicable: true,
});

beforeEach(() => {
  M.modelos = [PUBLICAVEL, REPROVADO, SEM_ARTEFATO];
  M.chamadas = [];
  M.simbolo = '';
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    M.chamadas.push({ url: String(url), body: init?.body ? JSON.parse(String(init.body)) : null });
    return { ok: true, json: async () => ({ models: M.modelos }) };
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const linhas = () => Array.from(document.querySelectorAll('.robo-modelo'));

describe('ListaModelos — o inventario real aparece inteiro', () => {
  it('lista os 39 modelos do inventario, um por linha', async () => {
    M.modelos = Array.from({ length: 39 }, (_, i) =>
      modelo({ id: `P${i}_H1`, symbol: `P${i}`, timeframe: 'H1' }),
    );
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(39));
  });

  it('o REPROVADO aparece, esmaecido, e nao sumiu', async () => {
    // PROVA NEGATIVA do erro 1: esconder o M5 faria o operador achar que o
    // app não tem M5 e não entender por que aquele par não opera.
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    const reprovado = linhas().find((n) => n.textContent?.includes('AUDUSD_M5'));
    expect(reprovado).toBeTruthy();
    expect(reprovado?.className).toContain('reprovado');
    // E o motivo da recusa está escrito — é o dado que explica a ausência.
    expect(reprovado?.getAttribute('title')).toContain('edge abaixo do minimo');
  });

  it('distingue "reprovado" de "sem artefato"', async () => {
    // São coisas diferentes: reprovado é decisão do treino; sem artefato é
    // arquivo faltando no disco. Juntar os dois esconde uma falha de instalação.
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    const semArtefato = linhas().find((n) => n.textContent?.includes('EURUSD_M15'));
    expect(semArtefato?.textContent).toContain('sem artefato');
  });

  it('conta quantos podem operar', async () => {
    render(<ListaModelos />);
    await waitFor(() => expect(document.body.textContent).toContain('1 de 3 podem operar'));
  });

  it('o publicavel vem PRIMEIRO na lista', async () => {
    // Edge maior decide melhor, e é o que o operador quer ver primeiro.
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    expect(linhas()[0].textContent).toContain('BTCUSD_H1');
  });
});

describe('ListaModelos — o que a tela mostra é do TREINO, não previsão', () => {
  it('as colunas dizem acerto e edge, e o cabeçalho é TREINADO', async () => {
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    const cabecalhos = Array.from(document.querySelectorAll('.robo-modelos-tabela th')).map(
      (n) => n.textContent,
    );
    expect(cabecalhos).toContain('Acerto');
    expect(cabecalhos).toContain('Edge');
    expect(document.body.textContent).toContain('Modelos treinados');
    // A palavra "previsão" não aparece: seria prometer resultado.
    expect(document.body.textContent).not.toMatch(/previs[ãa]o/i);
  });

  it('os numeros aparecem como percentual do treino', async () => {
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    /*
      O separador decimal depende do ICU do runtime, não do código: em pt-BR é
      "45,6%", e num runtime Node sem ICU completo sai "45.6%". Aceitar os dois
      é honesto — o que está sendo testado é o NÚMERO, não a vírgula.
      Fixar vírgula faria o teste reprovar por locale, que é o teste medindo a
      coisa errada.
    */
    const texto = linhas()[0].textContent ?? '';
    // accuracy 0.4558 → 45,6% · edge 0.1224 → 12,2%
    expect(texto).toMatch(/45[.,]6%/);
    expect(texto).toMatch(/12[.,]2%/);
  });

  it('numero ausente vira travessao, nunca zero', async () => {
    // accuracy ausente é ausência de dado. Mostrar 0,0% diria que o modelo
    // errou tudo, que é uma leitura errada e bem mais grave.
    M.modelos = [modelo({ accuracy: null, edge: null, f1: null, test_samples: null })];
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(1));
    const texto = linhas()[0].textContent ?? '';
    expect(texto).toContain('—');
    expect(texto).not.toContain('0,0%');
  });
});

describe('ListaModelos — escolher o modelo move par E período', () => {
  it('clicar escreve o par e manda o periodo para o motor', async () => {
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    const alvo = linhas().find((n) => n.textContent?.includes('EURUSD_M15'));
    fireEvent.click(alvo as HTMLElement);

    await waitFor(() => expect(M.simbolo).toBe('EURUSD'));
    // O periodo vai JUNTO. Se só o par mudasse, o gráfico continuaria com o
    // período do par antigo e o operador operaria EURUSD com o modelo do outro.
    await waitFor(() => {
      const config = M.chamadas.find((c) => c.url.includes('/api/auto/config'));
      expect(config?.body).toEqual({ simbolo: 'EURUSD', timeframe: 'M15' });
    });
  });

  it('marca a linha do modelo que esta no motor', async () => {
    M.modelos = [modelo({ id: 'GOLD_H1', symbol: 'GOLD', timeframe: 'H1' })];
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(1));
    // O mock de `useAutoState` diz GOLD/H1.
    expect(linhas()[0].className).toContain('em-uso');
    expect(linhas()[0].textContent).toContain('no motor');
  });

  it('nao trava quando a lista nao vem', async () => {
    vi.stubGlobal('fetch', async () => ({ ok: false, json: async () => ({}) }));
    render(<ListaModelos />);
    await waitFor(() => expect(document.querySelector('.robo-modelos')).toBeTruthy());
    // Falhou a lista: a tela diz, e o resto da página continua de pé.
    expect(document.body.textContent).toContain('Não foi possível ler os modelos treinados.');
  });

  it('lista vazia diz que nao ha inferencia', async () => {
    vi.stubGlobal('fetch', async () => ({ ok: true, json: async () => ({ models: [] }) }));
    render(<ListaModelos />);
    await waitFor(() =>
      expect(document.body.textContent).toContain('Nenhum modelo treinado encontrado'),
    );
  });
});