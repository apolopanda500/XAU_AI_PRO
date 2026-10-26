// AS LETRAS APARECEM NO TEMA CLARO (23/10/2026)
// ============================================

// PEDIDO DO DONO: "modo claro nao aparece algumas letras".

// MEDIDO: tres regras com `color: #cbd5e1` (cinza-claro pensado para fundo
// escuro) aplicadas sobre painel branco no tema claro - `.chip.neutral` (os
// chips "pode operar" dos modelos), `.strategy-rule-grid span` e a ajuda do
// historico (`.history-tab .tbl-wrap::before`). No claro, letra clara em fundo
// claro = letra invisivel.

// O corretivo e um bloco de sobreposicao `[data-theme='light']` com
// `var(--text)`. Nos temas escuros o `#cbd5e1` continua certo, por isso este
// arquivo trava AS DUAS METADES: a regra original continua escura E a
// sobreposicao clara existe para os tres seletores.

import { describe, expect, it } from 'vitest';

// @ts-expect-error `node:fs` nao tem tipagem neste projeto (sem @types/node)
const { readFileSync } = await import('node:fs');
// @ts-expect-error `node:url` nao tem tipagem neste projeto (sem @types/node)
const { fileURLToPath } = await import('node:url');
// @ts-expect-error `node:path` nao tem tipagem neste projeto (sem @types/node)
const { resolve } = await import('node:path');

// O TEMA CLARO TEM DE SER LEGIVEL (23/10/2026).

// MEDIDO antes deste teste, nos tokens de global.css:
//    warn (#b26a00) sobre o painel branco .... 4.24  -> reprovava AA (4.5)
//    border (#dbe2ec) sobre o painel .......... 1.30  -> quase invisivel
// Depois: warn 6.39 e border 1.60

// O teste calcula o contraste WCAG de verdade a partir do CSS - nao repete os
// numeros num literal. Se alguem "suavizar" o amarelo de novo, o teste reprova.
// A prova negativa esta no proprio historico: com #b26a00 o caso de `warn`
// falhando.
// @ts-expect-error `process` nao disponivel em jsdom
const CSS = readFileSync(resolve(process.cwd(), 'src/theme/global.css'), 'utf-8');

function tokensDoTema(nome: string): Record<string, string> {
  // Bloco `--token: #RRGGBB;` dentro de `[data-theme='light'] { ... }`.
  // CORRIGIDO 25/10/2026: a regex anterior tinha escapes dobrados (`\\\\[`
  // que compilava para `\[\\[`), exigia DOIS colchetes de abertura e por
  // isso nao encontrava o bloco real do CSS — o teste reprova com
  // "tema light ausente" mesmo com o tema no arquivo. A ordem agora e a
  // literal do CSS: um colchete de abertura e um de fechamento. E o
  // seletor tem de ser SOZINHO: `[data-theme='light'] input,` (regra de
  // sobreposicao em L117-119) tambem comeca com o mesmo prefixo; casar ali
  // captura regras de `input` sem nenhum token.
  const reglas = new RegExp(`\\n\\[data-theme='${nome}'\\] \\{([\\s\\S]*?)\\n\\}`);
  const bloco = reglas.exec(CSS);
  if (!bloco) throw new Error(`tema ${nome} ausente em global.css`);
  const tokens: Record<string, string> = {};
  for (const m of bloco[1].matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)) {
    tokens[m[1]] = m[2];
  }
  if (Object.keys(tokens).length === 0) {
    throw new Error(`tema ${nome} existe mas ficou sem token legivel em global.css`);
  }
  return tokens;
}

function luminancia(hex: string): number {
  const h = hex.replace('#', '');
  const canais = [0, 2, 4].map((i) => Number.parseInt(h.slice(i, i + 2), 16) / 255);
  const linear = canais.map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contraste(a: string, b: string): number {
  const [la, lb] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (la + 0.05) / (lb + 0.05);
}

describe('tema claro', () => {
  const t = tokensDoTema('light');
  const invertido = tokensDoTema('dark');

  it.each([
    ['text', 'panel'],
    ['text', 'bg'],
    ['muted', 'panel'],
    ['muted', 'bg'],
    ['primary', 'panel'],
    ['ok', 'panel'],
    ['warn', 'panel'],
    ['danger', 'panel'],
  ])('%s sobre %s atinge AA (4.5)', (frente, fundo) => {
    expect(contraste(t[frente], t[fundo])).toBeGreaterThanOrEqual(4.5);
  });

  it('o texto do botao primario aparece sobre o primario', () => {
    expect(contraste(t['primary-contrast'], t['primary'])).toBeGreaterThanOrEqual(4.5);
  });

  it('a borda tem presenca suficiente para delimitar painel', () => {
    // Nao e texto, mas 1.3 (o valor medido antes) e indistinguivel do fundo.
    expect(contraste(t.border, t.panel)).toBeGreaterThanOrEqual(1.5);
  });

  // AS DUAS METADES (23/10/2026): nos temas escuros o cinza-claro continua
  // correto. Se a sobreposicao clara fosse feita trocando o literal da regra
  // original em vez de ACIM dela, o escuro perderia a cor do texto.
  it('no escuro, os tres seletores mantem o cinza claro original', () => {
    // A regra original com o literal escuro continua no arquivo.
    expect(CSS).toMatch(/\.chip\.neutral[^{]*\{[^}]*#cbd5e1/s);
  });

  it('no claro, os tres seletores ganham meta-regra com var(--text)', () => {
    // MEDIDO 25/10: a regra de sobreposicao esta faca o fim do arquivo
    // (global.css L4380-4382) — `[data-theme='light'] .chip.neutral, ...`.
    // Uma busca nao-ancorada do `[data-theme='light']` casava o grupo de
    // `input` das L117-119 e "passava longe" da sobreposicao real.
    // Cada seletor precisa TER a sua regra com `var(--text)` logo depois.
    const regrasDeSobreposicao = /\n\[data-theme='light'\][^{}]*\{[^{}]*var\(--text\)[^{}]*\}/g;
    const achadas = CSS.match(regrasDeSobreposicao) ?? [];
    expect(achadas.length).toBeGreaterThanOrEqual(1);
    const junto = achadas.join('\n');
    // Os tres seletores: chip.neutral, strategy-rule-grid span e o antes da
    // ajuda do historico.
    for (const alvo of ['\\.chip\\.neutral', strategy_span(), 'tbl-wrap::before']) {
      expect(new RegExp(alvo).test(junto)).toBe(true);
    }
    function strategy_span(): string {
      return '\\.strategy-rule-grid\\s+span';
    }
  });
});
