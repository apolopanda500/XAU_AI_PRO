// SELOS NAO PODEM SEQUESTRAR CONTAINERS (25/11/2026)
// ==================================================
// MEDIDO no APK 1.2.191: `[class*="selo"]` casava 12 classes no fonte, mas
// apenas 4 eram chips/badges. As outras 8 eram o cabecalho de
// "Confianca & Responsavel" (`confianca-selo`, `selo-marca`,
// `selo-desenvolvedor`, `selo-nome`, `selo-versao`, `selo-rotulo`,
// `selo-nome-dev`, `selo-contato`), que precisa de `flex-wrap: wrap` e
// quebra de linha no celular. A regra de selo impunha `inline-flex`,
// `white-space: nowrap`, `flex-shrink: 0` e `overflow: hidden`, cortando
// o nome e os contatos do desenvolvedor.
//
// PROVA NEGATIVA: o teste aplica o detector a um CSS sintetico com o
// curinga antigo e exige que ele reprove. Depois exige que o CSS real
// pass e que os selos verdadeiros continuam endurecidos.
import { describe, expect, it } from 'vitest';

// @ts-expect-error `node:fs` nao tem tipagem neste projeto (sem @types/node)
const { readFileSync } = await import('node:fs');
// @ts-expect-error `node:url` nao tem tipagem neste projeto (sem @types/node)
const { fileURLToPath } = await import('node:url');
// O caminho vem do proprio arquivo de teste: rodar `vitest --root frontend`
// a partir da raiz MQL5 nao pode fazer a folha virar `MQL5/src/theme`.
const aqui = fileURLToPath(import.meta.url).replace(/\\/g, '/');
const pasta = aqui.slice(0, aqui.lastIndexOf('/'));
const CSS = readFileSync(`${pasta}/design_system_10_10.css`, 'utf-8');

function blocosDeRegra(css: string): string[] {
  // Comentarios explicam o bug e citam as classes proibidas; se entrassem na
  // analise, o teste proibira o proprio texto que documenta a correcao.
  const semComentario = css.replace(/\/\*[\s\S]*?\*\//g, '');
  return [...semComentario.matchAll(/[^{}]+\{[^{}]*\}/g)].map((m) => m[0]);
}

function seletoresComCuringa(css: string): string[] {
  // So os curingas de selo/badge estao em causa. `kpi`, `price`, `chart` etc.
  // sao usados para numeros tabulares e composicao GPU, sem risco de layout.
  return blocosDeRegra(css)
    .filter((bloco) => /\[class\*=\s*["'](?:selo|badge)["']\s*\]/i.test(bloco.slice(0, bloco.indexOf('{'))))
    .map((bloco) => bloco.slice(0, bloco.indexOf('{')).trim());
}

function blocoDosSelos(css: string): string {
  const bloco = blocosDeRegra(css).find((parte) => {
    const seletor = parte.slice(0, parte.indexOf('{'));
    return /(^|\s)\.mc-selo(\s|,|$)/.test(seletor) && /(^|\s)\.boleta-selo(\s|,|$)/.test(seletor);
  });
  if (!bloco) throw new Error('bloco de endurecimento dos selos ausente');
  return bloco;
}

describe('design_system_10_10 — selos endurecidos, containers livres', () => {
  it('REPROVA o curinga antigo (prova negativa do detector)', () => {
    const cssAntigo = `
      .badge, [class*="badge"], [class*="selo"] {
        display: inline-flex;
        white-space: nowrap;
      }`;
    const encontrados = seletoresComCuringa(cssAntigo);
    expect(encontrados.length).toBeGreaterThan(0);
    expect(encontrados.join(' ')).toContain('[class*="selo"]');
    expect(encontrados.join(' ')).toContain('[class*="badge"]');
  });

  it('o CSS real nao transforma qualquer classe com "selo" em chip', () => {
    expect(seletoresComCuringa(CSS)).toEqual([]);
  });

  it('os quatro selos verdadeiros continuam sem quebra e sem vazamento', () => {
    const bloco = blocoDosSelos(CSS);
    const seletor = bloco.slice(0, bloco.indexOf('{'));
    for (const selo of ['.badge', '.symbol-badge', '.mc-selo', '.boleta-selo']) {
      expect(seletor, `${selo} saiu da regra dos selos`).toContain(selo);
    }
    for (const propriedade of [
      'display: inline-flex',
      'white-space: nowrap',
      'flex-shrink: 0',
      'overflow: hidden',
      'text-overflow: ellipsis',
    ]) {
      expect(bloco, `${propriedade} sumiu e o selo pode vazar`).toContain(propriedade);
    }
    expect(seletor).not.toContain('confianca-selo');
    expect(seletor).not.toContain('selo-marca');
    expect(seletor).not.toContain('selo-desenvolvedor');
  });
});
