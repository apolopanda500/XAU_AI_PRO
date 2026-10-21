// OS CAMPOS DE RISCO SAO CAIXAS NOS DOIS TEMAS (13/10/2026)
// =========================================================
// MEDIDO na captura do dono: no tema escuro os campos de limite pareciam
// texto solto ("não declarada" sem caixa); no claro, caixas brancas. O bloco
// usa `--surface`, que NENHUM tema define (cai no reserva escuro), e os
// `input` nao tinham fundo nem borda proprios.
//
// A trava: a regra existe, e usa variaveis que os dois temas definem
// (`--panel2`, `--border`, `--text`) — nunca cor fixa, que seria certa num
// tema e errada no outro.

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

describe('risco — campos visiveis no claro e no escuro', () => {
  it('a regra do campo usa variaveis dos dois temas', async () => {
    const folha = await lerArquivo('robo.css');
    const inicio = folha.search(/\.robo-limites-grade \.field input\s*\{/);
    expect(inicio, 'sem regra propria para o campo de limite').toBeGreaterThan(-1);
    const bloco = folha.slice(inicio, inicio + 500);
    expect(bloco).toMatch(/background:\s*var\(--panel2\)/);
    expect(bloco).toMatch(/border:\s*1px solid var\(--border\)/);
    expect(bloco).toMatch(/color:\s*var\(--text\)/);
  });

  it('PROVA NEGATIVA: nenhum cinza fixo pinta o campo', async () => {
    // Cor fixa aqui seria certa num tema e invisivel no outro — que e o
    // defeito que esta trava apaga.
    const folha = await lerArquivo('robo.css');
    const inicio = folha.search(/\.robo-limites-grade \.field input\s*\{/);
    const bloco = folha.slice(inicio, inicio + 500);
    expect(bloco).not.toMatch(/#[0-9a-fA-F]{3,6}/);
  });
});
