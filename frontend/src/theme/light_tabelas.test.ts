// TABELAS E GRADES APARECEM NO TEMA CLARO (22/10/2026)
// ===================================================
// PEDIDO DO DONO: "corrigir tambem tema claro, aplicar dentro das tabelas e
// grades".
//
// MEDIDO antes: `global.css` tinha um bloco tardio de tabela com cinza fixo de
// tema escuro (`.tbl-wrap` = rgba(9,15,24,.7), `th` = #142131/9bb5c7,
// `td` = #d6e4ed) e outro bloco "neon" ainda mais adiante (linha 15,23,42,
// cabecalho #111827). Como o ultimo vence a cascata, o tema claro herdava
// fundo escuro com letra escura. Nas grades, o cartao de KPI do inventario e o
// do painel de comando tinham `rgba(17,31,47,.72)` fixo.
//
// A trava mede a REGRA: as declaracoes de tabela e de grade usam os tokens que
// os temas trocam (`--panel`, `--panel2`, `--border`, `--text`, `--muted`,
// `--primary`) e nao cor fixa. Tambem mede os dois alias que faltavam
// (`--panel-2` e `--surface`): sem eles, oito folhas caem no reserva escuro.
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

/** Recorta o bloco `{...}` que comeca no primeiro match do seletor. */
function bloco(folha: string, seletor: RegExp): string {
  const achado = folha.search(seletor);
  expect(achado, `seletor ausente: ${seletor}`).toBeGreaterThan(-1);
  const abre = folha.indexOf('{', achado);
  const fecha = folha.indexOf('}', abre);
  return folha.slice(abre, fecha + 1);
}

describe('tema claro — tabelas e grades usam os tokens do tema', () => {
  it('o corpo da tabela nao pinta linha nem celula com cor fixa', async () => {
    const folha = await lerArquivo('global.css');
    for (const seletor of [/\.tbl tbody tr \{/, /\.tbl tbody tr:nth-child\(even\) \{/, /\.tbl th \{/]) {
      const regra = bloco(folha, seletor);
      expect(regra).toMatch(/var\(--/);
      expect(regra, `${seletor} ainda tem cor fixa`).not.toMatch(/#[0-9a-fA-F]{3,6}/);
    }
  });

  it('o cabecalho sticky do historico usa o painel do tema', async () => {
    const folha = await lerArquivo('global.css');
    const regra = bloco(folha, /\.quantum-history \.history-table-card thead \{/);
    expect(regra).toMatch(/background:\s*var\(--panel2\)/);
    expect(regra).not.toMatch(/#[0-9a-fA-F]{3,6}/);
  });

  it('a grade de regras e a grade de KPI usam painel e borda do tema', async () => {
    const folha = await lerArquivo('global.css');
    for (const seletor of [/\.strategy-rule-grid \{/, /\.inventory-panel \.grid\.cols-4 > div \{/]) {
      const regra = bloco(folha, seletor);
      expect(regra).toMatch(/background:\s*(var|color-mix)\(/);
      expect(regra).toMatch(/var\(--(panel2|primary|border)\)/);
      expect(regra, `${seletor} ainda tem cor fixa`).not.toMatch(/#[0-9a-fA-F]{3,6}/);
    }
    const celula = bloco(folha, /\.strategy-rule-grid > div \{/);
    expect(celula).toMatch(/background:\s*var\(--panel2\)/);
  });

  it('os tokens que as folhas antigas pedem existem no :root', async () => {
    const folha = await lerArquivo('global.css');
    const raiz = bloco(folha, /^:root \{/m);
    expect(raiz).toMatch(/--panel-2:\s*var\(--panel2\)/);
    expect(raiz).toMatch(/--surface:\s*var\(--panel\)/);
  });

  it('PROVA NEGATIVA: o cinza fixo do tema escuro nao voltou para a tabela', async () => {
    const folha = await lerArquivo('global.css');
    for (const proibido of ['rgba(9, 15, 24, 0.7)', '#142131', '#d6e4ed', 'rgba(17, 31, 47, 0.72)']) {
      expect(folha, `cor fixa de tema escuro: ${proibido}`).not.toContain(proibido);
    }
  });
});
