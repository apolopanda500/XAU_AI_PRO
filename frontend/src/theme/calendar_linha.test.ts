// @vitest-environment jsdom
/*
  O FUNDO DA LINHA DO CALENDARIO (medido 08/10/2026)
  ===================================================
  MEDIDO nas capturas de 08/10/2026 14:14, no app instalado: a tabela do dia
  de HOJE aparecia com o papel de parede atravessando as linhas, e a do dia
  SEGUINTE aparecia opaca. Mesmo componente, mesmo dia de dado, duas iluminações
  — e o operador via "fundo diferente".

  A diferenca NAO era a regiao do dia. Era uma propriedade de outra folha:

      global.css:1112
        .calendar-tab button { background: var(--panel2) !important; }

  A linha do evento e um `<button>` (`EconomicCalendarTab.tsx:722`), entao essa
  regra pinta a superficie da linha com `!important`, sobrepondo o
  `background: transparent` do `calendar.css`.

  E o esmaecimento de evento JA DIVULGADO era:

      .cal-row.passado { opacity: 0.55; }

  `opacity` no elemento INTEIRO desvanece a superficie junto com o texto. Com o
  fundo opaco vindo de outro arquivo, a linha do dia de hoje saia 55%
  transparente e o papel de parede aparecia por tras. No dia seguinte nenhum
  evento e `passado`, nenhuma linha desvanece, e a mesma tabela saia opaca.

  E AGENTS.md §5 na forma exata: duas folhas, uma propriedade, e ninguem ligou
  as duas. O sintoma ("fundo com iluminacao errada") apontava para o calendario,
  e a causa estava na regra que NINGUEM procurava.

  Este arquivo trava:
    1. `.cal-row.passado` NAO pode ter `opacity` na linha inteira.
    2. O esmaecimento tem de existir no CONTEUDO.
    3. Nenhuma classe de linha pode ser declarada duas vezes — a segunda
       declaracao vence, e quem so le a ultima refaz o defeito.
*/
import { describe, expect, it } from 'vitest';

async function lerCss(nome: string): Promise<string> {
  // @ts-expect-error `node:fs` nao tem tipagem neste projeto (sem @types/node)
  const { readFileSync } = await import('node:fs');
  // @ts-expect-error `node:url` nao tem tipagem neste projeto (sem @types/node)
  const { fileURLToPath } = await import('node:url');
  const aqui = fileURLToPath(import.meta.url).replace(/\\/g, '/');
  const pasta = aqui.slice(0, aqui.lastIndexOf('/'));
  return String(readFileSync(`${pasta}/${nome}`, 'utf-8'));
}

/** Os blocos `{ ... }` de um seletor, com o comentario de cada um. */
function blocos(css: string, seletor: string): string[] {
  const re = new RegExp(
    `(?:/\\*[\\s\\S]*?\\*/\\s*)?${seletor.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')}\\s*\\{([^}]*)\\}`,
    'g',
  );
  const achados: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(css)) !== null) achados.push(m[1]);
  return achados;
}

describe('calendar.css — o evento passado esmaece o CONTEUDO, nao a superficie', () => {
  it('PROVA NEGATIVA DO DEFEITO: `.cal-row.passado` nao tem opacity na linha', async () => {
    const css = await lerCss('calendar.css');
    const decl = blocos(css, '.cal-row\\.passado').filter((b) => /^\s*opacity\s*:/m.test(b));

    // A REGRA INTEIRA e a linha que estava assim. Reproduzida aqui para o
    // teste nao depender de comentario:
    //     .cal-row.passado { opacity: 0.55; }
    expect(decl).toEqual([]);
  });

  it('o esmaecimento existe, e no conteudo da linha', async () => {
    const css = await lerCss('calendar.css');

    expect(css).toMatch(/\.cal-row\.passado\s+[^{]*\{[^}]*opacity\s*:/);
    // `.cal-row-time` e `.cal-row-title` sao os dois filhos que o operador le.
    expect(css).toMatch(/\.cal-row\.passado\s+\.cal-row-time/);
    expect(css).toMatch(/\.cal-row\.passado\s+\.cal-row-title/);
  });

  it('o hover de um evento passado volta a ler', async () => {
    const css = await lerCss('calendar.css');

    expect(css).toMatch(/\.cal-row\.passado:hover/);
  });
});

describe('nenhuma classe da linha e declarada duas vezes', () => {
  // Declaracao duplicada nao e soSujeira: a segunda vence, e quem le a ultima
  // acredita num valor que nao e o que a tela aplica.
  const DUPLICADAS = [
    '.cal-row\\.passado',
    '.cal-row\\.passado:hover',
    '.cal-row:hover',
    '.cal-row\\.alto',
    '.cal-row\\.medio',
  ];

  for (const seletor of DUPLICADAS) {
    it(`\`${seletor.replace(/\\/g, '')}\` aparece uma vez so`, async () => {
      const css = await lerCss('calendar.css');
      const n = blocos(css, seletor).length;

      // O nome entra na mensagem: um "expected 1" sem dizer qual seletor
      // falhou obriga a rodar o teste de novo para saber o que quebrou.
      expect(`${seletor} declarado ${n}x`).toBe(`${seletor} declarado 1x`);
    });
  }
});

describe('o que da o fundo da linha e o motivo do defeito', () => {
  it('`global.css` pinta `.calendar-tab button` com !important — e por isso que a superficie existe', async () => {
    // @ts-expect-error caminho relativo ao tema, lido como texto
    const { readFileSync } = await import('node:fs');
    // @ts-expect-error caminho relativo ao tema, lido como texto
    const { fileURLToPath } = await import('node:url');
    const aqui = fileURLToPath(import.meta.url).replace(/\\/g, '/');
    const pasta = aqui.slice(0, aqui.lastIndexOf('/'));
    const global_ = String(readFileSync(`${pasta}/global.css`, 'utf-8'));

    const bloco = global_.match(/\.calendar-tab button\s*\{([^}]*)\}/);
    expect(bloco).not.toBeNull();
    expect(bloco?.[1]).toMatch(/background:\s*var\(--panel2\)\s*!important/);
  });
});