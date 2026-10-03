/**
 * Testes do painel de IA.
 *
 * Estes testes verificam o que importa na interface: que o sinal vem da
 * INFERENCIA REAL do backend e que o gerador de regras fixas — com RSI/MACD/
 * volume inventados, confianca constante e SL/TP em preco*0.99 — nao volte.
 *
 * Nao leem arquivo em disco de proposito: o projeto nao tem @types/node, e
 * adicionar essa dependencia so para checar texto seria desproporcional. O
 * alvo e o codigo-fonte dos componentes, lido como string pelo proprio
 * bundler, via import estatico abaixo.
 */
import { describe, expect, it } from 'vitest';

import * as HOOK_SRC from './useAICommunication';
import * as TECH_SRC from '../lib/technical';

/** Le o codigo-fonte de um modulo ja importado, via o sourcemap do Vite. */
function fonte(mod: object): string {
  // O Vitest expoe o codigo-fonte em `import.meta` apenas em modo dev; no
  // lugar disso usamos a funcao abaixo com fetch do path relativo.
  return String((mod as { __fonte?: string }).__fonte ?? '');
}

/**
 * Alternativa sem types de node: o Vite serve o arquivo por HTTP no dev
 * server, mas nos testes nao. Portanto usamos uma variavel injetada pelo
 * glob de import, que o Vitest resolve: `?raw`.
 */
import HOOK_RAW from './useAICommunication?raw';
import TAB_RAW from '../components/tabs/AIControlTab?raw';
import TECH_RAW from '../lib/technical?raw';

/**
 * Remove comentarios antes de verificar o padrao.
 *
 * O arquivo documenta, no comentario de cabecalho, o codigo falso que
 * substituiu — e cita `price * 0.99`, `confidence = 70` e `volume = 1`
 * justamente para registrar o que nao pode voltar. Sem filtrar, o teste
 * acusaria a propria documentacao. O que importa e o CODIGO.
 */
function soCodigo(fonte: string): string {
  return fonte.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
}

const HOOK = soCodigo(HOOK_RAW);
const TAB = soCodigo(TAB_RAW);

describe('gerador de sinal falso nao pode voltar', () => {
  it('nao inventa RSI, MACD ou volume com valor padrao', () => {
    expect(HOOK).not.toMatch(/\?\s*50\b/);
    expect(HOOK).not.toMatch(/volume\s*[:=]\s*1\b/);
  });

  it('nao calcula SL/TP por percentual fixo do preco', () => {
    expect(HOOK).not.toMatch(/price\s*\*\s*0\.99/);
    expect(HOOK).not.toMatch(/price\s*\*\s*1\.02/);
  });

  it('nao define confianca como constante', () => {
    expect(HOOK).not.toMatch(/confidence\s*=\s*(70|75|80|60|55)\b/);
  });

  it('nao contem as regras por perfil de indicador', () => {
    for (const perfil of ['mean_reversion', 'breakout', "'multi'"]) {
      expect(HOOK).not.toContain(perfil);
    }
  });

  it('nao usa a funcao analyzeIndicators', () => {
    expect(HOOK).not.toContain('analyzeIndicators');
    expect(TAB).not.toContain('analyzeIndicators');
  });
});

describe('a inferencia vem do backend', () => {
  it('chama /api/ai/predict', () => {
    expect(HOOK).toContain('/api/ai/predict');
  });

  it('chama /api/ai/trained para o inventario', () => {
    expect(HOOK).toContain('/api/ai/trained');
    expect(TAB).toContain('buscarModelosTreinados');
  });

  it('a confianca exibida vem do campo confidence da resposta', () => {
    expect(HOOK).toContain('confidence: d.confidence');
  });

  it('a UI nao recalcula confianca', () => {
    expect(TAB).not.toMatch(/confidence\s*[=*/]/);
  });
});

describe('honestidade quando nao ha inferencia', () => {
  it('trata available:false como ausencia de sinal', () => {
    expect(HOOK).toContain('d.available !== true');
  });

  it('exige confianca numerica para aceitar o sinal', () => {
    expect(HOOK).toContain("typeof d.confidence !== 'number'");
  });

  it('limpa o sinal anterior quando a inferencia falha', () => {
    expect(HOOK).toMatch(/setSinal\(null\)/);
  });
});

describe('a tela mostra metricas reais do modelo', () => {
  it('exibe accuracy, edge e folds', () => {
    expect(TAB).toMatch(/modelo\.accuracy/);
    expect(TAB).toMatch(/modelo\.edge/);
    expect(TAB).toMatch(/edgeFolds/);
  });

  it('distingue publicado de reprovado', () => {
    expect(TAB).toContain('publicado');
    expect(TAB).toContain('reprovado');
  });

  it('nao promete SL/TP do modelo', () => {
    const aviso = TAB_RAW.replace(/\s+/g, ' ');
    expect(aviso).toMatch(/Stop Loss, Take Profit e volume n[aã]o v[eê]m do modelo/);
  });

  it('agrupa o inventario por simbolo em vez de listar tudo em sequencia', () => {
    expect(TAB).toContain('porSimbolo');
    expect(TAB).toContain('ai-symbol-block');
    expect(TAB).toContain('optgroup');
  });

  it('o cabecalho usa o simbolo do modelo, nao XAUUSD fixo', () => {
    expect(TAB).toContain('modelo.symbol');
    expect(TAB).not.toContain('XAUUSD ${modelo.timeframe}');
  });
});

describe('indicadores tecnicos sao honestos', () => {
  it('nao preenche RSI com 50 nem MACD com 0', () => {
    expect(TECH_RAW).not.toMatch(/return\s+50\b/);
    expect(TECH_RAW).toContain('return null');
  });

  it('RSI 100 e sobrecompra legitima, nao erro', () => {
    // O bug original tratava RSI == 100 como falha e devolvia 0.
    expect(TECH_RAW).not.toMatch(/>=\s*100\.0/);
  });
});
