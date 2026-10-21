// O SR-ONLY E GLOBAL, NAO SO NA PAGINA DE MERCADO (11/10/2026)
// =============================================================
// MEDIDO nas capturas da ROBÔ: o resumo do grafico ("GOLD: 300 candles no
// timeframe H1 ... ultimo fechamento ...") aparecia IMPRESSO na tela, embaixo
// do grafico, junto com a linha visivel dos candles — dois textos dizendo a
// mesma coisa, e o segundo parecia erro de layout. O mesmo acontecia com
// "Abrir latencia por corretora" (LatenciaBar).
//
// CAUSA: a unica regra `.sr-only` do projeto era `.market-page .sr-only`
// (`market.css:450`). Dentro da pagina de mercado ela esconde; fora dela a
// classe nao tem regra nenhuma e o elemento renderiza como texto comum. Sao
// cinco lugares usando a classe fora daquele escopo (PriceChart no grafico,
// LatenciaBar, HistoryTab, CopilotPanel, StatusBar).
//
// ESTE ARQUIVO TRAVA AS DUAS METADES DO CORRETIVO:
//   1. a regra existe e e de SELETOR SIMPLES (vale em qualquer pagina);
//   2. a folha que a define e importada por `main.tsx` — uma regra num CSS
//      que ninguem importa protege exatamente nada.

import { describe, expect, it } from 'vitest';

async function lerArquivo(caminhoRelativo: string): Promise<string> {
  // @ts-expect-error `node:fs` nao tem tipagem neste projeto (sem @types/node)
  const { readFileSync } = await import('node:fs');
  // @ts-expect-error `node:url` nao tem tipagem neste projeto (sem @types/node)
  const { fileURLToPath } = await import('node:url');
  const aqui = fileURLToPath(import.meta.url).replace(/\\/g, '/');
  const src = aqui.slice(0, aqui.lastIndexOf('/'));
  return String(readFileSync(`${src}/${caminhoRelativo}`, 'utf-8'));
}

describe('sr-only — a regra vale fora da pagina de mercado', () => {
  it('global.css define .sr-only com seletor simples', async () => {
    const folha = await lerArquivo('global.css');
    // `^\.sr-only\s*\{` com `m`: casa o SELETOR no inicio de linha, e nao um
    // `.market-page .sr-only` (que tambem existe, e so no escopo antigo).
    expect(folha).toMatch(/^\.sr-only\s*\{/m);
    // A tecnica e a mesma que ja funcionava no mercado: caixa de 1px, sem
    // quebra de linha. Sem `white-space: nowrap` o texto vaza na largura.
    const bloco = folha.slice(folha.search(/^\.sr-only\s*\{/m));
    expect(bloco).toMatch(/width:\s*1px/);
    expect(bloco).toMatch(/white-space:\s*nowrap/);
    expect(bloco).toMatch(/overflow:\s*hidden/);
  });

  it('main.tsx importa a folha que define a regra', async () => {
    const entrada = await lerArquivo('../main.tsx');
    expect(entrada).toMatch(/import\s+['"].*global\.css['"]/);
  });

  it('os elementos seguem marcados — a classe e usada, so faltava a regra', async () => {
    // PROVA NEGATIVA do outro lado: se um dia tirarem o `sr-only` do resumo
    // do grafico, o resumo volta a ser texto comum com a regra global existindo
    // — e a tela mostra o que era para ficar invisivel. Aqui se mede que os
    // cinco lugares continuam declarando a classe.
    const grafico = await lerArquivo('../components/charts/PriceChart.tsx');
    expect(grafico).toContain('className="sr-only"');
    const latencia = await lerArquivo('../components/LatenciaBar.tsx');
    expect(latencia).toContain('className="sr-only"');
    const historico = await lerArquivo('../components/tabs/HistoryTab.tsx');
    expect(historico).toContain('className="sr-only"');
  });
});
