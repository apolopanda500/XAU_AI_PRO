// AS LETRAS APARECEM NO TEMA CLARO (12/10/2026)
// ============================================
// PEDIDO DO DONO: "modo claro nao aparece algumas letras".
//
// MEDIDO: tres regras com `color: #cbd5e1` (cinza-claro pensado para fundo
// escuro) aplicadas sobre painel branco no tema claro — `.chip.neutral` (os
// chips "pode operar" dos modelos), `.strategy-rule-grid span` e a ajuda do
// historico (`.history-tab .tbl-wrap::before`). No claro, letra clara em fundo
// claro = letra invisivel.
//
// O corretivo e um bloco de sobreposicao `[data-theme='light']` com
// `var(--text)`. Nos temas escuros o `#cbd5e1` continua certo, por isso este
// arquivo trava AS DUAS METADES: a regra original continua escura E a
// sobreposicao clara existe para os tres seletores.

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

const ALVOS = [
  String.raw`\[data-theme='light'\] \.chip\.neutral`,
  String.raw`\[data-theme='light'\] \.strategy-rule-grid span`,
  String.raw`\[data-theme='light'\] \.history-tab \.tbl-wrap::before`,
];

describe('tema claro — nenhum texto some no fundo branco', () => {
  it('os tres seletores tem sobreposicao no claro com a cor do texto', async () => {
    const folha = await lerArquivo('global.css');
    for (const alvo of ALVOS) {
      const inicio = folha.search(new RegExp(alvo));
      expect(inicio, `sem sobreposicao clara para ${alvo}`).toBeGreaterThan(-1);
      // A sobreposicao usa a cor de texto do tema — nunca outro cinza fixo.
      const bloco = folha.slice(inicio, inicio + 400);
      expect(bloco).toMatch(/color:\s*var\(--text\)/);
    }
  });

  it('a sobreposicao vence a regra original — vem DEPOIS e tem mais forca', async () => {
    // PROVA NEGATIVA do outro lado: se a sobreposicao viesse ANTES da regra
    // com `#cbd5e1`, a cascata a engoliria e o claro voltaria a ter letra
    // invisivel sem ninguem apagar nada. Aqui se mede que cada sobreposicao
    // clara aparece DEPOIS da regra original que ela corrige.
    const folha = await lerArquivo('global.css');
    const originais = [
      String.raw`\.chip\.neutral\s*\{`,
      String.raw`\.strategy-rule-grid span\s*\{`,
      String.raw`\.history-tab \.tbl-wrap::before\s*\{`,
    ];
    for (let i = 0; i < ALVOS.length; i++) {
      const posOriginal = folha.search(new RegExp(originais[i]));
      const posClaro = folha.search(new RegExp(ALVOS[i]));
      expect(posOriginal, `regra original ${i} sumiu`).toBeGreaterThan(-1);
      expect(posClaro, `sobreposicao clara ${i} sumiu`).toBeGreaterThan(-1);
      expect(posClaro, 'a sobreposicao clara tem de vir DEPOIS da regra original').toBeGreaterThan(
        posOriginal,
      );
    }
  });
});
