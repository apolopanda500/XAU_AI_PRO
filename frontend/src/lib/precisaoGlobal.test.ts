// A PRECISAO NAO E PREFERENCIA GLOBAL (23/10/2026)
//
// MEDIDO no app 1.2.7: `SettingsCore.tsx` tinha o slider "Casas decimais:
// {settings.precision}" e o store tinha `precision: 2`. Leituras de
// `settings.precision` no codigo inteiro: ZERO (as outras ocorrencias eram o
// proprio slider, o default do store e o `digits` da ficha do simbolo em
// `marketApi.ts`).
//
// O comentario do arquivo dizia "ficou só a precisão decimal, que o formatador
// realmente usa" — um comentario que mentia sobre o proprio codigo, o defeito
// que o AGENTS 6 descreve. E a premissa era errada: preco, volume e moeda tem
// precisoes diferentes, e quem manda e a ficha que a corretora entrega.
//
// A trava abaixo le o FONTE sem comentario (AGENTS 6: case a regra, nao a
// palavra) — o arquivo PODE documentar a remocao, e nao pode voltar a ter o
// controle nem o campo.
import { describe, expect, it } from 'vitest';
// @ts-expect-error `node:fs` nao tem tipagem neste projeto (sem @types/node)
import fs from 'node:fs';
// @ts-expect-error `node:path` nao tem tipagem neste projeto (sem @types/node)
import path from 'node:path';

// @ts-expect-error `__dirname` nao tem tipagem neste projeto (sem @types/node)
const raiz = path.resolve(__dirname, '..');

function semComentarios(fonte: string): string {
  return fonte
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
}

const ler = (rel: string) => semComentarios(fs.readFileSync(path.join(raiz, rel), 'utf8'));

describe('precisao global de casas decimais', () => {
  it('PROVA: o store nao tem mais o campo `precision`', () => {
    const fonte = ler('hooks/useAppStore.ts');
    expect(fonte).not.toMatch(/\bprecision\s*:/);
  });

  it('PROVA: a tela nao oferece o controle de casas decimais', () => {
    const fonte = ler('components/SettingsCore.tsx');
    expect(fonte).not.toMatch(/settings\.precision/);
    // A REGRA E "NAO HA CONTROLE", NAO "A PALAVRA NAO EXISTE": a tela explica
    // ao operador de onde vem a precisao, e essa frase cita o termo. O que nao
    // pode voltar e o rotulo do slider (`Casas decimais: 2`) nem o range.
    expect(fonte).not.toMatch(/Casas decimais\s*:/i);
    expect(fonte).not.toMatch(/type=\{?["']range["']/i);
  });

  it('a tela DIZ de onde vem a precisao (a ficha do simbolo)', () => {
    expect(ler('components/SettingsCore.tsx')).toMatch(/ficha de cada s[íi]mbolo/i);
  });
});
