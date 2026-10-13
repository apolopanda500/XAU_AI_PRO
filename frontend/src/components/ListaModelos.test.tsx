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
    // O contador mudou em 09/10/2026: dizia "1 de 3 podem operar" e contava
    // LINHAS, quando o modelo de classe tem quatro linhas para um artefato.
    // MEDIDO: 48 linhas para 39 modelos, e o operador lia "48 modelos".
    await waitFor(() =>
      expect(document.body.textContent).toContain('1 de 3 períodos podem operar'),
    );
  });

  it('o publicavel vem PRIMEIRO na lista', async () => {
    // Edge maior decide melhor, e é o que o operador quer ver primeiro.
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    expect(linhas()[0].textContent).toContain('BTCUSD_H1');
  });
});

describe('ListaModelos — o que a tela mostra é do TREINO, não previsão', () => {
  it('o card mostra acerto e edge, e o cabeçalho é TREINADO', async () => {
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(3));
    // O card nao tem colunas: as metricas estao na capa (`acc`/`edge`) e nas
    // mini informacoes. O que esta travado e o VOCABULARIO — acerto e edge do
    // treino, nunca promessa.
    const card = linhas()[0];
    expect(card.textContent).toMatch(/acc/i);
    expect(card.textContent).toMatch(/edge/i);
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

/* ===========================================================================
   OS MODELOS DE CLASSE NA TABELA (09/10/2026)
   =========================================================================
   O DONO VIU na captura de 20:28: `MULTI_METALS | MULTI_METALS | METALS`.

   MEDIDO, eram dois defeitos no mesmo ponto:

   1. O `listar_modelos` descartava os tres artefatos sem underscore no nome
      (`MULTI_METALS`, `MULTI_FIAT`, `MULTI_CRYPTO`) — e o `MULTI_METALS` e o de
      MAIOR edge do catalogo. Travado no Python (`tests/test_ai_inference.py`).

   2. Com os multi de volta, a coluna MODELO mostrava `m.id` (nome do arquivo,
      que nos multi e o proprio simbolo) e a coluna PAR mostrava `m.symbol` — o
      mesmo texto duas vezes.

   E a chave da linha repetia: `key={m.id}` com quatro periodos do mesmo
   artefato sao quatro chaves iguais, e o React reaproveitava o no errado.
   Nao dava erro no console, so mostrava o periodo da primeira linha e
   selecionava o M5 quando o operador clicava no H1.
   ========================================================================= */
describe('os modelos multi-classe tem chave propria e rotulo que nao repete', () => {
  const cartoes = () =>
    Array.from(document.querySelectorAll('article.robo-modelo'));

  /** O valor do par nas mini informacoes do card (o `dd` do `dt` "Par"). */
  const parDe = (card: Element) => {
    const blocos = Array.from(card.querySelectorAll('.robo-modelo-mini > div'));
    const par = blocos.find((d) => d.querySelector('dt')?.textContent === 'Par');
    return (par?.querySelector('dd')?.textContent ?? '').trim();
  };

  const multi = (tf: string) =>
    modelo({
      id: 'MULTI_METALS',
      symbol: 'MULTI_METALS',
      timeframe: tf,
      label: `MODELO MULTI_METALS ${tf === 'H1' ? '1H' : tf}`,
      edge: 0.2497,
    });

  it('os quatro periodos do mesmo artefato geram quatro linhas', async () => {
    M.modelos = [multi('M5'), multi('M15'), multi('H1'), multi('H4')];
    render(<ListaModelos />);

    // Quatro linhas, uma por periodo, e nao quatro iguais.
    await waitFor(() => expect(linhas()).toHaveLength(4));
  });

  it('clicar no H1 seleciona o H1, e nao o M5 da primeira linha', async () => {
    // Mede a CHAVE. Com `key={m.id}`, o React reaproveitava o no da primeira
    // linha e a escolha do operador caia no periodo errado.
    M.modelos = [multi('M5'), multi('H1')];
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(2));

    fireEvent.click(linhas()[1]);
    await waitFor(() => expect(M.chamadas.length).toBeGreaterThan(0));

    // A chamada que importa e a que configura o motor; as outras (a leitura
    // inicial dos modelos, o estado do motor) nao escolhem nada.
    const configs = M.chamadas.filter((c) => String(c.url).includes('/api/auto/config'));
    expect(configs.length, 'clicar no H1 tem de mandar UMA configuracao').toBe(1);
    const corpo = configs[0].body as { simbolo: string; timeframe: string };
    expect(corpo.timeframe).toBe('H1');
    expect(corpo.simbolo).toBe('MULTI_METALS');
  });

  it('o nome no card nao repete o par', async () => {
    // Mede a redundancia que o dono apontou: duas colunas com o mesmo texto.
    // No card, o nome da capa (`MODELO MULTI_METALS 1H`) nao pode ser igual ao
    // par das mini informacoes (`classe METALS`).
    M.modelos = [multi('H1')];
    render(<ListaModelos />);
    await waitFor(() => expect(linhas()).toHaveLength(1));

    const card = cartoes()[0];
    const nome = card.querySelector('.mc-nome')?.textContent?.trim() ?? '';
    // A CLASSE NAO E UM ATIVO (11/10/2026)
    // =====================================
    // MEDIDO na captura do dono (12:26): a coluna PAR dizia `MULTI_METALS` — o
    // id cru do artefato, que e a CLASSE, nao um simbolo que se pode operar. A
    // cabeca da tabela dizia "37 de 37 periodos podem operar", e a coluna ao
    // lado mostrava um nome que nao existe no catalogo da corretora (§3).
    //
    // Esta trava ANTES esperava `MULTI_METALS` — ou seja, travava o valor
    // ERRADO (variante do §6: a trava mediu MODELO != PAR, nao "a classe
    // precisa aparecer como classe"). Agora ela mede o que a tela precisa
    // dizer: o operador lê `classe METALS`, e nunca um ativo inventado.
    expect(nome, 'Nome').toBe('MODELO MULTI_METALS 1H');
    const par = parDe(card);
    expect(par, 'Par').toContain('classe METALS');
    expect(par, 'nunca um simbolo cru da classe').not.toBe('METALS');
    expect(par, 'nunca o id cru do artefato').not.toBe('MULTI_METALS');
    expect(nome).not.toBe(par);
  });

  it('o contador fala em artefatos E em periodos', async () => {
    // "48 modelos" era mentira: sao 39 artefatos, tres deles com quatro
    // periodos. O operador lia a quantidade de modelos.
    M.modelos = [multi('M5'), multi('H1'), modelo({})];
    render(<ListaModelos />);

    // O CONTADOR nao estava no texto unico: o `<span>` quebrava em dois nos,
    // e o `getByText` nao achava o texto inteiro. Por isso a escrita pelo
    // `document.body.textContent`, como os outros testes deste arquivo.
    await waitFor(() =>
      expect(document.body.textContent).toContain('2 artefatos'),
    );
    expect(document.body.textContent).toContain('de 3 períodos');
  });
});